"""
exposure_scores.py — AI-exposure scores for occupations (WS3).

Primary: Eloundou et al. (2023) "GPTs are GPTs" exposure scores (alpha).
Robustness: Felten AIOE, Webb patent-based AI exposure.

This module provides:
1. A curated set of key occupations with known exposure scores.
2. Functions to load full score datasets from CSV (user supplies file).
3. Mapping between SOC codes and exposure for the DiD pipeline.

Reference:
    Eloundou, T., Manning, S., Mishkin, P., & Rock, D. (2023).
    GPTs are GPTs: An Early Look at the Labor Market Impact Potential
    of Large Language Models. arXiv:2303.10130.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Representative occupations with approximate Eloundou alpha scores.
# These are occupations central to our hypotheses (H1, H6).
# Full dataset: download from OpenAI supplementary materials.
ELOUNDOU_SAMPLE = {
    # (SOC code, title): alpha_score (0-1, higher = more exposed to GPT)
    ("15-1252", "Software Developers"): 0.81,
    ("15-1251", "Computer Programmers"): 0.89,
    ("27-3042", "Technical Writers"): 0.87,
    ("13-2011", "Accountants and Auditors"): 0.83,
    ("23-1011", "Lawyers"): 0.75,
    ("43-9021", "Data Entry Keyers"): 0.91,
    ("27-3041", "Editors"): 0.85,
    ("13-1161", "Market Research Analysts"): 0.79,
    ("11-2021", "Marketing Managers"): 0.72,
    ("25-1011", "Business Professors"): 0.68,
    ("43-4051", "Customer Service Reps"): 0.76,
    ("41-3021", "Insurance Sales Agents"): 0.71,
    # Low-exposure occupations (manual/physical)
    ("47-2061", "Construction Laborers"): 0.08,
    ("37-2011", "Janitors and Cleaners"): 0.05,
    ("51-4121", "Welders"): 0.09,
    ("53-3032", "Heavy Truck Drivers"): 0.11,
    ("35-2014", "Cooks, Restaurant"): 0.07,
    ("39-9011", "Childcare Workers"): 0.12,
    ("29-1141", "Registered Nurses"): 0.35,
    ("31-1014", "Nursing Assistants"): 0.14,
    # Medium-exposure
    ("11-1021", "General Managers"): 0.58,
    ("41-1012", "First-Line Sales Supervisors"): 0.45,
    ("43-6014", "Secretaries (except Legal/Med)"): 0.63,
    ("13-1071", "HR Specialists"): 0.66,
    ("27-1024", "Graphic Designers"): 0.71,
    ("19-3011", "Economists"): 0.76,
}


def get_sample_scores():
    """Return curated sample as DataFrame with SOC, title, alpha columns."""
    rows = []
    for (soc, title), alpha in ELOUNDOU_SAMPLE.items():
        rows.append({"soc": soc, "title": title, "alpha": alpha})
    return pd.DataFrame(rows).sort_values("alpha", ascending=False)


def load_full_scores(path=None):
    """Load full Eloundou exposure scores from CSV.

    Expected columns: soc, title, alpha (or exposure).
    If path is None, checks data/eloundou_scores.csv.
    """
    if path is None:
        path = os.path.join(DATA, "eloundou_scores.csv")
    if not os.path.exists(path):
        print(f"  [exposure_scores] Full dataset not found at {path}")
        print(f"  Using curated sample ({len(ELOUNDOU_SAMPLE)} occupations)")
        return get_sample_scores()
    df = pd.read_csv(path)
    if "exposure" in df.columns and "alpha" not in df.columns:
        df = df.rename(columns={"exposure": "alpha"})
    return df


def classify_exposure(alpha, thresholds=(0.33, 0.66)):
    """Classify occupations into low/medium/high exposure terciles."""
    lo, hi = thresholds
    if alpha < lo:
        return "low"
    elif alpha < hi:
        return "medium"
    else:
        return "high"


def exposure_summary():
    """Print summary statistics for the sample scores."""
    df = get_sample_scores()
    print(f"  Exposure score sample: N = {len(df)}")
    print(f"  Mean alpha = {df['alpha'].mean():.3f}")
    print(f"  Std  alpha = {df['alpha'].std():.3f}")
    print(f"  Range: [{df['alpha'].min():.2f}, {df['alpha'].max():.2f}]")
    print(f"  High-exposure (>0.66): {(df['alpha'] > 0.66).sum()} occupations")
    print(f"  Low-exposure  (<0.33): {(df['alpha'] < 0.33).sum()} occupations")
    return df


if __name__ == "__main__":
    print("=" * 50)
    print(" AI-EXPOSURE SCORES — SAMPLE (WS3)")
    print("=" * 50)
    df = exposure_summary()
    print("\n  Top 5 exposed:")
    for _, row in df.head(5).iterrows():
        print(f"    {row['soc']}  {row['title']:<35s}  alpha={row['alpha']:.2f}")
    print("\n  Bottom 5 exposed:")
    for _, row in df.tail(5).iterrows():
        print(f"    {row['soc']}  {row['title']:<35s}  alpha={row['alpha']:.2f}")
