/**
 * All site copy. Mirrors frontend/CONTENT.md, which records the source of every claim:
 * README, SCHEMA, ARCHITECTURE, FLOW, API, POLICY, DECISIONS, ROADMAP, QUICKSTART,
 * IMPLEMENTATION_NOTES, CODE (src/suncly), BRIEF, or SAMPLE (frontend/lib/sample).
 * Nothing on the site states customers, logos, testimonials, metrics, prices or
 * thresholds. Edit CONTENT.md first.
 */

export const site = {
  name: "suncly",
  domain: "https://suncly.com",
  title: "Suncly — Evaluate AI agents before you approve them",
  description:
    "Suncly tests what an A2A agent claims in its Agent Card, repeatedly, in a sandbox, and gives platform and security teams signed evidence to approve on, including what was not tested.",
  mission: "Evaluate AI agents before you approve them.",
  email: "team@suncly.com",
  city: "Tallinn, Estonia",
  copyright: "© 2026 Suncly",
} as const;

export const nav = {
  links: [
    { label: "Product", href: "/product" },
    { label: "Workflows", href: "/workflows" },
    { label: "Sample evaluation", href: "/demo" },
    { label: "Security", href: "/security" },
    { label: "Docs", href: "/docs" },
    { label: "Access", href: "/access" },
  ],
  workspace: { label: "Open workspace", href: "/app" },
  cta: { label: "Request pilot access", href: "/access#request" },
  menuOpen: "Menu",
  menuClose: "Close",
} as const;

export const hero = {
  eyebrow: "For platform and security teams that approve AI agents",
  headline: ["Evaluate agents", "before you approve them."],
  subhead:
    "Suncly reads what an A2A agent claims, tests every claim repeatedly in a sandbox, and hands your reviewers signed evidence: what passed, what failed, what stayed inconclusive, and what was never tested.",
  primary: { label: "Request pilot access", href: "/access#request" },
  secondary: { label: "Explore the sample evaluation", href: "/demo" },
  previewCaption:
    "A completed evaluation from the sample data set: the agent's card is unchanged since the previous run, its behaviour is not.",
} as const;

export const problem = {
  label: "The gap",
  headline: "An Agent Card is a list of claims. Approval is still a spreadsheet.",
  cards: [
    {
      title: "The protocol describes. Nothing verifies.",
      body: "Under the A2A protocol an agent publishes a card that names its skills. The specification defines how to describe a skill; it has no mechanism for checking that the agent performs it. A signed card proves who published it, not how it behaves.",
    },
    {
      title: "So review happens by hand.",
      body: "Someone reads the card, sends a few prompts, pastes the answers into a ticket, and signs off. The prompts are different every time, the evidence is scattered, and nobody can say what was not tried.",
    },
    {
      title: "And it is not repeated.",
      body: "The agent changes behind an unchanged card. The approval from three months ago still stands, because re-doing the manual review costs a day.",
    },
  ],
} as const;

export const chain = {
  label: "From claim to decision",
  headline: "One claim, followed to a decision.",
  intro:
    "Taken from the sample evaluation. The agent is fictional; the run, the verdicts, the evidence and the signature are produced by Suncly.",
  steps: [
    {
      title: "The claim",
      body: "The Agent Card of Harbor Returns Agent declares a skill, start-return: “Opens a return for one or more items of a delivered order and emails a prepaid label.” It gives one example: “Start a return for order 48213, item 2”.",
    },
    {
      title: "The approved test",
      body: "Suncly drafts a test case from that example. Expected: the task reaches TASK_STATE_COMPLETED, answers in text/plain within 2000 ms, and the answer text is present. A reviewer approves the contract; their identifier is recorded.",
    },
    {
      title: "The observed result",
      body: "Five runs. Every run ends in TASK_STATE_INPUT_REQUIRED: the agent asks “Which pickup address should the return label use?” and never completes. Verdict: fail, five of five. The previous evaluation of the same card passed five of five.",
    },
    {
      title: "The evidence",
      body: "Each run keeps its redacted transcript: the request, the response, the final task state, the latency, and the checks with expected and observed values. The hash of every transcript is in the signed payload.",
    },
    {
      title: "The decision",
      body: "The Policy engine records flag, because no policy is configured and a human must review. The reviewer reads the evidence, records a decision with a rationale, and the signed report travels with it.",
    },
  ],
} as const;

