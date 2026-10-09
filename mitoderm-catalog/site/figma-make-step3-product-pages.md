# Figma Make — Step 3: product pages from the catalogue

Как пользоваться: открыть Make-файл «Design modern website for mitoderm.com», приложить
`pdf/MITODERM-Catalog-EN.pdf` (для иврита — `pdf/MITODERM-Catalog-HE-36.pdf`) и
`site/mitoderm-site-blocks.xlsx`, вставить весь текст ниже начиная с «STEP 3». Make строит
страницы по уже существующему дизайну файла и заменяет текущие продуктовые страницы.
**EXO-NAD и EXOCELL MASK — брать новые версии по каталогу** (в Excel помечены «Use in
Make = yes»; старые страницы оставлены только как исходники). Готовые макеты всех
страниц лежат в Figma «MitoDerm — Catalog · Product Pages» (страницы `Product — …`,
`About — …`, `Science — …`). Фото подставляются потом — на каждой странице оставлены слоты.

---

STEP 3 — PRODUCT PAGES. Use the attached catalogue as the single source of content. Keep the
existing visual system of this site (header, type scale, colours, buttons, footer, EN/HE/RU
switch). Replace the current product pages with the set below; add the missing ones; link them
from the Catalog grid (filters: All · Exosomes · Peels · Masks · Hair · Bio-Spicules · Home care ·
Devices). Do not invent facts, numbers or ingredients — only what is listed here.

DESIGN RULES (proven on the MITODERM protocol pages, keep them):
- Font Rubik (Light for display, Regular body, Medium labels, Bold wordmark); dark theme, gold #c9a24a accents, 1160px content column at 1440.
- Packshots: PNG with transparent background in the HERO slot; a soft gold glow is allowed only BEHIND a product on a dark surface — never a glow on an empty band.
- Motion (vanilla Motion): hero fade-in, packshots rise on reveal, the gold step line draws on scroll, section indicator in the header; with prefers-reduced-motion everything is static and fully visible. No JavaScript → nothing hidden.
- Acceptance at 1440×900 and 390×844: 0 console errors, 0 horizontal scroll, every packshot visible after scrolling.
- Hebrew version: same skeleton mirrored RTL (text right-aligned, nav and chips mirrored), texts verbatim from the "Blocks HE" sheet of the Excel, Latin product/ingredient names stay Latin, dashes and punctuation as in the Hebrew catalogue.

PAGE TEMPLATE (same order on every product page):
1. Hero — eyebrow (line/category), product name, tagline, 2-sentence lead, buttons
   "Contact for price" + "Discover the science", photo slot HERO (packshot, transparent bg).
2. Stats strip — 4 key numbers.
3. 01 Benefits — 4 cards.
4. 02 Protocol — 3 steps (or "How it works").
5. 03 Formula — active ingredients list + photo slot TEXTURE (macro).
6. 04 Kit — what's in the box (if a kit) / Volume.
7. 05 Indications — chips.
8. Works with — chips linking to related products.
9. CTA — "Bring <product> to your clinic" (professional) or "Where to buy" (home care), note
   "For professional use only" where marked PRO.
10. Footer.
Photo slots: HERO 560×560, TEXTURE 520×360, plus GALLERY (3 × 371×400) at the end of the
Formula section. Leave them as clearly labelled placeholders; photos will be added by us.

ROADMAP (build in this order):
A. Knowledge pages: About MITODERM · Synthetic exosomes · BIOSPICULE™ technology.
B. PRO exosome line: V-TECH SYSTEM · EXO-NAD · EXOCELL MASK · EXOSIGNAL HAIR.
C. PRO bio-spicules: MICRO BOOST 10%.
D. Home care: EXOTECH GEL · EXOSIGNAL SPRAY · CELL RENEW 1.5% · CELLULAR AGE DEFENSE 2.5% ·
   DERMA RECOVERY CREAM.
E. Devices: MITOPEN · MITOSCAN.
F. Catalog grid: 12 product cards (name, one-liner, line tag, "View product →") + 3 knowledge
   cards; remove placeholder cards "EXOXE", "Bio-Spicule 01–04".

=== KNOWLEDGE PAGES ===

