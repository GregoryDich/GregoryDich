# SnapPlay AI — Economics

This is the unit-economics model for the pricing in contract §3, worked from first
principles. Every input is listed in §2 so the numbers can be re-run when a price
changes. Where the figures in the original product brief ($0.012 per job, ~$0.75 fees
on a $9 pack, "85–87 % margin") differ from the arithmetic, §12 says so.

## 1. The model

| plan (§3) | price | credits | price per credit | notes |
|-----------|-------|---------|------------------|-------|
| `free` | $0 | 3 at signup | — | one-time, the hook |
| `pack_50` | $9.00 | 50 | $0.180 | one-time |
| `sub_monthly` | $7.99 / month | 60 per month | $0.133 | 26 % cheaper per credit than the pack |

One credit is one job (§2): up to 60 s of audio → four stems, MIDI and analysis. A
credit is reserved at submission and captured only on success; failed jobs cost
nothing (§6). Subscription credits **do not roll over** (§13): each renewal grants the
plan's credits with `expires_at` = the end of that billing period and `expire_credits()`
sweeps the remainder, expiring balances being spent before non-expiring ones. Credit-pack
credits never expire. That is what makes breakage a real line in §11 for subscribers and
not for pack buyers.

The revenue target discussed throughout is **$135 / day**, which is exactly 15 packs
a day (15 × $9), or ≈ $4,050 / month, or ≈ 507 active monthly subscribers.

## 2. Assumptions

| # | assumption | value | source / note |
|---|-----------|-------|---------------|
| A1 | `g5.xlarge` (A10G) on-demand, us-east-1 | ≈ $1.006 / h | AWS list price; verify at deploy time |
| A2 | `g4dn.xlarge` (T4) on-demand | ≈ $0.526 / h | same |
| A3 | Job wall-clock on A10G | ≈ 2 s | §7 budget (1.8 s) + queue/IO overhead |
| A4 | Job wall-clock on T4 | ≈ 5–7 s | §7: separation alone 3–5 s on T4 |
| A5 | Input | 30 s stereo FLAC ≈ 3 MB | 16-bit 44.1 kHz PCM is 5.3 MB; FLAC ≈ 55 % |
| A6 | Output | 4 stems × 5.3 MB WAV + MIDI ≈ 21 MB | 16-bit 44.1 kHz; 24-bit would be 1.5 ×, float 2 × |
| A7 | S3 storage | $0.023 / GB-month, 24 h retention | §10 lifecycle rule |
| A8 | S3 requests | $0.005 / 1,000 PUT, $0.0004 / 1,000 GET | |
| A9 | Egress, S3 direct | $0.09 / GB | first 10 TB tier; the 100 GB/month free allowance ignored |
| A10 | Egress, CloudFront | $0 up to 1 TB / month, then $0.085 / GB | always-free tier |
| A11 | Egress, Cloudflare R2 (`S3_ENDPOINT_URL`) | $0 | |
| A12 | LemonSqueezy fee | 5 % + $0.50 per transaction | merchant-of-record base fee; PayPal, international-card and subscription surcharges exist and are **not** modelled, so this is a floor |
| A13 | Prices are tax-exclusive | | if tax-inclusive, VAT (up to ~25 % in the EU) comes out of the $9 before anything else |
| A14 | Control plane | ≈ $85 / month | 2 Fargate tasks at 0.5 vCPU / 1 GB ≈ $36, ALB ≈ $22, Supabase Pro $25; NAT / VPC endpoints ≈ $0 with S3 gateway endpoint and workers in public subnets |
| A15 | Affiliate commission | 30 % of net revenue after provider fees | §12 |
| A16 | Free → paid conversion | 3 % (range 1–5 %) | typical for freemium desktop tools; unmeasured until launch |
| A17 | Buyers consume all credits | worst case for cost | breakage only improves the numbers |
| A18 | Month | 730 h, 30.4 days | |

## 3. Cost per job

### 3.1 GPU time

| instance | $/h | $/s | 2 s job | 4 s job | realistic |
|----------|-----|-----|---------|---------|-----------|
| `g5.xlarge` (A10G) | 1.006 | 0.000279 | **$0.00056** | $0.00112 | 2 s (§7) → $0.00056 |
| `g4dn.xlarge` (T4) | 0.526 | 0.000146 | $0.00029 | $0.00058 | 5–7 s (§7) → $0.00073–$0.00102 |

