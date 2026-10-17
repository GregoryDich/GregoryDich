import Cocoa
import WebKit

// Diagnostics for feedback (also meant for a future «Скопировать диагностику» menu item).
// Public APIs only, no permission prompts. Never collected: serial number, hardware UUID,
// user/computer/host name, IP or Wi-Fi details, app or window lists, absolute paths, install IDs.

struct DiagnosticsReport: Codable {
    struct OS: Codable {
        var version: String                 // "14.6.1"
        var build: String?                  // "23G93"
        func encode(to encoder: Encoder) throws {
            var c = encoder.container(keyedBy: CodingKeys.self)
            try c.encode(version, forKey: .version)
            try c.encode(build, forKey: .build)
        }
    }
    struct Screen: Codable {
        var main: Bool
        var widthPt: Int
        var heightPt: Int
        var scale: Double
        var maxFps: Int?
        func encode(to encoder: Encoder) throws {
            var c = encoder.container(keyedBy: CodingKeys.self)
            try c.encode(main, forKey: .main)
            try c.encode(widthPt, forKey: .widthPt)
            try c.encode(heightPt, forKey: .heightPt)
            try c.encode(scale, forKey: .scale)
            try c.encode(maxFps, forKey: .maxFps)
        }
    }
    struct Power: Codable {
        var onBattery: Bool
        var lowPowerMode: Bool
        var thermal: String                 // nominal | fair | serious | critical
    }

    var os: OS
    var model: String                       // "Mac15,6"
    var arch: String                        // arm64 | x86_64
    var rosetta: Bool
    var memoryGB: Int
    var screens: [Screen]
    var appearance: String                  // dark | light
    var power: Power
    var launchAtLogin: Bool
    var appUptimeSec: Int
    var language: String?
    var engine: EngineStats?

    enum CodingKeys: String, CodingKey {
        case os, model, arch, rosetta, memoryGB, screens, appearance, power, launchAtLogin, appUptimeSec, language, engine
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(os, forKey: .os)
        try c.encode(model, forKey: .model)
        try c.encode(arch, forKey: .arch)
        try c.encode(rosetta, forKey: .rosetta)
        try c.encode(memoryGB, forKey: .memoryGB)
        try c.encode(screens, forKey: .screens)
        try c.encode(appearance, forKey: .appearance)
        try c.encode(power, forKey: .power)
        try c.encode(launchAtLogin, forKey: .launchAtLogin)
        try c.encode(appUptimeSec, forKey: .appUptimeSec)
        try c.encode(language, forKey: .language)
        try c.encode(engine, forKey: .engine)
    }
}

/// Engine numbers from `window.__aq.stats()` on the main-screen wallpaper.
struct EngineStats: Codable {
    var fps: Double?                        // smoothed frames per second
    var p90: Double?                        // 90th percentile frame INTERVAL over the last second, ms (engine GOV.p90)
    var power: String?                      // high | low | paused
    var theme: String?
    var bgMode: String?
    var backingMP: Double?                  // canvas backing store, megapixels
    var dpr: Double?
    var quality: [String: Double]?          // {level, particles, fishSlices, causticScale, rsMul}
    var fish: Int?

    enum CodingKeys: String, CodingKey { case fps, p90, power, theme, bgMode, backingMP, dpr, quality, fish }

