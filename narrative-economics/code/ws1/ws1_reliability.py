#!/usr/bin/env python3
"""
ws1_reliability.py - WS1.0 reliability analysis, implemented literally from
PROTOCOL_WS1.0.md sections 5-9 (identical in v1, 2026-09-18, and v1.1,
2026-10-10). The protocol version actually on disk is read at run time and
recorded with its sha256 in the report.

Inputs: one CSV per coder, from any of the three instruments
  (a) the claude.ai page (make_artifact_page.py): frag_id, text,
      human_relevant_0_1, human_valence_minus_plus_none, position,
      time_seconds, coder, codebook_version, order_seed, session_start,
      session_end, ui_language, english_level, source
      [, practice_correct, practice_n -- exported since 2026-10-10]
  (b) gforms/gforms_to_csv.py and (c) ws1_survey.html: the first four
      columns only.
Coder identity = the `coder` column if present, else the file stem.
Metadata the 4-column formats lack can be supplied with --meta (columns
coder, source, english_level, practice_correct, practice_n). Anything still
missing is reported as "not recorded"; every inclusion rule that depends on
it is "not assessable", and a rule that is not assessable is NOT passed
(section 5 admits a coder only if all rules hold).

Computed (protocol section in brackets):
  [5] inclusion rules a-d per coder                     -> exclusions.csv
  [6] primary pairs; Cohen's kappa for relevance (all fragments), valence on
      fragments both coders marked relevant, and valence on all fragments
      with `none` for non-relevant; percentile-bootstrap 95% CIs over
      fragments; gate = mean pairwise kappa >= 0.70 on relevance AND on
      (conditional) valence, compared exactly (rational arithmetic on the
      label counts, so a kappa of exactly 0.70 passes)
  [7] Krippendorff's alpha (nominal, missing allowed), PI vs each coder,
      kappa by recruitment source and by interface language, dictionary
      v0/v1 (and any --channel, e.g. the LLM channel) vs gold labels,
      timing distributions
  [8] gold labels: plurality among eligible coders, ties broken by the PI's
      label; valence is voted among the voters who marked the fragment
      relevant. Two other readings of section 8 are reported as sensitivity
      analyses (ADJ_READINGS)                            -> gold_labels.csv
  [9] decision
Everything goes to reliability_report.md and reliability.json in --out-dir.

The PI must be identified: --pi NAME has to match an input coder, otherwise
the run stops (the PI's coding must never reach the primary kappa); or
--pi-did-not-code declares that no PI file is among the inputs.

Stdlib only (like the rest of ws1/). Usage:
    python3 ws1_reliability.py ws1_coded_A.csv ws1_coded_B.csv ws1_coded_PI.csv \\
        (--pi PI_CODER_NAME | --pi-did-not-code) [--meta coders.csv] [--boot 1000] \\
        [--seed 2026] [--out-dir DIR] [--fragments coding_sample.csv|ws1_survey.html] \\
        [--channel LLM=llm_labels.csv]
"""
import argparse, csv, datetime, hashlib, json, math, os, random, re, statistics, subprocess, sys
from collections import Counter
from fractions import Fraction
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PROTOCOL_FILE = os.path.join(HERE, "PROTOCOL_WS1.0.md")
PROTOCOL_GIT_PATH = "narrative-economics/code/ws1/PROTOCOL_WS1.0.md"
PROTOCOL_KNOWN = ("1", "1.1")         # versions whose sections 5-9 this script implements
CODEBOOK = "v1"
GATE = 0.70                           # for display and JSON
GATE_EXACT = Fraction(7, 10)          # the comparison itself (section 6)
N_PROTOCOL = 300                      # section 2/5(c): "all 300 fragments"
BOOT_PROTOCOL = 1000                  # section 6: "1,000 resamples over fragments"
REL_CATS = ("0", "1")
VAL_CATS = ("minus", "plus", "mixed", "none")
ENGLISH_LEVELS = ("native", "fluent", "good", "basic")
ENGLISH_OK = ("native", "fluent", "good")          # rule 5(a)
SOURCES = ("public", "researcher", "other")        # page values; "public" = publicly recruited
PRACTICE_ITEMS, PRACTICE_MIN = 8, 6                # rule 5(b): >= 6 of 8, first attempt
MIN_MEDIAN_SECONDS = 3.0                           # rule 5(d)
FAST_SECONDS = 3.0                                 # "share under 3 s" in the timing table
REQUIRED = ("frag_id", "human_relevant_0_1", "human_valence_minus_plus_none")
PAGE_MARKERS = ("time_seconds", "coder", "english_level", "source")
SESSION_FIELDS = ("codebook_version", "order_seed", "session_start", "session_end",
                  "ui_language", "english_level", "source", "practice_correct", "practice_n")
META_FIELDS = ("source", "english_level", "practice_correct", "practice_n")
DIMS = ("relevance", "valence_conditional", "valence_all")
DIM_KEY = {"relevance": "rel", "valence_conditional": "val_cond", "valence_all": "val_all"}
DIM_LABEL = {"relevance": "relevance (all fragments)",
             "valence_conditional": "valence (both marked relevant)",
             "valence_all": "valence (all fragments, none for non-relevant)"}
RULES = (("a", "English good/fluent/native"), ("b", "practice >= 6 of 8, first attempt"),
         ("c", "all fragments completed"), ("d", "median time >= 3 s"))
PASS, FAIL, NA = "pass", "fail", "not assessable"
LLM_COLS = ("frag_id", "relevant_llm", "valence_llm")   # llm_labels.csv, PROTOCOL section 12.2

# Section 8 readings: (name, the PI votes when eligible, valence rule, text).
# The first is the gold standard of record (gold_labels.csv, machine channels);
# the others are reported as sensitivity analyses. Which reading is primary is
# a reading of section 8 that the lead confirms; to change it, reorder.
ADJ_READINGS = (
    ("pi_votes", True, "relevant_voters",
     "eligible coders vote, the PI too when eligible; valence is voted among the voters who "
     "marked the fragment relevant, and the PI breaks a valence tie only if the PI marked it relevant"),
    ("pi_breaks_ties_only", False, "relevant_voters",
     "the PI does not vote and only breaks ties among the eligible non-PI coders; valence as above"),
    ("valence_over_all_labels", True, "all_labels",
     "as the first, but valence is voted over every voter's all-fragments label (`none` from "
     "coders who marked the fragment not relevant counts as a vote)"),
)


class DataError(Exception):
    """An input problem that must stop the analysis (fail loudly)."""


# ---------------------------------------------------------------------------
# Dictionary v0, reconstructed verbatim from git history.
# Source: commit a2384895755c63ac3a42ec435bc3b8302760566a ("WS1.0: first real
# corpus + dictionary classifier + kappa gate"), i.e. 7eb5a1e^ -- the parent of
# the stance fix 7eb5a1e. File narrative-economics/code/ws1/ws1_pipeline.py,
# git blob 4311d765b036a451e54b905217d2ea0edf0c1f41. Term lists and classify()
# are copied unchanged (names prefixed V0_). At run time the copy is compared
# with `git show` when git history is available; a mismatch stops the run.
#
# Which dictionary drew the 300-fragment sample is NOT determined by these
# counts. On the 300 fragments v0 marks 136 relevant (the 136 / 164 of
# PROTOCOL section 2) and v1 marks 140, and every v0-relevant fragment is also
# v1-relevant, so a v1 draw would also show 136 under v0. The corpus (431
# fragments) has 136 v0-relevant (ws1_summary.md at a238489) and 140
# v1-relevant (at 7eb5a1e); all 140 are in the sample. ws1_pipeline.py takes
# every relevant fragment, so that is certain under a v1 draw and has
# probability C(291,160)/C(295,164) = 0.094 under a v0 draw (the 4 v1-only
# fragments must all fall among the 164 drawn from 295). The commit order
# also points to v1: 7eb5a1e re-ran the pipeline (which rewrites
# coding_sample.csv) at 00:28 UTC on 2026-06-20, and ws1_survey.html, which
# holds the 300, was first committed at 12:30 UTC (2453bb2). The evidence
# leans to v1; settling it needs the original coding_sample.csv/fragments.csv.
# ---------------------------------------------------------------------------
V0_COMMIT = "a2384895755c63ac3a42ec435bc3b8302760566a"
V0_PATH = "narrative-economics/code/ws1/ws1_pipeline.py"
V0_BLOB = "4311d765b036a451e54b905217d2ea0edf0c1f41"
V1_FROZEN_BLOB = "15759519ec822077ab755478193a6b270962fbed"   # PROTOCOL section 12.1
V0_AI_TERMS = [
    "ai", "a.i.", "artificial intelligence", "chatgpt", "chat gpt", "gpt",
    "llm", "generative ai", "gen ai", "genai", "automation", "automate",
    "automated", "algorithm", "machine learning", "chatbot", "ai agent",
    "agentic", "openai", "anthropic", "claude", "gemini", "copilot", "robot",
]
V0_OCC_TERMS = [
    "job", "jobs", "worker", "workers", "employee", "employees", "role",
    "roles", "position", "staff", "headcount", "workforce", "profession",
    "occupation", "hiring", "hire", "career", "white-collar", "white collar",
    "blue-collar", "blue collar", "entry-level", "entry level", "engineer",
    "developer", "programmer", "coder", "lawyer", "paralegal", "accountant",
    "analyst", "customer service", "customer support", "writer", "intern",
    "internship", "manager", "radiologist", "physician", "doctor", "teller",
    "bookkeeper", "clerk", "software engineer", "associate", "assistant",
]
V0_DISPLACE_TERMS = [   # X- (destruction)
    "replace", "replacing", "replaced", "layoff", "layoffs", "laid off",
    "lay off", "fired", "firing", "fire ", "cut ", "cuts", "cutting",
    "eliminate", "eliminated", "eliminating", "displacement", "displace",
    "displaced", "lose their job", "lose your job", "losing jobs",
    "job loss", "job losses", "unemployment", "obsolete", "redundant",
    "downsize", "slash", "slashed", "wipe out", "purge", "take your job",
    "take our job", "took their job", "replace your job", "replace workers",
    "replace humans", "replacing humans", "no way in", "stop hiring",
    "hiring freeze", "avoid hiring",
]
V0_CREATE_TERMS = [     # X+ (creation / augmentation / skeptical-debunk)
    "new job", "new jobs", "new role", "new roles", "created", "creating",
    "job creation", "create jobs", "hiring back", "rehire", "rehiring",
    "rehired", "augment", "augmentation", "opportunity", "opportunities",
    "demand for", "complement", "ai won't", "won't replace", "not replace",
    "didn't replace", "doesn't replace", "no evidence", "overstated",
    "exaggerat", "cover story", "excuse", "ai washing", "myth", "not happening",
    "no good evidence", "isn't replacing", "negligible", "augmenting",
    "new opportunities", "didn't take", "create new", "won't take your job",
]
V0_LISTS = {"AI_TERMS": V0_AI_TERMS, "OCC_TERMS": V0_OCC_TERMS,
            "DISPLACE_TERMS": V0_DISPLACE_TERMS, "CREATE_TERMS": V0_CREATE_TERMS}


