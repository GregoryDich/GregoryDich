# Tonamorph plugin

The JUCE 8 / C++20 VST3 (and, on macOS, AU) instrument. It takes a dropped audio clip,
sends it to the backend for separation, transcription and analysis
([`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md) §2), and turns what comes back into a
playable, scale-snapped sampler you can drag `.mid` or `.fsc` out of.

```
Source/
  Core/        JUCE-free C++20: ScaleLock, Envelope, TransientDetector, ZeroCrossing,
               MidiFileWriter, FscWriter, Types, Strings (every user-facing string),
               SemanticVersion, FeedbackPayload, CrashReportText, ParameterText (the
               host-visible value text), Retention (NPS timing, week-one gift, referral
               line) — the code the unit tests exercise
  Cloud/       ApiClient, AuthManager, JobClient (SSE), UploadEncoder, Models, SseParser,
               RetryPolicy — everything that talks HTTP
  Engine/      SamplerEngine, StemSound/StemVoice, PitchShifter, DrumKit,
               ScaleLockProcessor, AutoAdsr — the realtime-safe instrument
  Export/      MidiExporter, FscExporter, DragExport
  App/         PluginSettings (the settings file), CrashReporter (opt-in), DemoMorph
  UI/          TonamorphLookAndFeel, ScaleKeyboard, MessageToast, FeedbackBar, VersionBanner,
               PanelOverlay → AboutOverlay, ReferralPanel; NpsCard
  PluginProcessor.{h,cpp}, PluginEditor.{h,cpp}
Resources/     generate_demo.py — builds the bundled demo morph at configure time
Tests/         tonamorph_core_tests (no JUCE) + roundtrip.py
CMakeLists.txt
```

`Source/Core` is deliberately JUCE-free and the test executable only sees `Source/`, so a
Core header that started `#include <JuceHeader.h>` would fail to compile there. That is
the mechanism keeping the DSP and music-theory layer testable without a plugin host.

## Building

Requirements: **CMake ≥ 3.22**, a C++20 compiler (g++ 13 / clang 15 / MSVC 19.3x),
**JUCE 8.0.8** and a **python3 with numpy** on the PATH (`pip install numpy`; `soundfile`
is used when present). Everything else is optional.

### The bundled demo morph

Configure runs `Resources/generate_demo.py`, which synthesises a deterministic 4-bar,
120 BPM, A-minor clip already "morphed" into the plugin's own cache format — four mono
16-bit 44.1 kHz stems (bass, drums, a pad as `other`, a formant-synthesised vocal; 2.5–4 s
each), a `score.mid` and a `result.json` carrying `"demo": true` — into `<build>/demo/`
and embeds it with `juce_add_binary_data` (about 1.2 MB, target `TonamorphDemoData`,
namespace `DemoData`). Nothing is written into the source tree; the script rewrites a
file only when its bytes change, so a reconfigure does not cause a rebuild. If numpy is
missing, configure stops with a message saying so.

### JUCE: `JUCE_SOURCE_DIR` vs FetchContent

`CMakeLists.txt` resolves JUCE in three steps:

1. `-DJUCE_SOURCE_DIR=/path/to/JUCE` — used when that directory contains a
   `CMakeLists.txt`. It is added with `add_subdirectory(... EXCLUDE_FROM_ALL)`, so
   nothing of JUCE is built that the plugin does not link.
2. If `JUCE_SOURCE_DIR` is not defined and `/home/user/deps/JUCE/CMakeLists.txt` exists,
   that checkout is used. This is a convenience for the development image; on any other
   machine the path simply does not exist and the step is skipped.
3. Otherwise `FetchContent` clones `https://github.com/juce-framework/JUCE.git` at tag
   `8.0.8` (shallow) into `<build>/_deps`. This is what CI does — the runners have no
   local checkout — which is why the workflow caches `plugin/build/_deps` between runs.

Configure prints which one it took (`Tonamorph: using JUCE from …` or
`Tonamorph: fetching JUCE 8.0.8`). Prefer a local checkout offline; a fetch needs network
on the first configure only.

### Linux

```sh
sudo apt-get install -y libasound2-dev libcurl4-openssl-dev libx11-dev libxrandr-dev \
    libxinerama-dev libxcursor-dev libxcomposite-dev libfreetype-dev \
    libfontconfig1-dev libgl1-mesa-dev librubberband-dev

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DJUCE_SOURCE_DIR=/path/to/JUCE
cmake --build build --target Tonamorph_VST3 --parallel 4
```

`JUCE_USE_CURL=1` is set, so `juce_core` calls libcurl directly; `CMakeLists.txt` links
`CURL::libcurl` (or the `libcurl` pkg-config target) itself, because the JUCE module
system does not.

### macOS

```sh
brew install cmake pkgconf rubberband
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target Tonamorph_VST3 --parallel 4
cmake --build build --target Tonamorph_AU   --parallel 4      # AU is macOS-only
```

`AU` is appended to the format list only on Apple platforms, so `Tonamorph_AU` does not
exist as a target elsewhere.

### Windows

```powershell
cmake -S . -B build -DJUCE_SOURCE_DIR=C:/dev/JUCE
cmake --build build --config Release --target Tonamorph_VST3 --parallel 4
```

Windows and macOS are multi-config generators: pass `--config Release` at build time
rather than `-DCMAKE_BUILD_TYPE` at configure time.

### Build options

| option | default | effect |
|--------|---------|--------|
| `TONAMORPH_USE_RUBBERBAND` | `ON` | Looks for `rubberband` via pkg-config. Found → `TONAMORPH_HAS_RUBBERBAND=1` and `PitchShifter` transposes stems with the Rubber Band R3 engine offline, preserving duration. Not found (or `OFF`) → `TONAMORPH_HAS_RUBBERBAND=0` and it falls back to Lagrange resampling, which changes a stem's duration by `2^(-semitones/12)`. Configure warns when it falls back, and the plugin builds and runs either way. |
| `TONAMORPH_BUILD_TESTS` | `ON` | Adds `Tests/` (`enable_testing()` + the `tonamorph_core_tests` target and its CTest entry). `OFF` drops the test executable entirely — nothing else changes, since no plugin source depends on it. |
| `JUCE_SOURCE_DIR` | *(unset)* | Local JUCE checkout; see above. |

Other targets: `Tonamorph_Standalone` (a host-free app, handy for poking at the UI) and
`Tonamorph_All`.

## Tests

### `tonamorph_core_tests` — 59 JUCE-free unit tests

```sh
cmake --build build --target tonamorph_core_tests --parallel 4
ctest --test-dir build --output-on-failure          # add -C Release on Windows/macOS
```

The binary can also be run directly (`build/Tests/tonamorph_core_tests`); it prints one
line per case and ends with `59 passed, 0 failed, 59 total`. Coverage: scale snapping and
tie-breaking (`Source/Core/ScaleLock.h`), envelope/ADSR derivation, transient detection,
zero-crossing trimming, the SMF writer, the `.fsc` writer, one combined export fixture,
semantic version ordering (the update banner), the feedback JSON payload, the crash-report
text format and its user-name scrubbing, the parameter value text (`2.0 ms` / `120 ms` /
`1.20 s`, `80 %`, `-6.0 dB` with `-inf dB` at the floor, `250 Hz` / `1.25 kHz`, `0.71`,
note names with middle C = C4 — and the tolerant, locale-independent parsers behind the
text boxes), the retention rules (the day-14 NPS window and its two-dismissal cap, the
`POST /v1/nps` body, the week-one gift heuristic, the referral strings), the strings table
(no entry over twelve words, and no product-name literal anywhere in `Source/` but
`Core/Strings.h` — the test scans the tree; a line may opt out with a `not user-facing`
comment) and the generated demo manifest (strict JSON syntax, required fields, bundle size
under 1.5 MB).

### `Tests/roundtrip.py` — the export format check

`test_export_roundtrip.cpp` writes `sample.mid`, `sample.fsc` and `fixture.json` (the
notes it serialised) into `$TONAMORPH_TEST_OUT` when that variable names a directory. The
Python script then re-reads them with third-party parsers and compares field by field:

```sh
mkdir -p /tmp/tonamorph-export
TONAMORPH_TEST_OUT=/tmp/tonamorph-export ./build/Tests/tonamorph_core_tests
python3 Tests/roundtrip.py /tmp/tonamorph-export
```

It needs `mido` and, optionally, `pyflp` (`pip install mido pyflp`). The `.mid` side
checks SMF type 1, PPQ 480, the tempo and 4/4 meta events, per-track names and channels,
and note-on/note-off ordering at identical ticks. The `.fsc` side re-implements the
`FLhd`/`FLdt` framing byte for byte and, when pyflp is importable, cross-checks the event
ids, the `FileFormat.Score` marker, the PPQ and the 24-byte note record against pyflp's
own constants, decoding the payload with `NotesEvent.STRUCT`. (Full `pyflp.parse()` fails
on Python 3.11 for an unrelated reason in pyflp itself; the script says so and falls back
to that struct rather than skipping the check.) Expected output:

```
sample.mid: OK (7 notes over 2 tracks, PPQ 480, 124.0 BPM)
sample.fsc: OK (7 note records, PPQ 96, verified with pyflp 2.2.1 NotesEvent.STRUCT)
```

The round-trip script does not run in CI; the plugin workflow builds the VST3 (and the AU
on macOS), runs `ctest`, and then validates the builds with pluginval (next section).

### pluginval

```sh
pluginval --strictness-level 5 --validate "build/Tonamorph_artefacts/Release/VST3/Tonamorph.vst3"
```

Strictness 5 is the minimum pluginval recommends and the level to ship against. On a
headless Linux box the validator still needs an X display: prefix it with `xvfb-run -a`,
or add `--skip-gui-tests` to leave the editor out of the run. Add `--repeat 2
--randomise` before a release, and `--timeout-ms "-1"` when stepping through it in a
debugger. The flags above are those of pluginval 1.0.4.

In CI (`.github/workflows/plugin.yml`) the Linux job runs that command under `xvfb-run
-a` and the macOS job validates both the VST3 and the AU — the component is copied into
`~/Library/Audio/Plug-Ins/Components` first, because an AU loads through the system
registry — each with pluginval v1.0.4 downloaded from its GitHub release; the logs are
uploaded as the `pluginval-<OS>` artifact whatever the outcome. Those steps were written
against the 1.0.4 release asset names and have not yet run on the hosted runners: the
first run is their real test.

## Install locations

`COPY_PLUGIN_AFTER_BUILD` is `FALSE`, so a build never touches a system directory. The
artefacts land in the build tree and you copy them yourself:

```
build/Tonamorph_artefacts/<Config>/VST3/Tonamorph.vst3
build/Tonamorph_artefacts/<Config>/AU/Tonamorph.component        (macOS only)
build/Tonamorph_artefacts/<Config>/Standalone/Tonamorph
```

| OS | VST3 | AU |
|----|------|----|
| Linux | `~/.vst3/` (per user) or `/usr/lib/vst3/` (system) | — |
| macOS | `~/Library/Audio/Plug-Ins/VST3/` or `/Library/Audio/Plug-Ins/VST3/` | `~/Library/Audio/Plug-Ins/Components/` or `/Library/Audio/Plug-Ins/Components/` |
| Windows | `%CommonProgramFiles%\VST3\` (`C:\Program Files\Common Files\VST3\`) | — |

A VST3 is a bundle directory on every platform, so copy it recursively (`cp -R`,
`robocopy /E`). macOS caches AU registrations: `killall -9 AudioComponentRegistrar` after
the first install if the host does not list it.

## The two-click workflow

**1 — Drop.** Drag an audio file onto the window (or click the drop zone to browse).
`UploadEncoder` trims it to 60 s, encodes FLAC on a background thread and
`JobClient` posts it to `POST /v1/jobs`; the job's progress arrives over SSE. One credit
is reserved on submission and captured only if the job succeeds (contract §2, §6). If the
known balance is already 0 the paywall opens instead and nothing is spent.

**2 — Play.** When the `result` event lands, the analysis is applied first — Scale-Snap
takes the detected key, the BPM label updates — and the selected stem is decoded and
swapped into the sampler the moment its own download finishes, before the others land
(`JobClient` reaches `Downloading` with the result parsed; the processor applies the
analysis there and loads the stem on the first notification whose WAV exists). Then play
it, and drag `.mid` or `.fsc` straight into the DAW timeline. The time from the drop to the
first playable stem is kept as `drop_to_ready_ms` and sent with a rating.

**Before any of that: the demo.** A fresh instance with nothing to restore loads the
bundled demo morph (job id `demo`, 0 credits, no network) so the keyboard plays before
sign-in; the drop zone says "Play a key. That's a morphed clip. Now drop yours." Dropping a
clip while signed out opens the sign-in with "Sign in to morph your own clips. 3 free." and
morphs the clip once the session exists.

Results are cached under `<user application data>/Tonamorph/jobs/<job_id>/`
(`result.json`, the stem WAVs, `score.mid`). The processor stores the last job id in its
state, so reopening a DAW project reloads that job from the cache without spending a
credit.

### The window, top to bottom

| section | what it holds |
|---------|---------------|
| **Banner** | Only when `GET /v1/version` (asked at most once per 24 h, cached in the settings file) reports a `latest` newer than the build: "Tonamorph x.y.z is available." with Download and Dismiss (per version); when the build is below `min_supported`, a persistent "Update required" bar instead. Every API request carries `X-Plugin-Version` and `X-Host` (the DAW, from `juce::PluginHostType`). |
| **Header** | Title, "Send a morph to a friend" (only while `GET /v1/me` carries `referral.url`), About, a Settings menu (the "Send anonymous crash reports" opt-in, default off), the credit balance (`balance.available` from `GET /v1/me`), and sign in / log out. |
| **About** | Product name and version (`TONAMORPH_VERSION_STRING`), the website link, the same crash-report opt-in as a checkbox, and "Third-party notices": `THIRD_PARTY_LICENSES.md` rendered to text at configure time by `packaging/common/eula_to_txt.py --keep-unresolved` (placeholders such as `[[COMPANY_LEGAL_NAME]]` stay verbatim until a release build sets the repository variables) and embedded with the demo morph as `DemoData::third_party_notices_txt` (configure fails above 200 KB). Scrollable, selectable, with Copy — the notice obligation of that file's action 8. |
| **Referral** | The share link from `referral.url` with Copy, "They get 5 free morphs. You get 3 when their first morph lands." and, once a friend joined, `friends_joined` / `morphs_earned`. Hidden when `/v1/me` has no `referral`. |
| **NPS card** | 14 days after the first own-clip morph (`firstMorph.atMs` in the settings file, stamped on the first fresh morph) and while signed in: "How likely are you to recommend Tonamorph? 0–10" with a comment field, floating over the keyboard. Send → `POST /v1/nps {score, comment?}`; a 409 (already answered) counts as answered; "Not now" counts a dismissal. Never again after an answer or two dismissals; offered at most once per editor session (`Core/Retention.h`). |
| **Week-one gift** | "One week in. Two morphs on us." — the `gift:week1` ledger entry is not visible through `/v1/me`, so the toast is inferred: `balance.credits` rose by exactly 2 between two balance answers and the first morph was 7–8 days ago (purchases add 50/60, referral grants 3, refunds 1). The decision sits in one editor function, `weekOneGiftArrived`, which prefers a `gifts` list in `/v1/me` whenever the server sends one. Shown once. |
| **Drop zone** | The dashed drag target for the whole window; highlights during a drag, click to open a file chooser. |
| **Progress** | A progress bar, the stage line (`upload → separate → transcribe → analyze → package`) fed by SSE, and a cancel button that drops the in-flight requests and, when the job is still
`queued`, calls `DELETE /v1/jobs/{id}` so the reservation is released (a running job
would answer `409`). |
| **Category** | Bass / Drums / Synth / Vocals — which stem the keyboard plays. "Synth" is the contract's `other` stem. |
| **Scale-Snap** | Mode (Detected, Major, Minor, PentatonicMajor, PentatonicMinor, Off) and root selectors, with the detected key and BPM shown beside them. Snapping is entirely client-side (contract §8); a note-off always uses the pitch its note-on was snapped to, even if the mode changed while the key was held. |
| **Sound** | Attack / Decay / Sustain / Release (seeded from the stem's `suggested_adsr`), filter cutoff and resonance, gain, the root-target knob (`semitones = target_root_midi − stem.root_midi`) and the drum-mode toggle that maps slices to notes from 36 upward. Knob text boxes and host parameter lists show `2.0 ms` / `120 ms` / `1.20 s`, `80 %`, `-6.0 dB` (`-inf dB` at the floor), `250 Hz` / `1.25 kHz`, `0.71` and note names (`C3`; the scale root shows `F#`), and accept the same spellings when typed (`Core/ParameterText.h`, wired through the parameters' string converters so hosts see the same text). |
| **Export + feedback** | "Drag .mid" and "Drag .fsc" — drag them into the DAW to start an external file drag, or click for a save dialog. Files are written under `<temp>/Tonamorph/exports` and cleaned up after 24 h. To the right, once a fresh morph is playable: "How was this morph?" with Good / Not good; Not good opens the reason list (bleed, wrong key, MIDI off, clicks, slow, other) and an optional 140-character note. The rating goes to `POST /v1/jobs/{id}/feedback` with `drop_to_ready_ms`; `refunded: true` shows "Morph returned." and refreshes the balance. One rating per job (remembered in the settings file); a 404 from a backend without the route is treated as sent. |
| **Keyboard** | An on-screen keyboard (`ui::ScaleKeyboard`) spanning MIDI 24–108, so the instrument is playable without a controller. A toast above it carries the onboarding hints ("Ready. Play C3 — that's your bass, in key." with C3 highlighted; "Drag .mid into your piano roll.") and the three celebrations: the first own-clip morph (in-scale keys glow for 2 s, "Your first morph. F minor · 124 BPM." with the real key and tempo), the first `.mid` drag that lands outside the window ("MIDI's in your DAW."), and the first purchase the balance poll sees ("50 morphs loaded. Thanks for backing a one-person shop." with the real count). All visual, never audio; "seen" flags live in the settings file, not in the project. |
| **Overlays** | `LoginOverlay` (email + password against `POST /v1/auth/token`), opened by the header button or by a drop while signed out, dismissible; `PaywallPrompt` when available credits reach 0, built from `GET /v1/plans` and polling `GET /v1/me` every 5 s while open. |

Every string the window shows lives in `Source/Core/Strings.h` (US English, at most twelve
words each, the exact copy of `docs/GTM_PLAN.md` Appendix B §3), including the error
mapping: 413 → "That file's over 10 MB. Try a shorter or 16-bit clip.", 415 → "That's not
an audio file we can read. WAV, MP3, FLAC work.", 429 → "Whoa, fast. Try again in a
minute.", `service_unavailable` → "Morphing is paused for maintenance. Your morphs are
safe.", `worker_unavailable` → "Engine's busy. Nothing was charged — try again shortly.",
a failed job → "That morph didn't work. Morph returned. Try again?", no network → "You're
offline. Loaded stems still play; morphing needs internet.", a lost event stream → "Lost
contact with the morph. Checking…" while polling, 401 → "Please sign in again.", a bad
password → "Wrong email or password.", an unconfirmed address → "Check your inbox to
confirm, then sign in.", the auth budget → "Too many tries. Wait a minute, then sign in.",
and a cached job whose stems are gone → "Cached stems are missing. Morph again to play."

**Paywall.** "That was your last free morph. Nothing happens unless you buy." with three
equally sized buttons — "50 morphs · $9 once" / "60 a month · $7.99/mo" / "Not now" — the
lines "Pack morphs never expire." and "Renews monthly. 60 morphs expire at period end.
Cancel anytime.", no countdowns and no scarcity. Counts and prices come from `/v1/plans`
when it answers, otherwise from the strings table; a plan without a `checkout_url` (a
freshly seeded database, see [`db/README.md`](../db/README.md)) opens the website instead,
so the prompt never appears without buttons.

**Crash reports.** With "Send anonymous crash reports" on (the Settings menu or the
checkbox on the About screen — one setting), a `juce::SystemStats` crash
handler writes plugin version, OS, host, timestamp and the stack backtrace (home directory
and user name scrubbed; never audio, tokens or project paths) to
`<user application data>/Tonamorph/crash/`. The next editor open posts each report to
`POST /v1/telemetry/crash` and deletes it; with the option off, reports older than seven
days are deleted instead. The handler is installed only after opting in, so a host's own
crash handling is untouched otherwise. Nothing runs on the audio thread.

## Pointing the plugin at a backend

The base URL defaults to `https://api.tonamorph.com` (`ApiClient::Config::baseUrl`) and is
changed programmatically with `tonamorph::cloud::ApiClient::setBaseUrl()`; there is no
user-facing setting or environment variable for it yet. Tokens (never the password) are
persisted by `AuthManager` through a `juce::PropertiesFile` named `Tonamorph.settings`
in the plugin's data directory (`AuthManager::defaultDataDirectory()`, shared with the
job cache and the crash reports): `~/Library/Application Support/Tonamorph/` on macOS,
`%APPDATA%\Tonamorph\` on Windows and `~/.config/Tonamorph/` (`$XDG_CONFIG_HOME`) on
Linux — JUCE's own default would put a Linux settings file in `~/Tonamorph/`, so the
path is resolved explicitly there.

## Threading rules

`processBlock` and `renderNextBlock` never allocate, lock or do I/O. A loaded stem is an
immutable `StemSound` built off the audio thread and published through a single
`std::atomic<std::shared_ptr<StemSound>>` per slot; the audio thread `load`s it once per
block, and retired pointers are drained on the message thread so the last reference never
drops in the audio callback. Parameters are `std::atomic` values read once per block. Nothing calls into the UI from
a worker thread either: `ApiClient` delivers every completion through
`juce::MessageManager::callAsync`, `JobClient` publishes state changes as a
`juce::ChangeBroadcaster`, the processor coalesces stem reloads with a
`juce::AsyncUpdater`, and the editor refreshes on a `juce::Timer`.
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) §7 is the long version.

## Packaging and releases

`packaging/` turns a git tag into a notarized macOS `.pkg` and a signed Windows installer,
and `.github/workflows/release.yml` runs it on every `v*` tag. Everything reads the product
identity (name, slug, bundle id, vendor, plugin codes, minimum macOS) from **one file,
`packaging/product.env`** — when the product is renamed, change that file and
`CMakeLists.txt` and nothing else. The version is the tag (`v1.2.3` → `1.2.3`; `v1.2.3-rc1`
keeps the suffix in file names and uses `1.2.3` where installers need digits) and is passed to
CMake as `-DTONAMORPH_VERSION`, so the binaries report the tagged version.

```
packaging/
  product.env                 the single source of product identity
  common/lib.sh               shared bash helpers (version, paths, DRY_RUN)
  common/eula_to_txt.py       legal/eula.md and THIRD_PARTY_LICENSES.md → installer text
  macos/  build.sh  sign.sh  auval.sh  package.sh  notarize.sh  rubberband.sh
          entitlements.plist  entitlements-standalone.plist  distribution.xml.in
  windows/ build.ps1  sign.ps1  package.ps1  rubberband.ps1  installer.iss  Common.ps1
  checksums.sh                SHA256SUMS for the release assets
```

Both builds compile Rubber Band 3.3.0 from source as a static library (`rubberband.sh` /
`rubberband.ps1`, pinned to the tag's commit): a universal macOS binary cannot link
Homebrew's single-architecture dylib, and a shipped plug-in must not depend on
`/opt/homebrew/lib`. Rubber Band is GPL-or-commercial — a closed-source release needs the
commercial licence.

### One-time setup

**Apple (macOS signing and notarization)** — needs an Apple Developer Program membership.

1. Create the two certificates: Xcode → Settings → Accounts → *Manage Certificates…* → `+` →
   **Developer ID Application** and **Developer ID Installer** (or on developer.apple.com →
   Certificates with a CSR from Keychain Access).
2. In Keychain Access select *both* certificates (with their private keys), *File → Export
   Items…*, format `.p12`, choose a password. Then
   `base64 -i certificates.p12 | pbcopy`.
3. Notarization credentials — prefer an API key: App Store Connect → Users and Access →
   *Integrations* → *App Store Connect API* → *Team Keys* → *Generate API Key*, role
   **Developer**. Note the Key ID and Issuer ID and download the `.p8` (only offered once).
   Fallback: an app-specific password from appleid.apple.com → *Sign-In and Security* →
   *App-Specific Passwords*, plus your Team ID (developer.apple.com → Membership).
4. Create these **repository secrets** (Settings → Secrets and variables → Actions):

   | secret | value |
   |--------|-------|
   | `MACOS_CERT_P12_BASE64` | the base64 from step 2 |
   | `MACOS_CERT_PASSWORD` | the `.p12` password |
   | `NOTARY_KEY_ID`, `NOTARY_ISSUER_ID` | from step 3 |
   | `NOTARY_KEY_P8` | the full contents of the `.p8` file |
   | *or* `NOTARY_APPLE_ID`, `NOTARY_PASSWORD`, `NOTARY_TEAM_ID` | Apple ID, app-specific password, Team ID |

**Windows (Authenticode)** — two options; the workflow picks Azure when its six secrets exist,
the PFX otherwise.

- *Azure Artifact Signing* (formerly Trusted Signing; open to individuals, Basic tier
  $9.99/month): in the Azure portal create an **Artifact Signing account** (region e.g. West
  Europe), complete **Identity validation → Individual** (government photo ID plus a selfie
  through Entra Verified ID; it can take a few days), then create a **Certificate profile** of
  type *Public Trust*. Create an **App registration** in Entra ID with a client secret and give
  it the *Trusted Signing Certificate Profile Signer* role on the account. Secrets:
  `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_ENDPOINT` (the account's
  endpoint URL, e.g. `https://weu.codesigning.azure.net`), `AZURE_CODE_SIGNING_ACCOUNT` (account
  name), `AZURE_CERT_PROFILE` (profile name).
