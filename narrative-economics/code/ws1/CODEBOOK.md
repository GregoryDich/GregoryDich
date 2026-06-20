# WS1.0 Coding Codebook v1 — "AI × Jobs" narrative

You are coding short text fragments (~50 words each, from YouTube transcripts
about AI and work). For each fragment you assign **two** labels. The goal is a
shared, reproducible standard so two independent coders agree (Cohen's κ ≥ 0.70).

This v1 codebook was sharpened after a pre-test where two automatic coders
disagreed on 61/300 relevance and 143/300 valence labels. The rules below are
written specifically to remove those disagreements.

---

## How to work (independence)

- Code **alone**. Do not discuss fragments with the other coder while coding.
- Do **not** look at any machine/dictionary/LLM labels. Code only from the text.
- Do not look up the video. Judge **only the words in the fragment**.
- Go in order, don't skip. Code all 300. Don't go back and "fix" old rows to
  match a pattern you noticed later — first instinct under the rules is fine.

You fill two columns in `coding_sample.csv`:
`human_relevant_0_1` and `human_valence_minus_plus_none`.

---

## VARIABLE 1 — `human_relevant_0_1`  (0 or 1)

**A fragment is relevant (= 1) only if the fragment's own words contain BOTH:**

1. an **AI / automation referent** — AI, "the technology", ChatGPT, automation,
   algorithm, robot, agent, a model, "tools" (in the AI sense), a named AI
   company/product, etc.; **AND**
2. a **labor referent** — a job, occupation, worker, hiring, firing, layoff,
   salary, career, "white-collar work", a named profession, etc.; **AND**
3. the fragment **connects the two** — it says or reports *something about what
   AI does to that work* (destroys it, creates it, changes it, doesn't affect
   it, "AI is the excuse for layoffs", etc.).

If **any** of the three is missing in the fragment's own words → **0**.

> **The two-token rule is strict on purpose.** Do NOT use the video's overall
> topic to "fill in" a missing token. If a fragment reports "45,000 people were
> laid off" but contains no AI/automation word, it is **0** — even if the whole
> video is about AI. We are measuring whether *this fragment* carries the AI×jobs
> claim, not the video.

### Relevance — decision examples (real fragments)

| Fragment (shortened) | Label | Why |
|---|---|---|
| "Zuckerberg predicts millions of white-collar workers will be **replaced** by **AI**" | **1** | AI + workers + connection |
| "a paralegal was **laid off** — **replaced by an AI** that works for pennies" | **1** | AI + occupation + connection |
| "**AI** costs more than the **people** it's supposed to replace" | **1** | AI + workers + connection (even though it's skeptical) |
| "**AI** will change the economy… where will you sit in the new one?" | **0** | AI present, but **no occupation / no labor outcome** — too vague |
| "labor economists warn of a bifurcated **economy**… entry-level work eroding" | **0** | jobs present, but **no AI token** in the fragment |
| "stop every kid from creating their own **AI** system that breaks your rules" | **0** | AI present, but it's about AI governance — **no jobs** |
| "**AI** isn't inherently good or bad, it's a tool" | **0** | philosophy — no labor referent |
| "45,000 employees were **laid off** in March 2026" | **0** | layoff present, but **no AI token** in the fragment |

---

## VARIABLE 2 — `human_valence_minus_plus_none`

**Code valence ONLY if relevance = 1.** If relevance = 0, write `none`.

We treat this as **two competing narratives**:

- **`minus`** — the fragment, *on balance*, advances the **alarming** narrative:
  AI **destroys / replaces / shrinks** jobs, freezes hiring, lowers wages, or
  makes workers obsolete.
- **`plus`** — the fragment, *on balance*, advances the **reassuring**
  narrative. This is **TWO things folded into one code**:
  (a) AI **creates / augments / complements** jobs or raises demand for skills;
  **OR**
  (b) the destruction fear is **overblown / false** — debunking, "they had to
  **rehire**", "AI costs more than the worker", "the layoff narrative was a
  **lie**", "AI **won't** take your job."
- **`mixed`** — the fragment gives **roughly equal weight to both** directions
  (states destruction AND creation, neither dominates).
- **`none`** — relevant to AI×jobs, but the fragment makes **no directional
  claim**: pure factual setup, a question, or it **expresses uncertainty about
  the direction** ("was it really AI, or just an excuse? only time will tell").

### Two rules that caused most of the disagreement — read these twice

1. **Debunking destruction is `plus`, not `minus`.** If the speaker QUOTES
   displacement vocabulary ("replace", "laid off") but the *point* is that the
   fear is wrong / reversed / exaggerated → **`plus`**. The vocabulary is not the
   stance; the stance is what the speaker is arguing.

2. **Uncertainty about the cause is `none`, not `minus`.** If the fragment
   raises doubt that AI is really the cause ("hard to say how much is AI vs
   companies using AI as a cover for cost-cutting") → **`none`**. Reporting that
   doubt is not asserting destruction.

### Valence — decision examples (real fragments)

| Fragment (shortened) | Label | Why |
|---|---|---|
| "Zuckerberg predicts millions of white-collar workers will be replaced" | `minus` | asserts destruction |
| "AI will generate 170 million **new jobs** in the next 5 years" | `plus` | asserts creation |
| "job postings for software engineers actually **continue to increase**" | `plus` | asserts creation/augmentation |
| "those same companies are quietly **hiring back** the engineers they fired" | `plus` | **debunking** the destruction story |
| "AI **costs more** than the people it's supposed to replace" | `plus` | **debunking** — fear overblown |
| "the 'AI is replacing software engineers' narrative **was a lie**" | `plus` | explicit debunk |
| "hard to say how much is **AI vs** companies using AI as a **cover**" | `none` | expresses **uncertainty about cause** |
| "was AI the excuse, or a real miscalculation? only engineers can answer" | `none` | open question, no direction |
| "AI will eliminate some jobs **but** create demand for new skills" | `mixed` | both directions, balanced |

---

## One-line decision flow per fragment

```
Does the fragment text have AI-token AND labor-token AND a connection?
   NO  -> relevant = 0 ,  valence = none   (done)
   YES -> relevant = 1 , then pick valence:
          speaker argues AI destroys/replaces/shrinks work .......... minus
          speaker argues AI creates/augments work,
              OR argues the destruction fear is false/overblown ...... plus
          speaker gives both directions about equally ............... mixed
          relevant, but no direction / a question / "is it even AI?" . none
```

---

## After coding

Two independent coders → run `ws1_kappa.py` on each pair of columns.
Gate: **κ ≥ 0.70** on relevance and on valence. If we clear it, the instrument
is trustworthy and WS1 (the full index) starts. If not, we revise this codebook
again — that's the whole point of WS1.0, and it's cheap compared to building the
full index on a shaky instrument.