The T4 does not do a 2 s job, so its "2 s" column is hypothetical: per job the T4 is
only about 30 % cheaper than the A10G once the real durations are used, while being
2.5–3.5 × slower for the user.

This is the cost of GPU **seconds**. It is the true marginal cost only when the GPU is
billed per second (serverless) or is already running for other jobs. With an always-on
instance the marginal cost of one more job is effectively zero and the *fixed* cost is
what matters (§7 below). Both views are needed; conflating them is how the "$0.012"
figure came about (§12).

### 3.2 Storage, requests and egress

Per job, from A5–A11:

| item | quantity | cost |
|------|----------|------|
| storage, 24 MB for 1 day | 0.024 GB × $0.023 / 30.4 | $0.00002 |
| requests, ~6 PUT + ~6 GET | | $0.00003 |
| egress, S3 direct | 0.021 GB × $0.09 | **$0.0019** |
| egress, CloudFront within free tier, or R2 | | $0 |

Egress is the largest *variable* line item — three times the GPU seconds. At 750
jobs/day the stems add up to ≈ 480 GB / month, still inside CloudFront's 1 TB free
tier; above ≈ 1,500 jobs/day the CloudFront rate applies, and R2 is free at any volume.

### 3.3 Variable cost per job

| scenario | GPU seconds | storage + requests | egress | **total** |
|----------|-------------|--------------------|--------|-----------|
| A10G, S3 direct (conservative, used below) | $0.00056 | $0.00005 | $0.0019 | **$0.0025** |
| A10G, CloudFront free tier or R2 | $0.00056 | $0.00005 | $0 | **$0.0006** |
| T4, S3 direct | $0.0009 | $0.00005 | $0.0019 | $0.0029 |

The rest of this document uses **$0.0025 / job** as the variable cost.

## 4. Payment fees

LemonSqueezy is a merchant of record and charges 5 % + $0.50 per transaction (A12).

| plan | price | 5 % | + $0.50 | **fees** | effective rate | **net** |
|------|-------|-----|---------|----------|----------------|---------|
| `pack_50` | $9.00 | $0.45 | $0.50 | **$0.95** | 10.6 % | **$8.05** |
| `sub_monthly` | $7.99 | $0.40 | $0.50 | **$0.90** | 11.3 % | **$7.09** |

The fixed $0.50 is why fees are ~11 % rather than 5 % at these price points: a $9
product pays proportionally twice as much as a $50 one. (The Paddle path, §4 of the
contract, has a comparable MoR fee structure; the same arithmetic applies with its
rates.)

## 5. Unit margins

Contribution per sale, before any fixed cost, assuming full consumption of the credits
(A17):

| | `pack_50` | `sub_monthly` (one month) |
|---|---|---|
| price | $9.00 | $7.99 |
| − provider fees | $0.95 | $0.90 |
| = net revenue | $8.05 | $7.09 |
| − variable cost (credits × $0.0025) | 50 × = $0.125 | 60 × = $0.15 |
| **= contribution** | **$7.93** | **$6.94** |
| contribution margin on price | **88.1 %** | **86.9 %** |
| net revenue per credit | $0.161 | $0.118 |
| contribution per credit | $0.159 | $0.116 |

Two readings of the same table:

* **Per unit, the product is extremely cheap to serve.** Serving 50 jobs costs 12.5
  cents. Nothing about pricing needs to change on cost grounds.
* **This is not "gross margin" for the business** unless the GPU is billed per second.
  With an always-on instance the fixed floor (§7) must be covered first, and the
  margin at any given volume is what §10 shows: negative below ≈ 3.4 packs / day,
  ≈ 68 % at the $135 / day target on `g5.xlarge`.

## 6. Affiliate commission (§12)

Commission is 30 % of net revenue after provider fees, written in the same transaction
as the credit grant.

| | `pack_50` | `sub_monthly` |
|---|---|---|
| net revenue | $8.05 | $7.09 |
| affiliate commission (30 %) | $2.42 | $2.13 |
| contribution after commission | **$5.51** | **$4.81** |
| contribution margin on price | **61.2 %** | **60.2 %** |

An affiliate-sourced sale carries **27 points less margin** than a direct one. If a
fraction *f* of sales comes through affiliates, contribution per pack is
$7.93 − $2.42 × *f*, and the `g5.xlarge` break-even rises from 3.4 to 4.9 packs / day
at *f* = 1.

