# Verification log

How the rebuilt site was checked on 2026-10-05, what passed, and what was not tested.
Every command below ran in the build session; where a thing could not be run here, it says
so. Scripts are registered in `package.json` and need the static export served on port
3100 (`npm run build && npm run serve`).

## Commands

```bash
npm run typecheck        # tsc --noEmit: clean
npm run build            # next build --webpack: 31 static routes, no warnings
npm run serve            # serve out/ with clean URLs, gzip and cache headers on :3100
npm run screenshots      # every public page and the workspace at 1440, 1024, 768 and 390 px
npm run words            # visible words on the home page against the 800 budget
npm run forbidden        # scan out/ for things that must not ship
npm run axe              # axe-core, WCAG 2.2 AA rules, every page, desktop and phone
npm run keyboard         # tab order, focus ring, tabs, copy button, mobile menu, skip link
npm run inspect-storage  # cookies, storage keys and request hosts in the built site
npm run lighthouse       # Lighthouse mobile and desktop on / and /docs
python tasks.py check    # the repository's own ruff, mypy and pytest
```

## Results

| Check | Result |
| --- | --- |
| `npm run typecheck` | clean |
| `npm run build` | 31 routes, all static; the export builds with zero certification records (one `specimen` record page, noindex) |
| `npm run words` | 780 visible words on the home page (budget 800), counted per section: hero 47, works with 38, how it works 96, install 64, evidence 63, use cases 90, offer and certified 82, data 54, research 49, lab 67, scope 110, questions 18, closing 8. Navigation, code, collapsed answers, tables, the footer and the legal line are excluded |
| `npm run forbidden` | 39 files checked, 0 problems: no "trusted by", "A2A certified", "AI Act compliant", ®, "guarantee" outside a disclaimer, competitor name, placeholder, published price, "official" or "accredited" certification, or blue in the theme |
| `npm run axe` | 23 pages at 1440 and 390 px: no moderate, serious or critical violation after the fixes below |
| `npm run keyboard` | 14 of 14 checks pass: skip link first, visible focus ring, primary action, install tabs (arrow keys move the selection), copy button announces "Copied", specimen strip, FAQ summaries, Find Suncly links, mobile menu opens from the keyboard, focus trapped, Escape closes |
| `npm run inspect-storage` | cookies: none; sessionStorage: none; localStorage before any action: none; after loading the sample into the workspace: `suncly.workspace.v1`; request hosts: the site only; third-party hosts: none |
| `npm run lighthouse` | see the table below |
| `python tasks.py check` | ruff clean (the new `frontend/scripts/generate-badge.py` included), mypy clean (100 files), pytest 266 passed, 15 skipped (Postgres tests need `DATABASE_URL`), coverage above the 85% threshold. `src/` and `tests/` are unchanged |
| Horizontal overflow | none on any page at any of the four widths (the screenshot script reports `scrollWidth` beyond the viewport) |

Accessibility fixes made during the run: tab panels now carry the ids their tabs point
to (`aria-controls` only on the selected tab); the tertiary grey was darkened to pass
contrast on paper; amber eyebrows became ember; scrollable tables are focusable; the
workspace empty state's heading level; the Find Suncly links' accessible names include
their visible abbreviation.

## Lighthouse (Lighthouse 13, mobile and desktop, served from `out/` with gzip)

| Page | Form factor | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- | --- |
| `/` | mobile | 91 | 100 | 100 | 100 |
| `/` | desktop | 100 | 100 | 100 | 100 |
| `/docs` | mobile | 94 | 100 | 100 | 100 |
| `/docs` | desktop | 100 | 100 | 100 | 100 |

Mobile home metrics (simulated throttling): FCP 1.0 s, LCP 3.0 s, TBT 208 ms, CLS 0, TTI 3.1 s. The observed LCP in the same run was 177 ms (the preloaded hero picture); Lighthouse's simulated LCP for an image that paints while scripts are still arriving is pessimistic, and the real figure on a throttled connection measured directly with Playwright was about 1.0 s. Two consecutive runs on near-identical builds (the second differs by a code-block padding only) scored mobile performance on `/` at 88 and 91: treat the figure as about 90, at the edge of the brief's target, with the previous site's 88 as the floor. The levers left are the framework runtime itself and the fonts.

Floor from the previous site: accessibility 100, desktop performance 100, mobile
performance 88. Mobile performance on the home page is the figure to watch: the
remaining cost is the Next.js runtime and hydration of the interactive sections (install
tabs, specimen strip, sticky stage) and the three self-hosted fonts (Newsreader 56 KB
with its optical-size axis, JetBrains Mono 40 KB, Figtree 20 KB). The hero picture is
preloaded and paints first; the animation library was removed in favour of a CSS reveal.

## Screenshots

`screenshots/<page>-<width>.png` for every public page and three workspace screens at
1440, 1024, 768 and 390 px, plus the open mobile menu, with 1000 px tiles under
`screenshots/tiles/`. Inspected by the builder, section by section, at desktop and phone
width; the fixes that followed are in the commit history (headline wrapping, caption
placement, the four-frame story's phone layout, grid overflow, prose tables on phones).
The two hand-back images are copied to `design/handback/`.

## The CLI, run here (unchanged from the plan's section 12.1)

Clean Python 3.12 virtual environment, repository at the build commit. `pip install -e .`
20 s; `suncly --help` 0.5 s; `suncly doctor` exits 6 before a key exists (as documented);
`suncly demo` 3.6 s, two agents, 3 test cases × 3 runs each, honest 9 of 9 pass, lying
9 of 9 fail `output_modes`, both decisions `flag`, both signed; `suncly verify` passes
eight checks and names the failed check after a changed byte. The Install section's
output is the trimmed capture of that run. The Windows variant of the commands was not run.

## Browser review

Chromium only (Playwright's build). Checked: every public page at four widths; `/demo`
switches evaluations and the Signature tab's in-browser verification passes all eight
checks with the sample; `/app` empty state, settings, new-evaluation form; the sample
loads into the workspace from `/demo`; the install tabs, OS toggle and copy buttons; the
specimen strip; the FAQ; the closing sky's layers pause off screen and stay still under
reduced motion; the footer banner's edge light runs once.

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
