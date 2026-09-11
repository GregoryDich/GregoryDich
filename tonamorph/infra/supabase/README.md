# Supabase Auth: e-mail templates, URLs, SMTP and rate limits

Everything the dashboard needs so that the e-mails GoTrue sends land on the website and
actually get delivered. `config.md` covers the rest of the project (storage bucket, JWT
settings, `pg_cron` + `cleanup.sql`); `db/apply.sh` applies the migrations.

## 1. E-mail templates — Authentication → Emails

`email-templates/` holds one `.html` per GoTrue message. For each row: open the tab in
the dashboard, replace **Subject** with the value below, switch the body editor to source
view, select everything and paste the whole file over it, save.

| dashboard tab | file | Subject |
|---|---|---|
| Confirm sign up | `confirm-signup.html` | `Confirm your Tonamorph account` |
| Invite user | `invite.html` | `You're invited to Tonamorph` |
| Magic Link | `magic-link.html` | `Your Tonamorph sign-in link` |
| Change Email Address | `email-change.html` | `Confirm your new Tonamorph email` |
| Reset Password | `recovery.html` | `Reset your Tonamorph password` |

Leave the **Reauthentication** tab as it is: it carries a six-digit code, not a link, and
the website does not use it.

What the files are:

* **Table-based HTML with inline styles** — renders in Gmail, Outlook (desktop and web),
  Apple Mail and the iOS/Android clients. Dark mode is handled twice: `prefers-color-scheme`
  for Apple Mail and the mobile clients, `[data-ogsc]` for Outlook.com; Gmail inverts the
  neutral palette on its own. The button is a table cell with `bgcolor`, and the raw link
  is repeated as text under it for clients that strip buttons.
* **One link form everywhere.** Each button points at
  `{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=<type>`, with the type
  hard-coded per file: `signup`, `invite`, `magiclink`, `email_change`, `recovery`. The
  website's `/auth/confirm` route calls `verifyOtp` with that pair and continues to
  `/account?welcome=1` (signup, invite, magic link), `/auth/reset-password` (recovery) or
  `/account?email=changed` (email change) — see `web/README.md`, "Email templates".
  `{{ .ConfirmationURL }}` is deliberately not used: it detours through Supabase's
  redirect, and mail clients that pre-fetch links consume it before the user clicks.
* **Variables.** Only `.SiteURL`, `.TokenHash` and `.Email` appear (`.ConfirmationURL`
  is allowed but unused). Do not add `.NewEmail`, `.Token` or `.Data`; the "Change Email
  Address" copy is worded so that it needs neither address. With **Secure email change**
  on (`config.md` §2) both the old and the new address receive it and both must confirm.
* **The literal "Tonamorph".** These templates are the one place in the repository where
  the product name is written as a literal. Everywhere else it comes from
  `NEXT_PUBLIC_PRODUCT_NAME` (`web/README.md`), but GoTrue has no variable for it. If the
  name ever changes, edit the five `.html` files, the five `.txt` files and the subjects
  above together.
* **Plain-text versions.** Each template has a `.txt` sibling with the same copy and the
  same link. Supabase's dashboard has no plain-text field — GoTrue sends the HTML body
  only — so the `.txt` files are for review, for a text-only client test, and for any
  later mailer that takes a separate text part. Keep the two in step.
* **"The link expires in 1 hour"** is the dashboard default (Authentication → Sessions →
  *Email OTP Expiration* = `3600` s). If you change that setting, change the sentence in
  every template.
* **Invite** is only for hand-picked beta testers (Authentication → Users → *Invite
  user*). The invited person lands on the site signed in and sets a password through
  "Forgot password".

Before pasting an edited template, check that the tags still balance and that no other
variable has crept in:

```sh
grep -ho '{{[^}]*}}' infra/supabase/email-templates/* | sort | uniq -c
#   only {{ .Email }}, {{ .SiteURL }} and {{ .TokenHash }} may be listed
python3 -c 'import html.parser,sys,glob
class P(html.parser.HTMLParser):
    void={"meta","br","img","hr","link"}; stack=[]
    def handle_starttag(s,t,a): t in s.void or s.stack.append(t)
    def handle_endtag(s,t): assert t in s.void or s.stack.pop()==t, (t, s.getpos())
for f in glob.glob("infra/supabase/email-templates/*.html"):
    p=P(); p.feed(open(f).read()); assert not p.stack, f
print("templates parse")'
```

