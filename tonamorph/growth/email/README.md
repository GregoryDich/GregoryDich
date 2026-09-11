# Klaviyo email: templates, manifest, checker

Nine flow messages and one campaign as Klaviyo **code** templates, each with a plain-text
sibling, a manifest that declares what every template may reference, and a standard-library
checker. The layout is the one from `infra/supabase/email-templates/` (table-based, inline
styles, dark mode handled twice, the button as a `bgcolor` cell), so the GoTrue account mails
and these read as one family.

| slug | flow · step | trigger · delay | subject |
|---|---|---|---|
| `welcome-0h` | Welcome 1 | `Signed Up` · 0 h | Your 3 morphs are ready |
| `welcome-2d` | Welcome 2 | `Signed Up` · +2 d, no morph yet | Drop any track |
| `welcome-5d` | Welcome 3 | `Signed Up` · +5 d, no morph yet | Three loops producers morph first |
| `first-morph-success` | First morph | `Morph Completed` (morphs_total = 1) · +30 min | It's on your keys |
| `first-morph-failure` | Failed morph (**transactional**) | `Morph Failed` · +20 min, exit on a success within 1 h | That one didn't cost a morph |
| `credits-at-zero` | Zero credits | `Credits Exhausted` (plan = free) · 0 h, exit on purchase | 3 morphs down. Your MIDI stays. |
| `day-7-nudge` | Day-7, 0-morph branch | `Signed Up` · +7 d | Still have 3 free morphs |
| `win-back-day-30` | Win-back | segment `Dormant 30d` · 0 h, no refund | What changed in Tonamorph |
| `purchase-thank-you` | Purchase (**transactional**) | `Purchase Completed` · 0 h | Morphs added — three ways to use them well |
| `launch-week` | campaign | lists `Tonamorph waitlist` + `Tonamorph newsletter` | Tonamorph is live. Any track, now an instrument. |

Files: `templates/<slug>.html` + `templates/<slug>.txt`, `manifest.json` (one entry per
template: Klaviyo name, subject, preview text, flow, trigger metric, delay, transactional
flag, the exact `event.*` and `person|lookup` variables used), `build.py` (the checker),
`../tests/test_email_templates.py` (runs it under pytest and cross-checks the manifest
against `backend/app/services/growth.py`).

## What the copy follows

* **Bodies, subjects and preview texts are the ones in `docs/GTM_PLAN.md` Appendix A §4**,
  US English, verbatim. Three steps that appendix does not spell out are written here from
  the brand platform (§0), the landing copy (Appendix A §2) and the plugin strings
  (Appendix B §3): `welcome-2d`, `welcome-5d` and the `launch-week` campaign.
* **Numbers that depend on the account are variables with the verbatim number as the
  default**, because a referred friend starts with 5 morphs, not 3: `first-morph-success`
  renders `event.balance_after` ("2 morphs left" by default), `first-morph-failure` renders
  `person|lookup:'credits_available'` ("you still have 3" by default). The other figures in
  the copy (prices, 3 free morphs, 2 win-back morphs) are fixed by the offer in §0.
* **Where the plan's timings disagree, §3.3 and Appendix C §4 win over Appendix A §4:**
  first morph +30 min (not 20), failed morph +20 min (not 10), zero credits at 0 h (not 2 h).
* **Nobody is addressed by name.** The product does not collect names, so
  `person.first_name` is rejected by the checker; the mails simply start.
* **Klaviyo syntax only:** `{{ event.<property> }}` from the trigger metric,
  `{{ person|lookup:'<property>' }}` from the profile properties the backend writes,
  `{{ organization.name }}` / `{{ organization.full_address }}` (Klaviyo → Settings →
  Organization), `{% unsubscribe 'Unsubscribe' %}` in every marketing template and
  `{{ unsubscribe_link }}` in its text version, `{% if %}` for the two dynamic lines, filters
  `default`, `lookup`, `floatformat`. Every metric name and property comes from
  `backend/app/services/klaviyo.py` and `growth.py` (contract §14); `manifest.json` mirrors
  them so nothing can reference a property the backend never sends.
