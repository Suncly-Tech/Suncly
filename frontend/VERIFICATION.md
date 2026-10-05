# Verification log

How the rebuilt site was checked on 2026-10-05, what passed, what failed, and what was not
tested. Every command below ran in the build session on the final build of the branch;
where a thing could not be run here, it says so. Scripts are registered in `package.json`
and need the static export served on port 3100 (`npm run build && npm run serve`).

## Commands

```bash
npm run typecheck        # tsc --noEmit: clean
npm run build            # next build --webpack: 32 static routes, no warnings
npm run serve            # serve out/ with clean URLs, gzip and cache headers on :3100
npm run screenshots      # every public page and the workspace at 1440, 1024, 768 and 390 px
npm run words            # visible words on the home page against the 800 budget
npm run forbidden        # scan out/ for things that must not ship
npm run axe              # axe-core, WCAG 2.2 AA rules, every page, desktop and phone
npm run keyboard         # tab order, focus ring, tabs, copy button, mobile menu, skip link
npm run functional       # links, navigation, install tabs, copy, specimen strip, /demo, /app
npm run inspect-storage  # cookies, storage keys and request hosts in the built site
npm run lighthouse       # Lighthouse mobile and desktop on / and /docs
npm run lcp-probe        # Lighthouse mobile on /, simulated and devtools throttling side by side
npm run lcp-graph        # Lighthouse's own Lantern graph for the simulated LCP, with what-ifs
python tasks.py check    # the repository's own ruff, mypy and pytest
```

## Results

| Check | Result |
| --- | --- |
| `npm run typecheck` | clean |
| `npm run build` | 32 routes, all static; the export builds with zero certification records (one `specimen` record page, noindex) |
| `npm run words` | 779 visible words on the home page (budget 800), counted per section: hero 47, works with 38, how it works 96, install 64, evidence 63, use cases 90, offer and certified 82, data 54, research 49, lab 67, scope 110, questions 18, closing 7. Navigation, code, collapsed answers, tables, the footer and the legal line are excluded |
| `npm run forbidden` | 39 files checked, 0 problems: no "trusted by", "A2A certified", "AI Act compliant", ®, "guarantee" outside a disclaimer, competitor name, placeholder, published price, "official" or "accredited" certification, or blue in the theme |
| `npm run axe` | 24 pages (the specimen record included since stage 5) at 1440 and 390 px: no violation of any impact |
| `npm run keyboard` | 14 of 14 checks pass: skip link first, visible focus ring, primary action, install tabs (arrow keys move the selection), copy button announces "Copied", specimen strip, FAQ summaries, Find Suncly links, mobile menu opens from the keyboard, focus trapped, Escape closes |
| `npm run functional` | 22 of 22 checks pass: 31 internal link targets return 200 and every anchor has a target on its page; the five primary links open their pages and the Install button jumps to `#install`; six install tabs, a tool tab shows Planned, the Terminal tab returns with its code block, the Windows toggle shows the PowerShell line, the copy button copies exactly the shown commands and announces success; the specimen strip reports the lying agent; on `/demo` the Signature tab controls a panel with the matching id and the in-browser verification runs with every check passing; the sample loads into the workspace, the overview shows it, the evaluation opens, the review form announces its validation errors, settings renders the clear action; no page errors |
| `npm run inspect-storage` | cookies: none; sessionStorage: none; localStorage before any action: none; after loading the sample into the workspace: `suncly.workspace.v1`; request hosts: the site only; third-party hosts: none |
| `npm run lighthouse`, `npm run lcp-probe` | see the next section |
| `python tasks.py check` | ruff clean (the `frontend/scripts/generate-badge.py` included), mypy clean (100 files), pytest 266 passed, 15 skipped (Postgres tests need `DATABASE_URL`), coverage above the 85% threshold. Run before stage 4; no Python file changed since. `src/` and `tests/` are unchanged |
| Horizontal overflow | none on any page at any of the four widths (the screenshot script reports `scrollWidth` beyond the viewport; stage 4 found and fixed an overflow at 1024 px from pictures whose minimum height was being transferred into their width) |
| Draft pages | `/privacy`, `/terms`, `/legal` and `/certified/policy` render the draft notice and `<meta name="robots" content="noindex, nofollow">`; so does `/certified/specimen` |

