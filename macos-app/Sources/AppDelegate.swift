import Cocoa
import WebKit
import IOKit.ps
import ServiceManagement

/// Live-wallpaper controller: a menu-bar agent that places one desktop-level,
/// click-through window (hosting the aquarium WebView) on every screen, and
/// throttles rendering for battery/sleep. No pause/settings UI by design.
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var windows: [WallpaperWindow] = []
    private var statusItem: NSStatusItem!
    private var powerSource: CFRunLoopSource?

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupStatusItem()
        rebuildWindows()

        NotificationCenter.default.addObserver(
            self, selector: #selector(rebuildWindows),
            name: NSApplication.didChangeScreenParametersNotification, object: nil)

        let ws = NSWorkspace.shared.notificationCenter
        ws.addObserver(self, selector: #selector(displaySleep), name: NSWorkspace.screensDidSleepNotification, object: nil)
        ws.addObserver(self, selector: #selector(displayWake),  name: NSWorkspace.screensDidWakeNotification,  object: nil)

        startPowerMonitoring()
    }

    // MARK: Menu bar
    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = statusItem.button {
            btn.image = NSImage(systemSymbolName: "fish.fill", accessibilityDescription: "Aquarium")
            btn.image?.isTemplate = true
        }
        let menu = NSMenu()
        let login = NSMenuItem(title: "Запускать при входе", action: #selector(toggleLogin(_:)), keyEquivalent: "")
        login.target = self
        login.state = LoginItem.isEnabled ? .on : .off
        menu.addItem(login)
        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Выход", action: #selector(quit), keyEquivalent: "q")
        quit.target = self
        menu.addItem(quit)
        statusItem.menu = menu
    }

    // MARK: Wallpaper windows (one per screen)
    @objc private func rebuildWindows() {
        windows.forEach { $0.close() }
        windows = NSScreen.screens.map { WallpaperWindow(screen: $0) }
        windows.forEach { $0.show() }
        applyPowerState()
    }

    // MARK: Power / sleep — optimisation for a 24/7 laptop wallpaper
    private func startPowerMonitoring() {
        applyPowerState()
        let ctx = Unmanaged.passUnretained(self).toOpaque()
        let callback: IOPowerSourceCallbackType = { context in
            guard let context = context else { return }
            let me = Unmanaged<AppDelegate>.fromOpaque(context).takeUnretainedValue()
            DispatchQueue.main.async { me.applyPowerState() }
        }
        if let unmanaged = IOPSNotificationCreateRunLoopSource(callback, ctx) {
            let src = unmanaged.takeRetainedValue()
            CFRunLoopAddSource(CFRunLoopGetCurrent(), src, .defaultMode)
            powerSource = src
        }
    }

    @objc private func displaySleep() { windows.forEach { $0.setPower("paused") } }
    @objc private func displayWake()  { applyPowerState() }

    private func applyPowerState() {
        let mode = PowerInfo.isOnBattery ? "low" : "high"   // 30 fps on battery, 60 on power
        windows.forEach { $0.setPower(mode) }
    }

    // MARK: Menu actions
    @objc private func toggleLogin(_ sender: NSMenuItem) {
        LoginItem.toggle()
        sender.state = LoginItem.isEnabled ? .on : .off
    }
    @objc private func quit() { NSApp.terminate(nil) }
}

// MARK: - Battery state
enum PowerInfo {
    static var isOnBattery: Bool {
        guard let blob = IOPSCopyPowerSourcesInfo()?.takeRetainedValue(),
              let list = IOPSCopyPowerSourcesList(blob)?.takeRetainedValue() as? [CFTypeRef] else { return false }
        for ps in list {
            if let desc = IOPSGetPowerSourceDescription(blob, ps)?.takeUnretainedValue() as? [String: Any],
               let state = desc[kIOPSPowerSourceStateKey] as? String {
                return state == kIOPSBatteryPowerValue
            }
        }
        return false
    }
}

// MARK: - Launch at login (macOS 13+)
enum LoginItem {
    static var isEnabled: Bool {
        if #available(macOS 13.0, *) { return SMAppService.mainApp.status == .enabled }
        return false
    }
    static func toggle() {
        if #available(macOS 13.0, *) {
            do {
                if SMAppService.mainApp.status == .enabled { try SMAppService.mainApp.unregister() }
                else { try SMAppService.mainApp.register() }
            } catch { NSLog("Aquarium login-item error: \(error)") }
        }
    }
}
