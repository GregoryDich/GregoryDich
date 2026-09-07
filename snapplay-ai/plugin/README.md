# SnapPlay AI plugin

The JUCE 8 / C++20 VST3 (and, on macOS, AU) instrument. It takes a dropped audio clip,
sends it to the backend for separation, transcription and analysis
([`docs/API_CONTRACT.md`](../docs/API_CONTRACT.md) §2), and turns what comes back into a
playable, scale-snapped sampler you can drag `.mid` or `.fsc` out of.

```
Source/
  Core/        JUCE-free C++20: ScaleLock, Envelope, TransientDetector, ZeroCrossing,
               MidiFileWriter, FscWriter, Types — the code the unit tests exercise
  Cloud/       ApiClient, AuthManager, JobClient (SSE), UploadEncoder, Models, SseParser,
               RetryPolicy — everything that talks HTTP
  Engine/      SamplerEngine, StemSound/StemVoice, PitchShifter, DrumKit,
               ScaleLockProcessor, AutoAdsr — the realtime-safe instrument
  Export/      MidiExporter, FscExporter, DragExport
  UI/          SnapPlayLookAndFeel
  PluginProcessor.{h,cpp}, PluginEditor.{h,cpp}
Tests/         snapplay_core_tests (no JUCE) + roundtrip.py
CMakeLists.txt
```

`Source/Core` is deliberately JUCE-free and the test executable only sees `Source/`, so a
Core header that started `#include <JuceHeader.h>` would fail to compile there. That is
the mechanism keeping the DSP and music-theory layer testable without a plugin host.

## Building

Requirements: **CMake ≥ 3.22**, a C++20 compiler (g++ 13 / clang 15 / MSVC 19.3x) and
**JUCE 8.0.8**. Everything else is optional.

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

Configure prints which one it took (`SnapPlay: using JUCE from …` or
`SnapPlay: fetching JUCE 8.0.8`). Prefer a local checkout offline; a fetch needs network
on the first configure only.

### Linux

```sh
sudo apt-get install -y libasound2-dev libcurl4-openssl-dev libx11-dev libxrandr-dev \
    libxinerama-dev libxcursor-dev libxcomposite-dev libfreetype-dev \
    libfontconfig1-dev libgl1-mesa-dev librubberband-dev

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DJUCE_SOURCE_DIR=/path/to/JUCE
cmake --build build --target SnapPlayAI_VST3 --parallel 4
```

`JUCE_USE_CURL=1` is set, so `juce_core` calls libcurl directly; `CMakeLists.txt` links
`CURL::libcurl` (or the `libcurl` pkg-config target) itself, because the JUCE module
system does not.

### macOS

```sh
brew install cmake pkgconf rubberband
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target SnapPlayAI_VST3 --parallel 4
cmake --build build --target SnapPlayAI_AU   --parallel 4      # AU is macOS-only
```

`AU` is appended to the format list only on Apple platforms, so `SnapPlayAI_AU` does not
exist as a target elsewhere.

### Windows

```powershell
cmake -S . -B build -DJUCE_SOURCE_DIR=C:/dev/JUCE
cmake --build build --config Release --target SnapPlayAI_VST3 --parallel 4
```

Windows and macOS are multi-config generators: pass `--config Release` at build time
rather than `-DCMAKE_BUILD_TYPE` at configure time.

### Build options

| option | default | effect |
|--------|---------|--------|
| `SNAPPLAY_USE_RUBBERBAND` | `ON` | Looks for `rubberband` via pkg-config. Found → `SNAPPLAY_HAS_RUBBERBAND=1` and `PitchShifter` transposes stems with the Rubber Band R3 engine offline, preserving duration. Not found (or `OFF`) → `SNAPPLAY_HAS_RUBBERBAND=0` and it falls back to Lagrange resampling, which changes a stem's duration by `2^(-semitones/12)`. Configure warns when it falls back, and the plugin builds and runs either way. |
| `SNAPPLAY_BUILD_TESTS` | `ON` | Adds `Tests/` (`enable_testing()` + the `snapplay_core_tests` target and its CTest entry). `OFF` drops the test executable entirely — nothing else changes, since no plugin source depends on it. |
| `JUCE_SOURCE_DIR` | *(unset)* | Local JUCE checkout; see above. |

Other targets: `SnapPlayAI_Standalone` (a host-free app, handy for poking at the UI) and
`SnapPlayAI_All`.

## Tests

### `snapplay_core_tests` — 34 JUCE-free unit tests

```sh
cmake --build build --target snapplay_core_tests --parallel 4
ctest --test-dir build --output-on-failure          # add -C Release on Windows/macOS
```

The binary can also be run directly (`build/Tests/snapplay_core_tests`); it prints one
line per case and ends with `34 passed, 0 failed, 34 total`. Coverage: scale snapping and
tie-breaking (`Source/Core/ScaleLock.h`), envelope/ADSR derivation, transient detection,
zero-crossing trimming, the SMF writer, the `.fsc` writer, and one combined export
fixture.

