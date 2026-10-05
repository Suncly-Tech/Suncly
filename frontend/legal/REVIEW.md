# For the lawyer

Per document: the clause, the question, and the source. The drafts are complete in form;
every blank is a founder input named in `lib/launch.ts`. One flag, `launch.legalPublished`,
removes the draft notice and the `noindex` on all legal pages at once; set it only after
sign-off. Written 2026-10-05.

## Privacy Policy (`app/privacy/page.tsx`)

| Clause | Question | Source |
| --- | --- | --- |
| §1 controller | Entity, registry code, office, privacy contact. Is a DPO needed? (Our view: no.) | GDPR Art 13(1)(a), (b); Art 37 |
| §4 legal bases | Is (f) legitimate interest the right basis for answering a business enquiry from a work address, or (b)? | GDPR Art 6(1) |
| §5 recipients | Providers, locations and transfer safeguards once confirmed (Vercel, Cloudflare, Supabase are unconfirmed) | GDPR Arts 28, 44 to 46 |
| §6 retention | Periods for enquiries and logs | GDPR Art 13(2)(a); Accounting Act §12 |
| §7 complaint route | Confirm the Inspectorate's address and preferred complaint channel | aki.ee |
| §8 storage | Local storage used only at the visitor's request: strictly necessary, no consent needed? | ePrivacy Art 5(3); AKI guidance |
| §12, §13 roles | Controller and processor split once hosted; the DPA; how erasure requests meet append-only evidence | GDPR Arts 4(7), 4(8), 17, 28 |
| §6 retention | "Seven years" for accounting records is our reading of the Accounting Act; confirm the period and its start | Accounting Act §12 |
| §14 changes | Thirty days' notice for material changes: a drafted period, founder and counsel to set | |

## Terms of Service (`app/terms/page.tsx`)

| Clause | Question | Source |
| --- | --- | --- |
| §1 parties | Entity details; business-use statement sufficient to exclude consumer rules? | LOA; Consumer Protection Act |
| §4 authority to test | The confirmation, the sandbox declaration and the indemnity: enforceable and sufficient? Reference to criminal liability for unauthorised testing: correct wording for Estonia? | Penal Code (computer-related offences); LOA |
| §5 fees | Usage-only model; "no fees are charged yet"; the thirty-day notice before charging starts and the dispute periods (thirty days to raise, fourteen to answer) are drafted periods, founder and counsel to set; the fee table's blanks | LOA §§35 to 44 (standard terms); VAT Act |
| §6 licence | A public repository with no licence: is the limited licence in §6 enough until an open-source licence is chosen? Which licence? | Copyright Act |
| §7 certification by reference | Does incorporating the Certification Policy by reference work against operators who are not customers? | LOA §37 |
| §8 confidentiality | Three years after the contract ends: a drafted period | |
| §9 warranties | The disclaimer and the home-page statement (section 13): consistent and not "unreasonable"? | LOA §106 |
| §10 liability | Cap at twelve months' fees or EUR 1,000; carve-outs for intent and death or injury; exclusion of indirect loss | LOA §106; §1048 |
| §11 changes | Thirty days' notice and the right to leave: drafted period | LOA §§37 to 39 |
| §12 term | Thirty days' notice of termination by Suncly and thirty days to export: drafted periods | |
| §13 governing law | Estonian law and court (Harju County Court usual) | |
| §14 conclusion | Contract formed by first use: workable B2B? | LOA §9 |

## Certification Policy (`app/certified/policy/page.tsx`)

| Clause | Question | Source |
| --- | --- | --- |
| §2 nature | Is the "private, voluntary, not accredited" language enough to avoid the appearance of official recognition? | Advertising Act §4; UCPD Annex I pts 2, 4 |
| §3 criteria | The page now says no criteria are adopted; the v0.1 proposal stays internal (`REDESIGN_PLAN.md` §9) until the founder accepts it. When published: is the wording safe? | |
| §5 validity | Blank on the page (six months and the card-hash trigger were the proposal, now internal); also blank: re-test triggers, response times | |
| §6, §8, §12 periods | Fourteen days to correct a prohibited use, seven days to remove the badge, thirty days' notice of a licence-affecting change: drafted periods, founder and counsel to set | |
| §8 licence | Badge licence terms; should the badge be an EU certification mark (Suncly tests agents and does not supply them) or an ordinary mark? | EUTMR Arts 83 to 93 |
| §10 no pay-to-pass | Sufficient to meet seal rules on independence? | FTC Endorsement Guides (if the US is ever a market); UCPD |
| §11 corrections | The duty to correct incorrect expert information: does §1048 apply to a badge relied on by third parties? Liability exposure? Response times are blank on the page | LOA §1048 |

## Across the site

| Topic | Question | Source |
| --- | --- | --- |
| Trade mark symbol | ™ everywhere; design allows ® after registration. Clearance of "Suncly" against the SUNLY marks of Sunly AS (registry code 14695483, Tallinn): classes and risk | EUIPO, Estonian Patent Office |
| A2A attribution | Footer wording: "Agent2Agent (A2A) is an open-source project of the Linux Foundation. Suncly is independent and is not affiliated with, endorsed by or certified by the Linux Foundation or the A2A project. Other names belong to their owners." Confirm against the Linux Foundation's trademark usage page on the day | linuxfoundation.org/legal/trademark-usage |
| Coding-agent names | Cursor, Claude Code, Codex, omp, Pi as plain text with a no-endorsement line; no logos | Each vendor's brand guidelines |
| Platform glyphs | The "Find Suncly" row uses text abbreviations until the platforms' logo usage rules are confirmed | X, LinkedIn, GitHub, Reddit brand pages |
| Legal notice | Whether the Language Act requires an Estonian summary on this site, and in what form (our reading, unverified: it does); the summary's wording; which company facts the Information Society Services Act and the Commercial Code require | ISSA §4; Commercial Code §15; Language Act §16 |
| Security contact | `security.txt` and the disclosure policy point to the general team address; the founders have not confirmed it as the destination for security reports and `securityContactEmail` is blank | RFC 9116 |
| Security | Disclosure policy and `security.txt` state only facts: the report address, no acknowledgement time, fix window, safe harbour, credit or incident-notice promise, support period as current practice. Which commitments to make is a founder and counsel decision | CRA (2024/2847) |
| Licence | The repository is public with no licence: visitors have no right to run the code the site tells them to install | Copyright Act |
