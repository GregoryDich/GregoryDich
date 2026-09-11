# End-User Licence Agreement

_Effective date: [[EFFECTIVE_DATE]]_

> **In short:** We license the [[PRODUCT_NAME]] plugin to you; we do not sell it. You may install it on up to **3 computers** that you own or control and use it to make music, including music you sell. You may not copy it for others, reverse engineer it (beyond what the law allows) or tamper with its account and credit checks. The plugin needs an account and an internet connection to process clips: when you press "process" it sends the audio clip you chose and your sign-in token to our servers, and nothing else — crash reports only if you turn them on. Music you make with it is yours. The plugin includes open-source components listed in `THIRD_PARTY_LICENSES.md`. It is provided as is, and our liability is capped, except where the law says otherwise.

## 1. Agreement

1.1 This End-User Licence Agreement ("**EULA**") is between you and [[COMPANY_LEGAL_NAME]], [[COMPANY_ADDRESS]], registration number [[COMPANY_REG_ID]] ("**we**", "**us**"). It covers the [[PRODUCT_NAME]] plugin software in all its formats (VST3, Audio Unit and standalone), its installer, and any updates we provide (together, the "**Software**").

1.2 By downloading, installing or using the Software you accept this EULA. If you do not accept it, do not install the Software, and delete any copy you have.

1.3 The cloud service the Software connects to is governed by the Terms of Service (/legal/terms) and the Privacy Policy (/legal/privacy). Those documents apply to your account and credits; this EULA applies to the Software on your computer.

1.4 If you are a consumer, nothing in this EULA limits rights that the law of your country gives you and that cannot be waived by contract.

## 2. Licence

2.1 We grant you a **personal, non-exclusive, non-transferable, revocable** licence to install and use the Software on up to **three (3) computers** that you own or control, for your own musical work, whether hobbyist or professional. If you are a business, "you" means the natural person to whom the account is issued, and the three computers must be used by that person.
<!-- LAWYER-REVIEW: The three-computer limit is a contractual statement only — the current Software does not enforce machine activation. Confirm the number and whether "own or control" language is acceptable, or whether a per-seat definition for studios should be added. -->

