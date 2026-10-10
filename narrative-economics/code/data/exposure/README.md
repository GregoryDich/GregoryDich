# AI-exposure data (WS3)

Occupation-level AI-exposure scores used as the treatment intensity
`Exposure_i` in the pre-registered design (PREREGISTRATION_EN.md, A.2 and A.3).
All files were retrieved on **2026-10-10** through `raw.githubusercontent.com`.
`code/exposure_scores.py` loads them; `python exposure_scores.py download`
fetches anything missing and refuses any file whose SHA-256 differs from the
values below.

| Stored path (under `code/data/exposure/`) | Source URL | SHA-256 | Size (bytes) | Licence | In git? |
|---|---|---|---:|---|---|
| `eloundou/occ_level.csv` | https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv | `40c74f53de40aec91c0017d80690cbba915f83a8bb414bcf2f884692f1749acb` | 126,022 | MIT | yes |
| `eloundou/full_labelset.tsv` | https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/full_labelset.tsv | `094378905e1f3349e50a9a83dc69643a2ef227954d611c8316a46da08cb3d8de` | 3,893,248 | MIT | yes |
| `eloundou/LICENSE` | https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/LICENSE | `d831db55645e47ca8e491c5a0e37f1ee744d7b10bf5aa8d50146c795ac0176c0` | 1,063 | — | yes |
| `eloundou/README_upstream.md` | https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/README.md | `fb8ae66d02142a9b7178d8cbd59b90a6c5bd80bf088107cae126f4276c8d68c6` | 172 | MIT | yes |
| `felten/AIOE_DataAppendix.xlsx` | https://raw.githubusercontent.com/AIOE-Data/AIOE/main/AIOE_DataAppendix.xlsx | `c123b4c64840aff3568ae6c97256678719b88a74d45b6362dbefb5af34667b95` | 170,359 | none found | no (ignored) |
| `felten/Language Modeling AIOE and AIIE.xlsx` | https://raw.githubusercontent.com/AIOE-Data/AIOE/main/Language%20Modeling%20AIOE%20and%20AIIE.xlsx | `ccdd1fb916dfa404914367eafde7c00b7148ea86f18fe616240bc85cf6131c8b` | 55,714 | none found | no (ignored) |
| `webb/exposure_by_occ1990dd_lswt2010.csv` | https://raw.githubusercontent.com/demirev/ai-products/master/data/webb/exposure_by_occ1990dd_lswt2010.csv (**unofficial copy**) | `c5652fd3f862948cb77d87f38aa8296137c51e028992ab54e57246a066e0a779` | 21,263 | none found | no (ignored) |

Other files in this folder: `audit_hardcoded.py` and its output
`AUDIT_hardcoded_vs_source.md` (audit of the hand-typed values the first
version of `exposure_scores.py` contained).

---

## 1. Eloundou et al. (2023) — primary measure

**Citation.** Eloundou, T., Manning, S., Mishkin, P., & Rock, D. (2023). *GPTs
are GPTs: An Early Look at the Labor Market Impact Potential of Large Language
Models.* arXiv:2303.10130. The version read for this README is dated
22 August 2023 (full text obtained through the Hugging Face papers mirror of
arXiv; arxiv.org itself is blocked from this environment). A shorter version
appeared as "GPTs are GPTs: Labor market impact potential of LLMs", *Science*
384, 1306–1308 (2024). Title, volume, pages and year are confirmed by the EIG
replication README (read directly). The issue number (6702) and the DOI
(10.1126/science.adj0998) come from search results only. **TODO-verify**
both. The *Science* text itself was not read (blocked).

**Repository.** github.com/openai/GPTs-are-GPTs, branch `main`. The commit SHA
could not be recorded, because the GitHub API and web pages are blocked here
and the session's GitHub connector is restricted to this project's repository.
To locate the exact upstream version, use the git blob SHA-1 (`git hash-object`)
of each stored file:

| File | git blob SHA-1 |
|---|---|
| `occ_level.csv` | `faf734ccef32b373b16899d40636a9ff8de52a40` |
| `full_labelset.tsv` | `226e19b4082353b6fcf9e87cd416a815bd5ab66a` |
| `LICENSE` | `91ba98f3a21392ddd8c0e375f1f01e6d85d9e623` |
| `README.md` (stored as `README_upstream.md`) | `6a6bbfd68f6439044678502969c1147d5dbb80d7` |

**Licence.** MIT License, "Copyright (c) 2024 OpenAI" (file `eloundou/LICENSE`).
MIT permits copying and redistribution provided the copyright and permission
notice is kept, so the files are committed with the licence beside them.
`LICENSE.md` and `LICENSE.txt` returned HTTP 404; `LICENSE` returned 200.

**Upstream README** (verbatim, stored as `eloundou/README_upstream.md`):

