/**
 * All site copy. Mirrors frontend/CONTENT.md, which records the source of every
 * line (README, SCHEMA, ARCHITECTURE, FLOW, API, POLICY, DECISIONS, ROADMAP,
 * DATA_MODEL, A2A spec, or ILLUSTRATIVE). Edit CONTENT.md first.
 */

export const site = {
  name: "suncly",
  domain: "https://suncly.com",
  title: "Suncly — Attestation for A2A agents",
  description:
    "Suncly proves that an A2A agent does what its Agent Card claims: it tests every declared skill many times in a sandbox, judges the results, and hands your reviewers signed evidence to approve on.",
  mission: "Prove that an A2A agent does what its Agent Card claims.",
  email: "team@suncly.com",
  city: "Tallinn, Estonia",
  copyright: "© 2026 Suncly",
} as const;

export const nav = {
  links: [
    { label: "Product", href: "/#product" },
    { label: "How it works", href: "/#how-it-works" },
    { label: "Architecture", href: "/#architecture" },
    { label: "Policy", href: "/#policy" },
    { label: "Docs", href: "/docs" },
  ],
  cta: { label: "Get early access", href: "/#early-access" },
  menuOpen: "Menu",
  menuClose: "Close",
} as const;

export const hero = {
  eyebrow: "Early access · for platform and security teams",
  headline: ["Does your agent do", "what its card says?"],
  subhead:
    "Suncly reads an A2A Agent Card, tests every declared skill many times in a sandbox, judges the results, and hands your reviewers signed evidence to approve on.",
  primary: { label: "Get early access", href: "#early-access" },
  secondary: { label: "Read the docs", href: "/docs" },
} as const;

/**
 * The attestation window in the hero mirrors the example responses in
 * docs/API.md (GET /attestations/{id} and GET /agents/{id}/evidence).
 * All data is the docs' own fictional example.
 */
export const attestation = {
  title: "attestation",
  id: "3c4d5e6f",
  trigger: "ci",
  status: "completed",
  agent: { name: "Order Status Agent", owner: "example-team", risk: "low" },
  card: "agent.example.com/.well-known/agent-card.json",
  contract: "contract v1 · approved by reviewer@example.com",
  columns: ["Test case", "Pass", "Fail", "Inconclusive"],
  results: [
    { id: "9b0c1d2e", skill: "order-status", kind: "skill", pass: 49, fail: 0, inconclusive: 1 },
    { id: "2d3e4f5a", skill: "order-status", kind: "skill", pass: 50, fail: 0, inconclusive: 0 },
  ],
  decisions: [
    { outcome: "flag", by: "policy", at: "09:42" },
    { outcome: "approve", by: "reviewer@example.com", at: "11:05" },
  ],
  budget: { label: "Budget", cost: "3.42", limit: "25.0" },
  signed: "Signed · signing_key_id",
  notTested: {
    label: "Not tested",
    items: ["capabilities.streaming", "production endpoint (sandbox only)"],
  },
} as const;

export const problem = {
  label: "The gap",
  headline: "The protocol describes. Nothing verifies.",
  cards: [
    {
      title: "A card is a list of claims.",
      body: "An A2A agent publishes an Agent Card that names the skills it offers. The specification defines how to describe a skill. It has no mechanism for checking that the agent performs it.",
    },
    {
      title: "A signature is not a test.",
      body: "Agent Cards can be signed. A signature shows the card was not altered, and who signed it. It says nothing about how the agent behaves.",
    },
    {
      title: "So approval is done by hand.",
      body: "Platform and security teams read the card, send a few prompts, and sign off. Suncly is built for those teams.",
    },
  ],
} as const;

export const inspection = {
  label: "What Suncly does",
  headline: "A roadworthiness inspection for AI agents.",
  intro: "Point it at an Agent Card and it does five things.",
  steps: [
    "Reads the agent's Agent Card.",
    "Generates test cases for each declared skill.",
    "Runs each test many times against the agent, in a sandbox.",
    "Judges the results and stores signed evidence.",
    "Outputs an approval decision for your agent registry or CI pipeline.",
  ],
} as const;

