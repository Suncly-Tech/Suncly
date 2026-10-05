# Redesign progress

Kept current so the work survives a long session. States: done, in progress, blocked on
(which input), waiting (for a stop).

Last updated: 2026-10-05, phases 3 to 7 done; hand-back.

## Phases

| Phase | State | Notes |
| --- | --- | --- |
| 1 Read and audit; write REDESIGN_PLAN.md | done | No site files edited. Four parallel reads (CLI verification, frontend audit, references, legal sources) are in section 12 of the plan. |
| Stop 1: founder go-ahead | given for the drafts only | Questions in REDESIGN_PLAN.md §11 remain open. |
| 2 Art direction: three directions, wordmark trace, recommendation | done, waiting for the pick | Drafts in `design/directions/` (hero plus the Suncly Data section, 1440 and 390 px, `board.png`); wordmark trace in `design/wordmark/`; recommendation A in `design/directions/README.md`. Founder asked for lightweight drafts: hero plus one lower section, no final artwork, no legal drafting yet. |
| Stop 2: founder pick | given: A, Daylight, with B's linework for hatches and diagrams | Founder message of 2026-10-05. |
| 3 Foundations: tokens, type, grid, logo, badge, picture pipeline, core components | done | `app/globals.css`, `design/TOKENS.md`, `lib/wordmark.ts`, `scripts/generate-badge.py`, `art/` + `scripts/render-art.mjs`, `lib/launch.ts`, `lib/capabilities.ts`. |
| 4 Home page, section by section (02 to 16) | done | `components/home/*`; 780 visible words; shot at four widths; no horizontal overflow. |
| 5 Other pages and legal pages | done | `/offer`, `/certified` (+ policy, specimen record), `/data`, `/research`, `/lab`, `/cookies`, `/legal`; Privacy and Terms rewritten; `/security` extended; `legal/*.md`. |
| 6 Verification and hand-back | done | `VERIFICATION.md`. The founder asked for one agent and no subagents, so the two fresh-eyes reviews were not run. |
| 7 Stage 4 refinement (founder go-ahead of 2026-10-05) | done | Every section reviewed at 1440, 1024, 768 and 390 px; pictures made block-level with widths from the column (the min-height that forced them wider was removed); the Offer and Certified band restructured (412 px tall at 1440); the demo output kept unwrapped from tablet width; the closing headline set per sentence; every `/demo` tab panel given its id. Certification criteria withdrawn from public pages; specimen record labelled fictional; disclosure policy and `security.txt` stripped of promises. Fonts 117 to 80 KB; wordmark path written once per page. Functional checks and the LCP probe added. |

## Blocked on founder inputs

| Item | Input | Effect while blank |
| --- | --- | --- |
| Draft label on /privacy, /terms, /legal, /certified/policy | block 5 company and legal facts | pages ship complete, noindex, with named blanks |
| Find Suncly row | Hacker News URL only | four links render; Hacker News omitted |
| /offer unit and price; Terms fee schedule | block 4 | model stated, "no fees are charged yet" |
| Certification criteria | block 6 | v0.1 proposal only in `REDESIGN_PLAN.md` §9; policy page says none are adopted; nothing published |
| Recipients and retention tables in the Privacy Policy | block 5 hosting, endpoint, subprocessors, retention | named blanks |
| Vector wordmark | resolved | traced lettering in `lib/wordmark.ts`; the mark is `public/mark.svg` unchanged |
| Agent Skill | §8 decision | not built |

## Not possible in this environment

- The live site, the legal statute sites and registers, and eight of ten reference sites are refused by the environment's network policy. Listed in REDESIGN_PLAN.md §0 and §12.

## Built switched off

See `HANDOFF.md` §3: the draft label and noindex on the legal pages, the certification criteria (proposed), the hosted-API sections, the verified Works-with state, ®, the research notes, the Hacker News link, the platform glyphs.

## Decisions taken by me, to be confirmed

- Work stays on the environment's branch `claude/sweet-ride-ku6uau`; the founder permitted pushing there on 2026-10-05.
- "Available with limits" becomes "Available" plus the limit sentence; "Pilot" is used for
  the CLI and the programme states.
