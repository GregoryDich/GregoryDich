import Cocoa
import WebKit
import IOKit.ps
import ServiceManagement

/// Live-wallpaper controller: a menu-bar agent that places one desktop-level,
/// click-through window (hosting the aquarium WebView) on every screen, and
/// throttles rendering for battery/sleep. No pause/settings UI by design.
final class AppDelegate: NSObject, NSApplicationDelegate {
    /// One window per display, keyed by CGDirectDisplayID (stable across resolution/arrangement
    /// changes and wake), so a screen-parameter change never reloads the aquarium needlessly.
    private var windows: [CGDirectDisplayID: WallpaperWindow] = [:]
    private var statusItem: NSStatusItem!
    private var powerSource: CFRunLoopSource?
    private var powerMode = "high"
    private var displaysAsleep = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupStatusItem()
        powerMode = PowerInfo.isOnBattery ? "low" : "high"
        screensChanged()

        NotificationCenter.default.addObserver(
            self, selector: #selector(screensChanged),
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

    // MARK: Wallpaper windows (one per display)
    /// macOS posts didChangeScreenParameters for resolution/arrangement changes, display
    /// re-enumeration on wake and often for Dock/visible-frame changes. Previously every post closed
    /// all windows and reloaded every page (poster → video → fish re-placed → caches rebuilt, briefly
    /// two 1440p decoders per screen): the owner's "the app seems to restart". Now: diff by display ID —
    /// keep and only resize existing windows, create windows for new displays, close removed ones.
    private static func displayID(of screen: NSScreen) -> CGDirectDisplayID? {
        (screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value
    }

    @objc private func screensChanged() {
        var seen = Set<CGDirectDisplayID>()
        var kept = 0, added = 0
        for screen in NSScreen.screens {
            guard let id = AppDelegate.displayID(of: screen), !seen.contains(id) else { continue }
            seen.insert(id)
            if let w = windows[id] {
                w.update(screen: screen)
                kept += 1
            } else {
                let w = WallpaperWindow(screen: screen, displayID: id, power: currentMode())
                windows[id] = w
                w.show()
                added += 1
            }
        }
        var removed = 0
        for (id, w) in windows where !seen.contains(id) {
            w.close()
            windows[id] = nil
            removed += 1
        }
        NSLog("Aquarium: screens changed — kept \(kept), added \(added), removed \(removed)")
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

    @objc private func displaySleep() {
        displaysAsleep = true
        windows.values.forEach { $0.setPower("paused") }
    }
    @objc private func displayWake() {
        displaysAsleep = false
        applyPowerState()
    }

    private func currentMode() -> String { displaysAsleep ? "paused" : powerMode }

    private func applyPowerState() {
        powerMode = PowerInfo.isOnBattery ? "low" : "high"   // 30 fps on battery, 60 on power
        let mode = currentMode()
        windows.values.forEach { $0.setPower(mode) }        // no-op unless the mode really changed
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