> Occupation level codes are in occ_level.csv!
> - dv_rating is the GPT-4 rating and human is from the annotators
> - _alpha=E1, _beta = E1+.5*E2, _gamma=E1+E2

### `occ_level.csv` — 923 rows × 8 columns, no missing values

| Column | Meaning |
|---|---|
| `O*NET-SOC Code` | 8-digit O*NET-SOC 2019 code, e.g. `15-1252.00`. The first 7 characters are the 2018 SOC code. The paper uses O*NET 27.2 (Section 3.1). |
| `Title` | O*NET occupation title |
| `dv_rating_alpha` | GPT-4 rating, α = share of tasks rated E1 |
| `dv_rating_beta` | GPT-4 rating, β = E1 + 0.5·E2 |
| `dv_rating_gamma` | GPT-4 rating, E1 + E2 (called **ζ (zeta)** in the paper) |
| `human_rating_alpha` | human annotators, α |
| `human_rating_beta` | human annotators, β |
| `human_rating_gamma` | human annotators, E1 + E2 (ζ in the paper) |

`dv_rating_*` is GPT-4 with "Rubric 1". The paper's Table 2 caption says "In
the paper we use GPT-4, Rubric 1", and `dv_rating_*` is reproduced exactly
from the `gpt4_exposure` column of `full_labelset.tsv` (see below).

**Exposure levels** (paper, Appendix A.1, abridged):

- **E0:** direct access to the LLM through an interface like ChatGPT "cannot
  reduce the time it takes to complete this task with equivalent quality by
  half or more".
- **E1:** such access "alone can reduce the time it takes to complete the
  task with equivalent quality by at least half".
- **E2:** the LLM alone may not halve the time, "but it is easy to imagine
  additional software that could be developed on top of the LLM that would".
- **E3:** exposure given image capabilities. The paper combines E2 and E3 for
  all analyses (Section 3.3, footnote b).

**Weighting** (verified): each score is a weighted share of the occupation's
O*NET tasks, with **core tasks weighted 2 and supplemental tasks 1**. The
paper says "Core tasks receive twice the weight of supplemental tasks within
occupations ... All weights within an occupation sum to one" (Figure 4
caption). Recomputing all six measures from `full_labelset.tsv` with weights
Core = 2, Supplemental = 1, missing type = 1 reproduces `occ_level.csv`
exactly: 923/923 occupations × 6 measures, max |diff| = 0. 1,312 of 19,265
tasks have no Task Type. Equal task weights do *not* reproduce the file (for
example, `human_rating_alpha` would differ by up to 0.133).

**Consistency with the paper** (verified): Table 4 of the paper (top-5
occupations for Human α, Human β, Model α and Model β, computed with equal task
weights) is reproduced 20/20 from `full_labelset.tsv`. The counts of "fully
exposed" occupations (15 human ζ, 86 model ζ) also match.

### `full_labelset.tsv` — 19,265 task rows

Columns: unnamed row index; `O*NET-SOC Code`; `Task ID`; `Task` (text);
`Task Type` (Core / Supplemental / missing); `Title`; `human_exposure_agg`
(E0/E1/E2, human label aggregated to the task); `gpt4_exposure` (E0/E1/E2,
GPT-4 rubric 1); `gpt4_exposure_alt_rubric` (E0/E1/E2, GPT-4 "Rubric 2".
Not documented upstream, but verified: the paper's Table 2 is reproduced
from these three columns, see below); `gpt_3_relevant` (bool, undocumented);
`gpt4_automation` (T0–T4, undocumented
upstream); `alpha`, `beta`, `gamma` (task-level numeric versions of
`gpt4_exposure`: verified identical to E1 → 1/1/1, E2 → 0/0.5/1, E0 → 0);
`automation` (verified to be `gpt4_automation` mapped T0..T4 → 0, 0.25, 0.5,
0.75, 1); `human_labels` (verified identical to `human_exposure_agg`).

**Table 2 of the paper is a task-level comparison** (verified). Its agreement
rates and Pearson correlations are reproduced from the 19,265 task labels
(E1 → 1, E2 → 0.5 / 0 / 1 for β / α / ζ, E0 → 0), unweighted. 17 of 18 cells
match to the printed precision. The only exception is the agreement between
GPT-4 Rubric 2 and humans at β: 65.9% in the data, 65.6% in the paper.
Occupation-level correlations are much higher, e.g. human β vs GPT-4 β:
Pearson 0.876 across the 923 core-weighted O*NET-SOC rows, against 0.591 at
the task level. The caption's remark that "core tasks are given twice the
weight at the occupation-level" therefore does not describe the Table 2
figures.

### Aggregation to 6-digit SOC (rule used by `exposure_scores.py`)

