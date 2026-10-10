#!/usr/bin/env python3
"""
ws1_reliability.py - WS1.0 reliability analysis, implemented from
PROTOCOL_WS1.0.md sections 5-9 (v1, 2026-09-18) as clarified and extended by
the section-12 addendum (v1.1; ROADMAP D36): 12.1(b) gold labels, 12.3
sensitivity analyses, 12.5 frozen machine channels. The protocol version on
disk is read at run time and recorded with its sha256 in the report.

Inputs: one CSV per coder, from any of the three instruments
  (a) the claude.ai page (make_artifact_page.py): frag_id, text,
      human_relevant_0_1, human_valence_minus_plus_none, position,
      time_seconds, coder, codebook_version, order_seed, session_start,
      session_end, ui_language, english_level, source
      [, practice_correct, practice_n -- exported since 2026-10-10]
      [, practice_set -- id of the practice items the coder saw]
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
      (conditional) valence. The comparison is exact: the pair kappas are
      rationals of integer label counts, their mean is formed with
      fractions.Fraction and compared with Fraction(7, 10), so a mean of
      exactly 0.70 passes (no float rounding, no tolerance needed)
  [7] Krippendorff's alpha (nominal, missing allowed), PI vs each coder,
      kappa by recruitment source and by interface language, dictionary
      v0/v1 and any --channel (e.g. the LLM channel's llm_labels.csv) vs
      gold labels, timing distributions
  [8] gold labels as clarified in section 12.1(b) (D36.1): the PI does NOT vote. Gold
      relevance = plurality among the eligible non-PI coders; a tie is
      broken by the PI's label (counted as a PI tie-break); if the PI did
      not code (--no-pi) or did not code that fragment, it is unresolved.
      Gold valence (gold relevance 1) = plurality among the eligible non-PI
      coders who marked the fragment relevant; a tie is broken by the PI
      only if the PI marked it relevant, otherwise unresolved. Gold
      relevance 0 -> valence `none`. The reading "the PI votes" is reported
      as a sensitivity analysis (ADJ_READINGS)         -> gold_labels.csv
  [9] decision (on all fragments), as clarified in section 12.1(c): a mean
      below 0.70 on either gated dimension is FAIL whatever the other shows
      (including an undefined mean, whose cause is reported); NOT ASSESSABLE
      only when nothing failed and a mean is undefined or there is no primary
      pair; valence fails "alone" only when relevance passed
  [12.3] every statistic of [6] and [7] (and the gold summary) is also
      reported (a) without the fragments quoted as anchors in CODEBOOK.md,
      (b) without the fragments the old practice items paraphrased, (c)
      without both. Inclusion (section 5) and the primary pairs are decided
      once, on the full instrument; the exclusions only remove fragments.
Everything goes to reliability_report.md and reliability.json in --out-dir.

The PI must be identified: --pi NAME has to match an input coder, otherwise
the run stops with a non-zero exit (the PI's coding must never reach the
primary kappa); or --no-pi declares that no PI file is among the inputs.

Stdlib only (like the rest of ws1/). Usage:
    python3 ws1_reliability.py ws1_coded_A.csv ws1_coded_B.csv ws1_coded_PI.csv \\
        (--pi PI_CODER_NAME | --no-pi) [--meta coders.csv] [--boot 1000] \\
        [--seed 2026] [--out-dir DIR] [--fragments coding_sample.csv|ws1_survey.html] \\
        [--channel LLM=llm_labels.csv] [--anchor-ids FILE|ID,ID,...] \\
        [--old-practice-ids FILE|ID,ID,...]
"""
import argparse, ast, csv, datetime, hashlib, json, math, os, random, re, statistics, subprocess, sys
from collections import Counter
from fractions import Fraction
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

PROTOCOL_FILE = os.path.join(HERE, "PROTOCOL_WS1.0.md")
PROTOCOL_GIT_PATH = "narrative-economics/code/ws1/PROTOCOL_WS1.0.md"
# Versions whose sections 5-9 this script implements: v1 (sections 1-11) and
# v1.1 (v1 + the section-12 addendum, which clarifies section 8 and adds the
# fragment-exclusion sensitivity analyses, ROADMAP D36). A version not listed
# here is run with a warning; tests/test_reliability.py fails on it, so that
# sections 5-9 are re-read before the version is added.
PROTOCOL_KNOWN = ("1", "1.1")
PROTOCOL_ADDENDUM_SECTION = {"1.1": "12"}    # version -> section that must exist in the file
CODEBOOK = "v1"
GATE = 0.70                           # for display and JSON
GATE_EXACT = Fraction(7, 10)          # the comparison itself (section 6), exact
N_PROTOCOL = 300                      # section 2/5(c): "all 300 fragments"
BOOT_PROTOCOL = 1000                  # section 6: "1,000 resamples over fragments"
# SHA-256 of the evaluation input set, canonical JSON of [[frag_id, text], ...]
# sorted by frag_id (PROTOCOL section 12.5.3 (iv); D36.5): the 300 the LLM channel codes.
EVAL_INPUT_SHA256 = "603893308ce3bcf17aa71b33b39cfb0b8352192a754afa46d1a3e0aa425e47f2"
# Stratification of the 300 by the dictionary that drew them (section 12.1(a),
# D36.2: dictionary v1; section 2's 136 / 164 is the v0 count on the same fragments).
DRAW_STRATA_V1 = (140, 160)
# The practice set whose items the LLM prompt carries as worked examples
# (section 12.4, item 2; 12.5.3): instruction parity holds for coders whose
# export has this practice_set.
PRACTICE_SET_PROTOCOL = "3fa31542cb4a"
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
                  "ui_language", "english_level", "source", "practice_correct", "practice_n",
                  "practice_set")
META_FIELDS = ("source", "english_level", "practice_correct", "practice_n")
DIMS = ("relevance", "valence_conditional", "valence_all")
GATED = ("relevance", "valence_conditional")       # section 6: the gate dimensions
DIM_KEY = {"relevance": "rel", "valence_conditional": "val_cond", "valence_all": "val_all"}
DIM_LABEL = {"relevance": "relevance (all fragments)",
             "valence_conditional": "valence (both marked relevant)",
             "valence_all": "valence (all fragments, none for non-relevant)"}
RULES = (("a", "English good/fluent/native"), ("b", "practice >= 6 of 8, first attempt"),
         ("c", "all fragments completed"), ("d", "median time >= 3 s"))
PASS, FAIL, NA = "pass", "fail", "not assessable"
TIEBREAK = "PI tie-break"
# llm_labels.csv as written by ws1_llm_channel.py (PROTOCOL section 12.5.3; a
# fifth column, model_served, is read when present). Only rows with
# status_llm == "ok" are compared; every other status is reported and excluded
# from that channel's comparison. The run record next to it (llm_labels_run.json)
# is read when present: its labels_sha256 must match the file, and its four
# identities must be those of PROTOCOL 12.5.3 (LLM_V1_IDENTITY, below).
LLM_COLS = ("frag_id", "relevant_llm", "valence_llm", "status_llm")
LLM_STATUS_OK = "ok"
LLM_RUN_RECORD = "llm_labels_run.json"
# The four frozen identities of LLM channel v1 as written in PROTOCOL section
# 12.5.3 (i)-(iv). A run is a run of LLM channel v1 only if its run record
# carries exactly these (12.6.2), whatever the FROZEN table of
# verify_frozen_channels.py holds: the runner checks only that table, so a
# runner changed together with the table would still run. The run record's
# values are compared with these; at run time these are also checked against
# the protocol text on disk and the verifier's table (llm_frozen_consistency).
LLM_V1_CHANNEL = "ws1-llm-channel-v1"
LLM_V1_IDENTITY = {
    "runner_sha256": "4899c38ed3ea3a3ce4a1a3ca225612e799b8712057cf9cb7b7df9e8fadcbbcc6",   # 12.5.3 (ii)
    "prompt_sha256": "ec8cc4a7925b737f0d81f29f5293987bf5e83faf8e818ebda73a8082f71785a8",   # 12.5.3 (i)
    "spec_sha256": "129bb453c72e4d8fc23b9095a12c0fc3fddaf4e415b4ef55fe69e2fdd151605b",     # 12.5.3 (iii)
    "input_set_sha256": EVAL_INPUT_SHA256,                                                # 12.5.3 (iv)
}
VERIFY_FILE = os.path.join(HERE, "verify_frozen_channels.py")
VERIFY_KEYS = {"runner_sha256": "llm_runner_sha256", "prompt_sha256": "llm_prompt_sha256",
               "spec_sha256": "llm_spec_sha256", "input_set_sha256": "input_set_sha256"}

