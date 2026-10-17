# Окно обратной связи — спецификация v1 / Feedback window — implementation spec v1

**RU, кратко.** Пункт меню «Написать отзыв…» открывает обычное окно AppKit, не панель на обоях. В окне: тема, текст (единственное обязательное поле), необязательный e-mail, снимок аквариума и диагностика (обе — переключателями, точный JSON виден до отправки) и галочка согласия, по умолчанию снятая. По кнопке «Отправить» отзыв **всегда** сохраняется в `~/Library/Application Support/AquariumWallpaper/Feedback/`. Дальше: если задан `AQFeedbackEndpoint` (https) → POST; иначе если задан `AQFeedbackEmail` → `mailto:`; иначе → текст в буфер обмена и путь к файлу. Интерфейс на русском. Сторонних зависимостей нет. macOS 13+. Песочницы нет. Оценка: 2–3 дня агента.

Target: `macos-app/` (Swift, AppKit, built by `build.sh` with plain `swiftc`; `Sources/*.swift` is already globbed and Cocoa/WebKit are already linked, so `build.sh` needs no change). macOS 13.0+. No SwiftUI required. No third-party code. All user-facing strings live in one `enum FBText` (Russian now; EN/HE later).

---

## 0. Files

| File | Content |
|---|---|
| `Sources/Feedback.swift` | `FeedbackReport: Codable`, `FeedbackConfig` (Info.plist keys), `FeedbackStore` (save, list, retention), `FeedbackDelivery` (endpoint → mailto → clipboard, retry queue) |
| `Sources/FeedbackWindow.swift` | `FeedbackWindowController`: UI, validation, draft |
| `Sources/Diagnostics.swift` | `Diagnostics.collect(webView:completion:)`. Shared with P1's planned «Скопировать диагностику»; implement once |
| `Sources/WallpaperWindow.swift` | add `var screen: NSScreen`, `func snapshot(maxPixels: Int, completion: @escaping (NSImage?) -> Void)`, `func engineStats(completion: @escaping ([String: Any]?) -> Void)` |
| `Sources/AppDelegate.swift` | menu item, `launchDate`, retry timer, accessor for the main-screen wallpaper window |
| `Resources/Info.plist` | three new keys (§1) |

## 1. Info.plist keys / Ключи

| Key | Type | Repo default | Meaning |
|---|---|---|---|
| `AQFeedbackEndpoint` | String | `""` | HTTPS URL. If non-empty and valid → POST |
| `AQFeedbackEmail` | String | `support@tonamorph.com` (test builds; owner decision 17.10) | `mailto:` target |
| `AQPrivacyPolicyURL` | String | `""` | HTTPS URL. If non-empty → link under the consent checkbox |

Reading rules:
- Trim whitespace.
- The endpoint is valid only if `URL(string:)` is non-nil, `scheme?.lowercased() == "https"` and `host` is non-empty. Otherwise treat it as empty and log `NSLog("Aquarium feedback: AQFeedbackEndpoint ignored (must be https)")`.
- The email key is valid only if it matches the email regex in §4.
- Read the keys once when the window opens; the route line (§3, item 10) reflects them.

## 2. Menu / Меню

In `setupStatusItem()` the new order is:
1. «Написать отзыв…» → `@objc openFeedback()`, keyEquivalent `""`, `target = self`
2. separator
3. «Запускать при входе» (unchanged)
4. separator
5. «Выход»

When R23 ships, «Мой аквариум…» goes above item 1.

Behaviour:
- Single instance: if the window exists, bring it front.
- The app is an accessory app, so activate it explicitly:

```swift
if #available(macOS 14.0, *) { NSApp.activate() } else { NSApp.activate(ignoringOtherApps: true) }
window.makeKeyAndOrderFront(nil)
```

The wallpaper windows are untouched and stay `ignoresMouseEvents = true` at desktop level. Nothing is drawn on the wallpaper.

## 3. Window layout / Окно

