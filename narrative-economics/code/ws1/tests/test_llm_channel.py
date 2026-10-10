#!/usr/bin/env python3
"""
tests/test_llm_channel.py - validation of ws1_llm_channel.py and
verify_frozen_channels.py without an API key and without network.

Runs with plain python3 (pytest optional):
    python3 tests/test_llm_channel.py            # or: python3 -m pytest tests/
Two kinds of client stand in for the API:
  - a fake client object (no SDK needed) for the 300-fragment run, resume,
    retry and reply-validation logic;
  - the real anthropic SDK with a mocked HTTP transport (httpx2.MockTransport)
    for the request body the SDK actually sends and the SDK's own error
    classes. These tests are reported as SKIP, never silently passed, when the
    anthropic package is not installed.
Every reply here is SYNTHETIC (scripted in this file); nothing in this file is
an LLM label. All outputs go to temporary directories, removed at exit.
"""
import atexit, copy, csv, io, json, os, re, shutil, subprocess, sys, tempfile, unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout

sys.dont_write_bytecode = True
TESTS = os.path.dirname(os.path.abspath(__file__))
WS1 = os.path.dirname(TESTS)
sys.path.insert(0, WS1)
import ws1_llm_channel as L  # noqa: E402
import ws1_pipeline  # noqa: E402
import verify_frozen_channels as V  # noqa: E402
import make_artifact_page as PAGE  # noqa: E402

FRAGS, FRAG_SRC = L.load_fragments(os.path.join(WS1, "coding_sample.csv"), os.path.join(WS1, "ws1_survey.html"))
FRAGS = L.prepare_fragments(FRAGS)
PROMPT_TEXT, PROMPT_SHA = L.read_prompt()
IDENT = L.identity(PROMPT_SHA, FRAGS)
CTX = dict(IDENT, run_id="testrun")
_TMP = []


@atexit.register
def _cleanup():
    for d in _TMP:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------
def message(text, stop="end_turn", model=L.MODEL, usage=None):
    """A Messages API response body (thinking block first, as on this model)."""
    content = [{"type": "thinking", "thinking": "", "signature": "sig"}]
    if text is not None:
        content.append({"type": "text", "text": text})
    return {"id": "msg_test", "type": "message", "role": "assistant", "model": model, "content": content,
            "stop_reason": stop, "stop_sequence": None, "stop_details": None,
            "usage": usage or {"input_tokens": 100, "output_tokens": 40,
                               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1200}}


class FakeResponse:
    def __init__(self, body, request_id="req_test"):
        self.body, self._request_id = body, request_id

    def to_dict(self):
        return copy.deepcopy(self.body)


class FakeAPIError(Exception):
    def __init__(self, status_code, headers=None):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        self.response = type("R", (), {"headers": headers or {}})()


class FakeClient:
    """messages.create(**kw) -> script(kw, call_number) (a response, or an exception to raise)."""
    def __init__(self, script):
        outer = self
        self.calls = []

        class Messages:
            def create(self, **kw):
                outer.calls.append(kw)
                out = script(kw, len(outer.calls))
                if isinstance(out, Exception):
                    raise out
                return out
        self.messages = Messages()


def fragment_of(kw):
    m = re.fullmatch(r"Code this fragment\.\n\n<fragment>\n(.*)\n</fragment>", kw["messages"][0]["content"], re.S)
    assert m, "user message does not follow USER_TEMPLATE"
    return m.group(1)


def dictionary_reply(kw, n):
    """Synthetic 'LLM' = the dictionary's labels, so expected outputs are known."""
    *_, rel, val = ws1_pipeline.classify(fragment_of(kw))
    return FakeResponse(message(json.dumps({"relevant": int(rel), "valence": val})))


def expected_labels():
    out = {}
    for f in FRAGS:
        *_, rel, val = ws1_pipeline.classify(f["text"])
        out[f["id"]] = (str(int(rel)), val)
    return out


def quiet(fn, *a, **kw):
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
        rc = fn(*a, **kw)
    return rc, out.getvalue(), err.getvalue()


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.reader(fh)
        return next(r), list(r)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def tmp():
    d = tempfile.mkdtemp(prefix="llmch_")
    _TMP.append(d)
    return d


def paths(d):
    return {n: os.path.join(d, n) for n in ("llm_labels.csv", "llm_labels_run.json", "log.jsonl", "coder.csv")}


def skip(msg):
    raise unittest.SkipTest(msg)


def need_sdk():
    try:
        import anthropic, httpx2  # noqa: F401
    except ImportError as e:
        skip(f"anthropic SDK not installed ({e}); pip install anthropic")


def expect_abort(fn, *needles):
    try:
        fn()
    except L.ChannelAbort as e:
        for n in needles:
            assert n in str(e), (n, str(e))
        return str(e)
    raise AssertionError("expected ChannelAbort")


def classify_one(client, frag=None, sleeps=None, log=None, ctx=None):
    log = log or os.path.join(tmp(), "log.jsonl")
    import random
    rec = L.classify_fragment(client, frag or FRAGS[0], PROMPT_TEXT, ctx or CTX, log,
                              sleep=(sleeps.append if sleeps is not None else (lambda s: None)),
                              rng=random.Random(0))
    return rec, quiet(L.read_log, log)[0]


