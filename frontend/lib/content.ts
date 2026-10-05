/**
 * All site copy. Mirrors frontend/CONTENT.md, which records the source of every claim:
 * README, SCHEMA, ARCHITECTURE, FLOW, API, POLICY, DECISIONS, ROADMAP, QUICKSTART,
 * IMPLEMENTATION_NOTES, CODE (src/suncly), INPUTS (the founder inputs, lib/launch.ts),
 * RUN (commands run in the build session, VERIFICATION.md), or SAMPLE (lib/sample).
 * Nothing on the site states customers, logos, testimonials, metrics, prices or
 * thresholds. Edit CONTENT.md first.
 *
 * Status words come from lib/capabilities.ts and lib/launch.ts, never from here.
 */

import { launch, PRIMARY_ACTION } from "./launch";

export const site = {
  name: "suncly",
  domain: "https://suncly.com",
  title: "Suncly — Test the agent. Then decide.",
  description:
    "Suncly tests an A2A agent against what its Agent Card claims and hands security and platform teams signed evidence: what passed, what failed, and what was never tested.",
  mission: "Evidence before access.",
  email: "team@suncly.com",
  city: "Tallinn, Estonia",
  copyright: "© 2026 Suncly",
} as const;

export const nav = {
  links: [
    { label: "Offer", href: "/offer" },
    { label: "Data", href: "/data" },
    { label: "Research", href: "/research" },
    { label: "Lab", href: "/lab" },
    { label: "Docs", href: "/docs" },
  ],
  /** Pages that keep their URLs and live in the mobile sheet, the footer and contextual links. */
  more: [
    { label: "Product", href: "/product" },
    { label: "Workflows", href: "/workflows" },
    { label: "Sample evaluation", href: "/demo" },
    { label: "Certified", href: "/certified" },
    { label: "Security", href: "/security" },
    { label: "Access", href: "/access" },
    { label: "Company", href: "/company" },
    { label: "Glossary", href: "/glossary" },
  ],
  workspace: { label: "Open workspace", href: "/app" },
  cta: { label: PRIMARY_ACTION.short, href: PRIMARY_ACTION.href },
  menuOpen: "Menu",
  menuClose: "Close",
} as const;

/* ---------------------------------------------------------------------------------- */
/* Home page: sixteen sections, at most 800 visible words. Sources in CONTENT.md.      */
/* ---------------------------------------------------------------------------------- */

export const hero = {
  eyebrow: "For teams that approve third-party AI agents",
  headline: ["Test the agent.", "Then decide."],
  subhead:
    "Suncly tests an A2A agent against what its Agent Card claims, then hands your reviewers signed evidence: what passed, what failed, and what was never tested.",
  primary: { label: PRIMARY_ACTION.label, href: PRIMARY_ACTION.href },
  secondary: { label: "See a sample evaluation", href: "/demo" },
  /** Word for word from a `suncly demo` run on 2026-10-05 (the lying agent's first line). RUN. */
  caption: "uppercase  hello world  run 1  fail  5 ms  fail: output_modes",
  pictureAlt:
    "Two identical upright cards on a pale plane under one low sun. The left card casts the shadow you would expect. The right card casts a shadow that does not match its shape.",
} as const;

export const worksWith = {
  /** Shown while no tool is verified (lib/launch.ts testedIn). */
  headingUnverified: "Run it from the coding agent you already use",
  headingVerified: "Works with",
  lineUnverified:
    "A command-line tool runs wherever your agent has a terminal. Guided setup for each is planned.",
  disclaimer:
    "Names show where Suncly runs. No partnership, certification or endorsement is implied or exists.",
  tools: [
    { id: "cursor", name: "Cursor" },
    { id: "claude-code", name: "Claude Code" },
    { id: "codex", name: "Codex" },
    { id: "omp", name: "omp" },
    { id: "pi", name: "Pi" },
  ],
} as const;

export const howItWorks = {
  label: "How it works",
  headline: "From an Agent Card to a decision you can defend.",
  note: "Taken from the sample evaluation. The agent is fictional; the evidence is real output.",
  frames: [
    {
      title: "The claim",
      body: "The card says start-return opens a return and emails a label.",
      mono: "skill: start-return · “Start a return for order 48213, item 2”",
    },
    {
      title: "The approved test",
      body: "A named reviewer approves the test plan. Nothing runs before that.",
      mono: "approved_by: m.lind@harbor.example · expected: TASK_STATE_COMPLETED",
    },
    {
      title: "The runs",
      body: "Five runs in a sandbox. All five stop at TASK_STATE_INPUT_REQUIRED.",
      mono: "observed: TASK_STATE_INPUT_REQUIRED · “Which pickup address should the return label use?”",
    },
    {
      title: "The evidence",
      body: "A signed report: 0 of 5 completed, the card unchanged since the last evaluation, and a list of what was not tested. The decision stays with your reviewer.",
      mono: "pass 0 · fail 5 · inconclusive 0 · card re-check: unchanged · decision: flag",
    },
  ],
} as const;

export const install = {
  label: "Install",
  headline: "See it work on your machine.",
  prerequisites: "Python 3.12 or newer, and git.",
  /** RUN: measured on 2026-10-05 (install 20 s, demo 4 s); the clone is the longest step. */
  timing: "About a minute on a developer machine, plus the clone.",
  local:
    "It runs locally, calls only the card URL and the agent endpoint named in the card, and sends nothing to Suncly in this version.",
  next: "Next: evaluate a sandbox agent from its card URL.",
  guide: { label: "Full guide", href: "/docs/getting-started" },
  tabs: ["Terminal", "Cursor", "Claude Code", "Codex", "omp", "Pi"],
  toolPlanned: (tool: string) =>
    `Planned. Until a guided setup exists, run the Terminal steps from ${tool}'s terminal; the human approves the test plan.`,
  demoHeading: "Output of suncly demo, trimmed, not retyped:",
  copied: "Copied",
  copy: "Copy",
} as const;