export const howItWorks = {
  label: "How it works",
  headline: "Seven steps from trigger to signed decision.",
  steps: [
    {
      title: "A trigger arrives.",
      body: "CI, a schedule, a card change, or a person.",
    },
    {
      title: "Suncly fetches the Agent Card and hashes it.",
      body: "If the hash is new, a model drafts test cases for every declared skill, and a human approves them as a contract.",
    },
    {
      title: "The Orchestrator expands the contract into runs.",
      body: "Each test case runs many times, within a cost budget.",
    },
    {
      title: "The Runner calls the agent's sandbox endpoint.",
      body: "As an A2A client, capturing every message. It is the only component that holds your credentials.",
    },
    {
      title: "The Judge scores each run.",
      body: "Deterministic checks first; a pinned model only where those cannot decide. The verdict is pass, fail or inconclusive, and inconclusive never counts as a pass.",
    },
    {
      title: "The Policy engine decides and signs.",
      body: "It applies your policy for the agent's risk level, decides approve, flag for human review, or block, and signs the attestation.",
    },
    {
      title: "Adapters publish the result.",
      body: "A registry status, a CI gate, and an evidence report that states what was NOT tested.",
    },
  ],
  /** The command is from docs/API.md. The console output is illustrative; the format is not defined yet (OQ-P5). */
  terminal: {
    command: "suncly attest https://agent.example.com/.well-known/agent-card.json --runs 50",
    lines: [
      { kind: "note", text: "// console output is illustrative — the format is not defined yet" },
      { kind: "info", text: "fetched agent card · Order Status Agent · card_hash 7f3a…c1" },
      { kind: "info", text: "contract v1 approved · 2 test cases · 50 runs each" },
      { kind: "pass", text: "order-status / case 9b0c", status: "49 pass · 1 inconclusive" },
      { kind: "pass", text: "order-status / case 2d3e", status: "50 pass" },
      { kind: "info", text: "card re-fetched · hash unchanged · cost 3.42 of 25.0" },
      { kind: "partial", text: "policy (risk low) →", status: "flag" },
      { kind: "done", text: "attestation signed · report written · not tested: capabilities.streaming" },
    ],
  },
} as const;

export const architecture = {
  label: "Architecture",
  headline: "Six components in the core. Three thin adapters outside it.",
  intro:
    "Each component has one responsibility, and a list of things it must never do. A fault can make Suncly approve less, never more.",
  components: [
    {
      name: "Contract builder",
      does: "Turns the Agent Card into a versioned contract: one or more test cases per declared skill. A model drafts them; a human approves them. Approved contracts are immutable.",
      never: "Marks a contract approved without a human.",
    },
    {
      name: "Orchestrator",
      does: "Expands an approved contract into runs: every test case times the number of repetitions. Owns concurrency, retries, timeouts and the cost budget per attestation.",
      never: "Enqueues a run once the budget is reached.",
    },
    {
      name: "Runner",
      does: "The only component that holds your credentials and calls the agent. Acts as an A2A client in its own container, network-limited to the target, and redacts every transcript before it leaves.",
      never: "Lets a secret leave, or calls a production endpoint.",
    },
    {
      name: "Judge",
      does: "Layer 1 is deterministic: valid schema, final task state, required fields, latency limit. Layer 2 uses a pinned model with a fixed rubric, only for criteria Layer 1 cannot decide.",
      never: "Counts inconclusive as a pass.",
    },
    {
      name: "Evidence store",
      does: "Append-only. Per run: the full redacted transcript, verdict, timings and cost. Each attestation is signed and references the card hash and contract version.",
      never: "Updates or deletes a record. Corrections are new records.",
    },
    {
      name: "Policy engine",
      does: "Aggregates results per test case and applies your thresholds for the agent's risk level. Outcome: approve, flag or block. Signs the attestation.",
      never: "Approves automatically when a human is required.",
    },
  ],
  adapters: {
    title: "Adapters",
    body: "Registry status, CI gate and evidence report. They translate results into other systems and never decide anything.",
  },
  outputs: ["Registry status", "CI gate", "Evidence report"],
} as const;

