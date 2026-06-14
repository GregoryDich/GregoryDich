# PRE-ANALYSIS PLAN

**Title:** Competing Narratives of Creative Destruction: Why the AI-Displacement Story Outran Both the Opportunity Story and the Facts

**Authors:** G. D. (Tel Aviv, independent researcher); AI co-investigator
**Status:** Pre-analysis plan, registered prior to data access and prior to any estimation on outcome data.
**Registry:** OSF Registries (Part A — observational) + AEA RCT Registry (Part B — experiment, Phase 2).

---

## 0. Hypothesis Map

**Framework:** Two competing narratives about AI-driven creative destruction coexist — a **destruction narrative** ("AI will take your job") and a **creation narrative** ("AI gives new opportunity"). This paper provides the first empirical test of the competing-narratives model (Eliaz & Spiegler, 2020, AER) in a macroeconomic labor-market setting. The creation side is measured as a **reality benchmark**, NOT as a causal net-employment accounting exercise (see scope limitation in A.2).

- **H1 (co-primary):** The intensity of the destruction narrative causally precedes labor-market behavioral shifts — before any measurable effect of AI on productivity. *The narrative leads the fundamental.*
- **H2 (secondary):** The narrative's R₀ (branching ratio) predicts the magnitude of the behavioral response.
- **H3 (secondary):** The effect is concentrated in high-AI-exposure occupations (dose-response).
- **H4 (Phase 2, RCT):** Random exposure to the narrative causally shifts incentivized behavior.
- **H5 (secondary):** Contagion follows epidemic dynamics (Hawkes/SIR); narrative burnout predicts mean-reversion of behavior.
- **H6 (co-primary, valence asymmetry):** The negative narrative (destruction) has a higher R₀ and greater behavioral elasticity than the positive narrative (creation), even controlling for objective creation indicators. *Bad news is more contagious than good; the dominant narrative is selected by virality, not accuracy.*

**Primary tests:** H1 and H6 (Bonferroni-corrected, α = 0.025 each). Secondary family (H2, H3, H5): Romano-Wolf FWER control.

---

## PART A. Quasi-Experiment: Pre-Analysis Plan (OSF)

### A.1. Design

Difference-in-differences with continuous treatment intensity. Treatment: occupation-level AI exposure. Shock: surge in destruction-narrative intensity following the ChatGPT launch (November 30, 2022) and subsequent media peaks (GPT-4, Goldman report, WGA strike, etc.). Outcome data will not be accessed until this plan is locked.

- **Sample period:** January 2022 — March 2026 (pre-treatment: Jan–Nov 2022; post-treatment: Dec 2022 — Mar 2026).
- **Unit of observation:** occupation (SOC 6-digit) × week.
- **Treatment onset:** week of November 28, 2022 (ChatGPT public launch).
- **Minimum sample:** ≥ 50 SOC codes with valid exposure scores and behavioral outcome data.

### A.2. Data

**Narrative — Destruction (X−):**
YouTube auto-transcripts (Data API v3), Reddit archives (Arctic Shift), GDELT Global Knowledge Graph, Google Trends. Weekly index of "AI × occupation" narrative intensity via co-occurrence + LLM context classification. Validation: human-coded subsample (≥ 1,000 fragments, ≥ 2 coders, inter-rater κ ≥ 0.70).

**Narrative — Creation (X+):**
Same pipeline, second channel: "AI side hustle / vibe coding / AI democratizes access / build with AI." Comparison of R₀(X−) vs R₀(X+) tests H6.

**Creation reality benchmark (NOT causal):**
Census Business Formation Statistics (new business applications); Lightcast/Indeed (new AI-adjacent roles); creator proxies (Steam, itch.io, GitHub new repos, Hugging Face model uploads, App/Play Store); Upwork/Fiverr "AI services" listings (extends Hui 2024); Autor "new work" taxonomy.

> **SCOPE LIMITATION:** The creation side is used AS A BENCHMARK against which narrative distortion is visible. We do NOT causally attribute job creation to AI and do NOT claim net-employment accounting. That is the domain of Acemoglu/Autor/central banks. Our causal claim is about the narrative, not about net employment.

**Behavioral outcomes (Y):**
Revelio Labs (occupation transitions, career pivots into "AI-safe" fields); course enrollment proxies. Narrative source (X) and outcome source (Y) are **physically distinct datasets** — by design.

**Exposure scores:**
Eloundou et al. (2023) GPT-exposure α (primary); Felten AIOE, Webb patent-based AI exposure (robustness).

**Fundamental (lags behavior per H1):**
Industry/task-level AI productivity proxies.

### A.3. Specification

**Primary estimating equation (TWFE):**

    Y_it = α_i + γ_t + β · Exposure_i · NarrativeIntensity_t + X'_it δ + ε_it

Where:
- Y_it: behavioral outcome for occupation i at week t
- α_i, γ_t: occupation and time fixed effects
- Exposure_i: Eloundou GPT-exposure score (continuous, 0–1)
- NarrativeIntensity_t: weekly destruction-narrative index
- X_it: controls (region FE where available)
- β: causal parameter of interest (H1: β > 0)

**Event-study form:**

    Y_it = α_i + γ_t + Σ_k β_k · Exposure_i · 1(t ∈ bin_k) + ε_it