ABOUT MITODERM — "Where science meets beauty"
Israeli company: development, import and distribution of advanced technologies for professional
aesthetics, skin and scalp care. Partners: leading laboratories and manufacturers in Italy and
South Korea. Portfolio core: synthetic exosomes, peptides, PDRN, NAD+, biomimetic ingredients;
BIOSPICULE™ (purified Spongilla spicules). Principles: innovation, quality, safety, ease of use.
Offers training, scientific education, full treatment protocols. Name: MITO = cellular energy
(function, renewal, vitality) + DERM = the skin. Sections: Bridging science and clinical
practice · Our standards · The story behind the name.

SYNTHETIC EXOSOMES — "Engineered delivery, not biological material"
Exclusive importer of VM Corporation (Italy; sold to professionals in 100+ countries).
Exosomes = nanoscale vesicles for intercellular communication. Synthetic exosomes = engineered
delivery systems mimicking natural vesicles; encapsulate selected actives (PDRN, peptides…),
protect them and enhance penetration. Advantages: not derived from human/animal/plant material;
can carry larger molecules; targeted, efficient delivery.

BIOSPICULE™ TECHNOLOGY — "4th-generation bio-microneedling"
Spongilla = freshwater sponge; its skeleton = spongin fibres + silica micro-needles (spicules).
Millions of micro-needles penetrate 80–300 µm, stay up to 72 h: mechanical stimulation →
microcirculation, metabolism, collagen, renewal. 4th generation: Korean processing purifies and
sorts spicules by size (four types) instead of a single non-uniform powder; controlled
length mix = Hybrid Spicule Delivery System. Two mechanisms: Resurfacing (renewal) + Delivery
(temporary micro-pathways for actives) = BIOMICRONEEDLING. Diagram: Spicule → Resurfacing →
Delivery. Indications: anti-ageing, wrinkles, pores, firming, brightening, uneven tone, PIH,
lentigo, scars, post-acne, mild–moderate acne, thin/devitalised/dull skin; face, neck,
décolleté, hands, back.

=== PRO · SYNTHETIC EXOSOME LINE ===

EXO-NAD (PRO) — Three-stage biohacking system for skin renewal  [NEW VERSION — replaces the existing EXO-NAD page]
Eyebrow: Synthetic exosomes · skin longevity peel. Lead: professional multi-stage peeling
system from the VM laboratories (Italy), inspired by cellular-longevity research: biphasic
peel + neutralizer-restorer + Longevity Serum with synthetic exosomes, NAD⁺ and peptides.
Stats: 3 treatment stages · ≈30% AHA+BHA in the peel · 3–4 wk between treatments · Fitzpatrick I–VI.
Benefits: Renewal (dead-cell removal, texture) · Firmness & elasticity, fewer fine lines ·
Even tone (sun/age spots, PIH, post-acne; melasma-prone skin) · Radiance (pre-event; mature,
tired, dull skin).
System: 1 EXO BIPHASIC PEEL — lipid phase for comfort + acid phase (AHA+BHA ≈30%,
tranexamic acid, antioxidants) → 2 pH NORMALIZER — neutralises and rebalances; collagen,
peptides, vitamin B12 → 3 LONGEVITY SERUM — synthetic exosomes, NAD⁺, Epitalon, GHK-Cu,
peptides. Finish: EXOCELL MASK or DERMA RECOVERY CREAM + sun protection.
Formula: AHA+BHA complex (≈30%) · tranexamic acid & antioxidants · collagen & biomimetic
peptides · vitamin B12 · synthetic exosomes · NAD⁺ · Epitalon · GHK-Cu.
Kit: Biphasic Peel 15 ml · pH Normalizer 5 × 5 ml · Longevity Serum 5 × 5 ml.
Indications: dead-cell removal · accelerated renewal · texture · firmness & elasticity ·
fine lines · uneven tone · melasma-prone skin · sun & age spots · PIH & post-acne marks ·
radiance · mature, tired, dull skin · anti-ageing. Works with: EXOCELL MASK · DERMA
RECOVERY CREAM · EXOTECH GEL.

