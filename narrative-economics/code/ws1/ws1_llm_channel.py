#!/usr/bin/env python3
"""
ws1_llm_channel.py - WS1.0 LLM classification channel, frozen v1
(PROTOCOL_WS1.0.md section 12; the second pre-registered channel, A.2/A.6.3).

One Anthropic Messages API request per fragment (never several fragments in
one prompt). The system prompt is the whole of llm_channel_prompt_v1.txt: the
CODEBOOK.md v1 rules plus, as worked examples, the 8 practice items of the
coding page with their codebook answers and explanations, in the words the
human coders are shown (instruction parity, PROTOCOL 12.5.3). No evaluation
fragment is in the prompt; each request carries exactly one evaluation
fragment, in the user message (USER_TEMPLATE). The reply is constrained by a
JSON schema (structured outputs) to
    {"relevant": 0|1, "valence": "minus"|"plus"|"mixed"|"none"}.

Frozen identity (PROTOCOL 12.5.3): the SHA-256 of this file (request
construction, reply parser, label mapping, outputs), of the prompt file, of
the request specification and of the input set (the 300 frag_id + text). The
frozen values are read from verify_frozen_channels.py (FROZEN), which holds
the values written in PROTOCOL section 12. The script refuses to run, dry runs
included, if any of the four differs. A changed channel is a new version.

Model and parameters (from the claude-api skill reference, models cached
2026-10-06, and the installed anthropic SDK 1.13.0):
  - claude-opus-5-5: the current Opus model and the reference's default. The
    reference lists no dated snapshot id for it and says the id is complete as
    written. The served model of every response is logged and written next to
    each label, so a change of the served model would be visible.
  - No temperature/top_p/top_k: this model rejects them (400) and SDK 1.x has
    no such arguments; the reference notes that temperature 0 never
    guaranteed identical outputs and, where determinism was the intent, points
    to effort "low" with a tighter prompt. Thinking cannot be disabled on this
    model. Effort is "low". Outputs are not
    guaranteed to repeat run to run; which run is the run of record is fixed
    in PROTOCOL 12.6.
  - No refusal fallback to another model (a fallback would change the
    instrument); a refusal is logged and the label left missing.

A run is one raw log file, identified by the run id in its first record, and
may take several invocations: re-running with the same --log resumes
(fragments with a final record are skipped) and a complete log is never
appended to again. Every attempt is appended to the log (request with the
system text replaced by its SHA-256, the full response incl. served model,
request id and usage, timestamps). The log contains fragment text and is
git-ignored; its SHA-256 goes into the run record next to the labels.

Outputs:
  llm_labels.csv      frag_id, relevant_llm, valence_llm, status_llm,
                      model_served; sorted by frag_id; no fragment text
  llm_labels_run.json run record: run id, SHA-256 of llm_labels.csv and of
                      the raw log, the four frozen identities, served models,
                      status counts, first and last timestamps
  llm_raw_log.jsonl   the raw log (git-ignored)
The run record of one run is never overwritten by another run: a replicate
run uses a new --out and a new --log.

Usage:
    python3 ws1_llm_channel.py --dry-run          # no API call, no key, no file written
    ANTHROPIC_API_KEY=... python3 ws1_llm_channel.py
        [--fragments coding_sample.csv|ws1_survey.html] [--out llm_labels.csv]
        [--log llm_raw_log.jsonl] [--record llm_labels_run.json]
        [--coder-format llm_labels_coderformat.csv]
--coder-format additionally writes the labels with the coder columns
(frag_id, human_relevant_0_1, human_valence_minus_plus_none);
ws1_reliability.py --channel LLM=llm_labels.csv reads either file.
"""
import argparse, ast, copy, csv, datetime, hashlib, json, os, platform, random, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
CHANNEL = "ws1-llm-channel-v1"
PROMPT_FILE = os.path.join(HERE, "llm_channel_prompt_v1.txt")
RUNNER_FILE = os.path.abspath(__file__)
FROZEN_TABLE_FILE = os.path.join(HERE, "verify_frozen_channels.py")
# identity field -> key of the FROZEN table in verify_frozen_channels.py
FROZEN_KEYS = {"runner_sha256": "llm_runner_sha256", "prompt_sha256": "llm_prompt_sha256",
               "spec_sha256": "llm_spec_sha256", "input_set_sha256": "input_set_sha256"}
