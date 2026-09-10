# Third-Party Licences

_Last verified: 2026-09-09 against the manifests in this repository, the JUCE checkout used for builds, and the Python packages installed on the build machine. Re-run the verification (section 6) after any dependency change._

This file lists every third-party component that [[PRODUCT_NAME]] ships, runs or is developed with, the licence each one carries, where it is used, what that licence obliges us to do, and whether anything must happen before launch. It is referenced by `LICENSE`, by the End-User Licence Agreement (`legal/eula.md`) and by the Terms of Service, and it is installed with the plugin and published at `[[WEBSITE_URL]]/legal/third-party`.

**Where a component ships** decides what a licence requires of us:

| Bucket | What it means | Copyleft consequence |
|---|---|---|
| **Plugin binary** | Compiled into, or dynamically linked by, the VST3/AU/standalone builds that end users download | Distribution to the public. Notices must be reproduced; GPL/AGPL code cannot be included in a closed-source binary; LGPL only with relink rights |
| **Backend API server** | The `infra/Dockerfile.api` image (FastAPI control plane on ECS Fargate) | Not distributed. Permissive and copyleft licences alike impose no notice or source obligation on server-side use |
| **Worker image** | The `infra/Dockerfile.worker` GPU image (AWS ECS, Modal, RunPod) | Not distributed to users. Same as above, but model **weights** carry their own terms independent of the code licence |
| **Growth tool** | `growth/` — internal MCP server and Remotion renderer used by the operator | Not distributed. Licence tiers that depend on company size still apply |
| **Tests / dev only** | Test suites, linters, validators | Never shipped; GPL tooling is fine |

**Status legend:** `OK` — nothing to do beyond reproducing the notice where stated · `ACTION REQUIRED` — a concrete step is needed before launch · `BLOCKER` — shipping as-is is not permitted.

---

## 1. Actions before launch

