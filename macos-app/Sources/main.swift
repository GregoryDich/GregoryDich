import Cocoa

// Menu-bar agent (no Dock icon). The real work happens in AppDelegate.
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
FeedbackCenter.shared.start()   // uptime clock, local feedback retention, retry queue
app.run()
