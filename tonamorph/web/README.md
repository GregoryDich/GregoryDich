# Website and account portal

Next.js 15 (App Router, TypeScript strict, Tailwind CSS 4) with Supabase Auth cookie sessions
(`@supabase/ssr`) and a typed client for the backend described in `../docs/API_CONTRACT.md`.
Deployed on Vercel.

Everything product-facing (name, addresses, emails, merchant of record) comes from
`src/lib/brand.ts`, which reads the `NEXT_PUBLIC_*` variables below. No page or component
contains the product name as a literal.

## Run locally

```bash
cp .env.example .env.local        # fill in at least the Supabase URL and anon key
npm ci
npm run dev                       # http://localhost:3000
```

Requires Node 20.9 or newer. Without `NEXT_PUBLIC_API_URL` the site still runs: pricing shows
the static plan facts and `/account` explains that live data is unavailable.

## Scripts and CI

| script              | what it does                              |
|---------------------|-------------------------------------------|
| `npm run lint`      | ESLint (`next/core-web-vitals`, `next/typescript`, `react/no-danger`) |
| `npm run typecheck` | `tsc --noEmit`                            |
| `npm test`          | Vitest (legal loader, redirect guard, API error mapping, event tracking, speed wording, status parser) |
| `npm run build`     | `next build`                              |

CI should run, from this directory:

```bash
npm ci
npm run lint
npm run typecheck
npm test
NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co \
NEXT_PUBLIC_SUPABASE_ANON_KEY=anon \
NEXT_PUBLIC_SITE_URL=https://example.com \
npm run build
```

The build reads the legal documents from `../legal/*.md` and `../THIRD_PARTY_LICENSES.md`, so
the checkout must include the whole repository (see "Vercel" below). A document that is
missing is skipped with a warning; an unknown `[[PLACEHOLDER]]` fails the build.

## Environment variables

All variables are public (`NEXT_PUBLIC_*`) and inlined at build time — change one, redeploy.
Never add the Supabase service-role key or any other secret to this project.

| variable | required | purpose |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | yes | Supabase anon key |
| `NEXT_PUBLIC_SITE_URL` | yes | Canonical origin (metadata, sitemap, e-mail redirect targets) |
| `NEXT_PUBLIC_API_URL` | production | Backend base URL (`/v1/me`, `/v1/plans`, `/v1/jobs`, `/v1/api-keys`, `/v1/status`, `/v1/nps`) |
| `NEXT_PUBLIC_PRODUCT_NAME` | production | Product name; defaults to the working name |
| `NEXT_PUBLIC_SUPPORT_EMAIL`, `NEXT_PUBLIC_PRIVACY_EMAIL`, `NEXT_PUBLIC_LEGAL_EMAIL` | production | Contact addresses (legal documents, footer, deletion requests) |
| `NEXT_PUBLIC_COMPANY_LEGAL_NAME`, `NEXT_PUBLIC_COMPANY_ADDRESS`, `NEXT_PUBLIC_COMPANY_REG_ID` | production | Legal entity details substituted into the legal documents |
| `NEXT_PUBLIC_MERCHANT_OF_RECORD` | no | Defaults to `Paddle` |
| `NEXT_PUBLIC_LEGAL_EFFECTIVE_DATE` | production | ISO date for `[[EFFECTIVE_DATE]]` / `[[EFFECTIVE_YEAR]]` |
| `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN` | for `/checkout` | Paddle.js client token; unset renders a "checkout not configured" page |
| `NEXT_PUBLIC_PADDLE_ENV` | no | `sandbox` or `production` (default) |
| `NEXT_PUBLIC_BILLING_PORTAL_URL` | no | Shows "Manage subscription" on `/account` |
| `NEXT_PUBLIC_KLAVIYO_COMPANY_ID` | no | Loads Klaviyo after marketing consent; also unlocks its CSP entries |
| `NEXT_PUBLIC_SAMPLAB_PAGE` | no | `1` publishes `/samplab` (and lists it in the sitemap); anything else answers 404. Switch it on only after the founder has read samplab.com |
| `NEXT_PUBLIC_DOWNLOAD_BASE_URL` | no | Installer location; defaults to `/downloads` on this site |

Installer file names are derived: `<base>/<version>/<product-slug>-<version>-macos-universal.pkg`
and `…-windows-x64.exe`; versions come from `src/content/releases.ts`.