| # | Component | Status | Owner | What to do |
|---|---|---|---|---|
| 1 | **Demucs v4 pretrained weights** (`htdemucs`, `htdemucs_ft`, `htdemucs_6s`) | **BLOCKER** | Founder + counsel | The **code** is MIT; the **weights** are not. They are downloaded at run time from Meta's file server, are not in the repository, and the maintainer stated in facebookresearch/demucs issue #327 (2022-05-23) that "the model weights are not covered by the MIT license, and are provided only for scientific purposes". They were trained on MUSDB18-HQ ("educational purposes only … not … for any commercial purpose") plus an internal Meta set. Converting to ONNX/TensorRT does not change this. Third parties re-labelling the weights "MIT" on model hubs are not authoritative. The repository is archived and the author has left Meta, so a grant would have to come from Meta legal. **Either (a) obtain a written commercial licence from Meta for the exact checkpoints, or (b) replace the separation model before launch.** Read the issue thread yourself and archive a screenshot before deciding. Candidates are in section 2. |
| 2 | **Rubber Band Library** (pitch shifting in the plugin) | **BLOCKER** as currently configured | Founder | `plugin/CMakeLists.txt` enables Rubber Band by default (`*_USE_RUBBERBAND` option, `ON`) and links it whenever `pkg-config` finds it. Rubber Band is **GPL-2.0-or-later** unless a commercial licence is bought; a closed-source plugin containing it may not be distributed, and Breakfast Quay states explicitly that App Store distribution requires the commercial licence. **Either buy a commercial licence (perpetual, one-time fee, "with attribution" or "non-attribution" variants; price on request — breakfastquay.com was unreachable from the research environment) before the first public build, or build releases with the option set to `OFF`** (the code falls back to resampling pitch shift). Record which one in this file. |
| 3 | **VST3 SDK** as vendored in JUCE 8.0.8 (`VST 3.7.12`) | **ACTION REQUIRED** | Founder + counsel | Steinberg relicensed the VST3 SDK to **MIT** in late October 2025; the current upstream `LICENSE.txt` is the MIT text (© 2026, reproduced in Appendix A.1) and no Steinberg agreement or developer registration is needed. **But the copy actually compiled into the plugin is the one inside the pinned JUCE 8.0.8 checkout, and that copy's `LICENSE.txt` is still the pre-October-2025 dual licence ("Proprietary Steinberg VST3 License, or GPL v3"), which for a proprietary build requires a signed Steinberg agreement.** Resolve by moving to a JUCE release whose vendored `modules/juce_audio_processors/format_types/VST3_SDK/LICENSE.txt` is the MIT text, or by obtaining Steinberg's written confirmation that the MIT relicensing covers SDK 3.7.12. Using the "VST" word mark or logo additionally binds you to Steinberg's VST usage guidelines. |
| 4 | **JUCE 8.0.8** | **ACTION REQUIRED** | Founder | JUCE is dual-licensed AGPLv3 / commercial JUCE 8 EULA. AGPL is unusable for a closed-source plugin, so the commercial tier applies. Tiers are by **trailing-12-month gross revenue from all sources**: Starter (free) under about US$ 20k/year, Indie under US$ 500k/year, Pro unlimited. JUCE 8 dropped the splash-screen requirement on Starter (the build sets `JUCE_DISPLAY_SPLASH_SCREEN=0`, which is only correct if that is confirmed). JUCE 9 (July 2026) kept the same pricing and EULA. Sources on Indie pricing conflict (US$ 40/month or US$ 800 perpetual vs US$ 50/month or US$ 1,000) and juce.com was unreachable from the research environment. **Confirm the tier terms on juce.com, record the tier in this file, and buy Indie the month revenue crosses the Starter limit** — the EULA requires you to upgrade or stop distributing. |
| 5 | **aubio** (`backend/requirements-gpu.txt`) | **ACTION REQUIRED** | Backend | GPL-3.0. It runs only in the worker image and is never in the plugin, so no copyleft obligation is triggered today, but it is the one GPL component in the pipeline and a single mistaken packaging decision would contaminate a distributed artefact. `backend/app/pipeline/analysis.py` already falls back to librosa (ISC) and then to pure numpy for tempo. **Remove `aubio>=0.4.9` from `requirements-gpu.txt` and `backend/pyproject.toml [gpu]`**, re-run the pipeline tests, and delete this row. |
| 6 | **pyflp** | OK (verified) | Plugin | GPL-3.0. Verified with `grep -rn pyflp` across the repository on 2026-09-09: it is imported **only** in `plugin/Tests/roundtrip.py` (an optional, developer-run cross-check of the `.fsc` exporter, wrapped in a `try/except ImportError`) and mentioned in `plugin/README.md`. It is **not** in any `requirements*.txt` or `pyproject.toml`, not imported by `backend/`, `backend/tests/`, `growth/` or `infra/`, and not part of any image or binary. Nothing to do except keep it out of the manifests. |
| 7 | **Remotion 4.0.521** (`growth/remotion/package.json`) | **ACTION REQUIRED** | Founder | The Remotion Licence grants free use (including commercial) to individuals and to for-profit organisations with **up to 3 employees**; larger for-profit companies need a paid Company Licence. A sole proprietor qualifies for the free tier today. **Re-check the moment the business incorporates or takes on a fourth person**, and note that Remotion 5 changes the licence text. |
| 8 | **Plugin notice file / About box** | **ACTION REQUIRED** | Plugin | The BSD, Apache-2.0, MIT-style and IJG licences of components compiled into the plugin (section 3.1) require their copyright notices and disclaimers to be reproduced "in the documentation and/or other materials provided with the distribution". **Bundle this file with every installer and expose it from the plugin's About screen.** The texts are in the JUCE tree at the paths given in section 3.1; the ones with the strictest wording (FLAC, Ogg Vorbis) are reproduced in Appendix B. |
| 9 | **Worker-image transitive dependencies** | **ACTION REQUIRED** | Backend | `torch`, `demucs`, `basic-pitch` and `onnxruntime-gpu` are not installed on the build machine (no GPU wheels), so their transitive dependencies could not be enumerated here. Demucs pulls in at least `openunmix` (MIT), `julius` (MIT), `einops` (MIT), `torchaudio` (BSD-2) and `lameenc` (reported LGPL — confirm); Basic Pitch's own NOTICE (Appendix A.5) lists librosa (ISC), mir_eval (MIT), pretty_midi (MIT), resampy (ISC), scipy (BSD-3) and tensorflow (Apache-2.0). **Run `pip-licenses --format=markdown` inside the built worker image and paste the result into section 3.3.** Also confirm the NVIDIA CUDA 12.4.1 / cuDNN base image terms (NVIDIA Deep Learning Container Licence) permit our hosted use — they do for running containers, but record it. |
| 10 | **Website (`web/`)** | OK (verified) | Web | Enumerated with `npx license-checker --production` on 2026-09-10 (140 packages): MIT 124, Apache-2.0 5, ISC 3, BSD-3-Clause 1, 0BSD 1, MPL-2.0 1 (`@vercel/analytics`, unmodified, file-level copyleft only), CC-BY-4.0 1 (`caniuse-lite`, browser-support data), LGPL-3.0-or-later 2 (`@img/sharp-libvips-*`, Next.js image optimisation, runs only on the Vercel server and is never distributed). Nothing in the site bundle is copyleft. Re-run the command after any dependency change; details in section 3.6. |
| 11 | **Services used by the growth tool** (not software licences) | **ACTION REQUIRED** | Growth | ElevenLabs text-to-speech: commercial use of generated voice in advertising requires a paid plan under ElevenLabs' terms — confirm the plan. Free Music Archive tracks: per-track Creative Commons terms, enforced in code (`growth/mcp_server/licensing.py` drops NC/ND). TikTok, Meta and YouTube developer terms apply to the publishers. None of these are redistributed software; they are listed for completeness. |

### 2. Separation-model replacement candidates (for action 1)

From the launch research brief, in order of preference:

| Candidate | Licence status | Notes |
|---|---|---|
| **Mel-Band RoFormer (Kim vocal models)** | Reported relicensed from GPL-3.0 to **MIT** by the original author on 2026-04-22, weights included (per the mlx-community model card; corroborated by an independent licence-research document) | Strongest candidate; reported to outperform htdemucs on vocals. The reports come from model-hub cards, not the author's own repository. **Verify the licence on the exact checkpoint you ship, confirm a 4-stem (bass/drums/other/vocals) variant exists under the same terms, and archive a copy of the model card and licence on the day you ship.** |
| **Licensed commercial stem-separation API** (AudioShake, Music.ai/Moises, LALAL.AI) | Commercial B2B/API contract | Removes the weights question and the GPU-hosting line entirely; adds per-call cost and a vendor dependency. Re-run `docs/ECONOMICS.md` if chosen. |
| **Spleeter (Deezer)** | Code MIT; README silent on weights; Deezer sells "Spleeter Pro" commercially | Same ambiguity as Demucs, lower quality. **Not recommended.** |
| **Open-Unmix** | Code MIT; default `umxl` weights **CC BY-NC-SA 4.0**; `umxhq`/`umx` trained on MUSDB18 (non-commercial) | **Not recommended.** |