# ---------------------------------------------------------------------------
# Pre-specified fragment exclusions for the sensitivity analyses of PROTOCOL
# section 12.3 (addendum v1.1; ROADMAP D36.3). Every primary and secondary
# statistic is reported on all fragments and (a) without CODEBOOK_ANCHOR_FRAG_IDS,
# (b) without OLD_PRACTICE_PARAPHRASED_FRAG_IDS, (c) without both. Lists as
# supplied by the practice-item review (2026-10-10) and written out in section
# 12.3 (a) and (b); at run time they are compared with the ids listed on those
# two protocol lines (PROTOCOL_LIST_MARKERS). --anchor-ids / --old-practice-ids
# override them, and the report says so.
# (a) evaluation fragments quoted (shortened) as decision examples or anchors in
#     CODEBOOK.md v1. 16 fragments.
CODEBOOK_ANCHOR_FRAG_IDS = (
    "66zEFbmgQ5I_001", "66zEFbmgQ5I_007", "66zEFbmgQ5I_020", "66zEFbmgQ5I_027",
    "66zEFbmgQ5I_033", "6pvGBbIS7Xo_010", "E-7FJF51JSU_039", "EGskcTRnLJ0_015",
    "EGskcTRnLJ0_031", "IUBo9dnZM3g_011", "Zcpj-U5lcAc_000", "dvmcqxOoA5s_012",
    "jynC9SncpDM_000", "jynC9SncpDM_016", "jynC9SncpDM_017", "moiuHRHB6nE_042",
)
# (b) evaluation fragments that the OLD practice items (the 8 items shown before
#     the practice set was replaced) paraphrased. 75 fragments; 8 of them are also
#     in (a), so (c) removes 83.
OLD_PRACTICE_PARAPHRASED_FRAG_IDS = (
    "66zEFbmgQ5I_002", "66zEFbmgQ5I_005", "66zEFbmgQ5I_006", "66zEFbmgQ5I_007",
    "66zEFbmgQ5I_008", "66zEFbmgQ5I_012", "66zEFbmgQ5I_013", "66zEFbmgQ5I_015",
    "66zEFbmgQ5I_016", "66zEFbmgQ5I_028", "66zEFbmgQ5I_033", "6pvGBbIS7Xo_000",
    "6pvGBbIS7Xo_007", "6pvGBbIS7Xo_008", "6pvGBbIS7Xo_009", "6pvGBbIS7Xo_010",
    "6pvGBbIS7Xo_011", "E-7FJF51JSU_009", "E-7FJF51JSU_035", "EGskcTRnLJ0_006",
    "EGskcTRnLJ0_012", "EGskcTRnLJ0_020", "EGskcTRnLJ0_022", "IUBo9dnZM3g_007",
    "IUBo9dnZM3g_009", "IUBo9dnZM3g_010", "IUBo9dnZM3g_011", "IUBo9dnZM3g_021",
    "IUBo9dnZM3g_022", "IUBo9dnZM3g_023", "IUBo9dnZM3g_024", "IUBo9dnZM3g_025",
    "IUBo9dnZM3g_026", "IUBo9dnZM3g_028", "R6mTUK_yPKw_035", "R6mTUK_yPKw_044",
    "Zcpj-U5lcAc_000", "Zcpj-U5lcAc_001", "Zcpj-U5lcAc_008", "Zcpj-U5lcAc_011",
    "Zcpj-U5lcAc_012", "Zcpj-U5lcAc_013", "Zcpj-U5lcAc_014", "Zcpj-U5lcAc_019",
    "Zcpj-U5lcAc_020", "Zcpj-U5lcAc_021", "Zcpj-U5lcAc_034", "Zcpj-U5lcAc_037",
    "dvmcqxOoA5s_003", "dvmcqxOoA5s_005", "dvmcqxOoA5s_007", "dvmcqxOoA5s_013",
    "dvmcqxOoA5s_014", "jynC9SncpDM_004", "jynC9SncpDM_015", "jynC9SncpDM_016",
    "jynC9SncpDM_017", "moiuHRHB6nE_001", "moiuHRHB6nE_007", "moiuHRHB6nE_014",
    "moiuHRHB6nE_021", "moiuHRHB6nE_025", "moiuHRHB6nE_028", "moiuHRHB6nE_034",
    "moiuHRHB6nE_042", "pGBkP9jNz-U_006", "pGBkP9jNz-U_007", "pGBkP9jNz-U_008",
    "pGBkP9jNz-U_009", "sb5glj61LsA_003", "sb5glj61LsA_004", "sb5glj61LsA_009",
    "xsWaPdvCmy4_005", "xsWaPdvCmy4_006", "xsWaPdvCmy4_013",
)
EXCLUSION_LISTS = (("anchors", "fragments quoted as anchors in CODEBOOK.md", "--anchor-ids"),
                   ("old_practice", "fragments the old practice items paraphrased", "--old-practice-ids"))
# start of the section-12.3 protocol line that lists each set's frag_ids
PROTOCOL_LIST_MARKERS = {"anchors": "- (a) Codebook anchors:", "old_practice": "- (b) Earlier practice items:"}
FRAG_ID_IN_PROTOCOL = re.compile(r"`([A-Za-z0-9_-]{11}_\d{3})`")
# (name, label, which exclusion lists are removed); the first is the analysis of record
FRAGMENT_SETS = (
    ("all", "all fragments (analysis of record)", ()),
    ("excl_anchors", "(a) without the CODEBOOK.md anchor fragments", ("anchors",)),
    ("excl_old_practice", "(b) without the fragments the old practice items paraphrased", ("old_practice",)),
    ("excl_both", "(c) without both", ("anchors", "old_practice")),
)