export const evidence = {
  label: "Evidence",
  headline: "See what passed. See what is still in shadow.",
  body: "One evaluation from the sample set: counts per test case, and the list every report ends with.",
  verify: "Verify it yourself:",
  verifyCommand: "suncly verify <report-folder>",
  link: { label: "Open the full sample", href: "/demo" },
  fixed: "A pass covers these tests, on this sandbox, on this day.",
  notTestedHeading: "What was not tested",
} as const;

export const useCases = {
  label: "Examples",
  headline: "Different agents. The same question.",
  items: [
    {
      title: "Support and returns agents",
      today:
        "Every declared skill completes, answers in the declared format, within the latency limit.",
      outside: "Whether the refund amount is right.",
    },
    {
      title: "Internal workflow agents",
      today: "Required fields and schema in every answer, on repeat.",
      outside: "Behaviour on inputs the card never declared.",
    },
    {
      title: "Procurement and finance agents",
      today: "The sandbox completes the task and nothing real is booked.",
      outside: "Judging the meaning of an answer.",
    },
    {
      title: "A vendor's agent after an update",
      today: "The same approved tests on the new version, counts side by side.",
      outside: "Prompt injection, until probes ship.",
    },
  ],
  todayLabel: "Check today",
  outsideLabel: "Outside, for now",
} as const;

export const offer = {
  label: "Suncly Offer",
  headline: "Pay for what you run.",
  body: "Suncly charges for your usage of the Suncly API and for nothing else. No seats, no plans.",
  free:
    launch.connectingFee === "none" && launch.badgeFee === "none"
      ? "Connecting and the badge are free."
      : null,
  notLive:
    "Billing starts when the API does. Until then, pilot access is arranged with the team.",
  notLiveLink: { label: "Pilot access", href: "/access" },
  liveLink: { label: "What counts as usage", href: "/offer" },
} as const;

export const certified = {
  label: "Suncly Certified",
  eyebrowNotOpen: "Opening with our pilots",
  headline: "A badge with the evidence behind it.",
  body: "Agents that meet Suncly's published criteria can carry the Suncly Certified badge. Every badge links to its record: what was tested, when, on which version, and what was not.",
  link: { label: "The programme", href: "/certified" },
  specimen: "Specimen",
  sealAlt:
    "The Suncly Certified badge, blind-embossed in heavy paper under raking light. A specimen; no agent is certified yet.",
} as const;

export const data = {
  label: "Suncly Data",
  headline: "Know what enters a test, and what leaves it.",
  body: "Suncly runs where you run it. One Runner process holds the credential and redacts every transcript before it is stored. Nothing is sent to Suncly or to a model provider in this version.",
  facts: [
    "Runs locally.",
    "Credential stays in the Runner.",
    "The report folder is yours.",
  ],
  link: { label: "How data is handled", href: "/data" },
  pictureAlt:
    "A closed box with one narrow slit. A single blade of light leaves it toward the lower left.",
} as const;

export const research = {
  label: "Suncly Research",
  headline: "What evidence can tell you, and what it cannot.",
  body: "Notes on what a signed evaluation proves, written from the code and its tests. The first notes are in review.",
  inReview: "In review",
  notes: [
    "What a signed Agent Card proves",
    "Why inconclusive is never a pass",
    "An unchanged card is not an unchanged agent",
  ],
  link: { label: "Research", href: "/research" },
  pictureAlt:
    "Small brass discs pinned to a plaster wall in a figure of eight, each with its own shadow: the sun's analemma.",
} as const;

export const lab = {
  label: launch.labName,
  headline: "Agents that misbehave on purpose.",
  body: `The ${launch.labName} is where tests get built. It ships eleven mock agents, honest, lying, flaky, slow, leaky and more, so you can watch Suncly catch each one before you point it at a real agent.`,
  planned: "Probes and model-based judging",
  link: { label: "Run the Lab", href: "/lab" },
  pictureAlt:
    "Eleven small forms in a row on a plane at golden hour. Most cast true shadows; one casts a wrong shadow, one casts two, one casts none.",
  stripLabel:
    "The eleven mock agents. Choose one to see what Suncly reports for it.",
} as const;

export const stand = {
  headline: "A pass has a scope.",
  forTitle: "What we stand for",
  forItems: [
    "Evidence anyone can re-check.",
    "A human approves the tests and decides.",
    "Inconclusive is never a pass.",
    "Every report says what was not tested.",
    "Sandbox endpoints only.",
  ],
  notTitle: "What a pass or a badge does not mean",
  notItems: [
    "No guarantee of future behaviour.",
    "Nothing about your production endpoint.",
    "Not a security certification, compliance or insurance.",
    "No endorsement by any foundation or vendor.",
    "No substitute for your own approval.",
  ],
  statement:
    "We stand behind what we recorded: the tests that ran, on the version we tested, on the day we tested it. We do not guarantee how an agent behaves afterwards, and certifying an agent does not make Suncly responsible for what it does. Your organisation decides what gets access.",
} as const;

export const questions = {
  label: "Questions",
  items: [
    {
      q: "Is it available today?",
      a: "Yes, as a command-line tool in pilot. From a card URL it drafts a test plan, records your approval, runs the tests against your sandbox, judges every run, signs the evidence and writes a report. The HTTP API, model-based judging and probes are planned.",
    },
    {
      q: "Which agents can it test?",
      a: "Any agent that publishes an A2A 1.0 Agent Card and answers over JSON-RPC, whatever model or framework is behind it. Other bindings, streaming and push notifications are not exercised and are listed in the report as not tested.",
    },
    {
      q: "Does it touch production?",
      a: "No. Nothing runs unless you declare the endpoint a sandbox or dry-run endpoint, and the report records that declaration. Suncly cannot verify a sandbox; the declaration is yours.",
    },
    {
      q: "What does it cost?",
      a: "Usage of the Suncly API, and nothing else. No seats, no plans; connecting and the badge are free. Billing is not live yet and no price is published; pilot access is arranged with the team.",
    },
    {
      q: "What does the badge mean?",
      a: "That a named agent version met Suncly's published criteria on a date, on a sandbox, with the evidence linked from the badge. It is not your approval, not a rating, not a security certification and not a guarantee. The programme opens with our pilots.",
    },
  ],
} as const;