    init(dict d: [String: Any]) {
        func num(_ v: Any?) -> Double? {
            var x: Double?
            if let n = v as? NSNumber { x = n.doubleValue } else if let dv = v as? Double { x = dv } else if let iv = v as? Int { x = Double(iv) }
            guard let value = x, value.isFinite else { return nil }
            return value
        }
        func round1(_ v: Double?) -> Double? { v.map { ($0 * 10).rounded() / 10 } }
        fps = round1(num(d["fps"]))
        p90 = round1(num(d["p90"]))
        if let p = d["power"] as? String, ["high", "low", "paused"].contains(p) { power = p }
        theme = (d["theme"] as? String).map { String($0.prefix(20)) }
        bgMode = (d["bgMode"] as? String).map { String($0.prefix(20)) }
        backingMP = num(d["backingMP"]).map { ($0 * 100).rounded() / 100 }
        dpr = num(d["dpr"])
        if let q = d["quality"] as? [String: Any] {
            var out: [String: Double] = [:]
            for (k, v) in q { if let n = num(v) { out[String(k.prefix(20))] = n } }
            quality = out
        }
        fish = num(d["fish"]).flatMap { Int(exactly: $0.rounded()) }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(fps, forKey: .fps)
        try c.encode(p90, forKey: .p90)
        try c.encodeIfPresent(power, forKey: .power)
        try c.encode(theme, forKey: .theme)
        try c.encode(bgMode, forKey: .bgMode)
        try c.encode(backingMP, forKey: .backingMP)
        try c.encode(dpr, forKey: .dpr)
        try c.encode(quality, forKey: .quality)
        try c.encode(fish, forKey: .fish)
    }
}

enum Diagnostics {
    /// Set at process start (main.swift, via FeedbackCenter.start).
    static var launchDate = Date()

    /// System facts + engine stats from the main-screen wallpaper (1 s timeout → engine = null).
    /// Completion on the main thread.
    static func collect(completion: @escaping (DiagnosticsReport) -> Void) {
        let base = system()
        guard let webView = WallpaperProbe.mainWebView() else { completion(base); return }
        WallpaperProbe.engineStats(webView) { dict in
            var r = base
            r.engine = dict.map { EngineStats(dict: $0) }
            completion(r)
        }
    }

    static func system() -> DiagnosticsReport {
        let info = ProcessInfo.processInfo
        let mainID = NSScreen.main.flatMap { displayID($0) }
        let screens: [DiagnosticsReport.Screen] = NSScreen.screens.prefix(8).map { s in
            var maxFps: Int? = nil
            if #available(macOS 12.0, *) { maxFps = s.maximumFramesPerSecond }
            return DiagnosticsReport.Screen(main: mainID != nil && displayID(s) == mainID,
                                            widthPt: Int(s.frame.width.rounded()),
                                            heightPt: Int(s.frame.height.rounded()),
                                            scale: Double(s.backingScaleFactor),
                                            maxFps: maxFps)
        }
        let dark = NSApp.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
        var lowPower = false
        if #available(macOS 12.0, *) { lowPower = info.isLowPowerModeEnabled }
        #if arch(arm64)
        let arch = "arm64"
        #else
        let arch = "x86_64"
        #endif
        let memory = max(1, Int((Double(info.physicalMemory) / 1_073_741_824).rounded()))
        return DiagnosticsReport(
            os: .init(version: osVersion, build: sysctlString("kern.osversion")),
            model: String((sysctlString("hw.model") ?? "unknown").prefix(40)),
            arch: arch,
            rosetta: sysctlInt32("sysctl.proc_translated") == 1,
            memoryGB: memory,
            screens: screens,
            appearance: dark ? "dark" : "light",
            power: .init(onBattery: PowerInfo.isOnBattery, lowPowerMode: lowPower, thermal: thermalName(info.thermalState)),
            launchAtLogin: LoginItem.isEnabled,
            appUptimeSec: max(0, Int(Date().timeIntervalSince(launchDate))),
            language: Locale.preferredLanguages.first.map { String($0.prefix(35)) },
            engine: nil)
    }

    /// "14.6.1" (patch omitted when 0: "15.0").
    static var osVersion: String {
        let v = ProcessInfo.processInfo.operatingSystemVersion
        return v.patchVersion > 0 ? "\(v.majorVersion).\(v.minorVersion).\(v.patchVersion)"
                                  : "\(v.majorVersion).\(v.minorVersion)"
    }

    /// Pretty (window disclosure, local file) or compact (mail body) JSON, keys sorted.
    static func json(_ report: DiagnosticsReport, pretty: Bool) -> String {
        let enc = JSONEncoder()
        enc.outputFormatting = pretty ? [.prettyPrinted, .sortedKeys] : [.sortedKeys]
        guard let data = try? enc.encode(report), let s = String(data: data, encoding: .utf8) else { return "{}" }
        return s
    }

