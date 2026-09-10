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
| `npm test`          | Vitest (legal loader, redirect guard, API error mapping) |
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
| `NEXT_PUBLIC_API_URL` | production | Backend base URL (`/v1/me`, `/v1/plans`, `/v1/jobs`, `/v1/api-keys`) |
| `NEXT_PUBLIC_PRODUCT_NAME` | production | Product name; defaults to the working name |
| `NEXT_PUBLIC_SUPPORT_EMAIL`, `NEXT_PUBLIC_PRIVACY_EMAIL`, `NEXT_PUBLIC_LEGAL_EMAIL` | production | Contact addresses (legal documents, footer, deletion requests) |
| `NEXT_PUBLIC_COMPANY_LEGAL_NAME`, `NEXT_PUBLIC_COMPANY_ADDRESS`, `NEXT_PUBLIC_COMPANY_REG_ID` | production | Legal entity details substituted into the legal documents |
| `NEXT_PUBLIC_MERCHANT_OF_RECORD` | no | Defaults to `Paddle` |
| `NEXT_PUBLIC_LEGAL_EFFECTIVE_DATE` | production | ISO date for `[[EFFECTIVE_DATE]]` / `[[EFFECTIVE_YEAR]]` |
| `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN` | for `/checkout` | Paddle.js client token; unset renders a "checkout not configured" page |
| `NEXT_PUBLIC_PADDLE_ENV` | no | `sandbox` or `production` (default) |
| `NEXT_PUBLIC_BILLING_PORTAL_URL` | no | Shows "Manage subscription" on `/account` |
| `NEXT_PUBLIC_KLAVIYO_COMPANY_ID` | no | Loads Klaviyo after marketing consent; also unlocks its CSP entries |
| `NEXT_PUBLIC_DOWNLOAD_BASE_URL` | no | Installer location; defaults to `/downloads` on this site |

Installer file names are derived: `<base>/<version>/<product-slug>-<version>-macos-universal.pkg`
and `…-windows-x64.exe`; versions come from `src/content/releases.ts`.

## Vercel

* Import the repository; set **Root Directory** to `snapplay-ai/web` and keep the
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
