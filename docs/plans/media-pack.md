# R9. Пакет медиа: зашифрованный контейнер и схема `aquarium://`

> Часть дорожной карты (`ROADMAP.md`, R9; связано с R7, R8, R11, R13, R16). Итоговый проект от 22.10.2026 (v2).
> Это v1 после ревью: 18 замечаний, решение по каждому — в разделе «Что изменилось после ревью».
> Код только читали, в репозитории ничего не меняли. Это не юридическая консультация.
> **(?)** — не подтверждено первоисточником; **[Mac]** — проверяется только на Mac владельца.
> Текст для владельца — по-русски; технические разделы — по-английски.

## Коротко для владельца

1. Картинки и видео аквариума больше не будут лежать в приложении отдельными файлами: они собираются в один зашифрованный файл, и приложение расшифровывает их в памяти.
2. Код страницы (HTML и JS) остаётся открытым: лицензия стока требует прятать только медиа, а Apple не любит зашифрованный код.
3. Шифрование встроено в macOS, поэтому экспортных документов не нужно.
4. Это защита от простого копирования, а не от взломщика. Так же устроены игры и Wallpaper Engine.
5. **Главное сейчас:** репозиторий на GitHub открыт всем, и стоковое видео и картинки оттуда скачиваются без всякого пакета. Это нарушает лицензию Adobe сильнее всего остального. Нужно ваше решение — раздел ниже.
6. Сам аквариум не меняется, тестовый режим агентов тоже.
7. Сборка остаётся прежней (`./build.sh --run`). Она станет дольше примерно на 10 секунд и сама проверит пакет.
8. Один раз аквариум «забудет» подобранное качество картинки и за несколько секунд подберёт его заново.
9. Когда агенты закончат, нужна проверка на вашем Mac: около 40 минут, из них 25 — просто ждать.
10. Работы агентам — около 3,5 дня.

## Решение владельца

**Репозиторий `GregoryDich/GregoryDich` открыт всем.** Проверено 22.10.2026: `"visibility":"public"`, форков пока 0.
Ветка, на которой идёт работа, отдаёт `aquarium/assets/reef_day.mp4` любому (ответ 206 с `raw.githubusercontent.com`).
Условия Adobe запрещают давать третьим лицам скачивать сток «отдельным файлом». Пакет этого не исправляет. Пока
репозиторий открыт, выпуск невозможен: `release.sh` это проверит (§8).

Особенность: репозиторий называется так же, как ваш аккаунт, поэтому его README — это приветствие на вашей странице
GitHub. Если сделать его приватным, приветствие со страницы пропадёт.

| Вариант | Что сделать | Плюсы | Минусы |
|---|---|---|---|
| **А (советую)** | GitHub → репозиторий → Settings → внизу «Change visibility» → **Private** | Одна минута; агенты работают как раньше | Пропадёт приветствие на странице профиля |
| Б | Агенты переносят проект в новый приватный репозиторий, а в старом оставляют только README с очищенной историей | Приветствие остаётся | Около часа работы; переписывается история; сессии агентов придётся переключить на новый репозиторий |

Сделать это лучше сейчас, пока никто не сделал форк: по документации GitHub, публичный форк остаётся публичным и
после закрытия оригинала.

---

## Что изменилось после ревью

Все 18 замечаний проверены. Повторить удалось 1, 2, 3, 4, 5, 8, 10 и 13 (компилятор Swift 6.0.3 в режиме Swift 5,
исходники WebKit `main`, подсчёты). Для остальных проверены приведённые доказательства.

| # | Замечание | Решение | Что изменилось |
|---|---|---|---|
| 1 | Константы CommonCrypto в Swift имеют тип `Int`, поэтому вызов не компилируется | **Принято, повторено** (12 ошибок в дословной форме, 0 после явных приведений) | §2.1: явные приведения везде. L1/L2: заглушка CommonCrypto — модуль Clang в форме SDK, а не модуль Swift. Сверх замечания: настоящий `PackCipher.swift` теперь компонуется и запускается на Linux через прослойку OpenSSL (вектор NIST F.5.5 и все 2080 окон прошли), поэтому эталонный AES на Swift не нужен |
| 2 | Соответствие протоколу в основном объявлении выводит `@MainActor` и ломает неизолированных вызывающих | **Принято, повторено** (2 ошибки с протоколом `@MainActor`, 0 с соответствием в расширении) | §4.3: соответствие объявлено в `extension`. L1 проверяет вызывающих в трёх вариантах протокола |
| 3 | AVFoundation запрашивает много маленьких диапазонов, а путь через главный поток для каждого медленный | **Принято** | §4.3: быстрый путь, синхронно для тела ≤ 256 КБ. §4.4: задержки и гистограмма размеров. Журнал трассировки сводится по секундам. M4 получил порог и подшаг «меню и окна во время показа». В L5 добавлен сценарий на 3000 диапазонов |
| 4 | `stop` не приходит, если WKWebView освобождён | **Принято** | §4.3: слабая ссылка на веб-вид в каждой живой задаче, счётчик `orphaned`, сценарий L5 |
| 5 | `removeData` без обработчика завершения не компилируется и работает асинхронно | **Принято** | §4.6: окна создаются в обработчике завершения, запасной таймер 2 с. Заглушка L1 требует обработчик |
| 6 | Отображение файла в память при пропаже тома даёт SIGBUS | **Принято** | §1.3: `open` + `pread`; ошибка чтения превращается в `didFailWithError` |
| 7 | Настройка `maxRangeMB` не проверена, есть свидетельства против | **Принято: убрана из v1** | Если M8 покажет рост памяти — отдельный отладочный эксперимент (§12) |
| 8 | Утилите с кодом на верхнем уровне нужно имя `main.swift` | **Принято, повторено** | `macos-app/pack/main.swift` |
| 9 | Публичный репозиторий отдаёт медиа | **Принято как блокирующее**; проверку в `release.sh` пришлось исправить | URL из ревью (`…/main/aquarium/assets/reef_day.mp4`) уже отвечает 404: в `main` этого файла нет, а рабочая ветка его отдаёт. Поэтому проверяем видимость самого репозитория из `origin` (§8). Решение — у владельца |
| 10 | Поиск 3-байтовой сигнатуры JPEG в 79 МБ шума даёт ≈ 5 ложных находок | **Принято** (математическое ожидание 83,4·10⁶ / 2²⁴ ≈ 5) | §3.2: проверка по смещениям записей, шаблоны от 8 байт, энтропия, тест на 10 ключах |
| 11 | Проверка открытых медиа на диске слишком узкая; `removeData` асинхронный | **Принято частично** | Поиск по нескольким папкам — принят (§4.6). «Никогда не ждать `removeData`» — **отклонено**: это прямо противоречит замечанию 5, а удаление папки кэша во время создания `AVAssetCache` ведёт к гонке с неизвестным исходом. Ждём завершения, не больше 2 с, время пишем в диагностику |
| 12 | Шифровать собственный код — риск по правилу 2.5.19 | **Принято, без флага сборки** | §1.1: код лежит открыто в `Contents/Resources/web/` во **всех** сборках, раскладка одна. §11: ссылка на 2.5.19; отладочные переключатели и пункты ⌥ вырезаются в выпускной сборке |
| 13 | Пользовательская настройка `WebKitDebugDeveloperExtrasEnabled` открывает «Inspect Element» | **Принято, проверено по исходникам** | §10: правило и шаг M10 |
| 14 | Пересказ условий лицензии вместо цитаты; нет EULA для MAS | **Принято** | §0: цитата; §11: своё лицензионное соглашение в App Store Connect (R16) |
| 15 | Утверждения о ключе преувеличены; тестовый ключ может попасть в выпуск | **Принято** | §2.3: формулировки исправлены. `aqpack build --release` отказывается собирать с тестовым ключом |
| 16 | Изделие не EAR99; эталонный AES можно скомпоновать по ошибке | **Принято** | §11: новые основания. Эталонного AES на Swift больше нет (см. №1). В `release.sh` — проверка импорта CommonCrypto и отсутствия S-блока AES |
| 17 | `-Onone` и побайтовые циклы замедляют каждую сборку | **Принято** | Утилита собирается с `-O`; работа с целыми буферами — через `memmem` и CommonCrypto; порог времени в L3 |
| 18 | Повреждённый пакет: аварийное завершение или чёрные обои | **Принято** | §1.3: проверка границ и структуры, хэши кода при открытии, хэши картинок при отдаче, полная проверка в фоне |

Ещё три правки по ходу проверки:
- **Переход на главный поток.** Ответы передаются через `CFRunLoopPerformBlock` в общих режимах, а не через
  `DispatchQueue.main.async`. WebKit сам доставляет `start` и `stop` через источник цикла выполнения в общих режимах
  (`RunLoopCF.cpp:52-63`). Главную очередь не обслуживают, пока внутри её блока идёт модальный цикл: это уже
  записано в `HostAlert` (`Lifecycle.swift:205-212`).
- **`.gitignore`.** `macos-app/build/` и `dist/` там уже есть, добавить нужно только `macos-app/.packkey`. Довод v1
  о том, что `release.sh` видит `build/`, был неверен: там стоит `--untracked-files=no`.
- **Целостность во время работы.** Полная проверка SHA-256 пакета выполняется в фоне через 30 с после запуска
  (§1.3). Это закрывает и видео, которое отдаётся частичными диапазонами.

---

## 0. Исходное состояние

- **What the engine loads.**
  - `index.html` loads `fish/manifest.js`, `scene/scene.js`, `scene/corals/catalog.js`.
  - Images go through `new Image()`. The two videos `assets/reef_{day,night}.mp4` play in `<video>`: 2560×1440,
    H.264 High, ≈ 9.3 Mbit/s, 20.02 s, moov at the front, `loop`, `muted`, `requestVideoFrameCallback`. With
    `?vlayer`, the `<video>` elements are on the page as layers.
  - All paths are relative, and nothing checks `location.protocol`.
  - Storage: `localStorage` (`aq.gov.<screen>.<power>`) and `sessionStorage` (`aq.blackbox`, `aqBoots`, `aq.phase`).
- **What ships today:** 64 media files (59 PNG, 3 JPG, 2 MP4), 78 777 227 bytes (78.8 MB). This equals the 64
  registry rows with «In .app = Yes» in `docs/licences/ASSETS.md`. There are also 5 code files of 700 431 bytes:
  `index.html` 509 915, `scene/scene.js` 112 954, `scene/corals/catalog.js` 25 259, `fish/manifest.js` 16 577, and
  `spike/layers.html` 35 726.
- **App.**
  - `WallpaperWindow` calls `loadFileURL(index.html, allowingReadAccessTo: aquarium/)`.
  - `LayersTestWindow` does the same for `spike/layers.html`.
  - The boot script is a `WKUserScript`.
  - `build.sh` copies all of `aquarium/` and deletes `render/`, `alt/`, `blender/`, `*.md`, `README.txt`, `.DS_Store`.
  - Only two places create a `WKWebView` (`WallpaperWindow.swift:145`, `LayersTestWindow.swift:23`).
