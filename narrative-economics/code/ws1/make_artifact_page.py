#!/usr/bin/env python3
"""
make_artifact_page.py - build the claude.ai page edition of the WS1.0 coding
instrument (one fragment at a time, practice block, CSV export).

Reads coding_sample.csv (git-ignored) or recovers the fragments from
ws1_survey.html, and writes a single HTML file WITHOUT doctype/html/head/body
(the artifact publisher wraps it). Output goes to --out (default: scratch).
"""
import argparse, csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CODEBOOK = "v1"

PRACTICE = [
    {"text": "The bank says its new AI assistant will let it cut about 300 back-office roles by next year.",
     "rel": "1", "val": "minus", "why": "An AI word, a job word, and a claim that AI shrinks the work: relevant, alarming."},
    {"text": "Since the hospital started using AI to schedule operating rooms, it has hired two more data analysts to run the system.",
     "rel": "1", "val": "plus", "why": "AI plus hiring: the fragment says AI created work, so it is reassuring."},
    {"text": "Everyone panicked that AI would replace paralegals. Two years on, the firm employs more paralegals than before.",
     "rel": "1", "val": "plus", "why": "It quotes 'replace' but argues the fear was wrong. Debunking destruction is plus, not minus (rule 1)."},
    {"text": "The company laid off 800 people in March, most of them in sales and marketing.",
     "rel": "0", "val": "none", "why": "Layoffs, but no AI or automation word anywhere in the fragment. Do not borrow the video's topic."},
    {"text": "The newest model now scores higher than 90% of humans on the bar exam.",
     "rel": "0", "val": "none", "why": "AI capability only: no job, occupation, hiring or wage outcome is mentioned."},
    {"text": "Was it really the AI, or did management just need an excuse for the layoffs? Honestly, nobody knows yet.",
     "rel": "1", "val": "none", "why": "AI and layoffs are both there, but the speaker doubts AI is the cause. Doubt about the cause is none (rule 2)."},
    {"text": "AI will wipe out a lot of clerical work, but it will also create a wave of new roles in oversight and maintenance.",
     "rel": "1", "val": "mixed", "why": "Destruction and creation stated with roughly equal weight."},
    {"text": "AI is going to change the economy in ways we can't imagine. The real question is where you will stand in the new one.",
     "rel": "0", "val": "none", "why": "AI is present, but there is no occupation and no labour outcome: too vague to count."},
]

