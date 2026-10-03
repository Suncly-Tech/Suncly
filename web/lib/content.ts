/**
 * All site copy. Mirrors web/CONTENT.md, which records the source of every
 * line (README, BRIEF, A2A spec, or ILLUSTRATIVE). Edit CONTENT.md first.
 */

export const site = {
  name: "suncly",
  domain: "https://suncly.com",
  title: "Suncly — Attestation for A2A agents",
  description:
    "Suncly tests whether an A2A agent actually does what its Agent Card claims, and produces signed evidence you can approve on.",
  mission: "Attestation for agents that talk to agents.",
  email: "team@suncly.com",
  city: "Tallinn, Estonia",
  copyright: "© 2026 Suncly",
} as const;

export const nav = {
  links: [
    { label: "Product", href: "/#product" },
    { label: "How it works", href: "/#how-it-works" },
    { label: "Docs", href: "/docs" },
  ],
  cta: { label: "Get early access", href: "/#early-access" },
  menuOpen: "Menu",
  menuClose: "Close",
} as const;

export const hero = {
  eyebrow: "Early access",
  headline: ["Does your agent do", "what its card says?"],
  subhead:
    "Suncly reads an A2A Agent Card, exercises every capability it claims, and hands you signed evidence that others can approve on.",
  primary: { label: "Get early access", href: "#early-access" },
  secondary: { label: "Read the docs", href: "/docs" },
} as const;

export type ClaimResult = "pass" | "fail" | "partial";

/** Mock report shown in the hero window. Illustrative — align with the final schema. */
export const report = {
  file: "attestation.json",
  agent: { name: "ledger-agent", version: "v1.4.2" },
  card: "agent.example.com/.well-known/agent-card.json",
  badge: "Attested",
  badgeNote: "signed · ed25519",
  columns: ["Claimed in card", "Observed", "Result"],
  claims: [
    {
      path: "skills.reconcile-invoices",
      claim: "Matches invoices to ledger entries",
      observed: "12 of 12 fixtures matched",
      result: "pass" as ClaimResult,
    },
    {
      path: "skills.export-report",
      claim: "Returns CSV or PDF on request",
      observed: "Both formats returned",
      result: "pass" as ClaimResult,
    },
    {
      path: "capabilities.streaming",
      claim: "Streams partial results",
      observed: "Streamed, then stalled under load",
      result: "partial" as ClaimResult,
    },
    {
      path: "capabilities.pushNotifications",
      claim: "Pushes task updates",
      observed: "No callback received",
      result: "fail" as ClaimResult,
    },
  ],
  stress: {
    label: "Stress-test",
    stats: [
      { label: "Runs", value: "1,248" },
      { label: "Adversarial", value: "312" },
      { label: "Crashes", value: "0" },
      { label: "Timeouts", value: "3" },
    ],
  },
  footer: "Report signed 2026-10-03 · verify with",
  footerCmd: "suncly verify attestation.json",
} as const;

export const problem = {
  label: "Why attestation",
  cards: [
    {
      title: "Today, approval is manual.",
      body: "Someone reads the Agent Card, sends a few prompts, and signs off.",
    },
    {
      title: "A card is a claim, not a test.",
      body: "What an agent says it can do and what it does under real inputs are two different things.",
    },
    {
      title: "Suncly makes approval a check.",
      body: "Every claim is exercised. Every result is signed. The evidence travels with the agent.",
    },
  ],
} as const;

export const howItWorks = {
  label: "How it works",
  headline: "Three steps to a signed report.",
  steps: [
    {
      title: "Point Suncly at an Agent Card.",
      body: "Give it the card URL. Suncly reads the skills and capabilities the agent claims.",
    },
    {
      title: "It exercises every claimed capability.",
      body: "Each claim is run under normal inputs and adversarial ones: malformed, oversized, out of order, hostile.",
    },
    {
      title: "You get a signed report you can gate on.",
      body: "Pass, fail or partial for each claim, plus a stress-test summary, signed so anyone can verify it.",
    },
  ],
  /** Illustrative — align with the final CLI. */
  terminal: {
    command: "suncly attest https://agent.example.com/.well-known/agent-card.json",
    lines: [
      { kind: "note", text: "// illustrative — align with the final CLI" },
      { kind: "info", text: "reading agent card … ledger-agent v1.4.2" },
      { kind: "info", text: "2 skills, 2 capabilities claimed" },
      { kind: "pass", text: "exercising skills.reconcile-invoices", status: "pass" },
      { kind: "pass", text: "exercising skills.export-report", status: "pass" },
      { kind: "partial", text: "exercising capabilities.streaming", status: "partial" },
      { kind: "fail", text: "exercising capabilities.pushNotifications", status: "fail" },
      { kind: "info", text: "stress-test  1,248 runs · 312 adversarial · 0 crashes · 3 timeouts" },
      { kind: "done", text: "report signed → attestation.json" },
    ],
  },
} as const;

