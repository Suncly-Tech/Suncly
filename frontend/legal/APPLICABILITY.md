# Applicability

For each framework the brief names: whether it applies to Suncly today, what it requires,
where the site meets it, what is open, and the source. Written 2026-10-05.

**Verification caveat, stated once.** The environment's network policy refused every
primary legal source that day: riigiteataja.ee, eur-lex.europa.eu, aki.ee, edpb.europa.eu,
euipo.europa.eu, legislation.gov.uk, linuxfoundation.org. Nothing below was read from a
fetched primary page. Statutory wording comes from search-engine snippets of the cited
pages or from memory, and is marked **unverified**. Nothing here is legal advice, and no
page on the site claims compliance with any law. Counsel re-checks every row against the
primary source before a legal page loses its draft label (`launch.legalPublished`).

| Framework | Applies today? | What it requires | Where the site meets it | Open | Source (to re-check) |
| --- | --- | --- | --- | --- | --- |
| GDPR, Arts 12 to 14 | Yes, for the pilot form and correspondence | Controller identity, purposes and bases, recipients, transfers, retention, rights, one-month answer, right to complain | `/privacy` §1, §3 to §7 | Company facts, providers, retention periods (blanks) | eur-lex CELEX:32016R0679, **unverified** |
| GDPR Art 28 | Yes, for any vendor touching form data; later as processor for hosted evaluations | Written processor agreements; a DPA and sub-processor list when hosted | `/privacy` §5, §12, §13 | Vendors and agreements (blank) | Same |
| GDPR Art 33, 34 | Yes (procedure) | Notify the DPA within 72 hours where there is a risk; inform people where the risk is high | `/privacy` §11; `/security` incident notice | Internal procedure | Same |
| GDPR Chapter V | Conditionally, if a provider is outside the EEA | Adequacy decision or standard contractual clauses, named | `/privacy` §5 table | Provider locations (blank) | Same |
| GDPR Art 77 | Yes | Name the supervisory authority | `/privacy` §7: Andmekaitse Inspektsioon, Tatari 39, 10134 Tallinn, info@aki.ee | Address from snippets, **unverified** | aki.ee/en |
| Estonian Personal Data Protection Act | Supplementary | AKI as authority; nothing beyond GDPR for Suncly | `/privacy` §7 | Current English consolidation to locate (the 2023 one is superseded) | riigiteataja.ee, **unverified** |
| Information Society Services Act §4 | Yes | Name, registry code and register, address, e-mail; VAT number if registered | `/legal` | All four facts blank | riigiteataja.ee 515012019001, **unverified** snippet |
| Commercial Code §15 | Yes | Business name, seat and register code on the website | `/legal`; footer legal line | Facts blank | riigiteataja.ee, **unverified** snippet |
| Language Act §16 | Yes, one summary | A summary in Estonian of the field of activity on a foreign-language site of an Estonian company | `/legal`, Estonian paragraph (draft for founder review) | Founder review of the Estonian text | **unverified** snippet |
| Electronic Communications Act §103¹ | Only if marketing e-mail is sent (none today) | Prior consent for natural persons; opt-out in every message | `/privacy` §4 row "news" | | **unverified** snippet |
| Law of Obligations Act §§35 to 44 | Once terms exist | Standard-terms control applies B2B; surprising or unreasonably detrimental terms void | `/terms` §14 | Counsel review of every clause | riigiteataja.ee 506082024001, **unverified** |
| Law of Obligations Act §106 | Same | No exclusion of liability for intent; "unreasonable" exclusions void | `/terms` §10 carve-outs and cap | Counsel to confirm the cap and the EUR 1,000 floor | Same |
| Law of Obligations Act §1048 | Yes, for the badge and reports | Incorrect expert information in a financial matter is unlawful; a duty to correct | `/certified/policy` §11 (correction duty), scope and limits on every record | Counsel: whether a badge is "expert information" | Same |
| Advertising Act §4 | Yes | No misleading advertising, including claims of recognition or approval | No "official", "accredited", "compliant", "approved by"; `scripts/forbidden.mjs` | | riigiteataja.ee 504092025001, **unverified** |
| Accounting Act §12 | Once an invoice exists | Seven-year retention of source documents | `/privacy` §4, §6 | | **unverified** |
| Cookie consent (ePrivacy 5(3), enforced by AKI through GDPR) | Yes | No non-essential storage without consent; a statement of what is stored | `/cookies`: no cookies; one essential local-storage key, inspected | Exact Estonian transposition section (the §102 pointer looks wrong) | sorainen.com, **unverified** |
| EU AI Act (2024/1689), as amended by the Digital Omnibus on AI (2026/1744, per secondary sources) | Not today | Suncly is neither provider nor deployer of a tested agent; becomes a provider of a component once a model-based judge ships. Never claim CE, conformity assessment, notified body, "AI Act compliant" | `/certified/policy` §2; `forbidden.mjs` | Status of the Omnibus and dates, **unverified** | Secondary summaries only |
| Cyber Resilience Act (2024/2847) | Conditionally; reporting duties live since 11 Sept 2026 for products in scope (per secondary sources) | For a product in scope: CVD policy, a contact point, support period, Art 14 reporting; a free, non-commercial CLI is out of scope, a CLI that is the client of a paid API likely in | `/security` disclosure policy and support period; `/.well-known/security.txt` | Scope once billing exists; no compliance claimed | **unverified** |
| Data Act (2023/2854) Chapter VI | At API launch | Switching and export terms; no switching charges from 12 Jan 2027 | `/terms` §12 export clause | Full terms at launch | **unverified** |
| Digital Services Act | No | A registry authored by Suncly is first-party content, not hosting | | Changes only if operators self-publish | **unverified** |
| NIS2, DORA | Bind buyers, not Suncly | Supplier answers: measures, incident notice, data location, sub-processors, exit | `/security` supplier questionnaire table | | **unverified** |
| European Accessibility Act | No (B2B, microenterprise) | WCAG 2.2 AA stays the target; no claim under the Act | axe run on every page (`scripts/axe.mjs`) | | **unverified** |
| Trade marks: ® and ™ | Yes | ™ until registration; ® on an unregistered mark is misleading in the EU, an offence in the UK (TMA 1994 s.95), evidence of deceptive intent in the US | `TRADEMARK_SYMBOL` in `lib/launch.ts`; `forbidden.mjs` flags ® | Clearance against SUNLY (Sunly AS, Tallinn); certification mark or ordinary mark (EUTMR Art 83) | **unverified** |
| Linux Foundation trademark usage | Yes | Factual use, no implied endorsement, no logo, never "A2A certified" | Footer attribution; "tested against A2A 1.0" wording; `forbidden.mjs` | Re-read the page on the day | linuxfoundation.org/legal/trademark-usage, refused |
| UK GDPR and PECR, Swiss FADP, US CCPA, CAN-SPAM, FTC | Not assessed | `targetMarkets` is EU only | | Add if a market is named | |
