import Cocoa

// R12: is a display hidden behind a full-screen or maximised window? The fallback for NSWindow occlusion, which
// cannot see it: a maximised window leaves the strip under the (translucent) menu bar and the Dock uncovered, so
// the desktop-level wallpaper window stays `.visible` by definition (any visible part counts), and other live-wallpaper
// apps report that the occlusion notification is not reliable for a desktop-level window behind a full-screen app.
// Reads the window list (CGWindowListCopyWindowInfo: bounds, layer, alpha, owner PID — never titles or owner names,
// no Screen Recording permission, no prompt) on events (Space switch, app activation, occlusion change, screen
// change) and on a slow poll, at most once a second; never per frame.

/// The pure part (geometry and hysteresis), apart from AppKit so it can be tested anywhere.
enum Coverage {
    struct Window {
        var bounds: CGRect                               // CG global coordinates (top-left of the main display, y down)
        var layer: Int
        var alpha: Double
        var pid: Int32
    }
    struct Display {
        var id: CGDirectDisplayID
        var area: CGRect                                 // visibleFrame (no menu bar, no Dock), CG global coordinates
    }

    /// One window over at least this share of a display's usable area → covered. macOS 15 tiling «Fill» leaves
    /// margins (≈ 97 % of the area); a big window that still shows a band of the aquarium stays below.
    static let threshold = 0.95
    static let minAlpha = 0.9

    /// A Cocoa screen rect (origin bottom-left of the main display, y up) in CG global coordinates (origin top-left
    /// of the main display, y down), the window list's. `top`: the main display's frame.maxY.
    static func cgRect(_ r: CGRect, top: CGFloat) -> CGRect {
        CGRect(x: r.minX, y: top - r.maxY, width: r.width, height: r.height)
    }

    /// For each display: the largest share (0…1) of its usable area under one counting window. Counting: layer 0 (app
    /// windows — not the Dock's display-sized layer-20 surface, menus, panels, overlays, the desktop and its icons),
    /// nearly opaque, another process, a regular app (one with a Dock icon: no agents' invisible overlays).
    static func shares(displays: [Display], windows: [Window], ownPID: Int32,
                       regularPIDs: Set<Int32>) -> [CGDirectDisplayID: Double] {
        let counted = windows.filter {
            $0.layer == 0 && $0.alpha >= minAlpha && $0.pid != ownPID && regularPIDs.contains($0.pid)
        }
        var out: [CGDirectDisplayID: Double] = [:]
        for d in displays {
            let area = Double(d.area.width * d.area.height)
            var best = 0.0
            if area > 0 {
                for w in counted {
                    let i = w.bounds.intersection(d.area)
                    if i.isNull || i.isEmpty { continue }
                    best = max(best, Double(i.width * i.height) / area)
                }
            }
            out[d.id] = min(1, best)
        }
        return out
    }

    /// Hysteresis: a display becomes covered on its second hit in a row (the checks are ≥ 1 s apart: no pause in the
    /// middle of a Space swipe or while a window is being dragged over the screen) and stops being covered on the
    /// first miss (the aquarium resumes at once).
    static func step(covered: Set<CGDirectDisplayID>, pending: Set<CGDirectDisplayID>,
                     hits: Set<CGDirectDisplayID>) -> (covered: Set<CGDirectDisplayID>, pending: Set<CGDirectDisplayID>) {
        let now = hits.intersection(covered.union(pending))
        return (now, hits.subtracting(now))
    }
}

/// Which displays a full-screen or maximised window covers (`covered`), kept up to date while `active` (pages shown,
/// displays awake). Every check also calls `onCheck`: AppDelegate re-reads each window's occlusion state then (a lost
/// "visible again" notification must not keep a page paused) and re-applies the pauses.
/// Main thread only, like AppDelegate that owns it (checks run via perform(…afterDelay:) on the main run loop).
/// Deliberately NOT `@MainActor`: with the real macOS SDK AppDelegate is not actor-isolated in Swift 5 mode, and its
/// synchronous calls into a `@MainActor` class are hard errors on Apple's compiler (owner's build, 22.10).
final class CoverageMonitor: NSObject {
    static let minInterval: TimeInterval = 1         // never two window-list reads closer than this
    static let confirmAfter: TimeInterval = 1        // the second look at a new hit
    static let coveredPoll: TimeInterval = 2         // something is covered: un-maximised → resumes within ≈ 2 s
    static let idlePoll: TimeInterval = 3            // a window maximised with no app or Space change

    var onCheck: (() -> Void)?
    /// false (`aq.fullscreenCheck` NO): the window list is not read, nothing counts as covered; the poll still runs.
    var windowListEnabled = true
    private(set) var covered: Set<CGDirectDisplayID> = []
    private var pending: Set<CGDirectDisplayID> = []
    private(set) var active = false
    private var lastCheck: TimeInterval?             // systemUptime of the last check
    private var dueAt: TimeInterval?                 // systemUptime the scheduled check is due at
    private var checks = 0
    private var lastMs = 0.0
    private var maxMs = 0.0
    private var lastShares: [CGDirectDisplayID: Double] = [:]

    private static var uptime: TimeInterval { ProcessInfo.processInfo.systemUptime }