Reference period: last 8 weeks before ChatGPT launch (weeks −8 to −1 relative to treatment).

- Two-way fixed effects (occupation, time) + region where available.
- **Primary estimator:** Callaway & Sant'Anna (2021) for heterogeneous/staggered treatment; TWFE for comparability only.
- **Pre-trend test (falsification):** Joint F-statistic on all β_k for k < 0 must not reject H₀ at the 10% level. Rejection invalidates the design.
- Clustering at occupation level; wild-cluster bootstrap when the number of clusters is small (< 50).

### A.4. Narrative-Leads-Fundamental Test (Core of H1)

Temporal ordering: narrative index → behavioral shift → (later) productivity shift. Lags are pre-specified: 4, 8, 12, 16 weeks. Local-projection impulse-response functions. Lag length is NOT selected by significance — all are reported.

### A.5. Epidemic Model and R₀ (H2, H5, H6)

**Hawkes model with shock-aware baseline:**

    λ(t) = μ(t) + α · Σ_{j: t_j < t} exp(−β(t − t_j))
    μ(t) = μ₀ + Σ_k δ_k · exp(−γ(t − s_k)) · 1(t ≥ s_k)

Branching ratio n = α/β is the R₀ analog. Known exogenous shock times s_k are taken from the public narrative-shocks registry (ChatGPT launch, GPT-4, Goldman report, etc.).

- **H6 test:** One-sided: n̂(X−) > n̂(X+). Significance at α = 0.025 (Bonferroni-adjusted). Parametric bootstrap 90% CIs on each estimate. H6 is supported if the lower bound of [n̂(X−) − n̂(X+)] exceeds zero.
- **H2 test:** Cross-occupation regression of behavioral response magnitude on narrative R₀ (estimated per occupation cluster).
- **H5 test:** Post-peak phase (n declining below 1) predicts mean-reversion of behavioral outcome via local-projection IRF.
- SIR/Bass models as exposition/robustness. Primary = Hawkes (shock-aware).

### A.6. Robustness and Placebo Tests (Pre-Specified)

1. Placebo shocks on fictitious dates before November 2022 (no effect expected).
2. Alternative exposure scores (Felten AIOE, Webb).
3. Alternative index constructions (dictionary-based vs LLM-based; dual-index robustness per D18).
4. Leave-one-source-out (drop YouTube / Reddit / GDELT one at a time).
5. Sensitivity to LLM classification (reproduce on human-coded subsample).
6. Sun & Abraham (2021) as alternative estimator.
7. Israel multilingual diffusion lag (EN→HE→RU→AR via GDELT language filters) as additional identification variation.

### A.7. Multiple Testing

Co-primary: H1 + H6. Bonferroni correction for 2 tests: α = 0.025 each.
Secondary family (H2, H3, H5): Romano-Wolf step-down procedure controlling FWER at 5%.

### A.8. What Falsifies H1 (Pre-Declared)

Any of the following leads us to report that H1 is not supported:
- (a) Non-flat pre-trends (joint F rejects at 10%).
- (b) Behavior moves only AFTER (not before) a measurable productivity shift.
- (c) No dose-response (high-exposure occupations respond the same as low-exposure).

---

## PART B. RCT: Pre-Registration (AEA RCT Registry) — Phase 2

### B.1. Design

Information experiment in the tradition of Stantcheva (2023); Haaland, Roth & Wohlfart (2023). Individual-level randomization on Prolific, stratified by occupation AI-exposure.

### B.2. Sample and Recruitment

Employed adults recruited via Prolific; stratification by high/low AI-exposure of current occupation. Optional multilingual arm (Hebrew/Russian/Arabic recruitment via social-media ads in Israel) — extension, not primary. Exclusion criteria: failed attention checks, duplicate IP/device.

### B.3. Treatment Arms

- **Control:** No information treatment.
- **T1 (narrative):** Real news montage: "AI is displacing workers" (actual headlines, clips).
- **T2 (neutral/counter):** Neutral technology information — separates "narrative" from "any AI information."
- **(Optional) T3 (dose):** Intensified version for dose-response test.

### B.4. Outcomes

- **Primary (incentivized, behavioral):** Real allocation of bonus payment between investment in an "AI-safe" skill (e.g., course credit) and cash; and/or incentivized WTP for a real online course. Behavior with money, not stated intentions.
- **Secondary:** Stated intention to change career/reskill; subjective probability of own displacement; savings/portfolio reallocation intention.

### B.5. Hypotheses

H4: T1 shifts primary outcome relative to Control. Dose-response: T3 > T1. Pre-specified heterogeneity: AI-exposure, age, baseline beliefs.

### B.6. Power

Target MDE = 0.15 SD at 80% power, α = 0.05. Required N per arm to be calculated and locked before data collection (order of magnitude: several hundred per arm). Analysis code written and tested against simulated data before real collection.

### B.7. Analysis

ITT, OLS with pre-specified covariates (age, exposure, baseline beliefs); multiple-testing correction for secondary outcomes; manipulation/attention checks reported; mandatory debriefing.

### B.8. Ethics

Presentation of real news clips is a standard low-risk information-provision procedure. Informed consent; debriefing post-survey; no deception beyond the standard. IRB approval required (institutional or commercial) before data collection begins.