def words(t):
    return re.findall(r"[a-z0-9']+", t.lower().replace("’", "'").replace("‘", "'"))


def grams(t, n=5):
    w = words(t)
    return {" ".join(w[k:k + n]) for k in range(len(w) - n + 1)}


# ---------------------------------------------------------------------------
# frozen identity (PROTOCOL 12.5)
# ---------------------------------------------------------------------------
def test_verify_script_passes_on_frozen_files():
    r = subprocess.run([sys.executable, os.path.join(WS1, "verify_frozen_channels.py")],
                       capture_output=True, text=True, cwd=tempfile.gettempdir())
    assert r.returncode == 0, r.stdout + r.stderr
    n = len(r.stdout.strip().split("\n")) - 1
    assert n == 19 and r.stdout.count("OK          ") == n and "FAIL" not in r.stdout, r.stdout
    assert "all 19 checks passed" in r.stdout
    assert "every frag_id written in PROTOCOL_WS1.0.md section 12 is among the 300" in r.stdout
    assert "no run record of LLM channel v1 yet, nothing to check" in r.stdout      # none committed yet


def run_record_check(folder):
    """(status, detail) of the verifier's run-record check on the records in folder."""
    old = V.RUN_RECORD_DIR
    V.RUN_RECORD_DIR = folder
    try:
        res = V.checks()
    finally:
        V.RUN_RECORD_DIR = old
    hits = [(s, got) for label, s, got, _ in res if label.startswith("run records of LLM channel v1")]
    assert len(hits) == 1, res
    return hits[0]


def test_verify_checks_the_run_records_of_the_channel():
    """PROTOCOL 12.6.2: the run of record is committed at a commit at which the verifier
    exits 0, so the verifier checks every run record of channel v1 next to it: the four
    identities must be the FROZEN values (written in section 12) and labels_sha256 the
    sha256 of its labels file. A record made by a runner whose FROZEN table was edited
    to match it fails here, because this script's FROZEN must also be in section 12."""
    d = tmp()
    p = paths(d)
    rc, _, err = quiet(L.main, ["--out", p["llm_labels.csv"], "--log", p["log.jsonl"]],
                       client=FakeClient(dictionary_reply))
    assert rc == 0, err
    status, got = run_record_check(d)
    assert status == "OK" and "1 checked ['llm_labels_run.json']" in got, got
    with open(p["llm_labels_run.json"], encoding="utf-8") as fh:
        rec = json.load(fh)

    def write(name, r):
        with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
            json.dump(r, fh)
    write("llm_labels_run.json", dict(rec, runner_sha256="0" * 64, spec_sha256="1" * 64))
    status, got = run_record_check(d)
    assert status == "FAIL" and "runner_sha256, spec_sha256 differ from FROZEN" in got, got
    write("llm_labels_run.json", rec)
    with open(p["llm_labels.csv"], "a", encoding="utf-8") as fh:
        fh.write("\n")
    status, got = run_record_check(d)
    assert status == "FAIL" and "labels_sha256 is not the sha256 of llm_labels.csv" in got, got
    os.remove(p["llm_labels.csv"])
    status, got = run_record_check(d)
    assert status == "FAIL" and "its labels file 'llm_labels.csv' is not next to it" in got, got
    os.remove(p["llm_labels_run.json"])
    write("llm_labels_v2_run.json", dict(rec, channel="ws1-llm-channel-v2", runner_sha256="0" * 64))
    status, got = run_record_check(d)                    # another channel version is not a v1 record
    assert status == "OK" and "not checked: ['llm_labels_v2_run.json']" in got, got
    write("llm_labels_rep2_run.json", "not an object")
    status, got = run_record_check(d)
    assert status == "FAIL" and "llm_labels_rep2_run.json: not a JSON object" in got, got


def test_verify_checks_every_frag_id_in_section_12():
    """A frag_id written anywhere in section 12 (e.g. a disclosure in 12.4) must be one of the 300."""
    d = tmp()
    with open(V.PROTOCOL, encoding="utf-8") as fh:
        text = fh.read()
    changed = os.path.join(d, "PROTOCOL_WS1.0.md")
    with open(changed, "w", encoding="utf-8") as fh:
        fh.write(text.replace("`66zEFbmgQ5I_018`", "`66zEFbmgQ5I_918`"))
    old = V.PROTOCOL
    V.PROTOCOL = changed
    try:
        res = V.checks()
    finally:
        V.PROTOCOL = old
    hit = [(s, got) for label, s, got, _ in res if label.startswith("every frag_id written")]
    assert hit == [("FAIL", "90 distinct, not among the 300: ['66zEFbmgQ5I_918']")], hit


