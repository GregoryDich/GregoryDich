# Legal pack — README for the people who finish it

_Effective date: [[EFFECTIVE_DATE]]_

> **In short:** This folder holds the six customer-facing legal documents for [[PRODUCT_NAME]], written to be finished by a lawyer in about an hour. Every fact in them (prices, credit rules, retention periods, sub-processors, limits) was taken from the product documentation and the code in this repository, not invented. Fill the double-square-bracket placeholders, work through the lawyer checklist below, then publish in the order in section 6. The website renders these files verbatim.

## 1. What is in this folder

| File | Site path | Governs | Also needed by |
|---|---|---|---|
| `terms-of-service.md` | `/legal/terms` | The account, the cloud service, credits, subscriptions, referrals, liability | Checkout (link + acceptance), sign-up, merchant-of-record onboarding |
| `privacy-policy.md` | `/legal/privacy` | Personal data: controller, legal bases, retention, sub-processors, transfers, rights; Israel PPL notice, UK GDPR, CCPA | Sign-up, merchant-of-record onboarding, app-store and platform-API reviews, cookie banner |
| `refund-policy.md` | `/legal/refunds` | Withdrawal rights, voluntary refunds, subscriptions, chargebacks | Checkout (withdrawal-waiver checkbox), merchant-of-record refund configuration |
| `copyright-policy.md` | `/legal/copyright` | Rights in uploaded audio, DMCA-style notice and counter-notice, repeat infringers | DMCA agent registration, support runbook |
| `cookie-policy.md` | `/legal/cookies` | Website cookies, consent mechanism | Cookie banner implementation |
| `eula.md` | `/legal/eula` | The installed plugin: licence, restrictions, what it transmits, warranty, liability | Installer (accept step), plugin About screen |
| `../LICENSE` | — | Proprietary notice for the repository | — |
| `../THIRD_PARTY_LICENSES.md` | `/legal/third-party` | Every third-party component, its licence and obligations; the pre-launch action list (two blockers) is internal, in `../docs/LICENCE_ACTIONS.md` | Installer bundle, plugin About screen, website |

## 2. How the website renders these files

- The site renders each Markdown file **verbatim** (GitHub-flavoured Markdown; tables allowed; no HTML other than comments).
- **HTML comments are stripped** at build time. That is where the `<!-- LAWYER-REVIEW: … -->` markers live, so they never reach the public page — but they must be resolved (edited or deleted) before publication anyway; see section 4.
- **Double-square-bracket placeholders (the tokens in section 3) are substituted at build time** from the site configuration. The build fails on any token outside the allowed set in section 3, so do not introduce new ones.
- Each document begins with a level-1 heading, then `_Effective date: [[EFFECTIVE_DATE]]_`, then a blockquote — the plain-language summary the site shows first — then numbered sections. Keep that shape when editing.
- Documents reference each other only by site path (`/legal/terms`, `/legal/privacy`, `/legal/refunds`, `/legal/copyright`, `/legal/cookies`, `/legal/eula`, `/legal/third-party`).
- The product name is never written literally anywhere in these files; always `[[PRODUCT_NAME]]`. The product is being renamed and the build substitutes the final name.

## 3. Placeholders

Only these eleven tokens exist. Fill them in the site configuration (one place), not in the files.

| Token | Meaning | How to fill it |
|---|---|---|
| `[[PRODUCT_NAME]]` | The public product name | The final trade name as it will appear on the website and in the plugin |
| `[[COMPANY_LEGAL_NAME]]` | The legal person that contracts with users | For a sole proprietor ("osek murshe"): the proprietor's full legal name, optionally followed by the trading name — the lawyer decides the form (Terms s.1.1) |
| `[[COMPANY_ADDRESS]]` | Registered business address | Full postal address in Israel; appears as the notice address in every document and as the DMCA agent address |
| `[[COMPANY_REG_ID]]` | Registration number | The osek murshe number (ע.מ. / VAT dealer number) |
| `[[WEBSITE_URL]]` | Canonical website origin | `https://…` without a trailing slash; the documents append `/legal/…` paths to it |
| `[[SUPPORT_EMAIL]]` | Customer support mailbox | Monitored daily; receives refund and withdrawal requests |
| `[[PRIVACY_EMAIL]]` | Privacy / data-subject-request mailbox | May be the same mailbox as support, but must be stated separately; one-month response clock starts on receipt |
| `[[LEGAL_EMAIL]]` | Legal notices and copyright notices | Receives DMCA notices and counter-notices; should be the address registered with the US Copyright Office if that route is taken |
| `[[MERCHANT_OF_RECORD]]` | The merchant of record's legal name | "Paddle.com Market Ltd" or "Lemon Squeezy, LLC" (as it appears on the customer receipt) — the choice is still open in the product plan |
| `[[EFFECTIVE_DATE]]` | Date the documents take effect | One date for the whole pack on first publication, e.g. `1 October 2026`; later versions may diverge per document |
| `[[EFFECTIVE_YEAR]]` | Copyright year | Used only in `../LICENSE`; the year of first publication (extend to a range on later years) |