- **Licence.** Adobe Stock Additional Terms, §7.1 General Restrictions (A), quoted from the 10.05.2024 PDF: *"You must
  not … (A) use the Stock Assets in any way that allows a third party to use, download, extract or access the Stock
  Assets (1) as a stand-alone file; or (2) in a way that exceeds the scope of the license"*
  ([PDF 20240510](https://wwwimages2.adobe.com/content/dam/cc/en/legal/servicetou/Stock-Additional-Terms_en_US_20240510.pdf)).
  The same wording is reported for the Product Specific Terms of 16.01.2026
  ([PDF 20260116](https://www.adobe.com/cc-shared/assets/pdf/legal/servicetou/stock-product-specific-terms-en-us-20260116.pdf)).
  adobe.com is blocked from the agent sandbox, so the text comes from search excerpts. The 2026 section number has
  not been re-read from the PDF; whoever next has access to adobe.com re-reads it (?).
  - A file that can be taken out of the `.app` and played in QuickTime is case (1).
  - A file served by a public GitHub repository is case (1) too.
  - Industry practice (Unreal pak, Unity bundles, Wallpaper Engine) is: no loose files, a technical barrier, and a
    ban in the EULA. `docs/legal/eula.md` §3 already contains the ban.
- **Precondition (blocker):** the repository must not be public. See «Решение владельца» and the `release.sh`
  check in §8.

## 1. Контейнер и раскладка в `.app`

### 1.1 Что зашифровано, а что нет

| In the `.app` | Content | Encrypted |
|---|---|---|
| `Contents/Resources/content.aqp` | **media only**: 64 entries (59 PNG, 3 JPG, 2 MP4), 78.8 MB | yes |
| `Contents/Resources/web/` | `index.html`, `fish/manifest.js`, `scene/scene.js`, `scene/corals/catalog.js`, plus `spike/layers.html` in dev builds only | **no** |

Why code stays plain (review #12):
- The licences require hiding media, not our code. App Review Guideline 2.5.19 says *"Attempting to hide undocumented
  features in your app binary, such as through code obfuscation or other methods, is grounds for removal…"*.
- Every build uses the same layout (dev, direct and MAS), so there is one test matrix and no build flag.
- There is still a single origin: both folders are served by the same `aquarium://localhost` handler (§4). The
  canvas stays untainted and no CORS is needed.
- Stock IDs in `catalog.js` are not a licence problem.
- The LMA2 text gate (§3.4) still runs on the `web/` files.

**Whitelist** (rules live only in `aqpack`):

| Rule | Pack (`content.aqp`) | `web/` | Never shipped |
|---|---|---|---|
| Extensions | `.png .jpg .jpeg .mp4 .webp` | exactly the 4 code files above, plus `spike/layers.html` without `--release` | `.md`, `.txt`, `.py`, `.json` and everything else, including `README.md`, `PALETTE.md`, `scene/README.txt`, `assets/README.txt`, `fish/PROMPTS.md` |
| Folders | all of `aquarium/` | — | `blender/`, `fish/render/`, `assets/render/`, `assets/alt/`, dot files |

A file of an unknown type in a shipped folder gives the warning «не упакован: …», so a new asset type is not
dropped silently. The photo-scene fallbacks (`assets/reef_bg.jpg`, `scene/occ_*`, `scene/patch_*`,
`scene/light_mask.png`, `scene/props/*`) are packed: the engine uses them if the video scene fails.

### 1.2 Формат v1

All integers are little-endian, except the CTR counter, which is big-endian.

**Header, 64 bytes, in the clear:**

| Off | Len | Field |
|---|---|---|
| 0 | 4 | magic `AQPK` |
| 4 | 2 | `format` = 1 |
| 6 | 2 | `headerSize` = 64 |
| 8 | 4 | `flags`: bit 0 = release build |
| 12 | 4 | `entryCount` (media entries) |
| 16 | 16 | `salt` (§2.2) |
| 32 | 8 | `keyCheck` = SHA-256(K ‖ "aqpk/check/1")[0..8]: a wrong key gives a clear error instead of noise |
| 40 | 8 | `indexOffset` |
| 48 | 8 | `indexLength` |
| 56 | 8 | `indexNonce` |

**Data.**
- Entries start at byte 64. Each starts on a 16-byte boundary, and entries are sorted by path (UTF-8 byte order).
- Each entry is encrypted whole with its own nonce.
- There is no compression: PNG, JPG and MP4 are already compressed.

**Index.** It sits after the data and is encrypted with K and `indexNonce`. It is UTF-8 JSON with sorted keys:

```json
{"entries":[{"mime":"video/mp4","nonce":"9c1e…(16 hex)","offset":1234560,"path":"assets/reef_day.mp4",
             "sha256":"…(64 hex)","size":23226780}, …],
 "format":1,"id":"3fa2…(16 hex)",
 "web":[{"mime":"text/html; charset=utf-8","path":"index.html","sha256":"…","size":509915}, …]}
```

- `path` is relative to `aquarium/`. In URLs it follows `aquarium://localhost/`.
- `mime` is written by the packer. That gives one MIME table for the packer, the app and the harness server.
- `sha256` is the hash of the plaintext.
- `web` lists the plain code files with their hashes. This ties the code to the pack: a mismatch means the bundle is
  damaged (§1.3).
- `id` = SHA-256 of the canonical JSON of `entries` + `web`, first 8 bytes. It is a content fingerprint shown in
  diagnostics.

**What the pack does not contain:** build time, commit or host name. With the same key and the same `aquarium/`,
the pack is identical to the byte. Build metadata goes into the manifest, which is not in the `.app` (§3.3).

### 1.3 Чтение и проверка в приложении

**Open** (`PackStore.open`, `PackFormat.swift`, at launch before any window exists):
- `open(path, O_RDONLY)` once. Every read is a positional `pread(fd, buf, len, off)` into a fresh buffer, decrypted
  in place.
- Why not `Data(contentsOf: .alwaysMapped)`: if the volume disappears (for example the app was run from a mounted
  DMG and the DMG was ejected), the next page fault in the mapping is a SIGBUS crash. Apple, *Mapping Files Into
  Memory*: "If you map files on a removable or network drive and that drive is unmounted … accessing the mapped
  memory can cause a bus error". `pread` returns `EIO` instead, which we turn into `didFailWithError`, and the
  engine's existing `VID_BACKOFF` retry and image fallbacks take over.
- `pread` has no shared file offset, so it is safe from any thread.

**Validation before any slicing** (review #18). Any failure gives `PackError.corrupt(reason)`, which leads to the
existing `HostAlert` «Файлы аквариума повреждены (content.aqp: …). Переустановите приложение.» and to
`host.pack.error`. Swift must never trap here:
- `fileSize ≥ 64`; magic, `format == 1`, `headerSize == 64`.
- `64 ≤ indexOffset`, `indexOffset + indexLength == fileSize`, `indexLength ≤ 1 MiB` (all in checked arithmetic).
- `keyCheck` matches; the index decrypts to valid JSON; `entries.count == entryCount`; `id` recomputes.
- For each entry: `offset ≥ 64`, `offset % 16 == 0`, `offset + size ≤ indexOffset`; entries sorted and
  non-overlapping; `path` passes the same validator as `ContentRoute` (§4.2); nonce exactly 8 bytes; `mime`
  non-empty; extension on the pack whitelist.
- For each `web` entry, the file `Contents/Resources/web/<path>` exists and its SHA-256 matches. That is 0.66 MB, about
  1 ms. A damaged `index.html` would otherwise load as garbage and finish navigation with `.ready` while the heartbeat
  `0` still answers: a silent black wallpaper.

**While serving:**
- A full `200` GET of an image is hashed as it is read: synchronously on the fast path, or incrementally in the
  pump (§4.3). On a mismatch the task gets `didFailWithError` instead of `didFinish`, and
  `pack.error = "sha mismatch <path>"` is recorded once.
- Partial `206` ranges (video) cannot be hashed per request; the background check below covers them.

**Background full check.** 30 s after launch, on a `.utility` queue, every entry is read, decrypted and hashed with
the same `PackStore.read`. That is 78.8 MB: AES and SHA-256 both run on hardware instructions, so it costs about
0.1–0.2 s of CPU [estimate]. The result goes to `pack.verify {ok, ms, bad[≤3]}`. A failure gives `Log.error` and the
same alert, once.

**Integrity and code signing.** `content.aqp` and `web/` are sealed resources. The seal is checked by
`codesign --verify` at release and by Gatekeeper on the first launch of a quarantined copy, **not on later launches
or reads**. Dev builds have no seal at all. That is why the app does its own checks above.

## 2. Шифр, ключ, модель угроз

### 2.1 Шифр — AES-256-CTR из CommonCrypto

| | Pure-Swift ChaCha20 | CryptoKit AES-GCM chunks | **CommonCrypto AES-256-CTR** |
|---|---|---|---|
| Apple's export table | «industry standard algorithm, not provided within the Apple OS» → French declaration | OS crypto → nothing | **OS crypto → nothing** |
| Random access for Range requests | yes | per 64 KB chunk + 16 B tag | **yes, 16 B blocks, no overhead** |
| Linux tests | native | needs swift-crypto | **same source, linked against an OpenSSL shim (L2)** |
| Speed | ≈ 0.5–1 GB/s [estimate] | hardware | hardware (arm64 and x86 AES instructions) |
| Minimum macOS | any | 10.15 | 10.7 |

XOR and home-made ciphers are rejected. A XOR key falls out of known file headers, and a proprietary cipher means
CCATS and a French declaration.

**API.** The only crypto code is `enum PackCrypto` in `Sources/PackCipher.swift` (`import CommonCrypto`).
`CommonCryptor.h` declares `kCCEncrypt`, `kCCModeCTR`, `kCCAlgorithmAES`, `ccNoPadding`, `kCCModeOptionCTR_BE` and
`kCCSuccess` in **anonymous C enums**, which Swift imports as `Int`. The parameter types are `uint32_t` typedefs, and
`CC_SHA256_DIGEST_LENGTH` is a macro imported as `Int32`. Every use therefore converts explicitly (review #1). This
form compiles whatever integer type a constant has:

```swift
enum PackCrypto {
    static func sha256(_ parts: [Data]) -> [UInt8] {
        var ctx = CC_SHA256_CTX()
        _ = CC_SHA256_Init(&ctx)
        for p in parts { p.withUnsafeBytes { _ = CC_SHA256_Update(&ctx, $0.baseAddress, CC_LONG($0.count)) } }
        var out = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
        _ = CC_SHA256_Final(&out, &ctx)
        return out
    }
    /// XOR `buf` in place with the AES-256-CTR keystream starting at block `block` (IV = nonce ‖ UInt64BE(block)).
    static func ctrXOR(key: [UInt8], nonce: [UInt8], block: UInt64, _ buf: UnsafeMutableRawBufferPointer) -> Bool {
        guard key.count == 32, nonce.count == 8 else { return false }
        if buf.count == 0 { return true }
        var iv = nonce
        withUnsafeBytes(of: block.bigEndian) { iv.append(contentsOf: $0) }
        var ref: CCCryptorRef?
        let st = CCCryptorCreateWithMode(CCOperation(kCCEncrypt), CCMode(kCCModeCTR), CCAlgorithm(kCCAlgorithmAES),
                                         CCPadding(ccNoPadding), iv, key, 32, nil, 0, 0,
                                         CCModeOptions(kCCModeOptionCTR_BE), &ref)
        guard Int(st) == Int(kCCSuccess), let c = ref else { return false }
        defer { _ = CCCryptorRelease(c) }
        var moved = 0      // in-place is allowed for stream modes (CommonCryptor.h, CCCryptorUpdate)
        let u = CCCryptorUpdate(c, buf.baseAddress, buf.count, buf.baseAddress, buf.count, &moved)
        return Int(u) == Int(kCCSuccess) && moved == buf.count
    }
}
```

**Evidence, 22.10.2026.**
- The code above, the literal v1 call and a header copied from `CommonCryptor.h` (anonymous enums, typedefs,
  `#define`, prototypes) were compiled with Swift 6.0.3 in `-swift-version 5` through a Clang module:
  - the literal v1 call gives 12 errors of the form `cannot convert value of type 'Int' to expected argument type
    'CCOperation' (aka 'UInt32')`;
  - the code above gives 0.
- The same `PackCipher.swift` was then linked against a 40-line C shim over OpenSSL `EVP_aes_256_ctr` and
  `EVP_sha256` with the same prototypes. Results:
  - NIST SP 800-38A F.5.5 (CTR-AES256) passed;
  - all 2080 windows (a, len) over the 64-byte vector passed, using «start at block ⌊a/16⌋, drop a mod 16»;
  - FIPS 180-4 «abc» passed.

So the Linux tests run **the shipped source**, and the repo needs no Swift AES at all.

### 2.2 Ключи и nonce

- **M**, the master key: 32 bytes in `macos-app/.packkey`.
  - `build.sh` creates it if it is missing (`aqpack keygen`: 32 random bytes, mode 600).
  - **Add `macos-app/.packkey` to `.gitignore`**, so that `git add -A` can never commit it.
  - Losing the key (new Mac) breaks nothing: the pack and the binary are always built together.
- **In the binary.** `build/gen/PackKey.swift` is generated on every build: two `[UInt64]` arrays of 4 words with
  M = A ⊕ B and A = SHA-256(M ‖ "aqpk/mask/1"). It is deterministic, so the binary is reproducible.
- **salt** = SHA-256(M ‖ "aqpk/salt/1")[0..16], written to the header.
- **K** = SHA-256(M ‖ salt ‖ "aqpk/key/1"), computed at launch.
- **Entry nonce** = SHA-256(M ‖ "aqpk/nonce/1" ‖ path ‖ 0x00 ‖ sha256(plaintext))[0..8].
  - It is content-addressed: an unchanged file gives the same ciphertext, so Sparkle deltas (R11) stay small.
  - A changed file gets a new nonce, so a keystream is never reused for different data.
- **indexNonce** = SHA-256(M ‖ "aqpk/index/1" ‖ sha256(index JSON))[0..8].
- **IV of block n** = nonce(8) ‖ UInt64BE(n).
  - To read [a, b], start at block ⌊a/16⌋ and drop `a mod 16` bytes.
  - Entries are < 2^68 bytes, so the counter never carries out of the low 64 bits, and 64- and 128-bit counter
    increments (CommonCrypto, OpenSSL) agree.
- **Test key:** `tools/pack-test/test.packkey`, committed and labelled as test-only.
  - `aqpack build --release` **refuses** if SHA-256(M) equals SHA-256(test key), or if the key file path is under
    `tools/`: «Это тестовый ключ — выпуск с ним невозможен».
  - Test packs exist only in `tools/aquarium-test/out/`, which is gitignored.

### 2.3 Модель угроз

**Protects against:**
- «Show Package Contents» on the `.app` or the DMG, and copying a file into QuickTime or Preview;
- Spotlight, Quick Look and Time Machine, which only see `content.aqp`;
- signature carving (`binwalk`, file carving), `strings`, and generic unpackers for zip or folders.

**Does not protect against:**
- **Anyone who reads the format, which is public while the repo is public.** M is stored as two adjacent 32-byte
  constants, and `keyCheck` in the clear header is an oracle. A script of about 20 lines that XORs nearby 32-byte
  pairs in `__DATA_CONST` and tests `keyCheck` recovers M in seconds, with no disassembler. Hiding the format (a
  private repo) raises the bar a little; it does not change the class of protection.
- memory dumps of the WebContent and GPU processes; screen recording; GPU frame capture.
- Web Inspector in a dev build. Release builds: §10.

The barrier is deliberately at the level of Unreal pak (AES key in the binary, extracted by tools in seconds) and
Unity bundles. The industry standard is «no stand-alone files + technical barrier + EULA ban». This is not DRM:
there are no licence checks, no servers and no licence screen.

## 3. Упаковщик `aqpack` и манифест ассетов

### 3.1 Сборка утилиты

- The owner's Mac only guarantees `swiftc` (Command Line Tools). Node is not there, and the CLT `python3` has no AES.
- The source is **`macos-app/pack/main.swift`**. It must be named `main.swift`: in a multi-file compile, top-level
  statements are allowed only in a file of that name. With `aqpack.swift` the build fails with «statements are not
  allowed at the top level» (reproduced).
- It lives outside `Sources/`, so the app build never compiles it.
- Build command:
  ```
  swiftc -O -swift-version 5 pack/main.swift Sources/PackFormat.swift Sources/PackCipher.swift -o build/tools/aqpack
  ```
  - It builds for the host architecture only. `-O`, not `-Onone`: verify touches 79 MB on every build.
  - All whole-buffer work uses C primitives: `memmem` for pattern search, `Data ==` (memcmp), `CC_SHA256`,
    `CCCryptorUpdate` on whole entries.
  - The only per-byte Swift loop is the entropy histogram, written over `withUnsafeBytes`.
- `aqpack verify` therefore runs **the exact decryption code** of the wallpaper on every build.
- On Linux the same three files compile with `-I tools/pack-test/cc` and link against the OpenSSL shim (§13 L2).
- The tool lands in `build/tools/`, not in the `.app`, so the «no nested code» check in `release.sh` is unchanged.

### 3.2 Команды

| Command | What it does |
|---|---|
| `aqpack keygen --key .packkey` | creates the key if missing; prints «создан новый ключ … — в git не попадает» |
| `aqpack build --src ../aquarium --key .packkey --out <Resources>/content.aqp --web-out <Resources>/web --swift-key build/gen/PackKey.swift --registry ../docs/licences/ASSETS.md --manifest build/pack-manifest.json [--release]` | selection (§1.1); gates (§3.4); test-key refusal in `--release`; writes the pack, `web/`, `PackKey.swift` and the manifest |
| `aqpack verify --pack <.aqp> --web <web dir> --key .packkey --src ../aquarium` | decrypts every entry with **the app's code** and compares SHA-256 and bytes with the source; runs the noise gate below; checks determinism (an in-memory rebuild must match to the byte); prints elapsed seconds |
| `aqpack list --pack <.aqp> --key .packkey` | table: path, size, MIME, SHA-256 prefix (debugging) |
| `aqpack scan --app <AquariumWallpaper.app> [--allow-loose]` | allowed in the bundle: `content.aqp`; `web/` with exactly the whitelisted files; `Info.plist`, `.icns`, `_CodeSignature`, the executable. Any other file with a media/web extension (`png jpg jpeg mp4 mov webm webp gif html js`), or with a media magic **at offset 0** (all files except `content.aqp`), fails. The `web/` files also pass the LMA2 text gate. `--allow-loose` permits the dev `aquarium/` copy |

There is no «extract to files» command: plaintext media never go to disk, not even through our own tools. Messages
are in Russian with a hint, in the style of `build.sh` and `release.sh`.

**Noise gate in `verify`** (review #10). A correct 78.8 MB pack is random data. Any 3-byte pattern then occurs
about 78.8·10⁶ / 2²⁴ ≈ 5 times by chance; measured: 8 of 8 random blobs of that size had at least one `FF D8 FF`. So
the gate does not grep the whole blob for short magics:
1. **At each entry offset:** the first 16 ciphertext bytes differ from the first 16 plaintext bytes, and they do not
   start with a magic of 4 bytes or more (PNG 8 bytes; `ftyp` at +4; JPEG `FF D8 FF E0|E1|DB`; `<htm`; `<!do`). The
   same applies to byte 64 (the first entry) and to the index start.
2. **Whole data region, long patterns only** (≥ 8 bytes, chance hit ≈ 0): `89 50 4E 47 0D 0A 1A 0A`, `ftypisom`,
   `ftypmp42`, `ftypavc1`, `JFIF\0`, `Exif\0\0`, `<!doctype html` (case-insensitive), `<html`. The search uses
   `memmem`, and the gate requires 0 hits.
3. **Entropy:** the byte histogram over the data region gives ≥ 7.99 bits/byte. Random data of this size gives
   8 − 2·10⁻⁶.

L3 runs this gate on 10 packs built with random keys and requires 0 false positives.

### 3.3 Манифест ассетов (R9 «манифест с ID»)

`build/pack-manifest.json` is written on every build and never goes into the `.app`. `release.sh` copies it to
`dist/AquariumWallpaper-<version>.assets.json`.

```json
{"schema":"aq.packmanifest/1",
 "pack":{"file":"content.aqp","id":"3fa2…","format":1,"bytes":78790000,"sha256":"…","entries":64,"web":4},
 "build":{"kind":"dev|release","git":"8ad780c","dirty":false,"at":"2026-…","verifySeconds":1.4},
 "gates":{"registry":"ok","resolution":"ok","text":"ok","noise":"ok","testKey":"ok"},
 "entries":[{"path":"assets/reef_day.mp4","kind":"media","mime":"video/mp4","bytes":23226780,"sha256":"…",
             "px":"2560x1440","licence":"Enh","stock":["188049047"]},
            {"path":"index.html","kind":"web","mime":"text/html; charset=utf-8","bytes":509915,"sha256":"…"}]}
```

**Asset ID** = path in the pack + stock IDs from the registry. The path is unique and stable, and it is what the
engine requests; the stock ID is what Adobe would ask about.

If Adobe asks us to stop using asset X:
1. find X in `ASSETS.md`, which lists every derived file;
2. replace those files in `aquarium/` and build;
3. confirm that X is absent from the new `assets.json`;
4. ship the update.

The `dist/*.assets.json` files of past releases show which versions contained X. There is no hot-swap overlay: R9
asks for replacement through an update, and the whole app updates.

### 3.4 Гейты упаковщика

In a dev build these are warnings and the build continues. With `--release` they are errors and the release stops.
The owner's daily builds therefore never break over a forgotten registry row, but a release without it is
impossible.

1. **Registry (R7, KR2).**
   - Every pack entry has an `ASSETS.md` row with «In .app = Yes», and every such row is in the pack.
   - Parsing is line by line: a table row whose first cell is a path in backticks.
   - The licence is the 4th cell (`Std`, `Enh`, `own`). Stock IDs are all numbers of 6 or more digits in the
     source cell, including «derived from …».
2. **Resolution (§9).**
   - For `Std`/`Enh`: images ≤ 2560 px on the long side, video ≤ 2560×1440.
   - Sizes are read from headers only: PNG `IHDR`, JPEG `SOF0/1/2`, MP4 `tkhd` inside the front `moov`.
   - `own` assets are not limited.
3. **Text (R9, KR3):** no `LMA2`, `Living Marine Aquarium` or `Marine Aquarium` (case-insensitive) in the `web/` files.
4. **Whitelist:** a file of an unknown type in a shipped folder gives «не упакован: …».
5. **Test key:** `--release` with the test key is an error (§2.2).

## 4. Обработчик схемы `aquarium://`

### 4.1 Имя и адреса

- **Scheme and host:** scheme `aquarium`, host `localhost`. The page is `aquarium://localhost/index.html`; Layers
  test is `aquarium://localhost/spike/layers.html`, and its `../assets/…` resolve to `/assets/…`.
- **Why this scheme name.**
  - The scheme is registered per `WKWebViewConfiguration`, never system-wide, so it cannot clash with other apps.
  - Renaming the product (R10) does not touch it.
  - The scheme is part of the origin, and so of the `localStorage` key. It must never change again.
  - Before registering: `assert(!WKWebView.handlesURLScheme("aquarium"))`. Registering a scheme that WebKit handles
    itself raises `NSInvalidArgumentException`.
- **Why `localhost`.** WebKit exempts `localhost` from resource-load statistics in non-Safari apps
  (`WebsiteDataStoreCocoa.mm:225`, `ResourceLoadStatisticsStore.cpp:393-398`), so the 7-day ITP deletion of
  script-written storage does not apply to a wallpaper nobody clicks.
- **The origin:** a tuple origin, not `null` (`SecurityOriginData.cpp:193-231`), and a secure context. Images and
  video from it do not taint the canvas, and no CORS is needed.

### 4.2 Маршрут запроса

`ContentRoute.plan(method:path:range:index:) -> Plan` is a pure function in `PackFormat.swift`, with no WebKit
types, tested on Linux.

**Path.**
- Take `url.path` percent-decoded; drop the query and fragment.
- `/` becomes `index.html`.
- Reject with 404 if the path contains `..`, `\` or NUL, is empty, or matches nothing.
- Lookup order: pack entry, then `web` entry. The `folder` dev source (§5) serves both from the loose copy.

| Request | Response |
|---|---|
| no entry, document (`.html`) | `didFailWithError(URLError(.fileDoesNotExist))`: the existing `didFailProvisionalNavigation` retry fires. A 404 for the main document would give an empty page with `didFinish` |
| no entry, subresource | `HTTPURLResponse` 404 (`text/plain`, `Content-Length: 0`): `img.onerror` and the fallback chain fire (poster → photo → procedural reef) |
| no `Range` | 200, `Content-Length` = size |
| `Range: bytes=a-b` | 206, end clipped to `size−1` |
| `bytes=a-`, or a non-numeric end (`*`, old WebKit, bug 236401) | 206 to the end |
| `bytes=-n` | 206, the last n bytes |
| several ranges | the first one (research A, §5) |
| `a ≥ size`, or unparsable syntax | 416, `Content-Range: bytes */size` |
| `HEAD` | headers only, then `didFinish` at once |

**Headers on every response.**
- `Content-Type` from the index, `Content-Length`, `Accept-Ranges: bytes`.
- 206 adds `Content-Range: bytes a-b/size`.
- `.mp4` adds `Cache-Control: no-store`, a hint for `AVAssetCache` (?).
- HTML, JS and images get no `Cache-Control`. WebContent's memory cache keeps them while the process lives
  (`CachedResource.cpp:426-442`); nothing goes to disk, because the network process is not involved
  (`WebLoaderStrategy.cpp:335-343`).

**Range case table:** `tools/pack-test/range_cases.json`. Both the Swift `ContentRoute` and the Node `packserve.js`
are checked against it, so they cannot drift apart.

### 4.3 Потоки, быстрый путь, отмена

**Rules.**
1. WebKit calls `start` and `stop` on the main thread.
2. Every task call (`didReceive`, `didFinish`, `didFailWithError`) is made on the main thread and only while the
   task is live.
3. The main thread never waits synchronously for a background queue.
4. Small bodies are answered synchronously in `start` (the fast path). Large bodies are read and decrypted on a
   background queue.

**Why the fast path** (review #3). WebKit tells AVFoundation that the entire length is available on demand. Its own
comment says that AVAssetResourceLoader will then «request small data ranges over and over again during the playback»
(`WebCoreAVFResourceLoader.mm:428-434`, `main`). Actual-Chat measured this on a macOS AppKit app
([PR #5475](https://github.com/Actual-Chat/actual-chat/pull/5475)): exact ranges such as `bytes=0-1` and
`bytes=32-39`, about 100 per second, each requested only after the previous one completes.
- If every one of those took main → io → main, video throughput would depend on main-thread latency, and any hiccup
  would become `vstall`.
- Capacitor answers local Range requests synchronously inside `webView(_:start:)`
  ([WebViewAssetHandler.swift](https://github.com/ionic-team/capacitor/blob/main/ios/Capacitor/Capacitor/WebViewAssetHandler.swift)
  l.32-111).
- The fast path needs no live entry and has no stop race: `start` returns only after `didFinish`.
- Today 21 of the 64 media files fit in it whole, and so do all of AVFoundation's small ranges.

**Why the main hop is a run-loop block.** WebKit delivers `start` and `stop` through a `CFRunLoopSource` in
`kCFRunLoopCommonModes` and wakes the loop itself (`RunLoopCF.cpp:52-63`, `RunLoop.cpp:157-169`). The main dispatch
queue is **not** drained while a modal loop runs inside a main-queue block; the app already works around exactly
that in `HostAlert` (`Lifecycle.swift:205-212`). Hopping back with a common-modes run-loop block keeps our replies
flowing whenever WebKit's requests are flowing.

```swift
/// Main-thread hop with the same delivery as WebKit's own: a common-modes run-loop block plus a wake-up
/// (CFRunLoopPerformBlock alone does not wake the loop).
func onMain(_ body: @escaping () -> Void) {
    let rl = CFRunLoopGetMain()
    CFRunLoopPerformBlock(rl, CFRunLoopMode.commonModes.rawValue, body)
    CFRunLoopWakeUp(rl)
}

final class ContentSchemeHandler: NSObject {     // NOT `: WKURLSchemeHandler` here — see the extension below
    static let fastPathMax: UInt64 = 256 << 10
    static let chunk: UInt64 = 512 << 10
    private struct Live { let task: WKURLSchemeTask; weak var webView: WKWebView?; let t0: UInt64; let path: String }
    private var live: [ObjectIdentifier: Live] = [:]          // main thread only
    private let io = DispatchQueue(label: "aq.content.io", qos: .userInitiated, attributes: .concurrent)
    private let store: ContentStore                           // immutable: index + fd + K (pack) or the loose folder
    let stats = ContentStats()                                // main thread only, §4.4

    init(store: ContentStore) { self.store = store; super.init() }

    func startTask(_ webView: WKWebView, _ task: WKURLSchemeTask) {
        let t0 = DispatchTime.now().uptimeNanoseconds
        switch store.plan(task.request) {                    // ContentRoute.plan — pure, Linux-tested
        case .fail(let e):
            task.didFailWithError(e); stats.failed(task.request, t0)
        case .respond(let response, let body):
            if body.count <= Self.fastPathMax {               // fast path: synchronous, no live entry, no stop race
                guard let data = store.read(body), store.hashOK(body, data) else {   // hashOK: full 200 images only
                    task.didFailWithError(ContentError.read(body.path)); stats.failed(task.request, t0); return }
                task.didReceive(response)
                if !data.isEmpty { task.didReceive(data) }
                task.didFinish()
                stats.done(body, t0, fast: true)
                return
            }
            let id = ObjectIdentifier(task)
            live[id] = Live(task: task, webView: webView, t0: t0, path: body.path)
            task.didReceive(response)                         // sizes are known from the index
            pump(id, body, body.range, hasher: store.hasherIfFullImage(body))
        }
    }
    func stopTask(_ task: WKURLSchemeTask) {
        if live.removeValue(forKey: ObjectIdentifier(task)) != nil { stats.cancelled += 1 }   // no call ever again
    }
    /// The live entry, or nil if it was stopped, finished, or its page is gone. WebKit does not deliver `stop` when
    /// the WKWebView is released (platformStopTask with a nil cocoaView only suppresses exceptions).
    private func current(_ id: ObjectIdentifier) -> Live? {
        guard let l = live[id] else { return nil }
        if l.webView == nil { live[id] = nil; stats.orphaned += 1; return nil }
        return l
    }
    /// One chunk ≤ 512 KB in flight per task: pread + decrypt (+ hash) on io → run-loop hop → still live? → deliver.
    private func pump(_ id: ObjectIdentifier, _ body: Body, _ rest: Range<UInt64>, hasher: PackHasher?) {
        let store = self.store
        let part = rest.lowerBound ..< min(rest.upperBound, rest.lowerBound + Self.chunk)
        io.async {
            var h = hasher
            let data = store.read(body, part)
            if let d = data { h?.update(d) }
            let posted = DispatchTime.now().uptimeNanoseconds
            onMain {
                self.stats.hop(posted)                        // run-loop lag, §4.4
                guard let l = self.current(id) else { return }
                guard let d = data else { self.end(id, l, error: ContentError.read(body.path)); return }
                l.task.didReceive(d)
                if part.upperBound < rest.upperBound { self.pump(id, body, part.upperBound ..< rest.upperBound, hasher: h); return }
                if let h = h, !h.matches() { self.end(id, l, error: ContentError.sha(body.path)); return }
                self.end(id, l, error: nil)
            }
        }
    }
    private func end(_ id: ObjectIdentifier, _ l: Live, error: Error?) {
        live[id] = nil
        if let e = error { l.task.didFailWithError(e) } else { l.task.didFinish() }
        stats.done(l, error: error)
    }
    func snapshot() -> [String: Any] { stats.snapshot(inFlight: live.count) }
}

extension ContentSchemeHandler: WKURLSchemeHandler {
    func webView(_ webView: WKWebView, start urlSchemeTask: WKURLSchemeTask) { startTask(webView, urlSchemeTask) }
    func webView(_ webView: WKWebView, stop urlSchemeTask: WKURLSchemeTask) { stopTask(urlSchemeTask) }
}
```

**Isolation** (review #2).
- The SDK marks `WKURLSchemeHandler` with `WK_SWIFT_UI_ACTOR` (`WKURLSchemeHandler.h:38`); `WKURLSchemeTask` has no
  such mark.
- If the class conformed in its primary declaration, Swift would infer `@MainActor` for the whole class. Its `init`
  and `snapshot()` would then be hard errors when called from the nonisolated `ContentSource` and `AppDelegate`.
  That is the same error class as the R12 break (aae19eb).
- Reproduced with Swift 6.0.3, `-swift-version 5`, protocol in a separate module:
  - with `@MainActor` on the protocol: `call to main actor-isolated initializer 'init(store:)' in a synchronous
    nonisolated context`;
  - with the conformance in an extension: 0 diagnostics with all three protocol variants (none, `@MainActor`,
    `@preconcurrency @MainActor`), including the nonisolated callers.
- The skeleton above (fast path, `Live` with a weak web view, pump) was type-checked the same way: 0 errors and 0
  warnings in all three variants.

**Why bodies above 256 KB are still sent as fast as possible.**
- WebKit `main` arms a 10-second timer when a media request starts and stops it only when the request finishes.
  Data does not reset it (`WebCoreAVFResourceLoader.mm:60, 381, 447-460, 497-507`). So a response must be complete
  and quick; pacing a large body to the video bitrate is not allowed.
- Decrypting 512 KB takes ≈ 0.3–0.5 ms [estimate].
- When AVFoundation has enough data, WebKit calls `finishLoading`/`stopLoading` and we receive `stop`.

**Timeouts.**
- A main thread blocked for more than 10 s fails the video request; the engine's existing `VID_BACKOFF` retry covers
  that.
- Open menus and modal alerts do not stop our hops: we use common-modes run-loop blocks, and `HostAlert` already
  runs from a timer.

**WebContent death and window close.**
- On WebContent death, WebKit calls `stop` for every task of the page (`stopAllURLSchemeTasks(process)`).
- On **release** of the WKWebView (`WallpaperWindow.close()` sets `window.contentView = nil`; `LayersTestWindow` is
  freed after closing), `WebPageProxy::close` → `stopAllURLSchemeTasks` → `platformStopTask` finds
  `page.cocoaView()` nil and **does not call the handler**, only `suppressTaskStoppedExceptions()`
  (`WebURLSchemeHandlerCocoa.mm:56-63`, `WebPageProxy.cpp:2117`, `WebURLSchemeTask.cpp:78-79`). Without the weak
  web view, the pump would decrypt the rest of the range (up to 23 MB) for nobody and the counters would be wrong.
  With it, the pump ends within one chunk and `live` drains (`orphaned` +1).

### 4.4 Счётчики и журнал

**Counters** (main thread only; they go into diagnostics as `host.pack.requests`):

| Field | Meaning |
|---|---|
| `requests`, `ok200`, `partial206`, `notFound`, `badRange`, `failed`, `cancelled`, `orphaned`, `fastPath` | request outcomes. `cancelled` = `stop` before the end; `orphaned` = page released without `stop` |
| `bytes`, `mediaBytes` | bytes served |
| `inFlight`, `maxInFlight` | live (pumped) tasks |
| `latencyMs` per media path (`assets/reef_day.mp4`, …): `{p50, p95, max, n}` | start → finish, over a ring of the last 512 requests of that path |
| `sizes` per media path: `{le4K, le64K, le256K, gt256K}` | request-size histogram |
| `hopMs {p95, max}` | io-done → main-block-run lag of the pump; the direct measure of main-thread starvation |
| `missing` | last 10 distinct 404 paths |

**Log.**
- A 404 gives one `Log.error` per path per run.
- Pack open gives `Log.info("content: pack v1 id=… 64 entries 78.8 MB, web 4, opened in 3 ms")`.
- The cache clear gives `Log.info("content: disk cache cleared in N ms")` (§4.6).
- Dev builds only: the hidden setting `aq.content.trace` writes **one aggregated line per second per page**, for
  example `content: 1s n=96 bytes=3.1MB maxMs=0.4 206=96`. It does not log every request; at about 100 requests/s,
  per-request `notice` lines would flood the persisted log.

### 4.5 Регистрация

- `ContentSource.shared.install(on: config)` runs **before** `WKWebView(frame:configuration:)` and calls
  `config.setURLSchemeHandler(handler, forURLScheme: "aquarium")`.
- Each window has its own configuration, so a double install is a programmer error.
- There is one handler for the app. Tasks are told apart by `ObjectIdentifier`; the `Live` entry also holds the
  web view weakly.

### 4.6 Хранилище и кэш на диске (план А, по умолчанию)

- **Store:** `WKWebsiteDataStore.default()` as today. `localStorage` (the governor's memory) survives restarts.
- **Clearing the disk cache at launch** (review #5 and #11). In `applicationDidFinishLaunching`:
  ```swift
  ContentSource.shared.prepare()        // open + validate the pack (§1.3); on error: HostAlert, state .waiting
  let t0 = Date()
  var launched = false                                      // whichever comes first: completion or fallback
  let go = { [weak self] in
      guard let self = self, !launched else { return }
      launched = true
      ContentSource.shared.cacheClearMs = Int(Date().timeIntervalSince(t0) * 1000)
      self.applyScreens(); self.started = true            // moved here from the end of launch
  }
  WKWebsiteDataStore.default().removeData(ofTypes: [WKWebsiteDataTypeDiskCache], modifiedSince: .distantPast) { go() }
  DispatchQueue.main.asyncAfter(deadline: .now() + 2) { go() }   // fallback if the completion never comes
  ```
  - The Objective-C completion handler is non-null, so Swift has no overload without it, and a call without one does
    not compile (`WKWebsiteDataStore.h:82`).
  - It is asynchronous: the media-cache folder is removed on a work queue (`WebsiteDataStore.cpp:922-927`), with
    `removeItemAtURL:` of the whole `AVAssetCache` directory when `modifiedSince` is `distantPast`
    (`MediaPlayerPrivateAVFoundationObjC.mm` `clearMediaCache`). If windows started first, the GPU process could
    create an asset cache in a folder that is being deleted. That race has an unknown outcome, so windows wait for
    the completion. The wait is bounded at 2 s and shown as `cacheClearMs`. A DiskCache removal launches the network
    process, which the pages need anyway, and it does not kill web processes (`WebsiteDataStore.cpp:844-868, 929-948`).
  - `localStorage` is another data type and is not touched.
  - The completion closure runs on the main thread (`WK_SWIFT_UI_ACTOR` block).
- **`plaintextScan` in diagnostics** (review #11). It answers «is there decrypted stock on disk?». It runs on a
  `.utility` queue at most once per 60 s; diagnostics show the last result and its age.
  - **App-owned roots:** `$TMPDIR/<bundle-id>/` (WebKit `main` puts `MediaCache` there), `~/Library/Caches/<bundle-id>/`
    (older WebKit, research A), `~/Library/WebKit/<bundle-id>/`, and `$(getconf DARWIN_USER_CACHE_DIR)/<bundle-id>/`.
    In the MAS sandbox these paths already resolve inside the container (`Data/tmp`, `Data/Library/Caches`,
    `Data/Library/WebKit`).
  - For each regular file (cap 5000) read the first 12 bytes. **`matches`** counts MP4 (`ftyp` at bytes 4–8), JPEG
    (`FF D8 FF E0|E1|DB`) and PNG (`89 50 4E 47`) headers. Files over 1 MB are counted separately as `large`, for
    information only: Metal shader caches live there too.
  - **Shared temp** (non-sandboxed only): in the whole `$TMPDIR`, files ≥ 64 KB modified since launch whose first
    64 bytes equal the first 64 plaintext bytes of any pack media entry count as **`tmpMatches`**. This is exact, so
    other apps' JPEGs and MP4s are never counted.
  - Result: `{files, bytes, matches, tmpMatches, large, examples[≤3 relative paths], ms, at}`. M6 passes only with
    `matches = 0` and `tmpMatches = 0`.

### 4.7 План Б (только если M6 найдёт файлы)

`config.websiteDataStore = ContentSource.shared.ephemeralStore`: **one** `WKWebsiteDataStore.nonPersistent()` for
the whole app lifetime.
- For an ephemeral session WebKit itself sets `AVURLAssetUsesNoPersistentCacheKey = YES`
  (`HTMLMediaElement.cpp:9111-9117`, `MediaPlayerPrivateAVFoundationObjC.mm:972-979`), so nothing goes to disk.
- Cost: `localStorage` lives only until quit. The app then keeps the governor's memory: once a minute and on pause
  it reads `aquariumPerfSnapshot().gov` {key, level} into UserDefaults `aq.govMemory`, and passes the level of the
  current pair back through the existing `__AQ_BOOT.govLevel` (`index.html:281-285`). The engine is unchanged.
- `sessionStorage` (the black box) survives a WebContent death in an ephemeral session too, because it does not live
  in the page process.

## 5. Изменения приложения

| File | Change |
|---|---|
| **new** `Sources/PackFormat.swift` | header; index (Codable); validation (§1.3); CTR alignment; nonce; MIME; `ContentRoute.plan`; `PackStore` (`open`/`pread`/`read`/`hasher`/`verifyAll`); PNG/JPEG/MP4 header parsing for the gates. Foundation only, shared by the app, `aqpack` and the tests |
| **new** `Sources/PackCipher.swift` | `PackCrypto` on CommonCrypto (§2.1) |
| **new** `Sources/ContentSchemeHandler.swift` | §4.2–4.4, `onMain`, `ContentStats`. Foundation and WebKit only, so Linux can check it against a fake WebKit |
| **new** `Sources/ContentSource.swift` | source choice; `prepare()`; `install(on:)`; `pageURL(_:)`; `has(_:)`; `cacheClearMs`; deferred `verifyAll`; `plaintextScan`; `snapshot()`; one-time alert on error |
| `WallpaperWindow.swift` | `install(on: config)` before creating the `WKWebView`. In `load()`: source `file` → `loadFileURL` as now; otherwise `webView.load(URLRequest(url: ContentSource.shared.pageURL("index.html")))`. Source not ready → `Log.error` and `state = .waiting`, no retry loop. `hostInfo()` gains `"url": webView.url?.absoluteString` |
| `LayersTestWindow.swift` | the same; `init?` returns `nil` when `!ContentSource.shared.has("spike/layers.html")` |
| `AppDelegate.swift` | launch sequence of §4.6; `hostState()` gains `"pack": ContentSource.shared.snapshot()`; under `#if AQ_RELEASE` the three ⌥ test items (Тест производительности, Тест слоёв, Задник слоями) are not created |
| `Lifecycle.swift` | `AppSettings.content` (`aq.content`: `pack` default, `folder`, `file`), `contentTrace`; under `#if AQ_RELEASE` both and `inspectable` return the defaults (`pack`, `false`, `false`) and the keys are never read |
| `Resources/Info.plist` | `ITSAppUsesNonExemptEncryption` = `false`, with an XML comment pointing to §11 |

**Content sources** (`aq.content`; dev builds only, release is always `pack`):
- `pack` is the default.
- `folder`: the same handler and origin, with bytes from the loose `Contents/Resources/aquarium/`. That folder exists
  only after `./build.sh --loose`. It separates handler problems from pack problems. If the folder is missing, the app
  uses `pack` and logs a line.
- `file`: the old `loadFileURL` path from the same loose folder. It is the emergency exit if the scheme misbehaves
  on some macOS.

```sh
defaults write com.gregorydich.aquariumwallpaper aq.content -string folder   # with ./build.sh --loose --run
defaults delete com.gregorydich.aquariumwallpaper aq.content                   # back to the pack
```

**Diagnostics field `host.pack`:**

```json
{"source":"pack","file":"content.aqp","format":1,"id":"3fa2…","entries":64,"web":4,"bytes":78790000,"kind":"dev",
 "keyOK":true,"openMs":3,"cacheClearMs":140,"error":null,
 "verify":{"ok":true,"ms":160,"bad":[]},
 "requests":{"requests":4120,"ok200":71,"partial206":4040,"notFound":0,"badRange":0,"failed":0,"cancelled":6,
             "orphaned":0,"fastPath":4050,"bytes":118000000,"mediaBytes":88000000,"inFlight":0,"maxInFlight":9,
             "latencyMs":{"assets/reef_day.mp4":{"p50":0.2,"p95":0.6,"max":9,"n":512}},
             "sizes":{"assets/reef_day.mp4":{"le4K":30,"le64K":3900,"le256K":40,"gt256K":12}},
             "hopMs":{"p95":0.3,"max":4},"missing":[]},
 "plaintextScan":{"files":3,"bytes":41000,"matches":0,"tmpMatches":0,"large":0,"examples":[],"ms":12,"at":"…"}}
```

`FeedbackReport` may add `pack.id`; it contains no personal data.

## 6. Движок не меняется

- `aquarium/index.html`, `scene/*.js`, `fish/manifest.js` and `spike/layers.html` are unchanged.
- The test-only paths `../tools/aquarium-test/media/…` (only with `?test`) get a 404 through the scheme, as they
  should.
- The comment at `index.html:922-923` about `file://` tainting the canvas becomes outdated for the app. Editing it
  is optional: the harness still runs over `file://`.
- Optional, later: the app passes `__AQ_BOOT.govLevel` so that the governor's memory is not lost even once. That is
  app code; the engine already supports it.

## 7. Тестовый путь прежний; харнесс проверяет пакет

- Everything that worked still works: `node still.js …` over `file://`, `--http`, and all gates.
- The harness gets a **third** mode, `--pack <dir> --pack-key <file>`, in `lib.openEngine`. `<dir>` is a staged
  `Resources` layout (`web/` + `content.aqp`) produced by `tools/pack-test/run.sh` with the test key, so the
  whitelist is exercised too.
- The new `tools/aquarium-test/packserve.js` serves that layout on 127.0.0.1:
  - `web/` files as they are;
  - media decrypted **with OpenSSL** (`crypto.createDecipheriv('aes-256-ctr', K, IV)`), an implementation
    independent of the Swift packer;
  - 200/206/404/416/HEAD with the same headers, driven by `range_cases.json`;
  - a request log (`path`, `range`, `status`, `bytes`) available to scripts.
  - `http://127.0.0.1` is a secure context with a tuple origin, the closest Chromium analogue of
    `aquarium://localhost`.

**New `pack_check.js`, gates:**
1. **Bytes.** Every entry fetched by GET equals its source (SHA-256), plus 50 random ranges per media file and every
   case in `range_cases.json`.
2. **Completeness.**
   - On the pack, `still.js` (day/night, `--vlayer 0/1`, 1920×1200 and 1512×982@2), `perf.js` (live part: real rAF,
     MP4, video loop, watchdog), `blackbox.js` (several processes, renderer kill) and `gates_v2.js` all pass with
     `errors: none`.
   - From the server log: 0 responses 404; every requested path is in the pack or in `web/`; the mp4 got 206
     responses.
   - Entries never requested are listed for information. The photo-scene fallbacks and the second theme are expected
     there.
3. **Frames.**
   - `still.js --q nobg=1`: pack vs `file://`, bit-identical (the procedural reef is deterministic).
   - Video scene, using the method of `perf.js` and `layers_psnr.js`: one page, `__aq.pause(true)`, the same `simT`,
     `__aq.invalidate()`, a frame. The gate is bit-identical or PSNR ≥ 60 dB; the noise source is the order of async
     loads (see the harness README).
   - `--q "bgvideo=mp4&theme=night"`: a decoded MP4 frame from the pack equals the one from the file.
4. **Whitelist.** The staged layout is exactly 64 pack entries plus 5 `web/` files (dev), or 64 plus 4 (`--release`).

Add a section «Пакет (R9)» to the harness `README.md`: how to build the test pack (`tools/pack-test/run.sh`), the
flags and the reference numbers.

## 8. `build.sh` и `release.sh`

**`build.sh`, step order** (Russian messages, in the style of the file):

```
▸ Очистка
▸ Info.plist
▸ Ключ пакета        .packkey есть → «ключ: macos-app/.packkey»; нет → aqpack keygen, «в git не попадает»
▸ Упаковщик          swiftc -O -swift-version 5 pack/main.swift Sources/PackFormat.swift Sources/PackCipher.swift -o build/tools/aqpack
▸ Упаковка           build/tools/aqpack build … --out "$CONTENTS/Resources/content.aqp" --web-out "$CONTENTS/Resources/web" --swift-key build/gen/PackKey.swift
                     → «64 медиафайла, 78,8 МБ → content.aqp (id 3fa2…); код: 5 файлов → web/; реестр ok; разрешение ok; текст ok»
▸ Проверка пакета    build/tools/aqpack verify … → «✓ Пакет проверен: 64 из 64, шум без сигнатур, сборка повторяема (1,4 с)»
▸ Компиляция Swift   swiftc … Sources/*.swift build/gen/PackKey.swift [-D AQ_RELEASE]
▸ (--loose) рыхлая копия aquarium/ — ТОЛЬКО для отладки (aq.content folder|file)
▸ Проверка бандла    build/tools/aqpack scan "$OUT" [--allow-loose]
✓ Готово
```

- Remove the `cp -R ../aquarium …` line and the deletions after it: the packer's whitelist replaces them.
- Parse arguments in a loop: `--run`, `--sign "…"`, `--loose`. Today only `$1` is parsed.
- `AQ_BUILD=release` in the environment means `--release` for the packer and `-D AQ_RELEASE` for `swiftc`.
- Build time grows by ≈ 10 s [estimate]: compiling the packer with `-O` takes ≈ 6–8 s, packing and verification
  ≈ 1–2 s. The verify line prints the measured seconds.
- `.gitignore`: add `macos-app/.packkey`. `build/` and `dist/` are already there.

**`release.sh`, after the build** (next to the architecture check):
1. **Repository not public** (review #9). Probe the repository the release is built from:
   ```sh
   slug=$(git remote get-url origin | sed -E 's#^(https://github.com/|git@github.com:)##; s#\.git$##')
   code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "https://github.com/$slug")
   [ "$code" = 404 ] || fail "Репозиторий $slug открыт всем (ответ $code): стоковые медиа скачиваются с GitHub. Сделайте его приватным: GitHub → Settings → Change visibility. Без сети проверку не пройти — повторите при подключении."
   ```
   - Unauthenticated `curl` gets 404 for a private repository and 200 for a public one. It needs no `gh` login.
   - The review's raw URL `…/main/aquarium/assets/reef_day.mp4` cannot be used. It answers 404 today because `main`
     has no such file, while the working branch serves it with 206 (checked 22.10). It would pass while the media are
     public.
2. `Contents/Resources/content.aqp` and `web/` exist; `Contents/Resources/aquarium` does **not**.
3. `build/tools/aqpack scan "$APP_PATH"` without `--allow-loose`.
4. `plist_get ITSAppUsesNonExemptEncryption` = `false`.
5. `build/pack-manifest.json` has `"kind":"release"` and every gate `ok`. The test-key gate already stopped the
   build if the key was the test key.
6. **Crypto comes from the OS only** (review #16): `nm -u "$APP_PATH/Contents/MacOS/$APP" | grep -q _CCCryptorCreateWithMode`
   must succeed, and the binary must not contain the AES S-box prefix
   (`LC_ALL=C grep -qa "$(printf '\x63\x7c\x77\x7b\xf2\x6b\x6f\xc5')" "$BIN"` must fail).
7. **Signing** is unchanged: the pack and `web/` are ordinary sealed resources, and `codesign --verify --deep --strict`
   (already there, twice) catches any substitution.
8. **Release notes:** add the line «Пакет: content.aqp, id …, 64 файла, SHA-256 …», and copy the manifest to
   `dist/$APP-$VERSION.assets.json`.
9. **«No nested code»** is unchanged: `aqpack` lives in `build/tools`, not in the `.app`.

## 9. «Только экранное разрешение»

Adobe's terms have no such rule; it is risk reduction. Current sizes:

| Asset | In the build | Original | Share of pixels |
|---|---|---|---|
| Video 188049047, day and night loops | 2560×1440 | 3840×2160 | 44 % |
| Posters `reef_{day,night}.jpg` | 2560×1440 | frames of the same loop | 44 % |
| `reef_bg.jpg` (264961754) | 2560×1355 | 5760×3048 | 20 % |
| Fish cut-outs | up to 1000 px | photos 5184×3456 and similar | a few % |
| Colonies and props | up to 1200 px | photos 4–6 thousand px | a few % |
| Masks | up to 1392 px | derived from the video | — |

**Decision.**
- Keep the current sizes.
- No stock derivative above 2560 px on the long side (video: 2560×1440). The packer gate (§3.4) stops a silent breach.
- Never ship the 4K stock video: that would be the original at full quality.
- Higher tiers only from our own assets (our own Eilat backdrop, R8+); the gate passes them by the `own` licence.

## 10. Без «сохранить обои»; инспектор

**Checked in the code on 22.10:**
- `macos-app/Sources` has no `NSSavePanel`, `setDesktopImageURL`, `NSSharingService`, image drag-out, or frame
  writing.
- The engine has no `download`, `createObjectURL` or `Blob`. The only `toDataURL` is the test-only
  `__aq.flakeSprites()`, which renders procedural food flakes, not stock.

**Feedback snapshot** (allowed; the rules stay):
- taken with `WKWebView.takeSnapshot` (`Diagnostics.swift`);
- a finished frame of the whole scene, JPEG ≤ 1600 px, ≤ 400 KB, saved as `<id>.jpg` in
  `~/Library/Application Support/AquariumWallpaper/Feedback/`;
- main screen only; never a bare video frame or sprites.

**Rule for the future** (goes into R9 and the review checklist): no «save», «export», «share» or «set as desktop
picture» (that needs a file on disk), and no dragging out fish or video frames. Any such feature is for our own
assets only.

**Web Inspector.**
- `inspectable` (`Lifecycle.swift`) is compiled out under `AQ_RELEASE` (§5).
- Remote inspection of a release build is off: it uses the hardened runtime, has no `get-task-allow`, and is linked
  against a new SDK (`JSRemoteInspector.cpp:87-118`).
- **There is one bypass** (review #13). WebKit's `DeveloperExtrasEnabled` is `defaultsOverridable`
  (`UnifiedWebPreferences.yaml:1916-1922`). It is read from the app's own user defaults with the prefix
  `WebKitDebug` (`WKPreferences.mm:49`, `WebPreferencesCocoa.mm`). So any user can run
  `defaults write com.gregorydich.aquariumwallpaper WebKitDebugDeveloperExtrasEnabled -bool YES`, and then every
  WKWebView that **gets mouse events** shows «Inspect Element» in its context menu (`ContextMenuController.cpp:268`).
  The Network and Sources tabs would show decrypted resources.
- Today this is safe: wallpaper windows set `ignoresMouseEvents = true` (`WallpaperWindow.swift:151`), and the Layers
  test window (the only clickable WKWebView) does not exist in release builds.
- **Release rule:** no WKWebView that renders stock media may receive mouse events in a release build. If one ever
  must (R18 preview, R19 screensaver mode), it uses a `WKWebView` subclass whose `willOpenMenu(_:with:)` calls
  `menu.removeAllItems()`, and it repeats step M10.

## 11. Mac App Store, песочница, экспорт

- **Sandbox (R16).**
  - WebContent no longer needs a file-read sandbox extension: there is no `loadFileURL(…, allowingReadAccessTo:)`,
    and the app process serves the bytes.
  - Reading our own bundle is always allowed in the sandbox.
  - The R16 item «check WKWebView with local files» is closed by this; only the MAS build itself remains to check.
  - The media cache, if any, lives in the container (`Data/tmp/…`). `plaintextScan` covers it (§4.6).
- **Network entitlements:** not needed for content (feedback is a separate matter).
- **App Review.**
  - 2.5.2 / 2.4.5(iv): the pack is inside the bundle, and nothing is downloaded. The JavaScript ships as plain files
    in `web/`.
  - **2.5.19** (hidden features, obfuscation): the app's code is not encrypted (§1.1). Under `AQ_RELEASE` the ⌥ test
    items, `aq.content`, `aq.content.trace` and `inspectable` are **compiled out**, not merely documented. (v1 cited
    2.3.1, which is now about describing new features in the Notes for Review.)
  - 2.4.5(vi): no licence screen, no licence keys, no copy protection of the app.
  - Notes for Review: «Stock media assets (images, video) are stored in an encrypted container so the app never ships
    them as stand-alone files, as the stock licence requires. Decryption uses Apple CommonCrypto at run time. The
    app's own code is not encrypted; no licence keys or copy protection gate the app.»
  - 5.2.1: the submission comes from the holder of the licences (research B).
- **EULA on the Mac App Store** (review #14, an R16 item). Apple's Standard EULA applies unless a custom one is set,
  and it has no clause about extracting content. In App Store Connect → App Information → License Agreement, set a
  custom agreement containing `docs/legal/eula.md` §3–4, or Apple's EULA plus an addendum
  ([Apple: custom licence agreement](https://developer.apple.com/help/app-store-connect/manage-app-information/provide-a-custom-license-agreement/)).
  For the direct channel, `eula.md` is the agreement.
- **Export.**
  - `Info.plist`: `<key>ITSAppUsesNonExemptEncryption</key><false/>`.
  - Grounds:
    1. Apple: «Typically, the use of encryption that's built into the operating system—for example, when your app
       makes HTTPS connections using URLSession—is exempt». The App Store Connect table row «limited to that within
       the Apple operating system» → no documentation. The row «industry standard algorithm, not provided within the
       Apple operating system» would need the French declaration, which is why there is no Swift AES at all and why
       `release.sh` checks the binary (§8, step 6).
    2. EAR. The app uses HTTPS through URLSession (`Feedback.swift`), which is OS crypto in a mass-market item; the app
       is **not EAR99** (v1 was wrong). Pack decryption is outside «cryptography for data confidentiality» under
       Technical Note 1 to Category 5 Part 2, item (f): «encryption or decryption in support of entertainment, mass
       commercial broadcasts or medical records management» ([BIS](https://www.bis.gov/learn-support/encryption-controls/cryptography-for-data-confidentiality)).
       We rely on (f) rather than (e) DRM / copy-protected software, so as not to contradict the review note «no …
       copy protection». No Apple upload. No annual self-classification report for end-item apps since the BIS rule of
       29.03.2021 (?).
    3. Israel: the 1974 encryption order was repealed (in force March 2026 (?) for the date).
  - Apple: the interpretation is the developer's responsibility.
  - Direct channel (DMG): Apple asks nothing; the EAR analysis is the same.

## 12. Риски и откат

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | **Stock media downloadable from the public GitHub repo** | **certain, now** | **blocker:** owner makes the repo private («Решение владельца»); `release.sh` step 1 stops a release while it is public |
| 2 | Archives (Software Heritage, GH Archive, search caches) already hold copies of the public files | unknown | after going private, an agent checks archive.softwareheritage.org for the repo and files a removal request if it is there (?) |
| 3 | Video stutters through the handler (Range bugs, slow responses, main-thread latency) | medium → low after M3–M4 | fast path; run-loop hops; WebKit checks 206 for video itself (`TEST(URLSchemeHandler, Ranges)`); shared case table; `latencyMs`/`hopMs`/`vstall` in diagnostics; `aq.content folder/file` for A/B |
| 4 | «task already stopped» exception → crash | low | all task calls on the main thread under the `live` check; synchronous fast path; orphan detection; L5 with 10 000 random `stop`s and the release-without-stop case; M7 |
| 5 | AVFoundation writes decrypted video into a disk cache | unknown (undocumented) | cache cleared before windows; `plaintextScan` (M6 after 10 and after 30 min); plan B (§4.7) |
| 6 | 10-s media timeout with a busy main thread | low | fast path; common-modes hops; the engine retries video (`VID_BACKOFF`) |
| 7 | Wrong key, truncated or damaged pack, damaged `web/` | low | validation before slicing; web hashes at open; image hashes while serving; background full verify; clear alert and `pack.error`; never a trap |
| 8 | New build errors at the owner's: packer compile, registry | medium | gates only warn in dev builds; Russian messages with hints; same `swiftc` and SDK; L1 uses a Clang module shaped like the SDK |
| 9 | One-time loss of the governor's memory (new origin) | certain | the governor re-tunes in seconds; optionally `__AQ_BOOT.govLevel` |
| 10 | The owner's compiler infers isolation differently | low | conformance in an extension; no actor annotations; L1 in three variants including callers |
| 11 | GPU-process memory grows (WebKit buffers a 206 body) | low (small exact ranges) | M8. If it grows, a separate dev-only experiment with short 206 answers, with its own owner step (5 min; `vstall` 0, `verr` 0, loops rising), before any adoption: there is evidence that WebKit stalls on short answers (Actual-Chat PR #5475; `loadFinished` calls `finishLoading` regardless) |
| 12 | Media extracted by reversing the binary or a memory dump | accepted | threat model §2.3; EULA §3; MAS custom licence (§11) |
| 13 | The inspector bypass via `WebKitDebugDeveloperExtrasEnabled` | low | release rule in §10; M10 |

**Rollback.**
- **Dev build:** `./build.sh --loose` plus `defaults write … aq.content -string file` gives exactly the old
  `file://` path, with no engine rebuild.
- **Code:** the changes are isolated (4 new files, edits to the two windows, `AppDelegate`, `Lifecycle` and
  `build.sh`). Reverting one commit restores the folder copy and `loadFileURL`.
- **Release:** there are no users before v1.0. After v1.0, roll back to the previous version (Sparkle or MAS) or fix
  forward. Shipping loose files to roll back is not allowed: that would break R9.

## 13. Проверки

### 13.1 На Linux (агенты, до Mac)

- **L1. Type-check.**
  - Check all `Sources/*.swift`, the new files and a test `PackKey.swift`, with the extended `Stubs.swift`:
    `WKURLSchemeTask`, `WKURLSchemeHandler`, `setURLSchemeHandler(_:forURLScheme:)`,
    `WKWebView.handlesURLScheme`, `load(_:)`, `url`, `WKWebsiteDataStore.default()/nonPersistent()`,
    `removeData(ofTypes:modifiedSince:completionHandler:)` (completion **non-optional, no default**, so a call
    without it fails on Linux as on the Mac), `WKWebsiteDataTypeDiskCache`, `websiteDataStore`,
    `CFRunLoopGetMain`/`CFRunLoopPerformBlock`/`CFRunLoopWakeUp` with the SDK signatures, and
    `CFRunLoopMode.rawValue`.
  - **CommonCrypto rule:** never stub it as a Swift module. Use `tools/pack-test/cc/module.modulemap`
    (`module CommonCrypto [system] { header "cc.h" link "ccshim" export * }`) over a header copied **verbatim** from
    `CommonCryptor.h` and `CommonDigest.h` (anonymous enums, typedefs, `#define`s, prototypes), passed with `-I`.
    Swift then imports the constants as `Int`/`Int32`, exactly as on the Mac. A Swift stub with `UInt32` constants
    would hide the errors of review #1 until the owner's build, which is the R12 failure mode.
  - Run **three times**: protocol unannotated, `@MainActor`, `@preconcurrency @MainActor`. Each run type-checks
    `ContentSchemeHandler`, `ContentSource` and the `AppDelegate`/`WallpaperWindow` call sites (`install`,
    `snapshot`, `prepare`). Plus one run with `-D AQ_RELEASE`. Gate: 0 errors and 0 new warnings.
- **L2. Cipher, on the shipped source.**
  - Build `PackCipher.swift` with `-I tools/pack-test/cc` and link `tools/pack-test/cc/shim.c`, which implements
    `CCCryptorCreateWithMode` (CTR, AES-256, BE only, anything else `kCCUnimplemented`), `CCCryptorUpdate`,
    `CCCryptorRelease` and `CC_SHA256_*` over OpenSSL EVP.
  - Vectors: NIST SP 800-38A F.5.5/F.5.6, FIPS 180-4 («abc», empty, 1 million «a»).
  - Windows: every (a, len) over the vector, plus 1000 random (key, nonce, offset, length) against
    `openssl enc -aes-256-ctr` and Node.
  - The shim exists only under `tools/` and never builds on macOS.
- **L3. Format and packer.**
  - `aqpack build` on the real `aquarium/` with the test key, then `verify`. Two builds are identical to the byte.
  - The noise gate on 10 packs with random keys: 0 false positives.
  - Node/OpenSSL decrypts every entry back to the source bytes.
  - Gates:
    - drop a registry row → a warning, and an error code with `--release`;
    - add a 3000 px PNG with `Std` → resolution error;
    - add `LMA2` to a `web/` file → text error;
    - `--release` with the test key → refused.
  - **Corruption, never a trap** (each must give `PackError.corrupt`/a `didFail`, checked by a small Swift driver):
    - a truncated pack (cut at 10 offsets);
    - one byte flipped in the header, in the index, and in each of 5 random entries (image → sha mismatch on GET;
      video → background verify reports it);
    - one byte flipped in `web/index.html` → open fails.
  - **Timing:** build + verify of the real `aquarium/` under 5 s.
- **L4. Routes.** `range_cases.json` against `ContentRoute.plan` (Swift) and `packserve.js` (Node): the same
  statuses, ranges and headers.
- **L5. Handler simulation.**
  - Build `ContentSchemeHandler.swift`, `PackFormat.swift`, `PackCipher.swift` and the shim with a fake `WebKit`
    module whose task records calls. Drive it on the main `RunLoop`.
  - Scenarios:
    - full GET of 23 MB; Range; HEAD; 404; 416; missing document → `didFail`;
    - `stop` before the response and between chunks;
    - **page released without `stop`**: drop the fake web view mid-pump → the pump ends within one chunk, `live`
      drains, `orphaned` +1, no later task calls;
    - **about 3000 sequential 40 KB ranges**, each issued after the previous finishes (the AVFoundation pattern):
      every one takes the fast path, exactly one run-loop turn per request, no live entries;
    - 10 000 tasks with random `stop`.
  - On Linux the sim module also provides `CFRunLoopGetMain`/`CFRunLoopPerformBlock`/`CFRunLoopWakeUp` over
    `RunLoop.main`, because corelibs Foundation does not export them. Apple's modal-loop behaviour therefore cannot be
    simulated here; M4 checks it with the menu and window sub-step.
  - Assertions: no call after `stop`/finish/orphan; exactly one terminal call; bytes equal the source; time for 23 MB.
- **L6. Harness:** `pack_check.js` (§7), all gates.
- **L7. Bundle.** Reproduce the `build.sh` layout in a folder and run `aqpack scan`:
  - without `--loose` there are no loose media;
  - with `--loose` there are, and `scan` without `--allow-loose` fails;
  - a stray `foo.png` anywhere fails, and so does a renamed MP4 without an extension.

### 13.2 На Mac владельца (≈ 40 мин, из них ≈ 25 — ожидание)

Перед началом: Mac подключён к сети, тяжёлые программы закрыты.

| Шаг | Что сделать | Что должно получиться (агент читает диагностику) |
|---|---|---|
| M1 | Рыбка → «Выход». Терминал: `cd ~/GregoryDich && git pull && cd macos-app && ./build.sh --run` | В выводе есть «▸ Упаковка … 64 медиафайла, 78,8 МБ» и «✓ Пакет проверен: 64 из 64, шум без сигнатур, сборка повторяема (N с)». В первый раз — «создан новый ключ». Если есть «✗» или `error:`, прислать в чат последние 30 строк и дальше не продолжать |
| M2 | Посмотреть на рабочий стол; Рыбка → «Тема аквариума» → «Всегда ночь», через 5 с — «Как в системе» | Аквариум на всех экранах как раньше; переход в ночь и обратно |
| M3 | Рыбка → «Скопировать диагностику» → вставить в чат | `host.pack.source` = `pack`, `entries` 64, `keyOK` true, `error` null, `cacheClearMs` < 2000; `requests.notFound` 0, `failed` 0; `windows[].url` = `aquarium://localhost/index.html`; `snapshot.video.day.fps` ≈ 30 |
| M4 | Ничего не трогать 10 мин. Затем, пока идёт видео: открыть меню рыбки и закрыть; «Скопировать диагностику»; «Написать отзыв…» → закрыть окно. Снова диагностика | `video.*.loops` ≥ 25, `verr` 0, `vstall` 0 (и после подшага с меню и окнами); `notFound` 0; для `assets/reef_*.mp4`: `latencyMs.p95` < 5, `max` < 100; `hopMs.max` < 100; `verify.ok` true |
| M5 | ⌥ + рыбка → «Задник слоями (тест)» (галочка) → 10 мин → диагностика → снять галочку | То же для `vlayer: true`; страницы перезагрузились (`loadReason` `vlayer`) |
| M6 | Та же диагностика | `plaintextScan.matches` = 0 и `tmpMatches` = 0. Если не 0 — план Б (§4.7). Повторить после M8 |
| M7 | «Мониторинг системы» → строка «… Web Content» (или `com.apple.WebKit.WebContent`) → ⓧ → «Завершить принудительно» | Аквариум вернулся за 1–5 с; `lifecycle.wcTotal` +1, есть `prevSummary`. В «Консоли» (поиск `AquariumWallpaper`) нет `NSInternalInconsistencyException` |
| M8 | «Мониторинг системы» → «Память»: AquariumWallpaper, «… Web Content», «… Graphics and Media» — снимок экрана сейчас и через 20 мин; затем диагностика | Память не растёт; у процесса GPU нет скачка на +25 МБ на каждый оборот петли; `plaintextScan` снова 0 / 0 |
| M9 | ⌥ + рыбка → «Тест слоёв» → окно открылось, видео идёт → закрыть → через 10 с диагностика | Работает как раньше; `requests.inFlight` 0 (задачи закрытого окна не висят) |
| M10 | Терминал: `defaults write com.gregorydich.aquariumwallpaper WebKitDebugDeveloperExtrasEnabled -bool YES` → Рыбка → «Выход» → `open build/AquariumWallpaper.app` → правый клик по пустому месту рабочего стола → затем `defaults delete com.gregorydich.aquariumwallpaper WebKitDebugDeveloperExtrasEnabled` | Правый клик открывает обычное меню Finder, а не «Inspect Element»: обои клики не получают |
| M11 | Рыбка → «Выход», запустить снова (`./build.sh --run` или из `build/`) → через 2 мин диагностика | `snapshot.gov.stored` не `null`: память регулятора на новом origin сохранилась между запусками |
| M12 | Finder → `macos-app/build/AquariumWallpaper.app` → ПКМ «Показать содержимое пакета» → Contents → Resources | Видны `content.aqp`, папка `web` (4–5 файлов `.html`/`.js`) и служебные файлы; ни одной картинки или видео; пробел (Quick Look) на `content.aqp` ничего не показывает |

Если в M3 или M4 что-то не так: прислать диагностику, затем
`defaults write com.gregorydich.aquariumwallpaper aq.content -string folder`, `./build.sh --loose --run`,
снова диагностику. Это сразу покажет, где ошибка — в обработчике или в пакете.

## 14. План работ

Each step ends with its gate; a failed gate blocks the next step. Other agents edit `macos-app/Sources` and
`build.sh` in parallel, so the implementer rebases onto the latest commit before steps 5–6 and re-runs L1 after the
rebase.

| # | Step | Files | Gate |
|---|---|---|---|
| 1 | SDK-shaped CommonCrypto module and OpenSSL shim | new `tools/pack-test/cc/{module.modulemap, cc.h, shim.c}`, `tools/pack-test/run.sh` (build helpers) | `cc.h` diffed against `CommonCryptor.h`/`CommonDigest.h` declarations; the literal v1 call fails, the §2.1 form compiles |
| 2 | Cipher | new `macos-app/Sources/PackCipher.swift` | L2 |
| 3 | Format, validation, route, store | new `macos-app/Sources/PackFormat.swift`, `tools/pack-test/range_cases.json` | L4 (Swift half); unit driver for validation |
| 4 | Packer | new `macos-app/pack/main.swift`, `tools/pack-test/test.packkey`, `tools/pack-test/TestPackKey.swift` | L3 (determinism, noise gate × 10 keys, corruption cases, gates, test-key refusal, < 5 s) |
| 5 | Handler and source | new `macos-app/Sources/ContentSchemeHandler.swift`, `ContentSource.swift`; `tools/pack-test/WebKitSim/WebKit.swift`, `HandlerSim.swift` | L5; L1 three variants |
| 6 | App wiring | `WallpaperWindow.swift`, `LayersTestWindow.swift`, `AppDelegate.swift` (launch sequence §4.6, `hostState`, ⌥ items under `AQ_RELEASE`), `Lifecycle.swift` (`aq.content`, `contentTrace`, release defaults), `Resources/Info.plist`; Stubs extensions in the type-check kit | L1 (three variants + `-D AQ_RELEASE`), 0 errors |
| 7 | Build and release scripts | `macos-app/build.sh`, `macos-app/scripts/release.sh`, `.gitignore` (`macos-app/.packkey`) | L7; `release.sh --dry-run` on Linux shows the new steps; `bash -n` both scripts |
| 8 | Harness pack mode | new `tools/aquarium-test/packserve.js`, `pack_check.js`; `lib.js` (`--pack`, `--pack-key`) | L4 (Node half), L6 |
| 9 | Docs | `docs/licences/ASSETS.md` header («упаковывается в content.aqp», the gate), `macos-app/README.md`, `aquarium/README.md` (bundle section), `tools/aquarium-test/README.md` («Пакет (R9)»), `ROADMAP.md` (R9 status; «no export» rule; R16: MAS custom EULA; precondition: private repo) | review |
| 10 | Owner protocol on the Mac | — | M1–M12 |
| — | Owner action, any time before release | GitHub visibility (Решение владельца) | `release.sh` step 1 |

| File | New / edit | Lines [estimate] |
|---|---|---|
| `macos-app/Sources/PackFormat.swift` | new | 380 |
| `macos-app/Sources/PackCipher.swift` | new | 60 |
| `macos-app/Sources/ContentSchemeHandler.swift` | new | 300 |
| `macos-app/Sources/ContentSource.swift` | new | 280 |
| `macos-app/pack/main.swift` | new | 420 |
| `WallpaperWindow.swift`, `LayersTestWindow.swift`, `AppDelegate.swift`, `Lifecycle.swift` | edits | ≈ 90 |
| `macos-app/Resources/Info.plist` | edit | 4 |
| `macos-app/build.sh`, `macos-app/scripts/release.sh`, `.gitignore` | edits | ≈ 110 |
| `tools/pack-test/` (`cc/`, `test.packkey`, `TestPackKey.swift`, `WebKitSim/`, `HandlerSim.swift`, `CorruptDriver.swift`, `run.sh`, `range_cases.json`) | new | ≈ 650 |
| `tools/aquarium-test/packserve.js`, `pack_check.js`; `lib.js` | new and edit | ≈ 350 |

**Total:** ≈ 1450 lines of Swift in the app and the packer, ≈ 1000 lines of tests. **≈ 3.5 agent days**:
- format, cipher and packer: 1.2 days;
- handler and app: 1.2 days;
- tests, harness and docs: 1.1 days.

Then ≈ 40 minutes of the owner's time (§13.2). This can run in parallel with R8 (own backdrop): replacing the video
means replacing files in `aquarium/`, and the packer picks them up.

## Источники

**WebKit (GitHub, `main`, read 21–22.10.2026):**
- [WebCoreAVFResourceLoader.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/platform/graphics/avfoundation/objc/WebCoreAVFResourceLoader.mm): 10-s timer l.60, 381, 447–507; `setEntireLengthAvailableOnDemand` l.428–434.
- [MediaPlayerPrivateAVFoundationObjC.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/platform/graphics/avfoundation/objc/MediaPlayerPrivateAVFoundationObjC.mm): `clearMediaCache` l.368–385; `AVURLAssetUsesNoPersistentCacheKey`/`AVURLAssetCacheKey` l.902–1040.
- [HTMLMediaElement.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/html/HTMLMediaElement.cpp): l.9111–9117.
- [WebsiteDataStore.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/WebsiteData/WebsiteDataStore.cpp): l.844–868, 922–948.
- [WKWebsiteDataStore.h](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKWebsiteDataStore.h): l.82.
- [WebsiteDataStoreCocoa.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/WebsiteData/Cocoa/WebsiteDataStoreCocoa.mm): l.225, 446–451, 555–575.
- [WebsiteDataStoreConfiguration.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/WebsiteData/WebsiteDataStoreConfiguration.cpp): l.45–66, 109.
- [WKURLSchemeHandler.h](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKURLSchemeHandler.h) (l.38),
  [WKURLSchemeTask.h](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKURLSchemeTask.h),
  [WKURLSchemeTask.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKURLSchemeTask.mm),
  [WebURLSchemeTask.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/WebURLSchemeTask.cpp) (l.78–79),
  [WebURLSchemeHandlerCocoa.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/Cocoa/WebURLSchemeHandlerCocoa.mm) (l.56–63),
  [WebPageProxy.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/WebPageProxy.cpp) (l.2117, 15398).
- [RunLoopCF.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WTF/wtf/cf/RunLoopCF.cpp) (l.52–63),
  [RunLoop.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WTF/wtf/RunLoop.cpp) (l.157–169).
- [UnifiedWebPreferences.yaml](https://github.com/WebKit/WebKit/blob/main/Source/WTF/Scripts/Preferences/UnifiedWebPreferences.yaml) (l.1916–1922),
  [WKPreferences.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/API/Cocoa/WKPreferences.mm) (l.49),
  [WebPreferencesCocoa.mm](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/UIProcess/Cocoa/WebPreferencesCocoa.mm),
  [ContextMenuController.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/page/ContextMenuController.cpp) (l.268),
  [JSRemoteInspector.cpp](https://github.com/WebKit/WebKit/blob/main/Source/JavaScriptCore/API/JSRemoteInspector.cpp) (l.87–118).
- [WebLoaderStrategy.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/WebProcess/Network/WebLoaderStrategy.cpp),
  [SecurityOriginData.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/page/SecurityOriginData.cpp),
  [CachedResource.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebCore/loader/cache/CachedResource.cpp),
  [ResourceLoadStatisticsStore.cpp](https://github.com/WebKit/WebKit/blob/main/Source/WebKit/NetworkProcess/Classifier/ResourceLoadStatisticsStore.cpp).
- Tests: [WKURLSchemeHandler-1.mm](https://github.com/WebKit/WebKit/blob/main/Tools/TestWebKitAPI/Tests/WebKit/WKWebView/WKURLSchemeHandler-1.mm) (`Ranges`, `Origin`, `isSecureContext`, `NoMIMEType`).
- Bugs, from search excerpts only (bugs.webkit.org is unreachable from the sandbox): [199764](https://bugs.webkit.org/show_bug.cgi?id=199764), [203302](https://bugs.webkit.org/show_bug.cgi?id=203302), [236401](https://bugs.webkit.org/show_bug.cgi?id=236401), [202019](https://bugs.webkit.org/show_bug.cgi?id=202019).

**Implementations in the field:**
- Capacitor [WebViewAssetHandler.swift](https://github.com/ionic-team/capacitor/blob/main/ios/Capacitor/Capacitor/WebViewAssetHandler.swift) (sync local Range l.32–111; async proxy l.155–193).
- Actual-Chat [PR #5475](https://github.com/Actual-Chat/actual-chat/pull/5475) (small exact ranges on macOS; stalls on anything but an exact 206).
- wry [url_scheme_handler.rs](https://github.com/tauri-apps/wry/blob/dev/src/wkwebview/class/url_scheme_handler.rs); Tauri [asset.rs](https://github.com/tauri-apps/tauri/blob/dev/crates/tauri/src/protocol/asset.rs).

**Apple:**
- [CommonCryptor.h](https://github.com/apple-oss-distributions/CommonCrypto/blob/main/include/CommonCryptor.h): anonymous enums l.114–141, 650–688; in-place l.383–388; `CCCryptorCreateWithMode` l.744–756.
- [Mapping Files Into Memory](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/FileSystemAdvancedPT/MappingFilesIntoMemory/MappingFilesIntoMemory.html).
- [Complying with encryption export regulations](https://developer.apple.com/documentation/security/complying-with-encryption-export-regulations);
  [Export compliance documentation for encryption](https://developer.apple.com/help/app-store-connect/reference/app-information/export-compliance-documentation-for-encryption);
  [Overview of export compliance](https://developer.apple.com/help/app-store-connect/manage-app-information/overview-of-export-compliance).
- [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/): 2.3.1, 2.4.5, 2.5.2, **2.5.19**, 5.2.1 (copy saved 17.10.2026).
- [Provide a custom license agreement](https://developer.apple.com/help/app-store-connect/manage-app-information/provide-a-custom-license-agreement/).
- [removeData(ofTypes:modifiedSince:completionHandler:)](https://developer.apple.com/documentation/webkit/wkwebsitedatastore/removedata(oftypes:modifiedsince:completionhandler:)),
  [WKURLSchemeHandler](https://developer.apple.com/documentation/webkit/wkurlschemehandler),
  [WKURLSchemeTask](https://developer.apple.com/documentation/webkit/wkurlschemetask).

**Licences, export, GitHub:**
- Adobe Stock [Additional Terms 10.05.2024](https://wwwimages2.adobe.com/content/dam/cc/en/legal/servicetou/Stock-Additional-Terms_en_US_20240510.pdf) §7.1(A); [Product Specific Terms 16.01.2026](https://www.adobe.com/cc-shared/assets/pdf/legal/servicetou/stock-product-specific-terms-en-us-20260116.pdf).
- BIS [Cryptography for data confidentiality](https://www.bis.gov/learn-support/encryption-controls/cryptography-for-data-confidentiality); 2021 rule: [Jones Day](https://www.jonesday.com/en/insights/2021/04/commerce-reduces-requirements-relating-to-massmarket-encryption-items-and-publicly-available-software), [WSGR](https://www.wsgr.com/en/insights/us-department-of-commerces-bureau-of-industry-and-security-relaxes-several-classification-and-reporting-requirements-for-encryption-items.html).
- GitHub [Setting repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
- Cipher: [NIST SP 800-38A](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf) F.5.5–F.5.6; [FIPS 180-4](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf).
