# Beta Test Plan

Version: 2026-09-09. Applies to the first public beta of the plugin (VST3 on Windows and
macOS, AU on macOS). The product name is a placeholder here (`<Product>`) until the naming
decision in `docs/LAUNCH_CHECKLIST.md` §1 is final.

The beta exists to answer one question: **can a producer who has never seen the plugin
install it, turn a clip into a playable instrument inside their DAW, and get MIDI out —
without help?** Everything below is instrumentation for that question.

---

## 1. Goals and success criteria

| # | metric | how it is measured | target | kill line |
|---|--------|--------------------|--------|-----------|
| G1 | **Install rate** | testers whose DAW lists the plugin ÷ testers who downloaded (form Q3 + Q4) | ≥ 90 % | < 70 % — installer/signing is not launchable |
| G2 | **First-job success rate** | `jobs.status = 'succeeded'` ÷ all jobs on each tester's first day (SQL below) | ≥ 85 % | < 60 % |
| G3 | **Processing time, warm** | `jobs.finished_at - jobs.started_at`, p95 over jobs where the worker was already running | ≤ 5 s (design budget is 2.0 s on an A10G plus network) | > 15 s |
| G3b | **Cold-start time** | same, first job after ≥ 10 min of idle (serverless GPU container + model load) | reported, ≤ 120 s | > 300 s — change hosting or keep one container warm |
| G4 | **Paywall conversion** | testers who saw the paywall at 0 credits and clicked a buy button ÷ testers who reached 0 credits (form Q11 + Paddle transactions) | ≥ 10 % click-through; ≥ 3 real purchases across the cohort | 0 purchases and < 5 % click-through |
| G5 | **Crash-free sessions** | sessions without a DAW crash or plugin hang ÷ all sessions (form Q8, bug reports at S1) | ≥ 98 % | any reproducible crash on scan or project load = launch blocker |
| G6 | **Would use it for real** | form Q13 "would you use this in a real project" | ≥ 70 % yes | < 40 % |
| G7 | **MIDI is usable** | form Q9: exported `.mid` / `.fsc` matched what they heard | ≥ 70 % "mostly or fully" | < 40 % — transcription quality is the problem, not UX |

Measurement notes:

* G2/G3 come from the database, not from testers. Query (Supabase SQL editor):
  ```sql
  select p.email,
         count(*)                                              as jobs,
         count(*) filter (where j.status = 'succeeded')        as succeeded,
         percentile_cont(0.95) within group
           (order by extract(epoch from (j.finished_at - j.started_at)))
                                                               as p95_seconds
    from public.jobs j join public.profiles p on p.id = j.user_id
   where j.created_at >= '<beta start date>'
   group by p.email order by jobs desc;
  ```
* Cold starts are excluded from G3 by dropping the first job after any gap of ≥ 10 min
  between `started_at` values; they are reported separately as G3b.
* Sessions are self-reported (Q8); once the opt-in crash reporter exists it replaces Q8.

---

## 2. Cohort

**Size:** 10–20 producers. Fewer than 10 gives no signal on install rate; more than 20 is
more support than a solo founder can handle in two weeks.

**Mix to aim for** (recruit until each cell has at least the minimum):

| host | Windows | macOS (Apple Silicon) | macOS (Intel, if any) |
|------|---------|------------------------|-----------------------|
| FL Studio 21.2+ | ≥ 4 | ≥ 2 | 0–1 |
| Ableton Live 12 | ≥ 3 | ≥ 3 | 0–1 |
| Logic Pro 11 (AU) | — | ≥ 2 | 0–1 |

Genres: skew towards trap / drill / hip-hop / EDM — the audiences the growth engine
targets, and the ones where bass separation quality is most exposed.

**Where:** r/FL_Studio, r/edmproduction, the KVR Audio forum. All three police
self-promotion; the texts below are written to survive it. In every case:

1. **Message the moderators first** (modmail on Reddit; on KVR post in the forum matching
   the product — *Instruments* — after checking the current forum rules on developer
   posts). Say you are the developer, it is a free beta, there is nothing to buy in the
   post, and ask which flair/thread they want it in. r/edmproduction in particular has
   historically confined promotion to designated threads; do not post outside what the
   mods tell you.
