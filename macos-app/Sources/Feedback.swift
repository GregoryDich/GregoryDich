import Cocoa

// Feedback: strings, config (Info.plist keys), report model, local store,
// delivery chain (endpoint POST → mailto → clipboard) and the retry queue.
// UI lives in FeedbackWindow.swift, system/engine facts in Diagnostics.swift.

// MARK: - User-facing strings (Russian now; EN/HE later)
enum FBText {
    static let menuItem = "Написать отзыв…"
    static let windowTitlePrefix = "Отзыв — "
    static let fallbackAppName = "Морской аквариум"

    static let intro = "Расскажите, что починить или добавить. Каждое сообщение читает разработчик."
    static let topic = "Тема"
    static let categories = ["Ошибка", "Идея", "Хочу рыбку", "Другое"]
    static let fishLabel = "Какую рыбку?"
    static let fishPlaceholder = "например, мандаринка или мой петушок"
    static let messageLabel = "Сообщение"
    static let messagePlaceholder = "Что случилось или чего не хватает?"
    static let minLengthHint = "Минимум 10 символов"
    static let emailLabel = "E-mail для ответа (необязательно)"
    static let emailPlaceholder = "name@example.com"
    static let emailNote = "Только чтобы ответить на этот отзыв. Рассылок не будет без галочки ниже. Можно не указывать."
    static let emailError = "Проверьте адрес e-mail"
    static let marketing = "Хочу в группу первых пользователей: присылайте на этот e-mail короткие опросы и новости о новых рыбках. Адрес храним, пока вы не отпишетесь; отписаться — ответить «отписаться» на любое письмо."
    static let marketingVersion = "fb-marketing-ru-2"  // bump on any wording change
    static let marketingNeedsEmail = "Сначала укажите e-mail выше"

    static let snapshotToggle = "Приложить снимок аквариума"
    static let snapshotTaking = "Делаем снимок…"
    static let snapshotCaption = "Снимается только аквариум — без иконок, окон и вашего стола."
    static let snapshotFailed = "Не удалось сделать снимок"
    static let diagToggle = "Приложить диагностику (без личных данных)"
    static let diagShow = "Показать, что отправится ▸"
    static let diagHide = "Скрыть ▾"
    static let diagCollecting = "Собираем диагностику…"

    static let consent = "Согласен(на) передать разработчику этот отзыв, а также e-mail, снимок и диагностику — если я их указал(а) или включил(а). Данные нужны, чтобы ответить мне и улучшить приложение; хранятся до 24 месяцев. Отправка добровольная."
    static let consentVersion = "fb-consent-ru-1"      // bump on any wording change
    static let privacy = "Политика конфиденциальности"

    static let routeEndpoint = "Отправка: на сервер разработчика. Копия остаётся на этом Mac."
    static func routeMail(_ address: String) -> String {
        "Отправка: откроется письмо в вашей почтовой программе (адрес: \(address)). Копия остаётся на этом Mac."
    }
    static let routeClipboard = "Отправка: текст скопируется в буфер обмена — вставьте его в письмо или чат. Копия остаётся на этом Mac."

    static let cancel = "Отмена"
    static let send = "Отправить"
    static let sending = "Отправляем…"
    static let rateLimited = "Слишком часто. Попробуйте через несколько минут."
    static let needConsent = "Отметьте согласие ниже"
    static let sendShortcut = "⌘↩"

    // Alerts
    static let sentTitle = "Спасибо! Отзыв отправлен."
    static func sentReply(_ email: String) -> String { "Ответим на \(email) в течение нескольких дней." }
    static let pendingTitle = "Нет связи с сервером. Отзыв сохранён и уйдёт автоматически."
    static func rejectedTitle(_ code: Int) -> String { "Сервер не принял отзыв (код \(code))." }
    static let mailOpened = "Открылось письмо — проверьте его и нажмите «Отправить» в почте."
    static func mailFallback(_ address: String) -> String {
        "Если почта не открылась или просит настроить ящик, нажмите «Скопировать текст» и отправьте его на \(address) из своей почты."
    }
    static let pendingNotSaved = "Нет связи с сервером, а сохранить отзыв на этом Mac не удалось."
    static func dragSnapshot(_ id: String) -> String { "Перетащите снимок \(id).jpg из открытой папки в письмо." }
    static let copiedTitle = "Текст отзыва скопирован. Вставьте его (⌘V) в письмо или сообщение разработчику."
    static func copiedSaved(_ path: String) -> String { "Копия сохранена: \(path)" }
    static func attachSnapshot(_ id: String) -> String {
        "Снимок \(id).jpg приложите к сообщению — он рядом с копией («Показать в Finder»)."
    }
    static func developerAddress(_ email: String) -> String { "Адрес разработчика: \(email)" }
    static func saveFailed(_ error: String) -> String { "Не удалось сохранить копию на этом Mac: \(error)" }
    static let sendByMail = "Отправить письмом"
    static let copy = "Скопировать"
    static let copyText = "Скопировать текст"
    static let showInFinder = "Показать в Finder"
    static let done = "Готово"
    static let close = "Закрыть"

