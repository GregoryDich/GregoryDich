"""
exposure_scores.py — occupation-level AI-exposure scores (WS3).

Primary source (pre-registration A.2): Eloundou, Manning, Mishkin & Rock
(2023), "GPTs are GPTs", arXiv:2303.10130. Occupation-level scores are read
from the authors' public repository (openai/GPTs-are-GPTs, MIT licence),
stored in data/exposure/eloundou/. Robustness (pre-registration A.6 item 2):
Felten, Raj & Seamans AIOE and Webb (2020) patent-based scores.

Provenance, SHA-256 checksums, column definitions and the proposed choice of
primary measure are documented in data/exposure/README.md. Every number this
module returns comes from those files; nothing is typed in by hand.

The six Eloundou measures (names used in this module -> column in the file):

    human_alpha  human_rating_alpha   human annotators, E1
    human_beta   human_rating_beta    human annotators, E1 + 0.5*E2
    human_gamma  human_rating_gamma   human annotators, E1 + E2  (zeta in the paper)
    gpt4_alpha   dv_rating_alpha      GPT-4 (rubric 1), E1
    gpt4_beta    dv_rating_beta       GPT-4 (rubric 1), E1 + 0.5*E2
    gpt4_gamma   dv_rating_gamma      GPT-4 (rubric 1), E1 + E2  (zeta in the paper)

Each is the share (0-1) of an occupation's O*NET tasks rated exposed, with core
tasks weighted twice as heavily as supplemental ones (verified: this rule
reproduces occ_level.csv exactly from full_labelset.tsv). Parts of the paper
(Table 4, Figures 3 and 5) use equal task weights instead; which weighting
the analysis uses is an open choice documented in data/exposure/README.md.

Aggregation to 6-digit SOC (the pre-registered unit, A.1): the file is keyed by
8-digit O*NET-SOC 2019 codes (e.g. 15-1252.00), which nest inside 2018 SOC
codes. A 6-digit SOC score is the unweighted mean of its detailed O*NET-SOC
rows; `n_onet` records how many rows were averaged (798 SOC codes from 923
O*NET-SOC rows; 67 SOC codes have more than one row). No employment weights
exist below the 6-digit level, so the mean is unweighted. 24 SOC codes have
no '.00' row and are flagged `has_base_row == False` (see aggregate_to_soc);
they are kept, not dropped, until the PI decides how to treat them.

Felten AIOE uses 2010 SOC codes and Webb uses occ1990dd codes; neither can be
merged with the 2018-SOC Eloundou scores without a crosswalk that is not yet in
the repository (see README, "Open issues").
"""
import hashlib
import os
import urllib.request
import warnings

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
EXPOSURE_DIR = os.path.join(DATA, "exposure")

# Measure name -> column in occ_level.csv.
ELOUNDOU_COLUMNS = {
    "human_alpha": "human_rating_alpha",
    "human_beta": "human_rating_beta",
    "human_gamma": "human_rating_gamma",
    "gpt4_alpha": "dv_rating_alpha",
    "gpt4_beta": "dv_rating_beta",
    "gpt4_gamma": "dv_rating_gamma",
}
ELOUNDOU_MEASURES = tuple(ELOUNDOU_COLUMNS)

# Proposed primary measure. It is a proposal until the PI logs it as a decision
# in ROADMAP.md before any outcome data is seen; the rationale is in
# data/exposure/README.md ("Primary measure"). The other five are robustness.
PRIMARY_MEASURE = "human_beta"

# Occupations central to H1/H6, kept as SOC codes only; titles and scores are
# read from the data. 31-1131 is the 2018-SOC code for Nursing Assistants
# (2010 SOC: 31-1014, which does not exist in the source file).
KEY_OCCUPATIONS = (
    "15-1252", "15-1251", "27-3042", "13-2011", "23-1011", "43-9021",
    "27-3041", "13-1161", "11-2021", "25-1011", "43-4051", "41-3021",
    "47-2061", "37-2011", "51-4121", "53-3032", "35-2014", "39-9011",
    "29-1141", "31-1131", "11-1021", "41-1012", "43-6014", "13-1071",
    "27-1024", "19-3011",
)