# Section 8 readings: (name, the PI votes, text). The first is the gold standard
# of record (section 12.1(b), D36.1: gold_labels.csv, machine channels); the
# second is the sensitivity reading that 12.1(b) asks to report.
ADJ_READINGS = (
    ("pi_breaks_ties_only", False,
     "the PI does not vote: plurality among the eligible non-PI coders, a tie broken by the PI's label "
     "(unresolved if the PI did not code the fragment); valence among the eligible non-PI coders who "
     "marked the fragment relevant, a tie broken by the PI only if the PI marked it relevant"),
    ("pi_votes", True,
     "sensitivity reading: the PI votes as one of the eligible coders when the PI meets the inclusion "
     "rules; ties and valence as in the reading of record"),
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
# Section 7 compares v0 with the gold labels, so it is identified by these
# hashes (PROTOCOL section 12.5.2): the file's sha256 and git blob, and the
# sha256 of its four term lists (checked on the embedded copy at every run).
#
# Which dictionary drew the 300-fragment sample (ROADMAP D36.2, recorded in
# section 12.1(a) as a correction to section 2): dictionary v1. The
# post-stance-fix pipeline run (7eb5a1e) wrote fragments.csv and
# coding_sample.csv together (the lead's D36.2 also says fragments.csv carried
# the v1-only 'skeptical' column; fragments.csv is git-ignored and not in the
# repository, so that cannot be checked here and section 12.1(a) does not cite
# it), and all 140 v1-relevant corpus fragments (431 in all; 136 v0-relevant)
# are in the sample: certain under a v1 draw, probability
# C(291,160)/C(295,164) = 0.094 under a v0 draw (likelihood ratio about 10.6).
# Stratification by the drawing dictionary is therefore 140 relevant / 160
# non-relevant (DRAW_STRATA_V1); the 136 / 164 of section 2 is the v0 count on
# the same 300 (every v0-relevant fragment is also v1-relevant).
# ---------------------------------------------------------------------------
V0_COMMIT = "a2384895755c63ac3a42ec435bc3b8302760566a"
V0_PATH = "narrative-economics/code/ws1/ws1_pipeline.py"
V0_BLOB = "4311d765b036a451e54b905217d2ea0edf0c1f41"
V0_FILE_SHA256 = "8cfd994b5542411e0e4a8367ffb81dd05b3e117c1599caaf0ac343da4860ce49"    # PROTOCOL 12.5.2
V0_TERMS_SHA256 = "25080905de5acc63da004e4cc25a2ff7ea1274fec114b8a7ce5c5fce8c328693"   # PROTOCOL 12.5.2
V1_FROZEN_BLOB = "15759519ec822077ab755478193a6b270962fbed"   # PROTOCOL section 12.5.1
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


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def input_set_sha256(ref_text):
    """SHA-256 of canonical JSON [[frag_id, text], ...] sorted by frag_id -- the
    definition of PROTOCOL section 12.5.3 (iv) (fragments_sha256 in ws1_llm_channel.py)."""
    return hashlib.sha256(canonical_json([[f, ref_text[f]] for f in sorted(ref_text)]).encode("utf-8")).hexdigest()


def terms_sha256(lists):
    """SHA-256 of {name: list} term lists as PROTOCOL 12.5.1/12.5.2 define it
    (canonical JSON, lists in source order)."""
    return hashlib.sha256(canonical_json(lists).encode("utf-8")).hexdigest()


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
    """Version, date, hashes and section numbers of PROTOCOL_WS1.0.md as it is on disk now."""
    out = {"file": os.path.basename(PROTOCOL_FILE), "version": None, "date": None,
           "sha256": None, "git_blob": None, "matches_git_HEAD": None, "sections": [], "text": ""}
    if not os.path.exists(PROTOCOL_FILE):
        return out
    with open(PROTOCOL_FILE, "rb") as fh:
        data = fh.read()
    text = data.decode("utf-8")
    m = re.search(r"\*\*Version\s+([0-9][0-9.]*)\s*·\s*(\d{4}-\d{2}-\d{2})\.?\*\*", text)
    head = git("rev-parse", "HEAD:" + PROTOCOL_GIT_PATH)
    out.update(version=m.group(1) if m else None, date=m.group(2) if m else None,
               sha256=hashlib.sha256(data).hexdigest(), git_blob=git_blob_sha(data),
               matches_git_HEAD=None if head is None else head.decode().strip() == git_blob_sha(data),
               sections=re.findall(r"(?m)^##\s+(\d+)\.", text), text=text)
    return out


def protocol_label(p):
    if p["version"] is None:
        return f"{p['file']} (version line not found)"
    return f"{p['file']} v{p['version']} ({p['date']})"


def protocol_warnings(p):
    """Version check: the version must be one this script implements, and a
    version with an addendum must contain that section."""
    w = []
    if p["version"] not in PROTOCOL_KNOWN:
        w.append(f"{protocol_label(p)}: this script implements sections 5-9 as worded in versions "
                 f"{', '.join(PROTOCOL_KNOWN)} (with the section-12 clarifications of v1.1); check "
                 "them against this version")
    sec = PROTOCOL_ADDENDUM_SECTION.get(p["version"])
    if sec and sec not in p["sections"]:
        w.append(f"{protocol_label(p)} has no section {sec}, which version {p['version']} adds")
    return w


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


def read_id_list(spec, option):
    """frag_ids for --anchor-ids / --old-practice-ids: a file with frag_ids
    separated by newlines, commas or spaces ('#' starts a comment; a 'frag_id'
    header is skipped), or a comma-separated list on the command line."""
    if os.path.isfile(spec):
        with open(spec, encoding="utf-8-sig") as fh:
            text = "\n".join(line.split("#", 1)[0] for line in fh)
        origin = f"file {spec}"
    else:
        text, origin = spec, "command line"
    ids = [t for t in re.split(r"[\s,]+", text) if t and t != "frag_id"]
    dup = sorted(k for k, v in Counter(ids).items() if v > 1)
    if dup:
        raise DataError(f"{option} ({origin}): frag_id(s) listed twice: {dup[:10]}")
    return tuple(ids), origin


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
    for f in ("source", "english_level", "practice_correct", "practice_n", "practice_set", "ui_language",
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
        self.samples = [[rng.randrange(n) for _ in range(n)] for _ in range(n_boot)] if n else []

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
    """Agreement statistics over one set of fragments (coders' label lists
    aligned to ids), with one bootstrap shared by every statistic."""

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
        undefined = [{"pair": [a, b], "n": r[1]["n"], "why": undefined_kappa_why(dim, r[1]["n"])}
                     for (a, b), r in zip(pairs, runs) if r[1]["value_exact"] is None]
        info = {"n": [r[1]["n"] for r in runs], "pairs": [list(p) for p in pairs],
                "value_exact": fraction_str(value_exact), "undefined_pairs": undefined}
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
        out["value_exact"] = fraction_str(kappa_exact([p for p in P if p is not None]))
        out["confusion"] = confusion(P, cats)
        return out


def undefined_kappa_why(dim, n):
    """Why a pairwise kappa is undefined (PROTOCOL 12.1(c)): nothing to compare, or chance agreement 1."""
    if n == 0:
        return ("n = 0: no fragment that both coders marked relevant" if dim == "valence_conditional"
                else "n = 0: no fragment that both coders labelled")
    return f"chance agreement = 1: both coders gave one and the same label to all {n} compared fragments"


GATE_DIM_NAME = {"relevance": "relevance", "valence_conditional": "valence"}


def gate_of(mean):
    """Section 6 gate on the mean pairwise kappas, compared exactly with 7/10.
    'pass' is True, False, or None (not evaluated; 'cause' says why)."""
    out = {}
    for d in GATED:
        m = mean.get(d)
        if m is None:
            out[d] = {"pass": None, "cause": "no_primary_pair",
                      "why": "no primary pair (fewer than two eligible non-PI coders, section 6)"}
        elif m["value_exact"] is None:
            und = m.get("undefined_pairs") or []
            detail = "; ".join(f"{u['pair'][0]} × {u['pair'][1]}: {u['why']}" for u in und)
            out[d] = {"pass": None, "cause": "undefined_kappa",
                      "why": f"mean κ undefined: κ is undefined for {len(und)} of {len(m['pairs'])} primary "
                             f"pair(s)" + (f" ({detail})" if detail else "")}
        else:
            x = Fraction(m["value_exact"])
            ok = x >= GATE_EXACT
            out[d] = {"pass": ok, "why": f"mean κ {vs_gate(x)} {'≥' if ok else '<'} {GATE:.2f}"}
    return out


def decide(gate):
    """Section 9, as clarified in section 12.1(c). The gate needs mean κ >= 0.70
    on BOTH dimensions (section 6), so a mean below 0.70 on either dimension is
    a FAIL whatever the other dimension shows (at least 0.70, below, or
    undefined). NOT ASSESSABLE only when nothing failed and a dimension could
    not be evaluated (no primary pair, or an undefined pairwise κ); section 9
    then takes no decision. Valence fails 'alone' only if relevance passed."""
    failed = [GATE_DIM_NAME[d] for d in GATED if gate[d]["pass"] is False]
    unevaluated = [d for d in GATED if gate[d]["pass"] is None]
    causes = "; ".join(f"{GATE_DIM_NAME[d]}: {gate[d]['why']}" for d in unevaluated)
    if failed:
        text = ("Gate failed on " + " and ".join(failed) + ": codebook v2 is written from the "
                "disagreement patterns, deposited on OSF, and the reliability study is repeated with "
                "new or re-trained coders.")
        if unevaluated:
            text += (f" The gate on {' and '.join(GATE_DIM_NAME[d] for d in unevaluated)} could not be "
                     f"evaluated ({causes}); the gate needs mean κ ≥ 0.70 on both dimensions (section 6), "
                     "so the failure decides it (section 12.1(c)).")
        valence_only = failed == ["valence"] and gate["relevance"]["pass"] is True
        if valence_only:
            text += (" Valence alone failed: if this is the second valence-only failure, the "
                     "pre-specified fallback is a binary alarming/reassuring scheme, declared as a "
                     "deviation (this script does not know the attempt history).")
        elif failed == ["valence"]:
            text += (" Relevance was not evaluated, so this is not a valence-only failure in the sense of "
                     "the section 9 fallback (section 12.1(c)).")
        return {"status": "FAIL", "failed": failed, "not_evaluated": [GATE_DIM_NAME[d] for d in unevaluated],
                "valence_only": valence_only, "text": text}
    if unevaluated:
        if any(gate[d].get("cause") == "no_primary_pair" for d in unevaluated):
            text = (f"The gate cannot be evaluated ({causes}): the protocol needs at least two eligible "
                    "non-PI coders (section 6).")
        else:
            text = f"The gate cannot be evaluated ({causes}), and no mean pairwise κ is below 0.70."
        text += (" Section 9 defines only pass and fail, so no decision is taken; a decision taken in this "
                 "case is reported as a deviation (section 12.1(c)).")
        return {"status": "NOT ASSESSABLE", "failed": [],
                "not_evaluated": [GATE_DIM_NAME[d] for d in unevaluated], "valence_only": False, "text": text}
    return {"status": "PASS", "failed": [], "not_evaluated": [], "valence_only": False,
            "text": "Gate passed: WS1 starts with the codebook (v1) unchanged."}


# ---------------------------------------------------------------------------
# section 8: adjudication (section 12.1(b); D36.1)
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
        return pi_label, TIEBREAK, False
    return None, "unresolved: tie, PI label not among the tied labels", False


def tally(labels):
    return ";".join(f"{k}:{v}" for k, v in sorted(Counter(x for x in labels if x is not None).items()))


def build_gold(coders, ids, eligible, pi, pi_votes=False):
    """Gold labels per fragment under one reading of section 8 (ADJ_READINGS).
    pi_votes=False is section 12.1(b): the voters are the eligible non-PI coders, the PI
    only breaks ties. Relevance: plurality of the voters, a tie broken by the
    PI's label (unresolved when the PI did not code the fragment). Gold
    relevance 0 -> valence `none` (codebook); gold relevance 1 -> valence voted
    among the voters who marked the fragment relevant, a tie broken by the PI
    only if the PI marked it relevant. Also marks where the PI's label decided
    the gold: the gold differs from what the eligible non-PI coders give on
    their own (their plurality, unresolved when tied) -- under 12.1(b) exactly the
    PI tie-breaks; under pi_votes also fragments where the PI's vote was pivotal."""
    voters = [v for v in eligible if pi_votes or v != pi]
    nonpi = [v for v in eligible if v != pi]
    rows = []
    for i, fid in enumerate(ids):
        pr = coders[pi]["rel"][i] if pi else None
        pv = coders[pi]["val_cond"][i] if pi else None
        if pi is None:
            why_r = why_v = "PI did not code"
        else:
            why_r = "PI label missing"
            why_v = ("PI label missing" if pr is None else "PI did not mark it relevant" if pr != "1"
                     else "PI valence missing")
        rv = [coders[v]["rel"][i] for v in voters]
        vv = [coders[v]["val_cond"][i] for v in voters]
        g_rel, s_rel, abs_rel = adjudicate(rv, pr, why_r)
        g_val, s_val, abs_val = None, "unresolved: relevance unresolved", False
        if g_rel == "0":
            g_val, s_val = "none", "rule: gold relevance 0 -> none"
        elif g_rel == "1":
            g_val, s_val, abs_val = adjudicate(vv, pv, why_v)
        own_rel = adjudicate([coders[v]["rel"][i] for v in nonpi], None)[0]
        own_val = adjudicate([coders[v]["val_cond"][i] for v in nonpi], None)[0]
        pi_rel = g_rel is not None and g_rel != own_rel
        pi_val = g_rel == "1" and g_val is not None and g_val != own_val
        rows.append({"frag_id": fid, "gold_relevant": g_rel, "gold_valence": g_val,
                     "relevance_status": s_rel, "valence_status": s_val,
                     "n_voters": sum(1 for v in rv if v is not None),
                     "votes_relevance": tally(rv), "votes_valence": tally(vv),
                     "pi_relevant": pr, "pi_valence": coders[pi]["val_all"][i] if pi else None,
                     "pi_decided_relevance": "yes" if pi_rel else "no",
                     "pi_decided_valence": "yes" if pi_val else "no",
                     "_abs_rel": abs_rel, "_abs_val": abs_val})
    return rows


def gold_summary(rows):
    """Counts over gold rows (all fragments, or one sensitivity set)."""
    st = Counter()
    for g in rows:
        st["rel:" + g["relevance_status"]] += 1
        st["val:" + g["valence_status"]] += 1
    unres_rel = [g["frag_id"] for g in rows if g["gold_relevant"] is None]
    unres_val = [g["frag_id"] for g in rows if g["gold_relevant"] == "1" and g["gold_valence"] is None]
    return {
        "n": len(rows),
        "pi_tiebreaks_relevance": sum(g["relevance_status"] == TIEBREAK for g in rows),
        "pi_tiebreaks_valence": sum(g["valence_status"] == TIEBREAK for g in rows),
        "fragments_with_any_pi_tiebreak": sum(TIEBREAK in (g["relevance_status"], g["valence_status"])
                                              for g in rows),
        "pi_decided_relevance": sum(g["pi_decided_relevance"] == "yes" for g in rows),
        "pi_decided_valence": sum(g["pi_decided_valence"] == "yes" for g in rows),
        "fragments_pi_decided": sum("yes" in (g["pi_decided_relevance"], g["pi_decided_valence"])
                                    for g in rows),
        "unresolved_relevance": len(unres_rel),
        "unresolved_relevance_ids": unres_rel,
        # valence unresolved although gold relevance is 1 (a fragment with
        # unresolved relevance has no gold valence either; not counted here)
        "unresolved_valence": len(unres_val),
        "unresolved_valence_ids": unres_val,
        "gold_relevant_counts": dict(sorted(Counter(g["gold_relevant"] for g in rows
                                                    if g["gold_relevant"]).items())),
        "gold_valence_counts": dict(sorted(Counter(g["gold_valence"] for g in rows
                                                   if g["gold_valence"]).items())),
        "plurality_without_absolute_majority": {
            "relevance": sum(g["relevance_status"] == "majority" and not g["_abs_rel"] for g in rows),
            "valence": sum(g["valence_status"] == "majority" and not g["_abs_val"] for g in rows)},
        "status_counts": dict(sorted(st.items()))}


# ---------------------------------------------------------------------------
# machine channels
# ---------------------------------------------------------------------------
def v0_git_check(texts):
    """Compare the embedded v0 copy with git history (fails loudly on mismatch)."""
    src = git("show", f"{V0_COMMIT}:{V0_PATH}")
    if src is None:
        return {"status": "not checked", "detail": "git history not available here; the "
                "embedded copy was verified when written (see tests/test_reliability.py)"}
    blob, file_sha = git_blob_sha(src), hashlib.sha256(src).hexdigest()
    ns = {"__name__": "ws1_pipeline_v0_from_git"}
    exec(compile(src, f"{V0_COMMIT[:7]}:{V0_PATH}", "exec"), ns)
    lists_ok = all(ns[k] == v for k, v in V0_LISTS.items())
    out_ok = all(tuple(ns["classify"](t)) == tuple(classify_v0(t)) for t in texts)
    if blob != V0_BLOB or file_sha != V0_FILE_SHA256 or not lists_ok or not out_ok:
        raise DataError(f"embedded dictionary v0 differs from git {V0_COMMIT[:7]}:{V0_PATH} "
                        f"(blob {blob}, sha256 {file_sha}, lists equal {lists_ok}, outputs equal {out_ok})")
    return {"status": "identical", "detail": f"sha256 {file_sha[:12]}…, blob {blob} (PROTOCOL 12.5.2); term "
            f"lists and classify() output on all {len(texts)} fragments identical to git {V0_COMMIT[:7]}:{V0_PATH}"}


def dictionary_labels(ids, ref_text):
    """{channel: (rel list, val list, provenance)} for dictionary v0 and v1."""
    import ws1_pipeline
    with open(os.path.join(HERE, "ws1_pipeline.py"), "rb") as fh:
        blob = git_blob_sha(fh.read())
    head = git("rev-parse", "HEAD:" + V0_PATH)        # same path, current commit
    v1_prov = {"source": "classify() imported from ws1_pipeline.py (working tree)", "blob": blob,
               "matches_git_HEAD": None if head is None else head.decode().strip() == blob,
               "matches_protocol_frozen": blob == V1_FROZEN_BLOB}
    texts = [ref_text[f] for f in ids]
    v0_terms = terms_sha256(V0_LISTS)
    if v0_terms != V0_TERMS_SHA256:
        raise DataError(f"the embedded dictionary v0 term lists have sha256 {v0_terms}, PROTOCOL 12.5.2 "
                        f"freezes {V0_TERMS_SHA256}")
    v0_prov = {"source": f"embedded verbatim copy of {V0_COMMIT[:7]}:{V0_PATH} (7eb5a1e^, "
               "before the stance fix 7eb5a1e)", "commit": V0_COMMIT, "blob": V0_BLOB,
               "terms_sha256": v0_terms, "git_check": v0_git_check(texts)}
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


def read_llm_labels(path, name):
    """llm_labels.csv of ws1_llm_channel.py (PROTOCOL section 12.5.3). Rows whose
    status_llm is not 'ok' (refusal, invalid, pending, ...) are excluded from
    the comparison -- whatever labels they carry -- and reported."""
    header, rows = read_csv_rows(path)
    missing = [c for c in LLM_COLS if c not in header]
    if missing:
        raise DataError(f"--channel {name}: {path} looks like llm_labels.csv but lacks column(s) {missing}; "
                        f"expected {', '.join(LLM_COLS)} (PROTOCOL section 12.5.3)")
    kept, not_ok, labelled_not_ok, status, served = [], {}, [], Counter(), Counter()
    for r in rows:
        fid = r.get("frag_id", "").strip()
        st = r.get("status_llm", "").strip() or "(blank)"
        if fid:
            status[st] += 1
            if st == LLM_STATUS_OK and "model_served" in header:
                served[r.get("model_served", "").strip() or "(blank)"] += 1
        if fid and st != LLM_STATUS_OK:
            not_ok.setdefault(st, []).append(fid)
            if r.get("relevant_llm", "").strip() or r.get("valence_llm", "").strip():
                labelled_not_ok.append(fid)
            r = dict(r, relevant_llm="", valence_llm="")
        kept.append(r)
    labels, blank = label_rows(path, f"channel {name!r}", kept, "relevant_llm", "valence_llm")
    cf = {"file": path, "coder": name, "identity_from": "--channel", "sha256": sha256_file(path),
          "format": "llm_labels.csv (PROTOCOL section 12.5.3)", "session": {}, "session_conflicts": {},
          "rows": labels, "blank_id_rows": blank, "n_rows": len(labels)}
    excluded = {fid for v in not_ok.values() for fid in v}
    extra = {"status_llm_counts": dict(sorted(status.items())),
             "excluded_status_not_ok": {k: len(v) for k, v in sorted(not_ok.items())},
             "excluded_status_not_ok_ids": {k: sorted(v) for k, v in sorted(not_ok.items())},
             "labels_present_but_status_not_ok": sorted(labelled_not_ok),
             "model_served_counts_ok_rows": dict(sorted(served.items())) if "model_served" in header else None,
             "run_record": llm_run_record(path, cf["sha256"]),
             "ok_ids": sorted(fid for fid in labels if fid not in excluded)}
    return cf, extra


def llm_run_record(labels_path, labels_sha):
    """The run record ws1_llm_channel.py writes next to llm_labels.csv
    (PROTOCOL 12.5.3): <stem>_run.json or llm_labels_run.json in the same folder.
    Reported; its labels_sha256 is compared with the labels file, and its four
    identities (runner, prompt, request specification, input set) with the
    values written in PROTOCOL 12.5.3 (LLM_V1_IDENTITY): a run whose record
    carries other values is not a run of LLM channel v1 (12.6.2)."""
    folder = os.path.dirname(os.path.abspath(labels_path))
    cands = [os.path.splitext(os.path.abspath(labels_path))[0] + "_run.json", os.path.join(folder, LLM_RUN_RECORD)]
    path = next((c for c in cands if os.path.isfile(c)), None)
    if path is None:
        return {"found": False, "looked_for": [os.path.basename(c) for c in dict.fromkeys(cands)]}
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError) as e:
        return {"found": True, "file": os.path.basename(path), "error": f"unreadable: {e}"}
    if not isinstance(rec, dict):
        return {"found": True, "file": os.path.basename(path), "error": "not a JSON object"}
    keys = ("run_id", "complete", "status_counts", "models_served", "model_requested", "input_set_sha256",
            "labels_sha256", "raw_log_sha256", "first_request_utc", "last_response_utc")
    out = {"found": True, "file": os.path.basename(path), "sha256": sha256_file(path),
           **{k: rec.get(k) for k in keys}}
    out["labels_sha256_matches"] = rec.get("labels_sha256") == labels_sha
    out["input_set_matches_protocol"] = rec.get("input_set_sha256") == EVAL_INPUT_SHA256
    out["channel"] = rec.get("channel")
    out["identity"] = {k: rec.get(k) for k in LLM_V1_IDENTITY}
    out["identity_differs"] = [k for k, v in LLM_V1_IDENTITY.items() if rec.get(k) != v]
    out["identity_matches_protocol"] = not out["identity_differs"]
    return out


def frozen_table(path=None):
    """The FROZEN dict literal of verify_frozen_channels.py, read without executing
    that file (as ws1_llm_channel.py reads it); None if it cannot be read."""
    path = path or VERIFY_FILE
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), path)
    except (OSError, SyntaxError, ValueError):
        return None
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "FROZEN"):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return None
    return None