* **Every link** carries `?utm_source=klaviyo&utm_medium=email&utm_campaign=<flow slug>`
  plus `utm_content=<template slug>`. The personal checkout URLs in `credits-at-zero`
  come from the event (`checkout_url_pack_50`, `checkout_url_sub_monthly`, always with a
  query string for a signed-in user, so `&utm_…` is appended) and fall back to `/pricing`
  while the payment provider is not configured and the backend sends `null`.
* **Transactional templates** (`first-morph-failure`, `purchase-thank-you`) carry no
  unsubscribe link, no checkout URL and no link to `/pricing` or `/checkout`; the checker
  enforces it. "Receipt" points at `/account`; the payment provider mails its own receipt.
* **The literal "Tonamorph".** Like the GoTrue templates, these are the one place in the
  repository where the product name is written as a literal — Klaviyo has no variable for
  it (`organization.name` is the *account* name, used only in the footer). Everywhere else
  the name comes from `NEXT_PUBLIC_PRODUCT_NAME` (`web/README.md`). The checker allows the
  exact spelling `Tonamorph` and rejects any re-cased or misspelt variant. If the name ever
  changes, edit the ten `.html`, the ten `.txt`, the subjects in `manifest.json` and the
  `PRODUCT_NAME` constant in `build.py` together.

## 1. Founder: account, sender, lists (once, about 20 minutes)

1. klaviyo.com → create the account for **Tonamorph Audio**. Settings → Organization: the
   company name and a postal address (they render as `organization.name` /
   `organization.full_address` in every footer; CAN-SPAM requires the address).
2. Settings → Account → API keys: the **Public API Key / Site ID** goes to
   `NEXT_PUBLIC_KLAVIYO_COMPANY_ID` in Vercel (`docs/LAUNCH_CHECKLIST.md` §2.13); create a
   **Private API Key** with full access to Events, Profiles, Lists, Templates, Flows,
   Campaigns and Metrics and put it in the backend's `KLAVIYO_PRIVATE_API_KEY` (API server
   and GPU worker both; never in the repository). Connect the same key to the Klaviyo MCP.
3. Settings → Email → Domains and hostnames: add `tonamorph.com` as a dedicated sending
   domain and publish the DKIM and DMARC records it shows in Vercel DNS. Sender for every
   flow and campaign: `Tonamorph <support@tonamorph.com>`, reply-to `support@tonamorph.com`
   (the copy invites replies; support SLO in GTM §2.5).
4. Lists (the assistant can create them with `create_list`, `opt_in_process:
   "single_opt_in"` — consent is captured at sign-up as `marketing_opt_in`):
   `Tonamorph users` (every account), `Tonamorph newsletter` (only `marketing_opt_in`),
   `Tonamorph waitlist` (the landing page's "Notify me" before launch).
5. Segments (UI only): `Activated`, `Free no morph 48h`, `Paying`, `Dormant 30d` — the
   definitions are in `manifest.json` → `segments`.
6. Settings → Email → Tracking: leave Klaviyo's automatic UTM tracking **off**; the links
   already carry their parameters and would otherwise be tagged twice.

## 2. Seed the metrics before any flow

Klaviyo lists a metric only after its first event, and a flow cannot be built on a metric
that does not exist yet. Before step 4, from `backend/` with the private key in the
environment:

```sh
python -m app.services.klaviyo seed --email <a throwaway address you control>
# accepted 13 of 13 sample events
```

Then `get_metrics` through the MCP must list `Signed Up`, `Plugin Installed`, `Morph
Completed`, `Morph Failed`, `Credits Exhausted`, `Checkout Started`, `Purchase Completed`,
`Subscription Cancelled`, `Refund Issued`, `NPS Submitted`, `Referral Joined`, `Referral
Rewarded`, `Gift Granted`. Seed **before** creating flows: events that already happened
never enter a flow, so the throwaway profile receives nothing; suppress it afterwards
(`bulk_suppress_profiles`) so it can never be mailed. Repeat the seed whenever a new
metric is added to `app.services.klaviyo.METRICS`.

## 3. Assistant: push the templates through the Klaviyo MCP

For each entry in `manifest.json` → `templates`, in order:

1. `python3 growth/email/build.py --check` must print `0 problems` (below).
2. `create_email_template` with `data.attributes = {"name": <klaviyo_name>, "editor_type":
   "CODE", "html": <the .html file verbatim>, "text": <the .txt file verbatim>}`. Record
   the returned template id in the table at the end of this file. A later copy change is
   `update_email_template` with the same id and the new `html` / `text` — never a second
   `create`, or the flow keeps pointing at the old one.
3. `render_email_template` with the id and a context that exercises every variable, for
   example for `first-morph-failure`:
   `{"event": {"error_code": "worker_timeout", "stage": "separate"}, "person":
   {"credits_available": 2}, "organization": {"name": "Tonamorph Audio", "full_address":
   "…"}}` and for `credits-at-zero` once with the two `checkout_url_*` keys set and once
   without (the `/pricing` fallback). Read the returned HTML: every `{{ }}` resolved, the
   unsubscribe link present (marketing) or absent (transactional), the dark-mode CSS still in
   `<head>`. The endpoint is limited to 3 renders per second.
4. `create_template_preview_send_job` to the founder's address (needs the founder's
   confirmation in the call) — check Gmail, Outlook and one phone in dark mode.