2.2 **Your music is yours.** Everything you create with the Software — stems, MIDI, instruments, recordings and finished tracks — belongs to you, and you may use it for any purpose, including commercial release, without any payment or credit to us. (Whether you may use someone else's recording as the source is a different question: see the Copyright Policy at /legal/copyright.)

2.3 You may make one backup copy of the installer for archival purposes.

## 3. Restrictions

Except to the extent that applicable law expressly allows it despite this restriction, you may not:

(a) copy the Software except as permitted in section 2, or distribute, sell, rent, lease, lend, sublicense or otherwise make it available to anyone else, including as part of a bundle or a "cracked" package;
(b) reverse engineer, decompile, disassemble or otherwise attempt to derive the source code, algorithms, models or protocols of the Software — except that if you live in the EU or UK you may decompile the Software to the limited extent necessary to achieve interoperability with an independently created program, if we have not made the necessary information available on request;
(c) modify, adapt or create derivative works of the Software;
(d) remove, hide or alter any copyright, trademark or other proprietary notice, or the third-party licence notices in the Software;
(e) bypass, disable or interfere with the sign-in, credit or usage checks in the Software, or use the Software with a stolen or shared account;
(f) use the Software in breach of the Terms of Service or of any applicable law;
(g) use our name or logos to endorse or promote your products without our written permission.
<!-- LAWYER-REVIEW: Confirm the reverse-engineering carve-out tracks Art. 6 of the EU Software Directive 2009/24/EC and s.50B UK CDPA 1988, and that the anti-circumvention clause does not overreach for Israeli consumers. -->

## 4. Account, internet connection and what the Software sends

4.1 **Account and connection required.** Processing a clip requires a [[PRODUCT_NAME]] account with available credits and an internet connection. The audio analysis runs on our servers, not on your computer. Instruments the Software has already downloaded stay playable offline from the copy it keeps on your computer.

4.2 **What is transmitted, and when.** The Software sends data to our servers only in these cases:

- **When you sign in:** your email address and password, sent over an encrypted connection to obtain a session token. The Software never stores your password; it stores the session token and a refresh token.
- **On every request to our servers:** your session token (or, if you configured one, your API key), and the Software's product name and version number.
- **When you press "process":** the audio clip you selected or recorded, encoded to a lossless format (at most 10 MB, of which the first 60 seconds are processed), together with the processing options you chose (which stems to separate and transcribe, the target root note, and your session's sample rate).
- **Crash reports, only if you turn them on** in the Software's settings: a description of the crash, the Software and operating-system versions, the host application's name and version, and the device model. Crash reports never contain audio. Crash reporting is **off** by default.

The Software does **not** transmit your DAW project, any audio you did not choose to process, your files, your contacts or your location.

4.3 **What is stored on your computer.** The Software stores your session and refresh tokens, your settings and a local cache of downloaded results in a settings folder in your user profile. These files are protected by your operating system's file permissions. Signing out removes the tokens; you can clear the cache from the Software's settings or by deleting the folder.

4.4 **Server-side retention.** Uploaded audio and generated results are deleted from our servers 24 hours after upload. See the Privacy Policy.

## 5. Ownership

5.1 The Software is licensed, not sold. We and our licensors own all right, title and interest in the Software, including all copyright, patents, trade secrets, trademarks and other intellectual-property rights. This EULA gives you no rights other than the licence in section 2.

5.2 **Third-party components.** The Software includes open-source and other third-party components, each licensed under its own terms. The list of components, their licences and the notices we are required to reproduce are in the file **`THIRD_PARTY_LICENSES.md`** installed with the Software and published at [[WEBSITE_URL]]/legal/third-party. Where a third-party licence gives you rights that are broader than this EULA for that component, that licence prevails for that component.

5.3 "VST" is a trademark of Steinberg Media Technologies GmbH. "Audio Units" is a trademark of Apple Inc. Other names are trademarks of their owners and are used only to describe compatibility.

## 6. Updates

6.1 We may release updates that fix bugs, add features or change how the Software works with our servers. Updates may be delivered through the website or an installer; the Software does not update itself silently. We may require you to install an update to keep using the cloud service, for example when the API changes or for security reasons.

6.2 This EULA applies to updates unless an update comes with its own terms. We are not obliged to support old versions, old operating systems or old host applications.

## 7. Term and termination

7.1 This EULA lasts until terminated. You may terminate it at any time by uninstalling and deleting all copies of the Software.

7.2 It terminates automatically, without notice, if you breach it. It also terminates when your [[PRODUCT_NAME]] account is closed for breach of the Terms of Service.

7.3 On termination you must stop using the Software and delete all copies. Sections 2.2, 5, 8, 9, 10 and 11 survive termination.

## 8. Warranty disclaimer

8.1 To the fullest extent permitted by law, the Software is provided "**as is**" and "**as available**", without warranty of any kind, express or implied, including warranties of merchantability, fitness for a particular purpose, non-infringement, and that it will run without interruption or error in every host application, operating system or hardware configuration.

8.2 AI-based separation and transcription produce approximations. We do not warrant the accuracy, completeness or musical quality of any result.

8.3 **Consumers in the EU and UK** have statutory rights to digital content that conforms to the contract (Directive (EU) 2019/770; Consumer Rights Act 2015). Nothing in this section excludes those rights. If the Software does not conform, contact [[SUPPORT_EMAIL]] and we will bring it into conformity or offer the remedies the law provides.
<!-- LAWYER-REVIEW: Under the Digital Content Directive the trader must also supply updates necessary to keep the content in conformity for the period the consumer reasonably expects; confirm whether section 6 needs an express "security and conformity updates" commitment and a minimum support period. -->

## 9. Limitation of liability

9.1 Nothing in this EULA excludes or limits our liability for death or personal injury caused by our negligence, for fraud or fraudulent misrepresentation, for gross negligence or wilful misconduct, or for anything else that cannot be excluded or limited by applicable law.

9.2 Subject to 9.1, we are not liable for any indirect, incidental, special, consequential or punitive loss, or for loss of profits, revenue, business, goodwill, data, recordings or projects, however caused. Keep backups of your projects.

9.3 Subject to 9.1, our total liability arising out of or in connection with the Software, whether in contract, tort (including negligence), statute or otherwise, is limited to the total amount you paid to [[MERCHANT_OF_RECORD]] for [[PRODUCT_NAME]] in the 12 months before the event giving rise to the claim, or US$ 50 if you paid nothing in that period. This cap is shared with the cap in the Terms of Service; the two do not add up.
<!-- LAWYER-REVIEW: Same enforceability question as Terms of Service s.16 (Israeli Standard Contracts Law, EU UCTD, UK CRA); confirm a single shared cap across EULA and Terms is the intended structure. -->

## 10. Export control and sanctions

10.1 The Software uses standard encryption for its network connections and may be subject to export-control laws of Israel, the United States and other countries. You may not download, install or use the Software in a country or territory that is subject to comprehensive sanctions, or if you are on a sanctions or denied-parties list, or for any use prohibited by those laws.
<!-- LAWYER-REVIEW: Confirm whether the Software (a JUCE plugin using TLS via the operating system's or libcurl's crypto) needs any Israeli DECA/export classification or US EAR self-classification (likely mass-market/5D992 or exempt), and whether the sanctions clause should list countries expressly. -->

10.2 The Software is not designed for use in safety-critical systems, and you may not use it in any application where failure could lead to death, injury or severe damage.

## 11. Governing law and disputes

11.1 This EULA is governed by the laws of the **State of Israel**, and the competent courts of **Tel Aviv-Yafo** have exclusive jurisdiction, subject to 11.2.

11.2 If you are a consumer in the EEA, the UK, the United States or another country whose law gives you protections that cannot be waived by contract, you also benefit from those protections, you may bring proceedings in the courts of the country where you live, and we may bring proceedings against you only there.

11.3 The UN Convention on Contracts for the International Sale of Goods does not apply.

## 12. General

12.1 This EULA, the Terms of Service, the Privacy Policy and `THIRD_PARTY_LICENSES.md` are the entire agreement about the Software. If any provision is unenforceable, it is limited to the minimum extent necessary and the rest remains in force. We may assign this EULA to a successor of our business. Our failure to enforce a provision is not a waiver. This EULA is written in English; translations are for convenience only.

12.2 We may update this EULA for new versions of the Software. The version that applies is the one you accepted when installing the Software; the current version is always at /legal/eula.

## 13. Contact

[[COMPANY_LEGAL_NAME]] · [[COMPANY_ADDRESS]] · Registration number [[COMPANY_REG_ID]]
Support: [[SUPPORT_EMAIL]] · Legal: [[LEGAL_EMAIL]] · [[WEBSITE_URL]]