- `NSWindow(contentRect: NSRect(x: 0, y: 0, width: 480, height: 620), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)`.
- `title = "Отзыв — " + CFBundleDisplayName`, which currently gives «Отзыв — Морской аквариум».
- `isReleasedWhenClosed = false`, `center()` on the first open, `setFrameAutosaveName("AQFeedback")`, normal window level.
- Root view: vertical `NSStackView`, edge insets 20, spacing 12, alignment `.leading`, row width 440. Hidden rows collapse (`detachesHiddenViews = true`).
- Light and dark mode come from system colours; no custom colours except `.systemRed` for errors.

Controls from top to bottom (strings are exact):

1. **Intro** (`.secondaryLabelColor`, 12 pt): «Расскажите, что починить или добавить. Каждое сообщение читает разработчик.»
2. **«Тема»** + `NSSegmentedControl(labels: ["Ошибка", "Идея", "Хочу рыбку", "Другое"], trackingMode: .selectOne, target:, action:)`.
   - Start with `selectedSegment = -1` (nothing selected).
   - Mapping: `bug`, `idea`, `fish_request`, `other`. Nothing selected at send time → `other`.
3. **Only for «Хочу рыбку»:** «Какую рыбку?» + `NSTextField`, placeholder «например, мандаринка или мой петушок», max 100 characters.
4. **«Сообщение»** + `NSTextView` in an `NSScrollView`, height 140.
   - `isRichText = false`, `allowsUndo = true`, system font 13, wraps.
   - Placeholder overlay label «Что случилось или чего не хватает?», visible while the text is empty.
   - Under it, right-aligned: counter «N / 2000» (secondary). It turns red with the hint «Минимум 10 символов» when 0 < trimmed length < 10.
5. **«E-mail для ответа (необязательно)»** + `NSTextField`, placeholder «name@example.com».
   - Note under it (secondary, 11 pt): «Только чтобы ответить на этот отзыв. Рассылок не будет. Можно не указывать.»
   - Inline error (`.systemRed`): «Проверьте адрес e-mail».
6. **Checkbox «Приложить снимок аквариума»** — default **OFF**.
   - ON → take the snapshot asynchronously (§6), then show a thumbnail `NSImageView` 192×108 (aspect-fit, corner radius 6) with the caption «Снимается только аквариум — без иконок, окон и вашего стола.»
   - On failure → uncheck, caption «Не удалось сделать снимок».
7. **Checkbox «Приложить диагностику (без личных данных)»** — default OFF.
   - It switches ON automatically when the user selects «Ошибка», unless the user has already clicked this checkbox in this window.
   - Below it, a link-style button «Показать, что отправится ▸» / «Скрыть ▾» toggles a read-only, selectable, monospaced `NSTextView` (11 pt, height 160, scrollable) with the pretty-printed `diagnostics` JSON.
   - The shown object is **the same instance** that is sent. Collect it when the window opens; re-collect when the toggle goes ON.
8. Separator (`NSBox`, `.separator`).
9. **Consent row** — **unchecked by default**:
   - a checkbox with an empty title and next to it `NSTextField(wrappingLabelWithString:)` (preferredMaxLayoutWidth 410); an `NSClickGestureRecognizer` on the label toggles the checkbox;
   - the checkbox's `setAccessibilityLabel` is the full text below.

   > «Согласен(на) передать разработчику этот отзыв, а также e-mail, снимок и диагностику — если я их указал(а) или включил(а). Данные нужны, чтобы ответить мне и улучшить приложение; хранятся до 24 месяцев. Отправка добровольная.»

   - If `AQPrivacyPolicyURL` is valid, show a borderless link button «Политика конфиденциальности» underneath; it opens the URL via `NSWorkspace.shared.open`.
   - `consent.version = "fb-consent-ru-1"`. Bump the version on any wording change.