TEMPLATE = r'''<title>WS1.0 Narrative Coding</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>
:root{--ground:#F4F5F8;--surface:#FFFFFF;--ink:#171A21;--muted:#5B6270;--line:#E1E4EA;--accent:#0E6F6A;--accent-soft:#E6F2F1;--accent-ink:#FFFFFF;--warn:#7A4E00;--warn-soft:#FFF3DA;--ok:#1F6B3A;--ok-soft:#E4F3E9;--focus:#0E6F6A}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ground:#121417;--surface:#1A1D23;--ink:#E7E9EE;--muted:#9AA3B2;--line:#2A2F38;--accent:#4FB3AC;--accent-soft:#173331;--accent-ink:#0B1413;--warn:#E7BC66;--warn-soft:#2E2510;--ok:#7CC894;--ok-soft:#14291C;--focus:#4FB3AC}}
:root[data-theme="dark"]{--ground:#121417;--surface:#1A1D23;--ink:#E7E9EE;--muted:#9AA3B2;--line:#2A2F38;--accent:#4FB3AC;--accent-soft:#173331;--accent-ink:#0B1413;--warn:#E7BC66;--warn-soft:#2E2510;--ok:#7CC894;--ok-soft:#14291C;--focus:#4FB3AC}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:15px;line-height:1.5;padding-inline:16px;padding-block:0 40px;margin:0}
.wrap{max-width:680px;margin:0 auto}
.top{padding-block:22px 6px}
.eyebrow{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
h1{font-size:20px;line-height:1.2;margin:4px 0 0;font-weight:650;text-wrap:balance}
h2{font-size:18px;line-height:1.25;margin:0 0 10px;font-weight:650;text-wrap:balance}
.progress{position:sticky;top:env(safe-area-inset-top,0px);background:var(--ground);padding-block:10px 8px;z-index:2}
.bar{height:6px;background:var(--line);border-radius:6px;overflow:hidden}
.fill{height:100%;width:0;background:var(--accent);border-radius:6px;transition:width .25s ease}
.ptext{display:flex;justify-content:space-between;gap:12px;font-size:12px;color:var(--muted);margin-top:6px;font-variant-numeric:tabular-nums}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:22px 20px;margin-block:12px}
.rules{background:var(--ground);border-radius:10px;padding:12px 14px;font-size:13.5px;line-height:1.6;margin-block:12px}
.rules b{font-weight:650}
.note{font-size:13px;color:var(--muted);line-height:1.5}
label.field{display:block;font-size:13px;font-weight:600;margin-top:14px}
input[type=text]{width:100%;padding:11px 12px;border:1.5px solid var(--line);border-radius:10px;font:inherit;background:var(--surface);color:var(--ink);margin-top:6px}
input[type=text]:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.check{display:flex;gap:10px;align-items:flex-start;font-size:14px;margin-top:14px;cursor:pointer}
.check input{margin-top:3px;accent-color:var(--accent)}
.frag{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-block:12px 14px}
.frag .eyebrow{display:flex;justify-content:space-between;gap:10px}
.frag .fid{font:11px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;letter-spacing:0;text-transform:none;font-weight:400}
.frag p{font-family:"Source Serif 4",Georgia,"Times New Roman",serif;font-size:17px;line-height:1.6;border-left:3px solid var(--accent);padding-left:14px;margin:10px 0 0}
fieldset.q{border:0;padding:0;margin:14px 0 0;min-width:0}
fieldset.q legend{font-weight:650;font-size:15px;padding:0}
.help{font-size:13px;color:var(--muted);margin:4px 0 10px;line-height:1.5}
.opts{display:grid;gap:8px}
.opt{position:relative;display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border:1.5px solid var(--line);border-radius:10px;background:var(--surface);cursor:pointer;transition:border-color .12s,background .12s}
.opt input{position:absolute;opacity:0;width:1px;height:1px;margin:0}
.opt:hover{border-color:var(--accent)}
.opt.on,.opt:has(input:checked){border-color:var(--accent);background:var(--accent-soft)}
.opt:has(input:focus-visible){outline:2px solid var(--focus);outline-offset:2px}
.opt b{display:block;font-size:15px;font-weight:600}
.opt small{display:block;color:var(--muted);font-size:12.5px;margin-top:2px;line-height:1.4}
.key{font:11px/1 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:3px 5px;margin-left:auto;align-self:center;flex-shrink:0}
.actions{display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap}
.btn{appearance:none;border:0;border-radius:10px;padding:12px 18px;font:inherit;font-weight:650;cursor:pointer;background:var(--accent);color:var(--accent-ink)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn.ghost{background:transparent;border:1.5px solid var(--line);color:var(--ink)}
.btn:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.feedback{border-radius:10px;padding:12px 14px;margin-top:14px;font-size:14px;line-height:1.55}
.feedback.ok{background:var(--ok-soft);color:var(--ok)}
.feedback.miss{background:var(--warn-soft);color:var(--warn)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-block:12px}
.stat{background:var(--ground);border-radius:10px;padding:10px 12px}
.stat b{display:block;font-size:20px;font-variant-numeric:tabular-nums;font-weight:650}
.stat span{font-size:12px;color:var(--muted)}
textarea{width:100%;min-height:150px;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;border:1.5px solid var(--line);border-radius:10px;padding:10px;background:var(--ground);color:var(--ink);margin-top:8px}
details.ref{margin-block:6px 4px;font-size:13px}
details.ref summary{cursor:pointer;color:var(--accent);font-weight:600;list-style:none}
details.ref summary::-webkit-details-marker{display:none}
details.ref .rules{margin-top:8px}
.ref table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:6px}
.ref td{padding:4px 6px;border-top:1px solid var(--line);vertical-align:top}
.ref td:first-child{white-space:nowrap;font-weight:650}
.msg{font-size:13px;margin-top:10px;min-height:1.2em}
.msg.err{color:var(--warn)}
.log{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--muted);margin-top:12px;word-break:break-word}
kbd{font:11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;border:1px solid var(--line);border-radius:4px;padding:1px 4px}
@media (max-width:420px){.frag p{font-size:16px}h1{font-size:18px}.card{padding:18px 16px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
<header class="top">
  <div class="eyebrow">WS1.0 · Narrative validation gate</div>
  <h1>AI × Jobs Narrative Coding</h1>
</header>

<div class="progress" id="progressWrap" hidden>
  <div class="bar"><div class="fill" id="pfill"></div></div>
  <div class="ptext"><span id="ptext-left"></span><span id="ptext-right"></span></div>
</div>

<!-- WELCOME -->
<section id="s-welcome" class="card">
  <h2>Before you start</h2>
  <p>You will read short fragments (about 50 words each) taken from YouTube transcripts about AI and work, and answer two questions about each one. First <b>8 practice items with answers</b>, then <b>300 real fragments</b>. It takes about 45–60 minutes; you can close this page and continue later on the same device.</p>
  <div class="rules">
    <b>Rules</b><br>
    • Code alone — do not discuss fragments with anyone while coding.<br>
    • Judge <b>only the words in the fragment</b>, not the video's topic.<br>
    • One fragment at a time, no going back — a first reading under the rules is exactly what we need.<br>
    • The order of fragments is random and different for every coder.
  </div>
  <label class="field" for="coder-name">Your name or coder ID</label>
  <input type="text" id="coder-name" placeholder="e.g. Anna, Coder_B" autocomplete="off" maxlength="60">
  <label class="check" for="lang-ok"><input type="checkbox" id="lang-ok"><span>I read English comfortably (all fragments are in English).</span></label>
  <div class="actions">
    <button class="btn" id="btn-start" type="button">Start with the practice items</button>
  </div>
  <div class="msg" id="welcome-msg"></div>
  <div id="resume" hidden>
    <p class="note" id="resume-text"></p>
    <div class="actions">
      <button class="btn" id="btn-resume" type="button">Resume</button>
      <button class="btn ghost" id="btn-restart" type="button">Start over</button>
    </div>
  </div>
</section>

<!-- ITEM (practice + coding) -->
<section id="s-item" hidden>
  <details class="ref">
    <summary>Coding rules — quick reference</summary>
    <div class="rules">
      <b>Relevant = Yes</b> only if THIS fragment has an AI/automation word <b>and</b> a job/occupation word <b>and</b> connects them. Anything missing → No.
      <table>
        <tr><td>Alarming (minus)</td><td>AI destroys / replaces / shrinks jobs, freezes hiring, lowers wages.</td></tr>
        <tr><td>Reassuring (plus)</td><td>AI creates / augments jobs — <b>or</b> the destruction fear is overblown or false (debunking, "had to rehire", "AI costs more than the worker").</td></tr>
        <tr><td>Mixed</td><td>Both directions, roughly equal weight.</td></tr>
        <tr><td>Neutral (none)</td><td>Relevant, but no direction: a question, background, or doubt whether AI is really the cause.</td></tr>
      </table>
      <b>Rule 1:</b> debunking destruction = plus, not minus. <b>Rule 2:</b> doubt about the cause = none, not minus.
    </div>
  </details>

  <div class="frag">
    <div class="eyebrow"><span id="item-label"></span><span class="fid" id="item-id"></span></div>
    <p id="item-text"></p>
  </div>

  <fieldset class="q" id="q1">
    <legend>1. Is this fragment relevant to "AI affecting jobs"?</legend>
    <div class="help">Yes only if the fragment itself has an AI/automation word AND a job/occupation word AND connects them.</div>
    <div class="opts">
      <label class="opt" for="q1-yes"><input type="radio" name="q1" id="q1-yes" value="1"><span><b>Yes (1)</b><small>AI word + job word + a connection, all in this fragment</small></span><span class="key">1</span></label>
      <label class="opt" for="q1-no"><input type="radio" name="q1" id="q1-no" value="0"><span><b>No (0)</b><small>No AI word, or no job word, or no connection</small></span><span class="key">0</span></label>
    </div>
  </fieldset>

  <fieldset class="q" id="q2" hidden>
    <legend>2. What is the valence (direction)?</legend>
    <div class="help">On balance, which story does this fragment tell?</div>
    <div class="opts">
      <label class="opt" for="q2-minus"><input type="radio" name="q2" id="q2-minus" value="minus"><span><b>Alarming (minus)</b><small>AI destroys, replaces or shrinks jobs, freezes hiring, lowers wages</small></span><span class="key">A</span></label>
      <label class="opt" for="q2-plus"><input type="radio" name="q2" id="q2-plus" value="plus"><span><b>Reassuring (plus)</b><small>AI creates or augments jobs — or the destruction fear is debunked</small></span><span class="key">S</span></label>
      <label class="opt" for="q2-mixed"><input type="radio" name="q2" id="q2-mixed" value="mixed"><span><b>Mixed</b><small>Both directions, roughly equal</small></span><span class="key">D</span></label>
      <label class="opt" for="q2-none"><input type="radio" name="q2" id="q2-none" value="none"><span><b>Neutral / no direction (none)</b><small>A question, background, or doubt about the cause</small></span><span class="key">F</span></label>
    </div>
  </fieldset>

  <div class="feedback" id="feedback" hidden></div>
  <div class="actions">
    <button class="btn" id="btn-next" type="button" disabled>Next →</button>
    <span class="note" id="item-hint">Keys: <kbd>1</kbd>/<kbd>0</kbd> relevance · <kbd>A</kbd><kbd>S</kbd><kbd>D</kbd><kbd>F</kbd> valence · <kbd>Enter</kbd> next</span>
  </div>
</section>

<!-- FINISH -->
<section id="s-finish" class="card" hidden>
  <h2>All fragments coded — thank you</h2>
  <div class="stats">
    <div class="stat"><b id="st-n">0</b><span>fragments coded</span></div>
    <div class="stat"><b id="st-rel">0</b><span>marked relevant</span></div>
    <div class="stat"><b id="st-min">0</b><span>minutes</span></div>
    <div class="stat"><b id="st-med">0</b><span>median sec / fragment</span></div>
  </div>
  <p class="note" id="practice-score"></p>
  <div class="actions">
    <button class="btn" id="btn-save" type="button" hidden>Save results (CSV)</button>
    <button class="btn ghost" id="btn-copy" type="button">Copy results as text</button>
  </div>
  <div class="msg" id="finish-msg"></div>
  <p class="note" id="save-unavailable" hidden>Saving a file is not available in this view — copy the text below and send it to the researcher instead.</p>
  <p class="note">Send the saved file (or the copied text) to the researcher. Please do not edit it.</p>
  <textarea id="csv-box" readonly spellcheck="false" aria-label="Results as CSV text"></textarea>
  <div class="log" id="session-log"></div>
</section>
</div>

<script>
const FRAGMENTS = __FRAGMENTS_JSON__;
const PRACTICE = __PRACTICE_JSON__;
const CODEBOOK = "__CODEBOOK__";
const N = FRAGMENTS.length;
const $ = id => document.getElementById(id);
const use = name => (window.claude && typeof window.claude.use === "function")
  ? window.claude.use(name).catch(() => null) : Promise.resolve(null);

let S = blank();
let q1 = null, q2 = null, itemStart = 0, checked = false, sessionTimer = null;

function blank() { return { coder: "", mode: "welcome", pIdx: 0, cIdx: 0, order: [], answers: [], practice: [], startedAt: null, finishedAt: null, seed: 0 }; }
// same hash + LCG as ws1_survey.html / build_form.gs -> identical order for the same coder name
function hashStr(s) { let h = 0; for (let i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; } return Math.abs(h); }
function seededShuffle(arr, seed) {
  let s = seed; const rand = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
  const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a;
}
const key = name => "ws1v2_" + name;
function persist() { try { localStorage.setItem(key(S.coder), JSON.stringify(S)); localStorage.setItem("ws1v2_last", S.coder); } catch (e) {} }
function loadSaved(name) { try { const r = localStorage.getItem(key(name)); return r ? JSON.parse(r) : null; } catch (e) { return null; } }
function safeName(s) { return (s.replace(/[^A-Za-z0-9_\-]+/g, "_").replace(/^_+|_+$/g, "")) || "coder"; }

function show(id) {
  ["s-welcome", "s-item", "s-finish"].forEach(s => { $(s).hidden = (s !== id); });
  $("progressWrap").hidden = (id !== "s-item");
}
function setMsg(id, text, err) { const el = $(id); el.textContent = text || ""; el.className = "msg" + (err ? " err" : ""); }

// ---------- welcome ----------
$("btn-start").addEventListener("click", () => {
  const name = $("coder-name").value.trim();
  if (!name) { setMsg("welcome-msg", "Please enter your name or coder ID.", true); return; }
  if (!$("lang-ok").checked) { setMsg("welcome-msg", "Please confirm you read English comfortably — the fragments are in English.", true); return; }
  setMsg("welcome-msg", "");
  const saved = loadSaved(name);
  if (saved && saved.mode !== "welcome") {
    const done = saved.mode === "finish" ? N : (saved.mode === "coding" ? saved.cIdx : 0);
    $("resume-text").textContent = saved.mode === "finish"
      ? "This name has already finished all " + N + " fragments on this device. Resume to see the results again, or start over with a fresh run."
      : "Found saved progress for " + name + ": " + done + " of " + N + " fragments coded" + (saved.mode === "practice" ? " (still in practice)" : "") + ".";
    $("resume").hidden = false;
    $("btn-resume").onclick = () => { S = saved; $("resume").hidden = true; resume(); };
    $("btn-restart").onclick = () => { $("resume").hidden = true; begin(name); };
    return;
  }
  begin(name);
});
function begin(name) {
  S = blank(); S.coder = name; S.seed = hashStr(name);
  S.order = seededShuffle(Array.from({ length: N }, (_, i) => i), S.seed);
  S.mode = "practice"; persist(); resume();
}
function resume() {
  if (S.mode === "finish") { finish(); return; }
  show("s-item"); startSessionClock(); render();
}

// ---------- item screen ----------
function resetChoices() {
  q1 = null; q2 = null; checked = false;
  document.querySelectorAll('input[name="q1"], input[name="q2"]').forEach(i => { i.checked = false; });
  document.querySelectorAll(".opt").forEach(o => o.classList.remove("on"));
  $("q2").hidden = true; $("feedback").hidden = true; $("feedback").textContent = "";
  $("btn-next").disabled = true;
  $("btn-next").textContent = S.mode === "practice" ? "Check answer" : "Next →";
}
function render() {
  const practice = S.mode === "practice";
  let item, label, id;
  if (practice) { item = PRACTICE[S.pIdx]; label = "Practice " + (S.pIdx + 1) + " of " + PRACTICE.length; id = "training example"; }
  else { item = FRAGMENTS[S.order[S.cIdx]]; label = "Fragment " + (S.cIdx + 1) + " of " + N; id = item.id; }
  $("item-label").textContent = label; $("item-id").textContent = id; $("item-text").textContent = item.text;
  resetChoices();
  const frac = practice ? S.pIdx / PRACTICE.length : S.cIdx / N;
  $("pfill").style.width = (frac * 100).toFixed(1) + "%";
  $("ptext-left").textContent = practice ? "Practice · answers are shown after each item" : (S.cIdx + " coded · " + (N - S.cIdx) + " remaining");
  itemStart = Date.now();
  window.scrollTo({ top: 0, behavior: "auto" });
}
function pickQ1(v) {
  q1 = v; $("q1-" + (v === "1" ? "yes" : "no")).checked = true;
  document.querySelectorAll("#q1 .opt").forEach(o => o.classList.toggle("on", o.htmlFor === "q1-" + (v === "1" ? "yes" : "no")));
  if (v === "1") {
    q2 = null; $("q2").hidden = false;
    document.querySelectorAll('input[name="q2"]').forEach(i => { i.checked = false; });
    document.querySelectorAll("#q2 .opt").forEach(o => o.classList.remove("on"));
  } else { q2 = "none"; $("q2").hidden = true; }
  if (checked) { checked = false; $("feedback").hidden = true; $("btn-next").textContent = "Check answer"; }
  updateNext();
}
function pickQ2(v) {
  q2 = v; $("q2-" + v).checked = true;
  document.querySelectorAll("#q2 .opt").forEach(o => o.classList.toggle("on", o.htmlFor === "q2-" + v));
  if (checked) { checked = false; $("feedback").hidden = true; $("btn-next").textContent = "Check answer"; }
  updateNext();
}
function updateNext() { $("btn-next").disabled = !(q1 !== null && q2 !== null); }
document.querySelectorAll('input[name="q1"]').forEach(i => i.addEventListener("change", () => pickQ1(i.value)));
document.querySelectorAll('input[name="q2"]').forEach(i => i.addEventListener("change", () => pickQ2(i.value)));

const VAL_LABEL = { minus: "Alarming (minus)", plus: "Reassuring (plus)", mixed: "Mixed", none: "Neutral / no direction (none)" };
function showFeedback() {
  const it = PRACTICE[S.pIdx];
  const relOk = q1 === it.rel;
  const valOk = it.rel === "0" ? true : q2 === it.val;
  const ok = relOk && valOk;
  const fb = $("feedback");
  fb.className = "feedback " + (ok ? "ok" : "miss");
  fb.textContent = (ok ? "Correct. " : "Not quite. ") + "Codebook answer: relevant = " + (it.rel === "1" ? "Yes" : "No")
    + (it.rel === "1" ? ", valence = " + VAL_LABEL[it.val] : "") + ". " + it.why;
  fb.hidden = false;
  S.practice.push({ i: S.pIdx, rel: q1, val: q2, ok: ok });
}
$("btn-next").addEventListener("click", () => {
  if (q1 === null || q2 === null) return;
  if (S.mode === "practice") {
    if (!checked) { showFeedback(); checked = true; $("btn-next").textContent = (S.pIdx + 1 < PRACTICE.length) ? "Next practice item →" : "Start the 300 fragments →"; persist(); return; }
    S.pIdx++;
    if (S.pIdx >= PRACTICE.length) { S.mode = "coding"; S.cIdx = 0; S.answers = []; S.startedAt = new Date().toISOString(); }
    persist(); render(); return;
  }
  const f = FRAGMENTS[S.order[S.cIdx]];
  S.answers.push({ frag_id: f.id, rel: q1, val: q2, position: S.cIdx + 1, secs: Math.max(1, Math.round((Date.now() - itemStart) / 1000)) });
  S.cIdx++;
  if (S.cIdx >= N) { S.mode = "finish"; S.finishedAt = new Date().toISOString(); persist(); finish(); return; }
  persist(); render();
});
function startSessionClock() {
  if (sessionTimer) return;
  const tick = () => {
    if ($("s-item").hidden) return;
    const from = S.startedAt ? Date.parse(S.startedAt) : null;
    $("ptext-right").textContent = from ? ("session " + Math.max(0, Math.round((Date.now() - from) / 60000)) + " min") : "";
  };
  tick(); sessionTimer = setInterval(tick, 30000);
}
document.addEventListener("keydown", e => {
  if ($("s-item").hidden || e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === "1" || k === "y") pickQ1("1");
  else if (k === "0" || k === "2" || k === "n") pickQ1("0");
  else if (q1 === "1" && k === "a") pickQ2("minus");
  else if (q1 === "1" && k === "s") pickQ2("plus");
  else if (q1 === "1" && k === "d") pickQ2("mixed");
  else if (q1 === "1" && k === "f") pickQ2("none");
  else if (k === "enter" && !$("btn-next").disabled) { e.preventDefault(); $("btn-next").click(); }
});

// ---------- finish ----------
function csvCell(s) { s = String(s == null ? "" : s); return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
function buildCSV() {
  const text = {}; FRAGMENTS.forEach(f => { text[f.id] = f.text; });
  const rows = S.answers.slice().sort((a, b) => a.frag_id.localeCompare(b.frag_id));
  const head = ["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none", "position", "time_seconds", "coder", "codebook_version", "order_seed", "session_start", "session_end"];
  const lines = [head.join(",")];
  for (const r of rows) {
    lines.push([r.frag_id, text[r.frag_id] || "", r.rel, r.val, r.position, r.secs, S.coder, CODEBOOK, S.seed, S.startedAt || "", S.finishedAt || ""].map(csvCell).join(","));
  }
  return lines.join("\n") + "\n";
}
function median(a) { if (!a.length) return 0; const s = a.slice().sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : Math.round((s[m - 1] + s[m]) / 2); }
async function finish() {
  show("s-finish");
  const n = S.answers.length, rel = S.answers.filter(a => a.rel === "1").length;
  const mins = (S.startedAt && S.finishedAt) ? Math.round((Date.parse(S.finishedAt) - Date.parse(S.startedAt)) / 60000) : 0;
  $("st-n").textContent = n; $("st-rel").textContent = rel; $("st-min").textContent = mins; $("st-med").textContent = median(S.answers.map(a => a.secs));
  const pOk = S.practice.filter(p => p.ok).length;
  $("practice-score").textContent = "Practice: " + pOk + " of " + PRACTICE.length + " matched the codebook on the first try.";
  const csv = buildCSV(); $("csv-box").value = csv;
  $("session-log").textContent = "coder=" + S.coder + " · codebook " + CODEBOOK + " · order seed " + S.seed + " · started " + (S.startedAt || "—") + " · finished " + (S.finishedAt || "—") + " · " + n + " rows";
  $("btn-copy").onclick = async () => {
    try { await navigator.clipboard.writeText(csv); setMsg("finish-msg", "Copied — paste it into a message to the researcher."); }
    catch (e) { $("csv-box").focus(); $("csv-box").select(); setMsg("finish-msg", "Select all the text below (Ctrl/Cmd+A) and copy it.", true); }
  };
  const dl = await use("downloads");
  if (!dl) { $("save-unavailable").hidden = false; return; }
  const btn = $("btn-save"); btn.hidden = false;
  btn.onclick = async () => {
    btn.disabled = true;
    try { await dl.save({ filename: "ws1_coded_" + safeName(S.coder) + ".csv", data: csv }); setMsg("finish-msg", "Saved. Send the file to the researcher."); }
    catch (e) {
      const code = e && e.code;
      if (code === "declined") setMsg("finish-msg", "Not saved — try again, or copy the text below.", true);
      else if (code === "rate_limited") setMsg("finish-msg", "Please wait a moment and try again.", true);
      else { btn.hidden = true; $("save-unavailable").hidden = false; }
    }
    btn.disabled = false;
  };
}

// ---------- boot (hot reload across republish, then localStorage) ----------
function boot(data) {
  try { if (data && data.S && data.S.coder) { S = data.S; if (S.mode !== "welcome") { resume(); return; } } } catch (e) {}
  try { const last = localStorage.getItem("ws1v2_last"); if (last) $("coder-name").value = last; } catch (e) {}
}
try { window.claude && window.claude.hot && typeof window.claude.hot.snapshot === "function" && window.claude.hot.snapshot(() => ({ S })); } catch (e) {}
try {
  if (window.claude && window.claude.hot && typeof window.claude.hot.ready === "function") window.claude.hot.ready(boot);
  else boot(window.claude && window.claude.hot ? window.claude.hot.data : null);
} catch (e) { boot(null); }
</script>
'''


