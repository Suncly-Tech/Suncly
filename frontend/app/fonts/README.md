# Fonts

Self-hosted latin subsets of three open-source families, served via `next/font/local`:

- Newsreader Variable, optical size axis restricted to 18–72 (the display, lead and
  reading sizes the site sets; weight pinned at 400): 39 KB
- Figtree Variable (wght 300–900) for interface and small text: 20 KB
- JetBrains Mono Regular (a single 400 face; every mono label, command and hash on the
  site is set at 400) for commands, hashes and labels: 21 KB

All three are licensed under the SIL Open Font License 1.1. Newsreader and Figtree were
fetched on 2026-10-05 from the google/fonts repository and subset with pyftsubset
(`frontend/design/directions/fonts/` holds the full TTFs used for the drafts); the axis
restrictions were made with fontTools' `varLib.instancer`. The three files together are
80 KB, down from 117 KB, which is the largest single lever on the simulated mobile LCP.
Local files keep the build fully offline and deterministic; no font request leaves the site.