export const product = {
  label: "Product",
  sections: [
    {
      number: "01",
      name: "Contract",
      title: "Tests drafted by a model. Approved by a person.",
      body: "Suncly canonicalizes and hashes the card, then drafts at least one test case for every declared skill. Nothing runs until a human approves the contract. Approved contracts are immutable: any edit is a new version, and a changed card is a new contract.",
    },
    {
      number: "02",
      name: "Runs",
      title: "Many times, in a sandbox, inside a budget.",
      body: "Every test case runs repeatedly against a sandbox or dry-run endpoint, so nothing real is booked, paid or deleted. Each run has a deterministic key, so retries never double count, and the attestation stops when it reaches its cost cap.",
    },
    {
      number: "03",
      name: "Probes",
      title: "Beyond what the card declares.",
      body: "Alongside skill tests, the contract carries probes: behaviour the card does not declare, injected instructions, and failure conditions. They go through the same human approval and the same sandbox rule.",
    },
    {
      number: "04",
      name: "Judge",
      title: "Deterministic first. A pinned model only when needed.",
      body: "Valid schema, final task state, required fields and the latency limit are decided without a model. Where a criterion needs one, a model pinned by version applies a fixed rubric and stores its rationale. Inconclusive is a third verdict, and it is never a pass.",
    },
    {
      number: "05",
      name: "Evidence",
      title: "Signed, append-only, and honest about gaps.",
      body: "Every run keeps its transcript, verdict, timings and cost. The attestation is signed over the card hash, the contract version, the aggregated results and the hash of every transcript. The report states what was not tested.",
    },
    {
      number: "06",
      name: "Decision",
      title: "Approve, flag, or block. Then gate on it.",
      body: "The policy engine applies your thresholds per risk level and writes a decision. Adapters push it where approval happens: a status in your agent registry, pass or fail in your CI pipeline, and a report for the reviewer.",
    },
  ],
} as const;

export const policy = {
  label: "Approval policy",
  headline: "Risk decides how much a human is in the loop.",
  intro:
    "Every agent has a risk level. The default policy ties it to how an attestation is approved. Thresholds are configured per customer and per risk level; Suncly ships no numbers of its own.",
  columns: ["Risk", "Example", "Approval"],
  rows: [
    { risk: "low", example: "read-only lookup", approval: "automatic on pass" },
    { risk: "medium", example: "writes to internal systems", approval: "automatic on pass, human on any drop" },
    { risk: "high", example: "payments, personal data", approval: "human sign-off every time" },
  ],
  human: {
    title: "A human is always required for",
    items: [
      "the first approval of a contract",
      "new or changed skills",
      "borderline or dropping results",
      "every attestation of a high-risk agent",
    ],
  },
  outcomes: [
    { outcome: "approve", meaning: "The results meet your policy for the agent's risk level. No human is required." },
    { outcome: "flag", meaning: "A human must decide. Their resolution is a second decision record; the first is never edited." },
    { outcome: "block", meaning: "The results do not meet the policy." },
  ],
  noDecision: "An attestation that ran out of budget, or whose card changed mid-run, gets no decision at all. No decision is never an approval.",
} as const;

export const rules = {
  label: "Non-negotiable",
  headline: "Seven rules the system is built around.",
  intro: "Each one is a decision record. Changing one means changing the schema first.",
  items: [
    {
      id: "DR-001",
      rule: "Idempotent runs.",
      why: "Every run has a deterministic key. Retries never double count, so the signed results describe runs that happened the way they say.",
    },
    {
      id: "DR-002",
      rule: "Evidence is immutable.",
      why: "Records are never edited. Corrections are new records, so a signature and the approval behind it can be trusted later.",
    },
    {
      id: "DR-003",
      rule: "Secrets never leave the Runner.",
      why: "Transcripts are redacted before storage. The Runner is the only component with your credentials, which is what lets it run inside your network later.",
    },
    {
      id: "DR-004",
      rule: "The judge model is pinned.",
      why: "An attestation measures the agent, not changes in the judge. A new judge model is a deliberate configuration change, never drift.",
    },
    {
      id: "DR-005",
      rule: "Budget caps live in the Orchestrator.",
      why: "Runs are test cases times repetitions, so costs multiply. The component that enqueues runs is the one that stops them. No surprise bills.",
    },
    {
      id: "DR-006",
      rule: "Tests hit a sandbox or dry-run endpoint.",
      why: "Probes deliberately inject instructions and failure conditions. Against production that could book, pay or delete something real.",
    },
    {
      id: "DR-007",
      rule: "Reports state what was NOT tested.",
      why: "An approval on partial evidence misleads if the gaps are invisible. Suncly does not produce a score that would hide them.",
    },
  ],
} as const;