10. **Route line** (secondary, 11 pt), chosen by the config:
    - endpoint: «Отправка: на сервер разработчика. Копия остаётся на этом Mac.»
    - email: «Отправка: откроется письмо в вашей почтовой программе (адрес: <email>). Копия остаётся на этом Mac.»
    - neither: «Отправка: текст скопируется в буфер обмена — вставьте его в письмо или чат. Копия остаётся на этом Mac.»
11. **Buttons**, bottom-right:
    - «Отмена»: `keyEquivalent = "\u{1b}"`; closes the window and keeps the draft.
    - «Отправить»: `keyEquivalent = "\r"`, `keyEquivalentModifierMask = [.command]`, so ⌘↩ sends while a plain Return still inserts a newline.
    - While sending: «Отправить» is disabled, a small `NSProgressIndicator` spins and the text reads «Отправляем…».

**«Отправить» is enabled only when all of these hold:**
- the trimmed message is 10–2000 characters;
- the email is empty or valid;
- the fish field is ≤ 100 characters;
- consent is checked;
- the user is not rate-limited;
- nothing is being sent right now.

Accessibility: every control has a label; the Tab order follows the visual order; VoiceOver reads the counter and error labels.

## 4. Validation / Проверки

- **message:**
  - trim whitespace and newlines, count with `String.count`;
  - hard cap of 2000 while typing: `textView(_:shouldChangeTextIn:replacementString:)` rejects anything that would exceed it, and a paste is truncated to fit;
  - strip control characters except `\n` and `\t`.
- **email:**
  - trim; at most 254 characters;
  - regex `^[A-Z0-9a-z._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$`;
  - stored as typed.
- **fishRequest:** trim, at most 100 characters; `null` unless the category is `fish_request`.
- **Rate limit:** at most 5 sends per 10 minutes. Timestamps are kept in UserDefaults `AQFeedbackSendTimes`. When exceeded, show «Слишком часто. Попробуйте через несколько минут.»
- **Draft:**
  - `{category, message, email, fish}` is saved to UserDefaults `AQFeedbackDraft`, debounced 0.5 s after each edit;
  - it is restored when the window opens and cleared after a successful handoff (§8);
  - the last valid email is kept in `AQFeedbackLastEmail` and pre-filled.

## 5. Diagnostics / Диагностика

Diagnostics are attached only when their toggle is ON. Only public APIs are used and no permission prompts appear.

| Field | Source |
|---|---|
| `os.version` | `ProcessInfo.processInfo.operatingSystemVersion` → "14.6.1" |
| `os.build` | `sysctlbyname("kern.osversion")` → "23G93" |
| `model` | `sysctlbyname("hw.model")` → "Mac15,6" |
| `arch` | `#if arch(arm64) "arm64" #else "x86_64" #endif` |
| `rosetta` | `sysctlbyname("sysctl.proc_translated") == 1` |
| `memoryGB` | `physicalMemory / 1_073_741_824`, rounded |
| `screens[]` | `NSScreen.screens`, read fresh, never cached: `main`, `widthPt`, `heightPt`, `scale` (`backingScaleFactor`), `maxFps` (`maximumFramesPerSecond`, macOS 12+) |
| `appearance` | `NSApp.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua])` → "dark" / "light" |
| `power.onBattery` | existing `PowerInfo.isOnBattery` |
| `power.lowPowerMode` | `ProcessInfo.processInfo.isLowPowerModeEnabled` |
| `power.thermal` | `thermalState` → "nominal" / "fair" / "serious" / "critical" |
| `launchAtLogin` | `LoginItem.isEnabled` |
| `appUptimeSec` | now − `AppDelegate.launchDate` |
| `language` | `Locale.preferredLanguages.first` |
| `engine` | main-screen web view, 1.0 s timeout, otherwise `null`; script below |

```js
(() => { try {
  const s = window.__aq && window.__aq.stats && window.__aq.stats(); if (!s) return null;
  return JSON.stringify({ fps: s.governor ? s.governor.fps : null, p90: s.governor ? s.governor.p90 : null,
    power: s.power, theme: s.theme, bgMode: s.bgMode, backingMP: s.backing ? s.backing.mp : null,
    dpr: s.dpr, quality: s.quality, fish: s.fish });
} catch (e) { return null; } })()
```