2. No store links, no prices, no "launch" language in the post. One link: the beta
   sign-up form.
3. Reply to every comment in the thread for the first 48 hours; the thread *is* the
   recruitment.

### 2.1 Ready-to-post recruitment texts

**r/FL_Studio** (flair: Discussion or whatever the mods assign)

> **[Beta testers wanted] Turn any clip into a playable instrument inside FL — looking for 10 producers**
>
> Hi — I'm a solo dev (yes, this is my own plugin; mods OK'd the post). I built a VST3 that
> takes a short clip (up to 60 s), separates it into bass / drums / synth / vocals on a
> cloud GPU in a couple of seconds, and gives you each stem as a chromatic instrument you
> can play from your keyboard — root-locked to C3, scale-locked to the detected key, drums
> sliced across the keys — plus the transcribed MIDI, which you can drag straight into the
> piano roll as `.mid` or `.fsc`.
>
> FL already separates stems for free since 21.2; this is about what happens *after* —
> playing the stem and getting MIDI without leaving the plugin.
>
> I need 10 people on FL Studio 21.2+ (Windows or Mac) for a two-week beta. You get free
> credits for the beta and more at launch, no NDA, post whatever you think. I need honest
> answers to a 5-minute form at the end, and bug reports when it breaks.
>
> Sign-up form: `<form link>` — first 10 who fit the mix get a download link within a day.

**r/edmproduction** (only in the thread the mods designate)

> **Beta: playable stems + MIDI from any clip, inside your DAW (VST3/AU) — 10 testers**
>
> Solo dev here, posting where the mods asked. The plugin uploads a clip (≤ 60 s), splits
> it into four stems on a cloud GPU (~2 s warm), and maps each stem across your keyboard
> as an instrument — with the key detected and a scale lock so wrong notes snap to the
> scale. Drums get sliced across keys. The transcription comes back as MIDI you drag into
> your arrangement.
>
> Looking for producers on Ableton Live 12 or FL Studio (Win/Mac), two weeks, free
> credits, no NDA. Feedback form at the end, bug reports whenever. Form: `<form link>`.

**KVR Audio forum** (Instruments; title prefix per forum convention)

> **[BETA TESTERS WANTED] `<Product>` — clip → playable stems + MIDI (VST3/AU, Win/Mac)**
>
> I'm the developer. `<Product>` is a cloud-connected instrument plugin: drop a clip up to
> 60 s, it separates bass / drums / other / vocals on a GPU and returns each stem as a
> chromatic instrument (root at C3, scale-snap to the detected key, drum slices from C1),
> plus a `.mid` (and `.fsc` for FL Studio) of what it transcribed. Auto-ADSR from the stem's
> envelope, editable.
>
> Beta runs two weeks. I'm after 10–20 testers across FL Studio 21.2+, Ableton Live 12 and
> Logic Pro 11 (AU), Windows and Apple Silicon. Free credits during the beta and at launch,
> no NDA. What I need back: the acceptance checklist (short), a feedback form, and bug
> reports with the template in the beta pack.
>
> Sign up: `<form link>`. Signed installers (notarized .pkg / signed .exe); SmartScreen may
> still warn on Windows because the certificate is new — details in the pack.

### 2.2 Sign-up form (Tally or Google Form)

1. Email (for the download link and credits).
2. Which DAW(s) do you use most? — FL Studio / Ableton Live / Logic Pro / other (which version?).
3. OS — Windows 10 / Windows 11 / macOS (Apple Silicon) / macOS (Intel); OS version.
4. Genres you produce (free text).
5. How often do you sample or chop existing audio? — never / sometimes / most projects.
6. Which stem tools have you used? — FL's built-in / Logic Stem Splitter / Samplab / Moises / Fadr / Lalal.ai / Serato Sample / none / other.
7. Screen setup — single monitor / multi-monitor; any display scaling above 100 % (Windows)?
8. Internet: roughly your upload speed (Mbps), and are you often producing offline?
9. Can you commit to ~2 hours over two weeks and a 5-minute form at the end? — yes / no.
10. Anything you specifically want this to do? (free text)

---