export const standard = {
  label: "Open standard",
  headline: "Reads the A2A Agent Card. Emits a signed attestation.",
  intro:
    "Suncly does not ask you to describe your agent twice. It reads the card you already publish under the A2A protocol, version 1.0, and tests what is in it.",
  reads: {
    title: "What Suncly reads",
    items: [
      { field: "/.well-known/agent-card.json", note: "where A2A agents publish their card" },
      { field: "skills[]", note: "id · name · description · tags · examples. The claims under test." },
      { field: "supportedInterfaces[]", note: "url · protocolBinding · protocolVersion. The Runner picks the first it supports." },
      { field: "capabilities · securitySchemes", note: "what the card declares beyond skills, and how to authenticate" },
      { field: "signatures", note: "integrity and signer only. Not behaviour." },
    ],
  },
  emits: {
    title: "What Suncly emits",
    items: [
      { field: "results[]", note: "per test case: pass, fail and inconclusive counts" },
      { field: "decisions[]", note: "approve · flag · block, with policy_version and who decided" },
      { field: "signature · signing_key_id", note: "over card_hash, contract version, results and transcript hashes" },
      { field: "evidence report", note: "with a statement of what was NOT tested" },
    ],
  },
  /** From docs/API.md, GET /attestations/{id}. Marked Proposed in the docs; shortened here. */
  jsonTitle: "GET /attestations/3c4d5e6f…",
  json: `// from docs/API.md (proposed response shape), shortened
{
  "id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
  "trigger": "ci",
  "status": "completed",
  "budget_limit": 25.0,
  "cost_total": 3.42,
  "signature": "<signature>",
  "signing_key_id": "<signing_key_id>",
  "results": [
    { "skill_id": "order-status", "kind": "skill",
      "pass": 49, "fail": 0, "inconclusive": 1 },
    { "skill_id": "order-status", "kind": "skill",
      "pass": 50, "fail": 0, "inconclusive": 0 }
  ],
  "decisions": [
    { "outcome": "flag", "decided_by": "policy",
      "policy_version": "<policy_version>" }
  ]
}`,
} as const;

export const interfaces = {
  label: "Interfaces",
  headline: "One command. Four endpoints. The same core library.",
  intro: "The CLI arrives first and is enough to run a pilot by hand. The HTTP API follows and calls the same library.",
  cli: {
    title: "CLI",
    command: "suncly attest <card-url> --runs 50",
    args: [
      { name: "<card-url>", note: "the URL of the agent's Agent Card" },
      { name: "--runs", note: "repetitions per test case" },
    ],
    stages: [
      { stage: "Stage 1", note: "Fetches the card, runs each test case --runs times against a sandbox or dry-run endpoint, judges each run deterministically, and writes a file report that states what was NOT tested." },
      { stage: "From stage 2", note: "Runs only an approved contract. If the card's hash is new, a draft contract is created and must be approved first." },
    ],
  },
  api: {
    title: "HTTP API",
    endpoints: [
      { method: "POST", path: "/attestations", note: "start an attestation" },
      { method: "GET", path: "/attestations/{id}", note: "status and results" },
      { method: "POST", path: "/contracts/{id}/approve", note: "human approval" },
      { method: "GET", path: "/agents/{id}/evidence", note: "evidence history" },
    ],
    /** From docs/API.md, POST /attestations request (proposed). */
    example: `POST /attestations
{
  "agent_id": "6f1c2d3e-…",
  "card_url": "https://agent.example.com/.well-known/agent-card.json",
  "runs": 50,
  "trigger": "ci",
  "budget_limit": 25.0
}`,
  },
} as const;

