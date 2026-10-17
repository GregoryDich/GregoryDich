import Cocoa
import WebKit

/// «Тест слоёв» (⌥ in the menu, P1.8): aquarium/spike/layers.html in a normal, resizable window with
/// its own WKWebView — CSS blend layers over the video next to the canvas path, each half with its
/// own fps counter. Single instance; AppDelegate pauses the wallpapers while it is open so they do
/// not compete with the measurement.
final class LayersTestWindow: NSObject, NSWindowDelegate {
    static let autosaveName = "AQLayersTest"
    var onClose: (() -> Void)?
    private let window: NSWindow
    private let webView: WKWebView

    /// nil when the page is not in the bundle (built from an older checkout).
    init?(bundle: Bundle = .main) {
        guard let url = bundle.url(forResource: "layers", withExtension: "html", subdirectory: "aquarium/spike") else {
            Log.error("aquarium/spike/layers.html not in the bundle")
            return nil
        }
        let config = WKWebViewConfiguration()
        config.mediaTypesRequiringUserActionForPlayback = []
        let frame = NSRect(x: 0, y: 0, width: 1280, height: 800)
        webView = WKWebView(frame: frame, configuration: config)
        webView.autoresizingMask = [.width, .height]
        if AppSettings.inspectable {
            if #available(macOS 13.3, *) { webView.isInspectable = true }
        }
        // FeedbackPanelWindow: ⌘W/⌘C/… work although a menu-bar app has no Edit menu.
        window = FeedbackPanelWindow(contentRect: frame,
                                     styleMask: [.titled, .closable, .miniaturizable, .resizable],
                                     backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false              // owned here (AppDelegate.layersTest)
        window.title = "Тест слоёв"
        window.contentMinSize = NSSize(width: 640, height: 400)
        window.contentView = webView
        super.init()
        window.delegate = self
        if !window.setFrameUsingName(LayersTestWindow.autosaveName) { window.center() }
        _ = window.setFrameAutosaveName(LayersTestWindow.autosaveName)
        // Read access to the whole aquarium/ folder: the page loads ../assets, ../fish, the videos.
        let root = url.deletingLastPathComponent().deletingLastPathComponent()
        webView.loadFileURL(url, allowingReadAccessTo: root)
        Log.info("layers test opened")
    }

    func present() {
        AppActivation.bringToFront()
        window.makeKeyAndOrderFront(nil)
    }

    func windowWillClose(_ notification: Notification) {
        webView.stopLoading()
        Log.info("layers test closed")
        let done = onClose
        onClose = nil
        DispatchQueue.main.async { done?() }             // release after AppKit finishes closing
    }
}