## 3. Timeline (2 weeks)

| day | what happens | owner |
|-----|--------------|-------|
| −7 … −1 | Internal DAW acceptance (§5) on the founder's Mac M4 and a Windows machine; every non-Pass row fixed or listed as a known issue in the beta pack | founder + assistant |
| 0 | Recruitment posts go up (after mod approval); form open | founder |
| 1–2 | Cohort selected to fill the mix; each tester gets: download links, 30 credits on their account, the beta pack (install notes, known issues, bug template, checklist) | assistant grants credits (`grant_credits` SQL), founder sends the mail |
| 3–7 | **Week 1 — install and first job.** Testers install, run the acceptance checklist rows I1–P4, report. Daily triage; fix releases as `v0.1.0-beta.N` | both |
| 8–12 | **Week 2 — depth.** Real projects, MIDI export, paywall (credits run out around here by design), offline, project reload. Mid-beta check-in mail with the three most-reported issues and what changed | both |
| 13 | Feedback form goes out (§7) | founder |
| 14 | Form closes; metrics pulled (§1); go/no-go meeting (§8) | both |
| 15+ | Thank-you mail with the 50 launch credits, changelog of what their reports changed | founder |

Communication: one email thread per tester (support@ address), plus an optional Discord
or Telegram group if ≥ 8 testers want it. No daily mails; a mid-beta check-in and the
closing form.

---

## 4. What testers get, and what they sign

* **30 credits** at the start of the beta (10× the free tier), granted directly to their
  account after they sign up on the website — enough for a real session, few enough that
  most reach the paywall in week 2, which is intentional.
* **50 credits at launch** for everyone who submits the final form, regardless of what
  they said.
* Their name (or handle) in the launch changelog, opt-in.
* **No NDA.** Testers may post, stream and share screenshots. The one request: mention it
  is a beta if they post publicly. Because there is no NDA, the beta pack states plainly
  what is unfinished so nobody discovers it in public.
* Their uploaded audio is processed on a cloud GPU and deleted within 24 hours; the beta
  pack links the Privacy Policy and asks them to upload only audio they hold the rights
  to — same terms as launch.

---

## 5. Manual DAW acceptance checklist

Run once on the founder's **Mac M4** (FL Studio, Ableton Live 12, Logic Pro 11) and once
on a **Windows 10/11 machine** (FL Studio, Ableton Live 12) before day 0; testers run the
subset marked ★ on their own setup. Fill Pass / Fail / n-a and a note for every non-Pass.
Expected values come from the API contract (upload cap 10 MB, 60 s; default root C3 =
MIDI 48; drum slices from C1 = MIDI 36; four stems `bass / drums / other ("Synth") /
vocals`; paywall at `available = 0`; balance polled every 5 s while the paywall is open).

### 5.1 Test material

Prepare these files once and reuse them on every host:

| file | purpose |
|------|---------|
| `A_loop_30s_44k.wav` | 30 s stereo WAV, clear bass + drums + melodic part, known key (e.g. F minor, 124 BPM) — the reference clip |
| `B_song_58s.mp3` | 58 s MP3, full mix with vocals |
| `C_song_90s.flac` | 90 s FLAC — exercises the 60 s truncation |
| `D_big_12MB.wav` | > 10 MB WAV — exercises the size cap |
| `E_mono_8bit.wav` | odd format: mono, 8-bit or 22.05 kHz |
| `F_not_audio.txt` | renamed text file with `.wav` extension |
| `G_silence_10s.wav` | 10 s of digital silence |

### 5.2 Rows

