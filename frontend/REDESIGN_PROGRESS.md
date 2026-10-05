# Redesign progress

Kept current so the work survives a long session. States: done, in progress, blocked on
(which input), waiting (for a stop).

Last updated: 2026-10-05, phase 1.

## Phases

| Phase | State | Notes |
| --- | --- | --- |
| 1 Read and audit; write REDESIGN_PLAN.md | in progress | No site files edited. Four parallel reads (CLI verification, frontend audit, references, legal sources) feed section 12 of the plan. |
| Stop 1: founder go-ahead | waiting | Questions are batched in REDESIGN_PLAN.md §11. |
| 2 Art direction: three directions, wordmark trace, recommendation | not started | `art_direction: show me three, then wait`. |
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
| Vector wordmark | block 7 | trace of assets/suncly-black.png shown at stop 2 |
| Agent Skill | §8 decision | not built |

## Built switched off (none yet)

## Decisions taken by me, to be confirmed

- Work stays on the environment's branch `claude/sweet-ride-ku6uau`; pushes go only there.
- "Available with limits" becomes "Available" plus the limit sentence; "Pilot" is used for
  the CLI and the programme states.
