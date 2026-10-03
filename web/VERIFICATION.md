# Verification log

How the site was checked before the branch was handed over, and how to repeat it.

## Commands

```bash
npm run build                 # static export to out/ (webpack bundler, zero warnings)
node scripts/serve.mjs 3100   # serve out/ with clean URLs, gzip and cache headers
node scripts/screenshots.mjs http://localhost:3100   # full-page captures at 1440 / 1024 / 390
node scripts/keyboard.mjs http://localhost:3100      # keyboard-only navigation checks
node scripts/lighthouse.mjs http://localhost:3100    # Lighthouse mobile + desktop, / and /docs
node scripts/lcp-probe.mjs http://localhost:3100/    # observed LCP candidates under throttling
```

Playwright and Lighthouse drive the locally installed Google Chrome (`channel: "chrome"`),
so no browser download is needed.

## Lighthouse (2026-10-04, Lighthouse 13, served from `out/` with gzip)

| Page | Form factor | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- | --- |
| `/` | mobile | 97 | 100 | 100 | 100 |
| `/` | desktop | 100 | 100 | 100 | 100 |
| `/docs` | mobile | 97 | 100 | 100 | 100 |
| `/docs` | desktop | 100 | 100 | 100 | 100 |

Reports are written to `lighthouse/` (git-ignored). The remaining mobile deductions are
Next's hydration JavaScript; the observed LCP under 4G throttling is the hero subhead at
about 0.7 s, identical to first paint.

Two settings matter for the score and for production hosting:

- `experimental.inlineCss` inlines the 36 KB stylesheet so first paint does not wait on a
  render-blocking request.
- The export must be served compressed with long cache lifetimes for `/_next/static/`.
  Cloudflare Pages and Vercel do both by default; `scripts/serve.mjs` mimics them locally.

## Browser review

Full-page screenshots at 1440, 1024 and 390 px live in `screenshots/` (git-ignored), with
the open mobile menu and the `/docs` page captured as well. Issues found and fixed during
review:

- Mobile menu panel rendered transparent: the nav bar's backdrop blur made the header the
  containing block for the fixed panel. The blur now sits on an inner bar.
- Page overflowed to 664 px at phone width: single-column grids sized their track to the
  longest terminal / JSON line. Tracks are now `minmax(0, 1fr)`; terminal lines wrap on
  phones.
- Sun was fully hidden behind the product window on phones; resized and raised.
- JSON sample overflowed its column at 1024 px; column ratio and line lengths adjusted.
- Heading order skipped from h1 to h3; section labels are now real h2s.
- Partial-result pill contrast was 3.5:1; token corrected to 5.1:1.
- Footer and desktop nav links were under the 24 px tap-target minimum.

## Keyboard

`scripts/keyboard.mjs` confirms: skip link first in tab order and jumps to `#main`; all
nav links, CTAs, the email field, the FAQ summaries and footer links are reachable; FAQ
items open and close with Enter and Space; focus-visible outline is drawn on buttons; the
mobile menu opens from the keyboard, traps nothing, and closes on Escape; the terminal's
replay button is enabled after the demo and restarts it on Enter.

## Reduced motion

Under `prefers-reduced-motion: reduce`: cloud drift, ray breathing, caret blink and the
loading bar are disabled in CSS; the scroll reveals render their final state; the sun
parallax is off; the terminal renders its complete output immediately.
