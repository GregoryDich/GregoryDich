#!/usr/bin/env python3
"""
verify_frozen_channels.py - recompute every frozen identity of
PROTOCOL_WS1.0.md section 12 (addendum v1.1) and check it. No network, no API
key; dictionary v0 is read from git history.

    python3 verify_frozen_channels.py
exit 0: everything checked and equal; 1: at least one mismatch; 2: no
mismatch, but something could not be checked here (e.g. no git history).

FROZEN below holds the values written in section 12; ws1_llm_channel.py reads
its four values (runner, prompt, request specification, input set) from this
literal, without executing this file, and refuses to run on any difference.
This script also checks that every FROZEN value is written in section 12,
that the frag_id lists of the sensitivity analyses (section 12.3) are the ones
below and are all among the 300, that every frag_id written anywhere in
section 12 is among the 300, that the worked examples in the LLM prompt are
the practice items the coding page shows (instruction parity, section
12.5.3), and that every run record of LLM channel v1 in this folder
(llm_labels*_run.json) carries the four frozen identities and the SHA-256 of
its labels file (section 12.6.2: the run of record is committed at a commit
at which this script exits 0). Before any run record exists, that last check
passes with nothing to check.

The runner reads FROZEN only; it does not compare FROZEN with section 12.
Run this script before every invocation of ws1_llm_channel.py and start the
runner only if it exits 0 (PROTOCOL 12.6.2).

Definitions (as in section 12):
  file hashes      SHA-256 of the raw file bytes
  git blob         sha1("blob <size>\\0" + bytes), the id `git hash-object` gives
  term lists       SHA-256 of the UTF-8 bytes of
                   json.dumps({name: list, ...}, sort_keys=True,
                              ensure_ascii=False, separators=(",", ":"))
                   (lists in source order, read with ast; only the keys are sorted)
  request spec     ws1_llm_channel.spec_sha256(): the complete request with the
                   fragment as the placeholder "{fragment}" and the system text
                   replaced by a reference to the prompt hash, canonical JSON
  input set        canonical JSON of [[frag_id, text], ...] sorted by frag_id
  practice set     make_artifact_page.PRACTICE_SET: first 12 hex digits of the
                   SHA-256 of the canonical JSON of the 8 practice items
"""
import ast, hashlib, importlib.util, json, os, re, subprocess, sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
PROTOCOL = os.path.join(HERE, "PROTOCOL_WS1.0.md")
V1_LISTS = ("AI_TERMS", "OCC_TERMS", "DISPLACE_TERMS", "CREATE_TERMS", "SKEPTICAL_TERMS")
V0_LISTS = ("AI_TERMS", "OCC_TERMS", "DISPLACE_TERMS", "CREATE_TERMS")
V0_COMMIT = "a2384895755c63ac3a42ec435bc3b8302760566a"   # a238489 = 7eb5a1e^, before the stance fix
V0_PATH = "narrative-economics/code/ws1/ws1_pipeline.py"

FROZEN = {
    "dict_v1_file_sha256": "6e090f195c91398ffe311d1107490667e028ad82656ef21c39e1f23e623dfbe1",
    "dict_v1_git_blob": "15759519ec822077ab755478193a6b270962fbed",
    "dict_v1_terms_sha256": "7ef9fec0aad7ddc70d7be88d9f33b92ab17630d1da2576bb5d6364b7c7b1a620",
    "dict_v0_file_sha256": "8cfd994b5542411e0e4a8367ffb81dd05b3e117c1599caaf0ac343da4860ce49",
    "dict_v0_git_blob": "4311d765b036a451e54b905217d2ea0edf0c1f41",
    "dict_v0_terms_sha256": "25080905de5acc63da004e4cc25a2ff7ea1274fec114b8a7ce5c5fce8c328693",
    "llm_prompt_sha256": "ec8cc4a7925b737f0d81f29f5293987bf5e83faf8e818ebda73a8082f71785a8",
    "llm_runner_sha256": "4899c38ed3ea3a3ce4a1a3ca225612e799b8712057cf9cb7b7df9e8fadcbbcc6",
    "llm_spec_sha256": "129bb453c72e4d8fc23b9095a12c0fc3fddaf4e415b4ef55fe69e2fdd151605b",
    "input_set_sha256": "603893308ce3bcf17aa71b33b39cfb0b8352192a754afa46d1a3e0aa425e47f2",
    "practice_set": "3fa31542cb4a",
}
LABELS = {
    "dict_v1_file_sha256": "dictionary v1: ws1_pipeline.py sha256",
    "dict_v1_git_blob": "dictionary v1: ws1_pipeline.py git blob",
    "dict_v1_terms_sha256": "dictionary v1: five term lists sha256",
    "dict_v0_file_sha256": "dictionary v0: ws1_pipeline.py at a238489 sha256 (git history)",
    "dict_v0_git_blob": "dictionary v0: ws1_pipeline.py at a238489 git blob (git history)",
    "dict_v0_terms_sha256": "dictionary v0: four term lists sha256 (git history)",
    "dict_v0_terms_sha256 (ws1_reliability.py copy)": "dictionary v0: term lists of the copy in ws1_reliability.py",
    "llm_prompt_sha256": "LLM channel v1: llm_channel_prompt_v1.txt sha256",
    "llm_runner_sha256": "LLM channel v1: ws1_llm_channel.py sha256",
    "llm_spec_sha256": "LLM channel v1: request specification sha256",
    "input_set_sha256": "input set: the 300 fragments sha256",
    "practice_set": "instruction parity: practice set of the coding page",
}