### `Tests/roundtrip.py` — the export format check

`test_export_roundtrip.cpp` writes `sample.mid`, `sample.fsc` and `fixture.json` (the
notes it serialised) into `$SNAPPLAY_TEST_OUT` when that variable names a directory. The
Python script then re-reads them with third-party parsers and compares field by field:

```sh
mkdir -p /tmp/snapplay-export
SNAPPLAY_TEST_OUT=/tmp/snapplay-export ./build/Tests/snapplay_core_tests
python3 Tests/roundtrip.py /tmp/snapplay-export
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

Neither this script nor pluginval runs in CI; the plugin workflow builds the VST3 (and
the AU on macOS) and runs `ctest` only.

### pluginval

```sh
pluginval --strictness-level 5 --validate "build/SnapPlayAI_artefacts/Release/VST3/SnapPlay AI.vst3"
```

Strictness 5 is the minimum pluginval recommends and the level to ship against. On a
headless Linux box the validator still needs an X display: prefix it with `xvfb-run -a`,
or add `--skip-gui-tests` to leave the editor out of the run. Add `--repeat 2
--randomise` before a release, and `--timeout-ms "-1"` when stepping through it in a
debugger. The flags above are those of pluginval 1.0.4.

## Install locations

`COPY_PLUGIN_AFTER_BUILD` is `FALSE`, so a build never touches a system directory. The
artefacts land in the build tree and you copy them yourself:

```
build/SnapPlayAI_artefacts/<Config>/VST3/SnapPlay AI.vst3
build/SnapPlayAI_artefacts/<Config>/AU/SnapPlay AI.component        (macOS only)
build/SnapPlayAI_artefacts/<Config>/Standalone/SnapPlay AI
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
takes the detected key, the BPM label updates — and each stem is decoded and swapped into
the sampler as its download finishes, so the keyboard comes alive stem by stem. Then play
it, and drag `.mid` or `.fsc` straight into the DAW timeline.

Results are cached under `<user application data>/SnapPlay/jobs/<job_id>/`
(`result.json`, the stem WAVs, `score.mid`). The processor stores the last job id in its
state, so reopening a DAW project reloads that job from the cache without spending a
credit.

### The window, top to bottom

| section | what it holds |
|---------|---------------|
| **Header** | Title, the credit balance (`balance.available` from `GET /v1/me`), and a log-out button. |
| **Drop zone** | The dashed drag target for the whole window; highlights during a drag, click to open a file chooser. |
| **Progress** | A progress bar, the stage line (`upload → separate → transcribe → analyze → package`) fed by SSE, and a cancel button that drops the in-flight requests and, when the job is still
`queued`, calls `DELETE /v1/jobs/{id}` so the reservation is released (a running job
would answer `409`). |
| **Category** | Bass / Drums / Synth / Vocals — which stem the keyboard plays. "Synth" is the contract's `other` stem. |
| **Scale-Snap** | Mode (Detected, Major, Minor, PentatonicMajor, PentatonicMinor, Off) and root selectors, with the detected key and BPM shown beside them. Snapping is entirely client-side (contract §8); a note-off always uses the pitch its note-on was snapped to, even if the mode changed while the key was held. |
| **Sound** | Attack / Decay / Sustain / Release (seeded from the stem's `suggested_adsr`), filter cutoff and resonance, gain, the root-target knob (`semitones = target_root_midi − stem.root_midi`) and the drum-mode toggle that maps slices to notes from 36 upward. |
| **Export** | "Drag .mid" and "Drag .fsc" — drag them into the DAW to start an external file drag, or click for a save dialog. Files are written under `<temp>/SnapPlayAI/exports` and cleaned up after 24 h. |
| **Keyboard** | An on-screen `juce::MidiKeyboardComponent` spanning MIDI 24–108, so the instrument is playable without a controller. |
| **Overlays** | `LoginOverlay` (email + password against `POST /v1/auth/token`) while signed out; `PaywallPrompt` when available credits reach 0, built from `GET /v1/plans` and polling `GET /v1/me` every 5 s while open. |

> **Paywall caveat.** `PaywallPrompt` skips any plan whose `checkout_url` is null, and
> `/v1/plans` returns null for every plan until an operator fills in
> `plans.provider_variant_ids` in the database. Against a freshly seeded database the
> prompt therefore appears with **no buttons** and the fallback text "Visit snapplay.ai to
> add more." Nothing errors. See the deployment note in the root [`README.md`](../README.md)
> and in [`db/README.md`](../db/README.md).

## Pointing the plugin at a backend

The base URL defaults to `https://api.snapplay.ai` (`ApiClient::Config::baseUrl`) and is
changed programmatically with `snapplay::cloud::ApiClient::setBaseUrl()`; there is no
user-facing setting or environment variable for it yet. Tokens (never the password) are
persisted by `AuthManager` through a `juce::PropertiesFile` named `SnapPlayAI.settings`
under a `SnapPlay` folder in the OS's application-data location.

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