Accessibility fixes made during the runs: tab panels carry the ids their tabs point to
(`aria-controls` only on the selected tab) on the home page and, since stage 4, on every
tab of the evaluation view (`/demo`, `/app`); the tertiary grey was darkened to pass
contrast on paper; amber eyebrows became ember; scrollable tables and the demo output
block are focusable and labelled; the workspace empty state's heading level; the Find
Suncly links' accessible names include their visible abbreviation.

## Lighthouse (13.5, served from `out/` with gzip, Chromium headless)

The brief's targets: accessibility 100 and desktop performance 100 as floors, mobile
performance at least 90, LCP under 2.5 s, CLS under 0.1. Two kinds of figure appear below
and they must not be confused:

- **Simulated** (the default, what the Lighthouse score uses): the page is loaded once on a
  fast connection, and the metrics are *estimated* for a slow 4G link (1.6 Mbps, 150 ms
  round trip) and a 4× slower CPU from the recorded dependency graph.
- **Observed**: the metric as the browser actually reported it, either in the same
  unthrottled load ("observed LCP") or in a load made through a real throttled network and
  CPU ("devtools throttling", `npm run lcp-probe`).

### Full set, final build

| Page | Form factor | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- | --- |
| `/` | mobile | 91 (this run; 92, 95, 95 in three further quiet runs on the same build) | 100 | 100 | 100 |
| `/` | desktop | 100 | 100 | 100 | 100 |
| `/docs` | mobile | 95 | 100 | 100 | 100 |
| `/docs` | desktop | 100 | 100 | 100 | 100 |

### Mobile home page, metrics

| Metric | Simulated (score basis) | Devtools throttling (observed) | Unthrottled (observed) | Target |
| --- | --- | --- | --- | --- |
| Performance score | 91 to 95 (four runs; median 95) | 90 | | ≥ 90 |
| First Contentful Paint | 1.0 s | 1.15 s | | |
| Largest Contentful Paint | **2.87 to 2.91 s** | 1.36 s | 0.12 to 0.18 s | < 2.5 s |
| Total Blocking Time | 82 to 224 ms | 409 ms | | |
| Cumulative Layout Shift | 0 | 0.0004 | 0 | < 0.1 |
| Speed Index | 1.0 s | | | |
| Time to Interactive | 2.9 s | 5.8 s | | |

The LCP element is the hero picture (`/art/two-cards-1280.avif`, 5 KB, preloaded with
`fetchpriority=high`, discoverable in the document, not lazy). Its observed breakdown is
8 ms to first byte, 16 ms load delay, 13 ms load, 105 ms render delay.

**What passes and what fails.** Mobile performance passes the 90 target but sits close to
it: individual runs on the same build vary by four points with the container's CPU, so
treat the figure as "about 93, never below 90 in the session". CLS passes with room to
spare. Accessibility and desktop performance meet their floors. **The simulated LCP fails
the 2.5 s target by about 0.4 s**; the observed LCP passes under devtools throttling
(1.36 s) and unthrottled (0.18 s). The failing figure is not dismissed because the
observed one is faster: it was investigated and reduced, as follows.

**Why the simulation says 2.9 s.** Lighthouse's estimate for an image LCP averages an
optimistic graph (about the first paint, 1.0 s) with a pessimistic one that charges every
request started before the observed paint to the LCP. Everything the page needs starts
within 50 ms of the document, so that set is the document itself (59 KB gzipped, half of
it the React Server Components payload that hydration needs), the three fonts (80 KB),
seven framework and page scripts (158 KB) and the picture (5 KB). Over the simulated link
that is about 4.7 s, and the average lands at 2.9 s whatever the picture itself costs.

**What was done about it** (the previous build measured 3.07 s simulated, 1.39 s devtools,
score 88 to 91):