    // Mail / clipboard body
    static let mailSubjectPrefix = "[Аквариум]"
    static let clipboardHeader = "Отзыв для «Морского аквариума»"
    static let topicLine = "Тема: "
    static let bodyFish = "Рыбка: "
    static let bodyEmail = "E-mail для ответа: "
    static let bodyMarketing = "Группа первых пользователей: да"
    static let bodyId = "ID отзыва: "
    static let bodyVersion = "Версия: "
    static let bodyDiagnostics = "Диагностика:"
    static func diagnosticsInFile(_ id: String) -> String { "Диагностика сохранена в файле \(id).json" }
}

// MARK: - Limits
enum FBLimit {
    static let messageMin = 10
    static let messageMax = 2000
    static let fishMax = 100
    static let emailMax = 254
    static let sendsPerWindow = 5
    static let rateWindow: TimeInterval = 600            // 5 sends per 10 min
    static let snapshotMaxSide = 1600                    // px, long side
    static let snapshotMaxBytes = 409_600                // 400 KB
    static let postMaxBytes = 1_000_000                  // 1 MB
    static let mailtoMaxBytes = 8000
    static let retryMaxAttempts = 5
    static let pendingMaxAge: TimeInterval = 7 * 86_400
    static let localKeepAge: TimeInterval = 90 * 86_400
    static let localKeepCount = 100
}

// MARK: - Category
enum FBCategory: String, CaseIterable {
    case bug, idea, fishRequest = "fish_request", other

    /// Segment order in the window: «Ошибка», «Идея», «Хочу рыбку», «Другое».
    static let ordered: [FBCategory] = [.bug, .idea, .fishRequest, .other]

    static func from(segment: Int) -> FBCategory? {
        guard segment >= 0, segment < ordered.count else { return nil }
        return ordered[segment]
    }
    var segment: Int { FBCategory.ordered.firstIndex(of: self) ?? 3 }
    var title: String { FBText.categories[segment] }
}

// MARK: - Dates (ISO 8601 UTC)
enum FBDate {
    private static let formatter: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        f.timeZone = TimeZone(secondsFromGMT: 0)
        return f
    }()
    static func string(_ date: Date) -> String { formatter.string(from: date) }
    static func date(_ string: String) -> Date? { formatter.date(from: string) }
}

// MARK: - Validation helpers
enum FBValidate {
    static let emailPattern = #"^[A-Z0-9a-z._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"#

    static func isEmail(_ s: String) -> Bool {
        guard !s.isEmpty, s.count <= FBLimit.emailMax else { return false }
        return s.range(of: emailPattern, options: .regularExpression) != nil
    }

    /// Drops control characters except \n and \t (\r\n and \r become \n).
    static func stripControls(_ s: String) -> String {
        let normalized = s.replacingOccurrences(of: "\r\n", with: "\n").replacingOccurrences(of: "\r", with: "\n")
        var out = String.UnicodeScalarView()
        for u in normalized.unicodeScalars {
            if u == "\n" || u == "\t" { out.append(u); continue }
            if u.properties.generalCategory == .control { continue }
            out.append(u)
        }
        return String(out)
    }

    /// The message as it is stored and sent: controls stripped, trimmed.
    static func cleanMessage(_ s: String) -> String {
        stripControls(s).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// One line, collapsed whitespace, at most `max` characters (with an ellipsis if cut).
    static func oneLine(_ s: String, max: Int) -> String {
        let parts = s.components(separatedBy: .whitespacesAndNewlines).filter { !$0.isEmpty }
        let line = parts.joined(separator: " ")
        return line.count > max ? String(line.prefix(max)) + "…" : line
    }
}

// MARK: - Config (Info.plist), read once when the window opens
struct FeedbackConfig {
    enum Route: String { case endpoint, mailto, clipboard }