export const closing = {
  headline: ["Bring one agent.", "Leave with evidence."],
  action: { label: "Request pilot access", href: "/access#request" },
  contact: site.email,
  skyAlt: "",
} as const;

export const findSuncly = {
  heading: "Find Suncly",
  note: "Suncly's own profiles. Not partnerships, not endorsements.",
} as const;

export const banner = {
  line: "Evidence before access.",
} as const;

export const finalCta = {
  headline: "Bring one agent. Leave with evidence.",
  body: "Suncly is in pilot. If your team approves A2A agents by hand today, tell us about one agent and one sandbox, and we will run the first evaluation together.",
  primary: { label: "Request pilot access", href: "/access#request" },
  secondary: {
    label: "Read the getting-started guide",
    href: "/docs/getting-started",
  },
} as const;

/** Kept for /product, where the comparison table now lives. */
export const manualVsSuncly = {
  label: "Compared with manual review",
  headline: "The same questions, answered the same way every time.",
  intro:
    "Manual review is not wrong. It is unrepeatable, and its gaps are invisible. Suncly makes the review a recorded procedure.",
  columns: ["", "Manual review", "With Suncly"],
  rows: [
    {
      topic: "What gets tested",
      manual: "Whatever prompts the reviewer thinks of that day.",
      suncly:
        "A test case per declared example of each skill, plus your own criteria, in an approved contract.",
    },
    {
      topic: "How often",
      manual: "Once per approval, usually once per agent.",
      suncly:
        "Every test case runs N times per evaluation; the same contract re-runs on every card version.",
    },
    {
      topic: "Who approved the tests",
      manual: "Nobody, explicitly.",
      suncly:
        "A named person, recorded as approved_by with a timestamp. Approved contracts are immutable.",
    },
    {
      topic: "Evidence",
      manual: "Screenshots and pasted answers in a ticket.",
      suncly:
        "Redacted transcripts with check-by-check results, hashed and signed.",
    },
    {
      topic: "Inconsistent behaviour",
      manual: "Missed unless the reviewer happens to repeat a prompt.",
      suncly:
        "Shows up as a pass count and a fail count for the same test case.",
    },
    {
      topic: "What was not tested",
      manual: "Unknown.",
      suncly: "A required section of every report.",
    },
    {
      topic: "Change since last time",
      manual: "Re-do the review, or trust that nothing changed.",
      suncly:
        "Same card hash, same contract, comparable counts. An unchanged card is not treated as an unchanged agent.",
    },
    {
      topic: "Verification later",
      manual: "Ask the reviewer.",
      suncly: "suncly verify on the report folder, with the public key.",
    },
  ],
} as const;

/** Kept for /product: what Suncly is, and is not. */
export const scopeLines = {
  label: "What Suncly is, and is not",
  headline: "Behavioural evaluation. Not a gateway, not a monitor.",
  items: [
    {
      name: "Behavioural evaluation",
      status: "This is what Suncly does.",
      body: "It sends the declared examples to the agent, repeatedly, and judges each response against explicit criteria. Today the judge is deterministic: structure, state, latency, media types, required fields and schema. Whether an answer is correct in meaning needs the model-based judge of a later stage, and every report says so.",
      tone: "pass",
    },
    {
      name: "Protocol compliance",
      status: "Checked as part of judging, not as a product of its own.",
      body: "Each response is checked to be a well-formed A2A 1.0 Task or Message with a valid state, and the card is checked for the fields the specification requires. Suncly does not run a conformance suite over the whole protocol surface.",
      tone: "inconclusive",
    },
    {
      name: "Runtime monitoring",
      status: "Not offered.",
      body: "Suncly tests a sandbox endpoint before approval. It does not observe production traffic, enforce policies at a gateway, or alert on live behaviour. That is out of scope by design.",
      tone: "neutral",
    },
  ],
} as const;

/** Kept for /product. */
export const limitations = {
  label: "Limitations you should know before buying",
  headline: "What a passing evaluation does and does not tell you.",
  items: [
    "A pass means every deterministic check passed on the sandbox endpoint during this evaluation. It is not a guarantee of future behaviour, and it says nothing about the production endpoint, which is never called.",
    "The signature proves the evidence was not altered after signing and which deployment produced it. It does not prove the agent is correct.",
    "Decisions are flag-only in this version. Suncly never approves or blocks automatically; a human records the decision outside Suncly, and this workspace helps route it.",
    "Suncly cannot verify that an endpoint is a sandbox. Your --sandbox declaration is recorded as a declaration.",
    "Tests come from the examples the card declares. A skill without examples is reported as not tested, because Suncly never invents input.",
    "Prompt-injection, undeclared-behaviour and failure-handling probes are planned, not implemented. Every report lists them under what was not tested.",
  ],
} as const;

export const productPage = {
  title: "Product",
  headline: "Repeatable evaluation. Accountable approval.",
  intro:
    "Suncly turns the approval of an AI agent into a recorded procedure: a reviewed test plan, repeated runs in a sandbox, deterministic verdicts, signed evidence, and an explicit statement of what was not tested.",
  groups: [
    {
      id: "evaluation",
      title: "Evaluation",
      body: "What is tested, how often, and how it is judged.",
    },
    {
      id: "evidence",
      title: "Evidence",
      body: "What is kept, how it is signed, and how it is read later.",
    },
    {
      id: "approval",
      title: "Approval",
      body: "Who decides, on what, and how that is recorded.",
    },
    {
      id: "operations",
      title: "Operations",
      body: "Sandboxes, credentials, budgets and limits.",
    },
    {
      id: "integration",
      title: "Interfaces and integrations",
      body: "How Suncly fits into pipelines and registries.",
    },
  ],
  legend: {
    available:
      "Implemented in the current version and covered by tests. A limit, where one exists, is stated beside it.",
    pilot:
      "Exists and is used with pilots; the wording on this site says what a pilot gets.",
    planned:
      "On the roadmap. No date is promised, and nothing on this site treats it as current.",
  },
} as const;