def llm_frozen_consistency(proto_text, table=None):
    """Problems (list of str) with the LLM channel v1 identities held here
    (LLM_V1_IDENTITY): each must be written in section 12 of the protocol on
    disk and equal the FROZEN table of verify_frozen_channels.py, which the
    runner checks before it runs."""
    problems = []
    i = proto_text.find("\n## 12.")
    sec = proto_text[i:] if i >= 0 else ""
    missing = [k for k, v in LLM_V1_IDENTITY.items() if v not in sec]
    if missing:
        problems.append(f"PROTOCOL_WS1.0.md section 12 on disk does not contain the LLM channel v1 identities "
                        f"held by ws1_reliability.py for {missing}")
    table = frozen_table() if table is None else table
    if table is None:
        problems.append("the FROZEN table of verify_frozen_channels.py could not be read")
    else:
        differ = [k for k, fk in VERIFY_KEYS.items() if table.get(fk) != LLM_V1_IDENTITY[k]]
        if differ:
            problems.append(f"the FROZEN table of verify_frozen_channels.py (which the runner checks) differs "
                            f"from the PROTOCOL 12.5.3 values for {differ}: a runner run against that table is "
                            "not LLM channel v1 (12.6.2)")
    return problems


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
    header, _ = read_csv_rows(path)
    extra = None
    if any(c in header for c in LLM_COLS[1:]):
        cf, extra = read_llm_labels(path, name)
    else:
        cf = read_coder_file(path)
    c = build_coder(cf, {}, ref_text, ids)
    prov = {"source": path, "format": cf["format"], "sha256": cf["sha256"],
            "n_labelled": sum(1 for r, v in zip(c["rel"], c["val_all"]) if r is not None and v is not None),
            "missing_from_file": c["missing"], "unknown_ids": len(c["issues"]["unknown_ids"]),
            "issues": {k: len(v) for k, v in c["issues"].items() if v}}
    if extra is not None:
        ok = set(extra.pop("ok_ids"))
        # status ok but no valid label: a defect of the file, reported (the label stays missing)
        extra["status_ok_without_valid_label"] = [
            f for i, f in enumerate(ids) if f in ok and (c["rel"][i] is None or c["val_all"][i] is None)]
        prov.update(extra)
    return name, (c["rel"], c["val_all"], prov)


def machine_vs_gold(eng, g_rel, g_val, m_rel, m_val):
    """kappa of a machine channel with the gold labels on the three dimensions."""
    cond_gold = [gv if gr == "1" and mr == "1" else None for gv, gr, mr in zip(g_val, g_rel, m_rel)]
    return {"relevance": eng.versus(g_rel, m_rel, REL_CATS),
            "valence_conditional": eng.versus(cond_gold, m_val, VAL_CATS),
            "valence_all": eng.versus(g_val, m_val, VAL_CATS)}


# ---------------------------------------------------------------------------
# statistics on one set of fragments (all, or a sensitivity set)
# ---------------------------------------------------------------------------
def fragment_view(coders, idx):
    """The coders restricted to the fragments at positions idx."""
    keys = ("rel", "val_all", "val_cond", "times")
    return {nm: dict({k: [c[k][i] for i in idx] for k in keys},
                     metadata=c["metadata"], eligible=c["eligible"]) for nm, c in coders.items()}


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


