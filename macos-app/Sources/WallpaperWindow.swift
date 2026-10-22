import Cocoa
import WebKit

/// One borderless, click-through window pinned to the desktop (behind icons,
/// on every Space) hosting the aquarium in wallpaper mode.
///
/// The page is loaded ONCE per display. Screen changes (resolution, arrangement, Dock,
/// wake) only move/resize the window — WKWebView autoresizes and the engine handles
/// `resize` itself (see AppDelegate.applyScreens). A display that disappears keeps its window
/// hidden and paused for a while (`park()`), so a monitor waking from standby gets the same page back.
/// A WebContent crash/kill or a failed load is reloaded with a backoff: 1 / 5 / 15 s, then every
/// 10 min and on wake or a screen change — never black forever, never a reload storm.
/// R12: the window watches its own occlusion — not `.visible` for more than 2 s → `isCovered`, and AppDelegate pauses
/// this page only (`pauseReason` "covered"); visible again → resumed at once. A second, empty window (the sensor) over
/// the display's usable area tells whether any of it shows (`usableAreaVisible`): AppDelegate trusts the window list's
/// "full-screen" verdict only while it does not.
final class WallpaperWindow: NSObject, WKNavigationDelegate {
    enum State: String {
        case loading            // navigation in flight
        case ready              // didFinish: JS API available
        case waiting            // crashed or failed; a reload is scheduled
    }

    /// Point size, scale and refresh rate of the display, as the page sees them in `__AQ_BOOT.screen`.
    struct ScreenInfo {
        var w: Int
        var h: Int
        var scale: Double
        var maxFps: Int

        init(_ screen: NSScreen) {
            w = Int(screen.frame.width.rounded())
            h = Int(screen.frame.height.rounded())
            scale = Double(screen.backingScaleFactor)
            maxFps = screen.maximumFramesPerSecond          // macOS 12+; 120 on ProMotion
        }
        var dict: [String: Any] { ["w": w, "h": h, "scale": scale, "maxFps": maxFps] }
    }

    /// Secondary displays: pixel budget (MP) and frame cap (P1.2). The main display uses the
    /// engine's defaults (3.7 MP / 2.4 MP on battery, 60 / 30 fps).
    static let secondaryBudgetMP = 2.0
    static let secondaryFps = 30
    /// Low Power Mode or a hot Mac (thermalState serious/critical), any display (P1.3): 1.8 MP.
    static let constrainedBudgetMP = 1.8
    private static let backoff: [TimeInterval] = [1, 5, 15]     // quick reloads, at most 3 per 5 min…
    private static let backoffWindow: TimeInterval = 300
    private static let slowRetry: TimeInterval = 600            // …then every 10 min (and on wake / screen change)
    /// App-side heartbeat: WebKit checks the page only while it waits on it (loads, input — a wallpaper gets
    /// neither), so every 10 s a trivial evaluateJavaScript goes to a visible, running page; no reply in 6 s →
    /// an unresponsive episode dated from the send (source "heartbeat"); a reply closes it.
    private static let heartbeatInterval: TimeInterval = 10
    private static let pingTimeout: TimeInterval = 6
    /// A page killed while a ping has waited this long was hung already (a healthy page answers in milliseconds,
    /// a 1-s stall at most delays it): the termination closes an episode dated from the send.
    private static let pingLateAtDeath: TimeInterval = 2
    /// R12: the desktop not `.visible` for longer than this → covered (a window dragged across, a Space swipe or
    /// Mission Control do not pause the page); visible again → resumed at once.
    static let coverGrace: TimeInterval = 2
    /// R12: the sensor's margin inside the usable area (visibleFrame): more than a tiled «Fill» window's margins and the
    /// rounded corners of a maximised one, so those still cover it.
    static let sensorInset: CGFloat = 24

    let displayID: CGDirectDisplayID
    private let window: NSWindow
    /// R12 (`aq.coverSensor`, on by default): clear, empty, click-through, one level above the wallpaper (which is
    /// opaque and would hide it), below the desktop icons (desktop + 20). Only opaque windows occlude, so it stays
    /// `.visible` while the aquarium shows through anywhere in the usable area: behind a translucent maximised window
    /// (a terminal with background opacity reports kCGWindowAlpha 1.0 — the window list cannot tell), during Show
    /// Desktop (windows moved by a WindowServer transform keep their bounds), with a band of the screen left free.
    private let sensor: NSWindow?
    private var sensorVisible = false                // last logged sensor state
    private var sensorEvents = 0                     // its didChangeOcclusionState notifications this run
    private let webView: WKWebView
    private let contentController: WKUserContentController
    /// The mode the page runs in (sent to it): "high" | "low" | "paused".
    private(set) var power: String
    /// R12: why the page is paused, nil while it runs: sleep | layersTest | covered | fullscreen | parked.
    private(set) var pauseReason: String?
    private var pausedSince: Date?
    private var pauseCounts: [String: Int] = [:]      // this run, by reason
    private var pausedTotals: [String: TimeInterval] = [:]   // this run, finished pauses, by reason
    /// The desktop has not been `.visible` for more than coverGrace (never while parked).
    private(set) var isCovered = false
    private var occludedSince: Date?                 // not visible since (grace running or covered)
    private var occlusionEvents = 0                  // didChangeOcclusionState notifications this run
    private var parkedNow = false
    /// AppDelegate: an occlusion notification, or covered after the grace → re-decide this page's mode and check the
    /// window list soon. `visibleAgain`: visible after not being visible (e.g. back from a full-screen Space).
    var onOcclusionChange: ((WallpaperWindow, _ visibleAgain: Bool) -> Void)?
    /// Low Power Mode or thermal pressure: the smaller pixel budget (on top of power "low").
    private(set) var constrained: Bool
    private(set) var isMain: Bool
    private(set) var state: State = .loading
    private var screenInfo: ScreenInfo
    private var closed = false
    private var loadReason: String
    private var loadStartedAt: Date?
    private var loadBudget = "null"                  // budget in the boot script of the current load (JS literal)
    private var loadVlayer = false                   // `__AQ_BOOT.vlayer` of the current load (chosen at boot only)
    private var nextReason = "crashReload"
    private var failures: [Date] = []                // terminations + failed loads, last 5 min
    private var gaveUp = false                       // quick backoff exhausted → slow retry
    /// Set while the WebContent process is unresponsive (a hung page: WebKit said so, or a heartbeat went
    /// unanswered): since when.
    private var unresponsiveSince: Date?
    private var pingSentAt: Date?                    // heartbeat in flight and timed (nil: none): episode start
    private var pingSentUptime: TimeInterval = 0     // the same send, systemUptime (stops while the Mac sleeps)
    private var pingCheckDue: TimeInterval = 0       // systemUptime when pingOverdue is due
    private var pingSeq = 0                          // bumped to disown a ping (its document is gone)
    // This run only (the persistent totals are in LifecycleStats).
    private var loadCount = 0
    private var terminationCount = 0
    private var loadFailureCount = 0
    private var unresponsiveCount = 0

