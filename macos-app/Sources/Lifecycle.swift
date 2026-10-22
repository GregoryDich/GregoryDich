import Cocoa
import os

// Shared plumbing for AppDelegate and WallpaperWindow: the unified log, persisted settings,
// page-load, WebContent-termination and unresponsive-page counters (UserDefaults) and two small UI helpers.
// What happened and why is readable after the fact, without a debugger:
//   log show --last 3h --style compact --predicate 'subsystem == "com.gregorydich.aquariumwallpaper"'
//   defaults read com.gregorydich.aquariumwallpaper          (aq.wc.*, aq.pageLoads*, aq.unresponsive.*)

// MARK: - Log
enum Log {
    private static let lifecycle = Logger(subsystem: "com.gregorydich.aquariumwallpaper", category: "lifecycle")

    /// `notice`, not `info`: notices are persisted, so `log show` finds them hours later.
    /// Messages carry no personal data (display IDs, reasons, timings), hence public.
    static func info(_ message: String) { lifecycle.notice("\(message, privacy: .public)") }
    static func error(_ message: String) { lifecycle.error("\(message, privacy: .public)") }
}

// MARK: - Settings (UserDefaults, domain com.gregorydich.aquariumwallpaper)
enum AppSettings {
    static let hudKey = "aq.hud"                      // «Показать FPS»
    static let onlyMainKey = "aq.onlyMainScreen"      // «Только на главном экране»
    static let themeKey = "aq.theme"                  // «Тема аквариума»: auto | day | night
    /// ⌥ «Задник слоями (тест)» (ROADMAP P1.9): the engine's layered backdrop, chosen at boot (`__AQ_BOOT.vlayer`);
    /// off by default. Toggling reloads every wallpaper page.
    static let vlayerKey = "aq.vlayer"
    /// Safari ▸ Develop ▸ <Mac> ▸ wallpaper page (macOS 13.3+). Read when a page is created:
    ///   defaults write com.gregorydich.aquariumwallpaper inspectable -bool YES   (then restart the app)
    static let inspectableKey = "inspectable"
    /// R12, no menu item: pause a display behind a full-screen or maximised window (window list, CoverageMonitor).
    /// On unless set to NO — the way out if that check ever misjudges a Mac (the pause on occlusion stays):
    ///   defaults write com.gregorydich.aquariumwallpaper aq.fullscreenCheck -bool NO   (then restart the app)
    static let fullscreenCheckKey = "aq.fullscreenCheck"

    static var hud: Bool {
        get { UserDefaults.standard.bool(forKey: hudKey) }
        set { UserDefaults.standard.set(newValue, forKey: hudKey) }
    }
    static var onlyMainScreen: Bool {
        get { UserDefaults.standard.bool(forKey: onlyMainKey) }
        set { UserDefaults.standard.set(newValue, forKey: onlyMainKey) }
    }
    /// «Тема аквариума»; a missing or unknown value reads as `.auto` (follow the macOS appearance).
    static var theme: AquariumTheme {
        get { AquariumTheme(rawValue: UserDefaults.standard.string(forKey: themeKey) ?? "") ?? .auto }
        set { UserDefaults.standard.set(newValue.rawValue, forKey: themeKey) }
    }
    static var vlayer: Bool {
        get { UserDefaults.standard.bool(forKey: vlayerKey) }
        set { UserDefaults.standard.set(newValue, forKey: vlayerKey) }
    }
    static var inspectable: Bool { UserDefaults.standard.bool(forKey: inspectableKey) }
    static var fullscreenCheck: Bool {
        let d = UserDefaults.standard
        return d.object(forKey: fullscreenCheckKey) == nil || d.bool(forKey: fullscreenCheckKey)   // "NO" string too
    }

    /// "1.0 (1)" — CFBundleShortVersionString (CFBundleVersion).
    static var appVersion: String {
        let app = FeedbackReport.AppInfo.current
        return "\(app.version) (\(app.build))"
    }
}

/// «Тема аквариума» in the fish menu. The raw value is the contract with aquarium/index.html: UserDefaults
/// `aq.theme`, `__AQ_BOOT.theme` (the first frame is already in this theme) and `aquariumSetTheme(…)`.
/// `.auto` follows the macOS appearance (prefers-color-scheme in the WKWebView, live).
enum AquariumTheme: String, CaseIterable {
    case auto, day, night