export const workflowsPage = {
  title: "Supported workflows and integrations",
  headline: "One protocol in. Any model behind it.",
  intro:
    "Suncly evaluates agents through the A2A protocol. It does not integrate with model providers or agent frameworks directly: if an agent publishes an A2A 1.0 Agent Card and answers over JSON-RPC, Suncly can test it, whatever built it. This page states exactly what is inspected and tested, and where coverage differs.",
  protocol: {
    title: "Protocol coverage",
    intro:
      "What the Runner speaks and what the Judge checks. Verified against src/suncly/runner and src/suncly/core.",
    rows: [
      {
        item: "A2A 1.0 over JSON-RPC (HTTP)",
        status: "available",
        note: "SendMessage, then GetTask polling until a terminal or interrupted state. The first supportedInterfaces entry with JSONRPC and 1.0 is used.",
      },
      {
        item: "Agent Card at /.well-known/agent-card.json",
        status: "available",
        note: "Fetched over https (plain http for loopback sandboxes), size-limited, hashed with RFC 8785. Fields the spec requires but the card omits are reported.",
      },
      {
        item: "Direct Message replies",
        status: "available",
        note: "Handled without error. A direct Message counts as completing a task only if the criteria say accept_direct_message.",
      },
      {
        item: "Interrupted states (input or auth required)",
        status: "available",
        note: "Recorded as the final observed state and judged against the expected state. The Runner never invents input to continue.",
      },
      {
        item: "gRPC and HTTP+JSON bindings",
        status: "planned",
        note: "Not spoken. If the card lists them, the report lists them under interfaces not used.",
      },
      {
        item: "Streaming, push notifications, extended cards, extensions",
        status: "planned",
        note: "Not exercised. A card that declares them gets a 'declared capability not exercised' line in the report.",
      },
      {
        item: "Authentication to the agent",
        status: "available",
        note: "One Authorization header value from an environment variable read only by the Runner. Other security schemes the card declares are kept as opaque fields and not negotiated.",
      },
    ],
  },
  models: {
    title: "Model providers",
    intro:
      "Suncly is model-agnostic. It never calls a model provider in this version, and it does not need to know which model an agent uses. An agent built on any of these, or on none of them, is tested the same way through its A2A interface.",
    names: [
      "Claude",
      "OpenAI GPT and Codex",
      "Grok",
      "Gemini",
      "Llama",
      "Mistral",
      "DeepSeek",
      "Qwen",
      "Cohere",
      "Open-source and fine-tuned models",
    ],
    disclaimer:
      "Names are listed to illustrate that the model does not matter to Suncly. They are trademarks of their owners; no partnership, certification or endorsement is implied or exists.",
    futureNote:
      "Later stages add a model-based drafter and a model-based judge. Those will use your own model keys and a pinned judge model; the choice of provider is yours.",
  },
  frameworks: {
    title: "Agent frameworks and coding tools",
    intro:
      "What matters is whether the thing you want to evaluate exposes an A2A endpoint.",
    rows: [
      {
        item: "Any framework that serves an A2A 1.0 Agent Card and JSON-RPC endpoint",
        status: "available",
        note: "Point suncly attest at the card URL of its sandbox deployment.",
      },
      {
        item: "Agents that only expose a chat or vendor-specific API",
        status: "planned",
        note: "Not reachable until they are wrapped in an A2A server. Suncly adds no other transports in this version.",
      },
      {
        item: "Coding assistants and IDE agents",
        status: "planned",
        note: "They are not A2A agents by themselves. To evaluate one, run it behind an A2A server in a sandbox and declare that sandbox.",
      },
    ],
  },
  integrations: {
    title: "Integrations and interfaces",
    intro: "Where results go, and how Suncly is driven.",
  },
  mocks: {
    title: "Bundled sandbox agents",
    intro:
      "Eleven mock A2A agents ship with the package for the demo and the end-to-end tests. Each one models a behaviour the evaluation has to handle correctly. They are sandboxes by construction and run on your machine.",
    rows: [
      ["honest", "Does what its card says.", "every run passes"],
      [
        "honest-async",
        "Completes asynchronously; the client has to poll GetTask.",
        "every run passes after polling",
      ],
      [
        "lying",
        "Declares text/plain output but answers with JSON.",
        "every run fails output_modes",
      ],
      [
        "flaky",
        "Succeeds on odd calls, fails on even calls.",
        "an exact mix of pass and fail",
      ],
      [
        "slow",
        "Answers correctly after the latency limit.",
        "every run fails the latency limit",
      ],
      [
        "unreachable",
        "Its endpoint refuses connections.",
        "no run passes; runs are inconclusive",
      ],
      [
        "direct-message",
        "Replies with a Message instead of a Task.",
        "handled; not a pass",
      ],
      [
        "interrupted",
        "Always asks for more input.",
        "fail on final state; never a pass",
      ],
      [
        "leaky",
        "Echoes the Authorization header back.",
        "the credential appears nowhere",
      ],
      [
        "card-changer",
        "Changes its card during the run.",
        "the attestation ends invalidated",
      ],
      [
        "no-examples",
        "One skill declares no examples.",
        "that skill is listed as not tested",
      ],
    ],
  },
} as const;

