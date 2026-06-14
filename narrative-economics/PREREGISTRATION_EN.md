# Pre-Analysis Plan

**Competing Narratives of Creative Destruction: Why the AI-Displacement Story Outran Both the Opportunity Story and the Facts**

Gregory Diachenko (Tel Aviv)

Registered prior to accessing outcome data or running any estimation. Part A (observational) filed on OSF; Part B (experiment) to be filed on AEA RCT Registry upon IRB approval.

---

## Hypotheses

The starting observation is that two narratives about AI and work compete for attention: one about destruction ("AI will take your job") and one about creation ("AI opens new doors"). Eliaz and Spiegler (2020, AER) formalized how competing narratives shape beliefs; we test their model empirically in a labor-market setting. The creation narrative serves as a factual benchmark — we measure it to show that the destruction story dominates attention disproportionately to underlying reality, not to do net-employment accounting (that is Acemoglu and Autor territory, and we stay out of it).

**H1 (co-primary).** The destruction narrative causally precedes labor-market behavioral shifts, arriving before any measurable AI effect on productivity.

**H2.** A narrative's estimated R₀ (Hawkes branching ratio) predicts the magnitude of the subsequent behavioral response across occupations.

**H3.** The effect concentrates in high-AI-exposure occupations (dose-response).

**H4 (Phase 2).** Randomly showing subjects the destruction narrative shifts their incentivized career-investment decisions.

**H5.** Narrative contagion follows epidemic dynamics; the burnout phase predicts mean-reversion in behavior.

**H6 (co-primary).** The destruction narrative has a higher R₀ and a larger behavioral elasticity than the creation narrative, controlling for objective creation indicators. The dominant story is selected by contagiousness, not by accuracy.

H1 and H6 are tested at α = 0.025 each (Bonferroni for two co-primaries). H2, H3, H5 form a secondary family under Romano-Wolf step-down control at 5%.

---

## Part A — Observational Study (OSF)

### A.1 Design

Difference-in-differences with continuous treatment. The treatment variable is occupation-level AI exposure; the shock is the surge in destruction-narrative intensity after the ChatGPT launch on November 30, 2022, and the media peaks that followed (GPT-4, the Goldman "300 million jobs" report, the WGA strike, and others documented in our narrative-shocks registry).

We will not access outcome data until this plan is locked.

- Sample period: January 2022 through March 2026.
- Pre-treatment window: January–November 2022.
- Unit of observation: occupation (6-digit SOC) by week.
- Treatment onset: week of November 28, 2022.
- We require at least 50 SOC codes with valid exposure scores and behavioral data.

### A.2 Data

*Destruction narrative (X−).* Weekly intensity index constructed from YouTube auto-transcripts (Data API v3), Reddit archives (Arctic Shift), the GDELT Global Knowledge Graph, and Google Trends. Each text fragment is classified for AI-occupation co-occurrence using both a keyword dictionary and an LLM classifier. Validation requires a human-coded subsample of at least 1,000 fragments with two independent coders reaching κ ≥ 0.70.

*Creation narrative (X+).* Same pipeline applied to a second lexical channel: "AI side hustle," "vibe coding," "AI democratizes," and related phrases. Comparing R₀(X−) to R₀(X+) directly tests H6.

*Creation benchmark.* Census Business Formation Statistics (new business applications), Lightcast and Indeed postings for AI-adjacent roles, creator-economy proxies (Steam, GitHub new repos, Hugging Face uploads, App Store), and Upwork/Fiverr AI-service listings (extending Hui, Reshef, and Zhou 2024). We use these to show where the creation narrative departs from the creation reality — we are not attributing job creation to AI causally.

*Behavioral outcomes (Y).* Revelio Labs occupation-transition flows (career pivots into fields less exposed to AI) and course-enrollment proxies. The narrative data (X) and behavioral data (Y) come from physically separate sources, which is important for ruling out mechanical correlation.

*Exposure.* Eloundou et al. (2023) GPT-exposure scores as the primary measure. Felten AIOE and Webb patent-based scores for robustness.

*Productivity fundamental.* Industry- and task-level proxies of actual AI-driven productivity gains. Under H1 these should lag both the narrative and the behavioral response.

### A.3 Specification

The primary estimating equation is a two-way fixed-effects model:

    Y_it = α_i + γ_t + β · Exposure_i · NarrativeIntensity_t + X'_it δ + ε_it

with occupation fixed effects α_i, week fixed effects γ_t, the Eloundou exposure score interacted with the weekly narrative index, and optional regional controls. β is the parameter of interest; under H1 it should be positive.

The event-study version replaces the continuous narrative interaction with binned relative-time dummies:

    Y_it = α_i + γ_t + Σ_k β_k · Exposure_i · 1(t ∈ bin_k) + ε_it

The omitted category is weeks −8 to −1 relative to the ChatGPT launch. We use 8-week bins.