- The fonts were cut from 117 KB to 80 KB: Newsreader's optical-size axis restricted to
  18 to 72 (the sizes the site sets) with `fontTools.varLib.instancer`, JetBrains Mono
  shipped as a single regular face (every mono label on the site is set at 400), Figtree
  unchanged.
- The traced wordmark path (4 KB) is written into the document once per page and reused
  with `<use>` by the footer lockup, the banner and its light mask; the home document
  went from 63 KB to 59 KB gzipped.
- Earlier in the build: the animation library was removed in favour of a CSS reveal, the
  hero picture is preloaded with the same `srcset` and `sizes` as the element, the hero
  animation is transform-only so the picture paints at once, Newsreader's weight axis was
  pinned.

**Why it is still 2.9 s, from Lighthouse's own model** (`npm run lcp-graph`, final build,
output kept in `lighthouse/lcp-graph.txt`). Lighthouse's LCP is the average of an
optimistic and a pessimistic simulation of the page's dependency graph, floored at FCP;
for this page both come to 2.89 s because both treat every request that starts before
the observed paint as render-blocking. The simulated timeline is:

| Simulated ms | Node | KB |
| --- | --- | --- |
| 0 to 903 | the document (half of it the React Server Components payload) | 58 |
| 903 to 1206 | the hero picture, preloaded | 5 |
| 903 to 2256 | the three fonts, sharing the 1.6 Mbps link | 79 |
| 975 to 2710 | seven scripts, the two framework chunks last | 155 |
| 2710 to 2892 | the first evaluation of the React runtime, which performs layout before the observed paint and so counts as render-blocking | |

Re-simulating the same graph with resources removed, nothing else changed:

| Graph | Simulated LCP |
| --- | --- |
| as built | 2.89 s |
| without the three fonts | 2.63 s |
| without every script | 2.74 s |
| without the two framework chunks only | 2.89 s (the smaller scripts and the runtime evaluation remain) |
| without every font and every script | 2.55 s |

So the earlier estimate that "about 140 KB" had to go was wrong: even an empty-handed
page (no fonts, no scripts) simulates at 2.55 s, because the document's 0.9 s and the
layout work after it are most of the figure. The levers that remain are the document's
size and the simulation's own constants.

**The one small fix tested, and rejected.** Serving the stylesheet as an external file
instead of inlining it (`experimental.inlineCss: false`) removes the stylesheet's second
copy from the server-component payload: the document fell from 58 KB to 34 KB gzipped
and the simulated LCP from 2.89 s to 2.80 s (three runs: 2.80, 2.84, 2.80; score 94 to
95). But under devtools throttling the observed first paint and LCP went from 1.15 s and
1.36 s to 1.88 s and 1.88 s, because the render-blocking stylesheet request now costs a
round trip before anything paints, and a layout shift of 0.026 appeared. A tenth of a
second in the simulation is not worth half a second on a real slow connection, so the
inlined CSS stays. No other change inside the current stack (Next.js and the chosen fonts
are fixed by the brief) was found that moves the simulated figure without a cost
elsewhere, and optimising stopped there. **The simulated LCP target is recorded as
failed.** The observed LCP passes under both devtools throttling (1.36 s) and no
throttling (0.12 to 0.18 s).

## Screenshots

`screenshots/<page>-<width>.png` for every public page and three workspace screens at
1440, 1024, 768 and 390 px, plus the open mobile menu at 390 and 768, with 1000 px tiles
under `screenshots/tiles/`. Inspected by the builder, section by section, at all four
widths in stage 4; the fixes that followed: pictures made block-level with their width
from the column (the Data picture had overlapped the copy, then the Research and Lab
pictures overflowed at 1024), the Offer and Certified band restructured (412 px tall at
1440, two columns from 768), the `suncly demo` output kept unwrapped from tablet width
with horizontal scroll, the closing headline set one sentence per line. The hand-back
images (`home-1440.png`, `home-390.png`, `home-390-menu.png`, `offer-1440.png`) are
copied to `design/handback/`.

## The CLI, run here (unchanged from the plan's section 12.1)

