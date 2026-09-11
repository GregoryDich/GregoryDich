# Cookie Policy

_Effective date: [[EFFECTIVE_DATE]]_

> **In short:** The [[PRODUCT_NAME]] website uses a handful of cookies. Strictly necessary ones keep you signed in and remember your cookie choices; they need no consent. Our web analytics ([Vercel Web Analytics](https://vercel.com/analytics)) are **cookieless** — they set nothing on your device. Marketing cookies from our email provider (Klaviyo) are set **only after you opt in**. The plugin and the API use no cookies at all. You can change your mind at any time through "Cookie settings" in the website footer.

## 1. Scope

1.1 This policy applies to the website at **[[WEBSITE_URL]]** and its subdomains, operated by [[COMPANY_LEGAL_NAME]], [[COMPANY_ADDRESS]].

1.2 The [[PRODUCT_NAME]] **plugin does not use cookies**. It keeps your session tokens and cached results in a settings folder on your computer, as described in the EULA (/legal/eula). The **API** uses no cookies; it is authenticated with a bearer token or an API key.

1.3 How we use personal data collected through cookies is described in the Privacy Policy (/legal/privacy).

## 2. What cookies are

Cookies are small text files a website stores in your browser. "First-party" cookies are set by our domain; "third-party" cookies are set by another company's domain through code on our pages. Similar technologies (local storage, session storage) store data in the browser without being sent automatically to a server; we mention them where we use them.

## 3. Categories we use

### 3.1 Strictly necessary

Required for the website to work and to honour your choices. They are set without consent because the site cannot function without them (ePrivacy Directive Art. 5(3) exemption).

- **Authentication session.** When you sign in, our authentication provider's library (`@supabase/ssr`) stores your session in first-party cookies named `sb-<project-ref>-auth-token`. Because a session can exceed the size of a single cookie, it is split into numbered chunks: `sb-<project-ref>-auth-token.0`, `sb-<project-ref>-auth-token.1`, and so on. `<project-ref>` is the identifier of our authentication project. During a magic-link sign-in a short-lived cookie `sb-<project-ref>-auth-token-code-verifier` holds the PKCE code verifier and is removed when sign-in completes.
- **Cookie consent.** A first-party cookie `cookie-consent` records which categories you accepted or rejected so that we do not ask again and do not load anything you declined.

### 3.2 Functional

Remember choices that improve your experience but are not essential.

- **Referral attribution.** If you arrive through a referral link (`?ref=…`) or a campaign link, a first-party cookie `ref` stores the code so that the person who referred you gets credit when you sign up. Without it the referral is lost, so we treat it as functional; it contains no personal data.
<!-- LAWYER-REVIEW: Confirm whether the `ref` referral cookie can be treated as consent-exempt (it serves the visitor's own interest in the referral reward but is not strictly necessary to deliver a service they requested) or must sit behind the functional consent toggle under ePrivacy Art. 5(3) and the CNIL/ICO guidance. -->

We may also keep display preferences (for example a dark/light theme) in your browser's local storage. This data is never sent to our servers.

### 3.3 Analytics — cookieless

We use **Vercel Web Analytics** to count page views and referrers. It **does not set cookies** and does not store anything on your device. It derives a short-lived visitor hash from your request that is discarded within 24 hours and cannot be used to track you across sites. Because nothing is stored on your device, no consent banner choice is required for it; you can still object to this processing at [[PRIVACY_EMAIL]].
<!-- LAWYER-REVIEW: Confirm that cookieless Vercel Web Analytics (server-side visitor hash, no client storage) falls outside ePrivacy Art. 5(3) consent and is covered by legitimate interests under the GDPR in each target EU member state, or whether the more conservative approach of gating it behind the "analytics" consent toggle should be taken (the toggle exists in the banner either way). -->

### 3.4 Marketing — only after you opt in

If you accept marketing cookies, or sign up to our newsletter, we load **Klaviyo**'s onsite script, which sets a first-party cookie (`__kla_id`) to recognise your browser, connect your visits with your email subscription and measure whether our emails and sign-up forms work. If you do not opt in, the script is never loaded and no Klaviyo cookie is set.

We do not use advertising networks, social-media pixels or cross-site tracking cookies on the website.
<!-- LAWYER-REVIEW: The GROWTH plan mentions retargeting pixels (Meta, TikTok, Google) for a later phase; they are deliberately absent from this policy. If they are added, this section, the banner categories and the Privacy Policy s.11 "no sharing" statement must all be updated first. -->

## 4. Table of cookies

| Name | Set by | Category | Purpose | Duration |
|---|---|---|---|---|
| `sb-<project-ref>-auth-token` (and `.0`, `.1`, … chunks) | Our authentication provider (Supabase), first-party | Strictly necessary | Keeps you signed in; carries your session tokens | Session, refreshed while you use the site; expires with the refresh token (default 1 year of inactivity) |
| `sb-<project-ref>-auth-token-code-verifier` | Our authentication provider (Supabase), first-party | Strictly necessary | Completes a magic-link sign-in securely (PKCE) | Removed when sign-in completes; at most a few minutes |
| `cookie-consent` | Us, first-party | Strictly necessary | Stores your consent choices | 12 months |
| `ref` | Us, first-party | Functional | Referral attribution for the account you create | 30 days |
| _(none)_ | Vercel Web Analytics | Analytics | Cookieless page-view counting | No cookie; visitor hash discarded within 24 hours |
| `__kla_id` | Klaviyo, first-party (set by its script) | Marketing | Recognises your browser for email marketing and form tracking | Up to 2 years |
<!-- LAWYER-REVIEW: Have the web team confirm the final cookie names and lifetimes against the deployed site (Supabase auth cookie lifetime follows the project's refresh-token setting; Klaviyo's cookie lifetime should be checked in the Klaviyo account) before publication, and keep this table as the single source of truth for the consent banner. -->

## 5. Consent and how to withdraw it

5.1 On your first visit from a country where consent is required (the EU/EEA, the UK, Switzerland and others), the site shows a banner. Nothing other than strictly necessary cookies is loaded until you make a choice. "Reject all" is as easy as "Accept all", and you can accept or reject each category separately.

5.2 You can change or withdraw your choice at any time by clicking **"Cookie settings"** in the website footer. Withdrawing consent stops future setting of that category; already-set cookies are deleted when possible, and otherwise expire.

5.3 If your browser sends a **Global Privacy Control** signal, we treat it as a rejection of marketing cookies.

5.4 You can also delete or block cookies in your browser settings. Blocking strictly necessary cookies will prevent you from signing in to the website.
<!-- LAWYER-REVIEW: Confirm that the banner design (equal-prominence reject, per-category toggles, no pre-ticked boxes, consent logged with timestamp and policy version) satisfies the EDPB cookie-banner taskforce guidance and the UK ICO's 2024-2025 "reject all" position; the consent record retention (recommended: as long as the consent is relied on, plus a limitation period) should be stated in the Privacy Policy if the lawyer prefers. -->

## 6. Changes

We will update this policy when we add or remove cookies. The effective date at the top tells you when it last changed. Material changes are announced on the website before they take effect.

## 7. Contact

Questions about cookies: [[PRIVACY_EMAIL]] · [[COMPANY_LEGAL_NAME]], [[COMPANY_ADDRESS]] · [[WEBSITE_URL]]