def set_statistics(coders, ids, idx, design, gold_rows, chans, n_boot, seed):
    """Every primary (section 6) and secondary (section 7) statistic, and the
    gold summary (section 8), on the fragments at positions idx. Coder
    eligibility and the primary pairs (design) are fixed beforehand."""
    view = fragment_view(coders, idx)
    names, pi, pairs = sorted(coders), design["pi"], design["pairs"]
    eng = Engine(view, [ids[i] for i in idx], n_boot, seed)
    primary = {"pairs": [{"a": a, "b": b, **{d: eng.kappa_summary(a, b, d) for d in DIMS}} for a, b in pairs],
               "mean": {d: eng.mean_kappa(pairs, d) for d in DIMS}}
    primary["gate"] = gate_of(primary["mean"])
    primary["decision"] = decide(primary["gate"])
    sec = {"alpha": {}}
    for label, members in (("eligible", design["eligible"]),
                           ("eligible_plus_partial", design["eligible_plus_partial"])):
        sec["alpha"][label] = ({d: eng.alpha(members, d) for d in DIMS} if len(members) >= 2
                               else {"not_computed": f"{len(members)} coder(s)", "coders": members})
    sec["alpha"]["partial_completers"] = design["partial"]
    sec["pi_vs_each"] = ([{"other": nm, "other_eligible": coders[nm]["eligible"],
                           **{d: eng.kappa_summary(pi, nm, d) for d in DIMS}}
                          for nm in names if nm != pi] if pi else [])
    sec["by_source"] = by_group(eng, view, design["elig_nonpi"], "source")
    sec["by_ui_language"] = by_group(eng, view, design["elig_nonpi"], "ui_language")
    sec["all_pairs"] = [{"a": a, "b": b, "a_eligible": coders[a]["eligible"], "b_eligible": coders[b]["eligible"],
                         **{d: eng.kappa_summary(a, b, d) for d in DIMS}} for a, b in combinations(names, 2)]
    sec["timing"] = {nm: timing_stats(view[nm]["times"]) for nm in names}
    rows = [gold_rows[i] for i in idx]
    g_rel = [g["gold_relevant"] for g in rows]
    g_val = [g["gold_valence"] for g in rows]
    machine = {name: machine_vs_gold(eng, g_rel, g_val, [m_rel[i] for i in idx], [m_val[i] for i in idx])
               for name, (m_rel, m_val, _) in chans.items()}
    return {"n": len(idx), "primary": primary, "secondary": sec,
            "adjudication": gold_summary(rows), "machine_channels": machine}


def exclusion_lists(ids, overrides, proto_text, warnings, strict=False):
    """The two pre-specified exclusion lists (constants, or CLI overrides),
    checked against the reference fragments and the protocol text. strict (the
    reference is the protocol's input set): every listed id must be among the
    reference fragments; otherwise a list wholly outside the reference (another
    fragment set, e.g. synthetic) only warns."""
    defaults = {"anchors": CODEBOOK_ANCHOR_FRAG_IDS, "old_practice": OLD_PRACTICE_PARAPHRASED_FRAG_IDS}
    ref = set(ids)
    out = {}
    for key, label, option in EXCLUSION_LISTS:
        given = overrides.get(key)
        if given is None:
            lst, origin = defaults[key], "constant in ws1_reliability.py (PROTOCOL section 12.3)"
        else:
            lst, origin = given
            d = set(defaults[key])
            warnings.append(f"{option} ({origin}) overrides the pre-specified list of {label}: "
                            f"{len(set(lst) - d)} id(s) added, {len(d - set(lst))} removed")
        present = sorted(f for f in lst if f in ref)
        absent = sorted(set(lst) - ref)
        if absent and (present or strict):
            raise DataError(f"{option}: {len(absent)} of the {len(lst)} {label} are not in the reference "
                            f"fragments, e.g. {absent[:5]}; a wrong id would silently shrink the exclusion")
        if absent:
            warnings.append(f"none of the {len(absent)} {label} is in the reference fragments (a different "
                            "fragment set?): that exclusion removes nothing")
        proto_ids = protocol_list(proto_text, key)
        if proto_ids is None:
            match = None
            warnings.append(f"{os.path.basename(PROTOCOL_FILE)}: no line starting {PROTOCOL_LIST_MARKERS[key]!r} "
                            f"(section 12.3), so the list of {label} could not be checked against it")
        else:
            match = set(proto_ids) == set(lst) and len(proto_ids) == len(set(proto_ids))
            if not match:
                warnings.append(f"the {label} used here ({len(lst)}) differ from section 12.3 of "
                                f"{os.path.basename(PROTOCOL_FILE)} ({len(proto_ids)}): "
                                f"{len(set(lst) - set(proto_ids))} not in the protocol, "
                                f"{len(set(proto_ids) - set(lst))} missing here")
        out[key] = {"label": label, "origin": origin, "overridden": given is not None, "ids": present,
                    "n": len(present), "not_in_reference": absent, "matches_protocol_12_3": match,
                    "n_in_protocol_12_3": None if proto_ids is None else len(proto_ids),
                    "sha256": hashlib.sha256(canonical_json(sorted(lst)).encode("utf-8")).hexdigest()}
    return out