The research brief also flags two questions that need a lawyer, not an engineer: whether model weights are a derivative of MIT-licensed code and/or of non-commercially-licensed training data, and whether a maintainer's forum comment is a binding licence term (or evidence of the absence of one).

---

## 3. Component matrix

Columns: **Version pinned in repo** is what the manifests fix; "unpinned" means the manifest gives only a lower bound or nothing, and the version in brackets is what was installed on the build machine on the verification date. **Obligation** is what the licence requires of us in the bucket where the component is used.

### 3.1 Plugin binary (distributed to end users)

Built by `plugin/CMakeLists.txt`: formats VST3 and Standalone on every platform, plus AU on macOS. Linked JUCE modules: `juce_audio_utils`, `juce_audio_processors`, `juce_audio_formats`, `juce_dsp`, `juce_gui_extra`, and transitively `juce_audio_devices`, `juce_audio_basics`, `juce_gui_basics`, `juce_graphics`, `juce_events`, `juce_data_structures`, `juce_core`, `juce_audio_plugin_client`.

| Component | Version pinned in repo | Licence | Where used | Obligation | Status |
|---|---|---|---|---|---|
| **JUCE framework** (modules above) | **8.0.8** (`FetchContent GIT_TAG 8.0.8`, or the local checkout at the same version) | Dual: AGPLv3 **or** commercial JUCE 8 EULA (Starter / Indie / Pro by revenue) | Plugin binary | Hold the correct commercial tier for trailing-12-month revenue; comply with JUCE EULA (no splash needed on JUCE 8 Starter — confirm); do not claim JUCE endorsement | **ACTION REQUIRED** (action 4) |
| **VST3 SDK** (`juce_audio_processors/format_types/VST3_SDK`) | **3.7.12**, as vendored in JUCE 8.0.8 | Vendored copy: Steinberg VST3 Licence / GPLv3 dual (2024 text). Upstream since Oct 2025: **MIT** (© 2026 Steinberg) | Plugin binary (VST3 format) | Under MIT: reproduce the copyright and permission notice (Appendix A.1). Under the vendored dual licence: signed Steinberg agreement for proprietary use. VST word mark/logo use is optional and subject to Steinberg's usage guidelines | **ACTION REQUIRED** (action 3) |
| **Rubber Band Library** | **unpinned** — whatever `pkg-config rubberband` finds (3.3.0 on the build machine); linked when `*_USE_RUBBERBAND=ON` (default) | **GPL-2.0-or-later**, or commercial (perpetual, with-attribution or non-attribution variants) | Plugin binary (`plugin/Source/Engine/PitchShifter.cpp`) | GPL: not permitted in a closed-source binary. Commercial "with attribution" variant: credit line in documentation/About box. Commercial "non-attribution": none | **BLOCKER** as configured (action 2) |
| **libFLAC** (embedded in `juce_audio_formats`) | as in JUCE 8.0.8 (libFLAC © 2000-2009 Josh Coalson, 2011-2023 Xiph.Org Foundation) | BSD-3-Clause | Plugin binary (decoding uploads/results; FLAC encoding for upload) | Reproduce copyright notice, conditions and disclaimer with the distribution; no endorsement using Xiph's name (Appendix B.1) | OK — notice required (action 8) |
| **Ogg Vorbis** (embedded in `juce_audio_formats`) | as in JUCE 8.0.8 (© 2002-2020 Xiph.org Foundation) | BSD-3-Clause | Plugin binary (audio format support) | Reproduce notice and disclaimer (Appendix B.2) | OK — notice required (action 8) |
| **zlib** (embedded in `juce_core`) | as in JUCE 8.0.8 | zlib licence | Plugin binary (compression of state/network) | No notice strictly required for binaries; do not misrepresent origin. Text at `modules/juce_core/zip/zlib/README` | OK |
| **libpng** (embedded in `juce_graphics`) | as in JUCE 8.0.8 | PNG Reference Library Licence v2 | Plugin binary (UI images) | Reproduce the licence text if the software is redistributed with modifications; recommended in any case. Text at `modules/juce_graphics/image_formats/pnglib/LICENSE` | OK — include notice (action 8) |
| **jpeglib** (embedded in `juce_graphics`) | as in JUCE 8.0.8 | Independent JPEG Group licence | Plugin binary (UI images) | Documentation must state: "this software is based in part on the work of the Independent JPEG Group". Text at `modules/juce_graphics/image_formats/jpglib/README` | OK — notice required (action 8) |
| **HarfBuzz** (embedded in `juce_graphics`) | as in JUCE 8.0.8 (© Google, Ebrahim Byagowi, Facebook, Mozilla, Codethink, Nokia, Keith Stribley, Martin Hosken/SIL, and others) | "Old MIT" (MIT-style) | Plugin binary (text shaping) | Reproduce copyright notices and permission notice. Text at `modules/juce_graphics/fonts/harfbuzz/COPYING` | OK — notice required (action 8) |
| **SheenBidi** (embedded in `juce_graphics`) | as in JUCE 8.0.8 | Apache-2.0 | Plugin binary (bidirectional text) | Reproduce the licence and any NOTICE; state modifications if any. Text at `modules/juce_graphics/unicode/sheenbidi/LICENSE` | OK — notice required (action 8) |
| **AudioUnitSDK** (embedded in `juce_audio_plugin_client`) | as in JUCE 8.0.8 (Apple) | Apache-2.0 | Plugin binary — **macOS AU format only** | Reproduce the licence. Text at `modules/juce_audio_plugin_client/AU/AudioUnitSDK/LICENSE.txt` | OK — notice required (action 8) |
| **libcurl** | unpinned system library (Linux builds only; `JUCE_USE_CURL=1`, `find_package(CURL)`) | curl licence (MIT-style) | Plugin binary on Linux (dynamic link) | Reproduce the copyright notice in documentation | OK — notice required on Linux builds |
| **ALSA (libasound)** | unpinned system library (Linux only, via `juce_audio_devices`) | LGPL-2.1-or-later | Standalone/plugin audio I/O on Linux (dynamic link) | Dynamic linking satisfies the LGPL; no source obligation for our code | OK |
| **macOS / Windows system frameworks** (CoreAudio, AudioToolbox, WASAPI, DirectSound, etc.) | OS-provided | OS licences | Plugin binary | None | OK |

