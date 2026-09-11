# Terms of Service

_Effective date: [[EFFECTIVE_DATE]]_

> **In short:** [[PRODUCT_NAME]] is a plugin plus a cloud service that turns a short audio clip you own into stems, MIDI and a playable instrument. You need an account and you must be at least 16. Each successfully processed clip costs one credit; you get 3 free, and you can buy a 50-credit pack for $9.00 (never expires) or subscribe for $7.99/month (60 credits per month, unused ones expire at the end of the month). Purchases are made through [[MERCHANT_OF_RECORD]], which is the seller of record. You keep every right to what you upload and to what we generate for you; we never train models on your audio, and we delete your audio and results from our servers after 24 hours. Only upload audio you have the rights to. Our liability to you is capped at what you paid us in the previous 12 months, except where the law does not allow that.

## 1. Who we are and what these Terms cover

1.1 These Terms of Service ("**Terms**") are a contract between you and [[COMPANY_LEGAL_NAME]], a sole proprietorship registered in Israel under number [[COMPANY_REG_ID]], with its place of business at [[COMPANY_ADDRESS]] ("**we**", "**us**", "**our**").
<!-- LAWYER-REVIEW: Confirm the exact legal name, registration number ("osek murshe" / ע.מ.) and address of the proprietor, and whether the trading name needs to be stated separately from the personal legal name. -->

1.2 They apply to the [[PRODUCT_NAME]] service: your account, the website at [[WEBSITE_URL]], the cloud processing service, the application programming interface ("**API**") and any credits, subscriptions and referral rewards (together, the "**Service**"). The downloadable plugin itself is licensed to you under the End-User Licence Agreement at /legal/eula (the "**EULA**"). If the EULA and these Terms conflict about the installed software, the EULA wins; for everything else, these Terms win.

1.3 The following documents are part of these Terms: the Privacy Policy (/legal/privacy), the Cookie Policy (/legal/cookies), the Refund Policy (/legal/refunds) and the Copyright Policy (/legal/copyright).

1.4 If you use the Service on behalf of a company or another person, you confirm that you have authority to bind them, and "you" means both you and them.

## 2. Eligibility and age

2.1 You must be at least **16 years old** to create an account or use the Service. The Service is not directed at children under 16, and we do not knowingly allow them to use it.