    private var loaded: Bool { state == .ready }

    /// `reason` — why this page is being created: "launch" | "displayAdded"; `pauseReason` — why `power` is "paused".
    init(screen: NSScreen, displayID: CGDirectDisplayID, isMain: Bool, power: String, constrained: Bool,
         pauseReason: String? = nil, reason: String) {
        self.displayID = displayID
        self.isMain = isMain
        self.power = power
        if power == "paused" {
            let why = pauseReason ?? "paused"
            self.pauseReason = why
            pausedSince = Date()
            pauseCounts[why] = 1
        }
        self.constrained = constrained
        self.loadReason = reason
        screenInfo = ScreenInfo(screen)

        // Boot state (wallpaper flag, power mode, HUD, budget, theme, screen, crash count) reaches the page at
        // document start: the very first frame already runs at the right rate (evaluateJavaScript before
        // the page has loaded is lost). The script is rebuilt before every load (installBootScript).
        let config = WKWebViewConfiguration()
        contentController = config.userContentController
        // The backdrop is a muted, looping <video> of a real reef: let it start without a click
        // (wallpaper windows never receive user input). allowsInlineMediaPlayback is iOS-only;
        // on macOS video always plays inline.
        config.mediaTypesRequiringUserActionForPlayback = []

        webView = WKWebView(frame: screen.frame, configuration: config)
        webView.autoresizingMask = [.width, .height]
        // No white flash before the first paint: let the black window show through until the
        // page draws (the page itself starts dark and fades the scene in).
        if webView.responds(to: NSSelectorFromString("_setDrawsBackground:"))
            || webView.responds(to: NSSelectorFromString("setDrawsBackground:")) {
            webView.setValue(false, forKey: "drawsBackground")
        }
        if #available(macOS 12.0, *) { webView.underPageBackgroundColor = .black }
        if AppSettings.inspectable {
            if #available(macOS 13.3, *) { webView.isInspectable = true }
        }

        window = NSWindow(contentRect: screen.frame, styleMask: [.borderless],
                          backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false              // owned here; never closed by AppKit
        window.isOpaque = true
        window.backgroundColor = .black
        window.hasShadow = false
        window.ignoresMouseEvents = true                 // clicks fall through to desktop & icons
        window.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle, .fullScreenAuxiliary]
        // Desktop level = above the static wallpaper picture, below the desktop icons.
        window.level = NSWindow.Level(rawValue: Int(CGWindowLevelForKey(.desktopWindow)))
        window.setFrame(screen.frame, display: true)
        window.contentView = webView

        if AppSettings.coverSensor {
            let s = NSWindow(contentRect: WallpaperWindow.sensorFrame(screen), styleMask: [.borderless],
                             backing: .buffered, defer: false)
            s.isReleasedWhenClosed = false
            s.isOpaque = false
            s.backgroundColor = .clear
            s.hasShadow = false
            s.ignoresMouseEvents = true
            s.collectionBehavior = window.collectionBehavior
            s.level = NSWindow.Level(rawValue: window.level.rawValue + 1)
            sensor = s
        } else {
            sensor = nil
        }

        super.init()
        webView.navigationDelegate = self
        // Posted for this window only, on the main thread.
        NotificationCenter.default.addObserver(self, selector: #selector(occlusionChanged(_:)),
                                               name: NSWindow.didChangeOcclusionStateNotification, object: window)
        if let s = sensor {
            NotificationCenter.default.addObserver(self, selector: #selector(sensorChanged(_:)),
                                                   name: NSWindow.didChangeOcclusionStateNotification, object: s)
        }
        load(reason: reason)
        armHeartbeat()
    }