WHAT = {"runner_sha256": "ws1_llm_channel.py (runner: request, reply parser, label mapping, outputs)",
        "prompt_sha256": "llm_channel_prompt_v1.txt (system prompt)",
        "spec_sha256": "request specification (model, parameters, schema, user template)",
        "input_set_sha256": "input set (the 300 frag_id + text)"}

MODEL = "claude-opus-5-5"
EFFORT = "low"
MAX_TOKENS = 4096          # the JSON reply is ~15 tokens; adaptive thinking counts toward max_tokens
VALENCES = ("minus", "plus", "mixed", "none")
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "integer", "enum": [0, 1]},
        "valence": {"type": "string", "enum": list(VALENCES)},
    },
    "required": ["relevant", "valence"],
    "additionalProperties": False,
}
USER_TEMPLATE = "Code this fragment.\n\n<fragment>\n{fragment}\n</fragment>"

# pre-specified handling (PROTOCOL 12.5.3)
RETRY_STATUS = (408, 409, 429)   # plus every status >= 500, and connection errors / timeouts
TRANSPORT_ATTEMPTS = 8           # per request; when exhausted the run stops (rerun resumes)
CONTENT_ATTEMPTS = 3             # identical requests when the reply is not a valid label
BACKOFF_BASE, BACKOFF_MAX = 2.0, 120.0   # seconds; exponential with jitter, or retry-after
TIMEOUT_S = 180.0

# claude-opus-5-5 list prices, USD per million tokens (claude-api skill, cached 2026-10-06)
PRICE_IN, PRICE_OUT, PRICE_CACHE_WRITE_5M, PRICE_CACHE_READ = 4.00, 20.00, 5.00, 0.20
CACHE_MIN_TOKENS = 512           # minimum cacheable prefix on this model (same source)


class ChannelAbort(Exception):
    """The run cannot continue (frozen-identity mismatch, API error, retries exhausted)."""


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------
def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def read_prompt(path=None):
    """(text, sha256 of the raw bytes). The text is sent exactly as stored."""
    with open(path or PROMPT_FILE, "rb") as fh:
        raw = fh.read()
    return raw.decode("utf-8"), sha256_bytes(raw)


def user_message(fragment_text):
    return USER_TEMPLATE.replace("{fragment}", fragment_text)


def build_request(system_text, fragment_text):
    """The complete Messages API request for one fragment."""
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": EFFORT,
                          "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        "system": [{"type": "text", "text": system_text,
                    "cache_control": {"type": "ephemeral"}}],   # prompt caching: a cost/latency setting
        "messages": [{"role": "user", "content": user_message(fragment_text)}],
    }


def prompt_ref(prompt_sha):
    return f"<{os.path.basename(PROMPT_FILE)} sha256={prompt_sha}>"


def spec_sha256(prompt_sha):
    """SHA-256 of the request with the fragment as the literal placeholder
    "{fragment}" and the system text replaced by a reference to its hash."""
    return sha256_bytes(canonical_json(build_request(prompt_ref(prompt_sha), "{fragment}")).encode("utf-8"))


def identity(prompt_sha, frags):
    """The four frozen identities of a run (PROTOCOL 12.5.3)."""
    return {"runner_sha256": sha256_file(RUNNER_FILE), "prompt_sha256": prompt_sha,
            "spec_sha256": spec_sha256(prompt_sha), "input_set_sha256": fragments_sha256(frags)}


def frozen_table(path=None):
    """The FROZEN dict literal of verify_frozen_channels.py, read without executing that file."""
    path = path or FROZEN_TABLE_FILE
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), path)
        for node in tree.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "FROZEN"):
                return ast.literal_eval(node.value)
    except (OSError, SyntaxError, ValueError) as e:
        raise ChannelAbort(f"cannot read the frozen values from {path}: {type(e).__name__}: {e}") from e
    raise ChannelAbort(f"no FROZEN table in {path}")