The pre-registered unit is the 6-digit SOC code (A.1). The 923 O*NET-SOC rows
map to **798** SOC codes. 67 SOC codes have more than one detailed row (at most
9). For each of the six measures, the SOC score is the **unweighted mean over
its detailed O*NET-SOC rows**; `n_onet` stores the count and `onet_codes` the
codes. These files carry no employment weights below the 6-digit level, so
there is nothing to weight by. All 798 codes have all six measures; the
pre-registration requires at least 50 SOC codes with valid scores. A possible
alternative, not used here, is to keep only the `.00` row of each SOC code.

**No published precedent for this exact rule was found.** The EIG
replication code (EIG-Research/AI-unemployment, `code/01 Crosswalks.R`, read
2026-10-10 via raw.githubusercontent.com) also averages detailed O*NET-SOC
rows without weights, but at the **Census-2018 occupation level**, after a
SOC-2018 → Census crosswalk. That is its "admin" measure, lines 170–172 and
245–250: `substr(O.NET.SOC.Code, 1, 7)`, `left_join(xwalk_soc2018_cen2018)`,
then `group_by(census_2018)` and `mean`. Its alternative "sim" measure is an
ability-importance-weighted sum by Census code (lines 196–206). EIG never
forms a 6-digit SOC aggregate. A Census code can pool several SOC codes, so
EIG's numbers are not interchangeable with ours. EIG's input file
(`gptsRgpts_occ_lvl.csv`, "downloaded from the accompanying GitHub" per its
README) has the columns `gpt4_beta` and `human_beta`. Those names do not
occur in openai's `occ_level.csv`, so EIG renamed or re-derived the file. How
is not documented.

**24 SOC codes have no `.00` O*NET row.** For these, the score is the mean of
whichever O*NET specialties the file happens to list. That may not represent
the SOC category: 9 of the 24 rest on a single specialty. All 24 codes end in
9. By SOC convention, detailed codes ending in 9 are residual ("All Other")
categories. That convention is stated from general knowledge of the SOC
structure; it was not checked against the SOC 2018 manual, and the codes'
SOC 2018 titles could not be retrieved (bls.gov is blocked). None of the
file's 923 titles contains "All Other".
`exposure_scores.py` keeps these codes. It flags them with
`has_base_row == False` and replaces the misleading specialty title with
`[no .00 row; N specialty row(s)] <first specialty title>`. Whether they enter
the primary analysis (keep, drop, or keep and report without them as a
robustness check) was a specification choice. D36.9 settles it: the codes
are kept and flagged, and the results without them are a robustness check
(see "Primary measure").

| SOC | n_onet | O*NET-SOC rows averaged (title) |
|---|---:|---|
| 11-9179 | 2 | 11-9179.01 Fitness and Wellness Coordinators; 11-9179.02 Spa Managers |
| 11-9199 | 6 | 11-9199.01 Regulatory Affairs Managers; 11-9199.02 Compliance Managers; 11-9199.08 Loss Prevention Managers; 11-9199.09 Wind Energy Operations Managers; 11-9199.10 Wind Energy Development Managers; 11-9199.11 Brownfield Redevelopment Specialists and Site Managers |
| 13-1199 | 4 | 13-1199.04 Business Continuity Planners; 13-1199.05 Sustainability Specialists; 13-1199.06 Online Merchants; 13-1199.07 Security Management Specialists |
| 13-2099 | 2 | 13-2099.01 Financial Quantitative Analysts; 13-2099.04 Fraud Examiners, Investigators and Analysts |
| 15-1299 | 9 | 15-1299.01 Web Administrators; 15-1299.02 Geographic Information Systems Technologists and Technicians; 15-1299.03 Document Management Specialists; 15-1299.04 Penetration Testers; 15-1299.05 Information Security Engineers; 15-1299.06 Digital Forensics Analysts; 15-1299.07 Blockchain Engineers; 15-1299.08 Computer Systems Engineers/Architects; 15-1299.09 Information Technology Project Managers |
| 15-2099 | 1 | 15-2099.01 Bioinformatics Technicians |
| 17-2199 | 8 | 17-2199.03 Energy Engineers, Except Wind and Solar; 17-2199.05 Mechatronics Engineers; 17-2199.06 Microsystems Engineers; 17-2199.07 Photonics Engineers; 17-2199.08 Robotics Engineers; 17-2199.09 Nanosystems Engineers; 17-2199.10 Wind Energy Engineers; 17-2199.11 Solar Energy Systems Engineers |
| 17-3029 | 2 | 17-3029.01 Non-Destructive Testing Specialists; 17-3029.08 Photonics Technicians |
| 19-1029 | 4 | 19-1029.01 Bioinformatics Scientists; 19-1029.02 Molecular and Cellular Biologists; 19-1029.03 Geneticists; 19-1029.04 Biologists |
| 19-2099 | 1 | 19-2099.01 Remote Sensing Scientists and Technologists |
| 19-3039 | 2 | 19-3039.02 Neuropsychologists; 19-3039.03 Clinical Neuropsychologists |
| 19-3099 | 1 | 19-3099.01 Transportation Planners |
| 19-4099 | 2 | 19-4099.01 Quality Control Analysts; 19-4099.03 Remote Sensing Technicians |
| 25-2059 | 1 | 25-2059.01 Adapted Physical Education Specialists |
| 29-1129 | 2 | 29-1129.01 Art Therapists; 29-1129.02 Music Therapists |
| 29-1229 | 6 | 29-1229.01 Allergists and Immunologists; 29-1229.02 Hospitalists; 29-1229.03 Urologists; 29-1229.04 Physical Medicine and Rehabilitation Physicians; 29-1229.05 Preventive Medicine Physicians; 29-1229.06 Sports Medicine Physicians |
| 29-1299 | 2 | 29-1299.01 Naturopathic Physicians; 29-1299.02 Orthoptists |
| 29-2099 | 3 | 29-2099.01 Neurodiagnostic Technologists; 29-2099.05 Ophthalmic Medical Technologists; 29-2099.08 Patient Representatives |
| 29-9099 | 1 | 29-9099.01 Midwives |
| 31-9099 | 2 | 31-9099.01 Speech-Language Pathology Assistants; 31-9099.02 Endoscopy Technicians |
| 33-9099 | 1 | 33-9099.02 Retail Loss Prevention Specialists |
| 47-4099 | 1 | 47-4099.03 Weatherization Installers and Technicians |
| 49-9099 | 1 | 49-9099.01 Geothermal Technicians |
| 51-8099 | 1 | 51-8099.01 Biofuels Processing Technicians |