    // MARK: Loading
    private static var pageURL: URL? {
        Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "aquarium")
    }

    private func load(reason: String) {
        guard !closed else { return }
        guard let url = WallpaperWindow.pageURL else {
            Log.error("bundled aquarium/index.html not found")
            return
        }
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(recover), object: nil)
        disownPing()                                     // a ping lost with the old document is not held against the new one
        state = .loading
        loadReason = reason
        loadStartedAt = Date()
        loadBudget = budgetLiteral
        loadVlayer = AppSettings.vlayer
        loadCount += 1
        installBootScript()
        LifecycleStats.recordLoad(display: displayID, reason: reason)
        Log.info("load display \(displayID): reason=\(reason) main=\(isMain) power=\(power) vlayer=\(loadVlayer) " +
                 "\(screenInfo.w)x\(screenInfo.h)@\(screenInfo.scale)x \(screenInfo.maxFps)Hz")
        webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }

    /// A deliberate reload with a fresh boot script — ⌥ «Задник слоями (тест)»: the layered backdrop is chosen at
    /// boot (`__AQ_BOOT.vlayer`), so the page must start over. Same path as recovery (counted in `aq.pageLoads`
    /// under `reason`, e.g. "vlayer"); a recovery already scheduled is replaced by this load, and the backoff
    /// state stays as it is — this is not a failure. A parked (hidden, paused) page reloads too, so a returning
    /// display shows the chosen mode. A load in flight is simply superseded (its -999 cancel is ignored).
    func reload(reason: String) {
        guard !closed else { return }
        Log.info("display \(displayID): reload requested (\(reason), was \(state.rawValue))")
        load(reason: reason)
    }

    /// Pixel budget and frame cap for `aquariumSetBudget` / `__AQ_BOOT.budget`; nil = the engine's own
    /// (main display, not constrained). Secondary: {mp: 2, fps: 30}; Low Power Mode / heat: mp 1.8.
    private var budget: [String: Any]? {
        guard !isMain || constrained else { return nil }
        var mp = isMain ? WallpaperWindow.constrainedBudgetMP : WallpaperWindow.secondaryBudgetMP
        if constrained { mp = min(mp, WallpaperWindow.constrainedBudgetMP) }
        return ["mp": mp, "fps": isMain ? NSNull() : WallpaperWindow.secondaryFps]
    }

    /// The budget as a JS literal: `{"fps":30,"mp":2}` or `null`.
    private var budgetLiteral: String { budget.map { PageScript.literal($0) } ?? "null" }

    /// `window.__AQ_BOOT` (contract with aquarium/index.html, P1.1):
    /// {power, hud, budget: {mp, fps}|null, screen: {id, w, h (points), scale, maxFps, main}, crashes,
    ///  unresponsive, loadReason: launch|displayAdded|crashReload|retry|vlayer, appVersion, theme: auto|day|night,
    ///  vlayer: Bool}.
    /// `theme` («Тема аквариума») is decided before the page's first frame: no day → night transition at start.
    /// `vlayer` (⌥ «Задник слоями (тест)», P1.9) is read only at boot — `?vlayer=` in the URL wins, so headless
    /// tests are unaffected; the engine reports the mode in use as `aquariumPerfSnapshot().vlayer`.
    /// `__AQ_POWER` stays for older pages. Keys are only ever added (e.g. `unresponsive`, `theme`, `vlayer`), never
    /// renamed: older pages keep working.
    /// Every value goes through PageScript.literal (JSON), so nothing in it can break out of the script.
    private func bootSource() -> String {
        var screen = screenInfo.dict
        screen["id"] = Int(displayID)
        screen["main"] = isMain
        let boot: [String: Any] = [
            "power": power,
            "hud": AppSettings.hud,
            "budget": budget ?? NSNull(),
            "screen": screen,
            "crashes": LifecycleStats.terminations,
            "unresponsive": LifecycleStats.unresponsiveEpisodes,
            "loadReason": loadReason,
            "appVersion": AppSettings.appVersion,
            "theme": AppSettings.theme.rawValue,
            "vlayer": AppSettings.vlayer,
        ]
        return "window.__WALLPAPER = true; window.__AQ_POWER = \(PageScript.literal(power)); " +
               "window.__AQ_BOOT = \(PageScript.literal(boot));"
    }

    /// Takes effect on the next navigation (ours, or a reload WebKit does on its own).
    private func installBootScript() {
        contentController.removeAllUserScripts()
        contentController.addUserScript(WKUserScript(source: bootSource(), injectionTime: .atDocumentStart,
                                                     forMainFrameOnly: true))
    }

    private func evaluate(_ js: String) {
        guard loaded, !closed else { return }
        webView.evaluateJavaScript(js, completionHandler: nil)
    }

    // MARK: Window
    /// Ordered in (first time, or back from parking); the occlusion state is read again right away.
    func show() {
        parkedNow = false
        window.orderFrontRegardless()
        sensor?.orderFrontRegardless()                   // its own level, above the wallpaper
        refreshOcclusion()
    }

    /// R12: some of the display's usable area shows (the sensor is `.visible`): a "full-screen" verdict of the window
    /// list is not acted on. False without a sensor (`aq.coverSensor` NO) or while parked.
    var usableAreaVisible: Bool { sensor?.occlusionState.contains(.visible) ?? false }

    private static func sensorFrame(_ screen: NSScreen) -> NSRect {
        screen.visibleFrame.insetBy(dx: sensorInset, dy: sensorInset)
    }

    /// False while other windows cover this whole display: WebKit then hides the page and draws no frames.
    var isDesktopVisible: Bool { window.occlusionState.contains(.visible) }

    /// The display disappeared (maybe only for a moment: standby, re-enumeration): hide and pause,
    /// keep the page. AppDelegate re-shows it if the display returns, or closes it after 15 min.
    func park() {
        parkedNow = true                                 // ordered out = occluded: that is not "covered"
        refreshOcclusion()
        setPower("paused", constrained: constrained, reason: "parked")
        window.orderOut(nil)
        sensor?.orderOut(nil)
        Log.info("display \(displayID) gone — window parked (hidden, paused)")
    }

    /// Releases the page: WebKit logs `close:` and the WebContent process exits.
    func close() {
        guard !closed else { return }
        endUnresponsive("closed")                        // before `closed`: the episode must not stay open
        closed = true
        NSObject.cancelPreviousPerformRequests(withTarget: self)
        NotificationCenter.default.removeObserver(self, name: NSWindow.didChangeOcclusionStateNotification,
                                                  object: window)
        if let s = sensor {
            NotificationCenter.default.removeObserver(self, name: NSWindow.didChangeOcclusionStateNotification, object: s)
            s.orderOut(nil)
            s.close()
        }
        onOcclusionChange = nil
        webView.navigationDelegate = nil
        webView.stopLoading()
        window.orderOut(nil)
        window.contentView = nil                         // the WKWebView goes with this object
        window.close()                                   // out of NSApp.windows (isReleasedWhenClosed = false)
        Log.info("display \(displayID) window closed")
    }

    /// The display still exists but its geometry changed: move/resize only, no reload.
    func update(screen: NSScreen) {
        screenInfo = ScreenInfo(screen)
        if window.frame != screen.frame {
            Log.info("display \(displayID) resized to \(screenInfo.w)x\(screenInfo.h) (no reload)")
            window.setFrame(screen.frame, display: true)
        }
        if let s = sensor {
            let f = WallpaperWindow.sensorFrame(screen)
            if s.frame != f { s.setFrame(f, display: false) }
        }
    }

    // MARK: Occlusion (R12)
    /// NSWindow.didChangeOcclusionStateNotification for this window. Logged: whether it fires at all for a window at
    /// desktop level is one of the things the owner's test checks (`log show`, `occlusionEvents` in the diagnostics).
    @objc private func occlusionChanged(_ note: Notification) {
        guard !closed else { return }
        occlusionEvents += 1
        let visible = isDesktopVisible
        Log.info("display \(displayID) occlusion: \(visible ? "visible" : "not visible")" + (parkedNow ? " (parked)" : ""))
        let visibleAgain = visible && occludedSince != nil
        refreshOcclusion()
        onOcclusionChange?(self, visibleAgain)
    }

    /// Re-reads occlusionState: on its notification, on show/park and on every coverage poll (a missed "visible
    /// again" notification must not keep the page paused). Not visible → covered after coverGrace; visible → at once.
    /// The caller re-decides the page's mode (AppDelegate.applyPower).
    func refreshOcclusion() {
        guard !closed else { return }
        if parkedNow || isDesktopVisible {
            NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(coverGraceEnded), object: nil)
            occludedSince = nil
            isCovered = false
        } else if occludedSince == nil {
            occludedSince = Date()
            perform(#selector(coverGraceEnded), with: nil, afterDelay: WallpaperWindow.coverGrace, inModes: [.common])
        }
    }

    /// The sensor's occlusion changed: AppDelegate re-decides this page at once (a "full-screen" verdict applies again
    /// or not any more). No grace: the window list's two hits ≥ 1 s apart already gate every new pause.
    @objc private func sensorChanged(_ note: Notification) {
        guard !closed else { return }
        sensorEvents += 1
        let visible = usableAreaVisible
        if visible != sensorVisible {
            sensorVisible = visible
            Log.info("display \(displayID) usable area: \(visible ? "visible" : "covered") (sensor)" + (parkedNow ? " (parked)" : ""))
        }
        onOcclusionChange?(self, false)
    }

    @objc private func coverGraceEnded() {
        guard !closed, !parkedNow, !isCovered else { return }
        if isDesktopVisible {                            // visible again, its notification not here yet: no pause
            occludedSince = nil
            return
        }
        isCovered = true
        onOcclusionChange?(self, false)
    }

    // MARK: Page controls
    /// `mode`: "high" (60 fps) | "low" (30 fps: battery, Low Power Mode, heat) | "paused". `reason` — why "paused"
    /// (R12): sleep | layersTest | covered | fullscreen | parked; the page is told (`window.__AQ_PAUSE`, HUD line).
    /// `constrained`: Low Power Mode or heat → 1.8 MP budget.
    /// Sent only on a real change (every IOPS event, e.g. a battery-percent tick, used to reset the
    /// engine's frame-rate governor); re-sent after every (re)load in didFinish.
    func setPower(_ mode: String, constrained c: Bool, reason: String? = nil) {
        let why = mode == "paused" ? (reason ?? "paused") : nil
        let reasonChanged = why != pauseReason
        if reasonChanged { notePause(why) }
        let modeChanged = mode != power, budgetChanged = c != constrained
        if modeChanged || budgetChanged {
            let wasPaused = power == "paused"
            power = mode
            if (mode == "paused") != wasPaused { armHeartbeat() }   // no 10-s wakeups (and no pings) while paused, any reason
            constrained = c
            installBootScript()
            if modeChanged { sendPower() }
            if budgetChanged { applyBudget() }
        }
        if reasonChanged { sendPauseNote() }             // after the power call: the HUD is already frozen then
    }

    private func sendPower() {
        evaluate("window.aquariumSetPower && window.aquariumSetPower(\(PageScript.literal(power)))")
    }

    /// A pause starts, ends or changes its reason: log and this run's counters (setPower then sends the page's note).
    private func notePause(_ why: String?) {
        let now = Date()
        if let old = pauseReason, let since = pausedSince {
            let lasted = Int(now.timeIntervalSince(since).rounded())
            pausedTotals[old, default: 0] += now.timeIntervalSince(since)
            if let why = why {
                Log.info("display \(displayID) pause reason \(old) → \(why) after \(lasted) s")
            } else {
                Log.info("display \(displayID) resumed after \(lasted) s paused (\(old))")
            }
        } else if let why = why {
            Log.info("display \(displayID) paused: \(why)")
        }
        if let why = why {
            pauseCounts[why, default: 0] += 1
            pausedSince = now
        } else {
            pausedSince = nil
        }
        pauseReason = why
    }

    private static let pauseLabels: [String: String] = [
        "covered": "рабочий стол закрыт окнами", "fullscreen": "окно во весь экран", "sleep": "дисплей спит",
        "layersTest": "открыт «Тест слоёв»", "parked": "экран отключён",
    ]
    private static let clock: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        return f
    }()

    /// R12: `window.__AQ_PAUSE` = {reason, since} | null, and the HUD's first line "⏸ paused: covered — …": the engine
    /// stops updating the HUD while paused, so its last text stays below the line; its first update after the resume
    /// replaces it all (the line is also removed here). Nothing happens without a HUD element.
    private func sendPauseNote() {
        var note: Any = NSNull()
        var line: Any = NSNull()
        if let why = pauseReason {
            let since = pausedSince ?? Date()
            note = ["reason": why, "since": FBDate.string(since)]
            line = "⏸ paused: \(why) — \(WallpaperWindow.pauseLabels[why] ?? why), с \(WallpaperWindow.clock.string(from: since))"
        }
        evaluate("""
        (() => { try {
          window.__AQ_PAUSE = \(PageScript.literal(note));
          const el = document.getElementById("aqhud"), line = \(PageScript.literal(line));
          if (!el) return;
          const rest = el.textContent.replace(/^⏸[^\\n]*\\n/, "");
          el.textContent = line ? line + "\\n" + rest : rest;
        } catch (e) {} })()
        """)
    }

    /// The display became (or stopped being) the one with the menu bar.
    func setRole(isMain main: Bool) {
        guard main != isMain else { return }
        isMain = main
        installBootScript()
        applyBudget()
    }

    /// Secondary display: {mp: 2, fps: 30}. Main: `{mp: null, fps: null}` = back to the engine's own budget.
    private func applyBudget() {
        let arg = budget.map { PageScript.literal($0) } ?? "{mp: null, fps: null}"
        evaluate("window.aquariumSetBudget && window.aquariumSetBudget(\(arg))")
    }

    /// «Показать FPS»: the DOM HUD (not drawn on the canvas). Also in `__AQ_BOOT.hud` for later loads.
    func setHUD(_ on: Bool) {
        installBootScript()
        evaluate("window.aquariumSetDebug && window.aquariumSetDebug(\(PageScript.literal(on)))")
        if on, pauseReason != nil { sendPauseNote() }    // a paused page does not fill its new HUD: say why
    }

    /// «Тема аквариума» (AppSettings.theme, already saved): the page crossfades (≈3 s) to it now; later loads
    /// start in it (`__AQ_BOOT.theme`).
    func setTheme(_ theme: AquariumTheme) {
        installBootScript()
        sendTheme(theme)
    }

    private func sendTheme(_ theme: AquariumTheme) {
        evaluate("window.aquariumSetTheme && window.aquariumSetTheme(\(PageScript.literal(theme.rawValue)))")
    }

    // MARK: Diagnostics
    func hostInfo() -> [String: Any] {
        var screen = screenInfo.dict
        screen["id"] = Int(displayID)
        var d: [String: Any] = [
            "display": Int(displayID), "main": isMain, "state": state.rawValue, "power": power,
            "constrained": constrained, "budget": budget ?? NSNull(),
            "visible": window.isVisible, "screen": screen, "loadReason": loadReason,
            "vlayer": loadVlayer,                        // what this page booted with; in use: snapshot.vlayer
            "loadsThisRun": loadCount, "terminationsThisRun": terminationCount,
            "loadFailuresThisRun": loadFailureCount, "slowRetry": gaveUp,
            "unresponsiveThisRun": unresponsiveCount,
            // R12: why paused (null: running), occlusion as AppKit reports it, pauses this run by reason.
            "pauseReason": pauseReason ?? NSNull(), "occlusionVisible": isDesktopVisible, "covered": isCovered,
            "occlusionEvents": occlusionEvents, "pausesThisRun": pauseCounts,
            // R12 sensor (null: off, aq.coverSensor NO): does any of the usable area show; its notifications this run.
            "usableAreaVisible": sensor == nil ? NSNull() as Any : usableAreaVisible, "sensorEvents": sensorEvents,
        ]
        var totals = pausedTotals
        if let why = pauseReason, let since = pausedSince {
            d["pausedForSec"] = Int(Date().timeIntervalSince(since))
            totals[why, default: 0] += Date().timeIntervalSince(since)
        }
        d["pausedSecThisRun"] = totals.mapValues { Int($0.rounded()) }
        if let t = loadStartedAt { d["loadedAgoSec"] = Int(Date().timeIntervalSince(t)) }
        // Copied during a freeze: the page's snapshot times out, this says for how long it has been hung.
        if let u = unresponsiveSince { d["unresponsiveForSec"] = Int(Date().timeIntervalSince(u)) }
        return d
    }

    private static let snapshotScript = """
    (() => { try {
      if (typeof window.aquariumPerfSnapshot !== 'function') return JSON.stringify({ error: 'aquariumPerfSnapshot missing' });
      const s = window.aquariumPerfSnapshot();
      return JSON.stringify(s === undefined ? null : s);
    } catch (e) { return JSON.stringify({ error: String(e) }); } })()
    """

    /// `aquariumPerfSnapshot()` as a JSON object, or {error}. Completion on the main thread, exactly once.
    func perfSnapshot(timeout: TimeInterval = 2, completion: @escaping (Any) -> Void) {
        guard loaded, !closed else { completion(["error": "page not loaded (\(state.rawValue))"]); return }
        var finished = false
        let finish: (Any) -> Void = { value in
            if finished { return }
            finished = true
            completion(value)
        }
        webView.evaluateJavaScript(WallpaperWindow.snapshotScript) { result, error in
            if let s = result as? String, let data = s.data(using: .utf8),
               let obj = try? JSONSerialization.jsonObject(with: data, options: [.fragmentsAllowed]) {
                finish(obj)
            } else {
                finish(["error": error?.localizedDescription ?? "no result"])
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + timeout) { finish(["error": "timeout"]) }
    }

    // The function body always returns a string: callAsyncJavaScript's Result API traps on `undefined`.
    private static let probeBody = """
    if (typeof window.aquariumPerfProbe !== 'function') return JSON.stringify({ error: 'aquariumPerfProbe missing' });
    const r = await window.aquariumPerfProbe();
    return JSON.stringify(r === undefined ? null : r);
    """

    /// `aquariumPerfProbe()` (≈45 s): (result, nil) or (nil, error text). Main thread, exactly once.
    /// The timeout must clearly exceed the page's own abort timer (index.html probeStart: 11 configs ×
    /// (1 + 3 s) × 3 + 15 s = 147 s), so the page always answers first with its partial results: WebKit
    /// throttles timers of a hidden page and App Nap can delay them. Keep it ≥ 11·4·3 + 15 + 60 s.
    func perfProbe(timeout: TimeInterval = 240, completion: @escaping (Any?, String?) -> Void) {
        guard loaded, !closed else { completion(nil, "страница не загружена (\(state.rawValue))"); return }
        var finished = false
        let finish: (Any?, String?) -> Void = { value, error in
            if finished { return }
            finished = true
            completion(value, error)
        }
        webView.callAsyncJavaScript(WallpaperWindow.probeBody, arguments: [:], in: nil, in: .page) { result in
            switch result {
            case .success(let value):
                if let s = value as? String, let data = s.data(using: .utf8),
                   let obj = try? JSONSerialization.jsonObject(with: data, options: [.fragmentsAllowed]) {
                    finish(obj, nil)
                } else {
                    finish(nil, "неожиданный ответ страницы")
                }
            case .failure(let error):
                finish(nil, error.localizedDescription)
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + timeout) { finish(nil, "нет ответа за \(Int(timeout)) с") }
    }

    // MARK: WKNavigationDelegate
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard !closed else { return }
        state = .ready
        let ms = loadStartedAt.map { Int(Date().timeIntervalSince($0) * 1000) } ?? -1
        Log.info("display \(displayID) loaded in \(ms) ms (\(loadReason))")
        // Re-assert what may have changed while the page was loading (the boot script had the old values).
        sendPower()
        if budgetLiteral != loadBudget { applyBudget() }
        evaluate("window.aquariumSetDebug && window.aquariumSetDebug(\(PageScript.literal(AppSettings.hud)))")
        sendTheme(AppSettings.theme)                     // as at boot: a no-op; chosen while loading: crossfade
        if pauseReason != nil { sendPauseNote() }        // reloaded while paused (e.g. a crash behind a full-screen app)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        navigationFailed(error)
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        navigationFailed(error)
    }

    private func navigationFailed(_ error: Error) {
        let e = error as NSError
        // -999: replaced by our own newer load or stopLoading(); 102: interrupted by a policy change.
        if (e.domain == NSURLErrorDomain && e.code == NSURLErrorCancelled)
            || (e.domain == "WebKitErrorDomain" && e.code == 102) { return }
        // Already recovering (e.g. the WebContent crash that also failed this navigation): one incident.
        guard !closed, state != .waiting else { return }
        loadFailureCount += 1
        Log.error("load failed on display \(displayID): \(e.domain) \(e.code) \(e.localizedDescription)")
        scheduleRecovery(reason: "retry")
    }

    /// Public API. Implementing any termination method also stops WebKit's own silent reload
    /// (one per 30 s, black after a second kill): recovery below replaces it.
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        contentProcessTerminated(code: nil)
    }

    /// Private WebKit delegate method (WKNavigationDelegatePrivate.h). When it exists WebKit calls it
    /// INSTEAD of the public one and passes `_WKProcessTerminationReason` (NSInteger): 0 memory,
    /// 1 CPU, 2 client, 3 crash, 4 GPU-process crash limit. Matched by selector only (nothing private
    /// is linked); if a future WebKit drops it, the public method above takes over. `private` still
    /// registers the selector with the Objective-C runtime (respondsToSelector: sees it).
    @objc(_webView:webContentProcessDidTerminateWithReason:)
    private func privateWebContentProcessDidTerminate(_ webView: WKWebView, reason: Int) {
        contentProcessTerminated(code: reason)
    }

    private func contentProcessTerminated(code: Int?) {
        guard !closed else { return }
        // Killed before the ping was due but well after it was sent: hung already — on record (unresponsiveSec)
        if let sent = pingSentAt, pingWanted, WallpaperWindow.uptime - pingSentUptime >= WallpaperWindow.pingLateAtDeath {
            beginUnresponsive(since: sent, source: "heartbeat")
        }
        disownPing()                                     // its callback fails with an error: never "responsive"
        let since = loadStartedAt.map { Date().timeIntervalSince($0) }
        let frozeFor = endUnresponsive("terminated")     // a hang that ended in a kill: the white-screen case
        terminationCount += 1
        LifecycleStats.recordTermination(display: displayID, code: code, sinceLoad: since, unresponsiveFor: frozeFor)
        Log.error("WebContent terminated on display \(displayID): \(LifecycleStats.reasonName(code)), " +
                  "\(Int(since ?? -1)) s after load" +
                  (frozeFor.map { ", unresponsive for \(Int($0.rounded())) s before" } ?? "") +
                  " (total \(LifecycleStats.terminations))")
        if state != .waiting { scheduleRecovery(reason: "crashReload") }   // else a reload is already scheduled
    }

    /// Private WebKit delegate methods (WKNavigationDelegatePrivate.h: `_webViewWebProcessDidBecomeUnresponsive:`,
    /// `_webViewWebProcessDidBecomeResponsive:`; NavigationState.mm checks respondsToSelector: when the
    /// delegate is set). WebKit calls them when the WebContent process has not answered a message the UI
    /// process waits on for 3 s (ResponsivenessTimer, started only by loads, reloads, back/forward and input
    /// events) and when it answers again — a page stuck in a long JavaScript task, the suspected start of
    /// "freezes, then a white screen". A wallpaper page gets no input, so in steady state WebKit never asks;
    /// the heartbeat below covers that. Matched by selector only, like the termination method above.
    @objc(_webViewWebProcessDidBecomeUnresponsive:)
    private func privateWebProcessDidBecomeUnresponsive(_ webView: WKWebView) {
        // unresponsive → responsive → unresponsive within one turn: the same open episode
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(markResponsive), object: nil)
        beginUnresponsive(since: Date(), source: "webkit")
    }

    /// Decided one run-loop turn later: WebKit can report "responsive" in the same call stack just before the
    /// termination (WebPageProxy::dispatchProcessDidTerminate with site isolation; the background
    /// responsiveness timer's processTerminated without RunningBoard). A kill then closes the episode as
    /// `terminated` first, and the deferred call finds nothing open.
    @objc(_webViewWebProcessDidBecomeResponsive:)
    private func privateWebProcessDidBecomeResponsive(_ webView: WKWebView) {
        guard !closed, unresponsiveSince != nil else { return }
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(markResponsive), object: nil)
        perform(#selector(markResponsive), with: nil, afterDelay: 0, inModes: [.common])
    }

    @objc private func markResponsive() {
        guard !closed else { return }
        endUnresponsive("responsive")
    }

    // MARK: Heartbeat
    private static var uptime: TimeInterval { ProcessInfo.processInfo.systemUptime }

    /// Pinged only while a reply is due promptly: loaded, not paused (display asleep, parked, layers test, desktop
    /// covered for > 2 s, a full-screen window — R12), desktop not covered even within the 2-s grace (WebKit hides
    /// the page at once and may throttle it — a slow reply there is no hang). So a paused page never opens an
    /// "unresponsive" episode, and a resumed one is first pinged 10 s after the resume.
    private var pingWanted: Bool { loaded && power != "paused" && isDesktopVisible }

    /// The 10-s tick runs only while the page is not paused: a paused window (display asleep all night, parked
    /// up to 15 min, behind a full-screen app for hours) does not wake the app 6 times a minute (perform timers have
    /// no tolerance, not coalesced).
    /// .common: keeps running while a menu or an alert is open; close() cancels it. A ping already in flight
    /// at a pause is dropped by pingOverdue (pingWanted false) without a verdict.
    private func armHeartbeat() {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(heartbeat), object: nil)
        guard !closed, power != "paused" else { return }
        perform(#selector(heartbeat), with: nil, afterDelay: WallpaperWindow.heartbeatInterval, inModes: [.common])
    }

    /// Every 10 s: a page that `pingWanted` gets `0` to evaluate; one ping at a time (a hung page is not sent
    /// more). Only a successful reply counts as responsive; pingOverdue opens the episode. The completion
    /// captures like perfSnapshot's (a method without concurrency annotations): no Sendable diagnostics.
    @objc private func heartbeat() {
        guard !closed, power != "paused" else { return }   // setPower re-arms it on resume
        perform(#selector(heartbeat), with: nil, afterDelay: WallpaperWindow.heartbeatInterval, inModes: [.common])
        guard pingSentAt == nil, pingWanted else { return }
        pingSeq += 1
        let seq = pingSeq
        pingSentAt = Date()
        pingSentUptime = WallpaperWindow.uptime
        schedulePingCheck(after: WallpaperWindow.pingTimeout)
        webView.evaluateJavaScript("0") { [weak self] _, error in self?.pingReplied(seq: seq, error: error) }
    }

    private func pingReplied(seq: Int, error: Error?) {
        guard !closed, seq == pingSeq else { return }    // disowned: its document is gone
        // Killed (the code older WebKit gives it): contentProcessTerminated decides, whichever callback comes first.
        if let e = error as? WKError, e.code == .webContentProcessTerminated { return }
        if error != nil {
            // A dying WebContent fails pending evaluateJavaScript calls inside the termination, just BEFORE
            // webContentProcessDidTerminate (WebKit main: WebProcessProxy::processDidTerminateOrFailedToLaunch →
            // shutDown → Connection::invalidate → cancelAsyncReplyHandlers), and with WKError 5
            // (javaScriptResultTypeIsUnsupported), not .webContentProcessTerminated. Keep the ping for
            // contentProcessTerminated; if nothing disowns it this turn, drop it without a verdict.
            perform(#selector(pingFailed(_:)), with: NSNumber(value: seq), afterDelay: 0, inModes: [.common])
            return
        }
        pingSentAt = nil
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(pingOverdue), object: nil)
        endUnresponsive("responsive")
    }

    /// A failed ping that no termination or new load disowned within a turn: no verdict; the next tick pings again.
    @objc private func pingFailed(_ seq: NSNumber) {
        guard !closed, seq.intValue == pingSeq else { return }   // contentProcessTerminated / load() disowned it
        pingSentAt = nil
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(pingOverdue), object: nil)
    }

    private func schedulePingCheck(after delay: TimeInterval) {
        pingCheckDue = WallpaperWindow.uptime + delay
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(pingOverdue), object: nil)
        perform(#selector(pingOverdue), with: nil, afterDelay: delay, inModes: [.common])
    }

    /// The ping has gone unanswered for pingTimeout: the page is hung since it was sent.
    @objc private func pingOverdue() {
        guard !closed, let sent = pingSentAt else { return }
        // Hidden or paused meanwhile: no verdict. The reply (same seq) still ends an episode that is open.
        guard pingWanted else { pingSentAt = nil; return }
        // This check itself ran late (App Nap, a blocked main thread): the reply may be queued right behind it.
        if WallpaperWindow.uptime - pingCheckDue > 1 { schedulePingCheck(after: 1); return }
        beginUnresponsive(since: sent, source: "heartbeat")
    }

    /// The ping's document is gone (a new load, a termination): its reply, or error, is ignored.
    private func disownPing() {
        pingSentAt = nil
        pingSeq += 1
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(pingOverdue), object: nil)
    }

    /// Opens an unresponsive episode (`source`: webkit | heartbeat) unless one is open: counted and logged at once.
    private func beginUnresponsive(since: Date, source: String) {
        guard !closed, unresponsiveSince == nil else { return }
        let sinceLoad = loadStartedAt.map { since.timeIntervalSince($0) }
        unresponsiveSince = since
        unresponsiveCount += 1
        LifecycleStats.recordUnresponsive(display: displayID, at: since, sinceLoad: sinceLoad, source: source)
        Log.error("WebContent unresponsive on display \(displayID) (\(source)): \(Int(sinceLoad ?? -1)) s after load, " +
                  "state \(state.rawValue), power \(power) (total \(LifecycleStats.unresponsiveEpisodes))")
    }

    /// Ends an open unresponsive episode (`how`: responsive | terminated | closed) in the log and in
    /// LifecycleStats; returns how long it lasted, nil if none was open.
    @discardableResult
    private func endUnresponsive(_ how: String) -> TimeInterval? {
        guard let start = unresponsiveSince else { return nil }
        unresponsiveSince = nil
        let duration = Date().timeIntervalSince(start)
        LifecycleStats.endUnresponsive(display: displayID, duration: duration, end: how)
        let text = "display \(displayID): WebContent was unresponsive for \(String(format: "%.1f", duration)) s, " +
                   "ended: \(how)"
        if how == "responsive" { Log.info(text) } else { Log.error(text) }
        return duration
    }

    // MARK: Recovery
    private func scheduleRecovery(reason: String) {
        state = .waiting
        let now = Date()
        // A page that ran ≥ 5 min proved itself: back to the quick backoff.
        if gaveUp, let t = loadStartedAt, now.timeIntervalSince(t) >= WallpaperWindow.backoffWindow { gaveUp = false }
        failures = failures.filter { now.timeIntervalSince($0) < WallpaperWindow.backoffWindow }
        failures.append(now)
        if !gaveUp && failures.count > WallpaperWindow.backoff.count {
            gaveUp = true
            Log.error("display \(displayID): \(failures.count) failures in 5 min — next try in 10 min, " +
                      "on display wake or on a screen change")
        }
        let delay = gaveUp ? WallpaperWindow.slowRetry : WallpaperWindow.backoff[failures.count - 1]
        nextReason = gaveUp ? "retry" : reason
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(recover), object: nil)
        // .common: keeps running while a menu or an alert is open.
        perform(#selector(recover), with: nil, afterDelay: delay, inModes: [.common])
    }

    @objc private func recover() {
        guard !closed, state == .waiting else { return }
        Log.info("reloading display \(displayID) (\(nextReason))")
        load(reason: nextReason)
    }

    /// After the quick backoff ran out: try now (display woke, screens changed) instead of
    /// waiting for the 10-min timer. A failure goes straight back to the slow retry.
    func retryIfGaveUp() {
        guard !closed, gaveUp, state == .waiting else { return }
        Log.info("display \(displayID): early retry (wake / screen change)")
        load(reason: "retry")
    }
}

/// Swift value → JavaScript source literal via JSON: strings quoted and escaped, numbers, true/false, null,
/// arrays, objects (keys sorted: the same value always gives the same text, see didFinish).
/// U+2028/U+2029 are escaped as well (raw, they end a line in pre-ES2019 JavaScript).
/// Invalid input (NaN, a non-JSON type) gives `null` — checked first: JSONSerialization raises an
/// Objective-C exception on it, which `try?` does not catch.
enum PageScript {
    static func literal(_ value: Any) -> String {
        let wrapped: [Any] = [value]                     // fragments (a bare string/number) are not valid roots
        guard JSONSerialization.isValidJSONObject(wrapped),
              let data = try? JSONSerialization.data(withJSONObject: wrapped, options: [.sortedKeys]),
              var s = String(data: data, encoding: .utf8), s.hasPrefix("["), s.hasSuffix("]") else { return "null" }
        s.removeFirst()
        s.removeLast()
        return s.replacingOccurrences(of: "\u{2028}", with: "\\u2028")
                .replacingOccurrences(of: "\u{2029}", with: "\\u2029")
    }
}