def test_verify_script_fails_on_any_change_and_reports_unchecked():
    saved = copy.deepcopy(V.FROZEN), copy.deepcopy(V.SENSITIVITY_SETS)
    try:
        for k in saved[0]:
            V.FROZEN[k] = "0" * len(saved[0][k])
            rc, out, _ = quiet(V.main)
            assert rc == 1 and "FAIL" in out, k
            V.FROZEN[k] = saved[0][k]
        V.SENSITIVITY_SETS["codebook_anchors"] = saved[1]["codebook_anchors"][:-1]
        rc, out, _ = quiet(V.main)
        assert rc == 1 and "codebook_anchors" in out
        V.SENSITIVITY_SETS["codebook_anchors"] = saved[1]["codebook_anchors"]
        old_git = V.git_show
        V.git_show = lambda rev_path: None                     # no git history (e.g. an OSF download)
        try:
            rc, out, _ = quiet(V.main)
        finally:
            V.git_show = old_git
        assert rc == 2 and out.count("NOT CHECKED") == 3 and "FAIL" not in out
        rc, out, _ = quiet(V.main)
        assert rc == 0
    finally:
        V.FROZEN.clear()
        V.FROZEN.update(saved[0])
        V.SENSITIVITY_SETS.clear()
        V.SENSITIVITY_SETS.update(saved[1])


def test_runner_reads_the_frozen_values_of_the_verify_script():
    assert L.frozen_table() == V.FROZEN
    for k, fk in L.FROZEN_KEYS.items():
        assert IDENT[k] == V.FROZEN[fk], k
    assert L.check_frozen(IDENT) == IDENT