# Every external file: where it comes from and its SHA-256 at retrieval
# (2026-10-10). `tracked` files are committed (licence permits it); the others
# are git-ignored and must be fetched with download().
_RAW = "https://raw.githubusercontent.com"
SOURCES = {
    "eloundou/occ_level.csv": {
        "url": f"{_RAW}/openai/GPTs-are-GPTs/main/data/occ_level.csv",
        "sha256": "40c74f53de40aec91c0017d80690cbba915f83a8bb414bcf2f884692f1749acb",
        "tracked": True,
    },
    "eloundou/full_labelset.tsv": {
        "url": f"{_RAW}/openai/GPTs-are-GPTs/main/data/full_labelset.tsv",
        "sha256": "094378905e1f3349e50a9a83dc69643a2ef227954d611c8316a46da08cb3d8de",
        "tracked": True,
    },
    "eloundou/LICENSE": {
        "url": f"{_RAW}/openai/GPTs-are-GPTs/main/LICENSE",
        "sha256": "d831db55645e47ca8e491c5a0e37f1ee744d7b10bf5aa8d50146c795ac0176c0",
        "tracked": True,
    },
    "felten/AIOE_DataAppendix.xlsx": {
        "url": f"{_RAW}/AIOE-Data/AIOE/main/AIOE_DataAppendix.xlsx",
        "sha256": "c123b4c64840aff3568ae6c97256678719b88a74d45b6362dbefb5af34667b95",
        "tracked": False,
    },
    "felten/Language Modeling AIOE and AIIE.xlsx": {
        "url": f"{_RAW}/AIOE-Data/AIOE/main/Language%20Modeling%20AIOE%20and%20AIIE.xlsx",
        "sha256": "ccdd1fb916dfa404914367eafde7c00b7148ea86f18fe616240bc85cf6131c8b",
        "tracked": False,
    },
    # Unofficial third-party copy; the official source (Webb's data page) was
    # unreachable. Not verified against the original — see README.
    "webb/exposure_by_occ1990dd_lswt2010.csv": {
        "url": (f"{_RAW}/demirev/ai-products/master/data/webb/"
                "exposure_by_occ1990dd_lswt2010.csv"),
        "sha256": "c5652fd3f862948cb77d87f38aa8296137c51e028992ab54e57246a066e0a779",
        "tracked": False,
    },
}


# --------------------------------------------------------------------------
# Download and integrity checks
# --------------------------------------------------------------------------