# Section 12.3: evaluation fragments excluded in the sensitivity analyses, in the order
# written in the protocol. The marker is the start of the protocol line that lists them.
SENSITIVITY_SETS = {
    "codebook_anchors": [
        "jynC9SncpDM_000", "Zcpj-U5lcAc_000", "66zEFbmgQ5I_027", "6pvGBbIS7Xo_010", "dvmcqxOoA5s_012",
        "EGskcTRnLJ0_031", "E-7FJF51JSU_039", "66zEFbmgQ5I_007", "jynC9SncpDM_016", "EGskcTRnLJ0_015",
        "66zEFbmgQ5I_001", "66zEFbmgQ5I_020", "IUBo9dnZM3g_011", "66zEFbmgQ5I_033", "jynC9SncpDM_017",
        "moiuHRHB6nE_042",
    ],
    "old_practice_paraphrased": [
        "Zcpj-U5lcAc_014", "Zcpj-U5lcAc_013", "jynC9SncpDM_004", "dvmcqxOoA5s_007", "Zcpj-U5lcAc_011",
        "IUBo9dnZM3g_023", "EGskcTRnLJ0_020", "66zEFbmgQ5I_028", "jynC9SncpDM_015", "jynC9SncpDM_016",
        "6pvGBbIS7Xo_007", "6pvGBbIS7Xo_008", "Zcpj-U5lcAc_000", "Zcpj-U5lcAc_008", "Zcpj-U5lcAc_034",
        "IUBo9dnZM3g_025", "IUBo9dnZM3g_026", "IUBo9dnZM3g_021", "IUBo9dnZM3g_022", "Zcpj-U5lcAc_021",
        "IUBo9dnZM3g_009", "IUBo9dnZM3g_010", "dvmcqxOoA5s_005", "66zEFbmgQ5I_007", "66zEFbmgQ5I_008",
        "66zEFbmgQ5I_005", "moiuHRHB6nE_007", "sb5glj61LsA_003", "Zcpj-U5lcAc_012", "moiuHRHB6nE_014",
        "moiuHRHB6nE_025", "66zEFbmgQ5I_006", "sb5glj61LsA_004", "xsWaPdvCmy4_005", "pGBkP9jNz-U_008",
        "6pvGBbIS7Xo_000", "EGskcTRnLJ0_022", "66zEFbmgQ5I_015", "66zEFbmgQ5I_012", "66zEFbmgQ5I_013",
        "EGskcTRnLJ0_006", "66zEFbmgQ5I_016", "R6mTUK_yPKw_044", "66zEFbmgQ5I_033", "66zEFbmgQ5I_002",
        "IUBo9dnZM3g_011", "EGskcTRnLJ0_012", "pGBkP9jNz-U_006", "moiuHRHB6nE_042", "moiuHRHB6nE_028",
        "moiuHRHB6nE_034", "moiuHRHB6nE_021", "pGBkP9jNz-U_009", "pGBkP9jNz-U_007", "moiuHRHB6nE_001",
        "IUBo9dnZM3g_028", "jynC9SncpDM_017", "E-7FJF51JSU_009", "IUBo9dnZM3g_007", "IUBo9dnZM3g_024",
        "xsWaPdvCmy4_006", "Zcpj-U5lcAc_020", "dvmcqxOoA5s_003", "dvmcqxOoA5s_013", "R6mTUK_yPKw_035",
        "Zcpj-U5lcAc_001", "Zcpj-U5lcAc_019", "dvmcqxOoA5s_014", "6pvGBbIS7Xo_010", "xsWaPdvCmy4_013",
        "sb5glj61LsA_009", "6pvGBbIS7Xo_011", "6pvGBbIS7Xo_009", "E-7FJF51JSU_035", "Zcpj-U5lcAc_037",
    ],
}
SENSITIVITY_MARKERS = {"codebook_anchors": "- (a) Codebook anchors:", "old_practice_paraphrased": "- (b) Earlier practice items:"}
FRAG_ID = re.compile(r"`([A-Za-z0-9_-]{11}_\d{3})`")
# Run records of LLM channel v1 (PROTOCOL 12.5.3, 12.6.2): the runner writes
# <labels stem>_run.json next to the labels file; the identity fields must carry the FROZEN values.
LLM_CHANNEL = "ws1-llm-channel-v1"
RUN_RECORD_GLOB = re.compile(r"llm_labels.*_run\.json")
RUN_RECORD_KEYS = {"runner_sha256": "llm_runner_sha256", "prompt_sha256": "llm_prompt_sha256",
                   "spec_sha256": "llm_spec_sha256", "input_set_sha256": "input_set_sha256"}