export const process = {
  label: "How an evaluation works",
  headline: "Six steps, each one recorded.",
  steps: [
    {
      title: "Point Suncly at the Agent Card",
      body: "It fetches the card over https, keeps it byte for byte and hashes it. The hash pins everything that follows to this exact version of the claims.",
    },
    {
      title: "Review the test plan",
      body: "One test case per declared example of each skill, with structural criteria. Export it, add your own required fields, schema or latency limits, and approve it under your name. Nothing runs before that.",
    },
    {
      title: "Run it repeatedly, in a sandbox",
      body: "Each test case runs several times from an isolated Runner process. You declare the endpoint a sandbox; without the declaration nothing runs. Every attempt counts against a budget.",
    },
    {
      title: "Judge every run deterministically",
      body: "Valid A2A response, expected final state, latency, content present, declared output modes, required fields, schema. Pass, fail or inconclusive. Inconclusive is never a pass.",
    },
    {
      title: "Sign the evidence",
      body: "Counts per test case, the card hash, the contract version, the hash of every transcript and the decision are signed with the deployment's Ed25519 key. suncly verify re-checks a report offline.",
    },
    {
      title: "Decide, with the gaps in view",
      body: "The report states what was not tested. The Policy engine records a decision, flag in this version, and your reviewer decides on the evidence.",
    },
  ],
} as const;

export const manualVsSuncly = {
  label: "Compared with manual review",
  headline: "The same questions, answered the same way every time.",
  intro:
    "Manual review is not wrong. It is unrepeatable, and its gaps are invisible. Suncly makes the review a recorded procedure.",
  columns: ["", "Manual review", "With Suncly"],
  rows: [
    { topic: "What gets tested", manual: "Whatever prompts the reviewer thinks of that day.", suncly: "A test case per declared example of each skill, plus your own criteria, in an approved contract." },
    { topic: "How often", manual: "Once per approval, usually once per agent.", suncly: "Every test case runs N times per evaluation; the same contract re-runs on every card version." },
    { topic: "Who approved the tests", manual: "Nobody, explicitly.", suncly: "A named person, recorded as approved_by with a timestamp. Approved contracts are immutable." },
    { topic: "Evidence", manual: "Screenshots and pasted answers in a ticket.", suncly: "Redacted transcripts with check-by-check results, hashed and signed." },
    { topic: "Inconsistent behaviour", manual: "Missed unless the reviewer happens to repeat a prompt.", suncly: "Shows up as a pass count and a fail count for the same test case." },
    { topic: "What was not tested", manual: "Unknown.", suncly: "A required section of every report." },
    { topic: "Change since last time", manual: "Re-do the review, or trust that nothing changed.", suncly: "Same card hash, same contract, comparable counts. An unchanged card is not treated as an unchanged agent." },
    { topic: "Verification later", manual: "Ask the reviewer.", suncly: "suncly verify on the report folder, with the public key." },
  ],
} as const;

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

export const finalCta = {
  headline: "Run the first evaluation with us.",
  body: "Suncly is in pilot. If your team approves A2A agents by hand today, tell us about one agent and one sandbox, and we will run the first evaluation together.",
  primary: { label: "Request pilot access", href: "/access#request" },
  secondary: { label: "Read the getting-started guide", href: "/docs/getting-started" },
} as const;

export const productPage = {
  title: "Product",
  headline: "Repeatable evaluation. Accountable approval.",
  intro:
    "Suncly turns the approval of an AI agent into a recorded procedure: a reviewed test plan, repeated runs in a sandbox, deterministic verdicts, signed evidence, and an explicit statement of what was not tested.",
  groups: [
    { id: "evaluation", title: "Evaluation", body: "What is tested, how often, and how it is judged." },
    { id: "evidence", title: "Evidence", body: "What is kept, how it is signed, and how it is read later." },
    { id: "approval", title: "Approval", body: "Who decides, on what, and how that is recorded." },
    { id: "operations", title: "Operations", body: "Sandboxes, credentials, budgets and limits." },
    { id: "integration", title: "Interfaces and integrations", body: "How Suncly fits into pipelines and registries." },
  ],
  legend: {
    available: "Implemented in the current version and covered by tests.",
    limited: "Implemented, with a limitation a buyer must know about.",
    planned: "On the roadmap. No date is promised, and nothing on this site treats it as current.",
  },
} as const;

