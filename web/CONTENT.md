# Suncly website — content source

Every headline, paragraph, label and code snippet on the site lives here first.
Components import copy from `lib/content.ts`, which mirrors this file. Nothing is
improvised inside JSX.

## Sources

The repo contains exactly one product document at the time of writing:

- **README.md** — "Attestation for A2A agents: tests whether an agent actually
  does what its Agent Card claims, and produces signed evidence for approval."

There is no `/docs` folder, no architecture schema, no CLI reference and no
report schema in the repo. Each item below is tagged with where it came from:

| Tag | Meaning |
| --- | --- |
| `README` | Stated in README.md. |
| `BRIEF` | Stated in the website build brief (product framing supplied by the founders: first product is a stress-test / crash-test; step list; section names; early-access status; contact email; city). |
| `A2A` | Public A2A protocol specification (Agent Card structure). Not a Suncly claim. |
| `ILLUSTRATIVE` | Sample data in a mock UI or code snippet. Marked in code with `// illustrative — align with the final CLI` / `final schema`. Never presented as a measured result. |

Nothing on the site states pricing, integrations, customer names, logos,
testimonials, or usage numbers, because none exist in the repo.

---

## Global

- Site name: **suncly** (lowercase wordmark) — `BRIEF`
- Mission line: *Attestation for agents that talk to agents.* — `README` (restated)
- Meta title: *Suncly — Attestation for A2A agents* — `README`
- Meta description: *Suncly tests whether an A2A agent actually does what its Agent Card claims, and produces signed evidence you can approve on.* — `README`
- Contact: `team@suncly.com` — `BRIEF`
- Location: Tallinn, Estonia — `BRIEF`
- Copyright: © 2026 Suncly — `BRIEF`
- Repo is private → no GitHub link anywhere. — verified (unauthenticated 404)

## 1. Nav

- Links: Product · How it works · Docs — `BRIEF`
- CTA: **Get early access** — `BRIEF`
- Mobile: "Menu" / "Close" button labels; full-screen panel with the same links.

## 2. Hero

Three candidate headlines (all derived from `README`):

1. *Does your agent do what its card says?* ← **chosen** (a question the README answers directly; shortest; two clean lines)
2. *Attestation for agents that talk to agents.*
3. *Trust an agent for what it does, not what it claims.*

- Headline (two lines): **Does your agent do / what its card says?** — `README`
- Subhead: *Suncly reads an A2A Agent Card, exercises every capability it claims, and hands you signed evidence that others can approve on.* — `README` + `BRIEF`
- Primary CTA: **Get early access** → `#early-access` — `BRIEF`
- Secondary CTA: **Read the docs →** → `/docs` — `BRIEF`
- Eyebrow: *Early access* — `BRIEF`

### Product window (mock attestation report) — `ILLUSTRATIVE`

The schema does not exist yet; field names mirror the A2A Agent Card where the
report quotes the card (`name`, `version`, `skills[].id`, `capabilities.*`).

- Window title: `attestation.json`
- Agent: **ledger-agent** · `v1.4.2` — `ILLUSTRATIVE`
- Card: `agent.example.com/.well-known/agent-card.json` — `A2A` path, example host
- Badge: **Attested** · *signed · ed25519* — `README` ("signed evidence"); key type `ILLUSTRATIVE`
- Columns: *Claimed in card* · *Observed* · *Result*
- Rows (claims quoted from a sample card; results sampled):
  1. `skills.reconcile-invoices` — "Matches invoices to ledger entries" — **pass**
  2. `skills.export-report` — "Returns CSV or PDF on request" — **pass**
  3. `capabilities.streaming` — "Streams partial results" — **partial** (streamed, then stalled under load)
  4. `capabilities.pushNotifications` — "Pushes task updates" — **fail** (no callback received)
- Stress-test summary (illustrative sample numbers inside a mock, not site claims):
  - Runs: `1,248`
  - Adversarial inputs: `312`
  - Crashes: `0`
  - Timeouts: `3`
- Footer line: *Report signed 2026-10-03 · verify with `suncly verify`* — `ILLUSTRATIVE`

## 3. Problem strip

Section label: *Why attestation* — editorial

1. **Today, approval is manual.** *Someone reads the Agent Card, sends a few prompts, and signs off.* — `BRIEF` ("check agents by hand before approving them")
2. **A card is a claim, not a test.** *What an agent says it can do and what it does under real inputs are two different things.* — `README` (the gap the product exists for)
3. **Suncly makes approval a check.** *Every claim is exercised. Every result is signed. The evidence travels with the agent.* — `README`

## 4. How it works

Section label: *How it works* · Headline: *Three steps to a signed report.* — `BRIEF`

1. **Point Suncly at an Agent Card.** *Give it the card URL. Suncly reads the skills and capabilities the agent claims.* — `BRIEF` + `A2A`
2. **It exercises every claimed capability.** *Each claim is run under normal inputs and adversarial ones: malformed, oversized, out of order, hostile.* — `BRIEF` ("normal and adversarial inputs")
3. **You get a signed report you can gate on.** *Pass, fail or partial for each claim, plus a stress-test summary, signed so anyone can verify it.* — `BRIEF` + `README`

### Terminal panel — `ILLUSTRATIVE`

```text
$ suncly attest https://agent.example.com/.well-known/agent-card.json
// illustrative — align with the final CLI
→ reading agent card … ledger-agent v1.4.2
→ 2 skills, 2 capabilities claimed
→ exercising skills.reconcile-invoices       pass
→ exercising skills.export-report            pass
→ exercising capabilities.streaming          partial
→ exercising capabilities.pushNotifications  fail
→ stress-test  1,248 runs · 312 adversarial · 0 crashes · 3 timeouts
✓ report signed → attestation.json
```

## 5. Product sections 01–04

