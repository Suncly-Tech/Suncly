# Verification log

How the site was checked before the branch was handed over, and how to repeat it.

## Commands

```bash
npm run build                 # static export to out/ (webpack bundler, zero warnings)
node scripts/serve.mjs 3100   # serve out/ with clean URLs, gzip and cache headers
node scripts/screenshots.mjs http://localhost:3100   # full-page captures at 1440 / 1024 / 390 (+ tiles)
node scripts/keyboard.mjs http://localhost:3100      # keyboard-only navigation checks
node scripts/lighthouse.mjs http://localhost:3100    # Lighthouse mobile + desktop, / and /docs
node scripts/lcp-probe.mjs http://localhost:3100/    # observed LCP candidates under throttling
npm run assets                                        # regenerate favicons, logo lockups and og.png from mark.svg + assets/
```

Playwright and Lighthouse drive the locally installed Google Chrome (`channel: "chrome"`),
so no browser download is needed. Pages taller than Chrome's 16384px capture limit are
shot in clips and stitched.

## Lighthouse (2026-10-04, Lighthouse 13, served from `out/` with gzip)

| Page | Form factor | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- | --- |
| `/` | mobile | 95 | 100 | 100 | 100 |
| `/` | desktop | 100 | 100 | 100 | 100 |
| `/docs` | mobile | 96 | 100 | 100 | 100 |
| `/docs` | desktop | 100 | 100 | 100 | 100 |

Reports are written to `lighthouse/` (git-ignored). These are the scores for the expanded
site (fifteen sections, about 18,000px tall at 1440px). The remaining mobile deductions are
Next's hydration JavaScript; the observed LCP under 4G throttling is the hero subhead,
identical to first paint.

Settings that matter for the score and for production hosting:

- `experimental.inlineCss` inlines the stylesheet so first paint does not wait on a
  render-blocking request.
- Presentational sections are client components. Server-rendered sections are serialized
  twice in a static export (HTML plus the RSC payload); as client components their markup
  ships once and their code lands in a cacheable chunk. This took the home page from
  387 KB to 230 KB of HTML.
- `content-visibility: auto` on sections was tried and rejected: it broke anchor
  navigation (sections above the target expand as they render, so `#policy` landed
  6,000px off) and made the contrast checker read the wrong background.
- The export must be served compressed with long cache lifetimes for `/_next/static/`.
  Cloudflare Pages and Vercel do both by default; `scripts/serve.mjs` mimics them locally.

## Browser review

Full-page screenshots at 1440, 1024 and 390 px live in `screenshots/` (git-ignored), with
the open mobile menu and the `/docs` page captured as well. Issues found and fixed during
review of the expanded site:

- Terminal command and result lines overflowed at desktop width once `--runs 50` and the
  longer status lines were added; lines now wrap at every width.
- The POST example in the interfaces section overflowed its card; it wraps now, and the
  CLI card carries the documented stage-1 and stage-2 behaviour so the two columns balance.
- The attestation window's "not tested" footer broke mid-label on phones; it is a wrapping
  flex row now.
- Decision timestamps in the window used the muted grey at 12px (3.3:1); they use the soft
  ink (7:1) now.

Earlier fixes (mobile menu containing block, single-column grid tracks, sun placement,
heading order, tap targets) are described in the git history.

## Keyboard

`scripts/keyboard.mjs` confirms: skip link first in tab order and jumps to `#main`; all
nav links, CTAs, the email field, the FAQ summaries and footer links are reachable; FAQ
items open and close with Enter and Space; focus-visible outline is drawn on buttons; the
mobile menu opens from the keyboard and closes on Escape; the terminal's replay button is
enabled after the demo and restarts it on Enter.

## Reduced motion

Under `prefers-reduced-motion: reduce`: cloud drift, ray breathing, caret blink and the
loading bar are disabled in CSS; the scroll reveals render their final state; the sun
parallax is off; the terminal renders its complete output immediately.