## Pages

| route | what it shows | data |
|---|---|---|
| `/` | Landing page in the final copy (hero, problem, how it works, speed, not-a-splitter, proof, free, FAQ) | `src/content/performance.ts` switches the speed headline: `MEASURED_P95_SECONDS` is `null` until the beta benchmark exists ("Playable in seconds, not minutes."), then the measured figure. `src/content/proof.ts` holds opted-in beta quotes; the section renders nothing while the list is empty — never add a quote the named person did not write |
| `/pricing` | "50 morphs for $9, once. 60 morphs a month for $7.99." plus the guarantee | `GET /v1/plans` with the static facts in `src/content/pricing.ts` as fallback. Credits are called morphs in copy only; the API keeps `credits` |
| `/status` | Component table, last-24-hour morphs / success / p50 / p95, incidents, scheduled maintenance, SLO targets | `GET /v1/status` (`{components:{api,engine,payments,website}, last_24h:{morphs,success_rate,p50_ms,p95_ms}}`), revalidated every 60 s; when the API is unreachable the page says so and still lists the components. Incidents and maintenance windows come from `src/content/incidents.ts` (empty by default), the targets from `src/content/slo.ts` |
| `/nps` | 0–10 picker prefilled from `?score=` in the e-mail link, optional comment | `POST /v1/nps {score, comment?}` as the signed-in user through a server action; signed-out visitors go to `/login?next=/nps?score=…`; a 409 (one answer per 30 days) shows "Thanks, you already answered recently." |
| `/roadmap` | Now / Next / Later | `src/content/roadmap.ts` |
| `/changelog` | Releases, newest first | `src/content/releases.ts` |
| `/samplab` | "Moving from Samplab? What carries over, what doesn't." — the only page allowed to mention the wind-down | 404 unless `NEXT_PUBLIC_SAMPLAB_PAGE=1` |

## Events

`src/lib/track.ts` wraps `track` from `@vercel/analytics` with a typed union of the web events
from `docs/GTM_PLAN.md` (appendix C §3). Only these events, with only these properties, can be
emitted; none of them carries an e-mail, user id, IP or free text (the NPS comment is sent to
the API, never to analytics). Events are dropped when the visitor has rejected the analytics
cookie category, when the page renders on the server, and when the `Analytics` component is
not mounted.

| event | properties | fired from |
|---|---|---|
| `cta_clicked` | `cta`, `location` (`header`, `hero`, `free`, `pricing`, `download`, `samplab`, `footer`) | `AttributedLink` with `cta`/`location`, `TrackedLink` |
| `signup_started` | — | `/signup` form mounted |
| `signup_completed` | `source: "web"` | `/signup` after `supabase.auth.signUp` succeeds (the backend sends the full event to Klaviyo) |
| `plugin_downloaded` | `os: "macos" \| "windows"` | `/download` buttons |
| `demo_play` | — | "Watch the 60 s demo" on the landing page |
| `pricing_view` | — | `/pricing` mounted |
| `checkout_started` | `plan_id`, `ref?` | `/checkout` once the Paddle overlay is requested |
| `nps_submitted` | `score` | `/nps` after the API accepted the answer |

**Custom events need Vercel Pro.** On the Hobby plan Vercel Web Analytics records page views
only; `track()` calls are accepted by the script and discarded, so the funnel metrics in the
GTM plan (`demo_play`, `pricing_view` → `signup_started`, …) exist only once the project is on
Pro. Nothing else on the site depends on them.

## Vercel

* Import the repository; set **Root Directory** to `tonamorph/web` and keep the
  **Next.js** framework preset. Leave "Include source files outside of the Root Directory in
  the Build Step" enabled — the legal documents live one level up.
* Add the environment variables above (Production and Preview). Preview deployments should
  point `NEXT_PUBLIC_SITE_URL` at their own URL only if you also add that URL to Supabase's
  redirect allow-list; otherwise auth links from previews go to production.
* Custom domain: add it under the project's Domains, then set `NEXT_PUBLIC_SITE_URL` to
  `https://<domain>` and update the Supabase URLs below. Vercel Web Analytics is enabled from
  the project's Analytics tab; the `@vercel/analytics` component is already mounted.