export const roadmap = {
  label: "Where we are",
  headline: "Six stages. The first one runs a pilot.",
  intro:
    "Suncly is pre-prototype: the architecture is written down, the package skeleton exists, and the build order is fixed. Stage 1 is enough to run a first pilot by hand.",
  stages: [
    { number: "1", title: "Core library", body: "Runner, deterministic judge, CLI and a file report." },
    { number: "2", title: "Contract builder", body: "Drafted test cases with the human approval step." },
    { number: "3", title: "Evidence store", body: "Cloudflare D1 tables, R2 transcripts, and attestation signing." },
    { number: "4", title: "Model judge and probes", body: "Layer 2 with a pinned model, plus undeclared, injection and failure probes." },
    { number: "5", title: "API, policy, CI", body: "The four endpoints, the policy engine and the CI gate." },
    { number: "6", title: "Registry adapters", body: "Approval status written into your agent registry." },
  ],
  stack: {
    title: "Stack",
    items: [
      { k: "Language", v: "Python, for the most mature A2A SDK" },
      { k: "Storage", v: "Cloudflare D1 for tables, R2 for transcripts" },
      { k: "Signing", v: "asymmetric signatures over the canonicalized attestation" },
      { k: "Models", v: "you bring your own keys; the judge model is pinned by version" },
    ],
  },
  outOfScope: {
    title: "Not on the roadmap",
    body: "Suncly is not a registry, a gateway, an identity system, a monitoring platform, a universal score, or a payments product. It writes into the registry you have and gates the pipeline you run.",
  },
} as const;

export const resources = {
  label: "Documentation",
  headline: "The architecture is written down before the code.",
  intro: "Eight documents describe the system. Where they and the schema disagree, the schema wins. They ship with early access.",
  comingLabel: "With early access",
  cards: [
    { title: "Schema", body: "The architecture schema. The source of truth.", href: "/docs" },
    { title: "Architecture", body: "Each component's responsibility, inputs, outputs, what it must never do, and how it fails safely.", href: "/docs" },
    { title: "Data model", body: "The seven entities, with fields, keys, enums and an ER diagram.", href: "/docs" },
    { title: "Flow", body: "One attestation from trigger to result, with every failure path.", href: "/docs" },
    { title: "API", body: "The CLI command and the four HTTP endpoints, with examples.", href: "/docs" },
    { title: "Policy", body: "Risk levels, approval rules, and when a human is required.", href: "/docs" },
    { title: "Decisions", body: "The seven non-negotiable rules, as decision records.", href: "/docs" },
    { title: "Roadmap", body: "Six build stages, each with a definition of done.", href: "/docs" },
  ],
} as const;

export const earlyAccess = {
  headline: "Run the first pilot with us.",
  body: "Suncly is in early access. If your team approves A2A agents by hand today, leave your email and we will write back. No list size, no countdown, just a reply from the team in Tallinn.",
  fieldLabel: "Work email",
  placeholder: "you@company.com",
  button: "Request access",
  sending: "Sending",
  success: "Thanks. We will be in touch.",
  error: "That did not go through. Email us at team@suncly.com instead.",
} as const;

export const faq = {
  label: "FAQ",
  headline: "Questions.",
  items: [
    {
      q: "What is Suncly?",
      a: "An attestation tool for A2A agents. It reads an agent's Agent Card, tests every declared skill many times in a sandbox, judges the results, stores signed evidence, and outputs an approval decision for your registry or CI pipeline.",
    },
    {
      q: "What is an Agent Card?",
      a: "Under the A2A protocol, an agent publishes a JSON document, normally at /.well-known/agent-card.json, that names it and lists the skills it offers. Suncly treats that list as the claims to test.",
    },
    {
      q: "Why is a signed card not enough?",
      a: "A card signature shows the card was not altered and who signed it. It says nothing about how the agent behaves. Suncly tests the behaviour.",
    },
    {
      q: "Does Suncly call my production agent?",
      a: "No. Tests hit a sandbox or dry-run endpoint, so nothing real is booked, paid or deleted. The report says so.",
    },
    {
      q: "Who writes the tests?",
      a: "A model drafts at least one test case per declared skill. A human approves them as a contract before anything runs. Approved contracts are immutable; an edit is a new version.",
    },
    {
      q: "What can a run score?",
      a: "Pass, fail or inconclusive. Deterministic checks decide first; a pinned model with a fixed rubric decides only what they cannot. Inconclusive is never counted as a pass.",
    },
    {
      q: "What decision comes out?",
      a: "Approve, flag for human review, or block, under your policy for the agent's risk level. A high-risk agent is never approved without a human.",
    },
    {
      q: "Does it produce a score I can compare agents on?",
      a: "No. The outcome is a decision under one customer's policy, not a universal score. A score would hide what was not tested.",
    },
    {
      q: "Where do my credentials go?",
      a: "Only to the Runner, the one component that calls the agent. It runs in its own container, limited to the target, and redacts transcripts before they are stored. It is designed to run inside your network later.",
    },
    {
      q: "What stops a runaway bill?",
      a: "Each attestation has a budget. The Orchestrator stops enqueuing runs when the cost reaches it, the attestation ends as failed, and no decision is made.",
    },
    {
      q: "Which models does it use?",
      a: "You bring your own model keys for drafting test cases and for the model-based judge. The judge model is pinned by version so results do not drift.",
    },
    {
      q: "Is Suncly available today?",
      a: "It is pre-prototype and in early access. The architecture is documented and the build order is fixed; stage 1 is enough to run a first pilot by hand. Leave your email and we will write to you.",
    },
  ],
} as const;