export const workflowsPage = {
  title: "Supported workflows and integrations",
  headline: "One protocol in. Any model behind it.",
  intro:
    "Suncly evaluates agents through the A2A protocol. It does not integrate with model providers or agent frameworks directly: if an agent publishes an A2A 1.0 Agent Card and answers over JSON-RPC, Suncly can test it, whatever built it. This page states exactly what is inspected and tested, and where coverage differs.",
  protocol: {
    title: "Protocol coverage",
    intro: "What the Runner speaks and what the Judge checks. Verified against src/suncly/runner and src/suncly/core.",
    rows: [
      { item: "A2A 1.0 over JSON-RPC (HTTP)", status: "available", note: "SendMessage, then GetTask polling until a terminal or interrupted state. The first supportedInterfaces entry with JSONRPC and 1.0 is used." },
      { item: "Agent Card at /.well-known/agent-card.json", status: "available", note: "Fetched over https (plain http for loopback sandboxes), size-limited, hashed with RFC 8785. Fields the spec requires but the card omits are reported." },
      { item: "Direct Message replies", status: "limited", note: "Handled without error. A direct Message counts as completing a task only if the criteria say accept_direct_message." },
      { item: "Interrupted states (input or auth required)", status: "limited", note: "Recorded as the final observed state and judged against the expected state. The Runner never invents input to continue." },
      { item: "gRPC and HTTP+JSON bindings", status: "planned", note: "Not spoken. If the card lists them, the report lists them under interfaces not used." },
      { item: "Streaming, push notifications, extended cards, extensions", status: "planned", note: "Not exercised. A card that declares them gets a 'declared capability not exercised' line in the report." },
      { item: "Authentication to the agent", status: "limited", note: "One Authorization header value from an environment variable read only by the Runner. Other security schemes the card declares are kept as opaque fields and not negotiated." },
    ],
  },
  models: {
    title: "Model providers",
    intro:
      "Suncly is model-agnostic. It never calls a model provider in this version, and it does not need to know which model an agent uses. An agent built on any of these, or on none of them, is tested the same way through its A2A interface.",
    names: ["Claude", "OpenAI GPT and Codex", "Grok", "Gemini", "Llama", "Mistral", "DeepSeek", "Qwen", "Cohere", "Open-source and fine-tuned models"],
    disclaimer:
      "Names are listed to illustrate that the model does not matter to Suncly. They are trademarks of their owners; no partnership, certification or endorsement is implied or exists.",
    futureNote:
      "Later stages add a model-based drafter and a model-based judge. Those will use your own model keys and a pinned judge model; the choice of provider is yours.",
  },
  frameworks: {
    title: "Agent frameworks and coding tools",
    intro: "What matters is whether the thing you want to evaluate exposes an A2A endpoint.",
    rows: [
      { item: "Any framework that serves an A2A 1.0 Agent Card and JSON-RPC endpoint", status: "available", note: "Point suncly attest at the card URL of its sandbox deployment." },
      { item: "Agents that only expose a chat or vendor-specific API", status: "planned", note: "Not reachable until they are wrapped in an A2A server. Suncly adds no other transports in this version." },
      { item: "Coding assistants and IDE agents", status: "planned", note: "They are not A2A agents by themselves. To evaluate one, run it behind an A2A server in a sandbox and declare that sandbox." },
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
      ["honest-async", "Completes asynchronously; the client has to poll GetTask.", "every run passes after polling"],
      ["lying", "Declares text/plain output but answers with JSON.", "every run fails output_modes"],
      ["flaky", "Succeeds on odd calls, fails on even calls.", "an exact mix of pass and fail"],
      ["slow", "Answers correctly after the latency limit.", "every run fails the latency limit"],
      ["unreachable", "Its endpoint refuses connections.", "no run passes; runs are inconclusive"],
      ["direct-message", "Replies with a Message instead of a Task.", "handled; not a pass"],
      ["interrupted", "Always asks for more input.", "fail on final state; never a pass"],
      ["leaky", "Echoes the Authorization header back.", "the credential appears nowhere"],
      ["card-changer", "Changes its card during the run.", "the attestation ends invalidated"],
      ["no-examples", "One skill declares no examples.", "that skill is listed as not tested"],
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
      "Access to the repository and the suncly command for your team.",
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
  headline: "A small team in Tallinn, building the inspection step for AI agents.",
  intro:
    "Suncly is built for the platform and security teams that have to say yes or no to an agent. We write the architecture down before the code, we keep the open questions visible, and we would rather ship a report that says 'not tested' than a score that hides it.",
  principles: [
    { title: "Approve less, never more.", body: "Every fault in the system is designed to make Suncly approve less. Inconclusive is never a pass; no decision is never an approval." },
    { title: "Evidence over scores.", body: "Counts per test case, transcripts, hashes and a signature. No universal score, because a score would hide what was not tested." },
    { title: "A human stays in the loop.", body: "A person approves the test plan. A person resolves a flag. Suncly records who, and when." },
  ],
  contact: {
    title: "Contact",
    email: "team@suncly.com",
    location: "Tallinn, Estonia",
    registration: "Company registration details will be published here.",
  },
} as const;

export const docsPage = {
  title: "Documentation",
  headline: "Written down before the code. Kept current with it.",
  intro:
    "The repository carries the architecture schema, the component, data model, flow, policy and decision documents, the implementation notes, and a quickstart. The repository is private during the pilot; these pages carry the parts you need to get started, and the full documents come with access.",
  guides: [
    { href: "/docs/getting-started", title: "Getting started", body: "Install, run the bundled demo, evaluate your own sandbox agent, read and verify the report. Five minutes." },
    { href: "/docs/cli", title: "Command reference", body: "suncly attest, demo, verify, keys, db and doctor, every option, every exit code, and the contract file format." },
    { href: "/docs/evidence", title: "Evidence and reports", body: "What a report folder contains, what the signature covers, how to verify it, and how to load it into the workspace." },
  ],
  repositoryDocs: [
    { file: "SCHEMA.md", title: "Architecture schema", body: "System layout, components, data model, main flow, default approval policy, interfaces, stack, the non-negotiable rules, build order, and what is out of scope. The source of truth." },
    { file: "docs/QUICKSTART.md", title: "Quickstart", body: "Install, run the demo, attest your own sandbox agent, read and verify a report, use Postgres, troubleshoot." },
    { file: "docs/ARCHITECTURE.md", title: "Architecture", body: "Each component's responsibility, inputs, outputs, what it must never do, and how it fails safely. The A2A protocol facts Suncly depends on." },
    { file: "docs/CODE_ARCHITECTURE.md", title: "Code architecture", body: "How the code maps to the components: layers, the Runner boundary, where to add what, and the tests that enforce the boundaries." },
    { file: "docs/DATA_MODEL.md", title: "Data model", body: "The seven entities: agent, card_version, contract, test_case, attestation, run, decision. Fields, keys, enums, invariants." },
    { file: "docs/FLOW.md", title: "Attestation flow", body: "One attestation from trigger to result, the status lifecycle, and every failure path." },
    { file: "docs/API.md", title: "Interfaces", body: "The CLI with its options and exit codes, the contract file format, and the proposed HTTP endpoints." },
    { file: "docs/POLICY.md", title: "Approval policy", body: "Risk levels, decision outcomes, when a human is required, and how inconclusive results count." },
    { file: "docs/DECISIONS.md", title: "Decision records", body: "The seven non-negotiable rules, each with its decision, reason and consequences." },
    { file: "docs/ROADMAP.md", title: "Roadmap", body: "The six build stages, what the current version implements, and what it does not." },
    { file: "docs/IMPLEMENTATION_NOTES.md", title: "Implementation notes", body: "Every proposal the code implements, every choice that still needs a decision, and the facts that were verified." },
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
    "Draft. This page describes how the software and this website handle data, verified against the implementation. The legal identity, governing law and retention commitments are to be supplied by Suncly's owners before publication.",
  pending: "to be supplied by the owners",
} as const;

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
      a: "No price is published. Suncly is in pilot and a payment layer is planned; access is arranged with the team.",
    },
  ],
} as const;

export const footer = {
  groups: [
    {
      title: "Product",
      links: [
        { label: "Product", href: "/product" },
        { label: "Workflows", href: "/workflows" },
        { label: "Sample evaluation", href: "/demo" },
        { label: "Security", href: "/security" },
        { label: "Workspace", href: "/app" },
      ],
    },
    {
      title: "Developers",
      links: [
        { label: "Docs", href: "/docs" },
        { label: "Getting started", href: "/docs/getting-started" },
        { label: "Command reference", href: "/docs/cli" },
        { label: "Evidence and reports", href: "/docs/evidence" },
      ],
    },
    {
      title: "Company",
      links: [
        { label: "Company", href: "/company" },
        { label: "Access", href: "/access" },
        { label: "Contact", href: "mailto:team@suncly.com" },
      ],
    },
    {
      title: "Legal",
      links: [
        { label: "Privacy", href: "/privacy" },
        { label: "Terms", href: "/terms" },
      ],
    },
  ],
} as const;