    let endpoint: URL?          // AQFeedbackEndpoint, https only
    let email: String?          // AQFeedbackEmail
    let privacyPolicy: URL?     // AQPrivacyPolicyURL, https only

    var route: Route {
        if endpoint != nil { return .endpoint }
        if email != nil { return .mailto }
        return .clipboard
    }

    var routeText: String {
        switch route {
        case .endpoint: return FBText.routeEndpoint
        case .mailto: return FBText.routeMail(email ?? "")
        case .clipboard: return FBText.routeClipboard
        }
    }

    static func load(from bundle: Bundle = .main) -> FeedbackConfig {
        func value(_ key: String) -> String {
            let raw = bundle.object(forInfoDictionaryKey: key) as? String ?? ""
            return raw.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        let rawEndpoint = value("AQFeedbackEndpoint")
        let endpoint = httpsURL(rawEndpoint)
        if !rawEndpoint.isEmpty && endpoint == nil {
            NSLog("Aquarium feedback: AQFeedbackEndpoint ignored (must be https)")
        }
        let rawEmail = value("AQFeedbackEmail")
        let email: String? = FBValidate.isEmail(rawEmail) ? rawEmail : nil
        if !rawEmail.isEmpty && email == nil {
            NSLog("Aquarium feedback: AQFeedbackEmail ignored (not an e-mail address)")
        }
        let privacy = httpsURL(value("AQPrivacyPolicyURL"))
        return FeedbackConfig(endpoint: endpoint, email: email, privacyPolicy: privacy)
    }

    static func httpsURL(_ s: String) -> URL? {
        guard !s.isEmpty, let url = URL(string: s), url.scheme?.lowercased() == "https",
              let host = url.host, !host.isEmpty else { return nil }
        return url
    }
}

// MARK: - Report (schema aq.feedback/1)
struct FeedbackReport: Codable {
    struct Consent: Codable {
        var given: Bool
        var version: String
        var at: String
    }
    /// Separate, optional opt-in to the early-users group (surveys/news). Unchecked by default.
    struct Marketing: Codable {
        var optIn: Bool
        var version: String
        var at: String
    }
    struct AppInfo: Codable {
        var bundleId: String
        var version: String
        var build: String

        static var current: AppInfo {
            let info = Bundle.main.infoDictionary ?? [:]
            return AppInfo(bundleId: Bundle.main.bundleIdentifier ?? "com.gregorydich.aquariumwallpaper",
                           version: info["CFBundleShortVersionString"] as? String ?? "0",
                           build: info["CFBundleVersion"] as? String ?? "0")
        }
    }
    struct Snapshot: Codable {
        var mime: String = "image/jpeg"
        var width: Int
        var height: Int
        var bytes: Int
        var base64: String? = nil      // POST body only
        var file: String? = nil        // local copy only: "<id>.jpg"
    }
    /// LOCAL FILE ONLY — never sent.
    struct Delivery: Codable {
        var route: String              // endpoint | mailto | clipboard
        var status: String             // sent | pending | handed_off | failed
        var attempts: Int
        var lastAttemptAt: String? = nil
        var lastError: String? = nil
        var ticket: String? = nil
    }

    var schema: String = "aq.feedback/1"
    var id: String
    var createdAt: String
    var category: String
    var message: String
    var fishRequest: String?
    var email: String?
    var uiLanguage: String = "ru"
    var consent: Consent
    var marketing: Marketing?
    var app: AppInfo
    var diagnostics: DiagnosticsReport?
    var snapshot: Snapshot?
    var delivery: Delivery?

    enum CodingKeys: String, CodingKey {
        case schema, id, createdAt, category, message, fishRequest, email, uiLanguage
        case consent, marketing, app, diagnostics, snapshot, delivery
    }

    // Explicit nulls for the optional payload fields (as in the schema example); `marketing` and
    // `delivery` only when set, so reports without an opt-in stay valid against the v1 schema.
    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(schema, forKey: .schema)
        try c.encode(id, forKey: .id)
        try c.encode(createdAt, forKey: .createdAt)
        try c.encode(category, forKey: .category)
        try c.encode(message, forKey: .message)
        try c.encode(fishRequest, forKey: .fishRequest)
        try c.encode(email, forKey: .email)
        try c.encode(uiLanguage, forKey: .uiLanguage)
        try c.encode(consent, forKey: .consent)
        try c.encodeIfPresent(marketing, forKey: .marketing)
        try c.encode(app, forKey: .app)
        try c.encode(diagnostics, forKey: .diagnostics)
        try c.encode(snapshot, forKey: .snapshot)
        try c.encodeIfPresent(delivery, forKey: .delivery)
    }

