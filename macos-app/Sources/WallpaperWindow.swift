import Cocoa
import WebKit

/// One borderless, click-through window pinned to the desktop (behind icons,
/// on every Space) hosting the aquarium in wallpaper mode.
///
/// The page is loaded ONCE per display. Screen changes (resolution, arrangement, Dock,
/// wake) only move/resize the window — WKWebView autoresizes and the engine handles
/// `resize` itself (see AppDelegate.screensChanged). A WebContent crash or memory kill
/// is reloaded with a backoff instead of WebKit's silent default.
final class WallpaperWindow: NSObject, WKNavigationDelegate {
    let displayID: CGDirectDisplayID
    private let window: NSWindow
    private let webView: WKWebView
    private var power: String
    private var loaded = false
    private var crashTimes: [Date] = []

    init(screen: NSScreen, displayID: CGDirectDisplayID, power: String) {
        self.displayID = displayID
        self.power = power
        // Tell the page it is running as a wallpaper (hides hint/cursor/controls) and pass the
        // power mode at document start: the very first frame already runs at the right rate
        // (evaluateJavaScript before the page has loaded is lost).
        let config = WKWebViewConfiguration()
        let boot = WKUserScript(source: "window.__WALLPAPER = true; window.__AQ_POWER = '\(power)';",
                                injectionTime: .atDocumentStart, forMainFrameOnly: true)
        config.userContentController.addUserScript(boot)
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

        window = NSWindow(contentRect: screen.frame, styleMask: [.borderless],
                          backing: .buffered, defer: false)
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
        loadAquarium()
    }

    private func loadAquarium() {
        guard let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "aquarium") else {
            NSLog("Aquarium: bundled aquarium/index.html not found")
            return
        }
        loaded = false
        webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }

    func show()  { window.orderFrontRegardless() }
    func close() {
        webView.navigationDelegate = nil
        webView.stopLoading()
        window.orderOut(nil)
    }

    /// The display still exists but its geometry changed: move/resize only, no reload.
    func update(screen: NSScreen) {
        if window.frame != screen.frame {
            NSLog("Aquarium: display \(displayID) resized to \(Int(screen.frame.width))x\(Int(screen.frame.height)) (no reload)")
            window.setFrame(screen.frame, display: true)
        }
    }

    /// "high" (60 fps) | "low" (30 fps, battery) | "paused" (display asleep).
    /// Sent only on a real change (every IOPS event, e.g. a battery-percent tick, used to reset the
    /// engine's frame-rate governor); re-sent after every (re)load in didFinish.
    func setPower(_ mode: String) {
        if mode == power && loaded { return }
        power = mode
        guard loaded else { return }                     // didFinish will send it
        webView.evaluateJavaScript("window.aquariumSetPower && window.aquariumSetPower('\(mode)')",
                                   completionHandler: nil)
    }

    // MARK: WKNavigationDelegate
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        loaded = true
        webView.evaluateJavaScript("window.aquariumSetPower && window.aquariumSetPower('\(power)')",
                                   completionHandler: nil)
    }

    /// WebContent process crashed or was killed (memory pressure): reload with a backoff —
    /// at most 3 reloads in 5 minutes, then stay black and log (no reload storm).
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        loaded = false
        let now = Date()
        crashTimes = crashTimes.filter { now.timeIntervalSince($0) < 300 }
        crashTimes.append(now)
        let n = crashTimes.count
        NSLog("Aquarium: WebContent process terminated on display \(displayID) (\(n) in 5 min)")
        guard n <= 3 else {
            NSLog("Aquarium: too many WebContent crashes on display \(displayID) — staying black")
            return
        }
        let delay: Double = n == 1 ? 1 : (n == 2 ? 5 : 15)
        DispatchQueue.main.asyncAfter(deadline: .now() + delay) { [weak self] in
            guard let self = self, !self.loaded else { return }
            NSLog("Aquarium: reloading display \(self.displayID) after crash")
            self.loadAquarium()
        }
    }
}
