# Suncly website redesign: plan

Phase 1 deliverable of the "Rebuild suncly.com as a brand people remember" brief.
Written 2026-10-05 after reading the repository and the frontend, with no edits to
the site. This is the first of the two stops. Nothing below has been built yet.

Read with `REDESIGN_PROGRESS.md` (state of the work), `CONTENT.md` (source of every
claim) and `HANDOFF.md` (what is withheld and why).

## 0. Session facts you should know first

| Item | State in this session | What that means |
| --- | --- | --- |
| Branch | `claude/sweet-ride-ku6uau` (set by the environment) | The brief asks for `redesign/daylight` from `main`. The environment forbids pushing anywhere else, so the work lives on this branch. Rename it on merge if you want the brief's name. |
| Pushing | Commits are pushed to that one branch | The brief says "do not push". This cloud container is reclaimed when the session ends, so an unpushed branch is lost. The push goes only to the branch above; nothing is deployed, published or merged. |
| `frontend-design` skill | Not installed (the account has no plugins) | Add it with `claude plugin install frontend-design@claude-plugins-official`. Until then the brief's own design rules (sections 4 and 5) are the design guide. |
| Claude in Chrome | Not available in a cloud session | Screenshots come from the repository's Playwright setup, extended to the new pages and to 1440, 1024, 768 and 390 px. Playwright's Chromium is installed. |
| Image generation | None connected (a "Higgsfield" connector exists but its connection is incomplete) | Pictures are rendered in code: SVG and canvas scenes, path-traced stills in headless Chromium through Playwright, exported through the existing sharp pipeline. Blender is not installed. |
| Design canvas / Figma | Neither | Comparison boards are private artifact pages plus screenshots. Tokens and the type specimen live in the repository. |
| Python | 3.10, 3.11, 3.12 and 3.13 installed; `uv` available | The quickstart is run on 3.12, the minimum the package requires. |
| Outbound network | The environment's policy denies most hosts: suncly.com, the legal registers and statute sites, and several reference sites were refused | Allowing those hosts is a change to the environment's Network access setting (Edit the cloud environment, then a broader level or Custom with the hosts under Allowed domains; see https://code.claude.com/docs/en/cloud-environments#network-access). Until then: no look at the live site, legal sources from search snippets only, reference sites partly from memory. Each gap is marked in section 12. |
| `src/` and `tests/` | Untouched | The Agent Skill (section 7) is the only proposed change outside `frontend/`, and only if you say yes. |

## 1. Audit of the current site (ten lines)

1. The home page carries about 2,000 words in nine sections and is a stack of bordered cards; at 390 px it runs well past 12,000 px.
2. The first screen is a blue gradient sky (`#1d3a97` to `#4f78de`); blue is the accent, the focus ring, the link colour, the manifest theme colour and the input focus ring. The sun mark is a yellow disc behind a data table.
3. The hero drops into `EvaluationPreview`, a results table, before the visitor knows what the product is.
4. There is no picture anywhere. The only drawn element is the `//` cuts motif, which works.
5. The only action is "Request pilot access"; installing is not on the home page, although `suncly demo` takes a few minutes.
6. Instrument Serif is too narrow and too contrasty for the warm tone wanted; Manrope and JetBrains Mono are fine candidates to keep or replace.
7. The footer is a dark link grid with the mission line; no closing brand moment.
8. `/privacy` and `/terms` are `noindex` drafts with the company facts marked "to be supplied by the owners".
9. Worth keeping: `lib/content.ts` as the single copy source, `lib/capabilities.ts` as the status source, the real signed sample bundles in `lib/sample/`, the evidence components (`components/evidence/*`), the in-browser Ed25519 verifier, the workspace, the SEO layer (`lib/seo.ts`, JSON-LD, `llms.txt`), the accessibility work, the Lighthouse scripts, and the `// cuts` bullets in the not-tested list.
10. Lighthouse today: home mobile 88, desktop 100, accessibility 100. These are the floor.

## 2. Where the brief and the repository disagree

Raised here, not changed by me.

| Topic | Brief or inputs | Repository | Proposal |
| --- | --- | --- | --- |
| Repository visibility | Inputs: `public` | `CONTENT.md` and `/docs` say the repository is private; `git ls-remote` result recorded in section 12 | The Install section follows the inputs (`public`). CONTENT.md and the docs page get corrected in the build. Confirm that public is intended: a public repository with no licence gives visitors no right to copy or run the code (see next row). |
| Licence | `repository_licence` blank | `README.md`: "No license has been chosen yet"; `pyproject.toml` has no licence field | Not changed. Flagged for you and for counsel: "Install Suncly" from an unlicensed public repository is a legal gap. Until a licence exists, the Terms grant a limited licence to run the software for evaluation, and the site says the licence is being chosen. |
| Payments | Inputs: usage-only billing of the Suncly API, not live | `SCHEMA.md` §10: payments out of scope; `HANDOFF.md` §4: the billable unit is undecided (the code counts attempts) | Billing is treated as a commercial layer outside the core, as HANDOFF.md already does. The schema should say so before billing is built. The site states the model (usage only) and no unit or price until block 4 is filled. |
| Certification | Inputs: a "suncly certified" badge for agents that meet criteria | The product never approves or blocks (`core/policy_engine.py`, flag only) and produces no universal score (§10) | Certification is Suncly's own statement, made by a named person at Suncly on the basis of a signed evaluation Suncly ran, recorded outside the product's `decision` entity. The product stays flag-only. The badge is binary and dated, never a score or a tier. This keeps the two logics apart and the pages consistent. |
| Human approval | Brief 1.2: "waits for a named human to approve the test plan" | True for `suncly attest`. `suncly demo` approves on your behalf as `suncly-demo` (`docs/QUICKSTART.md` §2) | Copy says "`suncly attest` runs nothing until a named person approves the test plan"; the Install section says the demo approves its own two mock contracts. |
| Status words | Brief: Available, Pilot, Planned | `lib/capabilities.ts` has `available`, `limited` ("Available with limits"), `planned` | The map gets `available | pilot | planned` plus the existing `limit` sentence. Entries now marked `limited` become `available` with their limit shown in normal type beside them. The CLI as a whole is `pilot` (inputs). Say so if you want "limited" kept as a fourth word. |
| Coding agents | Brief 1.3: "the landing page shows that Suncly works with Cursor, Claude Code, Codex, omp and Pi" | No integration exists; `tested_in` is "no" for all five | Section 03 renders in its "none verified" state: "Run it from the coding agent you already use", with five names and a Planned marker each. |
| Quickstart timing | `docs/QUICKSTART.md`: "Five minutes" | Measured in this session (section 12) | The site uses the measured time, rounded up. |
| Domain | `lib/content.ts` uses `https://suncly.com`; the brief names `https://www.suncly.com` | Live site serves on `www` | Confirm the canonical host. Section 12 records what the live server returns. |

## 3. Claims that change

From the current site to the new one. Each gets a source line in `CONTENT.md` before
it enters `lib/content.ts`.

| Current | New | Source |
| --- | --- | --- |
| "Evaluate agents before you approve them." | "Test the agent. Then decide." with the brand line "Evidence before access." | Brief 4.1 and 5.02; the product behaviour in README |
| Repository private, no install on the home page | Install section with the quickstart commands, the real `suncly demo` output, and a measured duration | `docs/QUICKSTART.md`, this session's run, inputs block 3 |
| No price published | "Suncly charges for your usage of the Suncly API and for nothing else. No seats, no plans. Connecting and the badge are free. Billing starts when the API does." | Inputs block 4 (`connecting_fee: none`, `badge_fee: none`, `usage_billing: not live`) |
| No certification | "Agents that meet Suncly's published criteria can carry the Suncly Certified badge. Every badge links to its record." Programme state: not open, "Opening with our pilots", artwork marked Specimen | Inputs blocks 3 and 6; the Certification Policy draft |
| Model names list on `/workflows` ("Claude, OpenAI GPT and Codex, Grok…") | Removed from the home page. The Works-with row names five coding agents as plain text with a Planned marker and the existing no-endorsement sentence | Brief 5.03; HANDOFF.md §3 |
| Eleven mock agents in a table on `/workflows` | Suncly Lab: an interactive strip of the eleven, names and outcomes from `BEHAVIOURS` | `src/suncly/mock_agents/behaviours.py` lines 378 to 388 |
| "Available with limits" label | "Available" plus the limit sentence; "Pilot" for the CLI and the programme states | Section 2 above |
| Draft legal pages with blanks | Complete drafts with named blanks, plus a Certification Policy, a cookie page and a legal notice | Section 8 |
| No social links | "Find Suncly" row driven by one `social` object; a blank link is not rendered | Inputs block 1 (all five blank today) |
| Footer: mission line and link grid | Footer banner: the sun mark and the wordmark at monumental scale with ™ from `TRADEMARK_SYMBOL` | Inputs block 2 (`unregistered`) |
| "Suncly tests every claim repeatedly" | "Suncly tests an A2A agent against what its Agent Card claims" | A skill without examples is not tested (`core/contract_builder.py`); "every claim" is not provable |

Absolute words that survive, with the test that proves each (to be cited in CONTENT.md):

- "Inconclusive is never a pass": `tests/unit/test_non_negotiable_rules.py::test_inconclusive_is_never_counted_as_a_pass`.
- "Every report says what was not tested": `::test_dr_007_reports_state_what_was_not_tested`, `tests/unit/test_adapters.py::test_report_folder_is_self_contained_and_offline`.
- "Nothing runs before a named person approves" (for `suncly attest`): `tests/e2e/test_cli.py::test_attest_without_sandbox_declaration_is_refused` and the approval prompt path; the exact test for approval is listed in section 12.
- "The credential never appears in a transcript": `::test_dr_003_secrets_never_leave_the_runner`, `tests/e2e/test_mock_agents.py::test_leaky_agent_cannot_make_the_credential_appear_anywhere`.
- "Sandbox endpoints only": `::test_dr_006_tests_hit_only_a_declared_sandbox`. The copy keeps the limit: the declaration is the customer's; Suncly cannot verify a sandbox.
- "Suncly never approves or blocks an agent in this version": `core/policy_engine.py` (`decide` returns `flag` only); test named in section 12.

## 4. The section map

At most 800 visible words on the home page. The budget per section is the brief's (4.8).

| # | Section | Words | Picture | Status label | Built from |
| --- | --- | --- | --- | --- | --- |
| 01 | Navigation: lockup; Offer, Data, Research, Lab, Docs; "Install" | n/a | none | | `Nav.tsx` rebuilt on tokens, same mobile sheet behaviour |
| 02 | Hero: "Test the agent. Then decide." | 50 | Two cards (≥55% of first screen) | mono status line from the map | new `Hero.tsx`, `art/two-cards` |
| 03 | Works with: five names, Planned markers | 30 | none | from map | `WorksWith.tsx` |
| 04 | How it works: four frames from the Harbor sample | 90 | the card stage | | `HowItWorks.tsx`, sticky stage on desktop, stacked on phones |
| 05 | Install: Terminal tab plus five tool tabs | 45 + code | none | tool tabs Planned | `Install.tsx`, `lib/install.ts`, captured demo output |
| 06 | Evidence: one evidence card from the sample | 50 | the evidence card | | existing `components/evidence/*` restyled |
| 07 | Use cases: four examples | 100 | none | | `UseCases.tsx` |
| 08 | Suncly Offer | 45 | none | Billing not live | `Offer.tsx` |
| 09 | Suncly Certified | 45 | The seal at ~280 px, marked Specimen | Programme not open | `Certified.tsx`, `public/brand/badge/*` |
| 10 | Suncly Data | 55 | The aperture | | `Data.tsx`, `art/aperture` |
| 11 | Suncly Research | 55 | Analemma | notes are drafts, off the build | `Research.tsx`, `art/analemma` |
| 12 | Suncly Lab | 45 | Eleven specimens, interactive strip | probes and Layer 2 Planned | `Lab.tsx`, `art/specimens`, `BEHAVIOURS` |
| 13 | What we stand for, and limits | 135 | none | | `Stand.tsx` |
| 14 | Questions, and the closing sky | 45 + collapsed answers | the sky (the only blue) | | `Questions.tsx`, `ClosingSky.tsx` |
| 15 | Find Suncly | 10 | none | links blank today | `FindSuncly.tsx` |
| 16 | Footer and banner | not counted | Last light | ™ from one constant | `Footer.tsx`, `Banner.tsx`, `Wordmark.tsx` |

Section 08 and 09 sit side by side on desktop as one band no taller than half the
viewport. Product, Workflows, Sample evaluation, Security, Access, Company, Glossary and
the workspace keep their URLs and move to the footer and contextual links.

The one day: dawn tone in 02, clear paper through 03 to 09, warmer paper-deep bands for
11 and 12, the sky scene in 14, dusk in 16. Carried by background tone and the light
temperature of the pictures only.

## 5. Components and assets

Tokens (`app/globals.css`, Tailwind 4 `@theme`): `paper #FAF7F0`, `paper-deep #F1EBDD`,
`ink #1B1814`, `ink-soft #5C564C`, `line` ink at 10%, `sun #F2C14E` (sampled from
`public/mark.svg`), `amber #C8842B`, `ember #8F4A1E`, `dusk #17130F`; `pass`, `fail`,
`inconclusive` muted and scoped to evidence components; sky blues scoped to
`ClosingSky.tsx`. Removed from the global theme: `sky`, `sky-deep`, `sky-soft`,
`info-soft`, the blue focus ring, the blue input focus, blue links, the blue selection,
the manifest `theme_color`, and `og.png`. Focus ring: `ink` on paper, `sun` on dusk.
Brand angle: `--angle-brand: 18.4deg` (from the two cuts in `mark.svg`: 40 units across
120 up). Hatch: `--hatch-not-tested`, a repeating gradient at that angle.

Type: Newsreader variable (opsz and wght axes), latin subset, weights 300 to 500 in
use; display at 380 to 400, tracking 0, line height 1.05 to 1.15; reading at the text
optical size, 18 to 20 px, line height 1.5, measure under 68 characters. Sans: Figtree
or Hanken Grotesk, decided by a side-by-side screenshot against Manrope at the
art-direction stop. Mono: JetBrains Mono as now; labels uppercase at 0.08em. All through
`next/font/local`; no remote fonts. Scale: hero 72 to 96 / 40 to 48; headings 44 to 56 /
30 to 36; lead 20 to 22; body 17 to 18; small 13 to 14.

Vector logo: no SVG wordmark exists (`components/Logo.tsx` renders `logo-*.webp`, keyed
from `assets/suncly-black.png`). The plan is to trace `assets/suncly-black.png` with
potrace-style vectorisation at build time into `public/brand/wordmark.svg`, review the
trace at the art-direction stop, and keep the PNG path as a fallback until you accept it.
The sun mark stays exactly `public/mark.svg`.

Badge: `public/brand/badge/suncly-certified-{paper,dusk,mono}.svg` and PNGs at 64, 128,
256 and 512 px. Circular, the words "suncly certified" on a circular path converted to
outlines, the untouched mark at the centre, a fine ring, one notch at the brand angle. No
laurels, shields, stars, ribbons, ticks, medal colours or tiers; nothing like the CE mark.
Generated by `scripts/generate-badge.mjs` so it can be made again.

Pictures (`frontend/art/<name>/scene.mjs` and `README.md` each), rendered to
`public/art/<name>-{640,1280,1920}.{avif,webp}` with art-directed crops per breakpoint:

| Name | Section | Scene |
| --- | --- | --- |
| two-cards | 02 | Two identical upright cards on a pale plane; the right one's shadow does not match its shape |
| aperture | 10 | A closed box with one narrow slit and a single blade of light leaving it |
| analemma | 11 | Small brass discs pinned to a plaster wall in a figure of eight, each with its own shadow |
| specimens | 12 | Eleven small forms in a row; one wrong shadow, one with two, one with none |
| seal | 09 | The badge blind-embossed in heavy paper under raking light |
| last-light | 16 | The horizon the name stands on |

Route: a small path tracer in a Web Worker, run in headless Chromium through Playwright
at build time (`scripts/render-art.mjs`), with film grain added in sharp. The forms are
planes, boxes, discs and cylinders; the light is one directional sun at the brand angle
with a warm sky dome. If the screenshots show that this does not reach editorial
quality, I will say so and leave exact briefs to commission (subject, composition,
camera, light angle, palette, aspect ratios, file names), holding the layout with a
restrained rendered version. No stock.

Components (new): `Hero`, `WorksWith`, `HowItWorks` (with `CardStage`), `Install` (with
`InstallTabs`, `CopyButton`, `DemoOutput`), `EvidenceCard`, `UseCases`, `Offer`,
`Certified` (with `Badge`), `Data`, `Research`, `Lab` (with `SpecimenStrip`), `Stand`,
`Questions`, `ClosingSky`, `FindSuncly`, `Banner`, `Wordmark`, `Picture` (crops, alt,
dimensions, lazy loading), `Hatch`, `StatusMark`. Restyled: `Nav`, `Footer`, `Button`,
`Faq`, `SectionHeader`, `components/ui/*`, `components/evidence/*`, `components/app/*`
(tokens only, behaviour unchanged).

Data: `lib/capabilities.ts` extended with `http-api`, `usage-billing`, `certification`,
and `agent-cursor`, `agent-claude-code`, `agent-codex`, `agent-omp`, `agent-pi`, each
with a status from the inputs; `lib/launch.ts` reads the founder inputs
(`repository_visibility`, `cli`, `http_api`, `usage_billing`, `certification_programme`,
`tested_in`, `TRADEMARK_SYMBOL`, `social`) so a later change is one line;
`lib/certified/records.json` (empty at launch) drives `/certified/[id]`.

Scripts: `screenshots.mjs` extended to every page and to 1440, 1024, 768 and 390 px;
`axe.mjs` (axe-core through Playwright); `forbidden.mjs` searching `out/` for "trusted
by", "A2A certified", "AI Act compliant", "®" while unregistered, "guarantee" outside a
disclaimer, competitor names, blank-input placeholders and blue in the global theme;
`words.mjs` counting visible home-page words against the budget; `render-art.mjs`,
`generate-badge.mjs`, `trace-wordmark.mjs`.

## 6. Other pages

New: `/offer`, `/certified` (programme, badge files, usage rules, registry that says
"No agents are certified yet."), `/certified/policy`, `/certified/[id]` (static from the
empty records file; the export must build with zero records), `/data`, `/research` (index
only; notes stay out of the build), `/lab`, `/cookies`, `/legal`. A coding-agents guide
under `/docs` appears only when a tool is verified.

Existing pages take the new system: `/product` (gains the manual-review comparison table
from the old home page), `/workflows`, `/demo`, `/security` (gains the disclosure policy),
`/docs/*`, `/company`, `/access`, `/glossary`, `/privacy`, `/terms`. `/app` is restyled
through tokens only; every workspace screen is screenshotted and the `/demo` in-browser
verification is re-run. Every URL is kept. `public/.well-known/security.txt` is added.

Search surfaces updated together: `DEFINITION` in `lib/seo.ts`, JSON-LD (Organization
`sameAs` from the social object; no offers while no price exists), `llms.txt`,
`llms-full.txt`, the sitemap, the manifest, a new social preview image.

## 7. Agent Skill proposal (build only if you say yes)

A minimal Agent Skill so that the five coding agents can run Suncly with the human in
the loop. One folder, duplicated to the two paths the tools read:

```
.agents/skills/suncly/SKILL.md      read by Codex, Cursor, Pi, omp
.claude/skills/suncly/SKILL.md      read by Claude Code, Cursor, omp
AGENTS.md                           one paragraph pointing at the skill
```

The skill tells the agent to:

1. run `suncly doctor <card-url>` and stop on any failure;
2. run `suncly attest <card-url> --sandbox --export-draft contract.json` and show the
   draft test plan to the human, in full;
3. wait for the human to type their approval and their identifier; the skill states that
   it must never approve on the human's behalf, because human approval is a product rule;
4. run `suncly attest <card-url> --sandbox --contract contract.json --approve-as <the
   identifier the human typed>`;
5. run `suncly verify <report-folder>`;
6. summarise the report with its "What was NOT tested" list first, and say that exit code
   0 is not an approval.

Where the research pointers hold (section 12 records what was verified today), this one
folder serves all five tools. It lives outside `frontend/`, in its own commit. After it
exists I can perform and record the Claude Code run in `VERIFICATION.md` (version and
date); the other four need a person and change only when you update `tested_in`.

## 8. Legal page plan

Method (brief 7.1): `frontend/legal/DATA_MAP.md` from the code and the inputs;
`frontend/legal/APPLICABILITY.md` per framework with the primary source fetched that day;
the cookie table generated from an inspection of the built site (storage keys, network
requests); `frontend/legal/REVIEW.md` for counsel (clause, question, source). Every
document in full now, with blanks named in a draft notice at the top; `noindex` and the
notice are removed by one flag, `LEGAL_PUBLISHED`, once the facts exist and counsel has
signed off.

| Page | Contents | Blocked on |
| --- | --- | --- |
| `/privacy` | Three contexts kept apart: website and pilot form; the CLI (sends nothing); the hosted API, accounts and billing (switched on by launch state). Who we are; data and sources, including personal data inside transcripts; purposes and legal bases in one table; recipients and transfers; retention by category; rights, one-month deadline, complaint to the Estonian Data Protection Inspectorate; cookies as inspected; no automated decisions about people; children; security summary; controller and processor roles once hosted; changes and version history | legal entity, registered office, registry code, privacy contact, hosting regions, form endpoint and storage, subprocessors, retention periods |
| `/terms` | Parties and business use; the service and its status with pilot features labelled; accounts and keys (switched on by launch state); authority to test and the sandbox declaration; fees as usage-only, "no fees are charged yet" while billing is not live, connecting and badge free; evidence and ownership of report folders; software licence; certification by reference; confidentiality and data protection; warranties and disclaimers matching section 13; liability cap with carve-outs; changes with notice and a right to leave; term and termination; governing law and court; online conclusion | legal entity, governing law and court, billable unit and price, repository licence |
| `/certified/policy` | Issuer; private and voluntary, not an accredited conformity assessment; criteria and version; what is tested and not; validity and re-test triggers; suspension and revocation; the record as the single source of truth; badge licence; prohibited words; no pay-to-pass; corrections and appeals | block 6 (see section 9), appeals contact |
| `/cookies` | The inspected table, or the statement that the site sets none and that `/app` uses local storage only | nothing |
| `/legal` | Legal notice: company facts, VAT number, contact, the Estonian summary | legal entity, registry code, registered office, VAT number |
| `/security` | Extended with the coordinated disclosure policy and the support period; `security.txt` | security contact |

Frameworks assessed in APPLICABILITY.md (brief 7.2): GDPR; the Estonian Personal Data
Protection Act, Information Society Services Act §4, Commercial Code §15, Language Act,
Electronic Communications Act §103¹, Law of Obligations Act §§35 to 44, §106 and §1048,
Advertising Act §4, Accounting Act retention; cookie consent; the AI Act; the Cyber
Resilience Act; the Data Act and the DSA; NIS2 and DORA as buyer obligations; trade
marks (® and ™, certification mark or ordinary mark, the SUNLY clearance question); the
Linux Foundation trademark guidelines; WCAG 2.2 AA as a target with no claim under the
European Accessibility Act. UK, Swiss and US law are out, because `target_markets` is EU.
Section 12 records what the primary sources said today.

## 9. Proposed first certification profile (block 6 is blank)

Built only from checks that exist in the product today. Nothing is published until you
accept or change it; the policy page carries it as a draft.

**Criteria v0.1.** For one named agent version, identified by its `card_hash`, at a
sandbox endpoint the operator declared in writing:

1. The operator confirms it operates the agent or has the operator's permission.
2. The card declares A2A 1.0 over JSON-RPC and is served at `/.well-known/agent-card.json`.
3. Every declared skill has at least one approved test case. A skill without examples
   gets its test cases written into the contract file by the operator; a card with a
   skill nobody can write a test for is not certified.
4. A named person approved the contract; a named person at Suncly ran the evaluation
   with Suncly's deployment key, so the signature is Suncly's.
5. Each test case ran at least 5 times (the default) and the attestation ended
   `completed`: no budget stop, no card change during the run.
6. Every run passed. Zero `fail`, zero `inconclusive`. Inconclusive is never a pass, so a
   contract with `model_checks` cannot certify until Layer 2 exists.
7. `suncly verify` passes on the report folder.
8. The record lists what was not tested, taken from the report: semantic correctness,
   probes, the production endpoint, interfaces not used, declared capabilities not
   exercised.

**Validity:** 6 months, or until the `card_hash` changes, whichever is first.
**Re-test triggers:** a changed card; a changed agent version string; expiry; a
substantiated report of behaviour that contradicts the record; a new criteria version
(records keep their criteria version until expiry). **Who decides:** a named Suncly
reviewer, recorded on the record; a second person for revocations. **Corrections and
appeals:** `team@suncly.com` until you name another address. **What a badge is not:**
not the customer's approval, not a rating or a tier, not a security certification, not
legal compliance, not insurance, no guarantee of future behaviour, nothing about the
production endpoint, no endorsement by the Linux Foundation, the A2A project or any
vendor. The same sentences appear on the badge page, every record page, section 13 of the
home page, the Terms and the Policy.

## 10. Risks

1. **Picture quality without an image generator.** A code path tracer can do planes,
   boxes and discs under one sun; it may not reach the warmth of a photograph. The
   fallback is explicit briefs for commissioning, and the layout holds either way.
2. **Mobile performance with six pictures and a sky.** Mitigated by AVIF and WebP at
   three widths, lazy loading below the fold, the hero image under 120 KB at phone
   width, still images on phones, canvases loaded after first paint. If an effect costs
   the score, the effect goes.
3. **Certification is the heaviest legal item.** The Law of Obligations Act §1048
   (liability for incorrect expert information) and the Advertising Act §4 both bear
   on a badge. The limits must be on the record page itself. Whether the badge should be
   a certification mark is a question for counsel.
4. **The SUNLY trade marks of Sunly AS, Tallinn.** Clearance of the name is for counsel;
   recorded in REVIEW.md. Nothing on the site changes until counsel speaks.
5. **A public repository with no licence.** Visitors have no right to run the code they
   are told to install. The Terms bridge this with a limited licence; a real licence is
   the fix.
6. **Consistency across five documents.** Pricing model, product status, data flows and
   the meaning of certification must read the same on the home page, the product pages,
   the Terms, the Privacy Policy and the Certification Policy. A consistency check joins
   the verification.
7. **Word budget.** 800 words with sixteen sections leaves about 50 a section. Depth
   moves to the inner pages; the risk is a home page that is beautiful and vague. The
   check is the hand-back question "can a security lead say what Suncly does after one
   screen?".
8. **Session length.** This is weeks of agency work in one session. `REDESIGN_PROGRESS.md`
   is kept current so the work survives a long session or a restart.

## 11. Questions for you (one batch)

Blank inputs, in order of what they block. Everything else is built switched off and
listed in the hand-back.

1. **Legal entity name, registry code, registered office, VAT number, privacy and
   security contact addresses, governing law and court.** They block the draft label on
   `/privacy`, `/terms`, `/legal` and `/certified/policy`, and the legal line in the
   footer. Without them the pages ship complete, `noindex`, with named blanks.
2. **The five "Find Suncly" links.** All blank; the row renders empty and is listed in
   HANDOFF.md. Never a guessed handle.
3. **Billable unit, price and currency, billing period and payment method, pilot
   terms.** They block `/offer`'s unit and price and the Terms' fee schedule. The page
   ships with the model (usage only, connecting and badge free) and "no fees are charged
   yet".
4. **Certification block 6.** Accept or change the v0.1 profile in section 9. Nothing is
   published as criteria until you do.
5. **Hosting, DNS, database and regions; the pilot form endpoint and where it stores
   submissions; subprocessors; retention periods.** They block the recipients table and
   the retention table in the Privacy Policy.
6. **Vector logo.** None in the repository. I will trace `assets/suncly-black.png` and
   show the trace at the art-direction stop. If an SVG exists, give the path and the
   trace is dropped.
7. **Repository visibility and licence.** The inputs say public; confirm that is
   intended given the licence gap. Which licence, if any, is being chosen?
8. **Agent Skill (section 7).** Yes or no. If yes, I also record the Claude Code run.
9. **Status words.** Confirm the mapping of "Available with limits" to "Available" plus
   the limit sentence (section 2).
10. **Branch and push.** Confirm the work stays on `claude/sweet-ride-ku6uau` and that
    pushing to that branch only is acceptable in this cloud session.
11. **Canonical host.** `suncly.com` or `www.suncly.com`.

Not asked, because the brief decides them: the palette, the serif, the picture set, the
section order, the ™ default, the no-logo rule, the no-score rule, British spelling.

## 12. Verified in this session

Filled in from the four reads that ran in parallel (product verification in a clean
3.12 virtual environment, frontend audit and build, reference sites and research
pointers, legal primary sources). Where a line says "not verified", it was not.

### 12.1 The CLI, run here

Run on 2026-10-05 in a clean virtual environment on Python 3.12.3 (this machine's default
`python3` is 3.11, below the package's minimum, so the site must keep saying "Python 3.12
or newer"). Repository at `a0570ef`, which is the remote HEAD.

| Step | Wall clock | Result |
| --- | --- | --- |
| `python3.12 -m venv .venv` | 4.5 s | ok |
| `pip install -e .` | 20.4 s | 23 dependencies plus suncly 0.1.0 |
| `suncly --help` | 0.5 s | attest, db, demo, doctor, keys, verify |
| `suncly doctor` | 0.4 s | exit 6 on a fresh install: no deployment key yet; `suncly keys init` or the first attest creates one. The site must not promise that doctor passes before the first run. |
| `suncly demo` | 3.6 s | exit 0; two agents, 3 test cases x 3 runs each (the attest default is 5); honest agent 9 of 9 pass, lying agent 9 of 9 fail `output_modes`; both decisions `flag`; both signed; reports under `./suncly-reports/<id>/` |
| `suncly verify <folder>` | under 1 s | eight `ok` lines, "Verification passed." A changed byte in a transcript or a changed decision in `result.json` fails with the check named (exit 6). |

From clone to a signed demo report: under one minute on this machine, with the install
the longest step. The site will say "a few minutes" to allow for the clone and a slower
network; "five minutes" from QUICKSTART.md is kept as the upper bound. The full demo
output is in `scratchpad/demo-output.txt` for this session and will be committed under
`frontend/lib/install/demo-output.txt` when the Install section is built, trimmed, not
retyped. The caption for the hero's wrong shadow will be the lying agent's line, word for
word: `uppercase  hello world  run 1  fail  5 ms  fail: output_modes`.

Refusals seen live: without `--sandbox`, exit 3 and "Nothing ran: the endpoint is not
declared a sandbox or dry-run endpoint"; with `--sandbox` and no approval, the draft table
is shown and then "No approval was given. Nothing ran: the contract is not approved."

Code facts confirmed with file and line (kept for CONTENT.md): A2A 1.0 over JSON-RPC only
(`domain/a2a.py:15-22`, `core/coverage.py:87-93`); the Runner is a subprocess
(`adapters/subprocess_executor.py:27-35`); the only two network clients are the card
fetcher (`adapters/httpx_card_fetcher.py:32`) and the agent transport, which refuses any
other host (`runner/http_transport.py:77-93`); no telemetry, analytics or update check;
no model provider is called (`core/judge.py:1-8`); the Judge checks `valid_schema`,
`final_task_state`, `latency_limit`, `response_present`, `output_modes`,
`required_field`, `response_schema`, and `model_check` yields inconclusive
(`core/judge.py:134-229`); run and decision records are append-only in both stores
(`adapters/file_store.py:60-67`, migration triggers `run_append_only`,
`decision_append_only`); redaction inside the Runner (`runner/redaction.py`); Ed25519 over
RFC 8785 (`core/signing.py`); the not-tested list has three unconditional categories, so
it is never empty (`core/coverage.py:19-131`); `decide()` returns `flag` only
(`core/policy_engine.py:60-67`).

Absolute-claim tests, named: `tests/unit/test_non_negotiable_rules.py::
test_inconclusive_is_never_counted_as_a_pass`, `::test_nothing_runs_against_a_contract_
until_a_human_has_approved_it`, `::test_dr_003_secrets_never_leave_the_runner`,
`::test_dr_006_tests_hit_only_a_declared_sandbox`, `::test_dr_007_reports_state_what_was_
not_tested`, `::test_suncly_never_writes_an_approve_decision`;
`tests/unit/test_architecture.py::test_only_the_runner_reads_the_credential`;
`tests/e2e/test_mock_agents.py::test_leaky_agent_cannot_make_the_credential_appear_anywhere`.

The eleven mock agents, from `BEHAVIOURS` (`behaviours.py:377-389`), with the outcome the
code states: honest (every run passes), honest-async (every run passes after polling
GetTask), unreachable (no run passes; runs are inconclusive), lying (every run fails the
output_modes check), flaky (odd calls pass, even calls fail), slow (every run fails the
latency limit), direct-message (handled without error; not a pass), interrupted (recorded
as fail; never a pass), leaky (the credential appears in no transcript, report or log),
card-changer (the attestation ends invalidated), no-examples (the skill without examples
is listed as not tested).

Repository access: `git ls-remote https://github.com/Suncly-Tech/Suncly.git` succeeds
without credentials and the GitHub API reports `visibility: public`, `license: null`. No
`LICENSE` file exists. No coding-agent integration exists (no SKILL.md, AGENTS.md,
CLAUDE.md, `.claude/`, `.agents/`, `.cursor*`, MCP code).

`python tasks.py check`: exit 0 in 56 s. ruff clean, mypy clean (100 files), pytest 266
passed and 15 skipped (the Postgres tests need `DATABASE_URL`), coverage 90.12%.

### 12.2 The frontend, built here

`npm ci` 16 s, `npm run typecheck` clean, `npm run build` 41 s, 23 static routes. Next 16
no longer prints first-load JavaScript; measured from `out/index.html`, the home page
loads 13 scripts, about 605 KB raw and 189 KB gzipped in a modern browser (plus a 113 KB
legacy polyfill for old browsers), with 47.7 KB of inlined CSS and three font preloads.
That is the ceiling for the new home page's initial JavaScript.

Home page today: about 1,830 visible words (Hero 103, Problem 131, ClaimChain 227,
Process 205, ManualComparison 206, Coverage 166, Scope 314, FAQ 364, FinalCta 48, nav and
footer 68). Blue lives in the `sky*` and `info-soft` tokens, the focus ring, the input
focus ring, prose links, the info badge and notice tones, the import drag state, the
selected table row, the manifest and layout `themeColor`, `favicon.svg` tiles, `og.png`,
`Hero.tsx`, `Sky.tsx` and `scripts/generate-assets.mjs`. Selection is already yellow.

Assets: the four PNGs in `assets/` are 2168 x 725 RGB with solid backgrounds (black, blue,
purple, white); none is transparent. `public/brand/logo-*.webp` are 384 x 91 lockups keyed
from the black PNG. No vector wordmark exists anywhere.

Stale scripts to fix during the build: `screenshots.mjs` waits 9 s for a terminal
animation that no longer exists and shoots only three widths; `keyboard.mjs` asserts a
"Get early access" label that is now "Request pilot access"; `generate-assets.mjs` and
`generate-logo.mjs` both write `og.png`.

Live site: `https://www.suncly.com` and `https://suncly.com` could not be fetched from this
container (the egress proxy refuses the host), so the live build was not compared with
the repository and the canonical host could not be confirmed. The brief asked for a look
at the live site at desktop and phone widths; that did not happen here and is listed
under "not tested" in `VERIFICATION.md` at hand-back. If the environment's network policy
allows `suncly.com`, the check runs then.

### 12.3 References and research pointers

Reference sites: of the ten in the brief, only claude.com and anthropic.com could be
fetched from this container; lightspark.com, alven.ai, zobi.com, blume.codes, arcade.dev,
exa.ai, browserbase.com and resend.com were refused by the network policy, as were the
three further candidates (linear.app, workos.com, modal.com). So the study of computed
type and colour at 1440 and 390 px that the brief asks for did not happen here. Your notes
in brief 4.2 and the two fetched pages are the reference base for the art-direction
round; what search snippets added is secondary and marked so in
`scratchpad/research-references.md`. Two points from the fetched pages: claude.com sets
its hero serif at weight 330 on `#f8f8f6` and anthropic.com sets `#141413` ink on
`#faf9f5` ivory with cream and black bands; both already own the light-serif-on-cream
hero, so Suncly's distinction has to come from the gold and amber light, the brand angle
and the pictures, not from weight alone. If the environment is given access to those
hosts, the study runs at the start of phase 2.

Coding agents, from primary sources where reachable (Claude Code docs fetched; the Codex,
oh-my-pi and Pi repositories read on GitHub; Cursor docs from snippets only):

| Tool | `.agents/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` | `AGENTS.md` | MCP |
| --- | --- | --- | --- | --- |
| Cursor | yes (snippet) | yes, for compatibility (snippet) | yes (snippet) | not verified today |
| Claude Code | no: the docs list only `.claude/skills` and say `.agents/` is not read | yes | yes (when no CLAUDE.md is present, or with the setting that reads both) | yes (`.mcp.json`) |
| Codex | yes (`AGENTS_SKILLS_SUFFIX = ".agents/skills"` in the source) | not found in the source; not verified | yes | yes |
| omp (oh-my-pi; the binary is `omp`, written lowercase) | yes | yes | yes | yes |
| Pi (capital P in prose; the command is `pi`; repository now `earendil-works/pi`) | yes | no: zero matches in the source | yes | yes |

So the brief's pointer holds: one skill folder at `.agents/skills/suncly/` reaches Codex,
Cursor, Pi and omp, and a copy at `.claude/skills/suncly/` reaches Claude Code, Cursor and
omp. Pi's homepage wording and the exact Cursor and Codex page texts were not fetched.

Trade marks: the EUIPO, TMview, WIPO and Estonian Patent Office databases were refused
(and are JavaScript applications in any case). Web search finds no trade mark, company or
domain for the exact string "Suncly"; absence in search is not a register search. For
"SUNLY", Sunly AS (Tallinn, registry code 14695483) is confirmed as a company; its EU or
Estonian registrations and classes were not found by search. Both points go to counsel in
REVIEW.md.

Linux Foundation: the trademark usage page was refused; its rules are known from
snippets (adjective use, no alteration, no greater prominence than our own name, no
implied endorsement). The A2A repository is Apache-2.0 and publishes no attribution
wording of its own. Proposed footer line: "Agent2Agent (A2A) is an open protocol hosted by
The Linux Foundation. Suncly is independent and is not affiliated with, endorsed by or
certified by The Linux Foundation or the A2A project. Other names belong to their
owners." To be checked against the page on the day it becomes reachable.

Fonts (from the google/fonts repository metadata, fetched): Newsreader is OFL with `opsz`
6 to 72 and `wght` 200 to 800; Figtree OFL, `wght` 300 to 900; Hanken Grotesk OFL, `wght`
100 to 900; JetBrains Mono OFL 1.1. All four may be self-hosted.

### 12.4 Legal primary sources

The environment's network policy denied every legal-source host tried on 2026-10-05:
riigiteataja.ee, eur-lex.europa.eu, aki.ee, edpb.europa.eu, euipo.europa.eu,
legislation.gov.uk and linuxfoundation.org. Only raw.githubusercontent.com answered. So
the research notes in this session rest on search-engine snippets of the cited pages,
each marked "snippet-verified" or "not verified", and every statutory quotation must be
re-checked against the fetched primary page before a legal page loses its draft label.
APPLICABILITY.md will carry the same marks until the hosts are reachable (see section 0
for how to allow them). What the snippets support:

| Framework | Applies today? | What it asks of the site |
| --- | --- | --- |
| GDPR Arts 12 to 14, 28, 33, 77 | Yes, for the pilot form | Controller identity, purposes and bases, recipients, transfers, retention, rights, one-month answer, complaint to Andmekaitse Inspektsioon (Tatari 39, 10134 Tallinn, info@aki.ee); Art 28 agreements with the form, mail and hosting vendors |
| Estonian Personal Data Protection Act | Supplementary | AKI as the authority; nothing beyond GDPR for Suncly |
| Information Society Services Act §4; Commercial Code §15 | Yes | Name, registry code and register, address, e-mail; VAT number if registered; the business name, seat and register code on the website |
| Language Act §16 | Yes, one paragraph | A summary in Estonian of the field of activity on a foreign-language site of an Estonian-registered company; applies to B2B sites too |
| Electronic Communications Act §103¹ | Yes, if leads are e-mailed | Prior consent for natural persons; an opt-out in every message, including to legal persons |
| Law of Obligations Act §§35 to 44, §106, §1048 | Once terms exist | Standard-terms control applies between businesses; no exclusion of liability for intent; "unreasonable" exclusions void; §1048 makes incorrect expert information unlawful, which bears on a badge and asks for scope, date, version and correction duties |
| Advertising Act §4 | Yes | No misleading claims, including of recognition or approval |
| Accounting Act §12 | Once an invoice exists | Seven-year retention of source documents |
| Cookie consent (ePrivacy Art 5(3), enforced by AKI through GDPR) | Yes, if anything non-essential is stored | A static site with no cookies may state that fact; `/app` local storage is essential to its function and is disclosed |
| AI Act, as amended by the Digital Omnibus on AI (2026/1744, in force 27 July 2026 per secondary sources) | Not today | Suncly is neither provider nor deployer of a tested agent; it becomes a provider of a component once a model-based judge ships. Never "CE", "conformity assessment", "notified body", "AI Act compliant" |
| Cyber Resilience Act | Conditionally | Reporting duties live since 11 September 2026 for products in scope; a free CLI outside commercial activity is out of scope; once the CLI is the client of a paid API it is likely in scope. `security.txt`, a disclosure policy and a support period are the sensible preparation |
| Data Act Chapter VI | At API launch | Switching and export terms; no switching charges from 12 January 2027 |
| DSA | No | A registry authored by Suncly is first-party content, not a hosting service |
| NIS2, DORA | Bind buyers | `/security` answers a supplier questionnaire: measures, incident notice, data location, sub-processors, exit |
| European Accessibility Act | No (B2B, microenterprise) | WCAG 2.2 AA stays the target; no claim under the Act |
| Trade marks | Yes | ™ until a registration exists; ® on an unregistered mark is misleading advertising in the EU, an offence in the UK (TMA 1994 s.95) and evidence of deceptive intent in the US. EUTMR Art 83: a certification mark's owner must not supply the certified kind of goods or services; Suncly tests agents and does not supply them, so it could hold one. Whether to file is for counsel; so is the SUNLY clearance |
| Linux Foundation trademark usage | Yes | Full form on first reference, no greater prominence than our own name, no altered logos, attribution and no-affiliation line; the A2A repository carries no project-specific trademark policy |

Also noted: the environment could not reach the EUIPO, USPTO or Estonian Patent Office
registers, so the register check the brief cites for 5 October 2026 was not repeated
here; the default ™ stands on the inputs (`suncly_trade_mark: unregistered`).

## 13. Next steps after your go-ahead

1. Art direction: three directions as quick drafts (hero at 1440 and 390 px, footer
   banner), the wordmark trace, a recommendation, and the sans side-by-side. Stop two.
2. Foundations: tokens, type, grid, vector logo, badge, picture pipeline, core components.
3. Home page, one section at a time in the order of section 4; build, screenshot at four
   widths, look, fix, commit.
4. The other pages and the legal pages.
5. Verification and hand-back, including two fresh review subagents.