def test_runner_refuses_any_identity_change():
    d = tmp()
    log = os.path.join(d, "log.jsonl")

    def dry(*extra):
        return quiet(L.main, ["--dry-run", "--log", log, "--out", os.path.join(d, "o.csv")] + list(extra))

    # prompt bytes
    changed = os.path.join(d, "llm_channel_prompt_v1.txt")
    with open(changed, "w", encoding="utf-8") as fh:
        fh.write(PROMPT_TEXT + " ")
    old = L.PROMPT_FILE, L.EFFORT, L.RUNNER_FILE, L.FROZEN_TABLE_FILE
    try:
        L.PROMPT_FILE = changed
        rc, out, err = dry()
        assert rc == 2 and "llm_channel_prompt_v1.txt (system prompt)" in err, err
        L.PROMPT_FILE = old[0]
        # request specification (a parameter)
        L.EFFORT = "medium"
        rc, out, err = dry()
        assert rc == 2 and "request specification" in err and "(system prompt)" not in err, err
        L.EFFORT = old[1]
        # runner file: parser, label mapping, outputs are all in it
        runner = os.path.join(d, "ws1_llm_channel.py")
        src = read_bytes(old[2]).replace(b'return "ok", 0, "none", {"raw_valence": val}, True',
                                         b'return "ok", 0, val, {"raw_valence": val}, True')
        assert src != read_bytes(old[2])
        with open(runner, "wb") as fh:
            fh.write(src)
        L.RUNNER_FILE = runner
        rc, out, err = dry()
        assert rc == 2 and "ws1_llm_channel.py (runner" in err, err
        L.RUNNER_FILE = old[2]
        # frozen table unreadable
        L.FROZEN_TABLE_FILE = os.path.join(d, "missing.py")
        rc, out, err = dry()
        assert rc == 2 and "cannot read the frozen values" in err, err
        L.FROZEN_TABLE_FILE = old[3]
    finally:
        L.PROMPT_FILE, L.EFFORT, L.RUNNER_FILE, L.FROZEN_TABLE_FILE = old
    # input set: one text changed by one character, or one fragment missing
    for variant in ("edited", "299"):
        cs = os.path.join(d, f"sample_{variant}.csv")
        rows = [[f["id"], f["text"], "", ""] for f in FRAGS]
        if variant == "edited":
            rows[17][1] = rows[17][1] + "."
        else:
            rows = rows[1:]
        with open(cs, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none"])
            w.writerows(rows)
        rc, out, err = dry("--fragments", cs)
        assert rc == 2 and "input set (the 300 frag_id + text)" in err, err
        # a real run is refused before any request
        client = FakeClient(dictionary_reply)
        rc, out, err = quiet(L.main, ["--fragments", cs, "--log", log, "--out", os.path.join(d, "o.csv")],
                             client=client)
        assert rc == 2 and client.calls == [], err
    # the same 300 from a CSV give the same input set
    cs = os.path.join(d, "sample_same.csv")
    with open(cs, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["frag_id", "text", "human_relevant_0_1", "human_valence_minus_plus_none"])
        w.writerows([[f["id"], f["text"], "", ""] for f in reversed(FRAGS)])
    rc, out, err = dry("--fragments", cs)
    assert rc == 0, err
    for n in ("log.jsonl", "o.csv", "o_run.json"):                    # dry runs and refused runs write nothing
        assert not os.path.exists(os.path.join(d, n)), n


# ---------------------------------------------------------------------------
# the prompt: no evaluation fragment, codebook rules, instruction parity (12.5.3)
# ---------------------------------------------------------------------------
def test_prompt_contains_no_evaluation_fragment():
    """No evaluation fragment is quoted: no 5-word sequence of any of the 300 fragments, no frag_id,
    and nothing of the CODEBOOK.md decision-example tables (excerpts of evaluation fragments) is in
    the prompt. (Paraphrased claims are a different matter: see the next test and PROTOCOL 12.4.1.)"""
    assert len(FRAGS) == 300
    pg = grams(PROMPT_TEXT)
    hits = sorted({g for f in FRAGS for g in grams(f["text"]) & pg})
    assert not hits, hits
    assert not [f["id"] for f in FRAGS if f["id"] in PROMPT_TEXT]
    with open(os.path.join(WS1, "CODEBOOK.md"), encoding="utf-8") as fh:
        rows = [ln for ln in fh.read().split("\n") if ln.startswith('| "')]
    assert len(rows) == 17
    cells = [re.sub(r"\*\*", "", r.split("|")[1]) for r in rows]
    hits = sorted({g for c in cells for g in grams(c) & pg})
    assert not hits, hits


def test_prompt_paraphrases_of_anchor_claims_are_disclosed():
    """The CODEBOOK v1 rule text the prompt carries paraphrases, with their codes, the claims of
    seven anchor fragments (PROTOCOL 12.4.1). Each is named in 12.4.1 and is in the 12.3(a) list;
    the coding page's (English) rule reference shows two of the examples and none of the other five."""
    para = [ln for ln in V.section12().split("\n") if ln.startswith("1. *Codebook anchors.*")]
    assert len(para) == 1
    disclosed = {"moiuHRHB6nE_042": "is the excuse for layoffs",
                 "66zEFbmgQ5I_001": "firms having to rehire the people they let go",
                 "66zEFbmgQ5I_027": "AI costing more than the worker it was meant to replace",
                 "66zEFbmgQ5I_020": "the layoff narrative being called a lie",
                 "IUBo9dnZM3g_011": "ordinary cost-cutting for which AI serves as a pretext",
                 "66zEFbmgQ5I_033": "whether AI is truly the cause or merely an excuse, and leaving that open",
                 "66zEFbmgQ5I_007": "some number of employees were laid off but contains no AI"}
    for fid, phrase in disclosed.items():
        assert f"`{fid}`" in para[0] and fid in V.SENSITIVITY_SETS["codebook_anchors"], fid
        assert phrase in PROMPT_TEXT, phrase
    assert "seven anchor fragments" in para[0] and "the other five are in `CODEBOOK.md` and in the prompt" in para[0]
    ref = PAGE.I18N["en"]["ref.plus.d"]
    assert "had to rehire" in ref and "AI costs more than the worker" in ref
    page_ref = " ".join(v for k, v in PAGE.I18N["en"].items() if k.startswith(("ref.", "q1.", "q2.")))
    for phrase in ("excuse for layoffs", "lie", "pretext", "cost-cutting", "laid off"):
        assert not re.search(r"\b" + phrase + r"\b", page_ref, re.I), phrase


def test_prompt_has_instruction_parity_with_the_coding_page():
    """The worked examples are the page's 8 practice items, with the page's answers and English
    explanations verbatim, in the "Codebook answer: ..." form the page shows after each item."""
    blocks = V.practice_blocks(PAGE)
    assert len(blocks) == 8 == len(PAGE.PRACTICE)
    for k, b in enumerate(blocks, 1):
        assert f"Practice item {k}\n" + b in PROMPT_TEXT, k
    assert PROMPT_TEXT.count("Practice item ") == 8 and PROMPT_TEXT.count("Codebook answer: ") == 8
    for it, why in zip(PAGE.PRACTICE, PAGE.I18N["en"]["practice.why"]):
        assert PROMPT_TEXT.count(it["text"]) == 1 and PROMPT_TEXT.count(why) == 1
    assert PAGE.PRACTICE_SET == V.FROZEN["practice_set"]
    assert PROMPT_TEXT.index("WORKED EXAMPLES") < PROMPT_TEXT.index("OUTPUT\n")


def test_prompt_carries_the_codebook_v1_rules():
    t = PROMPT_TEXT
    for needle in ("an AI / automation referent", "a labor referent", "the fragment connects the two",
                   "two-token rule is strict", 'Debunking destruction is "plus", not "minus"',
                   'Uncertainty about the cause is "none", not "minus"', '"mixed"', "If relevant = 0",
                   '{"relevant": 0 or 1, "valence": "minus" | "plus" | "mixed" | "none"}'):
        assert needle in t, needle
    assert "\r" not in t and t.endswith("\n")
    assert read_bytes(L.PROMPT_FILE).decode("utf-8") == t


# ---------------------------------------------------------------------------
# dry run
# ---------------------------------------------------------------------------
def test_dry_run_prints_exact_request_count_and_estimate():
    d = tmp()
    p = paths(d)
    env_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        rc, out, err = quiet(L.main, ["--dry-run", "--log", p["log.jsonl"], "--out", p["llm_labels.csv"]])
    finally:
        if env_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = env_key
    assert rc == 0, err
    first = FRAGS[0]
    start = out.index("--- exact request")
    body = json.loads(out[out.index("{", start):out.index("\n--- estimate ---")])
    assert body == L.build_request(PROMPT_TEXT, first["text"])
    assert body["system"][0]["text"] == PROMPT_TEXT and fragment_of(body) == first["text"]
    assert "new run, 0 fragment(s) already final -> 300 to send" in out and "requests: 300" in out and "ASSUME" in out
    assert out.count("(frozen: OK)") == 4
    assert os.listdir(d) == []


def test_run_without_key_refuses_and_writes_nothing():
    d = tmp()
    p = paths(d)
    env_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        rc, out, err = quiet(L.main, ["--log", p["log.jsonl"], "--out", p["llm_labels.csv"]])
    finally:
        if env_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = env_key
    assert rc == 2 and "ANTHROPIC_API_KEY" in err
    assert os.listdir(d) == []


# ---------------------------------------------------------------------------
# mocked run over all 300 fragments
# ---------------------------------------------------------------------------
def test_full_mock_run_one_fragment_per_request():
    d = tmp()
    p = paths(d)
    client = FakeClient(dictionary_reply)
    rc, stdout, err = quiet(L.main, ["--out", p["llm_labels.csv"], "--log", p["log.jsonl"],
                                     "--coder-format", p["coder.csv"]], client=client)
    assert rc == 0, err
    assert len(client.calls) == 300
    sent = Counter()
    for kw in client.calls:
        assert set(kw) == {"model", "max_tokens", "thinking", "output_config", "system", "messages"}
        assert kw["model"] == "claude-opus-5-5" and kw["max_tokens"] == L.MAX_TOKENS
        assert kw["output_config"]["effort"] == "low" and kw["thinking"] == {"type": "adaptive"}
        assert kw["system"][0]["text"] == PROMPT_TEXT and len(kw["messages"]) == 1
        sent[fragment_of(kw)] += 1
    assert sorted(sent) == sorted(f["text"] for f in FRAGS) and set(sent.values()) == {1}
    head, rows = read_csv(p["llm_labels.csv"])
    assert head == ["frag_id", "relevant_llm", "valence_llm", "status_llm", "model_served"]
    assert [r[0] for r in rows] == sorted(f["id"] for f in FRAGS)
    exp = expected_labels()
    assert all((r[1], r[2]) == exp[r[0]] and r[3] == "ok" and r[4] == L.MODEL for r in rows)
    head2, rows2 = read_csv(p["coder.csv"])
    assert head2 == ["frag_id", "human_relevant_0_1", "human_valence_minus_plus_none"]
    assert rows2 == [r[:3] for r in rows]
    recs = L.read_log(p["log.jsonl"])
    att = [r for r in recs if r["type"] == "attempt"]
    run_id = recs[0]["run_id"]
    assert recs[0]["type"] == "run_start" and recs[-1]["type"] == "run_end" and recs[-1]["complete"] is True
    assert re.fullmatch(r"[0-9a-f]{32}", run_id) and all(r["run_id"] == run_id for r in recs)
    assert len(att) == 300 and all(r["final"] and r["status"] == "ok" for r in att)
    for r in att:
        assert (r["runner_sha256"], r["prompt_sha256"], r["spec_sha256"]) == (
            IDENT["runner_sha256"], PROMPT_SHA, IDENT["spec_sha256"])
        assert r["model_served"] == L.MODEL and r["request_id"] == "req_test" and r["usage"]["output_tokens"] == 40
        assert r["request"]["system"][0]["text"] == L.prompt_ref(PROMPT_SHA)    # prompt by hash, not 300 copies
        assert r["ts_request"] <= r["ts_response"] and r["ts_request"].endswith("+00:00")
    assert recs[0]["input_set_sha256"] == V.FROZEN["input_set_sha256"] and recs[0]["n_fragments"] == 300
    with open(p["llm_labels_run.json"], encoding="utf-8") as fh:
        rr = json.load(fh)
    assert rr["run_id"] == run_id and rr["complete"] is True and rr["status_counts"] == {"ok": 300}
    assert rr["labels_sha256"] == L.sha256_bytes(read_bytes(p["llm_labels.csv"]))
    assert rr["raw_log_sha256"] == L.sha256_bytes(read_bytes(p["log.jsonl"]))
    for k, fk in L.FROZEN_KEYS.items():
        assert rr[k] == V.FROZEN[fk], k
    assert rr["models_served"] == [L.MODEL] and rr["attempts"] == 300 and rr["invocations"] == 1
    assert rr["labels_file"] == "llm_labels.csv" and rr["raw_log_file"] == "log.jsonl"
    assert d not in json.dumps(rr)                                    # no local paths in the committed record
    assert f"sha256(llm_labels.csv) = {rr['labels_sha256']}" in stdout and "COMPLETE" in stdout


def test_resume_after_abort_sends_only_the_rest_and_complete_log_is_frozen():
    d = tmp()
    p = paths(d)
    args = ["--out", p["llm_labels.csv"], "--log", p["log.jsonl"]]

    def dies_after_40(kw, n):
        return FakeAPIError(400) if n > 40 else dictionary_reply(kw, n)
    c1 = FakeClient(dies_after_40)
    rc, stdout, err = quiet(L.main, args, client=c1)
    assert rc == 2 and "non-retryable" in err and "INCOMPLETE" in stdout
    head, rows = read_csv(p["llm_labels.csv"])
    assert Counter(r[3] for r in rows) == {"ok": 40, "pending": 260}
    run_id = L.read_log(p["log.jsonl"])[0]["run_id"]
    c2 = FakeClient(dictionary_reply)
    rc, stdout, err = quiet(L.main, args, client=c2)
    assert rc == 0 and len(c2.calls) == 260 and "COMPLETE" in stdout
    sent_first = {fragment_of(k) for k in c1.calls[:40]}
    assert not sent_first & {fragment_of(k) for k in c2.calls}
    recs = L.read_log(p["log.jsonl"])
    assert {r["run_id"] for r in recs} == {run_id}
    assert len(L.final_records(recs, FRAGS, dict(IDENT, run_id=run_id))) == 300
    head, rows = read_csv(p["llm_labels.csv"])
    exp = expected_labels()
    assert all((r[1], r[2]) == exp[r[0]] for r in rows)
    with open(p["llm_labels_run.json"], encoding="utf-8") as fh:
        rr = json.load(fh)
    assert rr["invocations"] == 2 and rr["attempts"] == 301 and rr["complete"] is True
    # a complete log is not appended to again; labels and run record are reproduced byte for byte
    before = {k: read_bytes(v) for k, v in p.items() if k != "coder.csv"}
    c3 = FakeClient(dictionary_reply)
    rc, stdout, _ = quiet(L.main, args, client=c3)
    assert rc == 0 and "0 to send" in stdout and c3.calls == []
    assert before == {k: read_bytes(v) for k, v in p.items() if k != "coder.csv"}


def test_replicate_cannot_overwrite_the_run_record_of_another_run():
    d = tmp()
    p = paths(d)
    rc, _, err = quiet(L.main, ["--out", p["llm_labels.csv"], "--log", p["log.jsonl"]],
                       client=FakeClient(dictionary_reply))
    assert rc == 0, err
    before = read_bytes(p["llm_labels.csv"]), read_bytes(p["llm_labels_run.json"])
    client = FakeClient(dictionary_reply)
    rc, _, err = quiet(L.main, ["--out", p["llm_labels.csv"], "--log", os.path.join(d, "log2.jsonl")],
                       client=client)
    assert rc == 2 and "replicate" in err and client.calls == []
    assert before == (read_bytes(p["llm_labels.csv"]), read_bytes(p["llm_labels_run.json"]))
    assert not os.path.exists(os.path.join(d, "log2.jsonl"))
    rc, _, err = quiet(L.main, ["--out", os.path.join(d, "rep2.csv"), "--log", os.path.join(d, "log2.jsonl")],
                       client=FakeClient(dictionary_reply))
    assert rc == 0, err
    with open(os.path.join(d, "rep2_run.json"), encoding="utf-8") as fh:
        rep = json.load(fh)
    assert rep["run_id"] != json.loads(before[1])["run_id"]


def test_log_from_another_run_identity_or_input_is_refused():
    d = tmp()
    log = os.path.join(d, "log.jsonl")
    rec, _ = classify_one(FakeClient(dictionary_reply), log=log)
    for field, needle in (("spec_sha256", "another spec_sha256"), ("runner_sha256", "another runner_sha256"),
                          ("prompt_sha256", "another prompt_sha256"), ("run_id", "belongs to run")):
        bad_log = os.path.join(d, f"bad_{field}.jsonl")
        L.append_log(bad_log, rec)
        L.append_log(bad_log, dict(rec, **{field: "0" * 64}, frag_id=FRAGS[1]["id"],
                                   fragment_sha256=L.sha256_bytes(FRAGS[1]["text"].encode())))
        expect_abort(lambda: L.final_records(L.read_log(bad_log), FRAGS, CTX), needle)
    log2 = os.path.join(d, "log2.jsonl")
    L.append_log(log2, dict(rec, fragment_sha256="0" * 64))
    expect_abort(lambda: L.final_records(L.read_log(log2), FRAGS, CTX), "fragment text")
    log3 = os.path.join(d, "log3.jsonl")
    L.append_log(log3, rec)
    L.append_log(log3, rec)
    expect_abort(lambda: L.final_records(L.read_log(log3), FRAGS, CTX), "two final records")


def test_torn_record_is_skipped_and_log_stays_appendable():
    d = tmp()
    log = os.path.join(d, "log.jsonl")
    rec, _ = classify_one(FakeClient(dictionary_reply), log=log)
    with open(log, "a", encoding="utf-8") as fh:
        fh.write('{"type": "attempt", "frag_')               # crash mid-write
    recs, _, err = quiet(L.read_log, log)
    assert len(recs) == 1 and recs[0]["frag_id"] == rec["frag_id"] and "line 2" in err
    rec2, _ = classify_one(FakeClient(dictionary_reply), frag=FRAGS[1], log=log)
    recs, _, err = quiet(L.read_log, log)
    assert [r["frag_id"] for r in recs] == [FRAGS[0]["id"], FRAGS[1]["id"]] and "line 2" in err
    assert len(L.final_records(recs, FRAGS, CTX)) == 2


# ---------------------------------------------------------------------------
# retries and reply validation (pre-specified handling, PROTOCOL 12.5.3)
# ---------------------------------------------------------------------------
def test_transient_errors_are_retried_with_backoff():
    good = FakeResponse(message('{"relevant": 1, "valence": "plus"}'))
    seq = [FakeAPIError(529), FakeAPIError(500), FakeAPIError(429, {"retry-after": "7"}), good]
    sleeps = []
    rec, recs = classify_one(FakeClient(lambda kw, n: seq[n - 1]), sleeps=sleeps)
    assert rec["status"] == "ok" and (rec["relevant"], rec["valence"]) == (1, "plus")
    assert [r["status"] for r in recs] == ["api_error"] * 3 + ["ok"]
    assert all(r["retryable"] for r in recs[:3]) and recs[0]["error"]["status_code"] == 529
    assert sleeps[2] == 7.0                                     # retry-after honoured
    assert 2.0 <= sleeps[0] <= 3.0 and 4.0 <= sleeps[1] <= 5.0  # exponential with jitter


def test_non_retryable_error_stops_and_exhaustion_stops():
    for status in (400, 401, 404):
        expect_abort(lambda: classify_one(FakeClient(lambda kw, n: FakeAPIError(status))), "non-retryable")
    log = os.path.join(tmp(), "log.jsonl")
    expect_abort(lambda: classify_one(FakeClient(lambda kw, n: FakeAPIError(503)), log=log),
                 "transport attempts failed")
    recs = L.read_log(log)
    assert len(recs) == L.TRANSPORT_ATTEMPTS and not any(r["final"] for r in recs)


def test_refusal_is_final_without_retry_or_fallback():
    body = message(None, stop="refusal")
    body["stop_details"] = {"type": "refusal", "category": "cyber", "explanation": "test"}
    client = FakeClient(lambda kw, n: FakeResponse(body))
    rec, recs = classify_one(client)
    assert len(client.calls) == 1 and rec["status"] == "refusal" and rec["final"]
    assert rec["relevant"] is None and rec["detail"]["stop_details"]["category"] == "cyber"
    assert "fallbacks" not in client.calls[0] and "betas" not in client.calls[0]


def test_invalid_replies_retried_identically_then_recorded():
    bad = [message('{"relevant": 1, "vale', stop="max_tokens"), message("not json"),
           message('{"relevant": true, "valence": "plus"}')]
    client = FakeClient(lambda kw, n: FakeResponse(bad[n - 1]))
    rec, recs = classify_one(client)
    assert len(client.calls) == L.CONTENT_ATTEMPTS == 3
    assert all(c == client.calls[0] for c in client.calls)                 # identical request
    assert [r["final"] for r in recs] == [False, False, True] and rec["status"] == "invalid"
    seq = [message("[]"), message('{"relevant": 1, "valence": "minus"}')]
    rec, recs = classify_one(FakeClient(lambda kw, n: FakeResponse(seq[n - 1])))
    assert rec["status"] == "ok" and rec["content_attempt"] == 2 and len(recs) == 2


def test_reply_parsing_and_label_mapping_rules():
    P = lambda t, stop="end_turn": L.parse_reply(message(t, stop=stop))  # noqa: E731
    assert P('{"relevant": 1, "valence": "mixed"}')[:3] == ("ok", 1, "mixed")
    assert P('{"relevant": 0, "valence": "none"}')[:3] == ("ok", 0, "none")
    st, rel, val, detail, coerced = P('{"relevant": 0, "valence": "minus"}')
    assert (st, rel, val, coerced) == ("ok", 0, "none", True) and detail == {"raw_valence": "minus"}
    for t in ('{"relevant": 2, "valence": "plus"}', '{"relevant": "1", "valence": "plus"}',
              '{"relevant": 1, "valence": "positive"}', '{"relevant": 1, "valence": "plus", "why": "x"}',
              '{"relevant": 1}', '{"relevant": 1.5, "valence": "plus"}'):
        assert P(t)[0] == "invalid", t
    assert P('{"relevant": 1, "valence": "plus"}', stop="max_tokens")[0] == "invalid"
    two = message('{"relevant": 1, "valence": "plus"}')
    two["content"].append({"type": "text", "text": "extra"})
    assert L.parse_reply(two)[0] == "invalid"


def test_refused_and_invalid_labels_stay_missing_in_the_outputs():
    d = tmp()
    p = paths(d)
    refusal = message(None, stop="refusal")

    def script(kw, n):
        t = fragment_of(kw)
        if t == FRAGS[0]["text"]:
            return FakeResponse(refusal)
        if t == FRAGS[1]["text"]:
            return FakeResponse(message("not json"))
        return dictionary_reply(kw, n)
    rc, stdout, err = quiet(L.main, ["--out", p["llm_labels.csv"], "--log", p["log.jsonl"]], client=FakeClient(script))
    assert rc == 0, err
    head, rows = read_csv(p["llm_labels.csv"])
    by = {r[0]: r for r in rows}
    assert by[FRAGS[0]["id"]][1:4] == ["", "", "refusal"] and by[FRAGS[1]["id"]][1:4] == ["", "", "invalid"]
    with open(p["llm_labels_run.json"], encoding="utf-8") as fh:
        rr = json.load(fh)
    assert rr["status_counts"] == {"ok": 298, "refusal": 1, "invalid": 1} and rr["complete"] is True


def test_served_model_mismatch_is_flagged_and_recorded():
    d = tmp()
    p = paths(d)
    client = FakeClient(lambda kw, n: FakeResponse(message('{"relevant": 0, "valence": "none"}', model="other-model")))
    rc, stdout, _ = quiet(L.main, ["--out", p["llm_labels.csv"], "--log", p["log.jsonl"]], client=client)
    assert rc == 0 and "WARNING: differs from the requested claude-opus-5-5" in stdout
    head, rows = read_csv(p["llm_labels.csv"])
    assert {r[4] for r in rows} == {"other-model"}
    with open(p["llm_labels_run.json"], encoding="utf-8") as fh:
        assert json.load(fh)["models_served"] == ["other-model"]


# ---------------------------------------------------------------------------
# the real SDK, mocked HTTP: request body on the wire and SDK error classes
# ---------------------------------------------------------------------------
def sdk_client(handler):
    import anthropic, httpx2
    return anthropic.Anthropic(api_key="sk-ant-test-not-a-real-key", base_url="http://mock.invalid", max_retries=0,
                               http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler),
                                                                        trust_env=False))