    var menuTitle: String {
        switch self {
        case .auto:  return "Как в системе"
        case .day:   return "Всегда день"
        case .night: return "Всегда ночь"
        }
    }
}

// MARK: - Page loads, WebContent terminations and unresponsive pages (persist across launches)
/// Keys: `aq.wc.total` (all terminations ever), `aq.wc.log` (last 20: at, display, reason, code, sinceLoadSec,
/// unresponsiveSec when the page was unresponsive at the moment it died),
/// `aq.pageLoads` ({reason: count}: launch | displayAdded | crashReload | retry | vlayer — the ⌥ «Задник слоями»
/// toggle reloading the page on purpose), `aq.pageLoads.log` (last 20),
/// `aq.unresponsive.total` (the page was unresponsive: WebKit reported it or the app's heartbeat went unanswered;
/// all episodes ever), `aq.unresponsive.log` (last 20: at, display, sinceLoadSec, source = webkit | heartbeat,
/// end = open | responsive | terminated | closed, durationSec).
/// Shown in «Скопировать диагностику»; the totals also go to the page as `__AQ_BOOT.crashes` / `.unresponsive`.
enum LifecycleStats {
    static let wcTotalKey = "aq.wc.total"
    static let wcLogKey = "aq.wc.log"
    static let loadsKey = "aq.pageLoads"
    static let loadsLogKey = "aq.pageLoads.log"
    static let unresponsiveTotalKey = "aq.unresponsive.total"
    static let unresponsiveLogKey = "aq.unresponsive.log"
    private static let logLimit = 20

    static var terminations: Int { UserDefaults.standard.integer(forKey: wcTotalKey) }
    static var unresponsiveEpisodes: Int { UserDefaults.standard.integer(forKey: unresponsiveTotalKey) }

    /// `_WKProcessTerminationReason` (WKNavigationDelegatePrivate.h); nil = the public delegate
    /// method was called, which carries no reason.
    static func reasonName(_ code: Int?) -> String {
        switch code {
        case 0?: return "memory"            // ExceededMemoryLimit
        case 1?: return "cpu"               // ExceededCPULimit
        case 2?: return "client"            // RequestedByClient (also idle exit / process swap)
        case 3?: return "crash"             // Crash, unresponsive, killed by the GPU/network process
        case 4?: return "gpuCrashLimit"     // ExceededSharedProcessCrashLimit (GPU process crashed too often)
        case let other?: return "code\(other)"
        case nil: return "unknown"
        }
    }

    /// `unresponsiveFor`: the page had been unresponsive this long when its process died (a freeze that
    /// ended in a kill — the white-screen case), nil if it was responsive.
    static func recordTermination(display: CGDirectDisplayID, code: Int?, sinceLoad: TimeInterval?,
                                  unresponsiveFor: TimeInterval? = nil) {
        let d = UserDefaults.standard
        d.set(d.integer(forKey: wcTotalKey) + 1, forKey: wcTotalKey)
        var entry: [String: Any] = ["at": FBDate.string(Date()), "display": Int(display), "reason": reasonName(code)]
        if let code = code { entry["code"] = code }
        if let s = sinceLoad { entry["sinceLoadSec"] = Int(s.rounded()) }
        if let u = unresponsiveFor { entry["unresponsiveSec"] = tenths(u) }
        append(entry, to: wcLogKey)
    }

    /// The page's WebContent process is unresponsive since `at` (`source`: webkit — WebKit reported it;
    /// heartbeat — the app's ping sent at `at` went unanswered). Counted and logged at once, as an
    /// `end: "open"` episode, so a freeze is on record even if the app is quit or killed before it ends;
    /// endUnresponsive fills in how and when it ended.
    static func recordUnresponsive(display: CGDirectDisplayID, at: Date, sinceLoad: TimeInterval?, source: String) {
        let d = UserDefaults.standard
        d.set(d.integer(forKey: unresponsiveTotalKey) + 1, forKey: unresponsiveTotalKey)
        var entry: [String: Any] = ["at": FBDate.string(at), "display": Int(display), "end": "open", "source": source]
        if let s = sinceLoad { entry["sinceLoadSec"] = Int(s.rounded()) }
        append(entry, to: unresponsiveLogKey)
    }