## 4. Lawyer checklist — every `LAWYER-REVIEW` marker

Each marker is an HTML comment on its own line in the source, placed directly under the clause it questions. Resolve each one by editing the clause and deleting the comment. The list below is generated from the files; regenerate it with the command in section 7 after editing.

| # | File | Line | Question for the lawyer |
|---|---|---|---|
| 1 | `terms-of-service.md` | 10 | Confirm the exact legal name, registration number ("osek murshe" / ע.מ.) and address of the proprietor, and whether the trading name needs to be stated separately from the personal legal name. |
| 2 | `terms-of-service.md` | 23 | Confirm the 16-year minimum is acceptable for every target market (GDPR Art. 8 allows 13-16 by member state; Israel's Legal Capacity and Guardianship Law treats under-18s as minors) and whether a separate parental-consent flow is needed at checkout rather than a statement in the Terms. |
| 3 | `terms-of-service.md` | 74 | Check the automatic-renewal disclosures and cancellation mechanism against California's Automatic Renewal Law and similar US state laws, the EU "withdrawal button" requirement for online contracts (Directive (EU) 2023/2673, applicable from 19 June 2026) and the Israeli Consumer Protection Law rules on continuing transactions ("עסקה מתמשכת"), including any required pre-renewal reminder emails. |
| 4 | `terms-of-service.md` | 91 | Confirm that the assignment/disclaimer of rights in AI-generated Output is drafted in a way that works under Israeli copyright law and does not undermine the position that the Output is the user's own work (or, where no copyright subsists, that nothing is being warranted). |
| 5 | `terms-of-service.md` | 132 | The implemented affiliate system pays a 30% recurring commission on net revenue while the product brief describes credit rewards to both parties. Confirm which programme(s) launch, whether affiliates need a separate written agreement (recommended, including tax/withholding and self-billing terms) and whether commissions to Israeli residents raise withholding-tax issues. |
| 6 | `terms-of-service.md` | 161 | Confirm the discontinuation refund commitment (unused pack credits bought in the last 12 months, pro rata) is what the business wants; a broader or narrower window is a commercial choice, but under EU/UK consumer law some refund on discontinuation is expected in any case. |
| 7 | `terms-of-service.md` | 182 | Confirm the 12-month-spend cap with a US$ 50 floor is enforceable against consumers in the EU (Unfair Contract Terms Directive), the UK (Consumer Rights Act 2015) and Israel (Standard Contracts Law 5743-1982, which lets courts void one-sided limitation clauses in standard-form contracts), and whether a different or no cap is advisable for consumers. |
| 8 | `terms-of-service.md` | 191 | Consumer indemnities are frequently held unenforceable in the EU/UK; confirm whether to keep the narrowed consumer indemnity or delete it for consumers entirely. |
| 9 | `terms-of-service.md` | 208 | Confirm the unilateral-variation clause (14 days' notice, deemed acceptance by continued use, exit refund) meets the transparency and "valid reason" requirements of the EU Unfair Contract Terms Directive and UK CMA guidance, and consider whether price changes need a separate express opt-in for subscribers. |
| 10 | `terms-of-service.md` | 215 | Confirm that the Israeli law/Tel Aviv venue clause with a mandatory-law carve-out is workable under Rome I Art. 6 and Brussels I recast Arts. 17-19 for EU consumers, the UK equivalents, and that the clause is presented in a way that survives Israel's Standard Contracts Law review; consider whether to add a plain-language statement that EU/UK consumers keep their local court. |
| 11 | `privacy-policy.md` | 14 | Confirm (a) no DPO is required under GDPR Art. 37 / UK GDPR, (b) whether an EU representative (GDPR Art. 27) and a UK representative (UK GDPR Art. 27) must be appointed given that we are established outside the EU/UK and offer services to EU/UK consumers, and (c) whether a Privacy Protection Officer is required under Amendment 13 to the Israeli Protection of Privacy Law. |
| 12 | `privacy-policy.md` | 73 | Confirm the 7-year retention for transaction records against the Israeli Income Tax (Bookkeeping) Regulations and VAT record-keeping rules for a sole proprietor, and whether any shorter period applies to the credit ledger entries that are not themselves invoices. |
| 13 | `privacy-policy.md` | 93 | Fill in the actual Supabase project region (EU-Frankfurt vs US), the AWS region(s) and whether Cloudflare R2 or CloudFront are used in production, and check that each US provider is either certified under the EU-US Data Privacy Framework / UK Extension or has signed SCCs with us; Modal Labs and RunPod in particular should be verified. |
| 14 | `privacy-policy.md` | 108 | Confirm the Israeli outbound-transfer basis for each US provider under the 2001 Transfer Regulations (Reg. 2 conditions) and whether Amendment 13 changed anything for transfers to processors outside Israel. |
| 15 | `privacy-policy.md` | 133 | Determine whether the database must be registered with, or notified to, the Registrar of Databases under Amendment 13's narrowed registration duty (number of data subjects, sensitive data, purpose of transfer to others), confirm the required security level under the Protection of Privacy (Data Security) Regulations 5777-2017 and the resulting incident-reporting duty, and confirm the section-11 wording meets the Authority's guidance. |
| 16 | `privacy-policy.md` | 152 | Confirm whether the business meets any CCPA applicability threshold (US$ 25M+ revenue, 100,000+ consumers/households, or 50%+ revenue from selling/sharing); if it does not, decide whether to keep this section as a voluntary commitment (recommended) or remove it. |
| 17 | `refund-policy.md` | 24 | Confirm whether prepaid credits are "digital content not supplied on a tangible medium" (withdrawal right lost on express consent + acknowledgement, CRD Art. 16(m) / UK CCR reg. 37) or a "digital service" (withdrawal right survives but the consumer pays a proportionate amount for credits used, CRD Art. 14(3)); the checkout wording and the text of 3.2 depend on the answer. |
| 18 | `refund-policy.md` | 27 | Confirm the basis for the proportionate deduction on first-month subscription withdrawal (credits used × subscription price per credit) matches CRD Art. 14(3) / UK CCR reg. 36 (proportion of the total price for the period), and that it is disclosed at checkout as required. |
| 19 | `refund-policy.md` | 32 | From 19 June 2026 EU online contracts must offer a "withdrawal button" (Directive (EU) 2023/2673); confirm whether the merchant of record's portal satisfies this or whether the website must add its own, and whether the Israeli Consumer Protection Law s.14C remote-sale cancellation right (14 days, with the exception for goods/services that can be copied) applies to Israeli buyers in addition. |
| 20 | `refund-policy.md` | 67 | Under the EU Digital Content Directive (2019/770) and UK CRA 2015 the consumer's conformity remedies (repair, price reduction, termination) cannot be excluded; confirm 6.3's line between "imperfect AI output" and "non-conforming digital content" is defensible and consistent with the objective conformity requirements. |
| 21 | `refund-policy.md` | 88 | Check that the merchant of record's own consumer refund terms are consistent with this policy (in particular the 14-day full refund for unused packs and the first-month subscription withdrawal), and who is the correct addressee of statutory withdrawal notices — the MoR as seller of record, or us. |
| 22 | `copyright-policy.md` | 12 | Israel's Copyright Law 5768-2007 has no statutory hosting safe harbour equivalent to DMCA §512; confirm the intended position (voluntary DMCA-style procedure plus Israeli case-law "notice and takedown" practice) and whether registering a DMCA agent with the US Copyright Office (required for §512 safe harbour) is worthwhile given the 24-hour deletion of content. |
| 23 | `copyright-policy.md` | 37 | Decide whether to register this agent in the US Copyright Office DMCA Designated Agent Directory (US$ 6, renewable every three years) and insert the exact name/phone required by 37 C.F.R. § 201.38; a sole proprietor may name themselves. |
| 24 | `copyright-policy.md` | 61 | Forwarding the complainant's name and contact details to the user is standard DMCA practice but is a disclosure of personal data under the GDPR/UK GDPR and the Israeli PPL; confirm the legal basis (legitimate interests / legal claims) and whether the Privacy Policy should mention it expressly. |
| 25 | `copyright-policy.md` | 77 | The §512(g) counter-notice consent to US federal jurisdiction is required for US safe-harbour purposes but may be awkward for a non-US operator and non-US users; confirm whether to keep it verbatim, and whether an EU DSA Art. 20 internal complaint-handling statement should be added or whether the business is below the DSA's applicability thresholds for that obligation. |
| 26 | `copyright-policy.md` | 82 | Confirm the repeat-infringer threshold (two valid, un-rebutted notices in 12 months) and the discretionary language are consistent with US case law on "reasonably implemented" §512(i) policies and with the account-termination provisions in the Terms of Service s.18. |
| 27 | `cookie-policy.md` | 33 | Confirm whether the `ref` referral cookie can be treated as consent-exempt (it serves the visitor's own interest in the referral reward but is not strictly necessary to deliver a service they requested) or must sit behind the functional consent toggle under ePrivacy Art. 5(3) and the CNIL/ICO guidance. |
| 28 | `cookie-policy.md` | 40 | Confirm that cookieless Vercel Web Analytics (server-side visitor hash, no client storage) falls outside ePrivacy Art. 5(3) consent and is covered by legitimate interests under the GDPR in each target EU member state, or whether the more conservative approach of gating it behind the "analytics" consent toggle should be taken (the toggle exists in the banner either way). |
| 29 | `cookie-policy.md` | 47 | The GROWTH plan mentions retargeting pixels (Meta, TikTok, Google) for a later phase; they are deliberately absent from this policy. If they are added, this section, the banner categories and the Privacy Policy s.11 "no sharing" statement must all be updated first. |
| 30 | `cookie-policy.md` | 59 | Have the web team confirm the final cookie names and lifetimes against the deployed site (Supabase auth cookie lifetime follows the project's refresh-token setting; Klaviyo's cookie lifetime should be checked in the Klaviyo account) before publication, and keep this table as the single source of truth for the consent banner. |
| 31 | `cookie-policy.md` | 70 | Confirm that the banner design (equal-prominence reject, per-category toggles, no pre-ticked boxes, consent logged with timestamp and policy version) satisfies the EDPB cookie-banner taskforce guidance and the UK ICO's 2024-2025 "reject all" position; the consent record retention (recommended: as long as the consent is relied on, plus a limitation period) should be stated in the Privacy Policy if the lawyer prefers. |
| 32 | `eula.md` | 20 | The three-computer limit is a contractual statement only — the current Software does not enforce machine activation. Confirm the number and whether "own or control" language is acceptable, or whether a per-seat definition for studios should be added. |
| 33 | `eula.md` | 37 | Confirm the reverse-engineering carve-out tracks Art. 6 of the EU Software Directive 2009/24/EC and s.50B UK CDPA 1988, and that the anti-circumvention clause does not overreach for Israeli consumers. |
| 34 | `eula.md` | 85 | Under the Digital Content Directive the trader must also supply updates necessary to keep the content in conformity for the period the consumer reasonably expects; confirm whether section 6 needs an express "security and conformity updates" commitment and a minimum support period. |
| 35 | `eula.md` | 94 | Same enforceability question as Terms of Service s.16 (Israeli Standard Contracts Law, EU UCTD, UK CRA); confirm a single shared cap across EULA and Terms is the intended structure. |
| 36 | `eula.md` | 99 | Confirm whether the Software (a JUCE plugin using TLS via the operating system's or libcurl's crypto) needs any Israeli DECA/export classification or US EAR self-classification (likely mass-market/5D992 or exempt), and whether the sanctions clause should list countries expressly. |
| 37 | `README.md` | 151 | Confirm that publishing all six documents with a single shared effective date is acceptable, and whether earlier beta users (if any) need a change notice under Terms s.19 rather than first-time acceptance. |

## 5. Facts the documents rely on (keep them consistent)

If any of these changes, change it everywhere it appears (grep for the number).

| Fact | Value | Appears in | Source |
|---|---|---|---|
| Free credits at sign-up | 3, once per account | terms, refunds, privacy | `docs/API_CONTRACT.md` §3 |
| Credit pack | 50 credits for US$ 9.00, never expire | terms, refunds | contract §3, §13 |
| Subscription | US$ 7.99/month, 60 credits per billing period, expire at period end, spent before pack credits | terms, refunds | contract §3, §13 |
| Cost per clip | 1 credit, reserved at submission, captured on success, released on failure | terms, refunds | contract §2, §6 |
| Upload limits | ≤ 10 MB; first 60 s processed, longer clips truncated | terms, privacy, eula | contract §2, `docs/SECURITY.md` §7 |
| Rate limits | 10 job submissions/min, 60 reads/min, 5 concurrent streams | terms | `docs/SECURITY.md` §6 |
| Deletion of uploads and outputs | 24 hours after upload (bucket lifecycle rule, signed URLs expire at the same time) | terms, privacy, refunds, copyright, eula | `docs/SECURITY.md` §5, §10; `infra/aws/modules/storage/main.tf` |
| Retained after deletion | job metadata and credit ledger; purchase records 7 years | privacy | `docs/SECURITY.md` §10; retention period is a lawyer question (marker) |
| Application log retention | 14 days | privacy | `infra/aws/modules/*/variables.tf` `log_retention_days` default |
| Model training on user audio | never | terms, privacy, copyright | product decision |
| Minimum age | 16 (18 / parental consent for purchases where required) | terms, privacy | product decision |
| Machines per licence | 3 | eula | product decision (not enforced in code) |
| Liability cap | amounts paid in the previous 12 months, US$ 50 floor; shared between Terms and EULA | terms, eula | product decision (marker) |
| Voluntary refund window | 14 days, unused pack only; subscription: no refund for current period | refunds, terms | product decision |
| Discontinuation refund | unused pack credits bought in the last 12 months, pro rata | terms, refunds | product decision (marker) |
| Governing law / venue | Israel / Tel Aviv-Yafo, with mandatory consumer-law carve-out | terms, eula | product decision (marker) |
| Sub-processors | Supabase, AWS, Modal Labs, RunPod, Vercel, merchant of record, Klaviyo, Sentry (planned) | privacy | product decision; regions still to be filled (marker) |
| Auth cookies | `sb-<project-ref>-auth-token` (chunked `.0`, `.1`, …) | cookies | `@supabase/ssr` naming |
| Analytics | Vercel Web Analytics, cookieless | cookies, privacy | product decision |
| Crash reporting | opt-in only, off by default, Sentry planned | privacy, eula | product decision — the plugin has no crash reporter yet; the EULA describes the intended behaviour |

## 6. Publication order

1. **Fill the placeholders** in the site configuration and render a preview of all six pages. Check that no placeholder token survives and that no HTML comment is visible.
2. **Resolve the two licence blockers** in `../docs/LICENCE_ACTIONS.md` (Demucs weights; Rubber Band) — the Terms and EULA describe a product that cannot lawfully ship until they are closed.
3. **Lawyer pass** over the checklist in section 4, in this order: privacy → terms → refunds → eula → cookies → copyright. Delete each marker as it is resolved.
4. **Publish the Privacy Policy and Cookie Policy first.** They are required before any personal data is collected (sign-up, analytics), before the merchant-of-record application, and by the platform-API reviews the growth engine needs.
5. **Wire the checkout**: link to `/legal/terms` and `/legal/refunds`; add the express-consent-and-acknowledgement checkbox for immediate delivery (Refund Policy s.3.2) and the withdrawal function; configure the merchant of record's refund settings to match the Refund Policy.
6. **Publish the Terms of Service and Refund Policy** together, then require acceptance of the Terms at sign-up.
7. **Ship the EULA** in the installer's accept step and at `/legal/eula`, with `THIRD_PARTY_LICENSES.md` bundled and reachable from the plugin's About screen.
8. **Publish the Copyright Policy** and, if the lawyer agrees, register the designated agent with the US Copyright Office; set up the `[[LEGAL_EMAIL]]` runbook (acknowledge, take down, notify, counter-notice clock).
9. **Deploy the cookie banner** matching the Cookie Policy table exactly (equal-prominence reject, per-category toggles, consent log).
10. **Israel**: decide on database registration/notification under Amendment 13 and file if required; document the security level under the Data Security Regulations.
11. Record the effective date, keep the previous version of each document, and set a reminder to re-verify `THIRD_PARTY_LICENSES.md` after every dependency change.

## 7. Verification commands

Run from the repository root.

```
# Only the eleven allowed placeholder tokens may appear:
grep -rno "\[\[[A-Z_]*\]\]" legal LICENSE THIRD_PARTY_LICENSES.md | sed 's/.*://' | sort -u

# The old product name must not appear anywhere in the pack:
OLD_NAME="<the pre-rename product name, as in the repository folder name>"
grep -rn -i "$OLD_NAME" legal LICENSE THIRD_PARTY_LICENSES.md   # expect no output

# Every document has the effective-date line and at least one marker:
for f in legal/*.md; do printf '%s  date=%s  markers=%s\n' "$f" "$(grep -c '^_Effective date: \[\[EFFECTIVE_DATE\]\]_$' "$f")" "$(grep -c '^<!-- LAWYER-REVIEW: ' "$f")"; done

# Regenerate the checklist rows in section 4 (paste over the table):
grep -n "^<!-- LAWYER-REVIEW: " legal/*.md
```

<!-- LAWYER-REVIEW: Confirm that publishing all six documents with a single shared effective date is acceptable, and whether earlier beta users (if any) need a change notice under Terms s.19 rather than first-time acceptance. -->