| ID | ★ | Step | Expected | Pass/Fail | Notes |
|----|---|------|----------|-----------|-------|
| **Install — macOS** | | | | | |
| I1 | ★ | Download the `.pkg` from the beta link in Safari; open it | Gatekeeper shows *no* "unidentified developer" block; installer opens | | |
| I2 | | `spctl -a -vv -t install <file>.pkg` in Terminal | `accepted`, `source=Notarized Developer ID` | | |
| I3 | ★ | Complete the installer | VST3 in `/Library/Audio/Plug-Ins/VST3/`, AU in `/Library/Audio/Plug-Ins/Components/`; no admin-password loop; installer says Succeeded | | |
| I4 | | `auval -v aumu <PLUGIN_CODE> <MANUFACTURER_CODE>` | `AU VALIDATION SUCCEEDED`; if Logic does not list it afterwards, `killall -9 AudioComponentRegistrar` and retry | | |
| **Install — Windows** | | | | | |
| I5 | ★ | Download `Setup.exe` in Edge; run it | Signature shows the publisher name in the UAC prompt. SmartScreen "unrecognised app" *may* appear (new certificate): **More info → Run anyway** works — record whether it appeared | | |
| I6 | | `signtool verify /pa /v Setup.exe` (Windows SDK) | `Successfully verified` | | |
| I7 | ★ | Complete the installer | VST3 in `C:\Program Files\Common Files\VST3\`; uninstaller listed in Apps & Features | | |
| **Scan** | | | | | |
| S1 | ★ | FL Studio: Options → Manage plugins → Find more plugins (with "Verify plugins" on) | Plugin found under Installed → Generators, no scan crash, no "unstable" flag | | |
| S2 | ★ | Ableton Live 12: Preferences → Plug-Ins → Rescan | Appears under Plug-Ins → VST3 (and Audio Units on macOS); no error dialog | | |
| S3 | ★ | Logic Pro 11: Plug-In Manager | AU listed, status "successfully validated" | | |
| S4 | | Quit and relaunch the DAW twice | Plugin still listed; no rescan prompt each launch | | |
| **Open the UI** | | | | | |
| U1 | ★ | Insert the plugin on an instrument track; open its window | Window opens within 2 s; sign-in overlay visible (Email, Password, Sign in, "Create an account" link) | | |
| U2 | ★ | Resize / move the window; close and reopen | Layout intact; no black or blank areas; reopens at the same size | | |
| U3 | | Windows: display scaling at 125 % and 150 % (Settings → Display) | Text crisp, controls not clipped, drag targets still hit | | |
| U4 | | macOS: external monitor with different scaling; move window between displays | No blur or half-size window after the move | | |
| **Sign in** | | | | | |
| A1 | ★ | Click "Create an account" | System browser opens the sign-up page on the website (not inside the plugin) | | |
| A2 | ★ | Sign up on the website, confirm the email, return to the plugin, sign in | Overlay closes; balance shows **3** (beta testers: 3 + granted credits) | | |
| A3 | | Wrong password | Clear error, field keeps the email, no freeze; after repeated attempts a rate-limit message rather than silence | | |
| A4 | | Sign in, quit the DAW, relaunch, reopen the plugin | Still signed in (token refreshed), balance shown, no password prompt | | |
| A5 | | "Log out" | Back to the overlay; balance hidden | | |
| **Drop a clip** | | | | | |
| D1 | ★ | Drag `A_loop_30s_44k.wav` from the DAW browser / Finder / Explorer onto the plugin | Drop accepted (highlight while hovering); "Processing" state starts | | |
| D2 | ★ | Same with `B_song_58s.mp3` | Accepted; MP3 decoded client-side | | |
| D3 | | Same with `C_song_90s.flac` | Accepted; result shows the input was **truncated to 60 s** (visible note), not rejected | | |
| D4 | | Same with `D_big_12MB.wav` | Rejected *before* upload with a message naming the 10 MB cap; no credit reserved (ledger unchanged) | | |
| D5 | | `E_mono_8bit.wav` | Accepted; stems play in stereo at the host rate | | |
| D6 | | `F_not_audio.txt` | Rejected with a readable message; no crash | | |
| D7 | | `G_silence_10s.wav` | Completes (or fails cleanly) without hanging; if it fails, the credit is **released** (ledger shows `reserve` then `release`) | | |
| D8 | | "Choose an audio file" button (file dialog path) | Same behaviour as drag-and-drop | | |
| D9 | | Drop a second clip while the first is processing | Either queued or refused with a message — never two jobs for one drop; credits reserved match jobs created | | |
| **Watch progress** | | | | | |
| P1 | ★ | During processing | Stage advances `upload → separate → transcribe → analyze → package`; progress moves; DAW audio keeps playing (no dropouts while uploading) | | |
| P2 | ★ | Time from drop to "Ready", warm worker | ≤ 5 s + upload time (note the number) | | |
| P3 | | Time from drop to "Ready", first job after ≥ 10 min idle | ≤ 120 s; the UI says it is still working (no apparent hang) — note the number | | |
| P4 | | Cancel during upload (if the UI offers it) | Job cancelled; ledger shows `reserve` then `release`; balance unchanged | | |
| P5 | | Pull the network cable mid-processing | Fails with "Request failed" / "Processing failed" within the timeout; credit released; plugin usable again | | |
| **Play stems from the keyboard** | | | | | |
| K1 | ★ | Select the bass stem; play C3 on a MIDI keyboard | Bass plays at its original pitch (root target C3 = MIDI 48 by default) | | |
| K2 | ★ | Play C2 and C4 | One octave down / up, duration preserved (Rubber Band build) or shortened/lengthened (fallback build — note which) | | |
| K3 | ★ | Select "Synth" (other) and "Vocals" | Each plays; switching stems does not click or hang | | |
| K4 | | Change "Root Target" to another note | Playback transposes accordingly; MIDI note that plays "original pitch" moves with it | | |
| K5 | ★ | Scale-Snap = **Detected** (default), play a note outside the detected scale | Note snaps to the nearest scale tone (ties resolve downward); the Root selector shows the detected root | | |
| K6 | | Scale-Snap = Major / Minor / Pentatonic Major / Pentatonic Minor / Off | Each set behaves as labelled; **Off** plays every note unsnapped | | |
| K7 | | Hold a note, change Scale-Snap mode, release | Note-off silences the note that was playing (no stuck note) | | |
| K8 | ★ | Enable **Drum mode** on the drums stem; play from C1 (MIDI 36) upward | One slice per key starting at C1, in order; keys above the last slice are silent | | |
| K9 | | Polyphony: play a 4-note chord on the synth stem | All four voices sound; CPU stays reasonable (see C1) | | |
| **ADSR and tone** | | | | | |
| E1 | ★ | After a job, look at Attack / Decay / Sustain / Release | Populated from the stem's suggested envelope (values change between bass and vocals) | | |
| E2 | ★ | Set Attack to max, then Release to max | Audible slow fade-in; long tail on release | | |
| E3 | | Cutoff / Resonance / Gain sweeps | Smooth, no zipper noise, no clipping at Gain 0 dB with a −3 dB stem | | |
| E4 | | Automate Attack from the DAW | Parameter follows automation; shows in the DAW's parameter list with a readable name and unit | | |
| **Export MIDI** | | | | | |
| M1 | ★ | Drag the **"Drag .mid"** target onto an empty track (Ableton / Logic) | A MIDI clip appears with the notes, tempo matching the detected BPM, one track per transcribed stem | | |
| M2 | ★ | FL Studio: drag **"Drag .fsc"** into the piano roll of a Sampler/instrument channel | Notes appear at the right positions; length and velocity plausible | | |
| M3 | | FL Studio: drag **"Drag .mid"** into the playlist / piano roll | Import dialog or notes appear; no error | | |
| M4 | | "Save MIDI file" / "Save FL Studio score" buttons | Files written where chosen; reopen in the DAW works | | |
| M5 | ★ | Compare the exported notes to what you hear on the bass stem | Q9 on the form: fully / mostly / partly / not at all | | |
| **Paywall and purchase** | | | | | |
| W1 | ★ | Spend credits until `available` = 0; drop another clip | Paywall opens: "You've used your 3 free credits — unlock 50 more for $9, or subscribe for $7.99/mo" with **two buttons**; "Not now" closes it | | |
| W2 | ★ | Click "50 credits" | System browser opens the checkout (Paddle) with the plan preselected; the plugin keeps polling | | |
| W3 | | Complete the purchase (sandbox card `4242 4242 4242 4242` before launch; real card after) | Within ~5 s the paywall closes by itself and the balance shows +50 | | |
| W4 | | Subscribe to "Pro Monthly" instead | Balance +60; website account page shows the subscription; the credits are marked as expiring at period end | | |
| W5 | | Reach 0 with the paywall open, then buy on the website in another window | Plugin balance updates without restarting | | |
| **Offline** | | | | | |
| O1 | ★ | Disconnect the network; open a project with stems already loaded | Stems play, keyboard works, ADSR works — nothing network-bound blocks playback | | |
| O2 | ★ | Still offline: drop a clip | Immediate "Request failed" (or similar) message; no hang, no credit reserved | | |
| O3 | | Offline at DAW launch, plugin on a saved track | UI opens; shows signed-in state from cache or a clear "offline" state; reconnecting recovers without restart | | |
| **CPU** | | | | | |
| C1 | ★ | DAW CPU meter with the plugin idle, then while playing an 8-note chord on a stem, at 128-sample buffer | Idle ≈ 0 %; playing well below what a stock sampler with 8 voices costs on the same machine — note both numbers | | |
| C2 | | Same at 64 samples | No dropouts on the M4; note the Windows result | | |
| C3 | | Three instances of the plugin in one project | CPU scales roughly linearly; no shared-state weirdness (each instance keeps its own stems) | | |
| **Project save / reload (state restore)** | | | | | |
| R1 | ★ | Save the project with a loaded job and tweaked ADSR / scale settings; close and reopen | All parameters restored; stems restored and playable (or a clear "stems expired, reload" state if the 24 h signed-URL window has passed) — **never** a silent empty plugin | | |
| R2 | | Reopen the same project the next day (> 24 h) | Parameters restored; state of stems as above; no crash | | |
| R3 | | Duplicate the track (Ableton ⌘D / FL clone channel) | The copy has the same stems and settings | | |
| R4 | | Freeze / bounce the track | Rendered audio matches live playback | | |
| **Uninstall** | | | | | |
| X1 | | macOS: remove the VST3 and component bundles; Windows: Apps & Features → Uninstall | Files gone; DAW no longer lists the plugin after a rescan; opening a project that used it shows the host's "missing plugin" placeholder, not a crash | | |

### 5.3 Host-specific notes for the runner

* **FL Studio:** test both "Use fixed size buffers" on and off in the wrapper settings;
  `.fsc` is FL-only and goes into the piano roll of the *channel* you drop it on — drop
  onto the plugin's own channel and onto a separate Sampler channel.
* **Ableton Live 12:** VST3 and AU are listed separately on macOS — run S2/U1/K1/M1 on
  both formats once. Drag `.mid` onto an empty MIDI track slot in Session view *and* into
  Arrangement view.
* **Logic Pro 11:** AU only. Logic runs its own validation beyond `auval`; a plugin that
  passes I4 can still be rejected here — S3 is the row that matters.
* **Windows machine:** if no physical Windows machine is available, a friend's PC beats a
  cloud VM (RDP audio latency makes K1–K9 meaningless). At minimum, I5–I7, S1–S2, U1–U3,
  D1, P1, M2, W1 must be run on real Windows hardware.

---

## 6. Bug reports and triage

### 6.1 Bug report template (paste into the email / form / Discord)

```
Title: <one line: what broke, where>
Build: <version from the plugin's About / installer name, e.g. v0.1.0-beta.2>
Host: <FL Studio 21.2.3 / Ableton Live 12.1 / Logic Pro 11.1> — format: <VST3 / AU>
OS: <Windows 11 23H2 / macOS 15.1> — CPU: <Apple M2 / Intel i7-12700 / …> — display scaling: <100 % / 125 % / …>
Audio device / buffer: <e.g. Focusrite 2i2, 128 samples, 48 kHz>
Clip: <format, length, size; attach it if you can — or say "cannot share">
Steps to reproduce:
  1.
  2.
  3.