The primary estimator is Callaway and Sant'Anna (2021), which handles heterogeneous treatment timing. Standard TWFE is reported for comparability. Standard errors are clustered at the occupation level. If the number of clusters falls below 50, we switch to wild-cluster bootstrap.

The pre-trend test is the joint F-statistic on all pre-treatment β_k. If it rejects at the 10% level, we treat the design as compromised and report H1 as unsupported.

### A.4 Temporal-ordering test

This is the core of H1. We estimate local-projection impulse-response functions (Jordà 2005) at pre-specified horizons of 4, 8, 12, and 16 weeks. The prediction: the narrative index should affect behavior at shorter horizons (4–8 weeks) than it affects productivity (12+ weeks). All horizons are reported; we do not select lags by significance.

### A.5 Epidemic model

We fit a univariate Hawkes self-exciting point process to each narrative's event stream. The conditional intensity is:

    λ(t) = μ(t) + α Σ_{j: t_j < t} exp(−β(t − t_j))

where the baseline μ(t) absorbs known exogenous shocks (ChatGPT launch, GPT-4, etc.) via exponential decay terms:

    μ(t) = μ₀ + Σ_k δ_k exp(−γ(t − s_k)) · 1(t ≥ s_k)

The branching ratio n = α/β is the R₀ analog. For H6, we test n̂(X−) > n̂(X+) one-sided at α = 0.025 using parametric-bootstrap confidence intervals. H6 is supported if the lower bound of the difference exceeds zero. For H2, we regress the occupation-level behavioral response on the occupation-cluster R₀. For H5, we check whether the post-peak decline in n predicts behavioral mean-reversion via local-projection IRF. SIR and Bass models appear in the paper as exposition but are not primary.

### A.6 Robustness battery

All pre-specified:

1. Placebo shocks at fictitious dates before November 2022.
2. Felten AIOE and Webb scores replacing Eloundou.
3. Dictionary-only index vs. LLM-only index (if both agree, the result is robust to the classification method).
4. Leave-one-source-out: drop YouTube, Reddit, or GDELT in turn.
5. Reproduce the main result on the human-coded subsample only.
6. Sun and Abraham (2021) as an alternative heterogeneity-robust estimator.
7. Israel multilingual lag: GDELT distinguishes languages, so we can trace diffusion from English to Hebrew to Russian to Arabic and use the lag structure as additional identification.

### A.7 Multiple testing

H1 + H6 are co-primary, corrected via Bonferroni (α = 0.025 each). The secondary family {H2, H3, H5} is corrected via Romano-Wolf step-down at FWER = 5%.

### A.8 Falsification

We commit in advance: H1 is reported as unsupported if any of the following holds:

(a) Pre-trends are not flat (joint F rejects at 10%).
(b) Behavioral shifts appear only after — not before — a measurable productivity change.
(c) There is no dose-response across exposure levels.

---

## Part B — RCT (AEA RCT Registry, Phase 2)

### B.1 Design

Information-provision experiment following Haaland, Roth, and Wohlfart (2023). Individual-level randomization on Prolific, stratified by occupation AI-exposure.

### B.2 Sample

Employed adults on Prolific. Stratification: high vs. low AI-exposure of current occupation. An optional multilingual arm recruits participants in Israel (Hebrew, Russian, Arabic) via social-media ads — this is an extension, not part of the primary analysis. We exclude respondents who fail attention checks or appear as duplicates by IP or device fingerprint.

### B.3 Arms

- Control: no treatment.
- T1: a montage of real news clips about AI displacing workers.
- T2: neutral technology information (separates "narrative about AI jobs" from "any information about AI").
- T3 (optional): intensified T1 for a dose-response check.

### B.4 Outcomes

Primary (incentivized): subjects allocate a real bonus between an "AI-safe" skill investment (e.g., a course credit) and cash. This measures behavior with money, not stated intentions. Secondary: intention to reskill or switch careers; subjective displacement probability; savings reallocation intention.

### B.5 Hypotheses

H4: T1 shifts the primary outcome relative to Control. Dose-response: T3 > T1. Pre-specified heterogeneity dimensions: AI-exposure, age, prior beliefs about AI.

### B.6 Power

We target an MDE of 0.15 SD at 80% power with α = 0.05. The exact N per arm will be computed and locked before any data collection. Order of magnitude: several hundred per arm. Analysis code is written and tested against simulated data before data collection begins.

### B.7 Analysis

Intent-to-treat, OLS with pre-specified covariates (age, exposure, prior beliefs). Secondary outcomes corrected for multiplicity. Manipulation and attention checks reported. Debriefing is mandatory.

### B.8 Ethics

Showing participants real news clips is a standard low-risk information-provision procedure used widely in experimental economics. Informed consent is obtained; debriefing follows the survey; no deception is involved. IRB approval (institutional or commercial) is required before data collection.
