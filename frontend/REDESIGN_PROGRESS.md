# Redesign progress

Kept current so the work survives a long session. States: done, in progress, blocked on
(which input), waiting (for a stop).

Last updated: 2026-10-05, phase 2 drafts.

## Phases

| Phase | State | Notes |
| --- | --- | --- |
| 1 Read and audit; write REDESIGN_PLAN.md | done | No site files edited. Four parallel reads (CLI verification, frontend audit, references, legal sources) are in section 12 of the plan. |
| Stop 1: founder go-ahead | given for the drafts only | Questions in REDESIGN_PLAN.md §11 remain open. |
| 2 Art direction: three directions, wordmark trace, recommendation | done, waiting for the pick | Drafts in `design/directions/` (hero plus the Suncly Data section, 1440 and 390 px, `board.png`); wordmark trace in `design/wordmark/`; recommendation A in `design/directions/README.md`. Founder asked for lightweight drafts: hero plus one lower section, no final artwork, no legal drafting yet. |
| Stop 2: founder pick | waiting | |
| 3 Foundations: tokens, type, grid, logo, badge, picture pipeline, core components | not started | |
| 4 Home page, section by section (02 to 16) | not started | Build, screenshot at 1440/1024/768/390, look, fix, commit per section. |
| 5 Other pages and legal pages | not started | |
| 6 Verification and hand-back | not started | Two fresh review subagents; forbidden-words script; axe; Lighthouse; `python tasks.py check`. |

## Blocked on founder inputs

| Item | Input | Effect while blank |
| --- | --- | --- |
| Draft label on /privacy, /terms, /legal, /certified/policy | block 5 company and legal facts | pages ship complete, noindex, with named blanks |
| Find Suncly row | block 1 links | row renders no links; listed in HANDOFF.md |
| /offer unit and price; Terms fee schedule | block 4 | model stated, "no fees are charged yet" |
| Certification criteria | block 6 | v0.1 proposal in the plan; policy page marked draft, no criteria published |
| Recipients and retention tables in the Privacy Policy | block 5 hosting, endpoint, subprocessors, retention | named blanks |
| Vector wordmark | block 7 | traced from assets/suncly-black.png; see design/wordmark/ and the note on the stripes mark |
| Agent Skill | §8 decision | not built |

## Not possible in this environment

- The live site, the legal statute sites and registers, and eight of ten reference sites are refused by the environment's network policy. Listed in REDESIGN_PLAN.md §0 and §12.

## Built switched off (none yet)

## Decisions taken by me, to be confirmed

- Work stays on the environment's branch `claude/sweet-ride-ku6uau`. Phase 2 commits are local only until the founder permits a push.
- "Available with limits" becomes "Available" plus the limit sentence; "Pilot" is used for
  the CLI and the programme states.