    /// Closes the newest open episode of `display`: `end` = responsive | terminated | closed, `durationSec`
    /// = time from its start (WebKit's "unresponsive", itself ≈3 s after the page stopped answering; or the
    /// unanswered heartbeat's send time) to that end.
    static func endUnresponsive(display: CGDirectDisplayID, duration: TimeInterval, end: String) {
        let d = UserDefaults.standard
        guard var log = d.array(forKey: unresponsiveLogKey),
              let i = log.lastIndex(where: { item in
                  guard let e = item as? [String: Any] else { return false }
                  return (e["display"] as? NSNumber)?.intValue == Int(display) && (e["end"] as? String) == "open"
              }),
              var entry = log[i] as? [String: Any] else { return }
        entry["end"] = end
        entry["durationSec"] = tenths(duration)
        log[i] = entry
        d.set(log, forKey: unresponsiveLogKey)
    }

    /// Seconds rounded to 0.1.
    private static func tenths(_ t: TimeInterval) -> Double { (t * 10).rounded() / 10 }

    static func recordLoad(display: CGDirectDisplayID, reason: String) {
        let d = UserDefaults.standard
        var counts: [String: Int] = [:]
        for (k, v) in d.dictionary(forKey: loadsKey) ?? [:] { counts[k] = (v as? NSNumber)?.intValue ?? 0 }
        counts[reason, default: 0] += 1
        d.set(counts, forKey: loadsKey)
        append(["at": FBDate.string(Date()), "display": Int(display), "reason": reason], to: loadsLogKey)
    }

    /// Plist values only (no NSNull): UserDefaults rejects anything else.
    private static func append(_ entry: [String: Any], to key: String) {
        let d = UserDefaults.standard
        var log = d.array(forKey: key) ?? []
        log.append(entry)
        if log.count > logLimit { log.removeFirst(log.count - logLimit) }
        d.set(log, forKey: key)
    }

    /// For «Скопировать диагностику» (`lifecycle`). Keys are only ever added, never renamed.
    static func snapshot() -> [String: Any] {
        let d = UserDefaults.standard
        return ["wcTotal": d.integer(forKey: wcTotalKey),
                "wcLog": d.array(forKey: wcLogKey) ?? [],
                "pageLoads": d.dictionary(forKey: loadsKey) ?? [:],
                "pageLoadsLog": d.array(forKey: loadsLogKey) ?? [],
                "unresponsiveTotal": d.integer(forKey: unresponsiveTotalKey),
                "unresponsiveLog": d.array(forKey: unresponsiveLogKey) ?? []]
    }
}

// MARK: - UI helpers
enum AppActivation {
    /// Accessory (menu-bar) app: without this, windows and alerts open behind the frontmost app.
    /// `activate()` exists only in the macOS 14 SDK (Swift 5.9+); `#available` alone does not
    /// stop an older SDK from failing to compile it.
    static func bringToFront() {
        #if compiler(>=5.9)
        if #available(macOS 14.0, *) { NSApp.activate() } else { NSApp.activate(ignoringOtherApps: true) }
        #else
        NSApp.activate(ignoringOtherApps: true)
        #endif
    }
}

enum HostAlert {
    /// A plain informational alert, shown on the next run-loop turn by a run-loop timer (never from
    /// inside a WebKit callback). Not DispatchQueue.main.async: a modal loop started inside a main-queue
    /// block stops the main queue until the alert closes (CFRunLoop does not drain it re-entrantly), so
    /// power changes, snapshot/probe timeouts and onClose would all wait for the OK click. From a timer
    /// callout the modal loop still services the main queue and `.common`-mode timers.
    /// `.default` mode: never fires inside menu tracking, and a second alert waits for the first to close.
    static func show(_ title: String, _ info: String, style: NSAlert.Style = .informational) {
        let timer = Timer(timeInterval: 0, repeats: false) { _ in
            MainActor.assumeIsolated {                   // Swift 5.9+, back-deployed to macOS 10.15
                AppActivation.bringToFront()
                let alert = NSAlert()
                alert.messageText = title
                alert.informativeText = info
                alert.alertStyle = style
                alert.addButton(withTitle: "OK")
                alert.runModal()
            }
        }
        RunLoop.main.add(timer, forMode: .default)
    }
}