def v0_has_any(text, terms):
    hits = [w for w in terms if w in text]
    return hits


def classify_v0(frag):
    low = " " + frag.lower() + " "
    ai = v0_has_any(low, V0_AI_TERMS)
    occ = v0_has_any(low, V0_OCC_TERMS)
    dis = v0_has_any(low, V0_DISPLACE_TERMS)
    cre = v0_has_any(low, V0_CREATE_TERMS)
    relevant = bool(ai) and bool(occ) and (bool(dis) or bool(cre))
    if not relevant:
        valence = "none"
    elif len(dis) > len(cre):
        valence = "minus"
    elif len(cre) > len(dis):
        valence = "plus"
    else:
        valence = "mixed"
    return ai, occ, dis, cre, relevant, valence


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha(data):
    """The id git gives a file with these bytes (`git hash-object`)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git(*args):
    """Run git in this folder; None when git or the history is unavailable."""
    try:
        r = subprocess.run(["git", "-C", HERE] + list(args), capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def protocol_info():
    """Version, date and hashes of PROTOCOL_WS1.0.md as it is on disk now."""
    out = {"file": os.path.basename(PROTOCOL_FILE), "version": None, "date": None,
           "sha256": None, "git_blob": None, "matches_git_HEAD": None}
    if not os.path.exists(PROTOCOL_FILE):
        return out
    with open(PROTOCOL_FILE, "rb") as fh:
        data = fh.read()
    m = re.search(r"\*\*Version\s+([0-9][0-9.]*)\s*·\s*(\d{4}-\d{2}-\d{2})\.?\*\*", data.decode("utf-8"))
    head = git("rev-parse", "HEAD:" + PROTOCOL_GIT_PATH)
    out.update(version=m.group(1) if m else None, date=m.group(2) if m else None,
               sha256=hashlib.sha256(data).hexdigest(), git_blob=git_blob_sha(data),
               matches_git_HEAD=None if head is None else head.decode().strip() == git_blob_sha(data))
    return out


def protocol_label(p):
    if p["version"] is None:
        return f"{p['file']} (version line not found)"
    return f"{p['file']} v{p['version']} ({p['date']})"


def percentile(sorted_vals, p):
    """Linear-interpolation percentile (numpy's default) of a sorted list."""
    if not sorted_vals:
        return None
    h = (len(sorted_vals) - 1) * p / 100.0
    lo = int(math.floor(h))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (h - lo) * (sorted_vals[hi] - sorted_vals[lo])


def norm_ws(s):
    return " ".join((s or "").split())


def read_csv_rows(path):
    """Rows of a CSV as dicts with stripped header names; tolerates a BOM."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = [(h or "").strip() for h in (reader.fieldnames or [])]
        rows = [{(k or "").strip(): (v if isinstance(v, str) else "")
                 for k, v in r.items() if k is not None} for r in reader]
    return header, rows


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def load_reference(path=None):
    """The fragment universe: coding_sample.csv, else the copy inside
    ws1_survey.html (same loader as make_artifact_page.py)."""
    from make_artifact_page import load_fragments
    if path:
        if not os.path.exists(path):
            raise DataError(f"--fragments: {path} not found")
        frags, src = (load_fragments("", path) if path.lower().endswith(".html")
                      else load_fragments(path, ""))
    else:
        frags, src = load_fragments(os.path.join(HERE, "coding_sample.csv"),
                                    os.path.join(HERE, "ws1_survey.html"))
    ids = [f["id"] for f in frags]
    dup = sorted(k for k, v in Counter(ids).items() if v > 1)
    if dup:
        raise DataError(f"reference fragments {src}: duplicate frag_id(s) {dup[:10]}")
    return {f["id"]: f["text"] for f in frags}, src


def label_rows(path, who, rows, rel_col, val_col):
    """{frag_id: raw labels} from CSV rows; a duplicate frag_id stops the run.
    Returns (labels, number of non-empty rows without a frag_id)."""
    labels, seen, blank = {}, Counter(), 0
    for r in rows:
        fid = r.get("frag_id", "").strip()
        if not fid:
            blank += any(v.strip() for v in r.values())
            continue
        seen[fid] += 1
        labels[fid] = {"rel": r.get(rel_col, ""), "val": r.get(val_col, ""),
                       "time": r.get("time_seconds", ""), "text": r.get("text", "")}
    dups = {k: v for k, v in seen.items() if v > 1}
    if dups:
        shown = ", ".join(f"{k} x{v}" for k, v in sorted(dups.items())[:10])
        raise DataError(f"{path} ({who}): {len(dups)} duplicate frag_id(s): {shown}"
                        f"{' ...' if len(dups) > 10 else ''}. Which answer is the coder's is "
                        "undecidable; fix the file by hand (keep the original) and rerun.")
    return labels, blank


def read_coder_file(path):
    """One per-coder CSV (page, Google Forms or ws1_survey.html format)."""
    header, rows = read_csv_rows(path)
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        raise DataError(f"{path}: missing column(s) {missing}; header is {header}")
    if all(m in header for m in PAGE_MARKERS):
        fmt = "page"
    elif set(header) <= {"frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none"}:
        fmt = "4-column (Google Forms / ws1_survey.html)"
    else:
        fmt = "other columns: " + ",".join(h for h in header if h not in REQUIRED)
    stem = os.path.splitext(os.path.basename(path))[0]
    coder, identity_from = stem, "file stem"
    if "coder" in header:
        names = sorted({r.get("coder", "").strip() for r in rows} - {""})
        if len(names) > 1:
            raise DataError(f"{path}: several coder names in one file: {names}")
        if names:
            coder, identity_from = names[0], "coder column"
    session, conflicts = {}, {}
    for f in SESSION_FIELDS:
        if f in header:
            vals = sorted({r.get(f, "").strip() for r in rows} - {""})
            if len(vals) == 1:
                session[f] = vals[0]
            elif vals:
                conflicts[f] = vals
    labels, blank = label_rows(path, f"coder {coder!r}", rows, "human_relevant_0_1",
                               "human_valence_minus_plus_none")
    return {"file": path, "stem": stem, "coder": coder, "identity_from": identity_from,
            "format": fmt, "sha256": sha256_file(path), "session": session,
            "session_conflicts": conflicts, "rows": labels, "blank_id_rows": blank,
            "n_rows": len(labels)}


def read_meta(path):
    header, rows = read_csv_rows(path)
    if "coder" not in header:
        raise DataError(f"--meta {path}: needs a 'coder' column; header is {header}")
    meta = {}
    for r in rows:
        name = r.get("coder", "").strip()
        if not name:
            continue
        if name in meta:
            raise DataError(f"--meta {path}: coder {name!r} appears twice")
        meta[name] = {f: r.get(f, "").strip() for f in META_FIELDS if r.get(f, "").strip()}
    return meta


def derive_labels(raw_rel, raw_val):
    """Codebook v1 labels for one row -> (rel, val_all, val_cond, issue).
    rel: '0'/'1'/None; val_all: valence with `none` for non-relevant (None if
    missing); val_cond: valence only when rel == '1'."""
    r, v = raw_rel.strip(), raw_val.strip().lower()
    rel = r if r in REL_CATS else None
    if rel == "0":
        # codebook: "If relevance = 0, write none" -> any other valence is overridden
        return rel, "none", None, ("valence_on_not_relevant" if v and v != "none" else None)
    if rel == "1":
        if v in VAL_CATS:
            return rel, v, v, None
        return rel, None, None, ("valence_out_of_codebook" if v else "valence_missing")
    if r:
        return None, None, None, "relevance_out_of_codebook"
    return None, None, None, ("valence_without_relevance" if v else None)


def norm_choice(v, allowed):
    v = (v or "").strip().lower()
    return v if v in allowed else None


def norm_int(v):
    try:
        return int((v or "").strip())
    except ValueError:
        return None


def merge_metadata(cf, meta_row):
    """Session metadata: the file's own trace first, --meta fills gaps."""
    out, notes = {}, []
    for f in ("source", "english_level", "practice_correct", "practice_n", "ui_language",
              "codebook_version", "order_seed", "session_start", "session_end"):
        fv = cf["session"].get(f)
        mv = meta_row.get(f) if f in META_FIELDS else None
        if fv is not None:
            raw, origin = fv, "file"
            if mv is not None and mv.strip().lower() != fv.strip().lower():
                notes.append(f"{f}: file says {fv!r}, --meta says {mv!r}; file value used")
        elif mv is not None:
            raw, origin = mv, "--meta"
        elif f in cf["session_conflicts"]:
            raw, origin = None, f"conflicting values in file {cf['session_conflicts'][f]}"
        else:
            raw, origin = None, "not recorded"
        if raw is None:
            val = None
        elif f == "source":
            val = norm_choice(raw, SOURCES)
        elif f == "english_level":
            val = norm_choice(raw, ENGLISH_LEVELS)
        elif f in ("practice_correct", "practice_n"):
            val = norm_int(raw)
        else:
            val = raw.strip()
        if raw is not None and val is None:
            origin = f"invalid value {raw!r} ({origin})"
        out[f] = {"value": val, "from": origin}
    return out, notes


def build_coder(cf, meta_row, ref_text, ids):
    """Analysis-ready coder: labels aligned to the sorted reference ids."""
    md, notes = merge_metadata(cf, meta_row)
    issues = {k: [] for k in ("unknown_ids", "relevance_out_of_codebook", "valence_out_of_codebook",
                              "valence_missing", "valence_on_not_relevant",
                              "valence_without_relevance", "text_mismatch", "bad_time")}
    by_id = {}
    for fid, row in cf["rows"].items():
        if fid not in ref_text:
            issues["unknown_ids"].append(fid)
            continue
        rel, val_all, val_cond, issue = derive_labels(row["rel"], row["val"])
        if issue:
            issues[issue].append(f"{fid}: rel={row['rel']!r} val={row['val']!r}")
        t = None
        if row["time"].strip():
            try:
                t = float(row["time"])
                if not math.isfinite(t) or t < 0:
                    raise ValueError
            except ValueError:
                t = None
                issues["bad_time"].append(f"{fid}: {row['time']!r}")
        if row["text"].strip() and norm_ws(row["text"]) != norm_ws(ref_text[fid]):
            issues["text_mismatch"].append(fid)
        by_id[fid] = (rel, val_all, val_cond, t)
    empty = (None, None, None, None)
    cols = list(zip(*[by_id.get(fid, empty) for fid in ids]))
    rel, val_all, val_cond, times = (list(c) for c in cols)
    completed = sum(1 for r, v in zip(rel, val_all) if r is not None and v is not None)
    return {"name": cf["coder"], "file": cf["file"], "format": cf["format"], "sha256": cf["sha256"],
            "identity_from": cf["identity_from"], "n_rows": cf["n_rows"],
            "blank_id_rows": cf["blank_id_rows"], "metadata": md, "metadata_notes": notes,
            "rel": rel, "val_all": val_all, "val_cond": val_cond, "times": times,
            "completed": completed, "missing": sum(1 for fid in ids if fid not in by_id),
            "issues": issues}


# ---------------------------------------------------------------------------
# section 5: inclusion rules
# ---------------------------------------------------------------------------
def inclusion_rules(c, n_ref):
    md = c["metadata"]
    rules = {}
    e = md["english_level"]
    if e["value"] is None:
        rules["a"] = (NA, f"english_level {e['from']}")
    elif e["value"] in ENGLISH_OK:
        rules["a"] = (PASS, e["value"])
    else:
        rules["a"] = (FAIL, f"english_level = {e['value']}")
    pc, pn = md["practice_correct"], md["practice_n"]
    if pc["value"] is None or pn["value"] is None:
        miss = [f"{k} {d['from']}" for k, d in (("practice_correct", pc), ("practice_n", pn))
                if d["value"] is None]
        rules["b"] = (NA, "; ".join(miss))
    elif not (0 <= pc["value"] <= pn["value"] <= PRACTICE_ITEMS):
        rules["b"] = (NA, f"impossible practice score {pc['value']} correct of {pn['value']} "
                          f"(expected 0 <= correct <= items <= {PRACTICE_ITEMS})")
    else:
        note = (f" (only {pn['value']} of {PRACTICE_ITEMS} practice items recorded; "
                "unrecorded items count as not correct)" if pn["value"] < PRACTICE_ITEMS else "")
        ok = pc["value"] >= PRACTICE_MIN
        rules["b"] = (PASS if ok else FAIL,
                      f"{pc['value']} of {PRACTICE_ITEMS} correct on first attempt{note}")
    if c["completed"] == n_ref:
        rules["c"] = (PASS, f"{c['completed']} of {n_ref}")
    else:
        bad = n_ref - c["missing"] - c["completed"]
        rules["c"] = (FAIL, f"{c['completed']} of {n_ref} completed ({c['missing']} missing, "
                            f"{bad} with an invalid or missing label)")
    times = sorted(t for t in c["times"] if t is not None)
    if not times:
        rules["d"] = (NA, "per-fragment time not recorded"
                          + ("" if c["format"] == "page" else f" (format: {c['format']})"))
    else:
        med = statistics.median(times)
        part = "" if len(times) == n_ref else f" (over the {len(times)} timed fragments)"
        rules["d"] = (PASS if med >= MIN_MEDIAN_SECONDS else FAIL, f"median {med:g} s{part}")
    eligible = all(s == PASS for s, _ in rules.values())
    reasons = [f"({k}) {'FAILED' if s == FAIL else 'NOT ASSESSABLE'}: {d}"
               for k, (s, d) in sorted(rules.items()) if s != PASS]
    return rules, eligible, reasons


def timing_stats(times):
    t = sorted(x for x in times if x is not None)
    if not t:
        return None
    fast = sum(1 for x in t if x < FAST_SECONDS)
    return {"n": len(t), "median": statistics.median(t), "q1": percentile(t, 25),
            "q3": percentile(t, 75), "min": t[0], "max": t[-1], "under_3s": fast,
            "share_under_3s": fast / len(t), "total_minutes": sum(t) / 60.0}


# ---------------------------------------------------------------------------
# agreement statistics
# ---------------------------------------------------------------------------
def kappa_parts(pairs):
    """Integer counts behind Cohen's kappa: (n, agreements, sum_k ca[k]*cb[k])."""
    ca, cb, agree = Counter(), Counter(), 0
    for a, b in pairs:
        ca[a] += 1
        cb[b] += 1
        agree += a == b
    return len(pairs), agree, sum(ca[k] * cb[k] for k in ca)


def kappa_counts(pairs):
    """Cohen's kappa of (a, b) label pairs; categories = union of observed
    labels (as sklearn). Returns (kappa, n, po, pe); kappa is None when
    undefined (no pairs, or chance agreement pe = 1). kappa = (n*agree - S) /
    (n^2 - S) in integers, then one correctly rounded division, so a kappa
    that is exactly 7/10 comes out as 0.7."""
    n, agree, s = kappa_parts(pairs)
    if n == 0:
        return None, 0, None, None
    po, pe = agree / n, s / (n * n)
    if s == n * n:
        return None, n, po, pe
    return (n * agree - s) / (n * n - s), n, po, pe


def kappa_exact(pairs):
    """Cohen's kappa as an exact Fraction (None when undefined); used for the gate."""
    n, agree, s = kappa_parts(pairs)
    return None if n == 0 or s == n * n else Fraction(n * agree - s, n * n - s)


def fraction_str(x):
    return None if x is None else f"{x.numerator}/{x.denominator}"


def vs_gate(x):
    """x (a Fraction) with as many decimals (3 to 12) as it takes to show on
    which side of 0.70 it lies; e.g. 0.69996 prints as 0.69996, not 0.700."""
    if x == GATE_EXACT:
        return "0.700 (exactly 7/10)"
    for d in range(3, 13):
        r = round(x, d)
        if r != GATE_EXACT and (r >= GATE_EXACT) == (x >= GATE_EXACT):
            return f"{float(r):.{d}f}"
    return f"{float(x):.12f} ({'above' if x > GATE_EXACT else 'below'} 0.70 by {abs(float(x - GATE_EXACT)):.1e})"


def alpha_nominal(units):
    """Krippendorff's alpha, nominal metric. units: one Counter of values per
    unit (missing values simply absent). Units with < 2 values are not
    pairable and drop out. Returns (alpha|None, pairable_units, n_values)."""
    n, nc, do, nu = 0, Counter(), 0.0, 0
    for cnt in units:
        m = sum(cnt.values())
        if m < 2:
            continue
        nu += 1
        n += m
        nc.update(cnt)
        do += (m * m - sum(v * v for v in cnt.values())) / (m - 1)
    denom = n * n - sum(v * v for v in nc.values())
    if n <= 1 or denom == 0:
        return None, nu, n
    return 1.0 - (n - 1) * do / denom, nu, n


class Bootstrap:
    """Percentile bootstrap over fragments. One set of resamples (seeded) is
    drawn up front and reused by every statistic, so means of pairwise kappas
    are bootstrapped jointly."""

    def __init__(self, n, n_boot, seed):
        rng = random.Random(seed)
        self.all = list(range(n))
        self.samples = [[rng.randrange(n) for _ in range(n)] for _ in range(n_boot)]

    def run(self, stat):
        value, info = stat(self.all)
        reps = [stat(s)[0] for s in self.samples]
        return value, info, reps


def summarise(value, info, reps):
    ok = sorted(x for x in reps if x is not None)
    out = {"value": value}
    out.update(info)
    out["ci95"] = ([percentile(ok, 2.5), percentile(ok, 97.5)]
                   if value is not None and ok else None)
    out["boot_resamples"] = len(reps)
    out["boot_undefined"] = len(reps) - len(ok)
    return out


def kappa_stat(P):
    def stat(idx):
        k, n, po, pe = kappa_counts([P[i] for i in idx if P[i] is not None])
        return k, {"n": n, "po": po, "pe": pe}
    return stat


def alpha_stat(U):
    def stat(idx):
        a, nu, nv = alpha_nominal([U[i] for i in idx])
        return a, {"n": nu, "n_values": nv}
    return stat


def confusion(P, cats):
    """rows = first label, cols = second label (over all fragments)."""
    m = {r: {c: 0 for c in cats} for r in cats}
    other = Counter()
    for p in P:
        if p is None:
            continue
        if p[0] in m and p[1] in m[p[0]]:
            m[p[0]][p[1]] += 1
        else:
            other[f"{p[0]}|{p[1]}"] += 1
    return {"rows": list(cats), "matrix": m, "other": dict(other)}


class Engine:
    def __init__(self, coders, ids, n_boot, seed):
        self.c = coders
        self.ids = ids
        self.boot = Bootstrap(len(ids), n_boot, seed)
        self.cache = {}

    def pair_units(self, a, b, dim):
        A, B = self.c[a], self.c[b]
        key = DIM_KEY[dim]
        return [(x, y) if x is not None and y is not None else None
                for x, y in zip(A[key], B[key])]

    def kappa(self, a, b, dim):
        """Pairwise kappa with CI (cached; stored with a < b)."""
        a, b = sorted((a, b))
        key = ("kappa", a, b, dim)
        if key not in self.cache:
            P = self.pair_units(a, b, dim)
            v, info, reps = self.boot.run(kappa_stat(P))
            info["value_exact"] = fraction_str(kappa_exact([p for p in P if p is not None]))
            cats = REL_CATS if dim == "relevance" else VAL_CATS
            info["confusion"] = confusion(P, cats)
            info["a"], info["b"] = a, b
            self.cache[key] = (v, info, reps)
        return self.cache[key]

    def kappa_summary(self, a, b, dim):
        return summarise(*self.kappa(a, b, dim))

    def mean_kappa(self, pairs, dim):
        """Mean pairwise kappa; undefined if any pair's kappa is undefined. The
        point estimate is the exact mean of the exact pair kappas
        ('value_exact', a fraction string; 'value' is its float), which is what
        the gate compares; bootstrap replicates are plain float means."""
        runs = [self.kappa(a, b, dim) for a, b in pairs]
        if not runs:
            return None
        def mean(vals):
            return None if any(v is None for v in vals) else sum(vals) / len(vals)
        exact = [r[1]["value_exact"] for r in runs]
        value_exact = None if None in exact else sum(Fraction(e) for e in exact) / len(exact)
        reps = [mean([r[2][i] for r in runs]) for i in range(len(self.boot.samples))]
        info = {"n": [r[1]["n"] for r in runs], "pairs": [list(p) for p in pairs],
                "value_exact": fraction_str(value_exact)}
        return summarise(None if value_exact is None else float(value_exact), info, reps)

    def alpha(self, names, dim):
        key = DIM_KEY[dim]
        U = [Counter(self.c[nm][key][i] for nm in names if self.c[nm][key][i] is not None)
             for i in range(len(self.ids))]
        out = summarise(*self.boot.run(alpha_stat(U)))
        out["coders"] = list(names)
        return out

    def versus(self, labels_x, labels_y, cats):
        """kappa of two aligned label lists (e.g. gold vs a machine channel)."""
        P = [(x, y) if x is not None and y is not None else None for x, y in zip(labels_x, labels_y)]
        out = summarise(*self.boot.run(kappa_stat(P)))
        out["confusion"] = confusion(P, cats)
        return out


# ---------------------------------------------------------------------------
# section 8: adjudication
# ---------------------------------------------------------------------------
def adjudicate(votes, pi_label, pi_missing="PI label absent"):
    """Plurality among the voters' labels; a tie for the top count is broken
    by the PI's label if it is one of the tied labels, else unresolved
    (pi_missing says why there is no PI label). Returns (gold|None, status,
    absolute_majority)."""
    counts = Counter(v for v in votes if v is not None)
    if not counts:
        return None, "unresolved: no voter gave a label", False
    top = max(counts.values())
    leaders = sorted(k for k, v in counts.items() if v == top)
    total = sum(counts.values())
    if len(leaders) == 1:
        return leaders[0], "majority", top * 2 > total
    if pi_label is None:
        return None, f"unresolved: tie, {pi_missing}", False
    if pi_label in leaders:
        return pi_label, "PI tie-break", False
    return None, "unresolved: tie, PI label not among the tied labels", False


def tally(labels):
    return ";".join(f"{k}:{v}" for k, v in sorted(Counter(x for x in labels if x is not None).items()))


def build_gold(coders, ids, eligible, pi, pi_votes=True, valence_rule="relevant_voters"):
    """Gold labels under one reading of section 8 (see ADJ_READINGS).
    Relevance: plurality of the voters, ties broken by the PI's label. Gold
    relevance 0 -> valence `none` (codebook); gold relevance 1 -> valence
    voted among the voters who marked the fragment relevant
    (valence_rule 'relevant_voters') or over all voters' all-fragments labels
    ('all_labels'). Also marks where the PI's label decided the gold: the gold
    differs from what the eligible non-PI coders give on their own (their
    plurality, unresolved when tied), i.e. the PI's vote was pivotal or the
    PI broke a tie. Returns (rows, summary)."""
    voters = [v for v in eligible if pi_votes or v != pi]
    nonpi = [v for v in eligible if v != pi]
    vkey = "val_cond" if valence_rule == "relevant_voters" else "val_all"
    rows, counts = [], Counter()
    for i, fid in enumerate(ids):
        pr = coders[pi]["rel"][i] if pi else None
        pv = coders[pi][vkey][i] if pi else None
        if pi is None:
            why_r = why_v = "PI did not code"
        else:
            why_r = "PI label missing"
            why_v = ("PI did not mark it relevant" if valence_rule == "relevant_voters" and pr != "1"
                     else "PI valence missing")
        rv = [coders[v]["rel"][i] for v in voters]
        vv = [coders[v][vkey][i] for v in voters]
        g_rel, s_rel, abs_rel = adjudicate(rv, pr, why_r)
        g_val, s_val, abs_val = None, "unresolved: relevance unresolved", False
        if g_rel == "0":
            g_val, s_val = "none", "rule: gold relevance 0 -> none"
        elif g_rel == "1":
            g_val, s_val, abs_val = adjudicate(vv, pv, why_v)
        own_rel = adjudicate([coders[v]["rel"][i] for v in nonpi], None)[0]
        own_val = adjudicate([coders[v][vkey][i] for v in nonpi], None)[0]
        pi_rel = g_rel is not None and g_rel != own_rel
        pi_val = g_rel == "1" and g_val is not None and g_val != own_val
        backers = voters + ([pi] if s_val == "PI tie-break" else [])
        unsupported = (g_rel == "1" and g_val == "none" and not any(
            coders[v]["rel"][i] == "1" and coders[v]["val_all"][i] == "none" for v in backers))
        counts["rel:" + s_rel] += 1
        counts["val:" + s_val] += 1
        counts["rel_plurality_without_absolute_majority"] += (s_rel == "majority" and not abs_rel)
        counts["val_plurality_without_absolute_majority"] += (s_val == "majority" and not abs_val)
        counts["pi_decided_relevance"] += pi_rel
        counts["pi_decided_valence"] += pi_val
        counts["pi_decided_any"] += pi_rel or pi_val
        counts["relevant_none_without_support"] += unsupported
        rows.append({"frag_id": fid, "gold_relevant": g_rel, "gold_valence": g_val,
                     "relevance_status": s_rel, "valence_status": s_val,
                     "n_voters": sum(1 for v in rv if v is not None),
                     "votes_relevance": tally(rv), "votes_valence": tally(vv),
                     "pi_relevant": pr, "pi_valence": coders[pi]["val_all"][i] if pi else None,
                     "pi_decided_relevance": "yes" if pi_rel else "no",
                     "pi_decided_valence": "yes" if pi_val else "no"})
    summary = {
        "voters": voters, "pi_votes": pi_votes, "valence_rule": valence_rule,
        "pi_tiebreaks_relevance": counts["rel:PI tie-break"],
        "pi_tiebreaks_valence": counts["val:PI tie-break"],
        "fragments_with_any_pi_tiebreak": sum(1 for g in rows if "PI tie-break" in
                                              (g["relevance_status"], g["valence_status"])),
        "pi_decided_relevance": counts["pi_decided_relevance"],
        "pi_decided_valence": counts["pi_decided_valence"],
        "fragments_pi_decided": counts["pi_decided_any"],
        "unresolved_relevance": sum(1 for g in rows if g["gold_relevant"] is None),
        "unresolved_valence": sum(1 for g in rows if g["gold_valence"] is None),
        "gold_relevant_counts": dict(Counter(g["gold_relevant"] for g in rows if g["gold_relevant"])),
        "gold_valence_counts": dict(Counter(g["gold_valence"] for g in rows if g["gold_valence"])),
        "relevant_none_without_support": counts["relevant_none_without_support"],
        "plurality_without_absolute_majority": {
            "relevance": counts["rel_plurality_without_absolute_majority"],
            "valence": counts["val_plurality_without_absolute_majority"]},
        "status_counts": {k: v for k, v in sorted(counts.items()) if k.startswith(("rel:", "val:"))}}
    return rows, summary


# ---------------------------------------------------------------------------
# machine channels
# ---------------------------------------------------------------------------
def v0_git_check(texts):
    """Compare the embedded v0 copy with git history (fails loudly on mismatch)."""
    src = git("show", f"{V0_COMMIT}:{V0_PATH}")
    if src is None:
        return {"status": "not checked", "detail": "git history not available here; the "
                "embedded copy was verified when written (see tests/test_reliability.py)"}
    blob = git_blob_sha(src)
    ns = {"__name__": "ws1_pipeline_v0_from_git"}
    exec(compile(src, f"{V0_COMMIT[:7]}:{V0_PATH}", "exec"), ns)
    lists_ok = all(ns[k] == v for k, v in V0_LISTS.items())
    out_ok = all(tuple(ns["classify"](t)) == tuple(classify_v0(t)) for t in texts)
    if blob != V0_BLOB or not lists_ok or not out_ok:
        raise DataError(f"embedded dictionary v0 differs from git {V0_COMMIT[:7]}:{V0_PATH} "
                        f"(blob {blob}, lists equal {lists_ok}, outputs equal {out_ok})")
    return {"status": "identical", "detail": f"blob {blob}; term lists and classify() output on "
            f"all {len(texts)} fragments identical to git {V0_COMMIT[:7]}:{V0_PATH}"}


def dictionary_labels(ids, ref_text):
    """{channel: (rel list, val list)} for dictionary v0 and v1, plus provenance."""
    import ws1_pipeline
    with open(os.path.join(HERE, "ws1_pipeline.py"), "rb") as fh:
        blob = git_blob_sha(fh.read())
    head = git("rev-parse", "HEAD:" + V0_PATH)        # same path, current commit
    v1_prov = {"source": "classify() imported from ws1_pipeline.py (working tree)", "blob": blob,
               "matches_git_HEAD": None if head is None else head.decode().strip() == blob,
               "matches_protocol_12_1": blob == V1_FROZEN_BLOB}
    texts = [ref_text[f] for f in ids]
    v0_prov = {"source": f"embedded verbatim copy of {V0_COMMIT[:7]}:{V0_PATH} (7eb5a1e^, "
               "before the stance fix 7eb5a1e)", "commit": V0_COMMIT, "blob": V0_BLOB,
               "git_check": v0_git_check(texts)}
    out = {}
    for name, fn, prov in (("dictionary_v0", classify_v0, v0_prov),
                           ("dictionary_v1", ws1_pipeline.classify, v1_prov)):
        res = [fn(t) for t in texts]
        rel = ["1" if r[-2] else "0" for r in res]
        val = [r[-1] for r in res]
        prov = dict(prov, n_relevant=rel.count("1"), n_fragments=len(rel),
                    valence_counts=dict(Counter(val)))
        out[name] = (rel, val, prov)
    return out


def channel_labels(spec, ids, ref_text):
    if "=" not in spec:
        raise DataError(f"--channel {spec!r}: use NAME=path.csv")
    name, path = spec.split("=", 1)
    name = name.strip()
    # the name becomes gold_labels.csv columns <name>_relevant/_valence
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or name in ("dictionary_v0", "dictionary_v1", "gold", "pi"):
        raise DataError(f"--channel: invalid or reserved name {name!r} (letters, digits, _; "
                        "not dictionary_v0/dictionary_v1/gold/pi)")
    if not os.path.exists(path):
        raise DataError(f"--channel {name}: {path} not found")
    header, rows = read_csv_rows(path)
    status = None
    if all(c in header for c in LLM_COLS) and not all(c in header for c in REQUIRED):
        # llm_labels.csv as written by ws1_llm_channel.py (PROTOCOL section 12.2);
        # refused or invalid fragments have empty labels and stay missing
        labels, blank = label_rows(path, f"channel {name!r}", rows, "relevant_llm", "valence_llm")
        cf = {"file": path, "coder": name, "identity_from": "--channel", "sha256": sha256_file(path),
              "format": "llm_labels.csv (PROTOCOL section 12.2)", "session": {}, "session_conflicts": {},
              "rows": labels, "blank_id_rows": blank, "n_rows": len(labels)}
        status = dict(Counter(r.get("status_llm", "").strip() or "(blank)" for r in rows
                              if r.get("frag_id", "").strip()))
    else:
        cf = read_coder_file(path)
    c = build_coder(cf, {}, ref_text, ids)
    prov = {"source": path, "format": cf["format"], "sha256": cf["sha256"], "n_labelled": c["completed"],
            "unknown_ids": len(c["issues"]["unknown_ids"]),
            "issues": {k: len(v) for k, v in c["issues"].items() if v}}
    if status is not None:
        prov["status_llm_counts"] = status
    return name, (c["rel"], c["val_all"], prov)


# ---------------------------------------------------------------------------
# the analysis
# ---------------------------------------------------------------------------
def resolve_pi(names, pi_arg):
    if pi_arg in names:
        return pi_arg
    hits = [n for n in names if n.strip().casefold() == pi_arg.strip().casefold()]
    if len(hits) > 1:
        raise DataError(f"--pi {pi_arg!r} matches several coders {hits}")
    return hits[0] if hits else None


def analyse(coder_files, pi_arg, meta=None, n_boot=BOOT_PROTOCOL, seed=2026,
            fragments=None, channels=(), pi_did_not_code=False):
    """Run sections 5-9. coder_files: paths. pi_arg: the PI's coder identity,
    which must match an input coder; or pi_arg=None with pi_did_not_code=True.
    Returns the results dict (JSON-ready) with 'gold_rows' and
    'exclusion_rows' for the CSVs."""
    if pi_did_not_code and pi_arg:
        raise DataError("--pi and --pi-did-not-code contradict each other; give one")
    if not pi_did_not_code and not (pi_arg or "").strip():
        raise DataError("name the PI's coder identity with --pi, or declare --pi-did-not-code")
    ref_text, ref_src = load_reference(fragments)
    ids = sorted(ref_text)
    n_ref = len(ids)
    meta = meta or {}
    warnings = []
    proto = protocol_info()
    if proto["version"] not in PROTOCOL_KNOWN:
        warnings.append(f"{protocol_label(proto)}: this script implements sections 5-9 as worded in "
                        f"versions {', '.join(PROTOCOL_KNOWN)}; check them against this version")
    if n_ref != N_PROTOCOL:
        warnings.append(f"reference has {n_ref} fragments, the protocol specifies {N_PROTOCOL}; "
                        f"rule (c) uses {n_ref}")
    if n_boot != BOOT_PROTOCOL:
        warnings.append(f"--boot {n_boot}: the protocol (section 6) specifies {BOOT_PROTOCOL} resamples")

    files = [read_coder_file(p) for p in coder_files]
    by_name = {}
    for cf in files:
        if cf["coder"] in by_name:
            raise DataError(f"coder {cf['coder']!r} appears in two files: "
                            f"{by_name[cf['coder']]['file']} and {cf['file']}")
        by_name[cf["coder"]] = cf
    for m in sorted(set(meta) - set(by_name)):
        warnings.append(f"--meta row for {m!r} matches no input coder (identity must equal the "
                        "coder column, or the file stem when there is none)")
    coders = {nm: build_coder(cf, meta.get(nm, {}), ref_text, ids) for nm, cf in by_name.items()}
    names = sorted(coders)
    if pi_did_not_code:
        pi = None
        warnings.append("declared with --pi-did-not-code: no PI file is among the inputs, so every "
                        "coder can enter the primary pairs, no PI tie-breaks are possible and no PI "
                        "comparisons are made")
    else:
        pi = resolve_pi(names, pi_arg)
        if pi is None:
            raise DataError(f"--pi {pi_arg!r} matches none of the input coders {names}. The PI's "
                            "coding must never enter the primary kappa (protocol section 6), so the "
                            "run stops. Give the PI's identity as it appears in the inputs (the coder "
                            "column, else the file stem), or --pi-did-not-code if the PI did not code.")

    # ---- section 5 ----
    for nm in names:
        c = coders[nm]
        c["rules"], c["eligible"], c["reasons"] = inclusion_rules(c, n_ref)
        c["timing"] = timing_stats(c["times"])
        c["is_pi"] = nm == pi
        cb = c["metadata"]["codebook_version"]["value"]
        if cb is not None and cb != CODEBOOK:
            warnings.append(f"{nm}: coded with codebook_version {cb!r}, not {CODEBOOK}")
        for note in c["metadata_notes"]:
            warnings.append(f"{nm}: {note}")
        if c["issues"]["unknown_ids"]:
            warnings.append(f"{nm}: {len(c['issues']['unknown_ids'])} frag_id(s) not in the reference "
                            f"set were ignored, e.g. {c['issues']['unknown_ids'][:3]}")
        if c["issues"]["text_mismatch"]:
            warnings.append(f"{nm}: fragment text differs from the reference for "
                            f"{len(c['issues']['text_mismatch'])} fragment(s), e.g. "
                            f"{c['issues']['text_mismatch'][:3]} (different instrument build?)")
    eligible = [nm for nm in names if coders[nm]["eligible"]]

    # ---- section 6: primary pairs ----
    elig_nonpi = [nm for nm in eligible if nm != pi]
    public = [nm for nm in elig_nonpi if coders[nm]["metadata"]["source"]["value"] == "public"]
    if len(public) >= 2:
        group, basis = public, "two or more publicly recruited coders are eligible: all pairs among them"
    else:
        group = elig_nonpi
        basis = (f"{len(public)} publicly recruited coder(s) eligible (< 2): "
                 "all pairs among eligible non-PI coders")
    unknown_src = [nm for nm in elig_nonpi if coders[nm]["metadata"]["source"]["value"] is None]
    if unknown_src:
        warnings.append(f"eligible non-PI coder(s) without a recorded recruitment source {unknown_src}: "
                        "they cannot be counted as publicly recruited, which can change the primary pair set")
    pairs = list(combinations(sorted(group), 2))
    eng = Engine(coders, ids, n_boot, seed)
    primary = {"basis": basis, "group": sorted(group), "pairs": [], "mean": {}, "gate": {}}
    for a, b in pairs:
        primary["pairs"].append({"a": a, "b": b, **{d: eng.kappa_summary(a, b, d) for d in DIMS}})
    for d in DIMS:
        primary["mean"][d] = eng.mean_kappa(pairs, d)
    for d in ("relevance", "valence_conditional"):
        m = primary["mean"][d]
        if m is None:
            primary["gate"][d] = {"pass": None, "why": "no primary pair (fewer than two eligible non-PI coders)"}
        elif m["value_exact"] is None:
            primary["gate"][d] = {"pass": None, "why": "a pairwise kappa is undefined"}
        else:
            x = Fraction(m["value_exact"])
            ok = x >= GATE_EXACT
            primary["gate"][d] = {"pass": ok, "why": f"mean κ {vs_gate(x)} {'≥' if ok else '<'} {GATE:.2f}"}
    decision = decide(primary["gate"])

    # ---- section 7: secondary ----
    secondary = {}
    partial = [nm for nm in names if not coders[nm]["eligible"]
               and coders[nm]["rules"]["c"][0] == FAIL
               and all(coders[nm]["rules"][k][0] == PASS for k in "abd")]
    secondary["alpha"] = {}
    for label, members in (("eligible", eligible), ("eligible_plus_partial", sorted(eligible + partial))):
        secondary["alpha"][label] = ({d: eng.alpha(members, d) for d in DIMS} if len(members) >= 2
                                     else {"not_computed": f"{len(members)} coder(s)", "coders": members})
    secondary["alpha"]["partial_completers"] = partial
    secondary["pi_vs_each"] = ([{"other": nm, "other_eligible": coders[nm]["eligible"],
                                 **{d: eng.kappa_summary(pi, nm, d) for d in DIMS}}
                                for nm in names if nm != pi] if pi else [])
    for field, key in (("source", "by_source"), ("ui_language", "by_ui_language")):
        secondary[key] = by_group(eng, coders, elig_nonpi, field)
    secondary["all_pairs"] = [{"a": a, "b": b, "a_eligible": coders[a]["eligible"],
                               "b_eligible": coders[b]["eligible"],
                               **{d: eng.kappa_summary(a, b, d) for d in DIMS}}
                              for a, b in combinations(names, 2)]

    # ---- section 8: adjudication (first reading = gold of record) ----
    readings = []
    for name, pi_votes, vrule, text in ADJ_READINGS:
        rows, summ = build_gold(coders, ids, eligible, pi, pi_votes, vrule)
        summ.update(name=name, description=text)
        readings.append((rows, summ))
    gold_rows, adjudication = readings[0]
    adjudication.update(pi=pi, pi_eligible=coders[pi]["eligible"] if pi else None, sensitivity={})
    for rows, summ in readings[1:]:
        summ["fragments_relevance_differs"] = sum(g["gold_relevant"] != h["gold_relevant"]
                                                  for g, h in zip(gold_rows, rows))
        summ["fragments_valence_differs"] = sum(g["gold_valence"] != h["gold_valence"]
                                                for g, h in zip(gold_rows, rows))
        adjudication["sensitivity"][summ["name"]] = summ
        for g, h in zip(gold_rows, rows):
            g[f"alt_{summ['name']}_relevant"] = h["gold_relevant"]
            g[f"alt_{summ['name']}_valence"] = h["gold_valence"]
    if len(eligible) < 2:
        warnings.append(f"gold labels rest on {len(eligible)} eligible coder(s)")

    # ---- machine channels vs gold ----
    chans = dictionary_labels(ids, ref_text)
    for spec in channels:
        name, lab = channel_labels(spec, ids, ref_text)
        chans[name] = lab
    g_rel = [g["gold_relevant"] for g in gold_rows]
    g_val = [g["gold_valence"] for g in gold_rows]
    machine = {}
    for name, (m_rel, m_val, prov) in chans.items():
        cond_gold = [gv if gr == "1" and mr == "1" else None for gv, gr, mr in zip(g_val, g_rel, m_rel)]
        machine[name] = {"provenance": prov,
                         "relevance": eng.versus(g_rel, m_rel, REL_CATS),
                         "valence_conditional": eng.versus(cond_gold, m_val, VAL_CATS),
                         "valence_all": eng.versus(g_val, m_val, VAL_CATS)}
        for i, g in enumerate(gold_rows):
            g[f"{name}_relevant"], g[f"{name}_valence"] = m_rel[i], m_val[i]
    if not chans["dictionary_v1"][2]["matches_protocol_12_1"]:
        warnings.append(f"dictionary v1 (ws1_pipeline.py, blob {chans['dictionary_v1'][2]['blob']}) is not "
                        f"the version frozen in PROTOCOL section 12.1 (blob {V1_FROZEN_BLOB})")
    if not channels:
        warnings.append("LLM channel (section 7) not compared: no LLM-channel labels were supplied "
                        "(pass them with --channel LLM=llm_labels.csv)")

    exclusion_rows = []
    for nm in names:
        c = coders[nm]
        md = c["metadata"]
        exclusion_rows.append({
            "coder": nm, "is_pi": "yes" if c["is_pi"] else "no", "file": os.path.basename(c["file"]),
            "format": c["format"], "source": md["source"]["value"] or md["source"]["from"],
            "ui_language": md["ui_language"]["value"] or md["ui_language"]["from"],
            "english_level": md["english_level"]["value"] or md["english_level"]["from"],
            "practice_correct": "" if md["practice_correct"]["value"] is None else md["practice_correct"]["value"],
            "practice_n": "" if md["practice_n"]["value"] is None else md["practice_n"]["value"],
            "completed": c["completed"], "n_reference": n_ref,
            "median_seconds": "" if not c["timing"] else c["timing"]["median"],
            **{f"rule_{k}": c["rules"][k][0] for k, _ in RULES},
            "eligible": "yes" if c["eligible"] else "no",
            "in_primary_pairs": "yes" if nm in group and len(group) >= 2 else "no",
            "reasons": " | ".join(c["reasons"])})

    coder_out = {}
    for nm in names:
        c = coders[nm]
        coder_out[nm] = {k: c[k] for k in ("file", "format", "sha256", "identity_from", "n_rows",
                                           "blank_id_rows", "metadata", "completed", "missing",
                                           "eligible", "reasons", "timing", "is_pi")}
        coder_out[nm]["rules"] = {k: {"status": s, "detail": d} for k, (s, d) in c["rules"].items()}
        coder_out[nm]["issues"] = {k: {"count": len(v), "examples": v[:5]} for k, v in c["issues"].items()}
        coder_out[nm]["n_relevant"] = c["rel"].count("1")
        coder_out[nm]["valence_counts"] = dict(Counter(v for v in c["val_all"] if v))

    return {"meta": {"generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "script": "ws1_reliability.py", "script_sha256": sha256_file(os.path.abspath(__file__)),
                     "git_head": (git("rev-parse", "HEAD") or b"").decode().strip() or None,
                     "protocol": proto, "codebook": CODEBOOK, "gate": GATE,
                     "bootstrap": {"resamples": n_boot, "seed": seed, "method":
                                   "percentile 95% CI; fragments resampled with replacement from the "
                                   "reference set; every statistic recomputed on the same resamples; "
                                   "undefined replicates dropped and counted"},
                     "reference": {"path": ref_src, "n": n_ref, "sha256": sha256_file(ref_src)},
                     "pi_argument": pi_arg, "pi": pi, "pi_did_not_code": bool(pi_did_not_code)},
            "warnings": warnings, "coders": coder_out, "eligible": eligible,
            "primary": primary, "decision": decision, "secondary": secondary,
            "adjudication": adjudication, "machine_channels": machine,
            "gold_rows": gold_rows, "exclusion_rows": exclusion_rows}


def by_group(eng, coders, members, field):
    """Within-group and between-group mean pairwise kappa (eligible non-PI coders)."""
    groups = {}
    for nm in members:
        groups.setdefault(coders[nm]["metadata"][field]["value"] or "not recorded", []).append(nm)
    out = {"groups": {g: sorted(v) for g, v in sorted(groups.items())}, "within": {}, "between": {}}
    for g, v in sorted(groups.items()):
        pairs = list(combinations(sorted(v), 2))
        out["within"][g] = ({d: eng.mean_kappa(pairs, d) for d in DIMS} if pairs
                            else {"not_computed": f"{len(v)} coder(s) in group"})
    for g1, g2 in combinations(sorted(groups), 2):
        pairs = [(a, b) for a in groups[g1] for b in groups[g2]]
        out["between"][f"{g1} x {g2}"] = {d: eng.mean_kappa(pairs, d) for d in DIMS}
    return out


def decide(gate):
    """Section 9."""
    rel, val = gate["relevance"]["pass"], gate["valence_conditional"]["pass"]
    if rel is None or val is None:
        return {"status": "NOT ASSESSABLE", "text":
                "The gate cannot be evaluated (" + "; ".join(
                    f"{d}: {gate[d]['why']}" for d in gate if gate[d]["pass"] is None) +
                "). Section 9 defines only pass and fail; no decision is taken. The protocol needs "
                "at least two eligible non-PI coders (section 6)."}
    if rel and val:
        return {"status": "PASS", "text": "Gate passed: WS1 starts with the codebook (v1) unchanged."}
    failed = [d for d, ok in (("relevance", rel), ("valence", val)) if not ok]
    text = ("Gate failed on " + " and ".join(failed) + ": codebook v2 is written from the "
            "disagreement patterns, deposited on OSF, and the reliability study is repeated with "
            "new or re-trained coders.")
    if failed == ["valence"]:
        text += (" Valence alone failed: if this is the second valence-only failure, the "
                 "pre-specified fallback is a binary alarming/reassuring scheme, declared as a "
                 "deviation (this script does not know the attempt history).")
    return {"status": "FAIL", "failed": failed, "valence_only": failed == ["valence"], "text": text}


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------
def f3(x):
    return "—" if x is None else f"{x:.3f}"


def est(e):
    if e is None:
        return "—"
    if "not_computed" in e:
        return f"not computed ({e['not_computed']})"
    n = e.get("n")
    ns = "/".join(str(x) for x in n) if isinstance(n, list) else str(n)
    if e.get("value") is None:
        return f"undefined (n={ns})"
    ci = e.get("ci95")
    cis = f"[{f3(ci[0])}, {f3(ci[1])}]" if ci else "[CI —]"
    und = f", {e['boot_undefined']} undefined resamples" if e.get("boot_undefined") else ""
    return f"{f3(e['value'])} {cis}, n={ns}{und}"


def confusion_md(cf, row_name, col_name):
    rows = cf["rows"]
    out = [f"| {row_name} \\ {col_name} | " + " | ".join(rows) + " |",
           "|---|" + "---:|" * len(rows)]
    for r in rows:
        out.append(f"| {r} | " + " | ".join(str(cf["matrix"][r][c]) for c in rows) + " |")
    if cf["other"]:
        out.append(f"\nOther label pairs: {cf['other']}")
    return "\n".join(out)


def rule_cell(r):
    return {PASS: "pass", FAIL: "**FAIL**", NA: "*not assessable*"}[r["status"]]


def write_report(res, path):
    L = []
    m = res["meta"]
    L.append("# WS1.0 reliability report\n")
    L.append(f"Generated {m['generated_utc']} by `ws1_reliability.py` · protocol "
             f"{protocol_label(m['protocol'])} · codebook {m['codebook']} · gate κ ≥ {m['gate']:.2f}  ")
    L.append(f"Reference fragments: {m['reference']['n']} (`{os.path.basename(m['reference']['path'])}`) · "
             f"bootstrap: {m['bootstrap']['resamples']} resamples, seed {m['bootstrap']['seed']} · "
             f"PI: {m['pi'] or 'did not code (declared with --pi-did-not-code)'}\n")
    if res["warnings"]:
        L.append("> **Warnings**")
        for w in res["warnings"]:
            L.append(f"> - {w}")
        L.append("")

    d, p = res["decision"], res["primary"]
    L.append("## 1. Decision (protocol §9)\n")
    L.append(f"**Gate: {d['status']}.** {d['text']}\n")
    L.append(f"Primary pairs: {p['basis']}. Group: {', '.join(p['group']) or '—'}.\n")
    L.append("| dimension | mean pairwise κ [95% CI], n per pair | gate ≥ 0.70 |")
    L.append("|---|---|---|")
    for dim in DIMS:
        g = p["gate"].get(dim)
        gs = "—" if g is None else (f"*not assessable* ({g['why']})" if g["pass"] is None
                                    else f"{'pass' if g['pass'] else '**FAIL**'} ({g['why']})")
        tag = "" if dim != "valence_all" else " (reported, not gated)"
        L.append(f"| {DIM_LABEL[dim]}{tag} | {est(p['mean'][dim])} | {gs} |")
    L.append("\nThe gate compares the exact mean of the exact pair κs (rational arithmetic on the "
             "label counts) with 0.70; the gate column prints as many decimals as it takes to show "
             "the side of 0.70, so a mean of 0.69996 is not shown as 0.700.\n")

    L.append("## 2. Coders and inclusion rules (§5)\n")
    L.append("A coder enters the primary analysis only if all four rules hold; *not assessable* "
             "(data not recorded) counts as not holding.\n")
    L.append("| coder | PI | format | source | English | practice (1st try) | completed | "
             "median s (n timed) | < 3 s | (a) | (b) | (c) | (d) | eligible |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for nm, c in res["coders"].items():
        md = c["metadata"]
        pr = (f"{md['practice_correct']['value']}/{md['practice_n']['value']}"
              if md["practice_correct"]["value"] is not None and md["practice_n"]["value"] is not None
              else "not recorded")
        t = c["timing"]
        ts = f"{t['median']:g} ({t['n']})" if t else "not recorded"
        fast = f"{t['share_under_3s']:.1%} ({t['under_3s']}/{t['n']})" if t else "—"
        L.append(f"| {nm} | {'yes' if c['is_pi'] else ''} | {c['format']} | "
                 f"{md['source']['value'] or md['source']['from']} | "
                 f"{md['english_level']['value'] or md['english_level']['from']} | {pr} | "
                 f"{c['completed']}/{m['reference']['n']} | {ts} | {fast} | "
                 + " | ".join(rule_cell(c["rules"][k]) for k, _ in RULES)
                 + f" | {'**yes**' if c['eligible'] else 'no'} |")
    L.append("")
    excl = [(nm, c) for nm, c in res["coders"].items() if not c["eligible"]]
    if excl:
        L.append("Excluded from the primary analysis (data kept for secondary analyses):\n")
        for nm, c in excl:
            L.append(f"- **{nm}**: " + "; ".join(c["reasons"]))
        L.append("")
    L.append("Rules: " + "; ".join(f"({k}) {t}" for k, t in RULES) + ".\n")

    L.append("## 3. Primary analysis (§6)\n")
    if not p["pairs"]:
        L.append("No primary pair: fewer than two eligible non-PI coders.\n")
    else:
        L.append("| pair | " + " | ".join(DIM_LABEL[x] for x in DIMS) + " |")
        L.append("|---|---|---|---|")
        for pr in p["pairs"]:
            L.append(f"| {pr['a']} × {pr['b']} | " + " | ".join(est(pr[x]) for x in DIMS) + " |")
        L.append("| **mean** | " + " | ".join(est(p["mean"][x]) for x in DIMS) + " |\n")
        L.append("Each cell: κ [95% percentile-bootstrap CI], n = fragments in the comparison.\n")
        L.append("### Confusion matrices of the primary pairs (disagreement patterns)\n")
        for pr in p["pairs"]:
            for x in ("relevance", "valence_conditional", "valence_all"):
                L.append(f"**{pr['a']} × {pr['b']}, {DIM_LABEL[x]}** (rows {pr[x]['a']}, columns {pr[x]['b']}; n={pr[x]['n']})\n")
                L.append(confusion_md(pr[x]["confusion"], pr[x]["a"], pr[x]["b"]) + "\n")

    s = res["secondary"]
    L.append("## 4. Secondary analyses (§7)\n")
    L.append("### 4.1 Krippendorff's α (nominal, missing values allowed)\n")
    L.append("| coder set | " + " | ".join(DIM_LABEL[x] for x in DIMS) + " |")
    L.append("|---|---|---|---|")
    for label in ("eligible", "eligible_plus_partial"):
        a = s["alpha"][label]
        members = a.get("coders") if "not_computed" in a else a["relevance"]["coders"]
        title = {"eligible": "all eligible coders", "eligible_plus_partial":
                 "eligible + partial completers"}[label] + f" ({', '.join(members) or '—'})"
        if "not_computed" in a:
            L.append(f"| {title} | not computed ({a['not_computed']}) | | |")
        else:
            L.append(f"| {title} | " + " | ".join(est(a[x]) for x in DIMS) + " |")
    L.append("\nn = pairable fragments. Partial completers = coders who pass rules (a), (b), (d) and "
             f"fail only (c): {', '.join(s['alpha']['partial_completers']) or 'none'}. For valence "
             "(both marked relevant) a coder's valence counts as missing where that coder marked the "
             "fragment not relevant.\n")
    L.append("### 4.2 PI versus each other coder\n")
    if not s["pi_vs_each"]:
        L.append("Not computed: the PI is not among the inputs.\n")
    else:
        L.append("| PI × coder | coder eligible | " + " | ".join(DIM_LABEL[x] for x in DIMS) + " |")
        L.append("|---|---|---|---|---|")
        for r in s["pi_vs_each"]:
            L.append(f"| {m['pi']} × {r['other']} | {'yes' if r['other_eligible'] else 'no'} | "
                     + " | ".join(est(r[x]) for x in DIMS) + " |")
        L.append("")
    for key, title in (("by_source", "4.3 κ by recruitment source"),
                       ("by_ui_language", "4.4 κ by interface language")):
        g = s[key]
        L.append(f"### {title} (eligible non-PI coders; mean pairwise κ)\n")
        L.append("Groups: " + ("; ".join(f"{k}: {', '.join(v)}" for k, v in g["groups"].items()) or "none") + "\n")
        rows = [(f"within {k}", v) for k, v in g["within"].items()] + \
               [(f"between {k}", v) for k, v in g["between"].items()]
        if rows:
            L.append("| comparison | " + " | ".join(DIM_LABEL[x] for x in DIMS) + " |")
            L.append("|---|---|---|---|")
            for lab, v in rows:
                if "not_computed" in v:
                    L.append(f"| {lab} | not computed ({v['not_computed']}) | | |")
                else:
                    L.append(f"| {lab} | " + " | ".join(est(v[x]) for x in DIMS) + " |")
            L.append("")
    L.append("### 4.5 All coder pairs (including excluded coders; pairwise-complete fragments)\n")
    if s["all_pairs"]:
        L.append("| pair | eligible | " + " | ".join(DIM_LABEL[x] for x in DIMS) + " |")
        L.append("|---|---|---|---|---|")
        for r in s["all_pairs"]:
            L.append(f"| {r['a']} × {r['b']} | {'yes' if r['a_eligible'] else 'no'}/{'yes' if r['b_eligible'] else 'no'} | "
                     + " | ".join(est(r[x]) for x in DIMS) + " |")
        L.append("")
    L.append("### 4.6 Timing (seconds per fragment, as recorded by the instrument)\n")
    L.append("| coder | n timed | median | IQR | min–max | share < 3 s | total min |")
    L.append("|---|---|---|---|---|---|---|")
    for nm, c in res["coders"].items():
        t = c["timing"]
        if t:
            L.append(f"| {nm} | {t['n']} | {t['median']:g} | {t['q1']:g}–{t['q3']:g} | {t['min']:g}–{t['max']:g} | "
                     f"{t['share_under_3s']:.1%} | {t['total_minutes']:.1f} |")
        else:
            L.append(f"| {nm} | 0 | not recorded | | | | |")
    L.append("")

    a = res["adjudication"]
    n = m["reference"]["n"]
    L.append("## 5. Adjudication and gold labels (§8)\n")
    L.append(f"Reading used for the gold labels (`{a['name']}`): {a['description']}. Plurality wins; a "
             "tie for the top count is broken by the PI's label when it is one of the tied labels, "
             "otherwise the fragment is unresolved. Gold relevance 0 → valence `none` (codebook). "
             "This is a reading of §8; the table below shows how the gold changes under the other "
             "readings.\n")
    L.append(f"Voters: {', '.join(a['voters']) or 'none'}; PI: "
             + (f"{a['pi']} (eligible: {'yes' if a['pi_eligible'] else 'no'})" if a["pi"] else "did not code")
             + "\n")
    L.append(f"- PI tie-breaks (the §8 count): relevance {a['pi_tiebreaks_relevance']}, valence "
             f"{a['pi_tiebreaks_valence']}; fragments with any PI tie-break: "
             f"{a['fragments_with_any_pi_tiebreak']} of {n}")
    L.append(f"- **Gold labels decided by the PI's label**: relevance {a['pi_decided_relevance']}, valence "
             f"{a['pi_decided_valence']}; fragments: {a['fragments_pi_decided']} of {n}. Decided = the "
             "gold differs from what the eligible non-PI coders give on their own (their plurality, "
             "unresolved when tied), i.e. the PI's vote was pivotal or the PI broke a tie. When the PI "
             "votes and the voters are odd in number, relevance cannot tie, so the tie-break count can "
             "be 0 while the PI decides every fragment on which the other coders split; this line "
             "counts those.")
    L.append(f"- Unresolved: relevance {a['unresolved_relevance']} of {n}, valence {a['unresolved_valence']} of {n}")
    L.append(f"- Gold relevance: {a['gold_relevant_counts']}; gold valence: {a['gold_valence_counts']}")
    L.append(f"- Gold 'relevant, valence `none`' that no voter (nor a tie-breaking PI) labelled "
             f"relevant/`none`: {a['relevant_none_without_support']}")
    L.append(f"- Plurality without absolute majority: relevance "
             f"{a['plurality_without_absolute_majority']['relevance']}, valence "
             f"{a['plurality_without_absolute_majority']['valence']}\n")
    L.append("Sensitivity of the gold labels to the reading of §8 (each alternative's labels are in "
             "`gold_labels.csv` as `alt_<reading>_relevant` / `alt_<reading>_valence`):\n")
    L.append("| reading | gold differs from the first: relevance / valence | unresolved: relevance / "
             "valence | PI tie-breaks: relevance / valence | decided by the PI: relevance / valence | "
             "relevant/`none` without support |")
    L.append("|---|---|---|---|---|---|")
    for r in [a] + list(a["sensitivity"].values()):
        diff = ("— (used for the gold labels)" if r is a else
                f"{r['fragments_relevance_differs']} / {r['fragments_valence_differs']}")
        L.append(f"| `{r['name']}`: {r['description']} | {diff} | {r['unresolved_relevance']} / "
                 f"{r['unresolved_valence']} | {r['pi_tiebreaks_relevance']} / {r['pi_tiebreaks_valence']} | "
                 f"{r['pi_decided_relevance']} / {r['pi_decided_valence']} | "
                 f"{r['relevant_none_without_support']} |")
    L.append("\nStatus counts (first reading): "
             + ", ".join(f"{k} = {v}" for k, v in a["status_counts"].items()) + "\n")

    L.append("## 6. Machine channels versus gold labels (§7)\n")
    for name, mc in res["machine_channels"].items():
        prov = mc["provenance"]
        L.append(f"### {name}\n")
        L.append(f"Source: {prov.get('source')}"
                 + (f"; git check: {prov['git_check']['status']} ({prov['git_check']['detail']})" if "git_check" in prov else "")
                 + (f"; blob {prov['blob']}" if "blob" in prov and "git_check" not in prov else "")
                 + (f"; identical to git HEAD: {prov['matches_git_HEAD']}" if "matches_git_HEAD" in prov else "")
                 + (f"; frozen version of PROTOCOL §12.1: {prov['matches_protocol_12_1']}"
                    if "matches_protocol_12_1" in prov else "")
                 + (f"; format {prov['format']}" if "format" in prov else "")
                 + (f"; status_llm {prov['status_llm_counts']}" if "status_llm_counts" in prov else "")
                 + (f"; relevant {prov['n_relevant']} of {prov['n_fragments']}" if "n_relevant" in prov else "")
                 + "\n")
        L.append("| comparison | κ [95% CI], n | accuracy |")
        L.append("|---|---|---|")
        for x in DIMS:
            lab = {"relevance": "relevance (gold resolved)",
                   "valence_conditional": "valence (gold relevant and channel relevant)",
                   "valence_all": "valence (all fragments, none for non-relevant)"}[x]
            L.append(f"| {lab} | {est(mc[x])} | {f3(mc[x]['po'])} |")
        L.append("")
        for x in DIMS:
            L.append(f"*{x}* (rows gold, columns {name}; n={mc[x]['n']})\n")
            L.append(confusion_md(mc[x]["confusion"], "gold", name) + "\n")

    L.append("## 7. Data quality\n")
    L.append("| coder | rows | missing | unknown ids | relevance out of codebook | valence out of codebook | "
             "valence missing | valence on not-relevant (→ none) | text ≠ reference | bad time |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for nm, c in res["coders"].items():
        i = c["issues"]
        L.append(f"| {nm} | {c['n_rows']} | {c['missing']} | {i['unknown_ids']['count']} | "
                 f"{i['relevance_out_of_codebook']['count']} | {i['valence_out_of_codebook']['count']} | "
                 f"{i['valence_missing']['count']} | {i['valence_on_not_relevant']['count']} | "
                 f"{i['text_mismatch']['count']} | {i['bad_time']['count']} |")
    L.append("\nExamples of each issue are in `reliability.json` (coders → issues).\n")

    L.append("## 8. Method notes and provenance\n")
    L.append("- Cohen's κ: categories = labels observed in the pair; κ undefined when chance "
             "agreement is 1. Valence (both marked relevant) uses fragments both coders marked "
             "relevant with a valid valence; the all-fragments version sets `none` for non-relevant.")
    L.append(f"- CIs: {m['bootstrap']['method']}.")
    L.append("- Gate: mean pairwise κ (point estimate, exact rational arithmetic) ≥ 0.70 on "
             "relevance and on valence (both marked relevant); the PI is never in a primary pair.")
    pr = m["protocol"]
    L.append(f"- Protocol file {pr['file']}: version {pr['version']} ({pr['date']}), sha256 {pr['sha256']}, "
             f"git blob {pr['git_blob']}; identical to git HEAD: {pr['matches_git_HEAD']}.")
    L.append("- Krippendorff's α: nominal metric, coincidence-matrix formula; CI from the same "
             "fragment bootstrap (not Krippendorff's own bootstrap algorithm).")
    L.append(f"- Reference fragments sha256 {m['reference']['sha256']}; script sha256 {m['script_sha256']}; "
             f"git HEAD {m['git_head'] or 'unavailable'}.")
    for nm, c in res["coders"].items():
        L.append(f"- {nm}: `{os.path.basename(c['file'])}` sha256 {c['sha256']}; identity from {c['identity_from']}")
    L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def write_outputs(res, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = {k: os.path.join(out_dir, f) for k, f in (
        ("report", "reliability_report.md"), ("json", "reliability.json"),
        ("gold", "gold_labels.csv"), ("exclusions", "exclusions.csv"))}
    with open(paths["gold"], "w", newline="", encoding="utf-8") as fh:
        rows = res["gold_rows"]
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)
    with open(paths["exclusions"], "w", newline="", encoding="utf-8") as fh:
        rows = res["exclusion_rows"]
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    out = {k: v for k, v in res.items() if k not in ("gold_rows", "exclusion_rows")}
    out["gold_labels_csv"] = os.path.basename(paths["gold"])
    with open(paths["json"], "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, sort_keys=False)
    write_report(res, paths["report"])
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("coder_csv", nargs="+", help="one CSV per coder")
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--pi", help="the PI's coder identity (coder column or file stem); must match "
                     "an input coder, otherwise the run stops")
    who.add_argument("--pi-did-not-code", action="store_true",
                     help="declare that no PI file is among the inputs")
    ap.add_argument("--meta", help="CSV: coder,source,english_level,practice_correct,practice_n")
    ap.add_argument("--boot", type=int, default=BOOT_PROTOCOL, help="bootstrap resamples (protocol: 1000)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--fragments", help="reference fragments (default: coding_sample.csv, else ws1_survey.html)")
    ap.add_argument("--channel", action="append", default=[],
                    help="extra machine channel NAME=path.csv: llm_labels.csv of ws1_llm_channel.py "
                         "(PROTOCOL section 12.2) or the coder columns frag_id, human_relevant_0_1, "
                         "human_valence_minus_plus_none")
    a = ap.parse_args(argv)
    if a.boot < 0:
        ap.error("--boot must be >= 0")
    try:
        res = analyse(a.coder_csv, a.pi, read_meta(a.meta) if a.meta else None,
                      a.boot, a.seed, a.fragments, a.channel, pi_did_not_code=a.pi_did_not_code)
        paths = write_outputs(res, a.out_dir)
    except DataError as e:
        raise SystemExit(f"ERROR: {e}")
    d, p, adj = res["decision"], res["primary"], res["adjudication"]
    print(f"coders {len(res['coders'])}, eligible {len(res['eligible'])} {res['eligible']}, "
          f"primary group {p['group']}")
    for dim in DIMS:
        g = p["gate"].get(dim)
        print(f"  mean pairwise kappa, {DIM_LABEL[dim]}: {est(p['mean'][dim])}"
              + ("" if g is None else f"  -> gate: {g['why']}"))
    print(f"GATE: {d['status']} - {d['text']}")
    print(f"gold ({adj['name']}): PI tie-breaks relevance {adj['pi_tiebreaks_relevance']}, valence "
          f"{adj['pi_tiebreaks_valence']}; decided by the PI's label relevance {adj['pi_decided_relevance']}, "
          f"valence {adj['pi_decided_valence']}; unresolved relevance {adj['unresolved_relevance']}, "
          f"valence {adj['unresolved_valence']}")
    for w in res["warnings"]:
        print("  ! " + w)
    print("-> " + ", ".join(paths.values()))


if __name__ == "__main__":
    main()
