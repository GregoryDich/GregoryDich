#!/usr/bin/env python3
"""
verify_frozen_channels.py - recompute every hash fixed in PROTOCOL_WS1.0.md
section 12 (machine channels frozen before human coding, addendum v1.1) and
exit 1 on any mismatch. Stdlib only; no network, no API key.

    python3 verify_frozen_channels.py

Definitions (as in section 12):
  file hashes      SHA-256 of the raw file bytes
  git blob         sha1("blob <size>\\0" + bytes), the id `git hash-object` gives
  term lists       SHA-256 of the UTF-8 bytes of
                   json.dumps({name: list for the five lists}, sort_keys=True,
                              ensure_ascii=False, separators=(",", ":"))
                   (lists in source order; only the keys are sorted)
  request spec     ws1_llm_channel.spec_sha256(): the complete request with the
                   fragment as the placeholder "{fragment}" and the system text
                   replaced by a reference to the prompt hash, canonical JSON
  input set        canonical JSON of [[frag_id, text], ...] sorted by frag_id
"""
import hashlib, importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TERM_LISTS = ("AI_TERMS", "OCC_TERMS", "DISPLACE_TERMS", "CREATE_TERMS", "SKEPTICAL_TERMS")

FROZEN = {
    "dictionary v1: ws1_pipeline.py sha256":
        "6e090f195c91398ffe311d1107490667e028ad82656ef21c39e1f23e623dfbe1",
    "dictionary v1: ws1_pipeline.py git blob (as at commit f4a1655)":
        "15759519ec822077ab755478193a6b270962fbed",
    "dictionary v1: five term lists sha256":
        "7ef9fec0aad7ddc70d7be88d9f33b92ab17630d1da2576bb5d6364b7c7b1a620",
    "LLM channel v1: llm_channel_prompt_v1.txt sha256":
        "17a98727a1a018544fc5203676f0066c901853fbc8b3e394a4e39d1f52cfd340",
    "LLM channel v1: request specification sha256":
        "31611568e0657a2ad763e7a3fc1b11d0fcab956fcb478542713a5709efff49d6",
    "input set: the 300 fragments sha256":
        "603893308ce3bcf17aa71b33b39cfb0b8352192a754afa46d1a3e0aa425e47f2",
}


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(name):
    with open(os.path.join(HERE, name), "rb") as fh:
        return fh.read()


def computed():
    pipe = read("ws1_pipeline.py")
    p = load("ws1_pipeline")
    terms = json.dumps({n: getattr(p, n) for n in TERM_LISTS}, sort_keys=True,
                       ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    L = load("ws1_llm_channel")
    prompt_sha = hashlib.sha256(read("llm_channel_prompt_v1.txt")).hexdigest()
    frags, _ = L.load_fragments(os.path.join(HERE, "coding_sample.csv"), os.path.join(HERE, "ws1_survey.html"))
    out = dict(zip(FROZEN, (
        hashlib.sha256(pipe).hexdigest(),
        hashlib.sha1(b"blob %d\0" % len(pipe) + pipe).hexdigest(),
        hashlib.sha256(terms).hexdigest(),
        prompt_sha,
        L.spec_sha256(prompt_sha),
        L.fragments_sha256(frags),
    )))
    # the constants ws1_llm_channel.py enforces must be the ones frozen here
    out["ws1_llm_channel.py FROZEN_PROMPT_SHA256 constant"] = L.FROZEN_PROMPT_SHA256
    out["ws1_llm_channel.py FROZEN_SPEC_SHA256 constant"] = L.FROZEN_SPEC_SHA256
    return out


def main():
    expected = dict(FROZEN)
    expected["ws1_llm_channel.py FROZEN_PROMPT_SHA256 constant"] = FROZEN["LLM channel v1: llm_channel_prompt_v1.txt sha256"]
    expected["ws1_llm_channel.py FROZEN_SPEC_SHA256 constant"] = FROZEN["LLM channel v1: request specification sha256"]
    try:
        got = computed()
    except Exception as e:  # noqa: BLE001 - a missing or broken file is a failed verification
        print(f"FAIL  could not compute the hashes: {type(e).__name__}: {e}")
        return 1
    bad = 0
    for k, want in expected.items():
        ok = got[k] == want
        bad += not ok
        print(f"{'OK  ' if ok else 'FAIL'}  {k}: {got[k]}" + ("" if ok else f"  (frozen: {want})"))
    print("all frozen hashes match" if not bad else f"{bad} mismatch(es): a frozen channel was changed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