EXOCELL MASK (PRO) — Advanced bio-cellulose mask, your second skin  [NEW VERSION — replaces the existing EXOCELL page]
Eyebrow: Synthetic exosomes · professional mask. Lead: advanced adhesion technology,
synthetic exosomal structures and hydrating, soothing actives — the finishing step after
professional treatments when the skin needs intensive hydration and barrier support.
Stats: 5 masks per box · bio-cellulose structure · post-procedure finishing step · instant hydration & cooling.
Benefits: Intensive hydration · Soothing after treatments · Barrier support, cooling ·
Smoothing & firming — fresh, calm, supple, radiant skin.
How it works: 1 Apply on cleansed skin — adheres evenly, minimal air pockets → 2 Moist
environment, continuous serum–skin contact → 3 Remove: hydrated, smooth, radiant skin
(dry, tired, sensitive, devitalised skin).
Formula: synthetic exosomal structures · polynucleotides · hyaluronic acid, glycerol &
plant oils · plant & algae extracts · Hexapeptide-8 · Coenzyme Q10 · Nannochloropsis
oculata · Spilanthes acmella. Pack: 5 masks.
Indications / best used after: V-TECH SYSTEM · EXO-NAD · MICRO BOOST 10% · microneedling ·
post-procedure protocols · dry, tired, sensitive, devitalised skin.

V-TECH SYSTEM (PRO) — Clinical skin regeneration at the dermal level
Eyebrow: Synthetic exosomes · professional kit. Lead: professional treatment kit based on
synthetic exosomes, advanced Italian technology; serum + gel mask.
Stats: 5 ampoules · 5 ml each · 4 treatments / course · 2 weeks interval.
Benefits: Hydration & radiance from the first treatment · Structure, texture, density improve
through the course · Firming & elasticity · Even tone.
Protocol: 1 Microneedling (RF microneedling / BIOSPICULE™ 10% / CO₂ laser also possible) →
2 Serum 1–1.5 ml per treatment, face/neck/décolleté/hands → 3 Gel mask after the ampoule, no
rinse; finish with EXOCELL MASK or DERMA RECOVERY + sun protection. Course ≥4 treatments every
two weeks; maintenance every six months.
Formula — Serum: PDRN 2% (20 mg/ml, salmon) · Acetyl Decapeptide-3 & Oligopeptide-20 · Apple
stem cell extract (Malus domestica). Gel mask: PDRN 1% low MW · Acetyl Heptapeptide-9 with
colloidal gold · Copper Tripeptide-1 · Snail secretion polysaccharides · Hyaluronic acid · Aloe.
Kit: Serum 5 × 5 ml · Gel mask 5 × 5 ml.
Indications: deep revitalisation · ageing signs · wrinkles & fine lines · dull skin · post-acne
marks & scars · post-surgical scars · uneven texture/tone · PIH · loss of elasticity · firming ·
barrier support. Works with: MITOPEN · EXOCELL MASK · DERMA RECOVERY CREAM · EXOTECH GEL.

EXO-NAD SKIN LONGEVITY PEEL (PRO) — Three-stage biohacking system for skin renewal
Eyebrow: Medical-grade longevity peel. Lead: biphasic peel + pH normalizer + Longevity Serum
with synthetic exosomes, NAD⁺, biomimetic peptides; developed in VM labs, Italy.
Stats: 3 steps · ~30% AHA+BHA · 1 treatment / 3–4 weeks · Fitzpatrick I–VI.
Benefits: Even tone & texture · Radiance · Fewer fine lines · Firmness & elasticity.
Protocol: 1 EXO BIPHASIC PEEL — lipid phase (comfort) + acid phase (AHA/BHA ≈30%, tranexamic
acid, antioxidants) → 2 pH NORMALIZER — neutralises, rebalances; collagen, peptides, vitamin
B12 → 3 LONGEVITY SERUM — synthetic exosomes, NAD⁺, Epitalon, GHK-Cu, peptides: cellular
communication, energy, renewal. Finish: EXOCELL MASK or DERMA RECOVERY CREAM + sun protection.
Single treatment or course; all skin types, year-round; may combine with hydration devices.
Formula: AHA + BHA · tranexamic acid · antioxidants · collagen · biomimetic peptides · vitamin
B12 · synthetic exosomes · NAD⁺ · Epitalon · GHK-Cu.
Kit: Biphasic Peel 15 ml · pH Normalizer 5 × 5 ml · Longevity Serum 5 × 5 ml.
Indications: dead-cell removal · accelerated renewal · texture · firmness · fine lines · uneven
tone · melasma-prone skin · sun/age spots · PIH & post-acne marks · radiance · pre-event ·
mature/tired/dull skin · anti-ageing. Works with: EXOCELL MASK · DERMA RECOVERY CREAM ·
EXOTECH GEL.

