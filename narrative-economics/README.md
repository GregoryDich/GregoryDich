# Narrative Economics — Research Project

Partnership **Gregory Diachenko (PI, Tel Aviv) + AI co-investigator**. Goal: build a measurable, falsifiable version of narrative economics (Shiller's open door) and bring it to publication.

**One-line thesis:** The "AI will take your job" narrative causally shifted labor-market behavior before AI shifted productivity; story contagiousness (R₀) is measurable from text and predicts the size of the real-world footprint.

## Project Documents
- **`ROADMAP.md`** — live monitor: dashboard, process stack, risk register, decision log, action queue.
- **`PREREGISTRATION.md`** — pre-analysis plan (H1–H6) for OSF (Russian working version).
- **`PREREGISTRATION_EN.md`** — English version ready for OSF upload.
- **`NARRATIVE_SHOCKS_REGISTRY.md`** — chronological catalog of narrative shocks (2022–2026).
- **`DEEP_ANALYSIS.md`** — competitor landscape, adversarial review by 4 judges, synergies.

## Code Pipeline (`code/`)

Full analysis pipeline validated on simulated data. Run `python run_all.py` — ALL 5 CHECKS PASS.

| Module | File | What it validates |
|--------|------|-------------------|
| Hawkes R₀ | `hawkes.py`, `build_poc.py` | Shock-aware MLE recovers true branching ratio (bias 1%) |
| DiD | `did_simulate.py` | TWFE recovers true β (bias 1.1%), flat pre-trends |
| LP-IRF | `local_projection.py` | Behavior responds to narrative BEFORE productivity (H1) |
| Placebo | `placebo_test.py` | Fictitious shocks yield null (p=0.000) |
| Exposure | `exposure_scores.py` | 26 key occupations with Eloundou GPT-α scores |
| Simulation | `simulate.py` | Two competing narratives with known R₀ |
| Growth proxy | `growth.py` | Exponential-growth R₀ from early take-off |
| GDELT | `gdelt_client.py` | Wired, needs egress allowlist |
| Master | `run_all.py` | Orchestrates all modules, unified report |

### Figures (generated)
- `fig1_infection_curves.png` — competing narrative intensity over time
- `fig2_branching_ratios.png` — naive vs shock-aware Hawkes comparison
- `fig3_shock_baseline.png` — estimated time-varying baseline μ(t)
- `fig4_event_study.png` — DiD event study with flat pre-trends
- `fig5_lp_irf.png` — LP-IRF showing narrative → behavior → productivity ordering
- `fig6_placebo.png` — placebo distribution vs real effect

### Quick Start
```bash
cd code
pip install -r requirements.txt
python run_all.py          # full pipeline (~11s)
python build_poc.py        # Hawkes only (with figures)
python did_simulate.py     # DiD only
python local_projection.py # LP-IRF only
python placebo_test.py     # placebo only
```

## Current Status
~14% on the scale. **Pre-registration LOCKED on OSF** (2026-06-20, observational Part A, registration osf.io/ehrac, project osf.io/j89yt, OSF Preregistration schema, embargo until 2027-06-23) — first irreversible priority anchor. Full analysis pipeline validated on simulation (ALL CHECKS PASS). Phase 1 autonomous. **Next blockers:** real data (GDELT egress / Revelio / YouTube transcripts).
