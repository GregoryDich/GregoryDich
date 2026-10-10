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
an LLM label. All outputs go to temporary directories.
"""
import copy, csv, io, json, os, re, subprocess, sys, tempfile, unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout

TESTS = os.path.dirname(os.path.abspath(__file__))
WS1 = os.path.dirname(TESTS)
sys.path.insert(0, WS1)
import ws1_llm_channel as L  # noqa: E402
import ws1_pipeline  # noqa: E402

FRAGS, FRAG_SRC = L.load_fragments(os.path.join(WS1, "coding_sample.csv"), os.path.join(WS1, "ws1_survey.html"))
FRAGS = L.prepare_fragments(FRAGS)
PROMPT_TEXT, PROMPT_SHA = L.read_prompt()
SPEC = L.spec_sha256(PROMPT_SHA)


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


def tmp():
    return tempfile.mkdtemp(prefix="llmch_")


def skip(msg):
    raise unittest.SkipTest(msg)


def need_sdk():
    try:
        import anthropic, httpx2  # noqa: F401
    except ImportError as e:
        skip(f"anthropic SDK not installed ({e}); pip install anthropic")


def classify_one(client, frag=None, sleeps=None, log=None):
    log = log or os.path.join(tmp(), "log.jsonl")
    import random
    rec = L.classify_fragment(client, frag or FRAGS[0], PROMPT_TEXT, PROMPT_SHA, SPEC, log,
                              sleep=(sleeps.append if sleeps is not None else (lambda s: None)),
                              rng=random.Random(0))
    return rec, quiet(L.read_log, log)[0]


# ---------------------------------------------------------------------------
# frozen identity
# ---------------------------------------------------------------------------
def test_verify_script_passes_on_frozen_files():
    r = subprocess.run([sys.executable, os.path.join(WS1, "verify_frozen_channels.py")],
                       capture_output=True, text=True, cwd=tempfile.gettempdir())
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("OK  ") == 8 and "FAIL" not in r.stdout


def test_verify_script_fails_on_any_change():
    import verify_frozen_channels as V
    got = V.computed()
    assert all(got[k] == v for k, v in V.FROZEN.items())
    saved = V.FROZEN.copy()
    try:
        V.FROZEN["dictionary v1: five term lists sha256"] = "0" * 64
        rc, out, _ = quiet(V.main)
        assert rc == 1 and "FAIL" in out
    finally:
        V.FROZEN.clear()
        V.FROZEN.update(saved)


def test_runner_refuses_changed_prompt_or_spec():
    d = tmp()
    changed = os.path.join(d, "llm_channel_prompt_v1.txt")
    with open(changed, "w", encoding="utf-8") as fh:
        fh.write(PROMPT_TEXT + " ")
    old_file, old_effort = L.PROMPT_FILE, L.EFFORT
    try:
        L.PROMPT_FILE = changed
        rc, out, err = quiet(L.main, ["--dry-run", "--log", os.path.join(d, "log.jsonl")])
        assert rc == 2 and "frozen" in err, err
        L.PROMPT_FILE = old_file
        L.EFFORT = "medium"
        rc, out, err = quiet(L.main, ["--dry-run", "--log", os.path.join(d, "log.jsonl")])
        assert rc == 2 and "request specification" in err, err
    finally:
        L.PROMPT_FILE, L.EFFORT = old_file, old_effort
    assert L.spec_sha256(PROMPT_SHA) == L.FROZEN_SPEC_SHA256


def test_prompt_contains_no_evaluation_or_practice_text():
    """No 5-word sequence of any of the 300 fragments or the 8 practice items is in the prompt."""
    from make_artifact_page import PRACTICE
    assert len(PRACTICE) == 8 and len(FRAGS) == 300
    words = lambda t: re.findall(r"[a-z0-9']+", t.lower())  # noqa: E731

    def grams(t, n=5):
        w = words(t)
        return {" ".join(w[k:k + n]) for k in range(len(w) - n + 1)}
    pg = grams(PROMPT_TEXT)
    hits = sorted({g for t in [f["text"] for f in FRAGS] + [p["text"] for p in PRACTICE] for g in grams(t) & pg})
    assert not hits, hits


def test_prompt_carries_the_codebook_v1_rules():
    t = PROMPT_TEXT
    for needle in ("an AI / automation referent", "a labor referent", "the fragment connects the two",
                   "two-token rule is strict", 'Debunking destruction is "plus", not "minus"',
                   'Uncertainty about the cause is "none", not "minus"', '"mixed"', "If relevant = 0",
                   '{"relevant": 0 or 1, "valence": "minus" | "plus" | "mixed" | "none"}'):
        assert needle in t, needle
    assert t.isascii() and "\r" not in t


# ---------------------------------------------------------------------------
# dry run
# ---------------------------------------------------------------------------
def test_dry_run_prints_exact_request_count_and_estimate():
    d = tmp()
    log = os.path.join(d, "log.jsonl")
    env_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        rc, out, err = quiet(L.main, ["--dry-run", "--log", log, "--out", os.path.join(d, "labels.csv")])
    finally:
        if env_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = env_key
    assert rc == 0, err
    first = FRAGS[0]
    start = out.index("--- exact request")
    body = json.loads(out[out.index("{", start):out.index("\n--- estimate ---")])
    assert body == L.build_request(PROMPT_TEXT, first["text"])
    assert body["system"][0]["text"] == PROMPT_TEXT and fragment_of(body) == first["text"]
    assert "300 to send" in out and "requests: 300" in out and "ASSUME" in out
    assert not os.path.exists(log) and not os.path.exists(os.path.join(d, "labels.csv"))


def test_run_without_key_refuses_and_writes_nothing():
    d = tmp()
    env_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        rc, out, err = quiet(L.main, ["--log", os.path.join(d, "log.jsonl"), "--out", os.path.join(d, "l.csv")])
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
    out, log, cf = (os.path.join(d, n) for n in ("llm_labels.csv", "log.jsonl", "coder.csv"))
    client = FakeClient(dictionary_reply)
    rc, stdout, err = quiet(L.main, ["--out", out, "--log", log, "--coder-format", cf], client=client)
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
    head, rows = read_csv(out)
    assert head == ["frag_id", "relevant_llm", "valence_llm", "status_llm"]
    assert [r[0] for r in rows] == sorted(f["id"] for f in FRAGS)
    exp = expected_labels()
    assert all((r[1], r[2]) == exp[r[0]] and r[3] == "ok" for r in rows)
    head2, rows2 = read_csv(cf)
    assert head2 == ["frag_id", "human_relevant_0_1", "human_valence_minus_plus_none"]
    assert [r for r in rows2] == [r[:3] for r in rows]
    recs = L.read_log(log)
    att = [r for r in recs if r["type"] == "attempt"]
    assert [r["type"] for r in recs][0] == "run_start" and recs[-1] == {**recs[-1], "type": "run_end", "complete": True}
    assert len(att) == 300 and all(r["final"] and r["status"] == "ok" for r in att)
    for r in att:
        assert r["prompt_sha256"] == PROMPT_SHA and r["spec_sha256"] == SPEC
        assert r["model_served"] == L.MODEL and r["request_id"] == "req_test" and r["usage"]["output_tokens"] == 40
        assert r["request"]["system"][0]["text"] == L.prompt_ref(PROMPT_SHA)    # prompt by hash, not 300 copies
        assert r["ts_request"] <= r["ts_response"] and r["ts_request"].endswith("+00:00")
    assert recs[0]["fragments_sha256"] == L.fragments_sha256(FRAGS) and recs[0]["n_fragments"] == 300
    digest = L.sha256_bytes(open(out, "rb").read())
    assert f"sha256(llm_labels.csv) = {digest}" in stdout and "COMPLETE" in stdout


def test_resume_after_abort_sends_only_the_rest():
    d = tmp()
    out, log = os.path.join(d, "llm_labels.csv"), os.path.join(d, "log.jsonl")

    def dies_after_40(kw, n):
        return FakeAPIError(400) if n > 40 else dictionary_reply(kw, n)
    c1 = FakeClient(dies_after_40)
    rc, stdout, err = quiet(L.main, ["--out", out, "--log", log], client=c1)
    assert rc == 2 and "non-retryable" in err and "INCOMPLETE" in stdout
    head, rows = read_csv(out)
    assert Counter(r[3] for r in rows) == {"ok": 40, "pending": 260}
    c2 = FakeClient(dictionary_reply)
    rc, stdout, err = quiet(L.main, ["--out", out, "--log", log], client=c2)
    assert rc == 0 and len(c2.calls) == 260 and "COMPLETE" in stdout
    sent_first = {fragment_of(k) for k in c1.calls[:40]}
    assert not sent_first & {fragment_of(k) for k in c2.calls}
    finals = L.final_records(L.read_log(log), FRAGS, PROMPT_SHA, SPEC)
    assert len(finals) == 300
    head, rows = read_csv(out)
    exp = expected_labels()
    assert all((r[1], r[2]) == exp[r[0]] for r in rows)
    rc, stdout, _ = quiet(L.main, ["--out", out, "--log", log], client=FakeClient(dictionary_reply))
    assert rc == 0 and "0 to send" in stdout


def test_log_from_another_spec_or_input_is_refused():
    d = tmp()
    log = os.path.join(d, "log.jsonl")
    rec, _ = classify_one(FakeClient(dictionary_reply), log=log)
    bad = dict(rec, spec_sha256="0" * 64)
    L.append_log(log, bad)
    try:
        L.final_records(L.read_log(log), FRAGS, PROMPT_SHA, SPEC)
        raise AssertionError("expected ChannelAbort")
    except L.ChannelAbort as e:
        assert "another channel spec" in str(e)
    log2 = os.path.join(d, "log2.jsonl")
    L.append_log(log2, dict(rec, fragment_sha256="0" * 64))
    try:
        L.final_records(L.read_log(log2), FRAGS, PROMPT_SHA, SPEC)
        raise AssertionError("expected ChannelAbort")
    except L.ChannelAbort as e:
        assert "fragment text" in str(e)


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
    assert len(L.final_records(recs, FRAGS, PROMPT_SHA, SPEC)) == 2


# ---------------------------------------------------------------------------
# retries and reply validation (pre-specified handling, PROTOCOL 12.2)
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
        try:
            classify_one(FakeClient(lambda kw, n: FakeAPIError(status)))
            raise AssertionError("expected ChannelAbort")
        except L.ChannelAbort as e:
            assert "non-retryable" in str(e)
    log = os.path.join(tmp(), "log.jsonl")
    try:
        classify_one(FakeClient(lambda kw, n: FakeAPIError(503)), log=log)
        raise AssertionError("expected ChannelAbort")
    except L.ChannelAbort as e:
        assert "transport attempts failed" in str(e)
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


def test_reply_parsing_rules():
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


def test_served_model_mismatch_is_flagged():
    d = tmp()
    client = FakeClient(lambda kw, n: FakeResponse(message('{"relevant": 0, "valence": "none"}', model="other-model")))
    rc, stdout, _ = quiet(L.main, ["--out", os.path.join(d, "o.csv"), "--log", os.path.join(d, "l.jsonl")],
                          client=client)
    assert rc == 0 and "WARNING: differs from the requested claude-opus-5-5" in stdout


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
    try:
        classify_one(sdk_client(bad_request))
        raise AssertionError("expected ChannelAbort")
    except L.ChannelAbort as e:
        assert "BadRequestError" in str(e)
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
