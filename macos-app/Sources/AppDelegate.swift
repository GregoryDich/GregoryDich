import Cocoa
import WebKit
import IOKit.ps
import ServiceManagement

/// Live-wallpaper controller: a menu-bar agent that places one desktop-level,
/// click-through window (hosting the aquarium WebView) on every screen, and
/// throttles rendering for battery, Low Power Mode, heat and sleep. No pause/settings UI by design;
/// the menu has diagnostics for the 60-fps work (P1.1) and the feedback form.
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    /// One window per display, keyed by CGDirectDisplayID (stable across resolution/arrangement
    /// changes and wake), so a screen-parameter change never reloads the aquarium needlessly.
    private var windows: [CGDirectDisplayID: WallpaperWindow] = [:]
    /// Windows of displays that disappeared: hidden and paused, re-shown without a reload if the
    /// display comes back within 15 min (monitor standby, lid closed and opened with an external display).
    private var parked: [CGDirectDisplayID: (window: WallpaperWindow, since: Date)] = [:]
    private static let parkTime: TimeInterval = 15 * 60
    /// macOS posts screen-parameter changes in bursts, and mid-burst an external display can vanish
    /// from NSScreen.screens for a moment: act once, 1.5 s after the last one.
    private static let screenDebounce: TimeInterval = 1.5

    private var statusItem: NSStatusItem!
    private var hudItem: NSMenuItem!
    private var probeItem: NSMenuItem!
    private var layersItem: NSMenuItem!
    private var onlyMainItem: NSMenuItem!
    private var loginItem: NSMenuItem!

    private var powerSource: CFRunLoopSource?
    private var powerMode = "high"
    private var powerReasons: [String] = []
    private var displaysAsleep = false
    private var started = false                      // first applyScreens done: later pages are "displayAdded"
    private var probeRunning = false
    private var layersTest: LayersTestWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupStatusItem()
        updatePowerMode()
        applyScreens()
        started = true

        NotificationCenter.default.addObserver(
            self, selector: #selector(screensChanged),
            name: NSApplication.didChangeScreenParametersNotification, object: nil)
        // Low Power Mode and thermal state: posted on arbitrary threads (handler hops to main, capture-free).
        NotificationCenter.default.addObserver(
            self, selector: #selector(powerConditionsChanged),
            name: .NSProcessInfoPowerStateDidChange, object: nil)
        NotificationCenter.default.addObserver(
            self, selector: #selector(powerConditionsChanged),
            name: ProcessInfo.thermalStateDidChangeNotification, object: nil)

        let ws = NSWorkspace.shared.notificationCenter
        ws.addObserver(self, selector: #selector(displaySleep), name: NSWorkspace.screensDidSleepNotification, object: nil)
        ws.addObserver(self, selector: #selector(displayWake),  name: NSWorkspace.screensDidWakeNotification,  object: nil)

        startPowerMonitoring()
        Log.info("started: \(AppSettings.appVersion), macOS \(Diagnostics.osVersion), power \(powerMode)")
    }

    // MARK: Menu bar
    /// Показать FPS · Скопировать диагностику · (⌥: Тест производительности, Тест слоёв) · — ·
    /// Написать отзыв… · Только на главном экране (2+ displays) · Запускать при входе · — · Выход
    private func setupStatusItem() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = statusItem.button {
            if let image = NSImage(systemSymbolName: "fish.fill", accessibilityDescription: "Aquarium") {
                image.isTemplate = true
                btn.image = image
            } else {
                btn.title = "🐟"                          // no SF Symbol: an empty item would be invisible
            }
        }
        let menu = NSMenu()
        menu.autoenablesItems = false
        menu.delegate = self

        hudItem = item("Показать FPS", #selector(toggleHUD(_:)))
        menu.addItem(hudItem)
        menu.addItem(item("Скопировать диагностику", #selector(copyDiagnostics)))
        probeItem = item("Тест производительности (≈45 с)", #selector(runPerfProbe))
        probeItem.isHidden = true
        menu.addItem(probeItem)
        layersItem = item("Тест слоёв", #selector(openLayersTest))
        layersItem.isHidden = true
        menu.addItem(layersItem)
        menu.addItem(.separator())

        menu.addItem(FeedbackCenter.shared.menuItem())   // «Написать отзыв…» (FeedbackWindow.swift)
        onlyMainItem = item("Только на главном экране", #selector(toggleOnlyMain(_:)))
        menu.addItem(onlyMainItem)
        loginItem = item("Запускать при входе", #selector(toggleLogin(_:)))
        menu.addItem(loginItem)
        menu.addItem(.separator())
        let quit = item("Выход", #selector(quit))
        quit.keyEquivalent = "q"
        menu.addItem(quit)
        statusItem.menu = menu
        refreshMenu(optionHeld: false)
    }

    private func item(_ title: String, _ action: Selector) -> NSMenuItem {
        let it = NSMenuItem(title: title, action: action, keyEquivalent: "")
        it.target = self
        return it
    }

    /// The test items show only when ⌥ is held while clicking the fish.
    func menuWillOpen(_ menu: NSMenu) {
        refreshMenu(optionHeld: NSEvent.modifierFlags.contains(.option))
    }

    private func refreshMenu(optionHeld: Bool) {
        hudItem.state = AppSettings.hud ? .on : .off
        loginItem.state = LoginItem.isEnabled ? .on : .off
        onlyMainItem.state = AppSettings.onlyMainScreen ? .on : .off
        onlyMainItem.isHidden = NSScreen.screens.count < 2 && !AppSettings.onlyMainScreen
        probeItem.isHidden = !optionHeld
        probeItem.isEnabled = !probeRunning
        probeItem.title = probeRunning ? "Тест производительности — идёт…" : "Тест производительности (≈45 с)"
        layersItem.isHidden = !optionHeld
        layersItem.isEnabled = !probeRunning                // the test pauses the wallpapers: the probe would stall
    }

    // MARK: Wallpaper windows (one per display)
    /// macOS posts didChangeScreenParameters for resolution/arrangement changes, display
    /// re-enumeration on wake and often for Dock/visible-frame changes. Previously every post closed
    /// all windows and reloaded every page: the owner's "the app seems to restart". Now: debounce,
    /// then diff by display ID — resize kept windows, re-show parked ones, create windows for new
    /// displays, park the windows of displays that went away.
    private static func displayID(of screen: NSScreen) -> CGDirectDisplayID? {
        (screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value
    }

    /// The display with the menu bar (NSScreen.screens[0]); NSScreen.main follows the key window instead.
    private static var primaryDisplayID: CGDirectDisplayID? {
        NSScreen.screens.first.flatMap { displayID(of: $0) }
    }

    @objc private func screensChanged() {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(applyScreens), object: nil)
        perform(#selector(applyScreens), with: nil, afterDelay: AppDelegate.screenDebounce, inModes: [.common])
    }

    @objc private func applyScreens() {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(applyScreens), object: nil)
        let primary = AppDelegate.primaryDisplayID
        var present: [CGDirectDisplayID: NSScreen] = [:]
        var order: [CGDirectDisplayID] = []
        for screen in NSScreen.screens {
            guard let id = AppDelegate.displayID(of: screen), present[id] == nil else { continue }
            present[id] = screen
            order.append(id)
        }
        let onlyMain = AppSettings.onlyMainScreen
        let wanted = Set(order.filter { !onlyMain || $0 == primary })
        let mode = currentMode()
        let constrained = powerConstrained
        var kept = 0, added = 0, restored = 0, parkedNow = 0, closed = 0

        for id in order where wanted.contains(id) {
            guard let screen = present[id] else { continue }
            let isMain = id == primary
            if let w = windows[id] {
                w.update(screen: screen)
                w.setRole(isMain: isMain)
                kept += 1
            } else if let p = parked.removeValue(forKey: id) {
                let w = p.window
                windows[id] = w
                w.update(screen: screen)
                w.setRole(isMain: isMain)
                w.setPower(mode, constrained: constrained)
                w.show()
                restored += 1
                Log.info("display \(id) is back after \(Int(Date().timeIntervalSince(p.since))) s — window restored, no reload")
            } else {
                let w = WallpaperWindow(screen: screen, displayID: id, isMain: isMain, power: mode,
                                        constrained: constrained, reason: started ? "displayAdded" : "launch")
                windows[id] = w
                w.show()
                added += 1
            }
        }
        for (id, w) in windows where !wanted.contains(id) {
            windows[id] = nil
            if present[id] == nil {                      // display gone, maybe only for a moment
                w.park()
                parked[id] = (w, Date())
                parkedNow += 1
            } else {                                     // «Только на главном экране»
                w.close()
                closed += 1
            }
        }
        for (id, p) in parked where present[id] != nil && !wanted.contains(id) {
            p.window.close()
            parked[id] = nil
            closed += 1
        }
        purgeParked()
        windows.values.forEach { $0.retryIfGaveUp() }    // never black forever
        Log.info("screens: \(order.count) present, kept \(kept), added \(added), restored \(restored), " +
                 "parked \(parkedNow), closed \(closed), waiting \(parked.count)")
    }

    /// Releases parked windows whose display has been gone for 15 min; re-arms itself for the next one.
    @objc private func purgeParked() {
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(purgeParked), object: nil)
        let now = Date()
        for (id, p) in parked where now.timeIntervalSince(p.since) >= AppDelegate.parkTime {
            p.window.close()
            parked[id] = nil
            Log.info("display \(id) did not come back in 15 min — its window is released")
        }
        if let oldest = parked.values.map({ $0.since }).min() {
            let delay = max(1, AppDelegate.parkTime - now.timeIntervalSince(oldest) + 1)
            perform(#selector(purgeParked), with: nil, afterDelay: delay, inModes: [.common])
        }
    }

    // MARK: Power / sleep — optimisation for a 24/7 laptop wallpaper
    private func startPowerMonitoring() {
        applyPowerState()
        // Battery/AC changes. Needs no context: the handler finds the delegate itself (applyPowerStateSoon).
        let callback: IOPowerSourceCallbackType = { _ in AppDelegate.applyPowerStateSoon() }
        if let unmanaged = IOPSNotificationCreateRunLoopSource(callback, nil) {
            let src = unmanaged.takeRetainedValue()
            CFRunLoopAddSource(CFRunLoopGetCurrent(), src, .commonModes)   // also while a menu/alert is open
            powerSource = src
        }
    }

    @objc nonisolated private func powerConditionsChanged() {
        AppDelegate.applyPowerStateSoon()
    }

    /// From any thread (IOPS callback, Low Power Mode / thermal-state notifications): applyPowerState() on
    /// the next main-queue turn. Static and capture-free on purpose: the main-queue block is @Sendable and
    /// AppDelegate is not Sendable, so capturing `self` (or the IOPS context object) in it is a Swift 6
    /// warning ("capture of 'self' with non-Sendable type 'AppDelegate?' in a '@Sendable' closure"). The
    /// delegate is looked up on the main thread instead; it lives as long as the app (main.swift).
    nonisolated private static func applyPowerStateSoon() {
        DispatchQueue.main.async {
            MainActor.assumeIsolated {                   // the main queue runs on the main thread
                guard let app = NSApp.delegate as? AppDelegate else { return }
                app.applyPowerState()
            }
        }
    }

    @objc private func displaySleep() {
        displaysAsleep = true
        applyPowerState()
    }
    @objc private func displayWake() {
        displaysAsleep = false
        applyPowerState()
        windows.values.forEach { $0.retryIfGaveUp() }
    }

    /// "paused" while the displays sleep or the layers test is open; else the power mode.
    private func currentMode() -> String {
        (displaysAsleep || layersTest != nil) ? "paused" : powerMode
    }

    /// Low Power Mode or heat: on top of "low", the pages get the 1.8 MP budget (ROADMAP P1.3).
    private var powerConstrained: Bool {
        powerReasons.contains("lowPowerMode") || powerReasons.contains("thermal")
    }

    /// 'low' (30 fps, smaller pixel budget) on battery, in Low Power Mode, or when the Mac is hot
    /// (thermal state serious/critical); 'high' (60 fps) otherwise.
    private func updatePowerMode() {
        var reasons: [String] = []
        if PowerInfo.isOnBattery { reasons.append("battery") }
        let info = ProcessInfo.processInfo
        if info.isLowPowerModeEnabled { reasons.append("lowPowerMode") }
        if info.thermalState.rawValue >= ProcessInfo.ThermalState.serious.rawValue { reasons.append("thermal") }
        let mode = reasons.isEmpty ? "high" : "low"
        if mode != powerMode || reasons != powerReasons {
            Log.info("power \(mode)" + (reasons.isEmpty ? "" : " (\(reasons.joined(separator: ", ")))"))
        }
        powerMode = mode
        powerReasons = reasons
    }

    private func applyPowerState() {
        updatePowerMode()
        let mode = currentMode(), constrained = powerConstrained
        windows.values.forEach { $0.setPower(mode, constrained: constrained) }   // no-op unless something changed
    }

    // MARK: Menu actions
    @objc private func toggleHUD(_ sender: NSMenuItem) {
        let on = !AppSettings.hud
        AppSettings.hud = on
        sender.state = on ? .on : .off
        windows.values.forEach { $0.setHUD(on) }
        parked.values.forEach { $0.window.setHUD(on) }
    }

    @objc private func toggleOnlyMain(_ sender: NSMenuItem) {
        AppSettings.onlyMainScreen = !AppSettings.onlyMainScreen
        sender.state = AppSettings.onlyMainScreen ? .on : .off
        Log.info("only main screen: \(AppSettings.onlyMainScreen)")
        applyScreens()
    }

    private func hostState() -> [String: Any] {
        let primary = AppDelegate.primaryDisplayID
        // Every display macOS reports (also those without an aquarium), with the app's notion of "main".
        let screens: [[String: Any]] = NSScreen.screens.prefix(8).map { screen in
            var d = WallpaperWindow.ScreenInfo(screen).dict
            let id = AppDelegate.displayID(of: screen)
            d["id"] = id.map { Int($0) } ?? -1
            d["main"] = id != nil && id == primary
            d["wallpaper"] = id.map { windows[$0] != nil ? "shown" : parked[$0] != nil ? "parked" : "none" } ?? "none"
            return d
        }
        return [
            "powerMode": powerMode,
            "powerReasons": powerReasons,
            "powerConstrained": powerConstrained,
            "screens": screens,
            "displaysAsleep": displaysAsleep,
            "onlyMainScreen": AppSettings.onlyMainScreen,
            "hud": AppSettings.hud,
            "inspectable": AppSettings.inspectable,
            "layersTestOpen": layersTest != nil,
            "primaryDisplay": primary.map { Int($0) } ?? -1,
            "parkedDisplays": parked.map { ["display": Int($0.key), "parkedAgoSec": Int(Date().timeIntervalSince($0.value.since))] },
        ]
    }

    /// Main display first, then by display ID.
    private var orderedWindows: [WallpaperWindow] {
        windows.values.sorted { a, b in a.isMain != b.isMain ? a.isMain : a.displayID < b.displayID }
    }

    /// aquariumPerfSnapshot() of every wallpaper + system and host facts → pretty JSON → clipboard.
    @objc private func copyDiagnostics() {
        let list = orderedWindows
        var snapshots: [CGDirectDisplayID: Any] = [:]
        var pending = list.count
        let finish: () -> Void = { [weak self] in
            guard let self = self else { return }
            let entries: [[String: Any]] = list.map { w in
                var d = w.hostInfo()
                d["snapshot"] = snapshots[w.displayID] ?? NSNull()
                return d
            }
            let json = PerfDiagnostics.report(kind: "diagnostics", host: self.hostState(), windows: entries)
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(json, forType: .string)
            Log.info("diagnostics copied (\(json.utf8.count) bytes, \(list.count) windows)")
            HostAlert.show("Диагностика скопирована",
                           "Вставьте её (⌘V) в письмо или сообщение разработчику. Экранов с аквариумом: \(list.count).")
        }
        if list.isEmpty { finish(); return }
        for w in list {
            w.perfSnapshot { value in
                snapshots[w.displayID] = value
                pending -= 1
                if pending == 0 { finish() }
            }
        }
    }

    /// ⌥ «Тест производительности (≈45 с)»: aquariumPerfProbe() on the main display's page; the result
    /// (plus system facts) goes to the clipboard and a short summary into an alert.
    @objc private func runPerfProbe() {
        guard !probeRunning else { return }
        guard let primary = AppDelegate.primaryDisplayID, let w = windows[primary] else {
            HostAlert.show("Тест не запущен", "На главном экране нет аквариума.", style: .warning)
            return
        }
        guard !displaysAsleep, layersTest == nil else {
            HostAlert.show("Тест не запущен", "Закройте «Тест слоёв» и не давайте экрану заснуть.", style: .warning)
            return
        }
        // WKWebView detects window occlusion: a desktop fully covered by windows is a hidden page, no frames.
        guard w.isDesktopVisible else {
            HostAlert.show("Тест не запущен",
                           "Аквариум сейчас закрыт окнами и не рисуется. Покажите рабочий стол (F11 или жест " +
                           "«развести большой и три пальца») и запустите тест снова.", style: .warning)
            return
        }
        probeRunning = true
        refreshMenu(optionHeld: true)
        Log.info("perf probe started on display \(primary)")
        w.perfProbe { [weak self] result, error in
            guard let self = self else { return }
            self.probeRunning = false
            self.refreshMenu(optionHeld: false)
            // The page answers {error} when it has no aquariumPerfProbe (an older engine).
            let pageError = (result as? [String: Any])?["error"] as? String
            guard let result = result, pageError == nil else {
                let why = pageError ?? error ?? "?"
                Log.error("perf probe failed: \(why)")
                HostAlert.show("Тест производительности не удался", why, style: .warning)
                return
            }
            let json = PerfDiagnostics.report(kind: "probe", host: self.hostState(),
                                              windows: [w.hostInfo()], extra: ["probe": result])
            NSPasteboard.general.clearContents()
            NSPasteboard.general.setString(json, forType: .string)
            // "hidden": the desktop got covered by windows (WebKit hid the page); "timeout": no frames for a
            // long while (display slept, page paused) — partial results only.
            let aborted = (result as? [String: Any])?["aborted"] as? String
            Log.info("perf probe done (\(json.utf8.count) bytes)" + (aborted.map { ", aborted: \($0)" } ?? ""))
            var parts: [String] = []
            if aborted != nil {
                parts.append("Аквариум перестал рисовать кадры (рабочий стол закрыли окнами или экран заснул) — " +
                             "ниже только то, что успели. Покажите рабочий стол и повторите тест.")
            }
            let summary = PerfDiagnostics.probeSummary(result)
            if !summary.isEmpty { parts.append(summary) }
            parts.append("Результат скопирован — вставьте его (⌘V) в письмо или сообщение разработчику.")
            if aborted == nil {
                HostAlert.show("Тест производительности готов", parts.joined(separator: "\n\n"))
            } else {
                HostAlert.show("Тест производительности прерван", parts.joined(separator: "\n\n"), style: .warning)
            }
        }
    }

    /// ⌥ «Тест слоёв»: aquarium/spike/layers.html in its own window; wallpapers pause meanwhile.
    @objc private func openLayersTest() {
        if let open = layersTest { open.present(); return }
        guard !probeRunning else {
            HostAlert.show("Тест слоёв не открыт", "Идёт тест производительности — дождитесь его окончания.", style: .warning)
            return
        }
        guard let test = LayersTestWindow() else {
            HostAlert.show("Тест слоёв недоступен", "В этой сборке нет страницы aquarium/spike/layers.html.", style: .warning)
            return
        }
        test.onClose = { [weak self] in
            self?.layersTest = nil
            self?.applyPowerState()                      // wallpapers resume
        }
        layersTest = test
        applyPowerState()                                // wallpapers pause
        test.present()
    }

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
            } catch { Log.error("login-item error: \(error.localizedDescription)") }
        }
    }
}
