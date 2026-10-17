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
    private static let backoff: [TimeInterval] = [1, 5, 15]     // quick reloads, at most 3 per 5 min…
    private static let backoffWindow: TimeInterval = 300
    private static let slowRetry: TimeInterval = 600            // …then every 10 min (and on wake / screen change)

    let displayID: CGDirectDisplayID
    private let window: NSWindow
    private let webView: WKWebView
    private let contentController: WKUserContentController
    private(set) var power: String
    private(set) var isMain: Bool
    private(set) var state: State = .loading
    private var screenInfo: ScreenInfo
    private var closed = false
    private var loadReason: String
    private var loadStartedAt: Date?
    private var loadIsMain = true                    // role in the boot script of the current load
    private var nextReason = "crashReload"
    private var failures: [Date] = []                // terminations + failed loads, last 5 min
    private var gaveUp = false                       // quick backoff exhausted → slow retry
    // This run only (the persistent totals are in LifecycleStats).
    private var loadCount = 0
    private var terminationCount = 0
    private var loadFailureCount = 0

    private var loaded: Bool { state == .ready }

    /// `reason` — why this page is being created: "launch" | "displayAdded".
    init(screen: NSScreen, displayID: CGDirectDisplayID, isMain: Bool, power: String, reason: String) {
        self.displayID = displayID
        self.isMain = isMain
        self.power = power
        self.loadReason = reason
        screenInfo = ScreenInfo(screen)

        // Boot state (wallpaper flag, power mode, HUD, budget, screen, crash count) reaches the page at
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

        super.init()
        webView.navigationDelegate = self
        load(reason: reason)
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
        state = .loading
        loadReason = reason
        loadStartedAt = Date()
        loadIsMain = isMain
        loadCount += 1
        installBootScript()
        LifecycleStats.recordLoad(display: displayID, reason: reason)
        Log.info("load display \(displayID): reason=\(reason) main=\(isMain) power=\(power) " +
                 "\(screenInfo.w)x\(screenInfo.h)@\(screenInfo.scale)x \(screenInfo.maxFps)Hz")
        webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }

    /// `window.__AQ_BOOT` (contract with aquarium/index.html, P1.1):
    /// {power, hud, budget: MP|null, screen: {id, w, h (points), scale, maxFps, main}, crashes,
    ///  loadReason: launch|displayAdded|crashReload|retry, appVersion}. `__AQ_POWER` stays for older pages.
    private func bootSource() -> String {
        var screen = screenInfo.dict
        screen["id"] = Int(displayID)
        screen["main"] = isMain
        let boot: [String: Any] = [
            "power": power,
            "hud": AppSettings.hud,
            "budget": isMain ? NSNull() : WallpaperWindow.secondaryBudgetMP,
            "screen": screen,
            "crashes": LifecycleStats.terminations,
            "loadReason": loadReason,
            "appVersion": AppSettings.appVersion,
        ]
        var json = "null"
        if let data = try? JSONSerialization.data(withJSONObject: boot), let s = String(data: data, encoding: .utf8) {
            json = s
        }
        return "window.__WALLPAPER = true; window.__AQ_POWER = '\(power)'; window.__AQ_BOOT = \(json);"
    }

    /// Takes effect on the next navigation (ours, or a reload WebKit does on its own).
    private func installBootScript() {
        contentController.removeAllUserScripts()
        contentController.addUserScript(WKUserScript(source: bootSource(), injectionTime: .atDocumentStart,
                                                     forMainFrameOnly: true))
    }

    private func evaluate(_ js: String) {
        guard loaded else { return }
        webView.evaluateJavaScript(js, completionHandler: nil)
    }

    // MARK: Window
    func show() { window.orderFrontRegardless() }

    /// The display disappeared (maybe only for a moment: standby, re-enumeration): hide and pause,
    /// keep the page. AppDelegate re-shows it if the display returns, or closes it after 15 min.
    func park() {
        setPower("paused")
        window.orderOut(nil)
        Log.info("display \(displayID) gone — window parked (hidden, paused)")
    }

    /// Releases the page: WebKit logs `close:` and the WebContent process exits.
    func close() {
        guard !closed else { return }
        closed = true
        NSObject.cancelPreviousPerformRequests(withTarget: self)
        webView.navigationDelegate = nil
        webView.stopLoading()
        window.orderOut(nil)
        window.contentView = nil
        Log.info("display \(displayID) window closed")
    }

    /// The display still exists but its geometry changed: move/resize only, no reload.
    func update(screen: NSScreen) {
        screenInfo = ScreenInfo(screen)
        if window.frame != screen.frame {
            Log.info("display \(displayID) resized to \(screenInfo.w)x\(screenInfo.h) (no reload)")
            window.setFrame(screen.frame, display: true)
        }
    }

    // MARK: Page controls
    /// "high" (60 fps) | "low" (30 fps: battery, Low Power Mode, heat) | "paused" (display asleep, parked).
    /// Sent only on a real change (every IOPS event, e.g. a battery-percent tick, used to reset the
    /// engine's frame-rate governor); re-sent after every (re)load in didFinish.
    func setPower(_ mode: String) {
        guard mode != power else { return }
        power = mode
        installBootScript()
        evaluate("window.aquariumSetPower && window.aquariumSetPower('\(mode)')")
    }

    /// The display became (or stopped being) the one with the menu bar.
    func setRole(isMain main: Bool) {
        guard main != isMain else { return }
        isMain = main
        installBootScript()
        applyBudget()
    }

    /// Secondary display: 2 MP / 30 fps. Main: `{mp: null, fps: null}` = back to the engine's own budget.
    private func applyBudget() {
        let arg = isMain ? "{mp: null, fps: null}"
                         : "{mp: \(WallpaperWindow.secondaryBudgetMP), fps: \(WallpaperWindow.secondaryFps)}"
        evaluate("window.aquariumSetBudget && window.aquariumSetBudget(\(arg))")
    }

    /// «Показать FPS»: the DOM HUD (not drawn on the canvas). Also in `__AQ_BOOT.hud` for later loads.
    func setHUD(_ on: Bool) {
        installBootScript()
        evaluate("window.aquariumSetDebug && window.aquariumSetDebug(\(on))")
    }

    // MARK: Diagnostics
    func hostInfo() -> [String: Any] {
        var screen = screenInfo.dict
        screen["id"] = Int(displayID)
        var d: [String: Any] = [
            "display": Int(displayID), "main": isMain, "state": state.rawValue, "power": power,
            "visible": window.isVisible, "screen": screen, "loadReason": loadReason,
            "loadsThisRun": loadCount, "terminationsThisRun": terminationCount,
            "loadFailuresThisRun": loadFailureCount, "slowRetry": gaveUp,
        ]
        if let t = loadStartedAt { d["loadedAgoSec"] = Int(Date().timeIntervalSince(t)) }
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
        guard loaded else { completion(["error": "page not loaded (\(state.rawValue))"]); return }
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
    func perfProbe(timeout: TimeInterval = 150, completion: @escaping (Any?, String?) -> Void) {
        guard loaded else { completion(nil, "страница не загружена (\(state.rawValue))"); return }
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
        evaluate("window.aquariumSetPower && window.aquariumSetPower('\(power)')")
        if !isMain || loadIsMain != isMain { applyBudget() }
        evaluate("window.aquariumSetDebug && window.aquariumSetDebug(\(AppSettings.hud))")
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
        let since = loadStartedAt.map { Date().timeIntervalSince($0) }
        terminationCount += 1
        LifecycleStats.recordTermination(display: displayID, code: code, sinceLoad: since)
        Log.error("WebContent terminated on display \(displayID): \(LifecycleStats.reasonName(code)), " +
                  "\(Int(since ?? -1)) s after load (total \(LifecycleStats.terminations))")
        if state != .waiting { scheduleRecovery(reason: "crashReload") }   // else a reload is already scheduled
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