def test_sdk_sends_exactly_the_frozen_request_and_parses_reply():
    need_sdk()
    import httpx2
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, json.loads(request.content), dict(request.headers)))
        return httpx2.Response(200, json=message('{"relevant": 1, "valence": "minus"}'),
                               headers={"request-id": "req_mock_1"})
    rec, recs = classify_one(sdk_client(handler))
    method, path, body, headers = seen[0]
    assert len(seen) == 1 and method == "POST" and path == "/v1/messages"
    assert body == L.build_request(PROMPT_TEXT, FRAGS[0]["text"])          # nothing added, nothing dropped
    assert body["system"][0]["text"].encode("utf-8") == read_bytes(L.PROMPT_FILE)   # prompt bytes unchanged
    assert "temperature" not in body and "top_p" not in body and "fallbacks" not in body
    assert headers.get("x-api-key") == "sk-ant-test-not-a-real-key"
    assert rec["status"] == "ok" and (rec["relevant"], rec["valence"]) == (1, "minus")
    assert rec["request_id"] == "req_mock_1" and rec["model_served"] == L.MODEL
    assert "sk-ant-test" not in json.dumps(recs)                          # key never logged


def test_sdk_error_classes_follow_the_retry_policy():
    need_sdk()
    import anthropic, httpx2
    n = {"k": 0}

    def flaky(request):
        n["k"] += 1
        if n["k"] == 1:
            raise httpx2.ConnectError("connection refused", request=request)
        if n["k"] == 2:
            return httpx2.Response(529, json={"type": "error", "error": {"type": "overloaded_error", "message": "x"}})
        if n["k"] == 3:
            return httpx2.Response(429, json={"type": "error", "error": {"type": "rate_limit_error", "message": "x"}},
                                   headers={"retry-after": "3"})
        return httpx2.Response(200, json=message('{"relevant": 0, "valence": "none"}'))
    sleeps = []
    rec, recs = classify_one(sdk_client(flaky), sleeps=sleeps)
    assert rec["status"] == "ok" and [r["status"] for r in recs] == ["api_error"] * 3 + ["ok"]
    assert [r["error"]["type"] for r in recs[:3]] == ["APIConnectionError", "OverloadedError", "RateLimitError"]
    assert sleeps[2] == 3.0

    def bad_request(request):
        return httpx2.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "x"}})
    expect_abort(lambda: classify_one(sdk_client(bad_request)), "BadRequestError")
    assert issubclass(anthropic.APITimeoutError, anthropic.APIConnectionError)   # timeouts are retried too


# ---------------------------------------------------------------------------
def main():
    tests = [(k, v) for k, v in sorted(globals().items(), key=lambda kv: kv[1].__code__.co_firstlineno
                                       if callable(kv[1]) and hasattr(kv[1], "__code__") else 0)
             if k.startswith("test_") and callable(v)]
    results = Counter()
    for name, fn in tests:
        try:
            with redirect_stdout(io.StringIO()):
                fn()
            print(f"PASS  {name}")
            results["pass"] += 1
        except unittest.SkipTest as e:
            print(f"SKIP  {name}: {e}")
            results["skip"] += 1
        except Exception as e:  # noqa: BLE001
            import traceback
            print(f"FAIL  {name}: {e.__class__.__name__}: {e}")
            traceback.print_exc()
            results["fail"] += 1
    print(f"\n{results['pass']} passed, {results['fail']} failed, {results['skip']} skipped "
          f"(fragments: {os.path.basename(FRAG_SRC)}, {len(FRAGS)})")
    sys.exit(1 if results["fail"] else 0)


if __name__ == "__main__":
    main()