def protocol_list(proto_text, key):
    """frag_ids (in backticks) on the section-12.3 protocol line for one
    exclusion list; None when the line is not there."""
    for line in proto_text.splitlines():
        if line.startswith(PROTOCOL_LIST_MARKERS[key]):
            return FRAG_ID_IN_PROTOCOL.findall(line)
    return None


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
            fragments=None, channels=(), no_pi=False, anchor_ids=None, old_practice_ids=None,
            pi_did_not_code=False):
    """Run sections 5-9 and the section-12 sensitivity analyses. coder_files:
    paths. pi_arg: the PI's coder identity, which must match an input coder; or
    pi_arg=None with no_pi=True (pi_did_not_code is the old name). anchor_ids /
    old_practice_ids: (ids, origin) overriding the pre-specified lists.
    Returns the results dict (JSON-ready) with 'gold_rows' and
    'exclusion_rows' for the CSVs."""
    no_pi = bool(no_pi or pi_did_not_code)
    if no_pi and pi_arg:
        raise DataError("--pi and --no-pi contradict each other; give one")
    if not no_pi and not (pi_arg or "").strip():
        raise DataError("name the PI's coder identity with --pi, or declare --no-pi (the PI did not code)")
    ref_text, ref_src = load_reference(fragments)
    ids = sorted(ref_text)
    n_ref = len(ids)
    meta = meta or {}
    warnings = []
    proto = protocol_info()
    warnings += protocol_warnings(proto)
    input_sha = input_set_sha256(ref_text)
    if input_sha != EVAL_INPUT_SHA256:
        warnings.append(f"reference fragments (sha256 {input_sha[:12]}…) are not the evaluation input set of "
                        f"PROTOCOL section 12.5.3 ({EVAL_INPUT_SHA256[:12]}…)")
    if n_ref != N_PROTOCOL:
        warnings.append(f"reference has {n_ref} fragments, the protocol specifies {N_PROTOCOL}; "
                        f"rule (c) uses {n_ref}")
    if n_boot != BOOT_PROTOCOL:
        warnings.append(f"--boot {n_boot}: the protocol (section 6) specifies {BOOT_PROTOCOL} resamples")
    excl = exclusion_lists(ids, {k: v for k, v in (("anchors", anchor_ids), ("old_practice", old_practice_ids))
                                 if v is not None}, proto["text"], warnings, strict=input_sha == EVAL_INPUT_SHA256)

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
    if no_pi:
        pi = None
        warnings.append("declared with --no-pi: no PI file is among the inputs, so every coder can "
                        "enter the primary pairs, no PI tie-breaks are possible (every tie is "
                        "unresolved) and no PI comparisons are made")
    else:
        pi = resolve_pi(names, pi_arg)
        if pi is None:
            raise DataError(f"--pi {pi_arg!r} matches none of the input coders {names}. The PI's "
                            "coding must never enter the primary kappa (protocol section 6), so the "
                            "run stops. Give the PI's identity as it appears in the inputs (the coder "
                            "column, else the file stem), or --no-pi if the PI did not code.")

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

    # ---- section 6: primary pairs (fixed once, on the full instrument) ----
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
    partial = [nm for nm in names if not coders[nm]["eligible"]
               and coders[nm]["rules"]["c"][0] == FAIL
               and all(coders[nm]["rules"][k][0] == PASS for k in "abd")]
    design = {"pi": pi, "eligible": eligible, "elig_nonpi": elig_nonpi, "partial": partial,
              "eligible_plus_partial": sorted(eligible + partial),
              "pairs": list(combinations(sorted(group), 2))}

    # ---- section 8: gold labels (12.1(b) = first reading) and the sensitivity reading ----
    readings = {name: build_gold(coders, ids, eligible, pi, pi_votes) for name, pi_votes, _ in ADJ_READINGS}
    record = ADJ_READINGS[0][0]
    gold_rows = readings[record]
    if len(elig_nonpi) < 2:
        warnings.append(f"gold labels rest on {len(elig_nonpi)} eligible non-PI coder(s)")

    # ---- machine channels ----
    chans = dictionary_labels(ids, ref_text)
    for spec in channels:
        name, lab = channel_labels(spec, ids, ref_text)
        chans[name] = lab
    if not chans["dictionary_v1"][2]["matches_protocol_frozen"]:
        warnings.append(f"dictionary v1 (ws1_pipeline.py, blob {chans['dictionary_v1'][2]['blob']}) is not "
                        f"the version frozen in PROTOCOL section 12.5.1 (blob {V1_FROZEN_BLOB})")
    if input_sha == EVAL_INPUT_SHA256:
        v1n = chans["dictionary_v1"][2]["n_relevant"]
        if (v1n, n_ref - v1n) != DRAW_STRATA_V1:
            warnings.append(f"dictionary v1 marks {v1n} of {n_ref} relevant; the drawing strata recorded "
                            f"in section 12.1(a) are {DRAW_STRATA_V1[0]} / {DRAW_STRATA_V1[1]}")
    llm_checked = False
    for name, (_, _, prov) in chans.items():
        if prov.get("excluded_status_not_ok"):
            warnings.append(f"channel {name}: {sum(prov['excluded_status_not_ok'].values())} fragment(s) with "
                            f"status_llm other than ok excluded from its comparison "
                            f"{prov['excluded_status_not_ok']}")
        if prov.get("status_ok_without_valid_label"):
            warnings.append(f"channel {name}: {len(prov['status_ok_without_valid_label'])} row(s) with status "
                            "ok but no valid label (left missing)")
        rr = prov.get("run_record")
        if rr is not None:
            if not rr["found"]:
                warnings.append(f"channel {name}: no run record ({' or '.join(rr['looked_for'])}) next to the labels "
                                "file; which run produced these labels cannot be checked (PROTOCOL 12.5.3, 12.6)")
            elif rr.get("error"):
                warnings.append(f"channel {name}: run record {rr['file']} {rr['error']}")
            else:
                if not rr["labels_sha256_matches"]:
                    warnings.append(f"channel {name}: the labels file's sha256 is not the labels_sha256 of its run "
                                    f"record {rr['file']} (run {rr.get('run_id')}): not the labels of that run")
                if not rr["input_set_matches_protocol"]:
                    warnings.append(f"channel {name}: run record {rr['file']} names input set "
                                    f"{rr.get('input_set_sha256')}, not the one of PROTOCOL 12.5.3")
                if rr.get("complete") is not True:
                    warnings.append(f"channel {name}: run record {rr['file']} does not mark the run complete")
                if rr["identity_differs"]:
                    shown = "; ".join(f"{k} {str(rr['identity'][k])[:12]}… (PROTOCOL 12.5.3: "
                                      f"{LLM_V1_IDENTITY[k][:12]}…)" for k in rr["identity_differs"])
                    warnings.append(f"channel {name}: NOT LLM CHANNEL v1 -- run record {rr['file']} (run "
                                    f"{rr.get('run_id')}) carries identities that differ from PROTOCOL 12.5.3: "
                                    f"{shown}. These labels are output of another channel version: they are "
                                    "neither the run of record nor a replicate (12.6.2) and must not be "
                                    "reported as the LLM channel")
            if not llm_checked:
                llm_checked = True
                for p in llm_frozen_consistency(proto["text"]):
                    warnings.append(f"LLM channel v1 identity: {p}")
        ms = prov.get("model_served_counts_ok_rows")
        if ms and len(ms) > 1:
            warnings.append(f"channel {name}: labels were served by more than one model {ms}")
        if prov.get("missing_from_file") and name not in ("dictionary_v0", "dictionary_v1"):
            warnings.append(f"channel {name}: {prov['missing_from_file']} reference fragment(s) not in the file")
    if not channels:
        warnings.append("LLM channel (section 7) not compared: no LLM-channel labels were supplied "
                        "(pass them with --channel LLM=llm_labels.csv)")

    # ---- statistics: all fragments, then the section-12 exclusion sets ----
    sets = {}
    for name, label, drop in FRAGMENT_SETS:
        dropped = set().union(*(excl[k]["ids"] for k in drop)) if drop else set()
        idx = [i for i, f in enumerate(ids) if f not in dropped]
        st = set_statistics(coders, ids, idx, design, gold_rows, chans, n_boot, seed)
        st.update(name=name, label=label, excluded=sorted(dropped), n_excluded=len(dropped))
        sets[name] = st
    full = sets["all"]
    primary = dict(full["primary"], basis=basis, group=sorted(group))
    decision = full["primary"]["decision"]

    adjudication = dict(full["adjudication"], name=record, description=ADJ_READINGS[0][2],
                        voters=[v for v in eligible if v != pi], pi=pi,
                        pi_eligible=coders[pi]["eligible"] if pi else None, sensitivity={})
    if pi and not coders[pi]["eligible"] and adjudication["fragments_with_any_pi_tiebreak"]:
        warnings.append(f"the PI ({pi}) does not meet the inclusion rules but broke ties on "
                        f"{adjudication['fragments_with_any_pi_tiebreak']} fragment(s); section 12.1(b) does not make "
                        "the tie-break depend on the inclusion rules")
    eng_all = Engine(fragment_view(coders, range(n_ref)), ids, n_boot, seed)
    for name, pi_votes, text in ADJ_READINGS[1:]:
        rows = readings[name]
        summ = gold_summary(rows)
        summ.update(name=name, description=text,
                    voters=[v for v in eligible if pi_votes or v != pi],
                    fragments_relevance_differs=sum(g["gold_relevant"] != h["gold_relevant"]
                                                    for g, h in zip(gold_rows, rows)),
                    fragments_valence_differs=sum(g["gold_valence"] != h["gold_valence"]
                                                  for g, h in zip(gold_rows, rows)))
        a_rel = [g["gold_relevant"] for g in rows]
        a_val = [g["gold_valence"] for g in rows]
        summ["machine_channels"] = {cn: machine_vs_gold(eng_all, a_rel, a_val, m_rel, m_val)
                                    for cn, (m_rel, m_val, _) in chans.items()}
        adjudication["sensitivity"][name] = summ
        for g, h in zip(gold_rows, rows):
            g[f"alt_{name}_relevant"] = h["gold_relevant"]
            g[f"alt_{name}_valence"] = h["gold_valence"]
    machine = {name: dict(full["machine_channels"][name], provenance=prov)
               for name, (_, _, prov) in chans.items()}
    anchors, oldp = set(excl["anchors"]["ids"]), set(excl["old_practice"]["ids"])
    for i, g in enumerate(gold_rows):
        g["in_codebook_anchors"] = "yes" if g["frag_id"] in anchors else "no"
        g["in_old_practice_paraphrases"] = "yes" if g["frag_id"] in oldp else "no"
        for name, (m_rel, m_val, _) in chans.items():
            g[f"{name}_relevant"], g[f"{name}_valence"] = m_rel[i], m_val[i]

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
            "practice_set": md["practice_set"]["value"] or md["practice_set"]["from"],
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

    proto_out = {k: v for k, v in proto.items() if k != "text"}
    return {"meta": {"generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "script": "ws1_reliability.py", "script_sha256": sha256_file(os.path.abspath(__file__)),
                     "git_head": (git("rev-parse", "HEAD") or b"").decode().strip() or None,
                     "protocol": proto_out, "codebook": CODEBOOK, "gate": GATE,
                     "bootstrap": {"resamples": n_boot, "seed": seed, "method":
                                   "percentile 95% CI; fragments resampled with replacement from the "
                                   "fragment set analysed; every statistic recomputed on the same resamples; "
                                   "undefined replicates dropped and counted"},
                     "reference": {"path": ref_src, "n": n_ref, "sha256": sha256_file(ref_src),
                                   "input_set_sha256": input_sha,
                                   "is_protocol_input_set": input_sha == EVAL_INPUT_SHA256},
                     "pi_argument": pi_arg, "pi": pi, "no_pi": no_pi},
            "warnings": warnings, "coders": coder_out, "eligible": eligible,
            "primary": primary, "decision": decision, "secondary": full["secondary"],
            "adjudication": adjudication, "machine_channels": machine,
            "sensitivity": {"exclusion_lists": excl,
                            "fragment_sets": {k: v for k, v in sets.items() if k != "all"},
                            "all": {"n": full["n"]}},
            "gold_rows": gold_rows, "exclusion_rows": exclusion_rows}


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


def gate_cell(g):
    if g is None:
        return "—"
    if g["pass"] is None:
        return f"*not assessable* ({g['why']})"
    return f"{'pass' if g['pass'] else '**FAIL**'} ({g['why']})"


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


def ids_short(ids, k=12):
    return (", ".join(ids[:k]) + (f", … ({len(ids)} in all)" if len(ids) > k else "")) if ids else "none"


def stat_rows(st, pi):
    """(label, cell) for every primary and secondary statistic of one fragment
    set, in a fixed order, for the side-by-side sensitivity table."""
    R = [("fragments analysed", str(st["n"]))]
    P, S, A = st["primary"], st["secondary"], st["adjudication"]
    prim = {(p["a"], p["b"]) for p in P["pairs"]}
    for p in P["pairs"]:
        for d in DIMS:
            R.append((f"§6 pair {p['a']} × {p['b']}: {DIM_LABEL[d]}", est(p[d])))
    for d in DIMS:
        R.append((f"§6 mean pairwise κ: {DIM_LABEL[d]}", est(P["mean"][d])))
    for d in GATED:
        R.append((f"§6 gate, {DIM_LABEL[d]}", gate_cell(P["gate"][d])))
    R.append(("gate rule applied to this set (sensitivity only; the decision is §1)", P["decision"]["status"]))
    for label in ("eligible", "eligible_plus_partial"):
        a = S["alpha"][label]
        for d in DIMS:
            R.append((f"§7 α, {label.replace('_', ' ')}: {DIM_LABEL[d]}",
                      est(a) if "not_computed" in a else est(a[d])))
    for r in S["pi_vs_each"]:
        for d in DIMS:
            R.append((f"§7 PI × {r['other']}: {DIM_LABEL[d]}", est(r[d])))
    for key, title in (("by_source", "source"), ("by_ui_language", "interface language")):
        for kind in ("within", "between"):
            for g, v in S[key][kind].items():
                for d in DIMS:
                    R.append((f"§7 by {title}, {kind} {g}: {DIM_LABEL[d]}",
                              est(v) if "not_computed" in v else est(v[d])))
    for r in S["all_pairs"]:
        if (r["a"], r["b"]) in prim or pi in (r["a"], r["b"]):
            continue                        # already listed above
        for d in DIMS:
            R.append((f"§7 other pair {r['a']} × {r['b']}: {DIM_LABEL[d]}", est(r[d])))
    for nm, t in S["timing"].items():
        R.append((f"§7 timing {nm}: median s (n) / share < 3 s",
                  f"{t['median']:g} ({t['n']}) / {t['share_under_3s']:.1%}" if t else "not recorded"))
    for name, mc in st["machine_channels"].items():
        for d in DIMS:
            R.append((f"§7 {name} vs gold: {d.replace('_', ' ')}", est(mc[d])))
    R.append(("§8 PI tie-breaks: relevance / valence", f"{A['pi_tiebreaks_relevance']} / {A['pi_tiebreaks_valence']}"))
    R.append(("§8 unresolved: relevance / valence (gold relevant)",
              f"{A['unresolved_relevance']} / {A['unresolved_valence']}"))
    R.append(("§8 gold relevant / not relevant",
              f"{A['gold_relevant_counts'].get('1', 0)} / {A['gold_relevant_counts'].get('0', 0)}"))
    return R