Clean Python 3.12 virtual environment, repository at the build commit. `pip install -e .`
20 s; `suncly --help` 0.5 s; `suncly doctor` exits 6 before a key exists (as documented);
`suncly demo` 3.6 s, two agents, 3 test cases × 3 runs each, honest 9 of 9 pass, lying
9 of 9 fail `output_modes`, both decisions `flag`, both signed; `suncly verify` passes
eight checks and names the failed check after a changed byte. The Install section's
output is the trimmed capture of that run. The Windows variant of the commands was not run.

## Browser review

Chromium only (Playwright's build). Checked by script (`npm run functional`, above) and by
eye: every public page at four widths; `/demo` switches evaluations and the Signature
tab's in-browser verification passes every check with the sample; `/app` empty state,
settings, new-evaluation form, the review form's validation; the sample loads into the
workspace from `/demo`; the install tabs, OS toggle and copy buttons; the specimen strip;
the FAQ; the closing sky's layers pause off screen and stay still under reduced motion
(checked in the first pass; that component's only stage-4 change is the headline markup);
the footer banner's edge light runs once; the shared wordmark definition renders in the
navigation, the footer lockup and the banner on every page.

## Stage 5: inner pages and legal drafts

- **Routes against section 6 of the brief.** Every page the brief lists exists and builds
  (`HANDOFF.md` §8). Two are conditional in the brief and are deferred because their
  condition is unmet: the research note pages (no note is published) and the coding-agents
  guide under `/docs` (no tool is verified). Nothing is missing.
- **Layouts inspected** from the final screenshots at 1440 and 390 px: `/offer`,
  `/certified`, `/certified/policy`, `/certified/specimen`, `/data`, `/research`, `/lab`,
  `/cookies`, `/legal`, `/privacy`, `/terms`, `/product`, `/workflows`, `/demo`,
  `/security`, `/docs`, `/docs/getting-started`, `/docs/cli`, `/docs/evidence`,
  `/company`, `/access`, `/glossary`, `/app`, `/app/new`, `/app/settings`. Fixes: the Lab
  table's agent names no longer break mid-word on phones; `/docs/getting-started` clones
  from the repository's current remote and no longer says repository access comes with the
  pilot.
- **Legal drafts read against the product, the data flows, the pricing state and the
  certification state.** Consistent on: no hosted service, no accounts, no billing, no
  price, flag-only decisions, the tool sends nothing to Suncly, one local-storage key, no
  cookies, no criteria adopted, no record issued, badge free, repository public with no
  licence. Four wording fixes: the Certification Policy's §11 summary promised an answer
  within one month while its body leaves response times blank; the Terms' certification
  section now says no criteria are published and no record exists; the legal notice now
  presents the Estonian Acts as our reading for counsel to confirm; the security page and
  `security.txt` say the contact is the general address, not yet confirmed for security
  reports. Every drafted period or amount (notice periods, dispute answers, confidentiality
  term, badge removal, liability cap) is listed in `legal/REVIEW.md` as a founder or counsel
  decision. No legal verification is claimed: every primary source remains unreachable.
- **Draft state.** Four legal drafts, `/privacy`, `/terms`, `/legal` and
  `/certified/policy`, carry the draft notice naming their missing facts and
  `<meta name="robots" content="noindex, nofollow">` in the export, both controlled by
  `launch.legalPublished`. A fifth page, `/certified/specimen`, is also noindex (because
  `records.json` is empty) and is labelled a fictional specimen, but it is not a legal
  draft and carries no draft notice. None of the five is in the sitemap. `/cookies` is
  indexable and factual.
- **The security reporting address.** `team@suncly.com` was the previous site's general
  contact (six files at the pre-redesign commit) and is `site.email` and
  `company.contactEmail` now. `company.securityContactEmail` is blank. Whether the founders
  want security reports at that address is unknown and is flagged in `HANDOFF.md` §4a.

## Acceptance against the stage-4 brief

| Item | Status | Evidence |
| --- | --- | --- |
| Sixteen home sections in the brief's order | pass | `app/page.tsx`; screenshots |
| Home page at or under 800 visible words | pass | `npm run words`: 779 |
| Inspected at 1440, 1024, 768, 390; no horizontal overflow | pass | `npm run screenshots`; stage-4 overflow probe at the four widths |
| Offer, Data, Research and Lab read as distinct | pass | distinct headlines, pictures and sources (`CONTENT.md`) |
| Install reachable from the home page | pass | nav Install → `#install` (`npm run functional`) |
| Capability and status labels true | pass | generated from `lib/capabilities.ts`; `npm run forbidden` |
| Social links accessible | pass | 44 px rings, accessible names, keyboard check; destinations themselves unverified (below) |
| Interactions, reduced motion and URLs preserved | pass | functional and keyboard checks; every previous route builds |
| Mobile Lighthouse performance ≥ 90 | pass, narrowly | 91 to 95 simulated across four runs; 90 devtools |
| LCP < 2.5 s | **fail (simulated)**, pass (observed) | 2.87 to 2.91 s simulated across seven runs; 1.36 s devtools; 0.12 to 0.18 s unthrottled; cause shown by `npm run lcp-graph` |
| CLS < 0.1 | pass | 0 simulated and unthrottled; 0.0004 devtools |
| Accessibility 100; desktop performance 100 | pass | Lighthouse on `/` and `/docs`; axe on 23 pages |
| Unapproved certification criteria kept internal | pass | `REDESIGN_PLAN.md` §9 only; `/certified/policy` says none adopted |
| Specimen record clearly fictional, no real agent implied | pass | `/certified/specimen`: "Specimen record (fictional)", "certifies nothing", noindex |
| Legal pages visibly draft and noindex | pass | draft notice and robots meta on `/privacy`, `/terms`, `/legal`, `/certified/policy` |
| No invented contacts or promises in `security.txt` and the disclosure policy | pass, with a flag | contact is the site's existing general address, stated as not yet confirmed for security reports; no acknowledgement, fix-time, safe-harbour, credit or incident-notice promise |
| Security reporting address founder-authorised | unverified | `securityContactEmail` is blank; founder decision needed |
| Legal drafts consistent with the product, data flows, pricing and certification state | pass | stage 5 read; four wording fixes above |
| Legal applicability verified against primary sources | unverified | every source unreachable (`legal/APPLICABILITY.md`) |
| `/demo` signature verification | pass | in-browser verification, every check passing (`npm run functional`) |
| `/app` behaviour | pass | sample load, overview, evaluation, review form errors, settings |
| Navigation, install tabs, copy buttons, links | pass | `npm run functional`: 31 targets, every anchor, six tabs, exact clipboard text |
| The four social destinations resolve | unverified | network policy refuses x.com, linkedin.com, reddit.com; github.com answers only for the configured repository |
| Live site comparison | unverified | `www.suncly.com` refused by the network policy |
| Firefox, Safari, real devices, screen readers | unverified | Chromium only |

## Not tested

- The live site at `www.suncly.com`: refused by the environment's network policy, so the
  old build was not compared with this one and the canonical host is unconfirmed.
- The four Find Suncly destinations: x.com, linkedin.com and reddit.com are refused by
  the network policy; github.com answers only for the configured repository. Linked
  exactly as supplied, unverified.
- Platform brand-guideline pages (X, LinkedIn, GitHub, Reddit): unreachable, so the row
  uses text abbreviations.
- Every primary legal source (see `legal/APPLICABILITY.md`): unreachable; the legal
  drafts rest on secondary snippets and are marked as such.
- Firefox and Safari rendering; real phones; screen readers beyond axe's rules.
- The Windows PowerShell install commands.
- Importing a real report folder through the file picker (no file-system access from
  the automation); the pilot form against a live endpoint (none configured).
- Browsers without Ed25519 in WebCrypto.
- Coding-agent runs: none performed, none claimed (`tested_in` is "no" for all five).
- The two fresh-eyes review passes the brief asked for were not run: the founder asked
  for one agent and no subagents.
