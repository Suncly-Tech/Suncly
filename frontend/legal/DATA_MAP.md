# Data map

Written from the code and the founder inputs on 2026-10-05. For each category of data:
its source, purpose, legal basis, where it is stored, who receives it, how long it is kept
and how it is deleted. Three contexts are kept apart because they differ in fact.
Blanks are founder inputs (`lib/launch.ts`), never guessed.

## A. This website and the pilot form (Suncly is controller)

| Category | Source | Purpose | Legal basis (GDPR 6(1)) | Stored where | Recipients | Retention | Deletion |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Work e-mail and optional note (may name the employer and the agent) | The pilot form on `/access` (`components/site/AccessForm.tsx`), which posts `{email, note, source}` to `NEXT_PUBLIC_SIGNUP_ENDPOINT` or, when unset, opens the visitor's own mail client to team@suncly.com | Answer the request; arrange a pilot | (b) pre-contractual steps, or (f) legitimate interest in answering a business enquiry | Endpoint storage: **blank** (`pilotFormEndpointAndStorage`); otherwise the team mailbox | E-mail provider: **blank**; form endpoint: **blank** | **blank** (`retentionPeriods`) | Delete from the mailbox and the endpoint's store at the end of the period or on request |
| Correspondence | The person | Same | Same | Team mailbox | E-mail provider: **blank** | **blank** | Same |
| Server logs: IP, user agent, page, time | The browser, received by the host | Serve the site; diagnose faults; security | (f) | Hosting provider (Vercel, **unconfirmed**; regions **blank**) | The host | Provider's log retention: **blank** | Rotated by the provider |
| Cookies | None set (inspected 2026-10-05 with `scripts/inspect-storage.mjs`) | | | | | | |
| Browser local storage `suncly.workspace.v1` | The visitor loads a report or the sample into `/app` | Keep the workspace between reloads | Strictly necessary for the function the visitor asked for; no consent needed | The visitor's browser only | Nobody; never sent | Until the visitor clears it (`/app/settings`) or clears site data | Clear the workspace, or clear site data |
| Analytics | None (`company.analytics = "none"`) | | | | | | |
| Marketing e-mail | Not sent today | If ever: (a) consent for natural persons; opt-out in every message (ECA §103¹) | | | | | |
| Accounting records (invoices, contracts) | None yet | Legal obligation | (c) Accounting Act §12 | **blank** | Accountant: **blank** | 7 years from the end of the financial year | After the period |

## B. The Suncly command-line tool (the customer is controller; Suncly receives nothing)

Verified in `src/suncly` on 2026-10-05 (REDESIGN_PLAN.md §12.1): the only network clients are the card fetcher (`adapters/httpx_card_fetcher.py`) and the agent transport (`runner/http_transport.py`), which refuses any other host; no telemetry, analytics, update check or model-provider call exists.

| Category | Source | Where it is stored (customer-controlled) | Who can read it | Deletion |
| --- | --- | --- | --- | --- |
| The Agent Card (`card_version.raw_json`, `card_hash`) | The card URL the customer gives | Evidence store: files under `~/.suncly/store` or the customer's Postgres | Whoever can read that store | Remove files or drop the database |
| Contract, test cases, `approved_by`, `approved_at` | The drafter and the approving person | Evidence store | Same | Same |
| Redacted transcripts, one per run, with the Layer 1 checks | The agent under test, via the Runner | `~/.suncly/transcripts` on the machine that ran it | Whoever can read that folder | Remove files |
| Personal data inside transcripts (whatever a sandbox agent returns) | The agent under test | Same as transcripts | Same | Same. Redaction targets credentials and tokens (`runner/redaction.py`), not personal data in general; the customer must not point Suncly at an agent that returns real personal data |
| The agent credential (`SUNCLY_AGENT_AUTHORIZATION`) | The customer's environment | Only in the Runner process's memory; never written | Nobody; redacted from every transcript | Unset the variable |
| The deployment signing key | Created on first run (`adapters/file_keys.py`) | `~/.suncly/keys` | Whoever can read that folder | Delete it; existing reports still verify with the embedded public key |
| Report folders (`report.html`, `report.md`, `result.json`, `transcripts/`) | The Report adapter | `./suncly-reports/<attestation-id>/` | Whoever the customer gives them to | Delete the folder |

Append-only: `run` and `decision` records are never updated or deleted by the software (`adapters/file_store.py` opens with mode `x`; Postgres triggers `run_append_only`, `decision_append_only`). Deletion is by removing files or dropping the database. Transcripts are stored locally until an object-storage adapter exists.

## C. The hosted API, accounts and billing (planned; nothing exists)

Written so the Privacy Policy's section 13 can switch on. When it exists, Suncly will be controller for account, contact, API-key and billing data, and processor (GDPR Art 28) for evaluation data submitted through the API. Open: how erasure requests are met against append-only evidence (recorded in HANDOFF.md). Providers: database Supabase (**unconfirmed**; regions **blank**), payments **blank**, sub-processor list **blank**.

## Inputs that complete this map

`pilotFormEndpointAndStorage`, e-mail provider, hosting regions and log retention, `retentionPeriods`, `subprocessors`, accountant, payment provider, `privacyContactEmail`, `securityContactEmail`.
