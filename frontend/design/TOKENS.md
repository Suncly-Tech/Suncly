# Tokens and type specimen

The design system lives in `app/globals.css` (Tailwind 4 `@theme`). This sheet is the
human-readable copy; the CSS wins where they differ.

## Colour: paper, ink, one sun

| Token (Tailwind name) | Value | Role |
| --- | --- | --- |
| `cream` | `#FAF7F0` | The page ("paper" in the brief) |
| `cream-deep` | `#F1EBDD` | Bands ("paper-deep") |
| `paper` | `#FFFDF8` | Raised surfaces; text on dark bands |
| `dusk` | `#17130F` | The dark surface: warm, never blue-black |
| `ink` | `#1B1814` | Text |
| `ink-soft` | `#5C564C` | Secondary text |
| `ink-mute` | `#8A8378` | Tertiary labels |
| `sun` | `#F2C14E` | The logo's gold, sampled from `public/mark.svg`. Light, not paint: the sun, light on things, one primary action per screen, the focus ring on dark surfaces |
| `amber` | `#C8842B` | Depth, underlines, linework |
| `ember` | `#8F4A1E` | Dusk, shadows, hover on links |
| `line` | ink at 10% | Hairlines |
| `pass`, `fail`, `partial` (+ `-soft`) | muted green, red, amber | Inside evidence components only, never decoration |
| `info-soft` | `#F1EBDD` | Warm neutral tint; no blue anywhere in the theme |

Blue exists only inside `components/home/ClosingSky.tsx`, in variables scoped to that
component (`--sky-high #A9C4E4`, `--sky-mid #CFDCEC`, `--sky-low #F0E2C8`).

The brand angle: `--angle-brand: 18.4deg`, the lean of the two cuts in `mark.svg` (40
units across 120 up). Every shadow, hatch and diagonal uses it; `--angle-hatch` is the
gradient angle for the "not tested" hatch (`.hatch`, `.hatch-dark`, `.cuts-bullet`).

## Type

| Role | Family | Settings |
| --- | --- | --- |
| Display, lead, long reading | Newsreader (variable: opsz 18 to 72, the sizes the site sets; wght pinned at 400; 39 KB) | Display at weight 390, tracking 0, line height 1.05 to 1.15, optical sizing on. Long reading (`.prose-site`) at the text optical size, 19 px, line height 1.55, measure 66ch |
| Interface and small text | Figtree (variable: wght 300 to 900; 20 KB) | Body 17 px / 1.55; small 14 px |
| Commands, hashes, labels | JetBrains Mono Regular (one 400 face; 21 KB) | Labels uppercase, 12.5 px, 0.08em tracking (`.text-eyebrow`); evidence strings in `.text-mono-label` |

Scale (clamped between phone and desktop): hero `text-display-xl` 40 to 92 px; section
`text-display-lg` 31 to 54 px; `text-display-md` 27 to 36 px; `text-lead` 19 to 22 px;
body 17 px; small 14 px.

Self-hosted latin subsets through `next/font/local` (`app/fonts/`); no font request
leaves the site. The wordmark is a drawing (`lib/wordmark.ts`, traced from
`assets/suncly-black.png`), never typeset.

## Components

Marketing: `Nav`, `Footer` (+ `Banner`), `Logo` (`Mark`, `Wordmark`, `Lockup`,
`TrademarkSymbol`), `Picture`, `InView`, `Button`, `SectionHeader`, `Faq`, `Reveal`,
`site/SiteLayout` (`PageHeader`, `Section`), `site/Legal` (`DraftNotice`, `Blank`,
`Summary`, `DocMeta`, `Toc`), `site/DocLayout`, `site/FinalCta`, `site/AccessForm`.

Home: `home/Hero`, `WorksWith`, `HowItWorks` (+ `Stage`, `StickyStage`),
`InstallSection`, `Evidence`, `UseCases`, `OfferCertified`, `DataResearchLab` (`Data`,
`Research`, `Lab` + `SpecimenStrip`), `Stand`, `Questions`, `ClosingSky`, `FindSuncly`.

Evidence and workspace: unchanged in behaviour, restyled through tokens (`components/ui/*`,
`components/evidence/*`, `components/app/*`).

## Motion

Light moves; layout does not. One entrance in the hero (`animate-settle`, 700 ms). The
banner's edge light crosses the word once on entering view (1.1 s). Reveals under 300 ms.
The sky's three layers drift with CSS transforms and pause off screen. Under
`prefers-reduced-motion` every animation is off and the page is complete and still.