export const demoPage = {
  title: "Sample evaluation",
  eyebrow: "Sample data · fictional agent · produced by the real code path",
  headline: "One agent, three evaluations, nothing hidden.",
  intro:
    "Harbor Returns Agent is fictional. The evaluations below were produced by running Suncly against a local mock of it, with the contract approved as a fictional reviewer. The hashes, verdicts, transcripts and signatures are real output of the software; the agent, the orders and the people are not real. Nothing here is a customer evaluation.",
  story: [
    {
      key: "1-baseline",
      title: "Evaluation 1: the baseline",
      body: "Four skills declared. Three have examples and get test cases; cancel-order declares none and is reported as not tested. order-status and start-return pass every run. refund-estimate is inconclusive on every run: its criteria include a check about the amount that only a model-based judge could decide, and that judge does not exist yet.",
    },
    {
      key: "2-regression",
      title: "Evaluation 2: the card is unchanged, the agent is not",
      body: "Same card hash, so the same approved contract runs again. start-return now stops at TASK_STATE_INPUT_REQUIRED on every run. The second order-status example fails two runs in five: the agent is inconsistent, which five repetitions make visible and one manual prompt would not.",
    },
    {
      key: "3-budget-stop",
      title: "Evaluation 3: the budget stops it",
      body: "The same agent with a budget of 7 attempts for 20 planned runs. Suncly stops starting runs when the budget is reached, ends the attestation as failed, lists the 13 runs never executed, and records no decision. A failed attestation is never an approval.",
    },
  ],
  reviewer: {
    title: "The reviewer's decision (sample)",
    note: "Human decisions are not yet recorded inside Suncly (planned, stage 5). This is what a reviewer records in the workspace and exports with the signed report.",
    record: {
      decision: "block",
      reviewer: "m.lind@harbor.example",
      rationale:
        "start-return no longer completes from a single message: all five runs stop at input-required, while evaluation 1 completed five of five against the same card. order-status is inconsistent on the shipping question (3 pass, 2 fail with upstream timeouts). refund-estimate remains inconclusive pending a semantic check. Block until the returns flow completes without extra input; re-evaluate with the same contract.",
    },
  },
  untested: {
    title: "What remains untested, in the reviewer's words",
    items: [
      "cancel-order: the card declares no examples, so there is no test case. Ask the team for examples or write them into the contract file.",
      "Whether refund amounts are correct: needs the model-based judge (stage 4). Until then the check is inconclusive by design.",
      "Streaming: declared by the card, never exercised.",
      "Prompt injection and behaviour outside the declared skills: probes are not implemented.",
      "The production endpoint: tests ran against the declared sandbox only.",
    ],
  },
} as const;

export const securityPage = {
  title: "Security and data handling",
  headline: "What Suncly touches, where it runs, and what it keeps.",
  intro:
    "Everything on this page is verified against the current implementation. Where behaviour is a proposal still open for a founders' decision, it says so. Suncly is a command-line tool you run yourself; there is no hosted service in this version.",
} as const;

export const accessPage = {
  title: "Access",
  headline: "Pilot access, arranged with the team.",
  intro:
    "Suncly is in pilot. There is no self-serve sign-up and no published price list yet. A payment layer is planned; until it exists, access is arranged by email and nothing on this site collects payment details.",
  whatYouGet: {
    title: "What a pilot includes",
    items: [
      "The suncly command for your team, from the public repository.",
      "A first evaluation of one of your agents against its sandbox endpoint, run together with us.",
      "The report folder, the signed evidence and the verify command for your reviewers.",
      "A direct line to the team for the open questions that affect you: policy thresholds, credentials, registries.",
    ],
  },
  whatYouNeed: {
    title: "What you need",
    items: [
      "An agent that publishes an A2A 1.0 Agent Card and answers over JSON-RPC.",
      "A sandbox or dry-run endpoint for it. Suncly never tests production.",
      "A machine with Python 3.12 or newer, inside your network if you prefer. Nothing leaves it.",
    ],
  },
  billing: {
    title: "Billing",
    body: "No price is published and no checkout exists. When the payment layer is ready, it will attach to accounts and usage; until then, terms are agreed per pilot by email.",
  },
  form: {
    headline: "Request pilot access",
    body: "Leave a work email and, if you like, one line about the agent you want to evaluate. We write back from Tallinn; there is no list size and no countdown.",
    fieldLabel: "Work email",
    placeholder: "you@company.com",
    noteLabel: "What would you evaluate first? (optional)",
    notePlaceholder: "One agent, one sandbox, one question.",
    button: "Request access",
    sending: "Sending",
    success: "Thanks. We will be in touch.",
    error: "That did not go through. Email us at team@suncly.com instead.",
  },
} as const;

export const companyPage = {
  title: "Company",
  headline:
    "A small team in Tallinn, building the inspection step for AI agents.",
  intro:
    "Suncly is built for the platform and security teams that have to say yes or no to an agent. We write the architecture down before the code, we keep the open questions visible, and we would rather ship a report that says 'not tested' than a score that hides it.",
  principles: [
    {
      title: "Approve less, never more.",
      body: "Every fault in the system is designed to make Suncly approve less. Inconclusive is never a pass; no decision is never an approval.",
    },
    {
      title: "Evidence over scores.",
      body: "Counts per test case, transcripts, hashes and a signature. No universal score, because a score would hide what was not tested.",
    },
    {
      title: "A human stays in the loop.",
      body: "A person approves the test plan. A person resolves a flag. Suncly records who, and when.",
    },
  ],
  contact: {
    title: "Contact",
    email: "team@suncly.com",
    location: "Tallinn, Estonia",
    registration:
      "Company registration details will be published on the legal notice once supplied.",
  },
  faq: [
    {
      q: "What is Suncly?",
      a: "Suncly is an evaluation tool for AI agents that speak the A2A (Agent2Agent) protocol. It reads an agent's Agent Card, tests every declared skill repeatedly in a sandbox, judges each run deterministically, signs the evidence, and reports what passed, what failed, what stayed inconclusive and what was never tested.",
    },
    {
      q: "Who is Suncly for?",
      a: "Platform and security teams that approve AI agents for use in their organisation and currently do that review by hand.",
    },
    {
      q: "Is Suncly a model or an agent?",
      a: "Neither. Suncly is a command-line evaluation tool that tests agents built on any model or framework through their A2A interface. In the current version it calls no model provider at all.",
    },
    {
      q: "Where is Suncly based?",
      a: "Tallinn, Estonia. Contact the team at team@suncly.com.",
    },
    {
      q: "How is Suncly pronounced and spelled?",
      a: "Sun-clee, one word, capital S: Suncly. The domain is suncly.com.",
    },
  ],
} as const;