def write_report(res, path):
    L = []
    m = res["meta"]
    n = m["reference"]["n"]
    L.append("# WS1.0 reliability report\n")
    L.append(f"Generated {m['generated_utc']} by `ws1_reliability.py` · protocol "
             f"{protocol_label(m['protocol'])} · codebook {m['codebook']} · gate κ ≥ {m['gate']:.2f}  ")
    L.append(f"Reference fragments: {n} (`{os.path.basename(m['reference']['path'])}`; input-set sha256 "
             f"{m['reference']['input_set_sha256'][:12]}…, "
             f"{'the' if m['reference']['is_protocol_input_set'] else 'NOT the'} evaluation set of PROTOCOL §12.5.3) · "
             f"bootstrap: {m['bootstrap']['resamples']} resamples, seed {m['bootstrap']['seed']} · "
             f"PI: {m['pi'] or 'did not code (declared with --no-pi)'}\n")
    if res["warnings"]:
        L.append("> **Warnings**")
        for w in res["warnings"]:
            L.append(f"> - {w}")
        L.append("")

    d, p = res["decision"], res["primary"]
    L.append("## 1. Decision (protocol §9)\n")
    L.append(f"**Gate: {d['status']}.** {d['text']}\n")
    L.append(f"Primary pairs: {p['basis']}. Group: {', '.join(p['group']) or '—'}. The decision is taken "
             f"on all {n} fragments; §7 of this report applies the gate rule to the §12.3 sensitivity sets as well.\n")
    L.append("| dimension | mean pairwise κ [95% CI], n per pair | gate ≥ 0.70 |")
    L.append("|---|---|---|")
    for dim in DIMS:
        gs = gate_cell(p["gate"].get(dim)) if dim in GATED else "reported, not gated"
        L.append(f"| {DIM_LABEL[dim]} | {est(p['mean'][dim])} | {gs} |")
    L.append("\nThe gate compares the exact mean of the exact pair κs (rational arithmetic on the "
             "label counts) with 7/10, so a mean of exactly 0.70 passes; the gate column prints as many "
             "decimals as it takes to show the side of 0.70, so a mean of 0.69996 is not shown as 0.700.\n")

    L.append("## 2. Coders and inclusion rules (§5)\n")
    L.append("A coder enters the primary analysis only if all four rules hold; *not assessable* "
             "(data not recorded) counts as not holding. Inclusion is decided on the full instrument "
             "and is not re-decided on the §12.3 sensitivity sets.\n")
    L.append("| coder | PI | format | source | English | practice (1st try) | practice set | completed | "
             "median s (n timed) | < 3 s | (a) | (b) | (c) | (d) | eligible |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
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
                 f"{md['practice_set']['value'] or md['practice_set']['from']} | "
                 f"{c['completed']}/{n} | {ts} | {fast} | "
                 + " | ".join(rule_cell(c["rules"][k]) for k, _ in RULES)
                 + f" | {'**yes**' if c['eligible'] else 'no'} |")
    L.append("")
    excl = [(nm, c) for nm, c in res["coders"].items() if not c["eligible"]]
    if excl:
        L.append("Excluded from the primary analysis (data kept for secondary analyses):\n")
        for nm, c in excl:
            L.append(f"- **{nm}**: " + "; ".join(c["reasons"]))
        L.append("")
    L.append("Rules: " + "; ".join(f"({k}) {t}" for k, t in RULES) + ". Practice set = the id the page "
             "exports for the practice items the coder saw (`untagged` = exported before the id was "
             "recorded).\n")
    cur = [nm for nm, c in res["coders"].items() if c["metadata"]["practice_set"]["value"] == PRACTICE_SET_PROTOCOL]
    other = [f"{nm} ({c['metadata']['practice_set']['value'] or c['metadata']['practice_set']['from']})"
             for nm, c in res["coders"].items() if c["metadata"]["practice_set"]["value"] != PRACTICE_SET_PROTOCOL]
    L.append(f"Practice set `{PRACTICE_SET_PROTOCOL}` (the items the LLM prompt carries; instruction parity, "
             f"PROTOCOL §12.4 item 2 and §12.5.3): {', '.join(cur) or 'none'}. Any other set, `untagged` or not "
             f"recorded: {', '.join(other) or 'none'}.\n")

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
            for x in DIMS:
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
    L.append("## 5. Adjudication and gold labels (§8, as clarified in §12.1(b))\n")
    L.append(f"Reading of record (`{a['name']}`): {a['description']}. \"Majority\" is the plurality "
             "(most votes); a tie for the top count is broken by the PI's label when it is one of the tied "
             "labels, otherwise the fragment is unresolved. Gold relevance 0 → valence `none` (codebook). "
             "The PI's label breaks ties whether or not the PI meets the §5 inclusion rules.\n")
    L.append(f"Voters: {', '.join(a['voters']) or 'none'}; PI (tie-breaks only): "
             + (f"{a['pi']} (meets the inclusion rules: {'yes' if a['pi_eligible'] else 'no'})" if a["pi"]
                else "did not code — every tie is unresolved") + "\n")
    L.append(f"- **PI tie-breaks**: relevance {a['pi_tiebreaks_relevance']}, valence "
             f"{a['pi_tiebreaks_valence']}; fragments with any PI tie-break: "
             f"{a['fragments_with_any_pi_tiebreak']} of {n}")
    L.append(f"- **Unresolved** relevance: {a['unresolved_relevance']} of {n} "
             f"({ids_short(a['unresolved_relevance_ids'])})")
    L.append(f"- **Unresolved** valence where gold relevance is 1: {a['unresolved_valence']} "
             f"({ids_short(a['unresolved_valence_ids'])})")
    L.append(f"- Gold relevance: {a['gold_relevant_counts']}; gold valence: {a['gold_valence_counts']}")
    L.append(f"- Plurality without absolute majority: relevance "
             f"{a['plurality_without_absolute_majority']['relevance']}, valence "
             f"{a['plurality_without_absolute_majority']['valence']}\n")
    L.append("Sensitivity reading of §8 (§12.1(b): the PI votes); its labels are in `gold_labels.csv` as "
             "`alt_<reading>_relevant` / `alt_<reading>_valence`. \"Decided by the PI\" = the gold differs "
             "from what the eligible non-PI coders give on their own (their plurality, unresolved when "
             "tied): in the reading of record these are exactly the PI tie-breaks; when the PI votes they "
             "also include fragments where the PI's vote was pivotal.\n")
    L.append("| reading | voters | gold differs from the reading of record: relevance / valence | unresolved: "
             "relevance / valence | PI tie-breaks: relevance / valence | decided by the PI: relevance / valence |")
    L.append("|---|---|---|---|---|---|")
    for r in [a] + list(a["sensitivity"].values()):
        diff = ("— (reading of record)" if r is a else
                f"{r['fragments_relevance_differs']} / {r['fragments_valence_differs']}")
        L.append(f"| `{r['name']}` | {', '.join(r['voters']) or '—'} | {diff} | {r['unresolved_relevance']} / "
                 f"{r['unresolved_valence']} | {r['pi_tiebreaks_relevance']} / {r['pi_tiebreaks_valence']} | "
                 f"{r['pi_decided_relevance']} / {r['pi_decided_valence']} |")
    L.append("\nStatus counts (reading of record): "
             + ", ".join(f"{k} = {v}" for k, v in a["status_counts"].items()) + "\n")

    L.append("## 6. Machine channels versus gold labels (§7)\n")
    L.append("Disclosure (PROTOCOL §12.2(b), §12.5.1): dictionary v1 is v0 as revised in `7eb5a1e` (the stance "
             "override), made after the dictionary had been compared with 50 labels that the AI co-author, a "
             "Claude model, produced in a chat session on 2026-06-20 (ROADMAP D29), and tuned on those 50 "
             "fragments, which can no longer be identified; v1's agreement with the gold labels may be partly "
             "in-sample. The LLM channel is also a Claude model, and `CODEBOOK.md` v1 and the LLM prompt were "
             "drafted by the AI co-author. Agreement between the dictionary-only and the LLM-only index "
             "(pre-registration A.6, item 3) is therefore not fully independent evidence; the evidence for "
             "each channel is its agreement with the human gold labels below. Fragments whose gold label is "
             "unresolved on a dimension are left out of that dimension's comparison (§12.1(b)).\n")
    for name, mc in res["machine_channels"].items():
        prov = mc["provenance"]
        L.append(f"### {name}\n")
        L.append(f"Source: {prov.get('source')}"
                 + (f"; git check: {prov['git_check']['status']} ({prov['git_check']['detail']})" if "git_check" in prov else "")
                 + (f"; blob {prov['blob']}" if "blob" in prov and "git_check" not in prov else "")
                 + (f"; identical to git HEAD: {prov['matches_git_HEAD']}" if "matches_git_HEAD" in prov else "")
                 + (f"; frozen version of PROTOCOL §12.5.1: {prov['matches_protocol_frozen']}"
                    if "matches_protocol_frozen" in prov else "")
                 + (f"; term lists sha256 {prov['terms_sha256'][:12]}… (PROTOCOL §12.5.2)" if "terms_sha256" in prov else "")
                 + (f"; format {prov['format']}; sha256 {prov['sha256']}" if "format" in prov else "")
                 + (f"; relevant {prov['n_relevant']} of {prov['n_fragments']}" if "n_relevant" in prov else "")
                 + "\n")
        if "status_llm_counts" in prov:
            excl_ids = prov["excluded_status_not_ok_ids"]
            L.append(f"status_llm counts: {prov['status_llm_counts']}. Excluded from this channel's comparison "
                     f"(status not ok): {sum(len(v) for v in excl_ids.values())}"
                     + "".join(f"; {k}: {ids_short(v, 8)}" for k, v in excl_ids.items())
                     + f". Rows with labels but status not ok: {len(prov['labels_present_but_status_not_ok'])}; "
                     f"status ok without a valid label: {len(prov['status_ok_without_valid_label'])}; "
                     f"reference fragments missing from the file: {prov['missing_from_file']}; "
                     f"compared: {prov['n_labelled']}. Served model (ok rows): "
                     f"{prov['model_served_counts_ok_rows'] if prov['model_served_counts_ok_rows'] is not None else 'no model_served column'}.\n")
            rr = prov["run_record"]
            if not rr["found"]:
                L.append(f"Run record: none found ({' or '.join(rr['looked_for'])}); which run produced these labels "
                         "is not checked here.\n")
            elif rr.get("error"):
                L.append(f"Run record {rr['file']}: {rr['error']}.\n")
            else:
                L.append(f"Run record `{rr['file']}` (sha256 {rr['sha256'][:12]}…): run {rr.get('run_id')}, complete "
                         f"{rr.get('complete')}, models served {rr.get('models_served')}, first request "
                         f"{rr.get('first_request_utc')}, last response {rr.get('last_response_utc')}; its "
                         f"labels_sha256 matches this file: {rr['labels_sha256_matches']}; raw log sha256 "
                         f"{(rr.get('raw_log_sha256') or '—')[:12]}…; input set as in PROTOCOL §12.5.3: "
                         f"{rr['input_set_matches_protocol']}; runner, prompt, request specification and input "
                         f"set as written in §12.5.3: {rr['identity_matches_protocol']}"
                         + (f" (**differ: {', '.join(rr['identity_differs'])} -- not LLM channel v1; these "
                            "labels are neither the run of record nor a replicate, §12.6.2**)"
                            if rr["identity_differs"] else "")
                         + ". Whether this is the run of record (§12.6.2: the first complete run of LLM channel "
                         "v1 committed and pushed before the first coder CSV is opened, at a commit at which "
                         "`verify_frozen_channels.py` exits 0) is decided by the commit history, not by this "
                         "script.\n")
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
    if a["sensitivity"]:
        L.append("Machine channels against the gold labels of the sensitivity reading of §8 (κ [95% CI], n):\n")
        L.append("| channel | reading | " + " | ".join(DIM_LABEL[x] for x in DIMS) + " |")
        L.append("|---|---|---|---|---|")
        for name, mc in res["machine_channels"].items():
            L.append(f"| {name} | `{a['name']}` (record) | " + " | ".join(est(mc[x]) for x in DIMS) + " |")
            for r in a["sensitivity"].values():
                L.append(f"| {name} | `{r['name']}` | " + " | ".join(est(r["machine_channels"][name][x]) for x in DIMS) + " |")
        L.append("")

    sens = res["sensitivity"]
    L.append("## 7. Sensitivity analyses: fragment exclusions (PROTOCOL §12.3)\n")
    for key, lst in sens["exclusion_lists"].items():
        mp = {True: "yes", False: "**no**", None: "protocol line not found"}[lst["matches_protocol_12_3"]]
        L.append(f"- {lst['label']}: {lst['n']} fragment(s) ({lst['origin']}; same ids as PROTOCOL §12.3: {mp}; "
                 f"list sha256 {lst['sha256'][:12]}…)")
    L.append("\nDisclosures (PROTOCOL §12.3, §12.4): CODEBOOK.md v1 quotes shortened excerpts of the anchor "
             "fragments (15 in its decision-example tables, one in its rule text), and the PI, whose label breaks "
             "ties in the gold labels, has seen them. Its rule text, which the LLM prompt carries in full, "
             "paraphrases with their codes the claims of seven anchor fragments; the coding page shows two of "
             "those examples, so on the other five the LLM channel and the PI had information the coders who "
             "saw only the page did not (§12.4.1). The 50 fragments the AI co-author labelled in a chat session on 2026-06-20 (ROADMAP D29) "
             "can no longer be identified, so no analysis can leave them out. Inclusion (§5), the primary "
             "pairs (§6) and each fragment's gold label (§8) are fixed on all fragments; the sets below "
             "only remove fragments, and each has its own bootstrap over its fragments (same seed). The "
             "gate is computed on all fragments (§1); the gate rows here are sensitivity results only.\n")
    order = [("all", f"all ({n})")] + [(k, f"{v['label']} ({v['n']})") for k, v in sens["fragment_sets"].items()]
    full_stats = {"n": n, "primary": res["primary"], "secondary": res["secondary"],
                  "adjudication": res["adjudication"], "machine_channels": res["machine_channels"]}
    cols = {"all": dict(stat_rows(full_stats, m["pi"]))}
    for k, v in sens["fragment_sets"].items():
        cols[k] = dict(stat_rows(v, m["pi"]))
    L.append("| statistic | " + " | ".join(lab for _, lab in order) + " |")
    L.append("|---|" + "---|" * len(order))
    for label, _ in stat_rows(full_stats, m["pi"]):
        L.append(f"| {label} | " + " | ".join(cols[k].get(label, "—") for k, _ in order) + " |")
    L.append("\nExcluded fragment ids per set are in `reliability.json` (sensitivity → fragment_sets → excluded) "
             "and as the `in_codebook_anchors` / `in_old_practice_paraphrases` columns of `gold_labels.csv`.\n")

    L.append("## 8. Data quality\n")
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

    L.append("## 9. Method notes and provenance\n")
    L.append("- Cohen's κ: categories = labels observed in the pair; κ undefined when chance "
             "agreement is 1. Valence (both marked relevant) uses fragments both coders marked "
             "relevant with a valid valence; the all-fragments version sets `none` for non-relevant.")
    L.append(f"- CIs: {m['bootstrap']['method']}.")
    L.append("- Gate: mean pairwise κ (point estimate, exact rational arithmetic) ≥ 7/10 on "
             "relevance and on valence (both marked relevant); the PI is never in a primary pair.")
    pr = m["protocol"]
    L.append(f"- Protocol file {pr['file']}: version {pr['version']} ({pr['date']}), sections "
             f"{', '.join(pr['sections']) or '—'}, sha256 {pr['sha256']}, git blob {pr['git_blob']}; identical "
             f"to git HEAD: {pr['matches_git_HEAD']}.")
    L.append("- Sample: drawn with dictionary v1, strata 140 relevant / 160 non-relevant (§12.1(a), a "
             "correction to §2; §2's 136 / 164 is the v0 count on the same fragments).")
    L.append("- Krippendorff's α: nominal metric, coincidence-matrix formula; CI from the same "
             "fragment bootstrap (not Krippendorff's own bootstrap algorithm).")
    L.append(f"- Reference fragments sha256 {m['reference']['sha256']} (file), input set "
             f"{m['reference']['input_set_sha256']}; script sha256 {m['script_sha256']}; "
             f"git HEAD {m['git_head'] or 'unavailable'}.")
    for nm, c in res["coders"].items():
        L.append(f"- {nm}: `{os.path.basename(c['file'])}` sha256 {c['sha256']}; identity from {c['identity_from']}")
    L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def strip_private(obj):
    """Drop internal keys (leading underscore) before writing JSON/CSV."""
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list):
        return [strip_private(v) for v in obj]
    return obj