def check_frozen(ident, table=None):
    """Raise ChannelAbort unless all four identities equal the frozen values."""
    frozen = frozen_table() if table is None else table
    bad = [f"{WHAT[k]}: sha256 {ident[k]}, frozen value {frozen.get(fk)}"
           for k, fk in FROZEN_KEYS.items() if ident[k] != frozen.get(fk)]
    if bad:
        raise ChannelAbort("the LLM channel is frozen (PROTOCOL_WS1.0.md section 12.5.3) and differs:\n  "
                           + "\n  ".join(bad) + "\nA changed channel is a new version (new prompt file, "
                           "runner and channel name), evaluated on fresh fragments (12.6); the input set is fixed.")
    return ident


# ---------------------------------------------------------------------------
# fragments (same sources and loader logic as make_artifact_page.py)
# ---------------------------------------------------------------------------
def load_fragments(sample, html):
    if sample and os.path.exists(sample):
        with open(sample, encoding="utf-8-sig") as fh:
            return [{"id": r["frag_id"], "text": r["text"]} for r in csv.DictReader(fh)], sample
    if html and os.path.exists(html):
        with open(html, encoding="utf-8") as fh:
            h = fh.read()
        i = h.index("const FRAGMENTS = ") + len("const FRAGMENTS = ")
        return json.JSONDecoder().raw_decode(h, i)[0], html
    raise ChannelAbort("no coding_sample.csv and no ws1_survey.html to read the fragments from")


def prepare_fragments(frags):
    """Validate and sort by frag_id (the processing and output order)."""
    ids = [f["id"] for f in frags]
    if len(ids) != len(set(ids)):
        raise ChannelAbort("duplicate frag_id in the fragment source")
    if not all(str(f["text"]).strip() for f in frags):
        raise ChannelAbort("empty fragment text in the fragment source")
    return sorted(({"id": f["id"], "text": f["text"]} for f in frags), key=lambda f: f["id"])


def fragments_sha256(frags):
    """SHA-256 of the input set: canonical JSON of [[frag_id, text], ...] sorted by frag_id."""
    return sha256_bytes(canonical_json([[f["id"], f["text"]] for f in prepare_fragments(frags)]).encode("utf-8"))


# ---------------------------------------------------------------------------
# responses: reply parser and label mapping (part of the frozen runner)
# ---------------------------------------------------------------------------
def response_to_dict(resp):
    if hasattr(resp, "to_dict"):
        return resp.to_dict()
    if isinstance(resp, dict):
        return resp
    raise ChannelAbort(f"unexpected response object {type(resp).__name__}")


def parse_reply(d):
    """(status, relevant, valence, detail, coerced) for one response dict.
    status: ok | refusal | invalid."""
    stop = d.get("stop_reason")
    if stop == "refusal":
        return "refusal", None, None, {"stop_details": d.get("stop_details")}, False
    if stop != "end_turn":
        return "invalid", None, None, {"reason": f"stop_reason={stop}"}, False
    texts = [b.get("text", "") for b in d.get("content") or [] if b.get("type") == "text"]
    if len(texts) != 1:
        return "invalid", None, None, {"reason": f"{len(texts)} text blocks"}, False
    try:
        obj = json.loads(texts[0])
    except ValueError:
        return "invalid", None, None, {"reason": "not JSON", "text": texts[0][:500]}, False
    if not isinstance(obj, dict) or set(obj) != {"relevant", "valence"}:
        return "invalid", None, None, {"reason": "keys", "text": texts[0][:500]}, False
    rel, val = obj["relevant"], obj["valence"]
    if isinstance(rel, bool) or rel not in (0, 1) or val not in VALENCES:
        return "invalid", None, None, {"reason": "values", "text": texts[0][:500]}, False
    if rel == 0 and val != "none":      # CODEBOOK v1: "If relevance = 0, write none"
        return "ok", 0, "none", {"raw_valence": val}, True
    return "ok", rel, val, None, False


def is_retryable(exc):
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status in RETRY_STATUS or status >= 500
    try:
        import anthropic
    except ImportError:
        return False
    return isinstance(exc, anthropic.APIConnectionError)     # includes APITimeoutError


def retry_after_seconds(exc):
    try:
        v = float(exc.response.headers.get("retry-after"))
        return v if v >= 0 else None
    except (AttributeError, TypeError, ValueError):
        return None


def backoff(attempt, exc, rng):
    ra = retry_after_seconds(exc)
    if ra is not None:
        return min(ra, BACKOFF_MAX)
    return min(BACKOFF_BASE * 2 ** (attempt - 1) + rng.uniform(0, 1), BACKOFF_MAX)


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------
def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