    /// Off while the displays sleep, the layers test is open or no page is shown. `covered` is kept meanwhile: a page
    /// paused behind a full-screen app before the displays slept stays paused on wake until a check says otherwise.
    func setActive(_ on: Bool) {
        guard on != active else { return }
        active = on
        if on {
            request(after: 0.3)
        } else {
            NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(check), object: nil)
            dueAt = nil
            pending = []
        }
    }

    /// Something may have changed what covers the displays (a Space switch, an app activated, an occlusion change,
    /// screens): a check in `delay`, but never within `minInterval` of the last one; a check already due sooner stays.
    func request(after delay: TimeInterval = 0.3) {
        guard active else { return }
        let now = CoverageMonitor.uptime
        var at = now + max(0, delay)
        if let last = lastCheck { at = max(at, last + CoverageMonitor.minInterval) }
        if let due = dueAt, due <= at { return }
        NSObject.cancelPreviousPerformRequests(withTarget: self, selector: #selector(check), object: nil)
        dueAt = at
        // .common: also while a menu or an alert is open.
        perform(#selector(check), with: nil, afterDelay: at - now, inModes: [.common])
    }

    /// The display's wallpaper window became visible again (occlusion): its verdict is dropped now, so the page
    /// resumes at once; the next check decides afresh (two hits again before a new pause).
    func forget(_ id: CGDirectDisplayID) {
        guard covered.contains(id) || pending.contains(id) else { return }
        covered.remove(id)
        pending.remove(id)
        Log.info("display \(id): visible again — full-screen verdict dropped until the next check")
    }

    @objc private func check() {
        dueAt = nil
        guard active else { return }
        let start = CoverageMonitor.uptime
        let shares = measure()
        let end = CoverageMonitor.uptime
        lastCheck = end
        checks += 1
        lastMs = (end - start) * 1000
        maxMs = max(maxMs, lastMs)
        lastShares = shares
        let hits = Set(shares.compactMap { $0.value >= Coverage.threshold ? $0.key : nil })
        let next = Coverage.step(covered: covered, pending: pending, hits: hits)
        for id in next.covered.subtracting(covered).sorted() {
            Log.info("display \(id): covered by a full-screen or maximised window " +
                     "(\(Int(((shares[id] ?? 0) * 100).rounded())) % of the screen)")
        }
        for id in covered.subtracting(next.covered).sorted() {
            Log.info("display \(id): no full-screen or maximised window any more")
        }
        covered = next.covered
        pending = next.pending
        request(after: !pending.isEmpty ? CoverageMonitor.confirmAfter
                     : !covered.isEmpty ? CoverageMonitor.coveredPoll : CoverageMonitor.idlePoll)
        onCheck?()
    }

    /// Share of each display's usable area under its biggest counting window (all 0 when the window list is off).
    private func measure() -> [CGDirectDisplayID: Double] {
        let screens = NSScreen.screens
        guard let top = screens.first?.frame.maxY else { return [:] }   // the main display's top edge: CG y = 0
        var displays: [Coverage.Display] = []
        for s in screens {
            guard let id = Diagnostics.displayID(s) else { continue }
            displays.append(Coverage.Display(id: id, area: Coverage.cgRect(s.visibleFrame, top: top)))
        }
        guard windowListEnabled else {
            var none: [CGDirectDisplayID: Double] = [:]
            for d in displays { none[d.id] = 0 }
            return none
        }
        let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID)
            as? [[String: Any]] ?? []
        let windows: [Coverage.Window] = list.compactMap { w in
            guard let layer = (w[kCGWindowLayer as String] as? NSNumber)?.intValue,
                  let pid = (w[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value,
                  let b = w[kCGWindowBounds as String] as? NSDictionary,
                  let bounds = CGRect(dictionaryRepresentation: b as CFDictionary) else { return nil }
            let alpha = (w[kCGWindowAlpha as String] as? NSNumber)?.doubleValue ?? 1
            return Coverage.Window(bounds: bounds, layer: layer, alpha: alpha, pid: pid)
        }
        var regular = Set<Int32>()
        for app in NSWorkspace.shared.runningApplications where app.activationPolicy == .regular {
            regular.insert(app.processIdentifier)
        }
        return Coverage.shares(displays: displays, windows: windows,
                               ownPID: ProcessInfo.processInfo.processIdentifier, regularPIDs: regular)
    }

    /// For «Скопировать диагностику» (`host.coverage`): shares and timings only — no window or app names.
    func snapshot() -> [String: Any] {
        var shares: [String: Double] = [:]
        for (id, s) in lastShares { shares[String(id)] = (s * 1000).rounded() / 1000 }
        var d: [String: Any] = [
            "active": active, "windowList": windowListEnabled, "checks": checks,
            "lastCheckMs": (lastMs * 10).rounded() / 10, "maxCheckMs": (maxMs * 10).rounded() / 10,
            "covered": covered.sorted().map { Int($0) }, "pending": pending.sorted().map { Int($0) },
            "share": shares,
        ]
        if let last = lastCheck { d["lastCheckAgoSec"] = Int(CoverageMonitor.uptime - last) }
        return d
    }
}