EXOCELL MASK (PRO) — Advanced bio-cellulose mask, your second skin
Eyebrow: Professional exosome mask. Lead: ultra-thin bio-cellulose mask with synthetic exosomal
structures and soothing/hydrating actives; the finishing step after professional treatments.
Stats: 5 masks / box · 100% bio-cellulose · post-procedure · immediate hydration.
Benefits: Intensive, immediate hydration · Soothing after treatments · Supports the epidermal
barrier · Cooling, smoothing, firming.
How it works: 1 Apply on cleansed skin — adheres with minimal air pockets → 2 Moist environment,
continuous contact of serum and skin → 3 Skin left hydrated, smooth, supple, radiant.
Formula: synthetic exosomal structures · polynucleotides · hyaluronic acid, glycerol & plant
oils · plant & algae extracts · Hexapeptide-8 · Coenzyme Q10 · Nannochloropsis oculata ·
Spilanthes acmella.
Pack: 5 masks.
Indications: post-procedure protocols · dry, tired, sensitive, devitalised skin. Works with:
V-TECH SYSTEM · EXO-NAD · MICRO BOOST 10% · all in-clinic protocols.

EXOSIGNAL HAIR (PRO) — Synthetic exosome system for scalp treatments
Eyebrow: Professional scalp & follicle care. Lead: VM Corporation formula — synthetic exosomal
delivery, high-concentration PDRN, hyaluronic acid, eight biomimetic peptides, plant stem
cells, vitamins, antioxidants; supports scalp health and hair growth, reduces shedding.
Stats: 5 ampoules · 5 ml · PDRN 2% · 8 peptides.
Benefits: Balanced, hydrated scalp · Better blood supply & follicle nourishment · Revitalises
dormant follicles · Longer anagen, shorter telogen.
Protocol: 1 Diagnose with MITOSCAN → 2 Scalp microneedling with MITOPEN → 3 Apply EXOSIGNAL
HAIR; home care with EXOSIGNAL SPRAY between sessions. Diagram: Scalp → Follicle → Hair.
Formula: synthetic exosomal structures · high-MW hyaluronic acid · SH-Oligopeptide-1/2 ·
SH-Polypeptide-1/9/11 · Acetyl Decapeptide-3 · Copper Tripeptide-1 (GHK-Cu) · Oligopeptide-20 ·
Swiss apple stem cells · Panthenol B5 · Biotin B7 · Pyridoxine B6 · Thiamine B1 · PDRN 2%
(20 mg/ml, salmon).
Pack: 5 ampoules × 5 ml.
Indications (men & women): seasonal/increased hair loss · thinning, reduced density · fine,
weak hair · dry/oily/unbalanced scalp · androgenetic alopecia · alopecia areata · before/after
hair transplant. Works with: MITOPEN · MITOSCAN · EXOSIGNAL SPRAY.

=== PRO · BIOSPICULE™ ===

MICRO BOOST 10% (PRO) — The most concentrated serum in the BIOSPICULE™ range
Eyebrow: BIOSPICULE™ professional in-clinic treatment. Lead: 10% hydrolyzed sponge in a 3 ml
syringe — the aesthetician controls amount, massage time and intensity; a BIOMICRONEEDLING
delivery system, not just a peel.
Stats: 10% spicules · 3 ml syringe · 40% mini (80–100 µm) · 60% long (300–360 µm).
Benefits: Renewal — resurfacing · Delivery of actives through micro-channels · Two depths of
stimulation · Up to 72 h continued action.
Protocol: 1 Diagnosis & cleansing → 2 Massage with MICRO BOOST 10% (dose and duration by skin
diagnosis) → 3 Delivery: V-TECH or Longevity Serum, then EXOCELL MASK; finish DERMA RECOVERY
CREAM (mandatory at home) + sunscreen. Expect tingling, temporary redness, dryness, tightness
or peeling in the following days.
Formula: Hydrolyzed Sponge 10% — mini + long spicules.
Indications (after professional assessment): ageing · dull, tired skin · rough/uneven texture ·
enlarged pores · uneven tone · post-acne & surgical scars · pigmentation, sun spots, PIH ·
wrinkles & fine lines · loss of elasticity · smokers' skin · mild–moderate acne · firming ·
overall skin quality. Works with: V-TECH SYSTEM · EXO-NAD Longevity Serum · EXOCELL MASK ·
DERMA RECOVERY CREAM.