---

## Primary measure (decided: ROADMAP D36.9, 2026-10-10)

The pre-registration (A.2; `PREREGISTRATION_EN.md` line 55) says only:
"Eloundou et al. (2023) GPT-exposure scores as the primary measure." It names
no column. The published file has six candidates (human or GPT-4 × α, β, ζ),
and turning it into `Exposure_i` involves further choices (items 1–5 below).

**Decision D36.9.** The project lead took this decision on 2026-10-10. It is
logged in ROADMAP.md as D36.9. **PI confirmation: TODO.**

| Item | Choice | D36.9 |
|---|---|---|
| 1 | Rater | Human annotators. |
| 2 | Exposure level | β (E1 + 0.5·E2). |
| 1–2 | Primary measure | `human_rating_beta` (`exposure_scores.PRIMARY_MEASURE = "human_beta"`). |
| 1–2 | First robustness check | `dv_rating_beta` (GPT-4 β). It is reported next to the primary in every main table, not only in an appendix. |
| 1–2 | Further robustness checks | `human_rating_alpha` and `human_rating_gamma` (lower and upper bounds), `dv_rating_alpha` and `dv_rating_gamma`. Felten AIOE and Webb, as pre-registered in A.6(2). |
| 3 | Task weighting | The published core-weighted `occ_level.csv`, used as is, with no re-derivation. |
| 4 | Aggregation to 6-digit SOC | Unweighted mean over the detailed O*NET-SOC rows. The 24 SOC codes without a `.00` row (residual codes, see "Aggregation" above) are kept and flagged (`has_base_row == False`). Dropping them is a robustness check (`get_scores(..., drop_no_base_row=True)`). |
| 5 | Comparability with Ozkan–Sullivan (D17) | **Open**: see below. |
| — | Disclosure | Pre-lock project documents labelled the intended measure α. The paper discloses this (see "How the project came to say α" below). |

**Timing.** The pre-registration was "Registered prior to accessing outcome
data or running any estimation" (`PREREGISTRATION_EN.md` line 7). D36.9 was
taken before any outcome data was opened. No outcome data (Revelio flows,
enrollment proxies) is in the repository, and ROADMAP.md lists the Revelio
request as still open (WS2).

**D36.9 was taken while item 5 was still open.** The exposure measure that
Ozkan–Sullivan use (D17) is still unknown. The reasons for not waiting:

- Item 5 cannot be resolved from this environment by any known date.
  stlouisfed.org is unreachable, and the web-search budget was used up on
  2026-10-10.
- Leaving the measure open while outcome data are procured (WS2) would
  undermine the ordering that the registration relies on.
- The cost to comparability is limited. GPT-4 β and the other four Eloundou
  columns are pre-specified robustness measures. If Ozkan–Sullivan use one of
  these columns, the comparable estimate is already among the reported
  results.

If they use a measure outside these six columns, how the D17 replication
handles it has not been decided (TODO: lead/PI, before outcome data).