    var categoryValue: FBCategory { FBCategory(rawValue: category) ?? .other }
}

// MARK: - Local store: ~/Library/Application Support/AquariumWallpaper/Feedback/
enum FeedbackStore {
    static func directory() throws -> URL {
        let fm = FileManager.default
        let base = try fm.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let dir = base.appendingPathComponent("AquariumWallpaper", isDirectory: true)
                      .appendingPathComponent("Feedback", isDirectory: true)
        try fm.createDirectory(at: dir, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        try? fm.setAttributes([.posixPermissions: 0o700], ofItemAtPath: dir.path)
        return dir
    }

    static func fileURL(id: String, ext: String) -> URL? {
        guard let dir = try? directory() else { return nil }
        return dir.appendingPathComponent("\(id).\(ext)")
    }

    static func encodeLocal(_ report: FeedbackReport) throws -> Data {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try enc.encode(report)
    }

    /// Writes `<id>.jpg` (if any) and `<id>.json` atomically, 0600.
    static func save(_ report: FeedbackReport, jpeg: Data?) throws {
        let dir = try directory()
        if let jpeg = jpeg {
            try write(jpeg, to: dir.appendingPathComponent("\(report.id).jpg"))
        }
        try write(try encodeLocal(report), to: dir.appendingPathComponent("\(report.id).json"))
    }

    /// Rewrites `<id>.json` (delivery status changes). Errors are logged; false when not written.
    @discardableResult
    static func update(_ report: FeedbackReport) -> Bool {
        do {
            let dir = try directory()
            try write(try encodeLocal(report), to: dir.appendingPathComponent("\(report.id).json"))
            return true
        } catch {
            NSLog("Aquarium feedback: could not update report: \(error.localizedDescription)")
            return false
        }
    }

    static func readFile(named name: String) -> Data? {
        guard isReportFileName(name), let dir = try? directory() else { return nil }
        return try? Data(contentsOf: dir.appendingPathComponent(name))
    }

    /// The current local copy of one report (small JSON; the snapshot lives in `<id>.jpg`).
    static func load(id: String) -> FeedbackReport? {
        guard let data = readFile(named: "\(id).json") else { return nil }
        return try? JSONDecoder().decode(FeedbackReport.self, from: data)
    }

    /// All decodable reports (call off the main thread).
    static func loadAll() -> [FeedbackReport] {
        guard let dir = try? directory(),
              let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil,
                                                                        options: [.skipsHiddenFiles]) else { return [] }
        let dec = JSONDecoder()
        var out: [FeedbackReport] = []
        for url in files where url.pathExtension == "json" && isReportFileName(url.lastPathComponent) {
            if let data = try? Data(contentsOf: url), let r = try? dec.decode(FeedbackReport.self, from: data) {
                out.append(r)
            }
        }
        return out
    }

    /// At launch (utility queue): drop sent/handed_off older than 90 days, keep at most 100 newest.
    static func applyRetention(now: Date = Date()) {
        let fm = FileManager.default
        guard let dir = try? directory(),
              let files = try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.contentModificationDateKey],
                                                      options: [.skipsHiddenFiles]) else { return }
        struct Entry { let id: String; let date: Date; let status: String? }
        let dec = JSONDecoder()
        var entries: [Entry] = []
        for url in files where url.pathExtension == "json" && isReportFileName(url.lastPathComponent) {
            let id = url.deletingPathExtension().lastPathComponent
            var date = (try? url.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? now
            var status: String? = nil
            if let data = try? Data(contentsOf: url), let r = try? dec.decode(FeedbackReport.self, from: data) {
                if let created = FBDate.date(r.createdAt) { date = created }
                status = r.delivery?.status
            }
            entries.append(Entry(id: id, date: date, status: status))
        }
        var remove = Set<String>()
        for e in entries where (e.status == "sent" || e.status == "handed_off")
                              && now.timeIntervalSince(e.date) > FBLimit.localKeepAge {
            remove.insert(e.id)
        }
        let kept = entries.filter { !remove.contains($0.id) }.sorted { $0.date > $1.date }
        if kept.count > FBLimit.localKeepCount {
            for e in kept[FBLimit.localKeepCount...] { remove.insert(e.id) }
        }
        for id in remove {
            for ext in ["json", "jpg"] { try? fm.removeItem(at: dir.appendingPathComponent("\(id).\(ext)")) }
        }
    }