Expected:
Actual:
How often: <every time / sometimes (x of y) / once>
Attachments: <screenshot / screen recording / DAW crash log*>
Checklist row (if any): <e.g. K5>
```
\* macOS crash logs: Console → Crash Reports, or `~/Library/Logs/DiagnosticReports/`.
Windows: Event Viewer → Windows Logs → Application, or the DAW's own crash dialog.
Never paste your password or an API key; screenshots of the sign-in screen are fine.

### 6.2 Severities

| severity | definition | response | blocks launch? |
|----------|------------|----------|----------------|
| **S1 — Blocker** | DAW crash or hang; plugin fails scan; installer fails; data loss (project will not reopen); a credit charged with no result and not released; a payment that did not grant credits | acknowledged within 12 h, fix release within 48 h | yes |
| **S2 — Major** | A core flow does not work for a class of users (a format not accepted, drag-out fails in one host, paywall without buttons, sign-in loop) but there is a workaround | fix within the beta | yes, unless a documented workaround exists and it affects < 20 % of the cohort |
| **S3 — Minor** | Wrong text, layout glitch, a parameter that does not save, cosmetic DPI issue, non-ideal default | fix if cheap, otherwise backlog | no |
| **S4 — Suggestion** | Feature request, workflow opinion, "it would be nice if" | logged, thanked, considered after launch | no |

Triage rule: the founder assigns severity within 24 h, the assistant reproduces (or asks
for more), every report gets a reply with its status, and the mid-beta mail lists all S1/S2
and what changed.

---

## 7. Feedback form (day 13)

1. Which DAW and OS did you test on? (as in the sign-up form)
2. Did the installer run without warnings? — yes / SmartScreen warning but I continued /
   Gatekeeper warning but I continued / I could not install (say what happened).
3. Did your DAW find the plugin on the first scan? — yes / after a rescan / no.
4. Did you see the plugin's window and sign in successfully? — yes / no (what happened?).
5. How many clips did you process, roughly? — 1–3 / 4–10 / 11–30 / more.
6. How long did a typical clip take from drop to playable? — under 5 s / 5–15 s / 15–60 s /
   over a minute / it never finished.
7. How did the stems sound compared with what you use now (FL's separator, Logic's,
   Moises, …)? — better / about the same / worse / I have nothing to compare.
8. Did the plugin or your DAW crash or freeze at any point? — no / once / more than once
   (please file a bug with the template if you have not).
9. Did the exported MIDI (`.mid` / `.fsc`) match what you heard? — fully / mostly / partly /
   not at all / I did not export MIDI.
10. Which of these did you actually use? — keyboard playing / scale-snap / drum mode /
    ADSR editing / `.mid` drag / `.fsc` drag / project save & reload.
11. Did you reach the "out of credits" screen? — no / yes and I closed it / yes and I clicked
    a buy button / yes and I bought credits or subscribed. If you clicked but did not buy:
    why?
12. Is $9 for 50 conversions / $7.99 a month for 60 — too much / about right / cheap? What
    would you pay?
13. Would you use this in a real project? — yes / maybe / no. Why?
14. What is the one thing that would make you use it every week? (free text)
15. What was the most annoying thing? (free text)
16. May we quote you (name or handle) on the website? — yes / anonymously / no.

---

## 8. How the results feed the launch decision

The go/no-go on day 14 uses the table in §1 plus the S1/S2 list:

| outcome | decision |
|---------|----------|
| All G1–G7 at target, no open S1, open S2 ≤ 2 with documented workarounds | **Go.** Launch on the next release; beta known-issues become the public changelog |
| One or two of G1–G7 below target but above the kill line, no open S1 | **Go with a fix week.** Ship the fixes to the beta cohort first, re-check the failed metrics on their reports, then launch |
| Any G-metric at or below its kill line, or any open S1 | **No-go.** Fix, re-run the affected rows of §5 on both platforms, and either extend the beta by a week with the same cohort or recruit five new testers for a clean install-rate read |
| G7 (MIDI usable) at the kill line while everything else passes | **Reposition, then go.** Lead with "playable stems inside the DAW"; treat MIDI export as a bonus in the copy until transcription improves — and say so in the changelog |
| G4 (paywall) has zero purchases but ≥ 10 % click-through | **Go, watch pricing.** Interest exists; the checkout or the price is the problem — read Q11/Q12 answers before changing either |

Two results from the beta go straight into other launch artifacts regardless of the
decision: the p95 numbers (G3/G3b) replace the "2 seconds" claim on the landing page with
a measured figure, and the Q7 stem-quality answers decide whether the separation engine
chosen in `docs/LAUNCH_CHECKLIST.md` §1 (decision 2) survives contact with trap and drill.