**Not part of D36.9** (open; TODO: lead/PI, to be decided before outcome
data):

- (a) whether to add, as a further robustness check, a recomputation with
  equal task weights from `full_labelset.tsv` (item 3). The paper uses equal
  weights for Figures 3 and 5 and Tables 4 and 5.
- (b) whether to add the `.00`-row-only aggregation as a robustness check
  (item 4).
- (c) item 5.

### How the project came to say "α"

Every project document written before the pre-registration was locked
(2026-06-19 23:53 UTC, ROADMAP D27/D34) labels the intended measure α:

- the first `exposure_scores.py` docstring: "Primary: Eloundou et al. (2023)
  'GPTs are GPTs' exposure scores (alpha)";
- the commit message of `492573c` (2026-06-14): "26 key occupations with
  Eloundou GPT-exposure alpha scores";
- ROADMAP.md line 74 as it stood until `61e80bb` ("SOC → alpha"), and line
  274, entry D25 ("Eloundou α"), which still stands;
- the project README.md line 24 as it stood until `61e80bb` ("Eloundou
  GPT-α").

The α label arrived only with the hand-typed values. Those values are
unsourced and are not α (`AUDIT_hardcoded_vs_source.md`). No document
records α as a deliberate design decision, and the locked text names no
column. As D36.9 requires, the paper discloses that pre-lock project notes
said α and explains why the logged measure differs. Otherwise a referee could
read the change as a post-hoc switch of measure.

### Items 1–5 (background to D36.9)

1. **Rater:** human annotators vs GPT-4 (rubric 1).
2. **Exposure level:** α (E1), β (E1 + 0.5·E2) or ζ (E1 + E2).
3. **Task weighting.** The published `occ_level.csv` weights core tasks 2,
   supplemental 1 (verified above). The paper does the same for Table 3
   (footnote 6) and Figure 4 (footnote 7). It uses **equal** task weights for
   Figure 3, Figure 5, Table 4 (verified: Table 4 is reproduced only with
   equal weights) and Table 5. Footnote 8 says results "do not change
   meaningfully" between the two schemes. The difference is not negligible
   for single occupations: `human_rating_alpha` differs by up to 0.133.
   D36.9: use the published file as is (core-weighted, no re-derivation).
   An equal-weight recomputation is not part of D36.9 (open point (a) above).
4. **Aggregation to 6-digit SOC:** mean over detailed rows vs the `.00` row
   only; and the treatment of the **24 SOC codes without a `.00` row** (see
   above). D36.9: mean over detailed rows; the 24 codes are kept and flagged,
   and the results without them are a robustness check. The `.00`-only
   variant is not part of D36.9 (open point (b) above).
5. **Comparability with Ozkan–Sullivan (D17).** ROADMAP D17 (line 266)
   commits the project to replicating the St. Louis Fed (2025) AI-exposure ×
   unemployment panel. Which exposure measure that work uses could not be
   determined: stlouisfed.org is blocked, and the web-search budget was used
   up (2026-10-10).
   **TODO:** identify their measure (rater, level, weighting, occupation
   coding). D36.9 was taken without it (see "D36.9 was taken while item 5
   was still open" above).

The evidence below supports β clearly. It does **not** by itself settle the
rater. D36.9 settles the rater as a decision, for the reasons given under
"Rationale".

### Evidence

| Source | What it says or does | How it was checked |
|---|---|---|
| Eloundou et al. (2023), Abstract | "we assess occupations ... integrating both human expertise and GPT-4 classifications"; headline 80% / 19% figures with no rater named. | Read in the full text (22 Aug 2023 version) |
| Eloundou et al. (2023), §1 | "To construct our primary exposure dataset, we collected both human annotations and GPT-4 classifications, using a prompt tuned for agreement with a sample of labels from the authors." The introduction's α and ζ headline numbers are human-rated: "Human assessments suggest that only 3% of U.S. workers have over half of their tasks exposed ..."; "our human estimates indicate that up to 49% ...". | Read in the full text |
| Eloundou et al. (2023), §3.3 | "We construct three primary measures for our dependent variable of interest: (i) α ... (ii) β ... and (iii) ζ" and "For the remainder of the analysis, if not specified, the reader may assume that we refer to β exposure". Human ratings: "The authors personally labeled a large sample of tasks and DWAs and enlisted experienced human annotators who have reviewed GPT-3, GPT-3.5 and GPT-4 outputs". | Read in the full text |
| Eloundou et al. (2023), §3.4.1 | "A fundamental limitation of our approach lies in the subjectivity of the labeling. ... this group is not occupationally diverse, potentially leading to biased judgments ..." | Read in the full text |
| Eloundou et al. (2023), §3.4.2 | GPT-4 classification is "sensitive to alterations in the rubric's wording, the prompt's order and composition ..."; "none should be considered the definitive ground truth relative to the others. In this analysis, we present results from human annotators as our primary results." | Read in the full text |
| Eloundou et al. (2023), §3.4.3 | "Human annotators were mostly unaware of the specific occupations mapped to each DWA during the labeling process." | Read in the full text |
| Eloundou et al. (2023), §4.1 | "Based on the β values, we estimate that 80% of workers belong to an occupation with at least 10% of its tasks exposed to LLMs, while 19% of workers are in an occupation where over half of its tasks are labeled as exposed." No rater named. | Read in the full text |
| Eloundou et al. (2023), §5.1 | Other indices "are all negatively correlated with our primary GPT-4 and human-assessed overall exposure ratings". | Read in the full text |
| Eloundou et al. (2023), Table 2 | Task-level agreement at β: GPT-4 rubric 1 vs human 65.6% (Pearson 0.591); rubric 1 vs rubric 2 76.0% (Pearson 0.705). The paper reports **no** inter-rater reliability statistic for the human annotators. A full-text search finds no "inter-rater", "inter-annotator" or "kappa", and the only "reliab…" matches concern LLM reliability. | Read in the full text; reproduced from `full_labelset.tsv` (see above) |
| EIG (eig.org), "AI and Jobs: The Final Word (Until the Next One)", 10 Aug 2025; repository EIG-Research/AI-unemployment | The main descriptive charts (`code/03 Main Analysis.R`, charts 4–8) group occupations by Felten AIOE quintiles (`AIOE_quint_wgt`). Eloundou human β and GPT-4 β appear side by side with the other measures: in the main-analysis difference-in-differences comparison (lines 764–840, chart `11_d_in_d.png`) and throughout the appendix (`code/04 Appendix.R`, labelled "Eloundou (human)" and "Eloundou (gpt4)"). Both use top-quintile indicators built from Census-2018 aggregates (see "Aggregation"). EIG does not single out either rater. Its README names contacts by first name only, so author surnames are not verified here. | Read directly via raw.githubusercontent.com: `README.md`, `code/01 Crosswalks.R`, `code/03 Main Analysis.R`, `code/04 Appendix.R` |
| Brynjolfsson, Chandar & Chen (2025), "Canaries in the Coal Mine?" (Stanford Digital Economy Lab) | **Unverified paraphrase:** reported to define exposure quintiles with the GPT-4 β measure of Eloundou et al. | Search-engine excerpts seen in an earlier session only. The paper was not read (host blocked; web-search budget used up). **TODO-verify** |
| Gimbel et al. (2025), Yale Budget Lab | **Unverified:** reported to use Eloundou exposure with core 1 / supplemental 0.5 task weights; rater not established. | Search-engine excerpts only. **TODO-verify** |
| Acemoglu (2024/2025), "The Simple Macroeconomics of AI" | **Unverified:** reported to use an Eloundou-based automation index, not one of these six columns. Not informative for this choice. | Search-engine excerpts only. **TODO-verify** |

### Assessment

- **β is well supported.** It is the paper's stated default (§3.3) and the
  basis of the 80% / 19% figures (§4.1). Where EIG uses Eloundou (verified),
  it uses only β, for both raters. Canaries reportedly uses GPT-4 β, but that
  is unverified. No source located argues for α or ζ as the main measure.
- **The rater is not settled by the source.** The paper says it presents human
  results as its primary results (§3.4.2). It also calls both raters' data
  "primary" (§1, §5.1), integrates both in the abstract, and reports both
  throughout. Its limitations cut both ways: GPT-4 labels move with the prompt
  (§3.4.2), while the human labels come from a group the authors call not
  occupationally diverse (§3.4.1), working mostly without occupation context (§3.4.3),
  with no reported inter-rater reliability.
- **The rater choice changes who counts as highly exposed.** Across the 798
  SOC codes the two β measures correlate at Pearson 0.881 and Spearman 0.908.
  But only 62.2% of codes fall in the same quintile under both (37.8% move,
  30 of them by two quintiles or more), and 80.2% in the same tercile. The two
  top quintiles share 111 of 160 codes. This matters for H3 (dose-response),
  for Part B's high/low-exposure stratification and for the occupations at
  the centre of the narrative:

| SOC | Title | human β (percentile) | GPT-4 β (percentile) | human α | GPT-4 α |
|---|---|---|---|---:|---:|
| 15-1252 | Software Developers | 0.447 (75th) | 0.868 (98th) | 0.053 | 0.789 |
| 43-9021 | Data Entry Keyers | 0.500 (81st) | 0.893 (99th) | 0.214 | 0.857 |
| 31-9094 | Medical Transcriptionists | 0.232 (44th) | 0.875 (98th) | 0.143 | 0.821 |
| 43-3031 | Bookkeeping, Accounting, and Auditing Clerks | 0.314 (55th) | 0.802 (97th) | 0.140 | 0.605 |
| 17-2061 | Computer Hardware Engineers | 0.318 (56th) | 0.727 (96th) | 0.182 | 0.545 |
| 23-1011 | Lawyers | 0.475 (79th) | 0.425 (64th) | 0.150 | 0.000 |

  (Percentiles are ranks among the 798 SOC codes, ties averaged; computed
  with `exposure_scores.load_eloundou()`.)

### Rationale for human β (and its limits)

1. **Closest to the source's one explicit statement.** The paper leans human
   in §3.4.2 ("we present results from human annotators as our primary
   results"), but it also calls both raters primary (§1, §5.1). Taking human β
   follows that statement. It does **not** remove a researcher degree of
   freedom: the rater, the weighting (item 3) and the aggregation (item 4)
   are choices. D36.9 logs them before any outcome data is seen, and that
   logging is what keeps them from being post-hoc.
2. **Reliability does not favour either rater.** GPT-4 labels depend on the
   prompt: two GPT-4 rubrics agree on only 76.0% of task labels at β (Table 2;
   §3.4.2). The human labels have no reported inter-rater reliability and
   come from a group the authors describe as not occupationally diverse
   (§3.4.1), mostly without knowing the occupation (§3.4.3). Human labels agree
   with GPT-4 rubric 1 on only 65.6% of task labels at β, less than the two
   GPT-4 rubrics agree with each other.
3. **Secondary consideration.** The narrative index (X) partly relies on an
   LLM classifier. A human-rated exposure measure keeps LLM judgment out of
   one side of the `Exposure_i × NarrativeIntensity_t` interaction. The
   separation is partial: the GPT-4 prompt was tuned to the authors' labels
   (§1), and the authors also labelled part of the human data (§3.3).

**Against this choice:** GPT-4 β is reportedly what Canaries uses (unverified,
above), and it may be what Ozkan–Sullivan use (unknown, item 5). Someone who
gives more weight to comparability with those follow-ups than to the source's
§3.4.2 statement would choose `dv_rating_beta`, which is a defensible
alternative. D36.9 therefore reports GPT-4 β next to the primary in every
main table: because of the re-ranking shown above, the two must be read side
by side. If the PI, on confirming D36.9, changes the primary measure, the
change must be logged before any outcome data is seen.

---

## 2. Felten, Raj & Seamans AIOE — robustness (pre-registration A.6, item 2)

**Citation** (as requested by the repository README): Felten E, Raj M, Seamans
R (2021). Occupational, industry, and geographic exposure to artificial
intelligence: A novel dataset and its potential uses. *Strategic Management
Journal* 42(12):2195–2217.

**Source.** github.com/AIOE-Data/AIOE. Branch `main` and branch `master` serve
byte-identical files (same SHA-256). Attempts, all via raw.githubusercontent.com:

- `AIOE-Data/AIOE/{main,master}/README.md`: 200.
  SHA-256 `6410cb1e5f874aeebc458d2d49267db41b3c5c7ec05f3d1dc790e60d1cd18db2`.
- `AIOE_DataAppendix.xlsx`: 200, stored.
- `Language Modeling AIOE and AIIE.xlsx`: 200, stored.
- `Image Generation AIOE and AIIE.xlsx`: 200, not stored (not relevant to an
  LLM-narrative design).
- `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENSE.rst`, `LICENCE`, `license`,
  `COPYING`: all 404.

**Licence.** None found. The README only asks users to cite the paper. Without
a licence, redistribution is not granted, so the files are **git-ignored**
(`code/.gitignore`). Fetch them with `python exposure_scores.py download`.

**Contents used.**

- `AIOE_DataAppendix.xlsx`, sheet `Appendix A`: 774 occupations, columns
  `SOC Code`, `Occupation Title`, `AIOE`. The score is standardized: mean 0,
  SD 1, range −2.67 to 1.53. Other sheets: B = industry AIIE, C = county AIGE,
  D = application–ability matrix, E = ability-level exposure.
- `Language Modeling AIOE and AIIE.xlsx`, sheet `LM AIOE`: same 774 SOC
  codes, `Language Modeling AIOE`. The repository README says only that "we
  have added data and code to produce AIOE scores for the generative AI
  applications of image generation and language modeling". The associated
  paper was not verified in this session. The pre-registered robustness
  measure is taken to be the original AIOE (`load_felten_aioe("aioe")`); the
  LM variant is optional (`load_felten_aioe("lm")`).

**SOC vintage: 2010, not 2018.** This is inferred from the codes: the file
contains 15-1132 and 15-1133 and lacks 15-1252, 15-1211 and 15-2051. Overlap
with the Eloundou 6-digit codes is 683. 91 codes appear only in AIOE and 115
only in Eloundou. A merge needs the BLS 2010→2018 SOC crosswalk (see Open
issues).

---

## 3. Webb (2020) patent-based scores — robustness, **PENDING**

**Citation.** Webb, M. "The Impact of Artificial Intelligence on the Labor
Market." Working paper, SSRN 3482150 (EIG cites it as Webb 2022).

**Official source.** Webb's data page, as linked from the EIG README:
https://www.notion.so/michaelwebb/Data-for-The-Impact-of-Artificial-Intelligence-on-the-Labor-Market-3b52b281505a48b8be107d11d8d0c363
(file `exposure_by_occ1990dd_lswt2010.csv`). Blocked from this environment;
`www.notion.so`, `www.michaelwebb.co` and `web.stanford.edu` all failed at the
proxy.

**What is stored.** GitHub code search found one copy of the file:
`demirev/ai-products`, branch `master`, path
`data/webb/exposure_by_occ1990dd_lswt2010.csv`. That repository is a different
project (an AI-products exposure measure). It has no licence and does not say
where it obtained the file. The copy has 341 rows and the columns `occ1990dd`,
`occ1990dd_title`, `lswt2010`, `pct_software`, `pct_robot`, `pct_ai`. Three
rows have no scores (occ1990dd 285, 349, 415). The column name `pct_ai` matches
the column EIG's code reads from Webb's file. The scale (1–100) suggests
percentiles. That reading, and the meaning of `lswt2010` (presumably a 2010
labour-supply weight), are inferred, not verified. The file is
**git-ignored**, and `load_webb()` warns every time it is called.

**To close this item:**

1. Download the official file from Webb's data page above, or request it from
   the author.
2. Compare its SHA-256 with `c5652fd3f862948cb77d87f38aa8296137c51e028992ab54e57246a066e0a779`.
   If they differ, replace the copy and update `SOURCES` in
   `exposure_scores.py`.
3. Obtain an occ1990dd → 2018 SOC crosswalk. EIG used David Dorn's
   `occ1990_occ1990dd.zip` (https://www.ddorn.net/data.htm) together with Census
   crosswalks. Webb scores are on occ1990dd codes and cannot be merged with SOC
   codes until this is done.

---

## Open issues

- **Decision log.** D36.9 (2026-10-10, the lead) settles items 1–4: rater,
  exposure level, task weighting, and aggregation including the 24 codes
  without a `.00` row. PI confirmation: TODO. Still open, to be logged before
  outcome data are accessed: item 5 and the optional robustness variants
  (a) and (b) under "Primary measure". This track does not edit ROADMAP.md.
  ROADMAP.md line 74 already cites "D36.9" and "эррата D36" ("erratum D36"),
  so the ROADMAP entry D36 must contain both D36.9 and the α erratum.
- **Ozkan–Sullivan (D17) exposure measure unknown.** TODO: identify it.
  stlouisfed.org is blocked, and the web-search budget was used up on
  2026-10-10. D36.9 was taken without it. If their measure is not one of the
  six Eloundou columns, decide how the D17 replication handles it before
  outcome data.
- **Unverified citations (TODO-verify).** Brynjolfsson, Chandar & Chen
  (Canaries) rater and column; Gimbel et al. (Yale Budget Lab) weighting and
  rater; Acemoglu's index; the *Science* issue number and DOI; EIG author
  surnames. None of these carries D36.9, and none may carry a later change
  until the sources are read.
- **Erratum for the "α" label.** README.md line 24 and ROADMAP.md line 74
  were corrected in `61e80bb` and now cite `AUDIT_hardcoded_vs_source.md`.
  ROADMAP.md line 74 also cites "эррата D36" ("erratum D36"). ROADMAP.md
  line 274 (entry D25, a dated log entry) still says "Eloundou α". The erratum
  in D36 has to cover it; this is outside this track. The paper discloses
  the pre-lock α label (see "How the project came to say α").
- **Upstream commit SHA** for openai/GPTs-are-GPTs could not be recorded
  (blocked). Blob SHA-1 and SHA-256 above identify the content.
- **SOC 2010 → 2018 crosswalk** needed for AIOE (BLS
  `soc_2010_to_2018_crosswalk.xlsx`, URL as cited in the EIG README:
  https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx; bls.gov is
  blocked here).
- **occ1990dd → SOC 2018 crosswalk** needed for Webb (see above).
- **Behavioral-data SOC vintage.** The Revelio occupation codes must be checked
  against 2018 SOC before merging.
- **`openpyxl`** is required to read the AIOE workbooks but is not in
  `code/requirements.txt`; that file is outside this track.