Round fps and p90 to one decimal place. Confirm the unit of `governor.p90` (frame interval in ms) in the code and name the field `p90` accordingly.

**Never collected:**
- serial number, hardware UUID;
- user, computer or host name;
- IP address, Wi-Fi details;
- lists of apps or windows;
- absolute file paths;
- any persistent install ID. v1 has no install ID; this keeps the MAS privacy label minimal.

## 6. Snapshot / Снимок

- Source: `WKWebView.takeSnapshot(with:completionHandler:)` on the wallpaper window of `NSScreen.main` (fallback: the first window).
  - Set `WKSnapshotConfiguration` `snapshotWidth = 1600` (points).
  - Redraw the result into an `NSBitmapImageRep` with a long side of **at most 1600 px**.
  - No Screen Recording permission is needed, and only the aquarium is captured.
- Encoding: JPEG with `compressionFactor` 0.7. If the file is larger than 400 KB, retry with 0.55 and 0.4, then downscale to 1280 px. If it is still above 400 KB, treat the snapshot as failed.
- Stored as `<id>.jpg` next to the JSON. Base64 is embedded **only** in the POST body.
- **Check on a real Mac:** a hardware-decoded `<video>` backdrop may come out black in `takeSnapshot`. Acceptance test 8 checks this. If it is black, ship R22 anyway, change the caption to «Снимок без видео-фона», and file an engine-side snapshot hook as a follow-up.

## 7. JSON

There are two forms:
- **Payload** — what leaves the Mac in the POST.
- **Local file** `<id>.json` — the payload with `snapshot.base64` removed, `snapshot.file` set, and a top-level `delivery` object added. `delivery` is local-only and never sent.