- *OV certificate from a CA*: since 2023 CAs deliver OV/EV keys on hardware tokens or cloud
  HSMs, so only a certificate you can export as a software `.pfx` (or a CA cloud-signing PFX)
  works in CI. Secrets: `WINDOWS_PFX_BASE64` (`base64 -w0 cert.pfx`) and
  `WINDOWS_PFX_PASSWORD`. EV costs more and no longer buys any SmartScreen advantage.

**Licence text** — the installers embed `legal/eula.md` (licence page) and
`THIRD_PARTY_LICENSES.md` (shown in the installer and installed as
`<Product> Third-Party Notices.txt` beside the plug-in). Their `[[PLACEHOLDERS]]` are filled
from **repository variables** (not secrets — they are printed in the text):
`COMPANY_LEGAL_NAME`, `COMPANY_ADDRESS`, `COMPANY_REG_ID`, `WEBSITE_URL`, `SUPPORT_EMAIL`,
`PRIVACY_EMAIL`, `LEGAL_EMAIL`, `MERCHANT_OF_RECORD`, `EFFECTIVE_DATE`, `EFFECTIVE_YEAR`
(`PRODUCT_NAME` comes from `product.env`). A tag build fails on an unresolved placeholder. If
either Markdown file is missing the build still succeeds with a placeholder text, warns, and
puts a **DO NOT PUBLISH** banner into the release notes — never publish such a draft.