2.2 If you are under the age of majority where you live (18 in most places), you may buy credits or a subscription only with the consent of a parent or legal guardian, and the parent or guardian is responsible for your use.
<!-- LAWYER-REVIEW: Confirm the 16-year minimum is acceptable for every target market (GDPR Art. 8 allows 13-16 by member state; Israel's Legal Capacity and Guardianship Law treats under-18s as minors) and whether a separate parental-consent flow is needed at checkout rather than a statement in the Terms. -->

2.3 You may not use the Service if you are barred from doing so under applicable law, or if we have previously closed your account for breach of these Terms.

## 3. Your account

3.1 You need an account to use the Service. Sign-up requires an email address and a password. Passwords are handled by our authentication provider; we never see or store your password in plain text. See the Privacy Policy for how we handle your data.

3.2 Keep your password and any API keys secret. You are responsible for everything that happens under your account, whether or not you authorised it, until you tell us at [[SUPPORT_EMAIL]] that your credentials may have been compromised.

3.3 One person, one account. Creating multiple accounts to obtain additional free credits or referral rewards is a breach of these Terms, and we may void credits and close the accounts involved.

3.4 You must give us accurate information and keep it up to date. We may need to contact you about your account, and email to the address on file counts as notice to you.

## 4. What the Service does

4.1 You choose an audio clip in the plugin (or send one through the API). The plugin encodes it and uploads it to our servers, where an automated, AI-based pipeline separates it into up to four stems (bass, drums, other, vocals), transcribes MIDI, analyses tempo and key, and returns the results to the plugin, which turns them into a playable instrument.

4.2 Limits that apply to every clip: the upload may not exceed **10 MB**; only the **first 60 seconds** of audio are processed (longer clips are truncated and marked as such); supported container formats are listed in the plugin and on the website. We may change these limits with notice on the website.

4.3 Processing happens in the cloud. The plugin needs an internet connection and a signed-in account to process a clip. Results you have already received stay usable in the plugin from its local copy.

4.4 The Service uses machine-learning models. The output is an automated approximation of the stems, notes and musical analysis in your clip. It can contain artefacts, missed or wrong notes, and mis-detected tempo or key. We do not promise a particular quality or that any output is fit for a particular use. See section 15.

## 5. Credits

5.1 **One credit per clip.** Each clip you submit for processing costs **one credit**. The credit is reserved when the job is accepted and captured only when the job succeeds. If a job fails on our side, the reservation is released and you are not charged.

5.2 **Free credits.** Every new account receives **3 free credits** once. Free credits have no cash value and are not refundable.

5.3 **Credit pack ("pack_50").** 50 credits for **US$ 9.00** (plus any tax [[MERCHANT_OF_RECORD]] is required to add). Pack credits **never expire**.

5.4 **Subscription ("sub_monthly").** **US$ 7.99 per month** for **60 credits per billing period**. Subscription credits expire at the end of the billing period in which they were granted; they **do not roll over**. When you hold both subscription credits and pack credits, the **subscription (expiring) credits are spent first**.

5.5 Credits are personal to your account. They have no monetary value, cannot be transferred, sold, exchanged for cash or applied to another account, and are not refundable except as stated in the Refund Policy (/legal/refunds) or where the law requires a refund.

5.6 We may offer promotional or bonus credits (for example through the referral programme). They may carry their own conditions, including an expiry date, which we will tell you at the time.

5.7 We may change prices, pack sizes and subscription allowances for the future. A price change does not affect credits you have already bought, and a subscription price change takes effect only from your next renewal after we have given you at least 30 days' notice by email.

5.8 Your credit balance and history are shown in the plugin and in your account. Our ledger is the record of your credits; if you think it is wrong, tell us at [[SUPPORT_EMAIL]] and we will investigate.

## 6. Subscriptions

6.1 A subscription **renews automatically** each month at the then-current price until you cancel it. By subscribing you authorise [[MERCHANT_OF_RECORD]] to charge your payment method at each renewal.

6.2 **Cancelling.** You can cancel at any time through the customer portal of [[MERCHANT_OF_RECORD]] (the link is in your receipt email and in your account page), or by asking us at [[SUPPORT_EMAIL]]. Cancellation takes effect at the end of the current billing period. You keep your remaining subscription credits until then, after which any unused subscription credits expire. Pack credits are not affected by a cancellation.

6.3 We do not refund the current billing period when you cancel, except as set out in the Refund Policy or where the law requires it.

6.4 If a renewal payment fails, [[MERCHANT_OF_RECORD]] may retry it. If it cannot be collected, the subscription ends and no further subscription credits are granted.
<!-- LAWYER-REVIEW: Check the automatic-renewal disclosures and cancellation mechanism against California's Automatic Renewal Law and similar US state laws, the EU "withdrawal button" requirement for online contracts (Directive (EU) 2023/2673, applicable from 19 June 2026) and the Israeli Consumer Protection Law rules on continuing transactions ("עסקה מתמשכת"), including any required pre-renewal reminder emails. -->

## 7. Payments and the merchant of record

7.1 Credits and subscriptions are sold by **[[MERCHANT_OF_RECORD]]**, an independent merchant of record that acts as the seller of record, collects payment, calculates and remits VAT, GST and sales tax, issues invoices and handles refunds and chargebacks. Its own terms and privacy policy apply to the checkout and payment.

7.2 We never receive your card number or bank details.

7.3 We grant credits to your account when [[MERCHANT_OF_RECORD]] confirms your payment to us. This normally takes seconds, but can occasionally be delayed. If your credits have not arrived within an hour, contact [[SUPPORT_EMAIL]] with your order number.

7.4 Prices are shown in US dollars unless [[MERCHANT_OF_RECORD]] shows a local price at checkout. Any tax is added at checkout where required.

7.5 If a payment is reversed by a chargeback or a refund of a purchase, we may remove the corresponding credits from your account. If your balance is then negative, we may suspend processing until it is settled. See the Refund Policy for chargebacks.

## 8. Your content and our licence to it

8.1 **You own your content.** You keep all rights in the audio you upload ("**Input**") and in the stems, MIDI, analysis data and any other output we generate from it for you ("**Output**"). We claim no ownership in either. To the extent we hold any right in the Output, we assign it to you when we deliver it.
<!-- LAWYER-REVIEW: Confirm that the assignment/disclaimer of rights in AI-generated Output is drafted in a way that works under Israeli copyright law and does not undermine the position that the Output is the user's own work (or, where no copyright subsists, that nothing is being warranted). -->

8.2 **Limited licence to us.** So that we can run the Service, you grant us a worldwide, non-exclusive, royalty-free licence to receive, store, copy, transmit, process and transform your Input, and to create, store and deliver the Output, in each case only for the purpose of providing the Service to you, keeping it secure and complying with the law. This licence ends when we delete your Input and Output (section 8.4), except for backups that are deleted in the ordinary course.

8.3 **No model training.** We do **not** use your Input or Output to train, fine-tune or evaluate machine-learning models, and we do not allow our sub-processors to do so.

8.4 **Deletion.** Your Input and Output are automatically deleted from our storage **24 hours** after upload. The download links the plugin receives expire at the same time. Keep your own copies: after 24 hours we cannot recover them for you. We retain job metadata (timings, tempo, key, error codes, credit entries) as described in the Privacy Policy.

8.5 **Your responsibility for Input.** You represent and warrant that, for every clip you upload, you own the recording and the underlying composition or hold all licences, consents and permissions needed for us to process it as described in these Terms, and that the clip does not infringe anyone's rights or break any law.

8.6 **We do not clear samples.** Separating, transcribing or transposing someone else's recording does not create a right to use it. If your Output is derived from a recording or composition you do not own, releasing, performing or distributing a track that contains it still requires a licence from the owners of the master recording and of the composition. Obtaining those licences is entirely your responsibility. See the Copyright Policy (/legal/copyright).

## 9. Acceptable use

You agree not to, and not to help anyone else to:

(a) upload content you do not have the right to upload, or content that is unlawful, defamatory, hateful, or that infringes anyone's intellectual property, privacy or other rights;
(b) upload malware or anything designed to interfere with the Service, or upload files that are not audio;
(c) probe, scan, overload, disrupt or bypass the security, rate limits, credit accounting or access controls of the Service;
(d) use automated tools to access the Service other than through the documented API with a valid API key;
(e) reverse engineer, decompile or extract the source code, models or weights of the Service, except to the extent that applicable law expressly allows this despite a contractual restriction;
(f) resell, sublicense or share your account or credits, or offer the Service to third parties as your own service without our written agreement;
(g) use the Service to build a competing separation or transcription product, or to benchmark it for publication without our permission;
(h) create multiple accounts, use false identities or manipulate the referral programme to obtain credits or rewards;
(i) use the Service in breach of export-control, sanctions or other applicable laws.

## 10. API keys and automated access

10.1 You can create API keys (`tm_live_…`) in your account to use the Service from scripts and other software. A key acts as you: it spends your credits and is subject to your rate limits. We show the full key only once, when it is created.

10.2 You are responsible for every request made with your keys. Store them securely, never put them in client-side or public code, and revoke a key immediately in your account if it may have leaked.

10.3 **Rate limits.** Currently: 10 job submissions per minute, 60 read requests per minute and 5 concurrent status streams per account. Requests above the limit are rejected with an error and a retry-after time. We may change the limits with notice on the website.

10.4 We may suspend a key or account that we reasonably believe is compromised, abusive or causing harm to the Service, and we will tell you when we do unless the law prevents us.

## 11. Referral programme

11.1 We may give you a referral code or link. When someone you refer signs up and meets the conditions shown on the referral page at the time (for example, making a first purchase), both of you receive the reward shown there — normally credits. Rewards are granted to the accounts involved and are subject to section 5.5 and 5.6.

11.2 **Affiliates.** If we have accepted you into our affiliate programme in writing, you may instead receive a commission on qualifying purchases made through your code, on the terms of that separate agreement. Commissions are calculated on net revenue after payment-provider fees, are held until the chargeback window for the purchase has closed, and are void if the purchase is refunded or charged back.
<!-- LAWYER-REVIEW: The implemented affiliate system pays a 30% recurring commission on net revenue while the product brief describes credit rewards to both parties. Confirm which programme(s) launch, whether affiliates need a separate written agreement (recommended, including tax/withholding and self-billing terms) and whether commissions to Israeli residents raise withholding-tax issues. -->

11.3 **Rules.** You may not: refer yourself or accounts you control; use the code in paid advertising on our brand name or on any brand you do not own; send unsolicited messages (spam) containing the code; make misleading claims about the Service; or present yourself as us. Referred users must be genuine, distinct people.

11.4 We may withhold, void or claw back rewards and commissions that we reasonably believe were obtained in breach of these rules, and we may end the programme or change its rewards for the future at any time by updating the referral page. Rewards already granted are not affected.

11.5 Referral marketing by you must comply with advertising and consumer-protection laws where you and your audience are, including disclosure of the fact that you receive a reward.

## 12. Our intellectual property

12.1 The Service, the plugin, the website, the models we use, and all associated software, designs, text, graphics, names and logos belong to us or our licensors and are protected by intellectual-property laws. Except for the rights expressly granted in these Terms and the EULA, we reserve all rights.

12.2 Third-party components in the plugin and the Service are licensed under their own terms, which are listed at [[WEBSITE_URL]]/legal/third-party and in the file `THIRD_PARTY_LICENSES.md` that ships with the plugin.

12.3 If you send us feedback or suggestions, you allow us to use them without any obligation to you. You keep the right to use your own ideas too.

12.4 "VST" is a trademark of Steinberg Media Technologies GmbH. Other product names (for example DAW names) are trademarks of their owners and are used only to describe compatibility.

## 13. Third-party services

The Service relies on third parties: our authentication, hosting, storage and GPU providers, [[MERCHANT_OF_RECORD]], and the digital audio workstation ("DAW") software in which you run the plugin. We are not responsible for those services, and their terms govern your relationship with them. We are responsible for choosing them with reasonable care and for our own obligations under these Terms and the Privacy Policy.

## 14. Availability, changes and no service-level guarantee

14.1 We work hard to keep the Service available, but we do not promise uninterrupted or error-free operation, particular processing times, or that the Service will be available in every country. Processing time depends on load, on our GPU providers and on your connection.

14.2 We may change, add or remove features, models and limits, and we may suspend the Service for maintenance, security or legal reasons. Where a change materially reduces what you have already paid for, we will tell you in advance where reasonably possible.

14.3 If we discontinue the Service entirely, we will give at least 30 days' notice by email and refund the unused portion of any credit pack purchased in the preceding 12 months, pro rata to the unused credits, and any prepaid subscription period that will not be delivered.
<!-- LAWYER-REVIEW: Confirm the discontinuation refund commitment (unused pack credits bought in the last 12 months, pro rata) is what the business wants; a broader or narrower window is a commercial choice, but under EU/UK consumer law some refund on discontinuation is expected in any case. -->

14.4 We have no obligation to provide support, but we try to answer questions sent to [[SUPPORT_EMAIL]] within a reasonable time.

## 15. Disclaimers

15.1 To the fullest extent permitted by law, the Service and all Output are provided "**as is**" and "**as available**", without warranties of any kind, whether express, implied or statutory, including any implied warranties of merchantability, fitness for a particular purpose, accuracy and non-infringement.

15.2 In particular, we do not warrant that stems will be cleanly separated, that transcribed MIDI will match the notes in your clip, that tempo or key detection will be correct, or that the Output is suitable for professional release without further work.

15.3 Nothing in the Service is legal advice. Whether you may use a particular recording, and whether your Output infringes anyone's rights, are questions only you (with your own advisers) can answer.

15.4 **Consumers.** If you are a consumer, you have legal rights in relation to digital content and services that do not conform to the contract, and nothing in these Terms limits those rights. Sections 15 and 16 apply only to the extent the law allows.

## 16. Limitation of liability

16.1 **Nothing in these Terms excludes or limits our liability** for death or personal injury caused by our negligence, for fraud or fraudulent misrepresentation, for gross negligence or wilful misconduct, or for any other liability that cannot be excluded or limited by applicable law.

16.2 Subject to 16.1, we are not liable to you for any indirect, incidental, special, consequential or punitive loss, or for loss of profits, revenue, business, goodwill, data or content, or for the cost of substitute services, however caused and even if we were told it might happen.

16.3 Subject to 16.1, **our total liability** to you for all claims arising out of or relating to the Service or these Terms, whether in contract, tort (including negligence), statute or otherwise, **is limited to the total amount you paid to [[MERCHANT_OF_RECORD]] for the Service in the 12 months immediately before the event giving rise to the claim**. If you paid nothing in that period, our liability is limited to US$ 50.
<!-- LAWYER-REVIEW: Confirm the 12-month-spend cap with a US$ 50 floor is enforceable against consumers in the EU (Unfair Contract Terms Directive), the UK (Consumer Rights Act 2015) and Israel (Standard Contracts Law 5743-1982, which lets courts void one-sided limitation clauses in standard-form contracts), and whether a different or no cap is advisable for consumers. -->

16.4 Because your Input and Output are deleted after 24 hours and are also held by you locally, we are not responsible for loss of Input or Output that you did not keep your own copy of.

16.5 Each provision of this section is separate. If any part is unenforceable, the rest still applies.

## 17. Your indemnity

If you are a business user, you will defend, indemnify and hold us harmless from any claim, loss, liability and expense (including reasonable legal fees) arising from your Input, from your use of the Output, or from your breach of these Terms or of any law. If you are a consumer, this section applies only to the extent permitted by the law of the country where you live, and only for losses caused by your breach of sections 8.5, 9 or 11.3.
<!-- LAWYER-REVIEW: Consumer indemnities are frequently held unenforceable in the EU/UK; confirm whether to keep the narrowed consumer indemnity or delete it for consumers entirely. -->

## 18. Suspension and termination

18.1 **By you.** You can stop using the Service at any time and can ask us to delete your account at [[PRIVACY_EMAIL]] or through your account settings. Unused credits are forfeited when the account is deleted, except for any refund you are entitled to under the Refund Policy or the law. Cancel any subscription first (section 6.2); deleting the account does not by itself stop renewals managed by [[MERCHANT_OF_RECORD]].

18.2 **By us.** We may suspend or terminate your account, API keys or access to the Service, with notice where reasonably possible, if: you materially breach these Terms (including sections 8.5, 9 and 11.3); we receive a valid infringement notice about your content and you are a repeat infringer (see the Copyright Policy); a payment is charged back; we are required to by law; or continued service would create a security or legal risk for us or others. We may also close accounts that have been inactive with a zero balance for more than 24 months, after emailing you 30 days beforehand.

18.3 If we terminate for your breach, we do not refund credits. If we terminate for any other reason, we will refund the unused part of a credit pack pro rata and any subscription period that will not be delivered.

18.4 Sections that by their nature should survive (including 8, 12, 15, 16, 17, 20 and 21) survive termination.

## 19. Changes to these Terms

19.1 We may update these Terms. For material changes we will give you at least **14 days' notice** by email or by a prominent notice in the plugin or on the website before they take effect, unless a change is required sooner by law or to address a security issue. Non-material changes (for example clarifications and typographical corrections) take effect when published.

19.2 If you do not agree to a change, stop using the Service before it takes effect and, if you have a subscription, cancel it. If a material change adversely affects you and you cancel within 30 days of the notice, we will refund the unused portion of any credit pack bought in the 12 months before the notice, pro rata. Using the Service after a change takes effect means you accept it.
<!-- LAWYER-REVIEW: Confirm the unilateral-variation clause (14 days' notice, deemed acceptance by continued use, exit refund) meets the transparency and "valid reason" requirements of the EU Unfair Contract Terms Directive and UK CMA guidance, and consider whether price changes need a separate express opt-in for subscribers. -->

## 20. Governing law and disputes

20.1 These Terms and any dispute or claim arising out of or in connection with them or the Service are governed by the laws of the **State of Israel**, without regard to its conflict-of-law rules. The competent courts of **Tel Aviv-Yafo, Israel** have exclusive jurisdiction.

20.2 **Mandatory consumer law.** If you are a consumer living in the European Economic Area, the United Kingdom, the United States or another country whose law gives consumers protections that cannot be waived by contract, then: (a) you also benefit from those mandatory protections, and nothing in these Terms takes them away; (b) you may bring proceedings in the courts of the country where you live, and we may bring proceedings against you only there; and (c) to the extent those mandatory rules conflict with section 20.1, they prevail.
<!-- LAWYER-REVIEW: Confirm that the Israeli law/Tel Aviv venue clause with a mandatory-law carve-out is workable under Rome I Art. 6 and Brussels I recast Arts. 17-19 for EU consumers, the UK equivalents, and that the clause is presented in a way that survives Israel's Standard Contracts Law review; consider whether to add a plain-language statement that EU/UK consumers keep their local court. -->

20.3 Before starting a formal dispute, please write to [[LEGAL_EMAIL]] and give us 30 days to try to resolve it with you. We are not obliged to take part in alternative dispute resolution proceedings before a consumer-arbitration body, but we may agree to do so case by case.

20.4 The United Nations Convention on Contracts for the International Sale of Goods does not apply.

## 21. General

21.1 These Terms, with the documents listed in section 1.3, are the whole agreement between you and us about the Service and replace any earlier terms.

21.2 If any part of these Terms is found invalid or unenforceable, that part is removed or limited to the minimum extent necessary and the rest remains in force.

21.3 We may assign or transfer these Terms to a successor of our business, and will tell you if we do. You may not assign them without our written consent.

21.4 A failure or delay by either of us in enforcing a right is not a waiver of it.

21.5 We are not liable for a failure to perform caused by events beyond our reasonable control, including failures of our hosting, GPU or payment providers, internet outages, and acts of government.

21.6 These Terms are written in English. Translations are for convenience; the English version prevails to the extent the law allows.

21.7 Notices to us must be sent to [[LEGAL_EMAIL]] (legal), [[SUPPORT_EMAIL]] (support) or [[PRIVACY_EMAIL]] (privacy), or by post to [[COMPANY_ADDRESS]]. Notices to you may be sent to the email address on your account.

## 22. Contact

[[COMPANY_LEGAL_NAME]]
[[COMPANY_ADDRESS]]
Registration number: [[COMPANY_REG_ID]]
Support: [[SUPPORT_EMAIL]] · Legal: [[LEGAL_EMAIL]] · Privacy: [[PRIVACY_EMAIL]]
Website: [[WEBSITE_URL]]