def read_log(path):
    """All parsable records. A line that is not JSON (a record torn by a crash mid-write)
    is skipped with a warning; its fragment then has no final record and is sent again."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    out = []
    for k, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            print(f"warning: {path} line {k} is not JSON (torn record?); skipped", file=sys.stderr)
    return out


def append_log(path, record):
    """Append one record as one line, flushed to disk; a torn last line is terminated first."""
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with open(path, "a+b") as fh:
        if fh.seek(0, os.SEEK_END):
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                line = "\n" + line
        fh.write(line.encode("utf-8"))
        fh.flush()
        os.fsync(fh.fileno())


def log_run_id(records):
    """The run id of a log: the run_id of its first record that has one (None for a new log)."""
    for r in records:
        if r.get("run_id"):
            return r["run_id"]
    return None


def final_records(records, frags, ctx):
    """{frag_id: final attempt record}; refuses a log of another run, channel identity or input."""
    text_sha = {f["id"]: sha256_bytes(f["text"].encode("utf-8")) for f in frags}
    out = {}
    for r in records:
        if r.get("run_id") != ctx["run_id"]:
            raise ChannelAbort(f"log record ({r.get('type')}, {r.get('frag_id', '-')}) belongs to run "
                               f"{r.get('run_id')}, not {ctx['run_id']}: one log holds one run; use a new --log")
        for k in ("runner_sha256", "prompt_sha256", "spec_sha256", "input_set_sha256"):
            if k in r and r[k] != ctx[k]:
                raise ChannelAbort(f"log record ({r.get('type')}, {r.get('frag_id', '-')}) was written with "
                                   f"another {k} ({r[k]}); use a new --log")
        if r.get("type") != "attempt" or not r.get("final"):
            continue
        fid = r["frag_id"]
        if fid not in text_sha or r.get("fragment_sha256") != text_sha[fid]:
            raise ChannelAbort(f"log record for {fid} does not match the current fragment text; use a new --log")
        if fid in out:
            raise ChannelAbort(f"log has two final records for {fid}")
        out[fid] = r
    return out


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def classify_fragment(client, frag, prompt_text, ctx, log_path, sleep=time.sleep, rng=None):
    """All attempts for one fragment; returns its final record."""
    rng = rng or random.Random()
    req = build_request(prompt_text, frag["text"])
    logged_req = copy.deepcopy(req)
    logged_req["system"][0]["text"] = prompt_ref(ctx["prompt_sha256"])
    base = {"type": "attempt", "channel": CHANNEL, "run_id": ctx["run_id"], "frag_id": frag["id"],
            "fragment_sha256": sha256_bytes(frag["text"].encode("utf-8")),
            "runner_sha256": ctx["runner_sha256"], "prompt_sha256": ctx["prompt_sha256"],
            "spec_sha256": ctx["spec_sha256"], "model_requested": MODEL, "request": logged_req}
    for content_attempt in range(1, CONTENT_ATTEMPTS + 1):
        for transport_attempt in range(1, TRANSPORT_ATTEMPTS + 1):
            t_req, t0 = utcnow(), time.monotonic()
            rec = dict(base, content_attempt=content_attempt, transport_attempt=transport_attempt,
                       ts_request=t_req)
            try:
                resp = client.messages.create(**req)
            except Exception as exc:  # noqa: BLE001 - every failure is logged, then retried or fatal
                retry = is_retryable(exc)
                rec.update(ts_response=utcnow(), latency_s=round(time.monotonic() - t0, 3),
                           status="api_error", final=False, retryable=retry,
                           error={"type": type(exc).__name__, "status_code": getattr(exc, "status_code", None),
                                  "message": str(exc)[:1000]})
                append_log(log_path, rec)
                if not retry:
                    raise ChannelAbort(f"{frag['id']}: non-retryable API error "
                                       f"{type(exc).__name__}: {str(exc)[:300]}") from exc
                if transport_attempt == TRANSPORT_ATTEMPTS:
                    raise ChannelAbort(f"{frag['id']}: {TRANSPORT_ATTEMPTS} transport attempts failed; "
                                       "rerun later to resume") from exc
                sleep(backoff(transport_attempt, exc, rng))
                continue
            d = response_to_dict(resp)
            status, rel, val, detail, coerced = parse_reply(d)
            final = status in ("ok", "refusal") or content_attempt == CONTENT_ATTEMPTS
            rec.update(ts_response=utcnow(), latency_s=round(time.monotonic() - t0, 3),
                       model_served=d.get("model"), request_id=getattr(resp, "_request_id", None),
                       stop_reason=d.get("stop_reason"), usage=d.get("usage"), response=d,
                       status=status, detail=detail, relevant=rel, valence=val,
                       valence_coerced=coerced, final=final)
            append_log(log_path, rec)
            if final:
                return rec
            break   # invalid reply: next content attempt (identical request)
    raise AssertionError("unreachable")


def run(client, frags, prompt_text, ctx, log_path, source, done, sleep=time.sleep, rng=None):
    """Send every fragment without a final record; called only when there is something to send."""
    todo = [f for f in frags if f["id"] not in done]
    try:
        import anthropic
        sdk = anthropic.__version__
    except ImportError:
        sdk = None
    append_log(log_path, {"type": "run_start", "channel": CHANNEL, "run_id": ctx["run_id"], "ts": utcnow(),
                          "model": MODEL, "effort": EFFORT, "max_tokens": MAX_TOKENS,
                          "runner_sha256": ctx["runner_sha256"], "prompt_sha256": ctx["prompt_sha256"],
                          "spec_sha256": ctx["spec_sha256"], "input_set_sha256": ctx["input_set_sha256"],
                          "fragments_source": os.path.basename(source), "n_fragments": len(frags),
                          "n_already_final": len(done), "anthropic_sdk": sdk,
                          "python": platform.python_version()})
    for k, f in enumerate(todo, 1):
        rec = classify_fragment(client, f, prompt_text, ctx, log_path, sleep=sleep, rng=rng)
        done[f["id"]] = rec
        print(f"[{k}/{len(todo)}] {f['id']}: {rec['status']} {rec.get('relevant')} {rec.get('valence')}")
    append_log(log_path, {"type": "run_end", "channel": CHANNEL, "run_id": ctx["run_id"], "ts": utcnow(),
                          "n_final": len(done), "complete": len(done) == len(frags)})
    return done


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------
def write_labels(frags, finals, out_path, coder_format=None):
    """llm_labels.csv sorted by frag_id; returns (sha256, complete, status counts)."""
    rows, counts = [], {}
    for f in prepare_fragments(frags):
        r = finals.get(f["id"])
        status = r["status"] if r else "pending"
        counts[status] = counts.get(status, 0) + 1
        ok = status == "ok"
        rows.append((f["id"], str(r["relevant"]) if ok else "", r["valence"] if ok else "", status,
                     (r.get("model_served") or "") if r else ""))
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["frag_id", "relevant_llm", "valence_llm", "status_llm", "model_served"])
        w.writerows(rows)
    if coder_format:
        with open(coder_format, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["frag_id", "human_relevant_0_1", "human_valence_minus_plus_none"])
            w.writerows(r[:3] for r in rows)
    return sha256_file(out_path), counts.get("pending", 0) == 0, counts


def usage_cost(records):
    """Token totals over every attempt in the log, and their cost at list price."""
    tot = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
    for r in records:
        for k in tot:
            tot[k] += ((r.get("usage") or {}).get(k) or 0) if r.get("type") == "attempt" else 0
    cost = (tot["input_tokens"] * PRICE_IN + tot["output_tokens"] * PRICE_OUT
            + tot["cache_creation_input_tokens"] * PRICE_CACHE_WRITE_5M
            + tot["cache_read_input_tokens"] * PRICE_CACHE_READ) / 1e6
    return tot, cost


def default_record_path(out_path):
    return os.path.splitext(out_path)[0] + "_run.json"


def check_record_owner(record_path, run_id):
    """Refuse to overwrite the run record of another run (e.g. the committed run of record).
    run_id is the id of the log's run, None for a new log (which can own no existing record)."""
    if not os.path.exists(record_path):
        return
    try:
        with open(record_path, encoding="utf-8") as fh:
            owner = json.load(fh).get("run_id")
    except (OSError, ValueError, AttributeError) as e:
        raise ChannelAbort(f"{record_path} exists but is not a run record ({e}); it is not overwritten") from e
    if run_id is None or owner != run_id:
        raise ChannelAbort(f"{record_path} is the run record of run {owner}; this log is "
                           f"{'a new run' if run_id is None else 'run ' + run_id}. A replicate run "
                           "writes to a new --out and a new --log (PROTOCOL 12.6).")