Dates are ISO 8601 UTC from `ISO8601DateFormatter` with `.withInternetDateTime`. The id is `UUID().uuidString.lowercased()`.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "aq.feedback.v1",
  "title": "AquariumWallpaper feedback report v1",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema", "id", "createdAt", "category", "message", "consent", "app", "uiLanguage"],
  "properties": {
    "schema": { "const": "aq.feedback/1" },
    "id": { "type": "string", "format": "uuid" },
    "createdAt": { "type": "string", "format": "date-time" },
    "category": { "enum": ["bug", "idea", "fish_request", "other"] },
    "message": { "type": "string", "minLength": 10, "maxLength": 2000 },
    "fishRequest": { "type": ["string", "null"], "maxLength": 100 },
    "email": { "type": ["string", "null"], "maxLength": 254 },
    "uiLanguage": { "const": "ru" },
    "consent": {
      "type": "object", "additionalProperties": false,
      "required": ["given", "version", "at"],
      "properties": {
        "given": { "const": true },
        "version": { "type": "string", "pattern": "^fb-consent-[a-z]{2}-[0-9]+$" },
        "at": { "type": "string", "format": "date-time" }
      }
    },
    "app": {
      "type": "object", "additionalProperties": false,
      "required": ["bundleId", "version", "build"],
      "properties": {
        "bundleId": { "type": "string" },
        "version": { "type": "string" },
        "build": { "type": "string" }
      }
    },
    "diagnostics": { "oneOf": [ { "type": "null" }, { "$ref": "#/$defs/diagnostics" } ] },
    "snapshot": { "oneOf": [ { "type": "null" }, { "$ref": "#/$defs/snapshot" } ] },
    "delivery": { "$ref": "#/$defs/delivery", "description": "LOCAL FILE ONLY - never sent" }
  },
  "$defs": {
    "diagnostics": {
      "type": "object", "additionalProperties": false,
      "required": ["os", "model", "arch", "screens", "appearance", "power"],
      "properties": {
        "os": { "type": "object", "additionalProperties": false, "required": ["version"],
          "properties": { "version": { "type": "string" }, "build": { "type": ["string", "null"] } } },
        "model": { "type": "string", "maxLength": 40 },
        "arch": { "enum": ["arm64", "x86_64"] },
        "rosetta": { "type": "boolean" },
        "memoryGB": { "type": "integer", "minimum": 1 },
        "screens": { "type": "array", "minItems": 1, "maxItems": 8, "items": {
          "type": "object", "additionalProperties": false,
          "required": ["main", "widthPt", "heightPt", "scale"],
          "properties": {
            "main": { "type": "boolean" },
            "widthPt": { "type": "integer" }, "heightPt": { "type": "integer" },
            "scale": { "type": "number" }, "maxFps": { "type": ["integer", "null"] } } } },
        "appearance": { "enum": ["dark", "light"] },
        "power": { "type": "object", "additionalProperties": false,
          "required": ["onBattery", "lowPowerMode", "thermal"],
          "properties": {
            "onBattery": { "type": "boolean" }, "lowPowerMode": { "type": "boolean" },
            "thermal": { "enum": ["nominal", "fair", "serious", "critical"] } } },
        "launchAtLogin": { "type": "boolean" },
        "appUptimeSec": { "type": "integer", "minimum": 0 },
        "language": { "type": ["string", "null"], "maxLength": 35 },
        "engine": { "oneOf": [ { "type": "null" }, {
          "type": "object", "additionalProperties": false,
          "properties": {
            "fps": { "type": ["number", "null"] }, "p90": { "type": ["number", "null"] },
            "power": { "enum": ["high", "low", "paused"] }, "theme": { "type": ["string", "null"] },
            "bgMode": { "type": ["string", "null"] }, "backingMP": { "type": ["number", "null"] },
            "dpr": { "type": ["number", "null"] }, "quality": { "type": ["object", "null"] },
            "fish": { "type": ["integer", "null"] } } } ] }
      }
    },
    "snapshot": {
      "type": "object", "additionalProperties": false,
      "required": ["mime", "width", "height", "bytes"],
      "properties": {
        "mime": { "const": "image/jpeg" },
        "width": { "type": "integer", "maximum": 1600 },
        "height": { "type": "integer", "maximum": 1600 },
        "bytes": { "type": "integer", "maximum": 409600 },
        "base64": { "type": "string", "description": "POST only" },
        "file": { "type": "string", "pattern": "^[0-9a-f-]{36}\\.jpg$", "description": "local file only" }
      }
    },
    "delivery": {
      "type": "object", "additionalProperties": false,
      "required": ["route", "status", "attempts"],
      "properties": {
        "route": { "enum": ["endpoint", "mailto", "clipboard"] },
        "status": { "enum": ["sent", "pending", "handed_off", "failed"] },
        "attempts": { "type": "integer", "minimum": 0 },
        "lastAttemptAt": { "type": ["string", "null"], "format": "date-time" },
        "lastError": { "type": ["string", "null"], "maxLength": 200 },
        "ticket": { "type": ["string", "null"], "maxLength": 40 }
      }
    }
  }
}
```

Example payload:

```json
{ "schema": "aq.feedback/1", "id": "3f1c0b7e-9a42-4d0e-8b1a-5c2f7e9d1a00",
  "createdAt": "2026-10-17T12:30:05Z", "category": "fish_request",
  "message": "Хочу мандаринку возле кораллов, очень красивая рыба.", "fishRequest": "мандаринка",
  "email": null, "uiLanguage": "ru",
  "consent": { "given": true, "version": "fb-consent-ru-1", "at": "2026-10-17T12:30:01Z" },
  "app": { "bundleId": "com.gregorydich.aquariumwallpaper", "version": "1.0", "build": "1" },
  "diagnostics": null, "snapshot": null }