The subject and preview text are message settings, not template content; step 4 below
copies them from the manifest. The template's hidden preheader `<div>` carries the same
preview text, so the inbox snippet is right even where the message setting cannot be given
(Windsor's `send-email` step has no preview field). The checker pins `<title>` and the
preheader to the manifest's subject and preview text.

## 4. Flows (Windsor `create_flow`, or the UI)

The Klaviyo MCP only reads flows (`get_flows`, `get_flow_report`). Two ways to build them:

**Path A — Windsor.** With Klaviyo connected in Windsor, `list_actions(connector="klaviyo")`
shows `create_flow` and `update_flow_status`. `create_flow` takes a `metric` trigger
(`metric_id` from `get_metrics`, optional `trigger_filter`) or a `list` trigger (`list_id`
from `get_lists`), `entry_action_id`, and `actions` wired by `temporary_id`: `time-delay`
(`unit`, `value`), `send-email` (`from_email`, `from_label`, `subject_line`, `template_id`,
`smart_sending_enabled`), `conditional-split` (`profile_filter`, `next_if_true`,
`next_if_false`). Flows are created in **draft**; `update_flow_status(flow_id, "live")` turns
them on. The Failed-morph flow, as one example:

```json
{
  "name": "Failed morph",
  "trigger": {"type": "metric", "metric_id": "<Morph Failed>"},
  "entry_action_id": "wait",
  "actions": [
    {"temporary_id": "wait", "type": "time-delay", "unit": "minutes", "value": 20,
     "links": {"next": "split"}},
    {"temporary_id": "split", "type": "conditional-split",
     "profile_filter": {"<Morph Completed at least once in the last 1 hour>": true},
     "next_if_true": null, "next_if_false": "send"},
    {"temporary_id": "send", "type": "send-email", "from_email": "support@tonamorph.com",
     "from_label": "Tonamorph", "subject_line": "That one didn't cost a morph",
     "template_id": "<first-morph-failure>", "smart_sending_enabled": false}
  ]
}
```

The `profile_filter` / `trigger_filter` shapes are untyped in Windsor's schema; if a call is
rejected, create the split or the trigger filter in the flow editor instead. Open every
created flow in the UI before it goes live.

**Path B — the UI.** Flows → Create flow → Build your own; the same triggers, delays,
splits and templates.

**UI only, either path:** the segment-triggered Win-back flow, the segments themselves,
the **transactional** flag on the Failed-morph and Purchase messages (message → Settings →
Transactional; it also disables the unsubscribe requirement), preview text, reply-to, and
smart sending (off for both transactional flows, on elsewhere).

| flow | trigger | steps |
|---|---|---|
| Welcome | `Signed Up` (Appendix C §4 says "added to list `Tonamorph users`"; the backend does not add to lists yet, so the metric is what fires today — switch the trigger once the list add exists) | 0 h `welcome-0h` → wait 2 d → split *morphs_total is not set or 0* → `welcome-2d` → wait 3 d → same split → `welcome-5d` |
| First morph | `Morph Completed`, trigger filter *morphs_total equals 1* | wait 30 min → `first-morph-success` |
| Failed morph | `Morph Failed` | wait 20 min → split *Morph Completed in the last 1 h → exit* → `first-morph-failure` (transactional) |
| Zero credits | `Credits Exhausted`, trigger filter *plan equals free*; flow filter *has not Purchase Completed since starting* | 0 h `credits-at-zero` (the +48 h social-proof and +7 d steps of Appendix C §4 are not authored yet) |
| Day-7 | `Signed Up` | wait 7 d → split *morphs_total is not set or 0* → `day-7-nudge`; *≥ 1 and plan = free* → the paid-features step (not authored yet); paying → exit |
| Win-back | segment `Dormant 30d`, flow filter *no Refund Issued* | 0 h `win-back-day-30` (the +5 d final step is not authored yet) |
| Purchase | `Purchase Completed` | 0 h `purchase-thank-you` (transactional; the same template on both sides of the *is_renewal* split; the +3 d workflow and +14 d NPS steps are not authored yet) |

Lifecycle flows mail every account that triggers them (an unsubscribe removes the profile
from all marketing flows); only campaigns are limited to `Tonamorph newsletter` and the
waitlist.

## 5. Launch-week campaign

`create_campaign` with `audiences.included` = the ids of `Tonamorph waitlist` and
`Tonamorph newsletter` (`excluded` = the `Paying` segment once it exists), one
`campaign-messages` entry `{"channel": "email", "content": {"subject": …,
"preview_text": …, "from_email": "support@tonamorph.com", "from_label": "Tonamorph",
"reply_to_email": "support@tonamorph.com"}}` with the values from the manifest, then
`assign_template_to_campaign_message` (message id from the create result, template id of
`launch-week`), `get_campaign_recipient_estimation`, and `send_campaign` only with the
founder's explicit confirmation. Launch-day send: 15:00 UTC (US morning, GTM §3.4).

## 6. Check

```sh
python3 growth/email/build.py --check         # summary table; exit 1 on any problem
cd growth && python3 -m pytest -q -p no:cacheprovider tests/test_email_templates.py
```

The checker validates tag balance (`html.parser`), every `{{ }}` / `{% %}` token against
the allow-list derived from the manifest, the unsubscribe rule, the transactional rule, the
UTM rule, subject and preview text, that the `.txt` twin links to the same URLs and carries
no HTML, and the product-name literal. It also cross-checks the manifest's metric names
against `backend/app/services/klaviyo.py` when the backend is in the checkout. `growth/email`
is deliberately not a Python package: with `pythonpath = ["."]` an `email/__init__.py`
would shadow the standard library's `email` module, so the test loads `build.py` by path.

After any copy change: run the check, `update_email_template`, `render_email_template`,
a preview send, and keep the `.html` and `.txt` in step.

## 7. Known gaps

* **Win-back's "2 morphs".** No backend path grants a win-back bonus (`Gift Granted` is the
  week-1 gift only). Before the Win-back flow goes live either grant the credits from the
  admin path for the `Dormant 30d` segment on a schedule (GTM §3.4, monthly code rotation)
  or change that sentence in `win-back-day-30`.
* **List membership.** `Signed Up` upserts the profile but nothing adds it to `Tonamorph
  users` / `Tonamorph newsletter`; a Klaviyo flow "Signed Up → add to list (newsletter only
  if `marketing_opt_in` is true)" or `add_profiles_to_list` from the backend closes it.
* **Referral share link.** Appendix C §4 wants the first-morph mail to carry the user's own
  `tonamorph.com/m/<code>` link; the profile does not carry the user's own code (only the
  code they signed up with), so the share button stays in the plugin and the portal.
* **Checkout URLs** are `null` until the payment provider's variant ids are configured
  (`backend/app/checks.py`); the fallback in `credits-at-zero` covers it.

## Klaviyo ids

Fill in as objects are created; the assistant reads this table before any update.

| object | id |
|---|---|
| list `Tonamorph users` | |
| list `Tonamorph newsletter` | |
| list `Tonamorph waitlist` | |
| template `welcome-0h` | |
| template `welcome-2d` | |
| template `welcome-5d` | |
| template `first-morph-success` | |
| template `first-morph-failure` | |
| template `credits-at-zero` | |
| template `day-7-nudge` | |
| template `win-back-day-30` | |
| template `purchase-thank-you` | |
| template `launch-week` | |