def run_record(records, finals, frags, ctx, out_path, log_path, labels_sha, complete, counts):
    """The run record: a function of the log and the labels only (no wall-clock value of its own)."""
    att = [r for r in records if r.get("type") == "attempt"]
    starts = [r for r in records if r.get("type") == "run_start"]
    tot, cost = usage_cost(records)
    return {
        "channel": CHANNEL, "protocol": "PROTOCOL_WS1.0.md section 12", "run_id": ctx["run_id"],
        "complete": complete, "n_fragments": len(frags), "status_counts": counts,
        "valence_coerced": sum(1 for r in finals.values() if r.get("valence_coerced")),
        "labels_file": os.path.basename(out_path), "labels_sha256": labels_sha,
        "raw_log_file": os.path.basename(log_path), "raw_log_sha256": sha256_file(log_path),
        "runner_sha256": ctx["runner_sha256"], "prompt_sha256": ctx["prompt_sha256"],
        "spec_sha256": ctx["spec_sha256"], "input_set_sha256": ctx["input_set_sha256"],
        "model_requested": MODEL, "effort": EFFORT, "max_tokens": MAX_TOKENS,
        "models_served": sorted({r["model_served"] for r in att if r.get("model_served")}),
        "invocations": len(starts), "attempts": len(att),
        "first_request_utc": min((r["ts_request"] for r in att), default=None),
        "last_response_utc": max((r.get("ts_response") or "" for r in att), default=None),
        "anthropic_sdk": sorted({str(r.get("anthropic_sdk")) for r in starts}),
        "python": sorted({str(r.get("python")) for r in starts}),
        "usage_totals": tot, "cost_usd_list_price": round(cost, 4),
    }