    static func displayID(_ screen: NSScreen) -> UInt32? {
        (screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value
    }

    private static func thermalName(_ s: ProcessInfo.ThermalState) -> String {
        switch s {
        case .nominal: return "nominal"
        case .fair: return "fair"
        case .serious: return "serious"
        case .critical: return "critical"
        @unknown default: return "nominal"
        }
    }

    private static func sysctlString(_ name: String) -> String? {
        var size = 0
        guard sysctlbyname(name, nil, &size, nil, 0) == 0, size > 0 else { return nil }
        var buf = [CChar](repeating: 0, count: size)
        guard sysctlbyname(name, &buf, &size, nil, 0) == 0 else { return nil }
        let bytes = buf.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }
        let s = String(decoding: bytes, as: UTF8.self)
        return s.isEmpty ? nil : s
    }

    private static func sysctlInt32(_ name: String) -> Int32? {
        var value: Int32 = 0
        var size = MemoryLayout<Int32>.size
        guard sysctlbyname(name, &value, &size, nil, 0) == 0 else { return nil }
        return value
    }
}

/// Read-only access to the wallpaper web views for feedback: a snapshot of the aquarium
/// (no Screen Recording permission, no icons/windows/desktop) and engine stats.
/// Finds the views through NSApp.windows, so WallpaperWindow needs no extra API.
enum WallpaperProbe {
    /// Wallpaper web view on NSScreen.main (fallback: the first wallpaper web view).
    static func mainWebView() -> WKWebView? {
        let desktop = Int(CGWindowLevelForKey(.desktopWindow))
        let wallpapers = NSApp.windows.filter { $0.level.rawValue == desktop && $0.contentView is WKWebView }
        let mainID = NSScreen.main.flatMap { Diagnostics.displayID($0) }
        let onMain = wallpapers.first { w in
            guard let id = mainID, let s = w.screen else { return false }
            return Diagnostics.displayID(s) == id
        }
        return (onMain ?? wallpapers.first)?.contentView as? WKWebView
    }

    /// `takeSnapshot` at ≤ `maxWidthPt` points wide; the JPEG step limits the long side to 1600 px.
    static func snapshot(_ webView: WKWebView, maxWidthPt: CGFloat = 1600, completion: @escaping (NSImage?) -> Void) {
        let cfg = WKSnapshotConfiguration()
        let width = webView.bounds.width
        if width > 0 { cfg.snapshotWidth = NSNumber(value: Double(min(maxWidthPt, width))) }
        webView.takeSnapshot(with: cfg) { image, error in
            if let error = error { NSLog("Aquarium feedback: snapshot failed: \(error.localizedDescription)") }
            completion(image)
        }
    }

    private static let statsScript = """
    (() => { try {
      const s = window.__aq && window.__aq.stats && window.__aq.stats(); if (!s) return null;
      return JSON.stringify({ fps: s.governor ? s.governor.fps : null, p90: s.governor ? s.governor.p90 : null,
        power: s.power, theme: s.theme, bgMode: s.bgMode, backingMP: s.backing ? s.backing.mp : null,
        dpr: s.dpr, quality: s.quality, fish: s.fish });
    } catch (e) { return null; } })()
    """

    /// Engine stats as a dictionary, or nil after 1 s / on any error. Completion on the main thread, once.
    static func engineStats(_ webView: WKWebView, timeout: TimeInterval = 1.0,
                            completion: @escaping ([String: Any]?) -> Void) {
        var finished = false
        let finish: ([String: Any]?) -> Void = { result in
            if finished { return }
            finished = true
            completion(result)
        }
        webView.evaluateJavaScript(statsScript) { result, _ in
            guard let s = result as? String, let data = s.data(using: .utf8),
                  let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else { finish(nil); return }
            finish(obj)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + timeout) { finish(nil) }
    }
}