def sha256_of(path):
    """Return the hex SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(keys=None, force=False):
    """Fetch source files into data/exposure/ and verify their SHA-256.

    keys: iterable of SOURCES keys; default = every file that is missing.
    A file whose checksum differs from the recorded one is not kept: the
    upstream file has changed and the provenance record must be updated
    deliberately, not silently.
    """
    keys = list(SOURCES) if keys is None else list(keys)
    for key in keys:
        src = SOURCES[key]
        path = os.path.join(EXPOSURE_DIR, key)
        if os.path.exists(path) and not force:
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"  [exposure_scores] downloading {src['url']}")
        with urllib.request.urlopen(src["url"], timeout=120) as r:
            payload = r.read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != src["sha256"]:
            raise RuntimeError(
                f"SHA-256 mismatch for {key}: got {digest}, expected "
                f"{src['sha256']}. Upstream changed; file not saved.")
        with open(path, "wb") as f:
            f.write(payload)


def verify(keys=None):
    """Check stored files against recorded SHA-256. Returns {key: status}."""
    out = {}
    for key in (SOURCES if keys is None else keys):
        path = os.path.join(EXPOSURE_DIR, key)
        if not os.path.exists(path):
            out[key] = "missing"
        else:
            ok = sha256_of(path) == SOURCES[key]["sha256"]
            out[key] = "ok" if ok else "CHECKSUM MISMATCH"
    return out


def _require(key):
    path = os.path.join(EXPOSURE_DIR, key)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run `python exposure_scores.py download` "
            f"(source: {SOURCES[key]['url']}).")
    return path


# --------------------------------------------------------------------------
# Eloundou et al. (2023) — primary
# --------------------------------------------------------------------------

def load_eloundou_onet(path=None):
    """Eloundou scores at the detailed O*NET-SOC level (923 rows).

    Columns: onet_soc (e.g. '15-1252.00'), soc (6-digit, e.g. '15-1252'),
    title, and the six measures named as in ELOUNDOU_MEASURES.
    """
    path = path or _require("eloundou/occ_level.csv")
    raw = pd.read_csv(path, dtype={"O*NET-SOC Code": str})
    df = raw.rename(columns={"O*NET-SOC Code": "onet_soc", "Title": "title"})
    df = df.rename(columns={v: k for k, v in ELOUNDOU_COLUMNS.items()})
    df["soc"] = df["onet_soc"].str[:7]
    return df[["onet_soc", "soc", "title", *ELOUNDOU_MEASURES]]


def aggregate_to_soc(onet):
    """Aggregate O*NET-SOC rows to 6-digit SOC (unweighted mean).

    Returns one row per SOC with the six measures, n_onet (number of
    detailed rows averaged), has_base_row, onet_codes ('; '-joined) and title.

    has_base_row is False when the SOC code has no '.00' O*NET row (24 codes
    in the published file, all ending in 9). For these the score is the mean
    of only the O*NET specialties that happen to be listed, so it need not
    represent the whole SOC category; whether they enter the analysis is a
    specification choice (see data/exposure/README.md). Their title is
    marked '[no .00 row; N specialty row(s)] <first specialty title>' so a
    specialty title is never mistaken for the SOC title.
    """
    onet = onet.sort_values("onet_soc")
    g = onet.groupby("soc", sort=True)
    out = g[list(ELOUNDOU_MEASURES)].mean()
    out["n_onet"] = g.size()
    out["onet_codes"] = g["onet_soc"].agg("; ".join)
    base = onet[onet["onet_soc"].str.endswith(".00")].set_index("soc")["title"]
    out["has_base_row"] = out.index.isin(base.index)
    marked = ("[no .00 row; " + out["n_onet"].astype(str) + " specialty row(s)] "
              + g["title"].first())
    out["title"] = base.reindex(out.index).fillna(marked)
    out = out.reset_index()
    return out[["soc", "title", *ELOUNDOU_MEASURES, "n_onet", "has_base_row",
                "onet_codes"]]


def load_eloundou(path=None):
    """Eloundou scores aggregated to 6-digit SOC (798 rows)."""
    return aggregate_to_soc(load_eloundou_onet(path))


def get_scores(measure=PRIMARY_MEASURE, level="soc", path=None):
    """Return one Eloundou measure as a Series indexed by occupation code.

    measure: one of ELOUNDOU_MEASURES.
    level: 'soc' (6-digit SOC, mean over detailed codes) or 'onet'
           (8-digit O*NET-SOC, as published).
    """
    if measure not in ELOUNDOU_COLUMNS:
        raise ValueError(f"measure must be one of {ELOUNDOU_MEASURES}")
    if level == "soc":
        df, key = load_eloundou(path), "soc"
    elif level == "onet":
        df, key = load_eloundou_onet(path), "onet_soc"
    else:
        raise ValueError("level must be 'soc' or 'onet'")
    return df.set_index(key)[measure].rename(measure)


# --------------------------------------------------------------------------
# Robustness measures (not mergeable with Eloundou without a crosswalk)
# --------------------------------------------------------------------------

def load_felten_aioe(variant="aioe"):
    """Felten, Raj & Seamans AIOE by occupation (774 rows, 2010 SOC codes).

    variant: 'aioe' = original AIOE (Data Appendix A, Felten et al. 2021 SMJ);
             'lm'   = language-modeling AIOE from the same repository.
    Scores are standardized (mean 0, sd 1). The `soc` column is 2010 SOC and
    must be crosswalked before merging with the 2018-SOC Eloundou scores.
    """
    if variant == "aioe":
        key, sheet, col = "felten/AIOE_DataAppendix.xlsx", "Appendix A", "AIOE"
    elif variant == "lm":
        key, sheet, col = ("felten/Language Modeling AIOE and AIIE.xlsx",
                           "LM AIOE", "Language Modeling AIOE")
    else:
        raise ValueError("variant must be 'aioe' or 'lm'")
    df = pd.read_excel(_require(key), sheet_name=sheet, engine="openpyxl",
                       dtype={"SOC Code": str})
    df = df.rename(columns={"SOC Code": "soc", "Occupation Title": "title",
                            col: "aioe" if variant == "aioe" else "lm_aioe"})
    df["soc_vintage"] = "2010"
    return df


def load_webb():
    """Webb (2020) exposure by occ1990dd (341 rows): pct_ai, pct_software, pct_robot.

    WARNING: the stored file is an unofficial third-party copy (see SOURCES);
    it has not been checked against the file on Webb's own data page.
    """
    warnings.warn("Webb scores come from an unverified third-party mirror; "
                  "see data/exposure/README.md before using them.")
    return pd.read_csv(_require("webb/exposure_by_occ1990dd_lswt2010.csv"))


# --------------------------------------------------------------------------
# Backward-compatible helpers (names kept from the first version)
# --------------------------------------------------------------------------

def get_sample_scores(measure=PRIMARY_MEASURE):
    """Key occupations (KEY_OCCUPATIONS) with real scores from the data.

    Returns soc, title, score (= `measure`), the six measures and n_onet,
    sorted by score. The earlier version returned hand-typed 'alpha' values
    with no source; those were removed (see AUDIT_hardcoded_vs_source.md).
    """
    df = load_eloundou()
    df = df[df["soc"].isin(KEY_OCCUPATIONS)].copy()
    missing = sorted(set(KEY_OCCUPATIONS) - set(df["soc"]))
    if missing:
        raise KeyError(f"key SOC codes not in source: {missing}")
    df.insert(2, "score", df[measure])
    cols = ["soc", "title", "score", *ELOUNDOU_MEASURES, "n_onet"]
    return df[cols].sort_values("score", ascending=False).reset_index(drop=True)


def load_full_scores(path=None):
    """All 6-digit SOC codes with the six Eloundou measures (see load_eloundou).

    path: optional alternative copy of occ_level.csv. There is no fallback to
    a curated sample: if the file is missing this raises FileNotFoundError.
    """
    return load_eloundou(path)


def classify_exposure(score, thresholds=(0.33, 0.66)):
    """Label a score 'low'/'medium'/'high' by fixed cut-offs.

    The default cut-offs are arbitrary placeholders, not terciles and not
    pre-registered; for empirical terciles use pd.qcut(scores, 3).
    """
    lo, hi = thresholds
    if score < lo:
        return "low"
    elif score < hi:
        return "medium"
    else:
        return "high"


def exposure_summary(measure=PRIMARY_MEASURE):
    """Print summary statistics of `measure` over all SOC codes; return them."""
    df = load_eloundou()
    s = df[measure]
    print(f"  Eloundou et al. (2023), measure = {measure}")
    print(f"  O*NET-SOC rows = {int(df['n_onet'].sum())}, "
          f"6-digit SOC codes = {len(df)} "
          f"({int((df['n_onet'] > 1).sum())} with >1 detailed code, "
          f"{int((~df['has_base_row']).sum())} without a .00 row)")
    print(f"  Mean = {s.mean():.3f}, SD = {s.std():.3f}, "
          f"range [{s.min():.3f}, {s.max():.3f}]")
    return df


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["download"]:
        download()
        for k, v in verify().items():
            print(f"  {v:>17s}  {k}")
        sys.exit(0)
    print("=" * 60)
    print(" AI-EXPOSURE SCORES — Eloundou et al. (2023) (WS3)")
    print("=" * 60)
    for k, v in verify().items():
        print(f"  {v:>17s}  {k}")
    print()
    exposure_summary()
    print()
    full = load_eloundou()
    print("  Correlation (Pearson) across SOC codes:")
    print(full[list(ELOUNDOU_MEASURES)].corr().round(2).to_string())
    print(f"\n  Key occupations, sorted by {PRIMARY_MEASURE}:")
    for _, r in get_sample_scores().iterrows():
        print(f"    {r['soc']}  {r['title'][:42]:<42s}  "
              f"human_beta={r['human_beta']:.3f}  gpt4_beta={r['gpt4_beta']:.3f}")