Two consequences of the settled policy in contract §13:

* **Commissions recur, with no cap.** Every purchase event that reaches
  `record_purchase` — a pack, a subscription's first payment and each renewal — writes
  one commission row at the affiliate's rate on `net_cents`. An affiliate therefore earns
  30 % of every renewal for the life of the subscriber. Capping at the first *n* months
  is common in this market; it is a product decision, and changing it means changing
  `record_purchase` and §13, not just a spreadsheet.
* **Voids.** A refund or chargeback must set the commission to `void` before payout;
  a payout hold longer than the card-network chargeback window (typically 30 days or
  more) avoids clawbacks. The `commission_status` enum is `pending | paid | void`.

## 7. Fixed floor: always-on GPU vs scale-to-zero

| configuration | GPU | control plane (A14) | **per month** | **per day** | first-job latency after idle |
|---|---|---|---|---|---|
| `g5.xlarge` always-on, on-demand | $734 | $85 | **≈ $820** | **$26.9** | 2.0 s target holds |
| `g5.xlarge` always-on, 1-year Savings Plan (≈ 30–40 % off; verify) | ≈ $470–510 | $85 | ≈ $560–600 | ≈ $19 | 2.0 s |
| `g4dn.xlarge` always-on | $384 | $85 | **≈ $470** | **$15.4** | ~5 s target |
| GPU only during peak hours (12 h / day) | $367 | $85 | ≈ $450 | ≈ $14.9 | 2.0 s in-window, minutes off-peak |
| Spot `g5.xlarge` (typically 50–70 % below on-demand; interruptible) | ≈ $220–370 | $85 | ≈ $300–450 | ≈ $10–15 | 2.0 s, with occasional redeliveries |
| Scale to zero on ECS | GPU seconds only | $85 | ≈ $85 + usage | $2.8 + usage | **minutes** (instance boot + multi-GB image pull + model load) |
| Serverless GPU (`modal` / `runpod` backends, §7) | per-second, ≈ 10 % above EC2 on-demand | $85 | ≈ $85 + usage | $2.8 + usage | tens of seconds cold; a keep-warm container costs about the same as always-on |

Scale-to-zero on ECS is incompatible with the product promise: the first user after
any idle gap waits minutes, and at 15 jobs / day almost every job is "the first after
an idle gap". The realistic choices are always-on (accept the floor), serverless GPU
(accept 20–60 s cold starts on a fraction of jobs), or peak-hours scheduling.

## 8. Break-even

Contribution per pack is $7.93; per subscription month $6.94 (§5).

| configuration | fixed / day | packs / day to break even | ≈ packs / month | or active subscribers | ≈ paid jobs / day at full consumption |
|---|---|---|---|---|---|
| `g5.xlarge` always-on | $26.9 | **3.4** | 103 | 118 | 170 |
| `g4dn.xlarge` always-on | $15.4 | 1.9 | 59 | 68 | 97 |
| serverless / scale-to-zero (control plane only) | $2.8 | 0.35 | 11 | 12 | 18 |

Break-even is in **sales**, not jobs: revenue is recognised when a pack is bought,
and consumption only moves the small variable line. The "jobs / day" column is what
the GPU would actually process if every buyer used every credit.

## 9. The $135 / day target — an honest check

* **Unit economics are not the obstacle.** 15 packs / day → $120.75 net after fees
  → minus $1.88 variable → minus $26.9 fixed = **≈ $92 / day** (68 % of gross,
  ≈ $2,800 / month) on an always-on `g5.xlarge`. One A10G at 2 s / job is 1.7 %
  utilised at 750 jobs / day; GPU capacity is a rounding error until several thousand
  jobs / day.
* **Acquisition is the obstacle.** At a 3 % free-to-paid conversion (A16) 15 packs /
  day requires **≈ 500 signups / day (≈ 15,000 / month)**; at 1 % it is 1,500 / day.
  Every signup costs up to 3 × $0.0025 = $0.0075 in free jobs — $3.75 / day at 500
  signups — so the free tier is cheap; the question is whether the growth engine
  (`GROWTH.md`) can drive that many installs of a DAW plugin.
* **The target date matters more than the target.** Until sales pass 3.4 packs / day,
  an always-on A10G loses money; the sensible sequencing is serverless GPU (or
  peak-hours scheduling) until volume justifies a reserved instance, then a Savings
  Plan.