    private static func write(_ data: Data, to url: URL) throws {
        try data.write(to: url, options: [.atomic])
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
    }

    /// "<uuid>.json" / "<uuid>.jpg" only — never touch other files.
    private static func isReportFileName(_ name: String) -> Bool {
        name.range(of: #"^[0-9a-f-]{36}\.(json|jpg)$"#, options: .regularExpression) != nil
    }
}

// MARK: - Send-rate limit: at most 5 sends per 10 minutes
enum FeedbackRateLimit {
    private static let key = "AQFeedbackSendTimes"

    private static func recent(now: Date = Date()) -> [Double] {
        let all = UserDefaults.standard.array(forKey: key) as? [Double] ?? []
        let t = now.timeIntervalSince1970
        return all.filter { t - $0 >= 0 && t - $0 < FBLimit.rateWindow }
    }
    static var isLimited: Bool { recent().count >= FBLimit.sendsPerWindow }
    static func record() {
        var times = recent()
        times.append(Date().timeIntervalSince1970)
        UserDefaults.standard.set(times, forKey: key)
    }
}

// MARK: - Draft (UserDefaults)
enum FeedbackDraft {
    struct Draft {
        var category: String
        var message: String
        var email: String
        var fish: String
    }
    private static let key = "AQFeedbackDraft"
    private static let lastEmailKey = "AQFeedbackLastEmail"

    static func load() -> Draft? {
        guard let d = UserDefaults.standard.dictionary(forKey: key) as? [String: String] else { return nil }
        return Draft(category: d["category"] ?? "", message: d["message"] ?? "",
                     email: d["email"] ?? "", fish: d["fish"] ?? "")
    }
    static func save(_ d: Draft) {
        if d.category.isEmpty && d.message.isEmpty && d.email.isEmpty && d.fish.isEmpty { clear(); return }
        UserDefaults.standard.set(["category": d.category, "message": d.message, "email": d.email, "fish": d.fish],
                                  forKey: key)
    }
    static func clear() { UserDefaults.standard.removeObject(forKey: key) }

    /// Remembered after a send with an e-mail; a send without one forgets it.
    static var lastEmail: String? {
        get { UserDefaults.standard.string(forKey: lastEmailKey) }
        set {
            let v = newValue?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if v.isEmpty {
                UserDefaults.standard.removeObject(forKey: lastEmailKey)
            } else if FBValidate.isEmail(v) {
                UserDefaults.standard.set(v, forKey: lastEmailKey)
            }
        }
    }
}

// MARK: - Snapshot JPEG (≤ 1600 px long side, ≤ 400 KB)
enum SnapshotEncoder {
    struct Result { let data: Data; let width: Int; let height: Int }

    /// Thread-safe (CoreGraphics only): call off the main thread.
    static func jpeg(from image: CGImage) -> Result? {
        for side in [FBLimit.snapshotMaxSide, 1280] {
            guard let scaled = scale(image, maxLongSide: side) else { continue }
            let rep = NSBitmapImageRep(cgImage: scaled)
            for quality in [0.7, 0.55, 0.4] {
                if let data = rep.representation(using: .jpeg, properties: [.compressionFactor: NSNumber(value: quality)]),
                   data.count <= FBLimit.snapshotMaxBytes {
                    return Result(data: data, width: scaled.width, height: scaled.height)
                }
            }
        }
        return nil
    }

    private static func scale(_ src: CGImage, maxLongSide: Int) -> CGImage? {
        let w = src.width, h = src.height
        guard w > 0, h > 0 else { return nil }
        let k = min(1.0, Double(maxLongSide) / Double(max(w, h)))
        let tw = max(1, Int((Double(w) * k).rounded())), th = max(1, Int((Double(h) * k).rounded()))
        let space = CGColorSpace(name: CGColorSpace.sRGB) ?? CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(data: nil, width: tw, height: th, bitsPerComponent: 8, bytesPerRow: 0,
                                  space: space, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue) else { return nil }
        ctx.interpolationQuality = .high
        ctx.draw(src, in: CGRect(x: 0, y: 0, width: tw, height: th))
        return ctx.makeImage()
    }
}

// MARK: - Delivery: endpoint POST → mailto → clipboard, plus the retry queue
enum FeedbackDelivery {
    enum PostOutcome {
        case sent(ticket: String?)
        case retryLater(String)        // 429, 5xx, offline/timeout → stays pending
        case rejected(Int)             // any other status → failed
    }