### Cutting a release

```sh
git tag -a v0.1.0 -m "First public build: ..."   # the message becomes RELEASE_NOTES.md
git push origin v0.1.0
```

Tag a commit that is green on the `plugin` workflow (the release workflow does not rerun the
unit tests). The `release` workflow then builds a universal (arm64 + x86_64) VST3 and AU on
`macos-14`, signs them with the hardened runtime, runs `auval`, builds the `.pkg`, notarizes and
staples it and checks `spctl`; builds the x64 VST3 on `windows-latest`, signs it, builds the Inno
Setup installer and signs that too; then writes `SHA256SUMS` and `RELEASE_NOTES.md` and creates a
**draft** GitHub release with `<Slug>-<version>-macOS.pkg`, `<Slug>-<version>-Windows-Setup.exe`,
`SHA256SUMS` and `RELEASE_NOTES.md`. Review the notes and the banners, then publish it by hand.

### Dry run

Actions → *release* → *Run workflow*, enter a version (e.g. `0.1.0-dry`). The same pipeline
runs; wherever secrets are absent it skips signing/notarization, labels the assets `-unsigned`
and tolerates unresolved licence placeholders. Nothing is released — the assets land in the
`<Slug>-<version>-dry-run` workflow artifact.

### Running the scripts locally