* **Subscriptions change the shape.** $135 / day from subscriptions alone needs ≈ 507
  active subscribers; at a 5–8 % monthly churn (assumption) that is 25–40 new
  subscribers / day just to stand still, but revenue then arrives without re-selling.

## 10. Sensitivity

Pack pricing, all jobs paid, full consumption, variable cost $0.0025 / job.

| jobs / day | ≈ packs / day | gross / day | fees | net | variable | contribution | **`g5` always-on P/L** | **`g4dn` always-on P/L** | **serverless P/L** | all-in cost / job on always-on `g5` |
|---|---|---|---|---|---|---|---|---|---|---|
| **15** | 0.3 | $2.70 | $0.29 | $2.42 | $0.04 | $2.38 | **−$24.55** | −$13.03 | −$0.41 | $1.61 |
| **100** | 2 | $18.00 | $1.90 | $16.10 | $0.25 | $15.85 | **−$11.08** | +$0.44 | +$13.06 | $0.24 |
| **750** | 15 | $135.00 | $14.25 | $120.75 | $1.88 | $118.88 | **+$91.95 (68 %)** | +$103.47 (77 %) | +$116.09 (86 %) | $0.032 |

With half of sales affiliate-sourced, the 750-row loses 7.5 × $2.42 = $18.11 / day of
contribution: `g5` P/L becomes ≈ +$74 / day (55 %).

The last column is the point of §12: the all-in cost per job on an always-on GPU is
$1.61 at launch volume and 3 cents at target volume. No single "cost per job" describes
the business.

## 11. Metrics to track

| metric | definition | why |
|--------|-----------|-----|
| signups / day, activations / day | accounts created; accounts that ran ≥ 1 job | top of funnel and the first 3-credit hook |
| free → paid conversion | buyers ÷ signups, by cohort week | the single biggest unknown (A16) |
| packs / day, new subs / day, active subs | from `purchases` and `subscriptions` | break-even in §8 is stated in these |
| ARPU, net revenue per credit | net after fees ÷ users; ÷ credits sold | tracks fee drag and pack / sub mix |
| credits sold vs credits captured | ledger `grant` vs `capture` | breakage; high breakage is margin now and churn later |
| jobs / day, GPU utilisation | captured jobs; worker busy-seconds ÷ available seconds | when to move from serverless to reserved |
| blended cost / job | (GPU + storage + egress + control plane) ÷ jobs | the honest replacement for "$0.012" |
| p50 / p95 job latency, queue wait | `started_at − created_at`, `finished_at − started_at` | the 2.0 s promise; cold-start exposure |
| failure rate, releases, refunds | ledger `release` + `refund` ÷ `reserve` | every failure is a free job and a support cost |
| affiliate share of net revenue, commission payable | from `affiliate_commissions` | 27-point margin gap in §6 |
| churn (subs), reactivation | cancelled ÷ active per month | required for any LTV claim |
| CAC by channel, LTV / CAC | ad spend + growth-engine cost ÷ new buyers | whether $135 / day is reachable at a profit |

## 12. Corrections to the source brief

| brief said | arithmetic gives | what to use |
|---|---|---|
| "$0.012 per job" | GPU seconds on an A10G cost $0.00056; the full variable cost is $0.0025 (S3 direct) or $0.0006 (CDN / R2). $0.012 corresponds to ≈ 43 s of A10G time, or to an always-on `g5.xlarge` amortised over ≈ 2,000 jobs / day — neither of which matches the 2 s job or the 15–750 jobs / day range. As an all-in figure it is 130 × too low at 15 jobs / day and 20 × too high at 750. | $0.0025 variable per job **plus** the fixed floor from §7 |
| "≈ $0.75 fees on a $9 pack" | 5 % + $0.50 = **$0.95** (10.6 %). $0.75 is what 5 % + $0.30 would give — a card-processor rate, not a merchant-of-record rate. | $0.95 per pack, $0.90 per subscription month, before surcharges |
| "85–87 % margin" | The brief's own inputs ($0.75 + 50 × $0.012) give 85.0 %. With corrected inputs the **contribution** margin is 88.1 % (pack) / 86.9 % (sub) — the two errors partly cancel. But that number excludes the GPU floor; the **operating** margin is negative below 3.4 packs / day and ≈ 68 % at the $135 / day target on an always-on `g5.xlarge`. | quote 88 % / 87 % as per-unit contribution; quote the §10 table for margin at a volume |
