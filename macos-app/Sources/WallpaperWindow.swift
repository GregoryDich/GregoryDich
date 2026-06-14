import Cocoa
import WebKit

/// One borderless, click-through window pinned to the desktop (behind icons,
/// on every Space) hosting the aquarium in wallpaper mode.
final class WallpaperWindow {
    private let window: NSWindow
    private let webView: WKWebView

    init(screen: NSScreen) {
        // Tell the page it is running as a wallpaper (hides hint/cursor/controls).
        let config = WKWebViewConfiguration()
        let flag = WKUserScript(source: "window.__WALLPAPER = true;",
                                injectionTime: .atDocumentStart, forMainFrameOnly: true)
        config.userContentController.addUserScript(flag)

        webView = WKWebView(frame: screen.frame, configuration: config)
        webView.autoresizingMask = [.width, .height]

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

        loadAquarium()
    }

    private func loadAquarium() {
        guard let url = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "aquarium") else {
            NSLog("Aquarium: bundled aquarium/index.html not found")
            return
        }
        webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }

    func show()  { window.orderFrontRegardless() }
    func close() { window.orderOut(nil) }

    /// "high" (60 fps) | "low" (30 fps, battery) | "paused" (display asleep).
    func setPower(_ mode: String) {
        webView.evaluateJavaScript("window.aquariumSetPower && window.aquariumSetPower('\(mode)')",
                                   completionHandler: nil)
    }
}