export const docsPage = {
  title: "Documentation",
  headline: "Written down before the code. Kept current with it.",
  intro:
    "The repository carries the architecture schema, the component, data model, flow, policy and decision documents, the implementation notes, and a quickstart. The repository is public; these pages carry the parts you need to get started, and the full documents are in the repository.",
  guides: [
    {
      href: "/docs/getting-started",
      title: "Getting started",
      body: "Install, run the bundled demo, evaluate your own sandbox agent, read and verify the report. Five minutes.",
    },
    {
      href: "/docs/cli",
      title: "Command reference",
      body: "suncly attest, demo, verify, keys, db and doctor, every option, every exit code, and the contract file format.",
    },
    {
      href: "/docs/evidence",
      title: "Evidence and reports",
      body: "What a report folder contains, what the signature covers, how to verify it, and how to load it into the workspace.",
    },
  ],
  repositoryDocs: [
    {
      file: "SCHEMA.md",
      title: "Architecture schema",
      body: "System layout, components, data model, main flow, default approval policy, interfaces, stack, the non-negotiable rules, build order, and what is out of scope. The source of truth.",
    },
    {
      file: "docs/QUICKSTART.md",
      title: "Quickstart",
      body: "Install, run the demo, attest your own sandbox agent, read and verify a report, use Postgres, troubleshoot.",
    },
    {
      file: "docs/ARCHITECTURE.md",
      title: "Architecture",
      body: "Each component's responsibility, inputs, outputs, what it must never do, and how it fails safely. The A2A protocol facts Suncly depends on.",
    },
    {
      file: "docs/CODE_ARCHITECTURE.md",
      title: "Code architecture",
      body: "How the code maps to the components: layers, the Runner boundary, where to add what, and the tests that enforce the boundaries.",
    },
    {
      file: "docs/DATA_MODEL.md",
      title: "Data model",
      body: "The seven entities: agent, card_version, contract, test_case, attestation, run, decision. Fields, keys, enums, invariants.",
    },
    {
      file: "docs/FLOW.md",
      title: "Attestation flow",
      body: "One attestation from trigger to result, the status lifecycle, and every failure path.",
    },
    {
      file: "docs/API.md",
      title: "Interfaces",
      body: "The CLI with its options and exit codes, the contract file format, and the proposed HTTP endpoints.",
    },
    {
      file: "docs/POLICY.md",
      title: "Approval policy",
      body: "Risk levels, decision outcomes, when a human is required, and how inconclusive results count.",
    },
    {
      file: "docs/DECISIONS.md",
      title: "Decision records",
      body: "The seven non-negotiable rules, each with its decision, reason and consequences.",
    },
    {
      file: "docs/ROADMAP.md",
      title: "Roadmap",
      body: "The six build stages, what the current version implements, and what it does not.",
    },
    {
      file: "docs/IMPLEMENTATION_NOTES.md",
      title: "Implementation notes",
      body: "Every proposal the code implements, every choice that still needs a decision, and the facts that were verified.",
    },
  ],
  howToRead: {
    title: "How the documents are written",
    items: [
      "Where a document and the schema disagree, the schema wins.",
      "Behaviour the schema does not define is marked Proposed and tracked as an open question. No document decides silently.",
      "Numeric thresholds are deliberately absent. They are configured per customer and per risk level, and do not exist yet.",
      "Every report lists the proposals in effect for that run.",
    ],
  },
} as const;

export const legal = {
  draftNotice:
    "Draft. This page is complete in form and describes how the software, the website and the company handle things today, verified against the implementation. It stays a draft, and off search engines, until the facts named below exist and a qualified lawyer has signed it off.",
  pending: "to be supplied",
} as const;

/** The home page FAQ now lives in `questions`; this keeps the longer set for /company and /product. */
export const faq = {
  label: "FAQ",
  headline: "Questions buyers ask.",
  items: [
    {
      q: "Is Suncly available today?",
      a: "Yes, as a command-line tool in pilot. From a card URL it drafts a test plan, records your approval, runs the tests repeatedly against your sandbox, judges every run, records a flag decision, signs the attestation and writes a report. The HTTP API, model-based judging, probes and automatic approve or block decisions are planned stages, not current features.",
    },
    {
      q: "Which agents can it evaluate?",
      a: "Any agent that publishes an A2A 1.0 Agent Card and answers over JSON-RPC, whatever model or framework is behind it. Other A2A bindings, streaming and push notifications are not exercised yet and are listed in the report as not tested.",
    },
    {
      q: "Does Suncly call my production agent?",
      a: "No. Nothing runs unless you declare the endpoint a sandbox or dry-run endpoint, and the report records that declaration. Suncly cannot verify a sandbox; the declaration is yours.",
    },
    {
      q: "Where do my credentials go?",
      a: "Into one environment variable that only the Runner process reads. The Runner redacts the credential, sensitive headers and known token patterns from every transcript before it leaves the process. A test proves no other module reads the variable.",
    },
    {
      q: "Does Suncly send anything to a model provider?",
      a: "Not in this version. Drafting is deterministic and judging is deterministic. Later stages will use your own model keys for a model-based drafter and judge.",
    },
    {
      q: "What does a decision look like?",
      a: "Every completed evaluation gets one signed decision record from the Policy engine. Without a configured policy the outcome is always flag, so a human reviews every result. Approve and block are never produced automatically yet.",
    },
    {
      q: "Can I compare two evaluations?",
      a: "An unchanged card reuses its approved contract, so two evaluations run the same tests and their counts are comparable. The workspace shows the comparison test case by test case. It is computed from the two signed bundles; Suncly's store has no comparison operation of its own yet.",
    },
    {
      q: "Does it produce a score?",
      a: "No. Counts per test case, never combined, and inconclusive runs are counted separately. A score would hide what was not tested.",
    },
    {
      q: "What does it cost?",
      a: "Usage of the Suncly API, and nothing else. No seats, no plans; connecting and the badge are free. Billing is not live yet and no price is published; pilot access is arranged with the team.",
    },
  ],
} as const;