=== HOME CARE · SYNTHETIC EXOSOME LINE ===

EXOTECH GEL — Cellular recovery & advanced skin renewal
Eyebrow: Home care · exosome line · 30 ml. Lead: continuation of professional care at home;
synthetic exosomes with hydrating, repairing, anti-ageing actives; lightweight daily gel.
Stats: 30 ml · daily use · light gel · exosomes + PDRN.
Benefits: Maintains in-clinic results · Hydration & renewal · Elasticity & vitality · Fresh,
non-greasy feel.
How to use: 1 Cleanse → 2 Apply morning/evening → 3 Pair with the clinic programme (V-TECH,
EXO-NAD, BIOSPICULE™ line).
Formula: synthetic exosomes · PDRN polynucleotides · biomimetic peptides, gold & copper ·
hyaluronic acid · purified snail polysaccharides.
Indications: normal to combination · dry/dehydrated · tired, dull · first signs of ageing and
fine lines. Works with: V-TECH SYSTEM · EXO-NAD · BIOSPICULE™ serums.

EXOSIGNAL SPRAY — Follicular support & scalp maintenance
Eyebrow: Home care · scalp · 15 ml. Lead: daily no-rinse spray that keeps the scalp balanced and
follicles supported between EXOSIGNAL HAIR treatments; rapidly absorbed.
Stats: 15 ml · daily · no rinse · scalp & follicle.
Benefits: Scalp balance & follicle activity · Relieves dryness/discomfort · Fuller, stronger-
looking hair · Targets thinning areas.
How to use: 1 Part the hair → 2 Spray directly on the scalp → 3 Massage lightly; do not rinse.
Formula: scalp-balancing and nourishing actives (as per catalogue).
Indications: hair thinning (women & men) · fine, brittle hair · scalp imbalance · hair-loss
programmes · maintenance after a course · after hair transplantation. Works with: EXOSIGNAL
HAIR · MITOPEN · MITOSCAN.

=== HOME CARE · BIOSPICULE™ LINE ===

CELL RENEW 1.5% — At-home serum for skin renewal and brightening
Eyebrow: BIOSPICULE™ serum · 30 ml. Lead: moderate spicule concentration introduces the skin to
an advanced renewal routine — radiant, smooth, even complexion; gentle tingling on massage.
Stats: 1.5% spicules · 30 ml · daily · all skin types.
Benefits: Renewal & brightening · Smoother texture, smaller pores · Even tone, fades marks ·
Hydrated, fresh skin.
How to use: 1 Clean, dry skin, massage gently (no pressure) → 2 Follow with DERMA RECOVERY
CREAM → 3 Sunscreen during the day.
Formula: Hydrolyzed Sponge 1.5% · Niacinamide · Galactomyces Ferment Filtrate · Sodium DNA ·
Salicylic + Citric acid · Sodium Hyaluronate, Glycerin & Betaine.
Indications: all skin types · dull, tired skin · texture · enlarged pores · uneven tone ·
hyperpigmentation · post-inflammatory marks · anti-ageing · fine lines · firming. Works with:
DERMA RECOVERY CREAM · CELLULAR AGE DEFENSE 2.5% (next step).