RUN_RECORD_DIR = HERE


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(name):
    return read_path(os.path.join(HERE, name))


def read_path(path):
    with open(path, "rb") as fh:
        return fh.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def term_lists(source, names, prefix=""):
    """{name: list} of the module-level list assignments `prefix + name`, read with ast."""
    found = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n.startswith(prefix) and n[len(prefix):] in names:
                found[n[len(prefix):]] = ast.literal_eval(node.value)
    missing = [n for n in names if n not in found]
    if missing:
        raise ValueError(f"term lists not found: {missing}")
    return {n: found[n] for n in names}


def terms_sha256(lists):
    return sha256(json.dumps(lists, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def git_show(rev_path):
    try:
        r = subprocess.run(["git", "-C", HERE, "show", rev_path], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def practice_blocks(page):
    """The worked examples the LLM prompt must contain: per practice item of the coding page,
    its text and the feedback line the page shows in English ("Codebook answer: ...")."""
    en = page.I18N["en"]
    out = []
    for it, why in zip(page.PRACTICE, en["practice.why"]):
        rel = en["yes"] if it["rel"] == "1" else en["no"]
        val = en["fb.val"].replace("{label}", en["q2." + it["val"]]) if it["rel"] == "1" else ""
        answer = en["fb.answer"].replace("{rel}", rel).replace("{val}", val).replace("{why}", why)
        out.append(f"Fragment: {it['text']}\n{answer}\n"
                   f'In the output format: {{"relevant": {it["rel"]}, "valence": "{it["val"]}"}}\n')
    return out


def section12():
    with open(PROTOCOL, encoding="utf-8") as fh:
        text = fh.read()
    i = text.find("\n## 12.")
    if i < 0:
        raise ValueError("PROTOCOL_WS1.0.md has no section 12")
    return text[i:]


def checks():
    """[(label, status, computed, expected)] with status OK | FAIL | NOT CHECKED."""
    res = []

    def add(key, got, want=None, label=None):
        want = FROZEN[key] if want is None else want
        res.append((label or LABELS[key], "OK" if got == want else "FAIL", got, want))

    def guard(label, fn):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - a missing or broken input is a failed check
            res.append((label, "FAIL", f"{type(e).__name__}: {e}", "computable"))

    def dict_v1():
        src = read("ws1_pipeline.py")
        add("dict_v1_file_sha256", sha256(src))
        add("dict_v1_git_blob", git_blob(src))
        add("dict_v1_terms_sha256", terms_sha256(term_lists(src, V1_LISTS)))

    def dict_v0():
        src = git_show(f"{V0_COMMIT}:{V0_PATH}")
        if src is None:
            for k in ("dict_v0_file_sha256", "dict_v0_git_blob", "dict_v0_terms_sha256"):
                res.append((LABELS[k], "NOT CHECKED", "git history not available here", FROZEN[k]))
        else:
            add("dict_v0_file_sha256", sha256(src))
            add("dict_v0_git_blob", git_blob(src))
            add("dict_v0_terms_sha256", terms_sha256(term_lists(src, V0_LISTS)))
        copy = terms_sha256(term_lists(read("ws1_reliability.py"), V0_LISTS, prefix="V0_"))
        add("dict_v0_terms_sha256", copy, label=LABELS["dict_v0_terms_sha256 (ws1_reliability.py copy)"])

    def llm():
        L = load("ws1_llm_channel")
        prompt = read("llm_channel_prompt_v1.txt")
        add("llm_prompt_sha256", sha256(prompt))
        add("llm_runner_sha256", sha256(read("ws1_llm_channel.py")))
        add("llm_spec_sha256", L.spec_sha256(sha256(prompt)))
        frags, _ = L.load_fragments(os.path.join(HERE, "coding_sample.csv"), os.path.join(HERE, "ws1_survey.html"))
        add("input_set_sha256", L.fragments_sha256(frags))
        table = L.frozen_table(os.path.abspath(__file__))
        res.append(("ws1_llm_channel.py reads these frozen values", "OK" if table == FROZEN
                    and all(k in FROZEN for k in L.FROZEN_KEYS.values()) else "FAIL",
                    "same table" if table == FROZEN else "different table", "same table"))
        ids = {f["id"] for f in frags}
        sec = section12()
        for name, want in SENSITIVITY_SETS.items():
            line = next((ln for ln in sec.split("\n") if ln.startswith(SENSITIVITY_MARKERS[name])), "")
            got = FRAG_ID.findall(line)
            res.append((f"section 12.3 list {name} ({len(want)} frag_ids, all among the 300)",
                        "OK" if got == want and set(want) <= ids and len(set(want)) == len(want) else "FAIL",
                        f"{len(got)} in the protocol, {len(set(want) - ids)} not among the 300",
                        f"{len(want)} in the protocol, 0 not among the 300"))
        written = set(FRAG_ID.findall(sec))
        unknown = sorted(written - ids)
        res.append(("every frag_id written in PROTOCOL_WS1.0.md section 12 is among the 300",
                    "OK" if written and not unknown else "FAIL",
                    f"{len(written)} distinct, not among the 300: {unknown}", "not among the 300: []"))

    def run_records():
        names = sorted(n for n in os.listdir(RUN_RECORD_DIR) if RUN_RECORD_GLOB.fullmatch(n))
        checked, other, bad = [], [], []
        for n in names:
            with open(os.path.join(RUN_RECORD_DIR, n), encoding="utf-8") as fh:
                rec = json.load(fh)
            if not isinstance(rec, dict):
                bad.append(f"{n}: not a JSON object")
                continue
            if rec.get("channel", LLM_CHANNEL) != LLM_CHANNEL:
                other.append(n)              # a record of another channel version is not a v1 record
                continue
            checked.append(n)
            diff = [k for k, fk in RUN_RECORD_KEYS.items() if rec.get(k) != FROZEN[fk]]
            if diff:
                bad.append(f"{n}: {', '.join(diff)} differ from FROZEN")
            lab = rec.get("labels_file")
            ok_name = isinstance(lab, str) and lab and os.path.basename(lab) == lab   # the runner writes a basename
            path = os.path.join(RUN_RECORD_DIR, lab) if ok_name else None
            if path is None or not os.path.isfile(path):
                bad.append(f"{n}: its labels file {lab!r} is not next to it")
            elif sha256(read_path(path)) != rec.get("labels_sha256"):
                bad.append(f"{n}: labels_sha256 is not the sha256 of {lab}")
        got = (f"{len(checked)} checked {checked}" if checked else "no run record of LLM channel v1 yet, nothing to check")
        got += (f"; other channel versions, not checked: {other}" if other else "")
        res.append(("run records of LLM channel v1 carry the frozen identities and their labels' sha256",
                    "OK" if not bad else "FAIL", got + (f"; problems: {bad}" if bad else ""),
                    "every run record matches"))

    def parity():
        page = load("make_artifact_page")
        prompt = read("llm_channel_prompt_v1.txt").decode("utf-8")
        add("practice_set", page.PRACTICE_SET)
        blocks = practice_blocks(page)
        missing = [k + 1 for k, b in enumerate(blocks) if b not in prompt]
        res.append(("instruction parity: the 8 practice items, answers and English explanations are in the "
                    "prompt verbatim", "OK" if len(blocks) == 8 and not missing else "FAIL",
                    f"{len(blocks)} items, missing from the prompt: {missing}", "8 items, missing from the prompt: []"))

    def protocol():
        sec = section12()
        missing = [k for k, v in FROZEN.items() if v not in sec]
        res.append(("every FROZEN value is written in PROTOCOL_WS1.0.md section 12",
                    "OK" if not missing else "FAIL", f"missing: {missing}", "missing: []"))

    guard("dictionary v1", dict_v1)
    guard("dictionary v0", dict_v0)
    guard("LLM channel v1 and input set", llm)
    guard("instruction parity", parity)
    guard("protocol section 12", protocol)
    guard("run records of LLM channel v1", run_records)
    return res


def main():
    res = checks()
    for label, status, got, want in res:
        print(f"{status:<11} {label}: {got}" + ("" if status == "OK" else f"  (frozen: {want})"))
    n_fail = sum(s == "FAIL" for _, s, _, _ in res)
    n_nc = sum(s == "NOT CHECKED" for _, s, _, _ in res)
    if n_fail:
        print(f"{n_fail} mismatch(es): a frozen identity was changed")
        return 1
    if n_nc:
        print(f"no mismatch, but {n_nc} identit(ies) could not be checked here")
        return 2
    print(f"all {len(res)} checks passed: every frozen identity matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