* Security headers (CSP, `frame-ancestors 'none'`, nosniff, referrer and permissions policies,
  HSTS) are set in `next.config.ts`. The CSP allows the Supabase origin and the API origin in
  `connect-src`; Klaviyo and Paddle hosts are added only when their variables are set.

## Supabase Auth settings

Authentication → URL configuration:

* **Site URL**: `https://<domain>` (the value of `NEXT_PUBLIC_SITE_URL`).
* **Redirect URLs**: `https://<domain>/auth/confirm`, `https://<domain>/auth/reset-password`
  (add `http://localhost:3000/auth/confirm` and `http://localhost:3000/auth/reset-password`
  for local development).

Sign-up happens directly through `supabase-js` in the browser (not through the API's
`POST /v1/auth/signup`) because the referral code, UTM parameters, the marketing opt-in and the
terms-acceptance timestamp are stored as user metadata (`raw_user_meta_data`:
`referral_code`, `marketing_opt_in`, `terms_accepted_at`, `utm_*`). Password reset requests
and confirmation resends also go through `supabase-js`; the new password is set with
`supabase.auth.updateUser`. Signing out clears the cookie session (`POST /auth/signout`).

### Email templates

`/auth/confirm` accepts both link styles, so the default templates work. The recommended
templates send the token hash straight to the site (no intermediate redirect through
Supabase, works in email clients that pre-fetch links). GoTrue cannot emit the type itself,
so each template hard-codes it.

**Confirm signup** (Authentication → Email Templates → Confirm signup):

```html
<h2>Confirm your email</h2>
<p>Follow this link to confirm your account:</p>
<p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=signup">Confirm my email</a></p>
```

**Reset password**:

```html
<h2>Reset your password</h2>
<p>Follow this link to choose a new password:</p>
<p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=recovery">Reset password</a></p>
```

**Change email address** (both the old- and new-address templates):

```html
<p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email_change">Confirm the new address</a></p>
```

**Magic link** (if enabled):

```html
<p><a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=magiclink">Log in</a></p>
```

Routing after confirmation: `signup` / `email` / `magiclink` → `/account?welcome=1`,
`recovery` → `/auth/reset-password`, `email_change` → `/account?email=changed`. With the
default `{{ .ConfirmationURL }}` templates the site receives `?code=` (PKCE) and exchanges
it; links generated without PKCE (accounts created from inside the plugin through the API)
arrive with the session in the URL fragment, which the login page consumes and then
continues to the account.

## How the pieces fit

* `src/middleware.ts` refreshes the Supabase session cookie on every request and sends
  anonymous visitors from `/account` to `/login?next=/account`.
* `src/middleware.ts` also sends anonymous visitors from `/nps` to `/login?next=/nps?score=…`,
  so the score from the e-mail link survives the sign-in.
* `src/lib/api.ts` is the only place that talks to the backend. It runs on the server
  (server components and server actions), sends the Supabase access token as the Bearer
  token, and maps the contract's error envelope to `ApiError`. Nothing logs tokens.
* `/pricing` fetches `GET /v1/plans` at request time (anonymous responses are cached for
  five minutes) and falls back to the static facts in `src/content/pricing.ts`.
* `/checkout` is Paddle's default payment link: it validates `price` (`pri_…`), `user_id`
  (UUID), `plan_id` and `ref`, then opens the overlay checkout with those values as
  `customData` and `/account?purchase=success` as the success URL.
* `/legal/<slug>` pages are built statically from `../legal/*.md` (`terms`, `privacy`,
  `refunds`, `copyright`, `cookies`, `eula`) and `../THIRD_PARTY_LICENSES.md`
  (`third-party`), with HTML comments stripped and `[[TOKENS]]` substituted from `brand`.
* Cookie consent lives in the `cookie-consent` cookie (12 months) with the categories
  named in the cookie policy. Functional consent enables the 30-day `ref` cookie; marketing
  consent loads Klaviyo; the analytics toggle controls the (cookieless) Vercel Web
  Analytics component. A Global Privacy Control signal keeps marketing off until the
  visitor chooses otherwise, and "Cookie settings" in the footer reopens the banner.
* Attribution (`?ref=`, `utm_*`) is carried through the landing page's calls to action in
  the URL, so it survives without storage; it is persisted only after functional consent.
* Demo media: drop `demo.webm`, `demo.mp4` and `demo-poster.jpg` into `public/media/`; the
  landing page shows an illustration until they exist.
