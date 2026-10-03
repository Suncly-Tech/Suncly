# Fonts

Self-hosted latin subsets of three open-source families, served via `next/font/local`:

- Instrument Serif Regular — display headlines
- Manrope Variable (200–800) — body and UI
- JetBrains Mono Variable (100–800) — code

All three are licensed under the SIL Open Font License 1.1 and were downloaded
from Google Fonts. `next/font/google` would self-host the same files at build
time; local files keep the build fully offline and deterministic.
