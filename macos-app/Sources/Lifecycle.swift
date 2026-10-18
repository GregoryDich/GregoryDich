import Cocoa
import os

// Shared plumbing for AppDelegate and WallpaperWindow: the unified log, persisted settings,
// page-load and WebContent-termination counters (UserDefaults) and two small UI helpers.
// What happened and why is readable after the fact, without a debugger:
//   log show --last 3h --style compact --predicate 'subsystem == "com.gregorydich.aquariumwallpaper"'
//   defaults read com.gregorydich.aquariumwallpaper          (aq.wc.*, aq.pageLoads*)

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
    /// Safari ▸ Develop ▸ <Mac> ▸ wallpaper page (macOS 13.3+). Read when a page is created:
    ///   defaults write com.gregorydich.aquariumwallpaper inspectable -bool YES   (then restart the app)
    static let inspectableKey = "inspectable"

    static var hud: Bool {
        get { UserDefaults.standard.bool(forKey: hudKey) }
        set { UserDefaults.standard.set(newValue, forKey: hudKey) }
    }
    static var onlyMainScreen: Bool {
        get { UserDefaults.standard.bool(forKey: onlyMainKey) }
        set { UserDefaults.standard.set(newValue, forKey: onlyMainKey) }
    }
    static var inspectable: Bool { UserDefaults.standard.bool(forKey: inspectableKey) }

    /// "1.0 (1)" — CFBundleShortVersionString (CFBundleVersion).
    static var appVersion: String {
        let app = FeedbackReport.AppInfo.current
        return "\(app.version) (\(app.build))"
    }
}

// MARK: - Page loads and WebContent terminations (persist across launches)
/// Keys: `aq.wc.total` (all terminations ever), `aq.wc.log` (last 20: at, display, reason, code, sinceLoadSec),
/// `aq.pageLoads` ({reason: count}: launch | displayAdded | crashReload | retry), `aq.pageLoads.log` (last 20).
/// Shown in «Скопировать диагностику»; the total also goes to the page as `__AQ_BOOT.crashes`.
enum LifecycleStats {
    static let wcTotalKey = "aq.wc.total"
    static let wcLogKey = "aq.wc.log"
    static let loadsKey = "aq.pageLoads"
    static let loadsLogKey = "aq.pageLoads.log"
    private static let logLimit = 20

    static var terminations: Int { UserDefaults.standard.integer(forKey: wcTotalKey) }

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

    static func recordTermination(display: CGDirectDisplayID, code: Int?, sinceLoad: TimeInterval?) {
        let d = UserDefaults.standard
        d.set(d.integer(forKey: wcTotalKey) + 1, forKey: wcTotalKey)
        var entry: [String: Any] = ["at": FBDate.string(Date()), "display": Int(display), "reason": reasonName(code)]
        if let code = code { entry["code"] = code }
        if let s = sinceLoad { entry["sinceLoadSec"] = Int(s.rounded()) }
        append(entry, to: wcLogKey)
    }

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

    /// For «Скопировать диагностику».
    static func snapshot() -> [String: Any] {
        let d = UserDefaults.standard
        return ["wcTotal": d.integer(forKey: wcTotalKey),
                "wcLog": d.array(forKey: wcLogKey) ?? [],
                "pageLoads": d.dictionary(forKey: loadsKey) ?? [:],
                "pageLoadsLog": d.array(forKey: loadsLogKey) ?? []]
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