    private static let session = URLSession(configuration: .ephemeral)
    private static var retrying = false
    /// Report ids with a POST under way (main thread only), so the retry queue never resends
    /// a report the window is still posting.
    private static var inFlight = Set<String>()

    // MARK: POST (call on the main thread; the completion runs on the main thread)
    static func post(_ report: FeedbackReport, jpeg: Data?, to endpoint: URL,
                     completion: @escaping (PostOutcome) -> Void) {
        let id = report.id
        inFlight.insert(id)
        let finish: (PostOutcome) -> Void = { outcome in
            inFlight.remove(id)
            completion(outcome)
        }
        request(report, jpeg: jpeg, endpoint: endpoint) { status, data, error in
            if status == 413, jpeg != nil, report.snapshot != nil {
                // Too large: resend once without the snapshot.
                request(report, jpeg: nil, endpoint: endpoint) { s2, d2, e2 in
                    finish(classify(status: s2, data: d2, error: e2))
                }
            } else {
                finish(classify(status: status, data: data, error: error))
            }
        }
    }

    /// The JSON that leaves the Mac: no `delivery`, snapshot as base64 (no local file name).
    static func payloadData(_ report: FeedbackReport, jpeg: Data?) -> Data? {
        var p = report
        p.delivery = nil
        if var s = p.snapshot, let jpeg = jpeg {
            s.base64 = jpeg.base64EncodedString()
            s.file = nil
            p.snapshot = s
        } else {
            p.snapshot = nil
        }
        let enc = JSONEncoder()
        enc.outputFormatting = [.sortedKeys]
        guard var data = try? enc.encode(p) else { return nil }
        if data.count > FBLimit.postMaxBytes && p.snapshot != nil {
            p.snapshot = nil
            if let smaller = try? enc.encode(p) { data = smaller }
        }
        return data
    }