Not present in the plugin, by verification: `aubio`, `libsndfile`/`soundfile`, `librosa`, `torch`, `onnxruntime`, any Python. Audio decoding in the plugin uses JUCE's own readers. JUCE modules that carry other third-party code (`juce_opengl` GLEW/Mesa, `juce_javascript` CHOC/QuickJS, `juce_box2d`, LV2 SDK, AAX SDK) are **not linked** and are not built.

### 3.2 Backend API server (`infra/Dockerfile.api`; not distributed)

Manifest: `backend/requirements.txt` / `backend/pyproject.toml`. All constraints are lower bounds (`>=`), so every row is **unpinned**; bracketed versions are those installed on the build machine on 2026-09-09. Server-side use imposes no notice obligation; the "Obligation" column therefore states what would apply if the component were ever redistributed.

| Component | Version pinned in repo | Licence | Where used | Obligation | Status |
|---|---|---|---|---|---|
| FastAPI | unpinned, `>=0.115,<1` [0.115.6] | MIT | Backend server | Notice on redistribution only | OK |
| Starlette | unpinned (FastAPI dependency; must stay `<0.42` for FastAPI 0.115) [0.41.3] | BSD-3-Clause | Backend server | Notice on redistribution only | OK |
| uvicorn (+ `standard` extras: uvloop, httptools, watchfiles, websockets, python-dotenv, PyYAML) | unpinned, `>=0.30` [0.52.4] | BSD-3-Clause (uvloop MIT/Apache-2.0; httptools MIT; watchfiles MIT; python-dotenv BSD-3; PyYAML MIT) | Backend server | Notice on redistribution only | OK |
| pydantic / pydantic-core | unpinned, `>=2.12,<3` [2.13.5 / 2.46.5] | MIT | Backend server, worker, growth | Notice on redistribution only | OK |
| pydantic-settings | unpinned, `>=2.4,<3` [2.15.0] | MIT | Backend server, growth | Notice on redistribution only | OK |
| httpx (+ httpcore, anyio, h11, idna, certifi) | unpinned, `>=0.27` [0.28.1] | BSD-3-Clause (httpcore BSD-3; anyio MIT; h11 MIT; idna BSD-3; certifi MPL-2.0) | Backend server, growth | Notice on redistribution only; MPL-2.0 (certifi) requires source of that file only if modified | OK |
| PyJWT (+ `crypto` extra: cryptography) | unpinned, `>=2.7,<3` [2.13.0] | MIT (cryptography: Apache-2.0 OR BSD-3) | Backend server (JWT verification) | Notice on redistribution only | OK |
| python-multipart | unpinned, `>=0.0.9` [0.0.32] | Apache-2.0 | Backend server (upload parsing) | Licence + NOTICE on redistribution only | OK |
| sse-starlette | unpinned, `>=2.1` [3.4.11] | BSD-3-Clause | Backend server (job progress streams) | Notice on redistribution only | OK |
| websockets | unpinned, `>=12` [17.1] | BSD-3-Clause | Backend server | Notice on redistribution only | OK |
| boto3 (+ botocore, s3transfer, jmespath, python-dateutil, urllib3, six) | unpinned, `>=1.34` [1.43.89] | Apache-2.0 (jmespath MIT; python-dateutil Apache-2.0/BSD-3; urllib3 MIT; six MIT) | Backend server (S3, SQS), worker | Licence + NOTICE on redistribution only | OK |
| NumPy | unpinned, `>=1.26` [2.4.6] | BSD-3-Clause (binary wheels bundle OpenBLAS and others under BSD/MIT/zlib/CC0 — see the wheel's `LICENSE.txt`) | Backend server (analysis), worker, growth | Notice on redistribution only (Appendix A.7) | OK |
| python-soundfile | unpinned, `>=0.12` [0.14.0] | BSD-3-Clause | Backend server (decoding uploads), worker, growth | Notice on redistribution only | OK |
| **libsndfile** (bundled in the soundfile wheel; also `apt libsndfile1` in the worker image) | unpinned | **LGPL-2.1-or-later** | Backend server and worker only — **never in the plugin** | None server-side. Would require dynamic linking + relink rights if ever shipped in a binary; the plugin uses JUCE readers instead | OK (keep out of the plugin) |
| mido | unpinned, `>=1.3` [1.3.3] | MIT | Backend server (MIDI export), growth | Notice on redistribution only (Appendix A.4) | OK |
| **ffmpeg / ffprobe** (`apt-get install ffmpeg` in both images) | unpinned (Debian/Ubuntu build) | LGPL-2.1+/GPL-2+ depending on the distro build (Debian's is GPL-enabled) | Backend server and worker, invoked as a **subprocess** for decode/truncate fallback | None: not linked, not distributed | OK |
| Python 3.11 (`python:3.11-slim`; deadsnakes on the worker) | 3.11 | PSF-2.0 | Both images | None | OK |
| typing_extensions, annotated-types, click, and other small transitive packages | unpinned | PSF-2.0 / MIT / BSD-3 | Both images | None server-side | OK |

### 3.3 GPU worker image (`infra/Dockerfile.worker`; runs on AWS ECS, Modal Labs and RunPod; not distributed)

Everything in 3.2 plus `backend/requirements-gpu.txt`. None of these packages could be installed on the build machine (no GPU wheels); versions are the manifest floors only.

| Component | Version pinned in repo | Licence | Where used | Obligation | Status |
|---|---|---|---|---|---|
| **Demucs — code** | unpinned, `>=4.0.1` | MIT (Meta Platforms) | Worker image (`backend/app/pipeline/separation.py`) | Notice on redistribution only (Appendix A.2) | OK |
| **Demucs — pretrained weights** `htdemucs` (and `_ft`, `_6s`) | not in repo; downloaded at run time from `dl.fbaipublicfiles.com` into `TORCH_HOME` | **No commercial licence** — "provided only for scientific purposes" per the maintainer; trained on MUSDB18-HQ (non-commercial) plus a Meta-internal set | Worker image at run time | Cannot be used commercially without a grant from Meta | **BLOCKER** (action 1) |
| **Basic Pitch** (Spotify) — code and ICASSP 2022 model (TF, CoreML, TFLite and ONNX formats shipped inside the package) | unpinned, `>=0.4` | Apache-2.0 (© 2022 Spotify AB), with NOTICE | Worker image (`backend/app/pipeline/transcription.py`, via onnxruntime) | Reproduce LICENSE and NOTICE if redistributed (Appendix A.5, A.6); we do not modify the package, so no modification marking is needed | OK |
| onnxruntime-gpu | unpinned, `>=1.17` | MIT (Microsoft) | Worker image | Notice on redistribution only (Appendix A.3) | OK |
| PyTorch (+ torchaudio) | unpinned, `>=2.2` | BSD-3-Clause (torchaudio BSD-2-Clause) | Worker image (separation, resampling) | Notice on redistribution only (Appendix A.8) | OK |
| **aubio** | unpinned, `>=0.4.9` | **GPL-3.0** | Worker image only (`backend/app/pipeline/analysis.py`, optional tempo tracker) | None while server-side; would contaminate any distributed artefact | **ACTION REQUIRED** — remove (action 5) |
| librosa | not declared — arrives transitively via Basic Pitch; used opportunistically by `analysis.py` | ISC | Worker image (tempo fallback) | Notice on redistribution only (Appendix A.9) | OK |
| SciPy | not declared — transitive via Basic Pitch/librosa; optional resampling fallback in `audio_io.py` | BSD-3-Clause | Worker image | Notice on redistribution only | OK |
| Open-Unmix (`openunmix`), `julius`, `einops`, `lameenc`, `dora-search`, `tqdm`, `PyYAML` | transitive via Demucs (not verified here) | MIT / MIT / MIT / LGPL / MIT / MPL-2.0+MIT / MIT | Worker image | None server-side | ACTION REQUIRED — enumerate in the built image (action 9) |
| `resampy`, `pretty_midi`, `mir_eval`, `tensorflow`/`tflite-runtime` (if pulled by the Basic Pitch extras) | transitive via Basic Pitch (not verified here) | ISC / MIT / MIT / Apache-2.0 | Worker image | None server-side | ACTION REQUIRED — enumerate in the built image (action 9) |
| **NVIDIA CUDA 12.4.1 + cuDNN runtime** (`nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`) | 12.4.1 | NVIDIA CUDA EULA, cuDNN SLA, NVIDIA Deep Learning Container Licence | Worker image base | Run-time use in our own hosted containers is permitted; no redistribution to users | OK — record confirmation (action 9) |
| Ubuntu 22.04 packages (`python3.11` from the deadsnakes PPA, `ffmpeg`, `libsndfile1`) | unpinned | Various (PSF-2.0, GPL/LGPL, LGPL-2.1+) | Worker image | None server-side | OK |

### 3.4 Growth tool (`growth/`; operator-run, not distributed)

| Component | Version pinned in repo | Licence | Where used | Obligation | Status |
|---|---|---|---|---|---|
| FastMCP (+ `mcp`, `mcp-types`) | unpinned, `>=4,<5` [4.0.3] | Apache-2.0 (mcp: MIT) | Growth tool (MCP server) | Licence + NOTICE on redistribution only | OK |
| httpx, pydantic, pydantic-settings, numpy, soundfile, mido | unpinned (see 3.2) | see 3.2 | Growth tool | see 3.2 | OK |
| **Remotion** (`remotion`, `@remotion/cli`, `@remotion/media-utils`) | **4.0.521** (exact) | Remotion Licence: free for individuals, non-profits and for-profit organisations with up to 3 employees; Company Licence otherwise | Growth tool (video rendering) | Stay within the free-tier eligibility or buy a Company Licence; do not resell Remotion itself | **ACTION REQUIRED** — confirm tier (action 7) |
| React, react-dom | **19.2.8** (exact) | MIT | Growth tool (Remotion compositions) | Notice on redistribution only | OK |
| TypeScript | **5.9.3** (exact, devDependency) | Apache-2.0 | Dev only | None | OK |
| `@types/react`, `@types/react-dom` | 19.2.18 / 19.2.7 (exact, devDependencies) | MIT | Dev only | None | OK |
| Node.js 22 | unpinned (build machine) | MIT (with bundled components under their own licences) | Growth tool runtime | None | OK |
| ffmpeg (fallback renderer, subprocess) | unpinned system package | LGPL/GPL (distro build) | Growth tool | None (subprocess, not distributed) | OK |

### 3.5 Tests and developer tooling (never shipped)

| Component | Version pinned in repo | Licence | Where used | Obligation | Status |
|---|---|---|---|---|---|
| pytest, pytest-asyncio | unpinned, `>=8` / `>=0.23` [9.1.1 / 1.4.0] | MIT / Apache-2.0 | Tests only | None | OK |
| respx | unpinned, `>=0.21` [0.23.1] | BSD-3-Clause | Tests only (HTTP mocking) | None | OK |
| moto (`[s3,sqs]`) | unpinned, `>=5` [5.2.3] | Apache-2.0 | Tests only (AWS mocking) | None | OK |
| ruff | unpinned, `>=0.5` [0.16.6] | MIT | Lint only | None | OK |
| **pyflp** (+ `construct`, `construct-typing`) | **not in any manifest**; [2.2.1] installed on the dev machine | **GPL-3.0** (construct: MIT) | **Tests only**: `plugin/Tests/roundtrip.py`, optional import; see action 6 | None — a GPL tool run by a developer is not distributed | OK (verified) |
| pluginval 1.0.4 | external tool at `/home/user/deps/pluginval` | GPL-3.0 | Plugin validation only | None | OK |
| CMake, g++/clang, pkg-config, pip-licenses | build machine | Various OSS | Build/dev only | None | OK |

### 3.6 Website (`web/`)

Hosted on Vercel; the browser receives compiled JavaScript, not the packages themselves.
Direct dependencies (`web/package.json`) and the licence of the whole production tree as
reported by `npx license-checker --production --csv` on 2026-09-10:

| Component | Version | Licence | Where | Obligation |
|---|---|---|---|---|
| Next.js (`next`) | 15.5.x | MIT | server + browser bundle | Notice in this file. |
| React / React DOM | 19.x | MIT | server + browser bundle | Notice in this file. |
| `@supabase/supabase-js`, `@supabase/ssr` | 2.x / 0.12.x | MIT | server + browser bundle | Notice in this file. |
| `react-markdown`, `remark-gfm` | 10.x / 4.x | MIT | build time (legal pages are pre-rendered) | Notice in this file. |
| `@vercel/analytics` | 1.6.x | MPL-2.0 | browser bundle | File-level copyleft on the MPL files only; we ship them unmodified, so no source obligation beyond keeping the notice. |
| `@img/sharp-libvips-linux-x64`, `-linuxmusl-x64` (via `sharp`, pulled in by Next.js image optimisation) | 1.3.x | LGPL-3.0-or-later | Vercel server only, never distributed | None while it stays server-side; do not bundle it into any downloadable artefact. |
| `caniuse-lite` (via browserslist) | data package | CC-BY-4.0 | build time | Attribution: "Data from caniuse.com" is carried by the package itself. |
| Everything else (transitive) | — | MIT / Apache-2.0 / ISC / BSD / 0BSD | build or server | Notices aggregated by the command above. |

Paddle.js (`cdn.paddle.com`) and the optional Klaviyo snippet are loaded from their vendors
at run time under those vendors' service terms; they are not part of the repository.

---

## 4. Trademarks

"VST" is a trademark of Steinberg Media Technologies GmbH; using the VST word mark or logo is optional and, if done, follows Steinberg's VST usage guidelines. "Audio Units" is a trademark of Apple Inc. "FL Studio" is a trademark of Image-Line Software; "Ableton Live" of Ableton AG; other DAW names belong to their owners. They are used only to state compatibility, never to imply endorsement, and their logos are not used as design elements. "JUCE" is a trademark of Raw Material Software Limited.

## 5. How the plugin's notice bundle is produced

Until a generator exists, the release checklist is manual: copy this file next to the installer, and populate the About screen from Appendix A and B plus the JUCE-tree texts listed in 3.1 (`Flac Licence.txt`, `Ogg Vorbis Licence.txt`, `pnglib/LICENSE`, `jpglib/README`, `harfbuzz/COPYING`, `sheenbidi/LICENSE`, `AudioUnitSDK/LICENSE.txt` on macOS, and the libcurl notice on Linux). If Rubber Band ships under a with-attribution commercial licence, add the credit line Breakfast Quay specifies.

## 6. Verification commands

```
# Python side (run in each image / environment):
pip install pip-licenses && pip-licenses --format=markdown --with-urls

# What is linked into the plugin:
sed -n '/target_link_libraries/,/)/p' plugin/CMakeLists.txt
pkg-config --modversion rubberband

# GPL/AGPL/LGPL sweep over declared manifests:
grep -rn -i -E "aubio|pyflp|rubberband|gpl" backend/requirements*.txt backend/pyproject.toml growth/requirements.txt growth/pyproject.toml plugin/CMakeLists.txt

# Where pyflp is imported:
grep -rn pyflp --include='*.py' .
```

---

## Appendix A — Licence texts reproduced verbatim
Each text below is reproduced exactly as published by the licensor, inside a code block so that Markdown rendering cannot alter it. The heading gives the component, the licence, the copyright holder and where the text was obtained.

### A.1 VST3 SDK — MIT

**Copyright holder:** Steinberg Media Technologies GmbH. Applies to the VST3 SDK as published by Steinberg since October 2025. Source: `https://raw.githubusercontent.com/steinbergmedia/vst3sdk/master/LICENSE.txt` (identical to `vst3_pluginterfaces/master/LICENSE.txt`), fetched 2026-09-09. **Note:** the copy vendored in JUCE 8.0.8 carries a different, older licence text (see action 3).

```text
MIT License

Copyright (c) 2026, Steinberg Media Technologies GmbH

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### A.2 Demucs (code) — MIT

**Copyright holder:** Meta Platforms, Inc. and affiliates. Covers the Demucs source code only; **not** the pretrained weights (see action 1). Source: `https://raw.githubusercontent.com/facebookresearch/demucs/main/LICENSE`, fetched 2026-09-09.

```text
MIT License

Copyright (c) Meta Platforms, Inc. and affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### A.3 ONNX Runtime — MIT

**Copyright holder:** Microsoft Corporation. Source: `https://raw.githubusercontent.com/microsoft/onnxruntime/main/LICENSE`, fetched 2026-09-09.

```text
MIT License

Copyright (c) Microsoft Corporation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### A.4 mido — MIT

**Copyright holder:** Ole Martin Bjørndalen. Source: `https://raw.githubusercontent.com/mido/mido/main/LICENSE`, fetched 2026-09-09; byte-identical to the `LICENSE` in the installed `mido-1.3.3.dist-info`.

```text
The MIT License

Copyright (c) Ole Martin Bjørndalen

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

### A.5 Basic Pitch — Apache License 2.0

**Copyright holder:** Spotify AB (2022). Source: `https://raw.githubusercontent.com/spotify/basic-pitch/main/LICENSE`, fetched 2026-09-09. The same Apache-2.0 text governs boto3/botocore/s3transfer, python-multipart, FastMCP, pytest-asyncio, moto, SheenBidi and Apple's AudioUnitSDK; each carries its own copyright line and, where present, NOTICE file.

```text
Copyright 2022 Spotify AB

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

### A.6 Basic Pitch — NOTICE

**Copyright holder:** Spotify AB. Must accompany any redistribution of Basic Pitch under Apache-2.0 §4(d). Source: `https://raw.githubusercontent.com/spotify/basic-pitch/main/NOTICE`, fetched 2026-09-09.

```text
Basic Pitch
Copyright 2022 Spotify AB

This product includes software developed at
Spotify AB (http://www.spotify.com/).

This product includes software from Librosa (ISC).
* Copyright (C) 2013--2017, librosa development team.

This product includes software from mir_eval (MIT)
* Copyright (C) 2014 Colin Raffel

This product includes software from numpy (BSD)
* Copyright (C) 2005-2022, NumPy Developers.

This product includes software from pretty-midi (MIT)
* Copyright (C) 2014 Colin Raffel

This product includes software from resampy (ISC)
* Copyright (C) 2016, Brian McFee

This product includes software from scipy (BSD)
* Copyright (C) 2001-2002 Enthought, Inc. 2003-2022, SciPy Developers

This product includes software from tensorflow (Apache 2.0)
* Copyright (C) 2019 Google, LLC <packages@tensorflow.org>

The tests for `basic-pitch` include audio files from the
Vocadito dataset liscened under Creative Commons
Attribution 4.0 International. The dataset can be found at:
https://zenodo.org/record/5578807#.YnRm5vPMKDU
```

### A.7 NumPy — BSD-3-Clause

**Copyright holder:** NumPy Developers (2005-2025). Source: `https://raw.githubusercontent.com/numpy/numpy/main/LICENSE.txt`, fetched 2026-09-09; the first 30 lines of the installed `numpy-2.4.6.dist-info/licenses/LICENSE.txt` are identical, and that file continues with the notices of libraries bundled in the binary wheel (OpenBLAS, LAPACK, pocketfft, highway, and others) which must travel with any redistribution of the wheel.

```text
Copyright (c) 2005-2025, NumPy Developers.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

    * Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.

    * Redistributions in binary form must reproduce the above
       copyright notice, this list of conditions and the following
       disclaimer in the documentation and/or other materials provided
       with the distribution.

    * Neither the name of the NumPy Developers nor the names of any
       contributors may be used to endorse or promote products derived
       from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### A.8 PyTorch — BSD-3-Clause

**Copyright holder:** Facebook, Inc. and the contributors listed in the text. Source: `https://raw.githubusercontent.com/pytorch/pytorch/main/LICENSE`, fetched 2026-09-09.

```text
From PyTorch:

Copyright (c) 2016-     Facebook, Inc            (Adam Paszke)
Copyright (c) 2014-     Facebook, Inc            (Soumith Chintala)
Copyright (c) 2011-2014 Idiap Research Institute (Ronan Collobert)
Copyright (c) 2012-2014 Deepmind Technologies    (Koray Kavukcuoglu)
Copyright (c) 2011-2012 NEC Laboratories America (Koray Kavukcuoglu)
Copyright (c) 2011-2013 NYU                      (Clement Farabet)
Copyright (c) 2006-2010 NEC Laboratories America (Ronan Collobert, Leon Bottou, Iain Melvin, Jason Weston)
Copyright (c) 2006      Idiap Research Institute (Samy Bengio)
Copyright (c) 2001-2004 Idiap Research Institute (Ronan Collobert, Samy Bengio, Johnny Mariethoz)

From Caffe2:

Copyright (c) 2016-present, Facebook Inc. All rights reserved.

All contributions by Facebook:
Copyright (c) 2016 Facebook Inc.

All contributions by Google:
Copyright (c) 2015 Google Inc.
All rights reserved.

All contributions by Yangqing Jia:
Copyright (c) 2015 Yangqing Jia
All rights reserved.

All contributions by Kakao Brain:
Copyright 2019-2020 Kakao Brain

All contributions by Cruise LLC:
Copyright (c) 2022 Cruise LLC.
All rights reserved.

All contributions by Tri Dao:
Copyright (c) 2024 Tri Dao.
All rights reserved.

All contributions by Arm:
Copyright (c) 2021, 2023-2025 Arm Limited and/or its affiliates

All contributions from Caffe:
Copyright(c) 2013, 2014, 2015, the respective contributors
All rights reserved.

All other contributions:
Copyright(c) 2015, 2016 the respective contributors
All rights reserved.

Caffe2 uses a copyright model similar to Caffe: each contributor holds
copyright over their contributions to Caffe2. The project versioning records
all such contribution and copyright details. If a contributor wants to further
mark their specific copyright on a particular contribution, they should
indicate their copyright solely in the commit message of the change when it is
committed.

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. Neither the names of Facebook, Deepmind Technologies, NYU, NEC Laboratories America
   and IDIAP Research Institute nor the names of its contributors may be
   used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```

### A.9 httpx — BSD-3-Clause

**Copyright holder:** Encode OSS Ltd (2019). Source: `https://raw.githubusercontent.com/encode/httpx/master/LICENSE.md`, fetched 2026-09-09; byte-identical to the installed `httpx-0.28.1.dist-info/licenses/LICENSE.md`. Starlette, httpcore, uvicorn, sse-starlette, websockets and python-soundfile are BSD-3-Clause under the same conditions with their own copyright lines.

```text
Copyright © 2019, [Encode OSS Ltd](https://www.encode.io/).
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### A.10 librosa — ISC

**Copyright holder:** librosa development team (2013-2026). Source: `https://raw.githubusercontent.com/librosa/librosa/main/LICENSE.md`, fetched 2026-09-09.

```text
## ISC License

Copyright (c) 2013--2026, librosa development team.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

## Appendix B — Notices for components compiled into the plugin from the JUCE tree

### B.1 libFLAC — BSD-3-Clause

**Copyright holder:** Josh Coalson (2000-2009), Xiph.Org Foundation (2011-2023). Compiled into the plugin via `juce_audio_formats`. Source: `modules/juce_audio_formats/codecs/flac/Flac Licence.txt` in the JUCE 8.0.8 checkout (the licence portion; JUCE's own preamble omitted).

```text
libFLAC - Free Lossless Audio Codec library
Copyright (C) 2000-2009  Josh Coalson
Copyright (C) 2011-2023  Xiph.Org Foundation

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

- Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

- Neither the name of the Xiph.Org Foundation nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### B.2 Ogg Vorbis — BSD-3-Clause

**Copyright holder:** Xiph.org Foundation (2002-2020). Compiled into the plugin via `juce_audio_formats`. Source: `modules/juce_audio_formats/codecs/oggvorbis/Ogg Vorbis Licence.txt` in the JUCE 8.0.8 checkout (the licence portion; JUCE's own preamble omitted).

```text
Copyright (c) 2002-2020 Xiph.org Foundation

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

- Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

- Neither the name of the Xiph.org Foundation nor the names of its
contributors may be used to endorse or promote products derived from
this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION
OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

The remaining JUCE-embedded notices (zlib, libpng, jpeglib, HarfBuzz, SheenBidi, AudioUnitSDK) are reproduced from the paths listed in section 3.1 when the installer's notice bundle is assembled (action 8).