CELLULAR AGE DEFENSE 2.5% — Advanced serum for firming and anti-ageing
Eyebrow: BIOSPICULE™ serum · 30 ml. Lead: higher spicule concentration with Bakuchiol, five
peptides and moisture actives — a more intensive programme for signs of ageing; transition
gradually from CELL RENEW 1.5%.
Stats: 2.5% spicules · 30 ml · 5 peptides · Bakuchiol.
Benefits: Firmness & elasticity · Fewer wrinkles and fine lines · Refined texture & pores ·
Brightening.
How to use: 1 Clean, dry skin, massage gently (noticeable tingling; don't rub) → 2 DERMA
RECOVERY CREAM → 3 Sunscreen; start with 1.5% if not accustomed.
Formula: Hydrolyzed Sponge 2.5% · Bakuchiol · Acetyl Hexapeptide-8, Acetyl Tetrapeptide-5,
Palmitoyl Tetrapeptide-7, Palmitoyl Tripeptide-5, Carnosine · Hydrolyzed Collagen · Adenosine ·
Yeast Beta-Glucan · Akebia Quinata & Camellia Japonica extracts.
Indications: all skin types · wrinkles & fine lines · anti-ageing · elasticity · tired, dull
skin · rough texture · pores · firming & brightening · post-acne scars · mild–moderate acne.
Works with: DERMA RECOVERY CREAM · CELL RENEW 1.5%.

DERMA RECOVERY CREAM — Snail collagen · restorative cream for soothing and barrier support
Eyebrow: BIOSPICULE™ line · 50 ml. Lead: spicule-free daily cream that completes every spicule
and in-clinic protocol — hydration, softness, comfort, barrier support during renewal.
Stats: 50 ml · 0% spicules · daily · all skin types.
Benefits: Soothes after procedures · Rebuilds the moisture barrier · Softens roughness/flaking ·
Healthy-looking glow.
How to use: 1 After CELL RENEW / CELLULAR AGE DEFENSE → 2 After in-clinic V-TECH, EXO-NAD,
MICRO BOOST 10% → 3 Morning & evening on clean skin.
Formula: Panthenol (B5) · Madecassoside (Centella asiatica) · Allantoin · Shea Butter ·
Niacinamide · Hydrolyzed Collagen · Snail Secretion Filtrate (purified polysaccharides).
Indications: all skin types · after in-clinic treatment · dry/dehydrated · post-spicule
support · irritated, rough, flaky skin. Works with: all PRO protocols · CELL RENEW 1.5% ·
CELLULAR AGE DEFENSE 2.5%.

=== DEVICES ===

MITOPEN — Professional microneedling pen
Eyebrow: Clinic equipment. Lead: cordless pen creating temporary micro-channels — the pathway
for MITODERM actives; precise, uniform protocols.
Stats: 0.25–2.5 mm depth · 5 speeds · cordless · face & scalp.
Benefits: Adjustable depth by area/indication · Controlled channel density · Quiet, ergonomic ·
Built for active delivery.
Protocol: 1 Set depth & speed → 2 Microneedling → 3 Apply V-TECH SYSTEM or EXOSIGNAL HAIR.
Works with: V-TECH SYSTEM · EXOSIGNAL HAIR · MICRO BOOST 10%.

MITOSCAN — Hair & scalp diagnostic system · "Measure what matters"
Eyebrow: Clinic equipment. Lead: high-magnification analysis (×50, ×200) of hair density,
follicle count, hair diameter, scalp condition; HD imaging and tracking over time.
Stats: ×50 · ×200 · HD imaging · before/after tracking.
Benefits: Clear starting point for the patient · Findings on screen, not impressions · Realistic
goals & personalised plan · Trust and documented results.
How it works: 1 Scan & photograph areas → 2 Explain findings on screen → 3 Compare progress
over the course. Works with: EXOSIGNAL HAIR · EXOSIGNAL SPRAY · MITOPEN.

=== CATALOG GRID CARDS (one-liners) ===
V-TECH SYSTEM — Professional synthetic-exosome kit for dermal regeneration (PRO)
EXO-NAD — 3-step longevity peel with NAD⁺ and exosomes (PRO)
EXOCELL MASK — Bio-cellulose exosome mask, the post-treatment finish (PRO)
EXOSIGNAL HAIR — Exosome + PDRN system for scalp and follicles (PRO)
MICRO BOOST 10% — The most concentrated BIOSPICULE™ in-clinic serum (PRO)
EXOTECH GEL — Daily exosome gel that keeps clinic results (home)
EXOSIGNAL SPRAY — No-rinse scalp spray between treatments (home)
CELL RENEW 1.5% — Spicule serum for renewal and brightening (home)
CELLULAR AGE DEFENSE 2.5% — Spicule serum with Bakuchiol and 5 peptides (home)
DERMA RECOVERY CREAM — Snail-collagen barrier cream after every protocol (home)
MITOPEN — Cordless microneedling pen, 0.25–2.5 mm (device)
MITOSCAN — ×50/×200 scalp & hair diagnostics (device)
MITOTECH CELL BOOSTER — Two-vial cell booster for in-clinic protocols with MITOPEN or MICRO BOOST 10% (PRO, "Coming soon" card, no page yet; protocol: booster vial poured into the concentrated powder vial → clear solution, up to 2 ml for face/neck/décolleté; finish EXOCELL MASK + DERMA RECOVERY CREAM + SPF 30)

STEP 4 (later) — 3D VERSION: the same pages with 3D packshots (hero product rotating on scroll / drag), to be briefed separately after the pages are approved.