export const footer = {
  groups: [
    {
      title: "Product",
      links: [
        { label: "Product", href: "/#product" },
        { label: "How it works", href: "/#how-it-works" },
        { label: "Architecture", href: "/#architecture" },
        { label: "Policy", href: "/#policy" },
        { label: "Roadmap", href: "/#roadmap" },
        { label: "FAQ", href: "/#faq" },
      ],
    },
    {
      title: "Developers",
      links: [
        { label: "Docs", href: "/docs" },
        { label: "Interfaces", href: "/#interfaces" },
        { label: "Open standard", href: "/#standard" },
        { label: "Changelog", href: null },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "Early access", href: "/#early-access" },
        { label: "Contact", href: "mailto:team@suncly.com" },
        { label: "Tallinn, Estonia", href: null, plain: true },
      ],
    },
    {
      title: "Legal",
      links: [
        { label: "Privacy", href: null },
        { label: "Terms", href: null },
      ],
    },
  ],
  coming: "Coming",
} as const;

export const docsPage = {
  title: "Docs",
  headline: "Eight documents. One source of truth.",
  body: "Suncly's architecture is written down before its code. The documents below describe the system component by component, entity by entity, and step by step. They are in the repository today and will be published here with early access. Where a document and the schema disagree, the schema wins.",
  status: "Status: pre-prototype. The repository holds the architecture documentation and a package skeleton. No stage has started.",
  docs: [
    { file: "SCHEMA.md", title: "Architecture schema", body: "System layout, components, data model, main flow, default approval policy, interfaces, stack, the non-negotiable rules, build order, and what is out of scope. The source of truth." },
    { file: "docs/ARCHITECTURE.md", title: "Architecture", body: "Each component's responsibility, inputs, outputs, what it must never do, and how it fails safely. Also the A2A protocol facts Suncly depends on, checked against specification v1.0.1." },
    { file: "docs/DATA_MODEL.md", title: "Data model", body: "The seven entities: agent, card_version, contract, test_case, attestation, run, decision. Fields, types, keys, relationships, enums, invariants, and an ER diagram." },
    { file: "docs/FLOW.md", title: "Attestation flow", body: "One attestation from trigger to result, the attestation status lifecycle, and the failure paths: agent unreachable, budget exceeded, inconclusive verdicts, card changed mid-run." },
    { file: "docs/API.md", title: "Interfaces", body: "The CLI command and the four HTTP endpoints, with example requests and responses." },
    { file: "docs/POLICY.md", title: "Approval policy", body: "Risk levels, decision outcomes, when a human is required, the decision table, and how inconclusive results count." },
    { file: "docs/DECISIONS.md", title: "Decision records", body: "The seven non-negotiable rules, each with its decision, reason and consequences." },
    { file: "docs/ROADMAP.md", title: "Roadmap", body: "The six build stages, each with a definition of done, and what is not on the roadmap." },
  ],
  howToRead: {
    title: "How the documents are written",
    items: [
      "Where a document and the schema disagree, the schema wins.",
      "Behaviour the schema does not define is marked Proposed and tracked as an open question. No document decides silently.",
      "Protocol details still to be checked against the A2A specification are marked for verification.",
      "Numeric thresholds are deliberately absent. They are configured per customer and per risk level.",
    ],
  },
  cta: { label: "Get early access", href: "/#early-access" },
  back: { label: "Back to the site", href: "/" },
} as const;