def write_outputs(res, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    paths = {k: os.path.join(out_dir, f) for k, f in (
        ("report", "reliability_report.md"), ("json", "reliability.json"),
        ("gold", "gold_labels.csv"), ("exclusions", "exclusions.csv"))}
    with open(paths["gold"], "w", newline="", encoding="utf-8") as fh:
        rows = strip_private(res["gold_rows"])
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows({k: ("" if v is None else v) for k, v in r.items()} for r in rows)
    with open(paths["exclusions"], "w", newline="", encoding="utf-8") as fh:
        rows = res["exclusion_rows"]
        if rows:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    out = strip_private({k: v for k, v in res.items() if k not in ("gold_rows", "exclusion_rows")})
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
                     "an input coder, otherwise the run stops with a non-zero exit")
    who.add_argument("--no-pi", "--pi-did-not-code", dest="no_pi", action="store_true",
                     help="declare that no PI file is among the inputs (every gold tie is then unresolved)")
    ap.add_argument("--meta", help="CSV: coder,source,english_level,practice_correct,practice_n")
    ap.add_argument("--boot", type=int, default=BOOT_PROTOCOL, help="bootstrap resamples (protocol: 1000)")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--fragments", help="reference fragments (default: coding_sample.csv, else ws1_survey.html)")
    ap.add_argument("--channel", action="append", default=[],
                    help="extra machine channel NAME=path.csv: llm_labels.csv of ws1_llm_channel.py "
                         "(frag_id, relevant_llm, valence_llm, status_llm[, model_served]; only status ok is compared) "
                         "or the coder columns frag_id, human_relevant_0_1, human_valence_minus_plus_none")
    ap.add_argument("--anchor-ids", help="override CODEBOOK_ANCHOR_FRAG_IDS (PROTOCOL section 12.3 (a)): a file "
                    "of frag_ids (one per line, # comments) or a comma-separated list")
    ap.add_argument("--old-practice-ids", help="override OLD_PRACTICE_PARAPHRASED_FRAG_IDS (PROTOCOL "
                    "section 12.3 (b)): a file of frag_ids or a comma-separated list")
    a = ap.parse_args(argv)
    if a.boot < 0:
        ap.error("--boot must be >= 0")
    try:
        res = analyse(a.coder_csv, a.pi, read_meta(a.meta) if a.meta else None,
                      a.boot, a.seed, a.fragments, a.channel, no_pi=a.no_pi,
                      anchor_ids=read_id_list(a.anchor_ids, "--anchor-ids") if a.anchor_ids is not None else None,
                      old_practice_ids=(read_id_list(a.old_practice_ids, "--old-practice-ids")
                                        if a.old_practice_ids is not None else None))
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
          f"{adj['pi_tiebreaks_valence']}; unresolved relevance {adj['unresolved_relevance']}, "
          f"valence (gold relevant) {adj['unresolved_valence']}")
    for name, st in res["sensitivity"]["fragment_sets"].items():
        g = st["primary"]["gate"]
        print(f"  sensitivity {name} ({st['n']} fragments): mean kappa relevance "
              f"{f3(st['primary']['mean']['relevance']['value']) if st['primary']['mean']['relevance'] else '—'}, "
              f"valence {f3(st['primary']['mean']['valence_conditional']['value']) if st['primary']['mean']['valence_conditional'] else '—'}"
              f" -> {st['primary']['decision']['status']}")
    for w in res["warnings"]:
        print("  ! " + w)
    print("-> " + ", ".join(paths.values()))


if __name__ == "__main__":
    main()