```sh
# macOS
export VERSION=0.1.0
packaging/macos/build.sh && packaging/macos/sign.sh && packaging/macos/auval.sh
packaging/macos/package.sh && packaging/macos/notarize.sh dist/*.pkg
# Windows (Developer PowerShell so cl.exe is on PATH; choco install pkgconfiglite)
packaging\windows\build.ps1 -Version 0.1.0
packaging\windows\sign.ps1 -Mode pfx -Path "build\Tonamorph_artefacts\Release\VST3\Tonamorph.vst3"
packaging\windows\package.ps1 -Version 0.1.0
```

Every script honours `DRY_RUN=1` (prints the commands it would run; works on Linux too), reads
`BUILD_DIR`/`DIST_DIR`, and auto-detects the signing identities from the keychain when
`DEVELOPER_ID_APPLICATION` / `DEVELOPER_ID_INSTALLER` are unset. `ALLOW_UNSIGNED=1` (macOS)
and `UNSIGNED=1` (Windows) build unsigned packages for testing only.

### Verifying a downloaded installer

```sh
# macOS — expect "accepted" and "source=Notarized Developer ID"
spctl -a -vv -t install Tonamorph-0.1.0-macOS.pkg
pkgutil --check-signature Tonamorph-0.1.0-macOS.pkg      # Developer ID Installer chain
xcrun stapler validate Tonamorph-0.1.0-macOS.pkg          # the ticket is stapled
shasum -a 256 -c SHA256SUMS
```

```powershell
# Windows — "Successfully verified" and the publisher name
signtool verify /pa /v Tonamorph-0.1.0-Windows-Setup.exe
Get-AuthenticodeSignature Tonamorph-0.1.0-Windows-Setup.exe | Format-List Status, SignerCertificate
```

### Known limits

- **SmartScreen reputation takes time.** A freshly signed certificate still triggers "Windows
  protected your PC" until enough downloads accumulate; this is expected and is not fixed by EV.
- **No auto-update.** The plug-in shows an update banner from `GET /v1/version` and links
  the download; installing the new version is still a manual step.
- `auval` passing is necessary for Logic Pro / GarageBand but not sufficient — Logic runs its
  own checks; test there before publishing.
- The Windows build is x64 only (no ARM64 VST3); macOS installs system-wide only
  (`/Library/Audio/Plug-Ins`), not per user.
- `-unsigned` assets and placeholder licence banners are for dry runs; never publish them.