    private static func request(_ report: FeedbackReport, jpeg: Data?, endpoint: URL,
                                done: @escaping (Int?, Data?, Error?) -> Void) {
        guard let body = payloadData(report, jpeg: jpeg) else {
            DispatchQueue.main.async { done(-1, nil, nil) }
            return
        }
        var req = URLRequest(url: endpoint, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
        req.httpMethod = "POST"
        req.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("AquariumWallpaper/\(report.app.version) (macOS \(Diagnostics.osVersion))",
                     forHTTPHeaderField: "User-Agent")
        req.setValue(report.schema, forHTTPHeaderField: "X-AQ-Schema")
        req.httpBody = body
        session.dataTask(with: req) { data, response, error in
            let status = (response as? HTTPURLResponse)?.statusCode
            DispatchQueue.main.async { done(status, data, error) }
        }.resume()
    }

    private static func classify(status: Int?, data: Data?, error: Error?) -> PostOutcome {
        if let error = error {
            if let u = error as? URLError { return .retryLater("URLError \(u.code.rawValue)") }
            return .retryLater("network error")
        }
        guard let s = status else { return .retryLater("no response") }
        switch s {
        case 200..<300: return .sent(ticket: ticket(from: data))
        case 429, 500..<600: return .retryLater("HTTP \(s)")
        default: return .rejected(s)
        }
    }

    private static func ticket(from data: Data?) -> String? {
        guard let data = data,
              let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              let t = obj["ticket"] as? String, !t.isEmpty else { return nil }
        return String(t.prefix(40))
    }

    // MARK: mailto / clipboard text
    static func subject(for r: FeedbackReport) -> String {
        "\(FBText.mailSubjectPrefix) \(r.categoryValue.title): \(FBValidate.oneLine(r.message, max: 50))"
    }

    static func body(for r: FeedbackReport, includeDiagnostics: Bool) -> String {
        var lines = [r.message, "", "—"]
        if let fish = r.fishRequest { lines.append(FBText.bodyFish + fish) }
        if let email = r.email { lines.append(FBText.bodyEmail + email) }
        if r.marketing?.optIn == true { lines.append(FBText.bodyMarketing) }
        lines.append(FBText.bodyId + r.id)
        var version = FBText.bodyVersion + "\(r.app.version) (\(r.app.build)), macOS "
        version += r.diagnostics?.os.version ?? Diagnostics.osVersion
        if let d = r.diagnostics { version += ", \(d.model)" }
        lines.append(version)
        if let d = r.diagnostics {
            if includeDiagnostics {
                lines.append(FBText.bodyDiagnostics)
                lines.append(Diagnostics.json(d, pretty: false))
            } else {
                lines.append(FBText.diagnosticsInFile(r.id))
            }
        }
        return lines.joined(separator: "\n")
    }

    static func clipboardText(for r: FeedbackReport) -> String {
        [FBText.clipboardHeader, FBText.topicLine + r.categoryValue.title, "", body(for: r, includeDiagnostics: true)]
            .joined(separator: "\n")
    }

    static func mailtoURL(for r: FeedbackReport, to address: String) -> URL? {
        func build(_ withDiagnostics: Bool) -> URL? {
            let text = body(for: r, includeDiagnostics: withDiagnostics).replacingOccurrences(of: "\n", with: "\r\n")
            let s = "mailto:" + encode(address, keeping: "@")
                  + "?subject=" + encode(subject(for: r)) + "&body=" + encode(text)
            return URL(string: s)
        }
        guard let full = build(true) else { return build(false) }
        if r.diagnostics != nil && full.absoluteString.utf8.count > FBLimit.mailtoMaxBytes { return build(false) }
        return full
    }

    /// Strict percent-encoding (RFC 3986 unreserved only), so "+", "&", "=" survive in mail clients.
    private static func encode(_ s: String, keeping extra: String = "") -> String {
        var allowed = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")
        allowed.insert(charactersIn: extra)
        return s.addingPercentEncoding(withAllowedCharacters: allowed) ?? ""
    }

    // MARK: Retry queue (10 s after launch, then hourly; silent)
    static func retryPending() {
        guard !retrying else { return }
        guard let endpoint = FeedbackConfig.load().endpoint else { return }   // key removed → leave pending
        retrying = true
        DispatchQueue.global(qos: .utility).async {
            let queue = FeedbackStore.loadAll().filter {
                $0.delivery?.route == FeedbackConfig.Route.endpoint.rawValue && $0.delivery?.status == "pending"
            }
            DispatchQueue.main.async {
                retryNext(ArraySlice(queue.filter { !inFlight.contains($0.id) }), endpoint: endpoint)
            }
        }
    }

    private static func retryNext(_ queue: ArraySlice<FeedbackReport>, endpoint: URL) {
        guard let queued = queue.first else { retrying = false; return }
        let rest = queue.dropFirst()
        // The list was read earlier: skip a report that is being posted now, and re-read the file,
        // since the window may have sent it (or a previous pass updated it) in the meantime.
        guard !inFlight.contains(queued.id), var report = FeedbackStore.load(id: queued.id),
              report.delivery?.route == FeedbackConfig.Route.endpoint.rawValue,
              report.delivery?.status == "pending" else {
            retryNext(rest, endpoint: endpoint)
            return
        }
        var d = report.delivery ?? FeedbackReport.Delivery(route: FeedbackConfig.Route.endpoint.rawValue,
                                                           status: "pending", attempts: 0)
        let age = FBDate.date(report.createdAt).map { Date().timeIntervalSince($0) } ?? 0
        if age > FBLimit.pendingMaxAge || d.attempts >= FBLimit.retryMaxAttempts {
            d.status = "failed"
            report.delivery = d
            FeedbackStore.update(report)
            retryNext(rest, endpoint: endpoint)
            return
        }
        let jpeg = report.snapshot?.file.flatMap { FeedbackStore.readFile(named: $0) }
        post(report, jpeg: jpeg, to: endpoint) { outcome in
            d.attempts += 1
            d.lastAttemptAt = FBDate.string(Date())
            switch outcome {
            case .sent(let ticket):
                d.status = "sent"; d.ticket = ticket; d.lastError = nil
            case .retryLater(let reason):
                d.lastError = String(reason.prefix(200))
                if d.attempts >= FBLimit.retryMaxAttempts { d.status = "failed" }
            case .rejected(let code):
                d.status = "failed"; d.lastError = "HTTP \(code)"
            }
            report.delivery = d
            FeedbackStore.update(report)
            retryNext(rest, endpoint: endpoint)
        }
    }
}