## 2. URL configuration — Authentication → URL Configuration

| setting | value |
|---|---|
| Site URL | `https://<domain>` — the same value as `NEXT_PUBLIC_SITE_URL` (Vercel) and `AUTH_SITE_URL` (backend) |
| Redirect URLs | `https://<domain>/auth/confirm` |
| | `https://<domain>/auth/reset-password` |
| | `https://*-<vercel-project>.vercel.app/auth/confirm` (preview deployments) |
| | `http://localhost:3000/auth/confirm` and `http://localhost:3000/auth/reset-password` (local development) |

The templates link straight to the Site URL, so they need only the first value. The
two paths are what the API sends as `redirect_to` on sign-up, resend and recovery
(contract §1): a `redirect_to` that is not in the list is silently replaced by the Site
URL, and the link lands on the wrong page without any error.

## 3. SMTP — Project Settings → Authentication → SMTP Settings → Enable Custom SMTP

The built-in mailer sends from `noreply@mail.app.supabase.io` and is capped at a few
messages per hour for the whole project: enough for the first invite, not for a beta.

| field | Resend | Postmark |
|---|---|---|
| Sender email | `noreply@<domain>` | `noreply@<domain>` |
| Sender name | `Tonamorph` | `Tonamorph` |
| Host | `smtp.resend.com` | `smtp.postmarkapp.com` |
| Port | `465` (TLS; `587` for STARTTLS) | `587` (STARTTLS; `2525` if 587 is blocked) |
| Username | `resend` | the server's **Server API Token** |
| Password | the API key `re_…` (permission *Sending access*, restricted to `<domain>`) | the same Server API Token |
| Domain verification | Resend → Domains → Add `<domain>` → add the DKIM TXT (`resend._domainkey`) and the return-path MX + TXT (`send.<domain>`) in Vercel DNS → Verify | Postmark → Sender Signatures → Add domain → add the DKIM TXT and the Return-Path CNAME → Verify |

Postmark: the token is per *server* (Servers → the server → API Tokens), and SMTP uses the
`transactional` message stream by default — do not send these through a broadcast stream.
Both providers show a per-message log (Resend → Emails, Postmark → Activity); "Delivered"
there is the check that the credentials and the domain records are right.

## 4. Rate limits and related settings — Authentication → Rate Limits

| setting | value | why |
|---|---|---|
| Rate limit for sending emails | `30` per hour | shown only once custom SMTP is on; the default is a handful per hour |
| Minimum interval between emails | `60` s | one resend per address per minute; the site's "Resend" button stays usable |
| Rate limit for sign ups and sign ins | default `30` / 5 min per IP for the beta; raise it before launch | every plugin sign-in reaches GoTrue from the API server's single address (`docs/SECURITY.md` §6), so this limit is shared by all plugin users together |
| Rate limit for token refreshes, token verifications, anonymous users | defaults | the API keeps its own per-credential budgets (contract §1) |
| Sessions → Email OTP Expiration | `3600` s | matches "The link expires in 1 hour" in the templates |
| Attack Protection → Bot and Abuse Protection (CAPTCHA) | **off** | the plugin signs in through `POST /v1/auth/token` and cannot solve one |

## 5. Verify

1. Authentication → Users → *Invite user* with your second address: the message arrives
   from `noreply@<domain>`, looks right in dark mode, and the button's link host is
   `<domain>`.
2. Sign up on the preview site, follow the link: `/account?welcome=1` with 3 morphs.
3. "Forgot password" on the site: the recovery mail lands on `/auth/reset-password` and the
   new password signs in.
4. `python3 -m scripts.live_smoke` from `backend/` (`backend/scripts/README.md`) proves
   the rest of the account lifecycle against the live deployment; it creates its user
   already confirmed through the admin API, so it exercises everything except the mail
   path above.