```

## 8. Delivery chain / Доставка

When the user presses «Отправить»:

1. **Build the report** (§7).
2. **Always save locally first.**
   - Directory: `FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)` + `AquariumWallpaper/Feedback/`, created with intermediates and permissions 0700.
   - Write `<id>.json` (and `<id>.jpg` if there is a snapshot) atomically with permissions 0600.
   - If saving fails, still continue to delivery, and show «Не удалось сохранить копию на этом Mac: <ошибка>» in the final alert.
3. **Choose the route** in this order:

   **a. `AQFeedbackEndpoint` is valid → POST**
   - Request: `POST <endpoint>` via `URLSession(configuration: .ephemeral)`, timeout 20 s.
   - Headers: `Content-Type: application/json; charset=utf-8`, `Accept: application/json`, `User-Agent: AquariumWallpaper/<version> (macOS <os.version>)`, `X-AQ-Schema: aq.feedback/1`.
   - Body: the payload, at most 1 MB.

   | Response | Status | User sees |
   |---|---|---|
   | 2xx | `sent`; `ticket` taken from the optional JSON field `ticket` | «Спасибо! Отзыв отправлен.» If an email was given, add «Ответим на <email> в течение нескольких дней.» |
   | 413 | — | Retry once with `snapshot = null`, then handle that result as usual |
   | 429, 5xx, `URLError` (offline or timeout) | `pending` | «Нет связи с сервером. Отзыв сохранён и уйдёт автоматически.» If `AQFeedbackEmail` is valid, add a button «Отправить письмом» (runs route b on the same report) |
   | Any other 4xx | `failed`, window stays open | «Сервер не принял отзыв (код N).» Buttons «Отправить письмом» (if an email is configured) or «Скопировать» |

   **b. Otherwise, `AQFeedbackEmail` is valid → `mailto:`**
   - Subject: `[Аквариум] <Категория по-русски>: <первые 50 знаков сообщения в одну строку>`.
   - Body:
     ```
     <message>

     —
     Рыбка: <fishRequest>          (only if set)
     E-mail для ответа: <email>    (only if set)
     ID отзыва: <id>
     Версия: <version> (<build>), macOS <os.version>, <model>   (model only if diagnostics ON)
     Диагностика:
     <compact JSON>                (only if diagnostics ON)
     ```
   - Encoding: `URLComponents` with `scheme = "mailto"`, `path = email`, and `queryItems` for `subject` and `body`. Then set `percentEncodedQuery = percentEncodedQuery?.replacingOccurrences(of: "+", with: "%2B")`.
   - If the URL is longer than 8000 UTF-8 bytes, drop the diagnostics from the body and add the line «Диагностика сохранена в файле <id>.json».
   - Open it with `NSWorkspace.shared.open(url)`:
     - returns `true` → status `handed_off`, alert «Открылось письмо — проверьте его и нажмите «Отправить» в почте.» If a snapshot is attached, also call `NSWorkspace.shared.activateFileViewerSelecting([jpgURL])` and add «Перетащите снимок <id>.jpg из открытой папки в письмо.»
     - returns `false` (no mail client) → continue with route c.

   **c. Otherwise → clipboard**
   - Plain text: the header «Отзыв для «Морского аквариума»», then «Тема: …», then the same body as in route b.
   - Copy it: `NSPasteboard.general.clearContents(); setString(text, forType: .string)`.
   - Status `handed_off`.
   - Alert: «Текст отзыва скопирован. Вставьте его (⌘V) в письмо или сообщение разработчику. Копия сохранена: ~/Library/Application Support/AquariumWallpaper/Feedback/<id>.json».
     - Show the path with `abbreviatingWithTildeInPath`, never with the user name.
     - Buttons: «Показать в Finder» (`activateFileViewerSelecting`) and «Готово».
4. **Finish.** On `sent`, `handed_off` or `pending`: clear the draft, record the send time for the rate limit, close the window. On `failed`: keep the window open with the text intact.

**Retry queue.** Runs 10 s after launch, then every 60 min via `Timer`, silently:
- covers files with `route == endpoint` and `status == pending`;
- POST again with at most 5 attempts in total;
- reports older than 7 days get `status = failed`;
- if the endpoint key has since been removed, leave the file as `pending`.

**Retention.** At launch:
- delete `sent` and `handed_off` reports older than 90 days, both `.json` and `.jpg`;
- keep at most the 100 newest reports.

**Threads.** JS calls, snapshots and all UI run on the main thread. URLSession callbacks hop back to main for UI updates. File I/O for retention runs on a utility queue.

## 9. Server contract (future Cloudflare Worker) / Контракт сервера

- Request: `POST` JSON, at most 1 MB.
- Responses:
  - 2xx with optional `{"ok": true, "ticket": "AQ-000123"}`;
  - 400 — invalid schema;
  - 413 — too large;
  - 429 — rate limited.
- Deduplicate by `id`: retries may resend the same report.
- Server side:
  - validate against the schema in §7;
  - store the row in D1 created with `--jurisdiction=eu`;
  - store the snapshot in an EU-jurisdiction R2 bucket;
  - send a notification via the `send_email` binding to the verified destination `support@tonamorph.com`; the sender is any owner domain on Cloudflare;
  - rate-limit by a salted IP hash kept no longer than 24 h;
  - keep reports for 24 months.
- Cost: $0 within the Free plan limits.

## 10. Privacy and App Store notes / Приватность

- Data is sent only on the button and with consent. The diagnostics JSON is visible before sending. There is no background telemetry.
- Retention: 24 months on the server (as the consent text says), 90 days for local copies.
- When this becomes a sandboxed MAS build (R16):
  - the Application Support path maps into the container automatically;
  - POST needs `com.apple.security.network.client`;
  - `mailto:` and the pasteboard work as is.
- MAS privacy label: because diagnostics can be attached, probably disclose Email Address and Diagnostics with purpose App Functionality; final decision in R16.
- This window never asks for an App Store rating (5.6.1), and no reward depends on what the feedback says.

## 11. Acceptance tests / Приёмка

1. Both keys empty → Send → `<id>.json` exists with permissions 0600; the clipboard holds the text; the alert shows a `~/...` path; «Показать в Finder» works.
2. Only `AQFeedbackEmail` set → Mail opens with subject and body prefilled; the JSON has `delivery.route = mailto`, `status = handed_off`. With no mail client configured → falls back to the clipboard.
3. Endpoint is a test HTTPS server: 2xx → `status = sent`. Network off → `pending`, and the report is delivered after the next launch. 413 → resent without the snapshot.
4. Endpoint `http://…` → ignored, logged, and the next route is used.
5. Message of 9 characters → Send disabled. Typing beyond 2000 → blocked. Email `a@b` → error shown, Send disabled. Consent unchecked → Send disabled.
6. Selecting «Ошибка» turns diagnostics ON. The JSON shown in the disclosure equals `diagnostics` in the saved file byte for byte (compare after re-serialising).
7. `grep` of the saved JSON finds neither the user name nor `/Users/`.
8. Snapshot shows only the aquarium, is at most 1600 px and at most 400 KB, and the **video backdrop is visible**. If the backdrop is black, follow §6.
9. With two monitors, `screens` lists both and the snapshot is taken from the main screen.
10. Dark mode: the window renders correctly. Wallpaper windows still pass clicks through.
11. Six sends within 10 minutes → the sixth is blocked with the rate-limit message.
12. Closing with Cancel and reopening restores the draft.

## 12. Estimate / Оценка

2–3 agent days in total:
- UI: 1 day;
- model, storage and delivery: 0.5–1 day;
- diagnostics and snapshot: 0.5 day;
- tests and polish: 0.5 day.

The Worker backend is a separate 0.5–1 day.

Owner actions:
- confirm `AQFeedbackEmail`;
- later, provide a Cloudflare account and domain and verify the destination address;
- publish the privacy-policy URL (R13).