The README names two things: attestation (testing claims) and signed evidence
for approval. The brief names the first product (stress-test / crash-test) and
gating. Section 04 is therefore **Approve**, not "Audit": report history is not
described anywhere in the repo.

Section label: *Product*

- **01 Attest** — *Test the card, not the pitch.*
  *Suncly reads an A2A Agent Card and exercises every skill and capability it declares. Each claim comes back as pass, fail or partial, with the evidence attached.* — `README`
- **02 Stress-test** — *Find out what breaks before your users do.*
  *The first Suncly product is a crash-test for agents. Each claimed capability is run under normal inputs and under adversarial ones, and the report records every crash, timeout and wrong answer.* — `BRIEF`
- **03 Gate** — *Only attested agents get in.*
  *The report is signed, so you can require one. Make a current attestation the condition for an agent to join your network, your registry or your pipeline.* — `BRIEF` + `README`
- **04 Approve** — *Evidence that travels with the agent.*
  *Approval stops being a judgment call. Whoever signs off reads the same signed report, verifies the signature, and sees exactly which claims held.* — `README` ("signed evidence for approval")

## 6. Open standard

Section label: *Open standard* · Headline: *Reads the A2A Agent Card. Emits a signed report.*

- Intro: *Suncly does not ask you to describe your agent twice. It reads the Agent Card you already publish under the A2A protocol and tests what is in it.* — `README` + `A2A`
- **What Suncly reads** (A2A Agent Card fields) — `A2A`:
  - `name`, `description`, `version`, `url`
  - `capabilities` — `streaming`, `pushNotifications`, `stateTransitionHistory`
  - `skills[]` — `id`, `name`, `description`, `tags`, `examples`
  - `defaultInputModes`, `defaultOutputModes`
  - `securitySchemes`
- **What Suncly emits** — `README` for "signed evidence"; shape `ILLUSTRATIVE`:
  - One report per attestation run, one result per claim, a stress-test summary, and a signature.

JSON sample — `ILLUSTRATIVE`:

```json
// illustrative — align with the final schema
{
  "agent": { "name": "ledger-agent", "version": "1.4.2" },
  "card": "https://agent.example.com/.well-known/agent-card.json",
  "claims": [
    { "path": "skills.reconcile-invoices", "result": "pass" },
    { "path": "skills.export-report", "result": "pass" },
    { "path": "capabilities.streaming", "result": "partial" },
    { "path": "capabilities.pushNotifications", "result": "fail" }
  ],
  "stress": { "runs": 1248, "adversarial": 312, "crashes": 0, "timeouts": 3 },
  "signature": { "alg": "ed25519", "value": "…" }
}
```

## 7. Developer resources

Section label: *Developers* · Headline: *Everything you need to ship an attested agent.*

Nothing exists yet, so every card carries a muted **Coming** badge and has no link. — verified against repo contents

1. **Docs** — *Install, attest, verify, gate.* — Coming
2. **Schema** — *The attestation report, field by field.* — Coming
3. **Example agent** — *A small A2A agent with a card you can attest.* — Coming
4. **Changelog** — *What changed in each release.* — Coming

## 8. Early access

- Headline (serif): *Get early access.* — `BRIEF`
- Body: *Suncly is in early access. Leave your email and we will write to you when your spot opens. No list size, no countdown, just a reply from the team.* — `BRIEF` ("honest early-access framing"; no "join N others")
- Field label: *Work email* · placeholder `you@company.com`
- Button: **Request access**
- Success: *Thanks. We will be in touch.*
- Error: *That did not go through. Email us at team@suncly.com instead.* — `BRIEF`
- Posts to `NEXT_PUBLIC_SIGNUP_ENDPOINT`; fallback `mailto:team@suncly.com`. — `BRIEF`

## 9. FAQ

Section label: *FAQ* · Headline: *Questions.*

1. **What is Suncly?**
   *Suncly is an attestation tool for A2A agents. It tests whether an agent actually does what its Agent Card claims, and produces signed evidence for approval.* — `README`
2. **What is an Agent Card?**
   *Under the A2A protocol, every agent publishes a JSON Agent Card that lists its name, skills, capabilities and how to reach it. Suncly treats that card as the set of claims to test.* — `A2A` + `README`
3. **Which agents can Suncly attest?**
   *Any agent that speaks the A2A protocol and publishes an Agent Card.* — `README`
4. **What does the stress-test do?**
   *It runs every claimed capability under normal and adversarial inputs and records crashes, timeouts and wrong answers. It is the first Suncly product.* — `BRIEF`
5. **Can I block agents that are not attested?**
   *Yes. The report is signed, so you can make a valid attestation a condition for an agent to join your network or pass your pipeline.* — `BRIEF`
6. **Is Suncly available today?**
   *Suncly is in early access. Leave your email above and we will write to you when your spot opens.* — `BRIEF`

## 10. Footer

- Logo lockup + mission line: *Attestation for agents that talk to agents.*
- **Product**: Product · How it works · Early access · FAQ
- **Developers**: Docs · Schema (Coming) · Example agent (Coming) · Changelog (Coming)
- **Company**: Contact (`mailto:team@suncly.com`) · Tallinn, Estonia
- **Legal**: Privacy (Coming) · Terms (Coming) — no documents exist yet
- Bottom line: *Tallinn, Estonia · © 2026 Suncly*

## /docs page

No real docs location exists, so `/docs` is a short page: — verified

- Title: *Docs*
- Headline: *The docs ship with early access.*
- Body: *Suncly is an attestation tool for A2A agents. The full documentation (install, attest, verify, gate) will be published here when early access opens. Until then, the landing page explains the model, and the team answers questions at team@suncly.com.* — `README` + `BRIEF`
- CTA: **Get early access** → `/#early-access`
