# Verification log

How the site and the workspace were checked on 2026-10-04/05, what passed, and what was
not tested.

## Commands

```bash
npm run typecheck             # tsc --noEmit: clean
npm run build                 # next build --webpack: 22 static routes, no warnings
node scripts/serve.mjs 3100   # serve out/ with clean URLs, gzip and cache headers
node scripts/lighthouse.mjs http://localhost:3100   # Lighthouse mobile + desktop, / and /docs
.venv/bin/python frontend/scripts/make-sample.py    # regenerate the sample data set (needs the package installed)
```

The sample generator and Lighthouse were run from the Terminal panel (they need local
ports and Chrome); the build and typecheck ran in the sandbox.

## Sample data

`frontend/scripts/make-sample.py` ran the real attestation use case three times against
a fictional local mock agent with a fake credential in the Runner's environment. The
script fails if the credential appears in any transcript; it did not. The three bundles
verify with the in-browser verifier (eight checks, including the Ed25519 signature) and
carry the owner and risk level the script passes.

## Lighthouse (2026-10-05, Lighthouse 13, served from `out/` with gzip)

| Page | Form factor | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- | --- |
| `/` | mobile | 88 | 100 | 100 | 100 |
| `/` | desktop | 100 | 100 | 100 | 100 |
| `/docs` | mobile | 95 | 100 | 100 | 100 |
| `/docs` | desktop | 100 | 100 | 100 | 100 |

The mobile home deduction is unused JavaScript from the interactive sections. The hero
evaluation window is server-rendered, so the sample JSON does not ship to the client on
the home page.

## Browser review (built-in browser, static export)

Checked at the pane's desktop width, at 1024 × 800 and at 375 × 812:

- Home: hero with the real sample window, the gap, claim-to-decision chain, process,
  manual-review comparison, coverage, scope and limitations, FAQ, final CTA, footer.
- `/product`, `/workflows`, `/security`, `/docs`, `/docs/getting-started`, `/docs/cli`,
  `/docs/evidence`, `/access`, `/company`, `/privacy`, `/terms` render; anchor links and
  sticky side navigation work.
- `/demo`: the three evaluation cards switch the view; tabs work; the Signature tab's
  in-browser verification passes all eight checks; the comparison and the sample reviewer
  record render.
- `/app`: empty state with three guided actions; "Load sample data" fills the overview
  (stats, outstanding reviews, what changed, recent evaluations, agents); phone width no
  longer overflows after constraining the tab row.
- `/app/evaluation?…&tab=review`: submitting the empty form shows both field errors;
  recording a note with a reviewer and rationale adds it to the decision history with
  Markdown and JSON export buttons.
- `/app/agent?id=<unknown>` shows the not-found empty state; `/app/compare` picks the
  last two completed attestations by default and shows regressions; `/app/new`,
  `/app/import` and `/app/settings` render with their forms and notices.
- `/access`: submitting the empty form shows the email validation error inline.

Issues found and fixed during the review: nav labels wrapping at mid widths; the desktop
nav overflowing at 1024 px (tighter spacing, workspace link from xl); the workspace tab
row forcing horizontal overflow on phones; a comparison labelling test cases without
runs as "improved" (now "no runs recorded"); the sample agent registered with default
owner and risk because the draft-export step ran first.

## Keyboard

Skip link first in tab order; nav links show the focus ring (outline in sky blue);
tabs use roving focus with arrow keys; the mobile menu opens from the keyboard and
closes on Escape; dialogs are native `<dialog>` elements (focus trap and Escape from the
browser); every form control has a label, and errors are announced with `role="alert"`.

## Reduced motion

Scroll reveals render their final state, the sky animations are disabled, and the
budget meter is static by design.

## Not tested

- Importing a real report folder through the file picker and drag-and-drop in the
  built-in browser (no file-system access from the automation). The parser is the same
  code path the sample loader uses, and its error branches are unit-level logic in
  `lib/workspace/store.ts`.
- The pilot form against a live `NEXT_PUBLIC_SIGNUP_ENDPOINT` (none is configured; the
  mailto fallback was exercised as far as building the link).
- Browsers without Ed25519 in WebCrypto: the verifier reports that check as "not run"
  and points to the CLI; this branch was not exercised.
- Firefox and Safari rendering.
- The Python test suite was not run as part of this work; the backend is unchanged from
  `origin/mvp`.