def load_fragments(sample, html):
    if os.path.exists(sample):
        with open(sample, encoding="utf-8-sig") as fh:
            return [{"id": r["frag_id"], "text": r["text"]} for r in csv.DictReader(fh)], sample
    if os.path.exists(html):
        h = open(html, encoding="utf-8").read()
        i = h.index("const FRAGMENTS = ") + len("const FRAGMENTS = ")
        return json.JSONDecoder().raw_decode(h, i)[0], html
    raise SystemExit("no coding_sample.csv and no ws1_survey.html to recover from")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default=os.path.join(HERE, "coding_sample.csv"))
    ap.add_argument("--html", default=os.path.join(HERE, "ws1_survey.html"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    frags, src = load_fragments(a.sample, a.html)
    ids = [f["id"] for f in frags]
    assert len(ids) == len(set(ids)) and all(f["text"].strip() for f in frags)
    js = lambda obj: json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    page = (TEMPLATE.replace("__FRAGMENTS_JSON__", js(frags))
                    .replace("__PRACTICE_JSON__", js(PRACTICE))
                    .replace("__CODEBOOK__", CODEBOOK))
    assert "__" + "FRAGMENTS_JSON__" not in page and "__PRACTICE" + "_JSON__" not in page
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"fragments {len(frags)} (from {os.path.basename(src)}), practice {len(PRACTICE)}, "
          f"page {len(page.encode('utf-8'))/1024:.0f} KB -> {a.out}")


if __name__ == "__main__":
    main()