def estimate(prompt_text, todo):
    """Rough pre-run cost range. Token counts are NOT from a tokenizer: they assume 3 to 4
    characters per token (a rule of thumb for English, not a figure from the skill)."""
    n = len(todo)
    if not n:
        return "nothing to send"
    sys_c = len(prompt_text)
    usr_c = sum(len(user_message(f["text"])) for f in todo)
    json_c = len('{"relevant":1,"valence":"minus"}')
    lines = [f"requests: {n}; characters: system prompt {sys_c} (sent with every request), "
             f"user messages {usr_c} in total",
             "token counts below ASSUME 3-4 characters per token (rule of thumb, not a tokenizer count; "
             "exact counts are in the log's `usage` after the run)"]
    for cpt, label in ((4.0, "low"), (3.0, "high")):
        st, ut, jt = sys_c / cpt, usr_c / cpt, json_c / cpt
        cached = st >= CACHE_MIN_TOKENS
        no_cache = (n * st + ut) * PRICE_IN / 1e6
        with_cache = ((st * PRICE_CACHE_WRITE_5M + (n - 1) * st * PRICE_CACHE_READ + ut * PRICE_IN) / 1e6
                      if cached else no_cache)
        out_lo, out_hi = n * jt * PRICE_OUT / 1e6, n * MAX_TOKENS * PRICE_OUT / 1e6
        lines.append(f"[{label} token assumption, {cpt:g} chars/token] input ~{n * st + ut:,.0f} tokens: "
                     f"${no_cache:.2f} without cache hits, ${with_cache:.2f} if the system prompt is read from "
                     f"cache after the first request; output between ~{n * jt:,.0f} tokens (JSON only, ${out_lo:.2f}) "
                     f"and {n * MAX_TOKENS:,} tokens (every reply at max_tokens incl. thinking, ${out_hi:.2f})")
    lines.append(f"prices used (USD per MTok, claude-api skill cached 2026-10-06): input {PRICE_IN:.2f}, "
                 f"output {PRICE_OUT:.2f}, 5-min cache write {PRICE_CACHE_WRITE_5M:.2f}, cache read {PRICE_CACHE_READ:.2f}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
def main(argv=None, client=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="print the identity check, the exact first request, the request count and a cost "
                         "estimate; no API call, no file written")
    ap.add_argument("--fragments", default=None, help="coding_sample.csv or ws1_survey.html "
                    "(default: coding_sample.csv if present, else ws1_survey.html)")
    ap.add_argument("--out", default=os.path.join(HERE, "llm_labels.csv"))
    ap.add_argument("--log", default=os.path.join(HERE, "llm_raw_log.jsonl"))
    ap.add_argument("--record", default=None, help="run record (default: <out without .csv>_run.json)")
    ap.add_argument("--coder-format", default=None,
                    help="also write the labels in the coder columns read by ws1_reliability.py --channel")
    a = ap.parse_args(argv)
    record_path = a.record or default_record_path(a.out)
    try:
        prompt_text, prompt_sha = read_prompt()
        if a.fragments:
            frags, src = (load_fragments(None, a.fragments) if a.fragments.lower().endswith(".html")
                          else load_fragments(a.fragments, None))
        else:
            frags, src = load_fragments(os.path.join(HERE, "coding_sample.csv"), os.path.join(HERE, "ws1_survey.html"))
        frags = prepare_fragments(frags)
        ident = check_frozen(identity(prompt_sha, frags))
        records = read_log(a.log)
        old_id = log_run_id(records)
        if records and old_id is None:
            raise ChannelAbort(f"{a.log} has records but no run id; use a new --log")
        check_record_owner(record_path, old_id)
        ctx = dict(ident, run_id=old_id or uuid.uuid4().hex)
        done = final_records(records, frags, ctx)
        todo = [f for f in frags if f["id"] not in done]
        print(f"{CHANNEL}: model {MODEL}, effort {EFFORT}, max_tokens {MAX_TOKENS}, adaptive thinking, "
              f"JSON-schema output, no sampling parameters, no fallback")
        for k in FROZEN_KEYS:
            print(f"{WHAT[k]}: sha256 {ident[k]} (frozen: OK)")
        print(f"fragments {len(frags)} from {os.path.basename(src)}")
        print(f"log {a.log}: " + (f"run {old_id}, " if old_id else "new run, ")
              + f"{len(done)} fragment(s) already final -> {len(todo)} to send")
        if a.dry_run:
            if todo:
                print(f"\n--- exact request for the first fragment to send ({todo[0]['id']}) ---")
                print(json.dumps(build_request(prompt_text, todo[0]["text"]), indent=2, ensure_ascii=False))
            print("\n--- estimate ---")
            print(estimate(prompt_text, todo))
            return 0
        if todo and client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise ChannelAbort("ANTHROPIC_API_KEY is not set (it is read from the environment only "
                                   "and never written to the log)")
            import anthropic
            client = anthropic.Anthropic(max_retries=0, timeout=TIMEOUT_S)   # retries are ours, so all are logged
        try:
            if todo:
                run(client, frags, prompt_text, ctx, a.log, src, done)
        finally:
            records = read_log(a.log)
            if records:
                finals = final_records(records, frags, ctx)
                digest, complete, counts = write_labels(frags, finals, a.out, a.coder_format)
                rec = run_record(records, finals, frags, ctx, a.out, a.log, digest, complete, counts)
                with open(record_path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
                print(f"\nlabels -> {a.out}  status counts {counts}")
                print(f"coerced valence (relevant 0 with a valence): {rec['valence_coerced']}")
                served = rec["models_served"]
                print(f"served model(s): {served}" + ("" if served in ([], [MODEL]) else "  WARNING: differs from "
                                                       f"the requested {MODEL}"))
                print(f"usage {rec['usage_totals']}, cost at list price ${rec['cost_usd_list_price']:.2f}")
                print(f"run record -> {record_path}: run {ctx['run_id']}, sha256({os.path.basename(a.out)}) = "
                      f"{digest}, sha256({os.path.basename(a.log)}) = {rec['raw_log_sha256']}")
                if complete:
                    print("COMPLETE. Commit the labels and the run record (not the raw log, which is git-ignored); "
                          "the run of record is defined in PROTOCOL_WS1.0.md 12.6.")
                else:
                    print("INCOMPLETE: rerun with the same --log to resume (fragments with a final record are skipped)")
    except ChannelAbort as e:
        print(f"stopped: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