export const footer = {
  groups: [
    {
      title: "Product",
      links: [
        { label: "How it works", href: "/#how" },
        { label: "Install", href: "/#install" },
        { label: "Offer", href: "/offer" },
        { label: "Certified", href: "/certified" },
        { label: "Sample evaluation", href: "/demo" },
        { label: "Workspace", href: "/app" },
      ],
    },
    {
      title: "Learn",
      links: [
        { label: "Docs", href: "/docs" },
        { label: "Research", href: "/research" },
        { label: "Lab", href: "/lab" },
        { label: "Data", href: "/data" },
        { label: "Glossary", href: "/glossary" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "Company", href: "/company" },
        { label: "Access", href: "/access" },
        { label: "Contact", href: "mailto:team@suncly.com" },
        { label: "Security", href: "/security" },
      ],
    },
    {
      title: "Legal",
      links: [
        { label: "Privacy", href: "/privacy" },
        { label: "Terms", href: "/terms" },
        { label: "Certification Policy", href: "/certified/policy" },
        { label: "Cookies", href: "/cookies" },
        { label: "Legal notice", href: "/legal" },
      ],
    },
  ],
  /** Checked against the Linux Foundation's guidance as far as it could be reached (REDESIGN_PLAN.md §12.3); confirm on the day. */
  attribution:
    "Agent2Agent (A2A) is an open-source project of the Linux Foundation. Suncly is independent and is not affiliated with, endorsed by or certified by the Linux Foundation or the A2A project. Other names belong to their owners.",
} as const;

/* ---------------------------------------------------------------------------------- */
/* New pages                                                                           */
/* ---------------------------------------------------------------------------------- */

export const offerPage = {
  title: "Offer",
  headline: "Usage of the Suncly API. Nothing else.",
  intro:
    "Suncly charges for a customer's usage of the Suncly API: no seats and no plans. Connecting costs nothing and the badge is free. Billing is not live; when it starts, the unit and the price will be published here first.",
  sections: {
    get: {
      title: "What you get",
      items: [
        "The suncly command, from the public repository, for your team.",
        "Signed evidence your reviewers can verify offline with suncly verify.",
        "The Suncly Certified badge when an agent earns it, once the programme opens.",
      ],
    },
    connect: {
      title: "What you connect",
      items: [
        "An agent that publishes an A2A 1.0 Agent Card and answers over JSON-RPC.",
        "A sandbox or dry-run endpoint for it. Suncly never tests production.",
        "Once the API exists: an API key for your organisation.",
      ],
    },
    usage: {
      title: "What counts as usage",
      body: "Calls to the Suncly API. The billable unit, the rate schedule and the billing period are not yet published; the Terms will carry them when they are.",
    },
    never: {
      title: "What is never charged",
      items: [
        "Connecting an agent.",
        "The badge.",
        "Running the command-line tool on your own machines.",
        "Reading or verifying a report.",
      ],
    },
    invoices: {
      title: "Invoices and VAT",
      body: "Invoices will be issued by the legal entity named on the legal notice, with VAT where it applies. Payment method and period: not yet published.",
    },
    stop: {
      title: "How to stop",
      body: "Stop calling the API. There is no plan to cancel and no minimum term; the Terms describe notice for any change to charging.",
    },
  },
} as const;

export const certifiedPage = {
  title: "Certified",
  headline: "A badge with the evidence behind it.",
  intro:
    "Suncly Certified is a private, voluntary programme. It is Suncly's statement that a named agent version met a named, published set of criteria on a date, on a sandbox. It is not the customer's approval, not a rating and not a tier.",
  state:
    "The programme opens with our pilots. No criteria are published as accepted yet, and no agent is certified.",
  registry: { title: "Registry", empty: "No agents are certified yet." },
  badge: {
    title: "The badge",
    intro:
      "Circular, with the words suncly certified on a circular path and the sun mark at the centre. One notch at the brand angle. Versions for paper, for dusk and in one colour.",
    files: [
      { label: "Paper, SVG", href: "/brand/badge/suncly-certified-paper.svg" },
      { label: "Dusk, SVG", href: "/brand/badge/suncly-certified-dusk.svg" },
      {
        label: "One colour, SVG",
        href: "/brand/badge/suncly-certified-mono.svg",
      },
      {
        label: "Paper, PNG 512",
        href: "/brand/badge/suncly-certified-paper-512.png",
      },
      {
        label: "Dusk, PNG 512",
        href: "/brand/badge/suncly-certified-dusk-512.png",
      },
    ],
    rules: [
      "Show it unaltered: no recolouring, cropping, rotation, effects or added words.",
      "Only for the certified agent version, only while the record is valid.",
      "Always linked to its record at suncly.com/certified/<id>.",
      "At least 64 px wide; 96 to 128 px is the normal size; clear space of a quarter of its width on every side.",
      "Never next to words such as guaranteed, secure, safe, compliant or approved by.",
      "No trade mark symbol on the badge.",
    ],
  },
  record: {
    title: "What a record shows",
    items: [
      "The agent and its operator",
      "The sandbox endpoint tested",
      "The card hash and the A2A version",
      "The date and the run counts",
      "The criteria version",
      "What was not tested",
    ],
  },
  limits: {
    title: "What a badge does not mean",
    items: [
      "No guarantee of future behaviour.",
      "Nothing about the production endpoint, which is never tested.",
      "Not a security certification, legal compliance, conformity assessment or insurance.",
      "No endorsement by the Linux Foundation, the A2A project or any vendor.",
      "No substitute for your organisation's own approval.",
    ],
  },
} as const;