export const product = {
  label: "Product",
  sections: [
    {
      number: "01",
      name: "Attest",
      title: "Test the card, not the pitch.",
      body: "Suncly reads an A2A Agent Card and exercises every skill and capability it declares. Each claim comes back as pass, fail or partial, with the evidence attached.",
    },
    {
      number: "02",
      name: "Stress-test",
      title: "Find out what breaks before your users do.",
      body: "The first Suncly product is a crash-test for agents. Each claimed capability is run under normal inputs and under adversarial ones, and the report records every crash, timeout and wrong answer.",
    },
    {
      number: "03",
      name: "Gate",
      title: "Only attested agents get in.",
      body: "The report is signed, so you can require one. Make a current attestation the condition for an agent to join your network, your registry or your pipeline.",
    },
    {
      number: "04",
      name: "Approve",
      title: "Evidence that travels with the agent.",
      body: "Approval stops being a judgment call. Whoever signs off reads the same signed report, verifies the signature, and sees exactly which claims held.",
    },
  ],
} as const;

export const standard = {
  label: "Open standard",
  headline: "Reads the A2A Agent Card. Emits a signed report.",
  intro:
    "Suncly does not ask you to describe your agent twice. It reads the Agent Card you already publish under the A2A protocol and tests what is in it.",
  reads: {
    title: "What Suncly reads",
    items: [
      { field: "name · description · version · url", note: "who the agent is and where it lives" },
      { field: "capabilities", note: "streaming · pushNotifications · stateTransitionHistory" },
      { field: "skills[]", note: "id · name · description · tags · examples" },
      { field: "defaultInputModes · defaultOutputModes", note: "what it accepts and returns" },
      { field: "securitySchemes", note: "how to authenticate against it" },
    ],
  },
  emits: {
    title: "What Suncly emits",
    items: [
      { field: "claims[]", note: "one result per claim: pass, fail or partial" },
      { field: "stress", note: "runs, adversarial inputs, crashes, timeouts" },
      { field: "signature", note: "so anyone can verify the report" },
    ],
  },
  /** Illustrative — align with the final schema. */
  json: `// illustrative — align with the final schema
{
  "agent": { "name": "ledger-agent", "version": "1.4.2" },
  "card": "https://agent.example.com/.well-known/agent-card.json",
  "claims": [
    { "path": "skills.reconcile-invoices", "result": "pass" },
    { "path": "skills.export-report", "result": "pass" },
    { "path": "capabilities.streaming", "result": "partial" },
    { "path": "capabilities.pushNotifications", "result": "fail" }
  ],
  "stress": {
    "runs": 1248, "adversarial": 312,
    "crashes": 0, "timeouts": 3
  },
  "signature": { "alg": "ed25519", "value": "…" }
}`,
} as const;

export const resources = {
  label: "Developers",
  headline: "Everything you need to ship an attested agent.",
  comingLabel: "Coming",
  cards: [
    { title: "Docs", body: "Install, attest, verify, gate.", href: null },
    { title: "Schema", body: "The attestation report, field by field.", href: null },
    { title: "Example agent", body: "A small A2A agent with a card you can attest.", href: null },
    { title: "Changelog", body: "What changed in each release.", href: null },
  ],
} as const;

export const earlyAccess = {
  headline: "Get early access.",
  body: "Suncly is in early access. Leave your email and we will write to you when your spot opens. No list size, no countdown, just a reply from the team.",
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
      a: "Suncly is an attestation tool for A2A agents. It tests whether an agent actually does what its Agent Card claims, and produces signed evidence for approval.",
    },
    {
      q: "What is an Agent Card?",
      a: "Under the A2A protocol, every agent publishes a JSON Agent Card that lists its name, skills, capabilities and how to reach it. Suncly treats that card as the set of claims to test.",
    },
    {
      q: "Which agents can Suncly attest?",
      a: "Any agent that speaks the A2A protocol and publishes an Agent Card.",
    },
    {
      q: "What does the stress-test do?",
      a: "It runs every claimed capability under normal and adversarial inputs and records crashes, timeouts and wrong answers. It is the first Suncly product.",
    },
    {
      q: "Can I block agents that are not attested?",
      a: "Yes. The report is signed, so you can make a valid attestation a condition for an agent to join your network or pass your pipeline.",
    },
    {
      q: "Is Suncly available today?",
      a: "Suncly is in early access. Leave your email above and we will write to you when your spot opens.",
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
        { label: "Early access", href: "/#early-access" },
        { label: "FAQ", href: "/#faq" },
      ],
    },
    {
      title: "Developers",
      links: [
        { label: "Docs", href: "/docs" },
        { label: "Schema", href: null },
        { label: "Example agent", href: null },
        { label: "Changelog", href: null },
      ],
    },
    {
      title: "Company",
      links: [
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
  headline: "The docs ship with early access.",
  body: "Suncly is an attestation tool for A2A agents. The full documentation (install, attest, verify, gate) will be published here when early access opens. Until then, the landing page explains the model, and the team answers questions at team@suncly.com.",
  cta: { label: "Get early access", href: "/#early-access" },
  back: { label: "Back to the site", href: "/" },
} as const;
