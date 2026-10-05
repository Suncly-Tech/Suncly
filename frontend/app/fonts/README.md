# Fonts

Self-hosted latin subsets of three open-source families, served via `next/font/local`:

- Newsreader Variable (opsz 6–72, wght 300–500) — display, lead and long reading
- Figtree Variable (wght 300–900) — interface and small text
- JetBrains Mono Variable (wght 100–800) — commands, hashes and labels

All three are licensed under the SIL Open Font License 1.1. Newsreader and Figtree were
fetched on 2026-10-05 from the google/fonts repository and subset with pyftsubset
(`frontend/design/directions/fonts/` holds the full TTFs used for the drafts). Local files
keep the build fully offline and deterministic; no font request leaves the site.