export const dataPage = {
  title: "Data",
  headline: "Know what enters a test, and what leaves it.",
  intro:
    "How Suncly handles data, verified against the code. The command-line tool runs where you run it and sends nothing to Suncly in this version. Suncly Data is how data is handled; it is not a dataset, and nothing you test trains anything.",
  inventory: {
    title: "Inventory",
    columns: [
      "What",
      "Where it is stored",
      "Who can read it",
      "How to delete it",
    ],
    rows: [
      [
        "The Agent Card you point Suncly at",
        "The evidence store (files under ~/.suncly/store, or your Postgres)",
        "Whoever can read that store",
        "Remove the files or drop the database",
      ],
      [
        "The test plan and its approval (contract, test cases, approved_by)",
        "The evidence store",
        "Whoever can read that store",
        "Remove the files or drop the database",
      ],
      [
        "Redacted transcripts of every run",
        "~/.suncly/transcripts on the machine that ran it",
        "Whoever can read that folder",
        "Remove the files",
      ],
      [
        "Your agent credential",
        "Only the Runner process, from one environment variable; never written",
        "Nobody; it is redacted from every transcript",
        "Unset the variable",
      ],
      [
        "The deployment signing key",
        "~/.suncly/keys",
        "Whoever can read that folder",
        "Delete the key; earlier reports still verify with the public key in result.json",
      ],
      [
        "Report folders",
        "./suncly-reports/<attestation-id>/",
        "Whoever you give them to",
        "Delete the folder",
      ],
    ],
  },
  anatomy: {
    title: "Anatomy of a report folder",
    rows: [
      [
        "report.html",
        "The report for a reviewer. Self-contained; opens offline.",
      ],
      ["report.md", "The same content as Markdown."],
      [
        "result.json",
        "The evidence bundle: attestation, runs, decisions, card version, contract, results, the signed payload and the public key.",
      ],
      [
        "transcripts/<run-id>.json",
        "One redacted transcript per run, with its Layer 1 checks.",
      ],
    ],
  },
  deletion: {
    title: "Deletion, truthfully",
    body: "The evidence store is append-only by design: run and decision records are never updated or deleted by the software. You delete by removing files or dropping the database. For a hosted service, append-only evidence and erasure requests will need a documented answer; that question is open and recorded in HANDOFF.md.",
  },
  hosted: {
    title: "What changes when the hosted API arrives",
    items: [
      "Evidence for hosted evaluations would be stored by Suncly, under a data processing agreement, with a published sub-processor list.",
      "Accounts and API keys would exist; the Privacy Policy's hosted sections switch on then.",
      "The Runner is designed to run inside your network later, so credentials can stay there.",
    ],
  },
} as const;

export const researchPage = {
  title: "Research",
  headline: "What evidence can tell you, and what it cannot.",
  intro:
    "Short notes on what a signed evaluation proves, drafted strictly from facts the repository verifies. Every note carries its author, date, method, limits and sources. No findings, benchmarks, citations or partners are invented.",
  state:
    "The first three notes are drafts in founder review and are not published yet.",
  drafts: [
    {
      title: "What a signed Agent Card proves",
      summary:
        "A signature on a card shows who published it and that it was not altered. It says nothing about how the agent behaves.",
    },
    {
      title: "Why inconclusive is never a pass",
      summary:
        "A check the judge cannot decide is reported separately, and a test case cannot pass on inconclusive runs.",
    },
    {
      title: "An unchanged card is not an unchanged agent",
      summary:
        "The same card hash reuses the same approved tests; the counts can still move, and that is the point of re-running them.",
    },
  ],
} as const;

export const labPage = {
  title: "Lab",
  headline: "Agents that misbehave on purpose.",
  intro: `The ${launch.labName} is where tests get built. Eleven mock A2A agents ship with the package; each models a behaviour the evaluation has to handle. They run on your machine and are sandboxes by construction.`,
  run: {
    title: "Run a mock agent",
    body: "Start one in a second terminal, then evaluate it from its card URL. Any of the eleven names works in place of honest.",
  },
  sample: {
    title: "The sample generator",
    body: "frontend/scripts/make-sample.py runs the real attestation code path against a fictional local agent and writes the three sample bundles the site shows. It fails if the fake credential appears in any transcript.",
  },
  contract: {
    title: "Example contract file",
    body: "Export the draft, edit it, run with the file. The example below is the sample agent's contract: four test cases, one skill without a test case, structural criteria only.",
  },
  planned: [
    "Prompt-injection, undeclared-behaviour and failure-handling probes (stage 4)",
    "Model-based judging for criteria Layer 1 cannot decide (stage 4)",
  ],
} as const;

export const cookiesPage = {
  title: "Cookies",
  headline: "This site sets no cookies.",
  intro:
    "Inspected in the built site on 2026-10-05 with a browser automation script: no cookie is set, no third-party request is made, and no analytics runs. The one thing stored is the review workspace's own data, in your browser, at your request.",
  tableCaption: "Browser storage used by suncly.com, as inspected",
  columns: ["Name", "Type", "Set by", "Purpose", "Duration", "Third parties"],
  rows: [
    [
      "suncly.workspace.v1 (local storage)",
      "localStorage, first party",
      "The review workspace at /app, only when you load a report or the sample",
      "Keeps the evaluation bundles and review notes you load, so they survive a reload",
      "Until you clear the workspace in its settings or clear site data",
      "None",
    ],
  ],
  consent:
    "Nothing non-essential is stored or read, so no consent banner is shown. If anything non-essential is ever added, a real choice with equal Accept and Reject comes first.",
} as const;

export const legalNoticePage = {
  title: "Legal notice",
  headline: "Who runs this site.",
  intro:
    "The company details the Information Society Services Act and the Commercial Code ask for, and a summary in Estonian of what Suncly offers.",
  estonianTitle: "Kokkuvõte eesti keeles",
  /** Draft for founder review (Language Act): a summary in Estonian of the field of activity. */
  estonian:
    "Suncly on tarkvara, millega platvormi- ja turvameeskonnad testivad A2A (Agent2Agent) protokolli kõnelevaid tehisintellekti agente enne, kui neile ligipääs antakse. Suncly loeb agendi Agent Cardi, käivitab iga deklareeritud oskuse testid liivakastis korduvalt, hindab iga käivituse deterministlikult, allkirjastab tõendid ja koostab aruande, mis ütleb, mis läbis, mis ebaõnnestus ja mida ei testitud. Praeguses versioonis on Suncly käsurea tööriist, mis töötab kliendi enda masinas ja ei saada Sunclyle andmeid.",
} as const;
