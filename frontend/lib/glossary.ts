/**
 * Definitions written to be quoted: one term, one plain sentence first, then the Suncly
 * specifics. Sources: docs/ARCHITECTURE.md (A2A facts), docs/DATA_MODEL.md (entities),
 * docs/POLICY.md, docs/DECISIONS.md, src/suncly.
 */

export interface GlossaryTerm {
  term: string;
  anchor: string;
  definition: string;
  detail: string;
  related?: string[];
}

export const glossary: GlossaryTerm[] = [
  {
    term: "A2A protocol (Agent2Agent)",
    anchor: "a2a-protocol",
    definition:
      "The A2A protocol is an open protocol in which an AI agent publishes an Agent Card describing itself and its skills, and answers requests as Tasks or Messages over bindings such as JSON-RPC 2.0.",
    detail:
      "Suncly evaluates agents through A2A version 1.0 over JSON-RPC: it sends each test input as a Message and follows the Task to a terminal or interrupted state. The protocol defines how skills are described; it has no mechanism for checking that the agent performs them, which is the gap Suncly fills.",
    related: ["agent-card", "skill"],
  },
  {
    term: "Agent Card",
    anchor: "agent-card",
    definition:
      "An Agent Card is the JSON document an A2A agent publishes, usually at /.well-known/agent-card.json, naming the agent, its version, its interfaces, its capabilities and the skills it offers.",
    detail:
      "Suncly keeps the card byte for byte, hashes it, and treats the skills list as the claims under test. A signed card proves who published it and that it was not altered; it says nothing about behaviour.",
    related: ["card-hash", "skill"],
  },
  {
    term: "Skill",
    anchor: "skill",
    definition: "A skill is one capability an Agent Card declares, with an id, a name, a description, tags and optionally example inputs.",
    detail:
      "Suncly drafts one test case per declared example of each skill. A skill with no examples gets no test case and is reported under what was not tested, because Suncly never invents input.",
    related: ["test-case", "not-tested"],
  },
  {
    term: "AI agent evaluation",
    anchor: "ai-agent-evaluation",
    definition:
      "AI agent evaluation is the practice of testing what an AI agent actually does against what it claims, before the agent is approved for use.",
    detail:
      "In Suncly an evaluation is an attestation: a contract of test cases, approved by a person, run repeatedly against a sandbox endpoint, judged deterministically, signed, and reported with its coverage gaps. It is behavioural evaluation, not protocol conformance testing and not runtime monitoring.",
    related: ["attestation", "behavioural-evaluation"],
  },
  {
    term: "Behavioural evaluation",
    anchor: "behavioural-evaluation",
    definition:
      "Behavioural evaluation sends real inputs to an agent and judges the responses, as opposed to reading its documentation or checking its protocol conformance.",
    detail:
      "Suncly's judge checks that each response is a well-formed A2A Task or Message, reached the expected final state, answered within the latency limit, carries content, uses the declared output modes, and satisfies required fields and schema. Whether an answer is correct in meaning needs the model-based judge of a later stage.",
  },
  {
    term: "Attestation",
    anchor: "attestation",
    definition:
      "An attestation is one execution of an approved contract against an agent: every test case run a configured number of times, each run judged, the results signed.",
    detail:
      "Its status is queued, running, completed, failed, cancelled or invalidated. Only a completed attestation carries a decision. Failed (budget or card re-fetch) and invalidated (card changed) attestations are signed with no decision, and no decision is never an approval.",
    related: ["contract", "run", "decision"],
  },
  {
    term: "Contract",
    anchor: "contract",
    definition: "A contract is a versioned, human-approved set of test cases for one version of an Agent Card.",
    detail:
      "Nothing runs until a person approves the contract and their identifier is recorded as approved_by. Approved contracts are immutable; an edit creates a new version, and a changed card needs a new contract.",
    related: ["test-case", "card-hash"],
  },
  {
    term: "Test case",
    anchor: "test-case",
    definition: "A test case is one input to send to the agent and the criteria its response must satisfy.",
    detail:
      "Criteria in the current version: expected final task state, latency limit, response present, declared output modes, required fields as JSON pointers, an optional JSON Schema, and model checks that stay inconclusive until the model judge exists.",
    related: ["criteria", "run"],
  },
  {
    term: "Run",
    anchor: "run",
    definition: "A run is one execution of one test case, identified by a deterministic key of attestation, test case and attempt number.",
    detail:
      "Retries reuse the key, so a crashed run never counts twice. Each run keeps its redacted transcript, verdict, latency, cost and timestamps.",
    related: ["verdict", "transcript"],
  },
  {
    term: "Verdict: pass, fail, inconclusive",
    anchor: "verdict",
    definition:
      "A verdict is the judge's outcome for one run: pass when every check passed, fail when any check failed, inconclusive when a check could not be decided.",
    detail:
      "Inconclusive is never counted as a pass. Counts are reported per test case and never combined into a score.",
    related: ["inconclusive", "judge"],
  },
  {
    term: "Inconclusive",
    anchor: "inconclusive",
    definition:
      "Inconclusive is the verdict for a run whose outcome could not be decided: the agent was unreachable, the transcript could not be read, or a criterion needs a judge that does not exist yet.",
    detail: "Suncly reports inconclusive runs separately and lists them under what was not tested. They never count as passes.",
  },
  {
    term: "Judge (Layer 1 and Layer 2)",
    anchor: "judge",
    definition:
      "The judge assigns a verdict to each run. Layer 1 is deterministic; Layer 2 is a model pinned by version with a fixed rubric, used only for criteria Layer 1 cannot decide.",
    detail: "Only Layer 1 exists in the current version. Every report says that semantic correctness was not tested.",
  },
  {
    term: "Decision: approve, flag, block",
    anchor: "decision",
    definition:
      "A decision is the Policy engine's recorded outcome for a completed attestation: approve, flag for human review, or block.",
    detail:
      "Without a configured policy the only outcome is flag, so a human reviews every result. Automatic decisions are signed; a later human decision is a second record and is never written over the first.",
    related: ["policy-engine", "risk-level"],
  },
  {
    term: "Policy engine",
    anchor: "policy-engine",
    definition: "The Policy engine aggregates results per test case, applies the customer's policy for the agent's risk level, records the decision and signs the attestation.",
    detail: "Thresholds are a customer configuration that does not exist yet; Suncly ships no numbers of its own.",
  },
  {
    term: "Risk level",
    anchor: "risk-level",
    definition: "The risk level (low, medium, high) records how much a human must be involved in approving an agent.",
    detail:
      "By design, low-risk agents can be approved automatically on pass, medium-risk agents need a human on any drop, and high-risk agents need human sign-off every time. In the current version the level is recorded but every decision is flag.",
  },
  {
    term: "Probe",
    anchor: "probe",
    definition:
      "A probe is a test case that exercises behaviour the card does not declare: undeclared capabilities, injected instructions, or failure handling.",
    detail: "Probes are a planned stage. Every report lists them under what was not tested until they exist.",
  },
  {
    term: "Sandbox declaration",
    anchor: "sandbox",
    definition: "The sandbox declaration (--sandbox) is the caller's statement that the endpoint under test is a sandbox or dry-run endpoint.",
    detail:
      "Nothing runs without it, so tests cannot book, pay or delete anything real. Suncly cannot verify a sandbox; the report records the declaration as a declaration, and the production endpoint is listed as not tested.",
  },
  {
    term: "card_hash",
    anchor: "card-hash",
    definition: "card_hash is the SHA-256 of the Agent Card's RFC 8785 canonical form without the signatures field.",
    detail:
      "It pins an evaluation to an exact version of the claims. An unchanged hash reuses the approved contract, which makes two evaluations comparable. An unchanged card is not proof of an unchanged agent.",
  },
  {
    term: "Signed evidence",
    anchor: "signed-evidence",
    definition:
      "Signed evidence is the attestation's Ed25519 signature over the card hash, the contract version, the per-test-case counts, the hash of every transcript and the decision.",
    detail:
      "suncly verify re-checks a report folder offline with the public key. A valid signature proves the evidence was not altered after signing and which deployment produced it; it does not prove the agent is correct or will behave the same tomorrow.",
    related: ["transcript", "attestation"],
  },
  {
    term: "Transcript",
    anchor: "transcript",
    definition: "A transcript is the complete record of one run: every request and response, the final task state, latency, outcome and the checks applied.",
    detail:
      "Transcripts are redacted inside the Runner before they are stored: the credential, sensitive headers and known token patterns are removed. Each transcript's hash is in the signed payload.",
  },
  {
    term: "What was NOT tested",
    anchor: "not-tested",
    definition: "What was NOT tested is the mandatory report section listing every gap in the evidence.",
    detail:
      "Categories: skills without a test case, runs never executed, inconclusive runs, declared capabilities not exercised, interfaces not used, probes and semantic checks that do not exist yet, the production endpoint, and card fields the specification requires but the card omits.",
  },
  {
    term: "Budget",
    anchor: "budget",
    definition: "The budget is the maximum number of attempts an attestation may make against the agent, retries included.",
    detail: "When it is reached no new run starts, the attestation ends failed, the runs never executed are listed, and no decision is made.",
  },
  {
    term: "Runner",
    anchor: "runner",
    definition: "The Runner is the isolated process that calls the agent. It is the only component that holds the agent credential.",
    detail:
      "It refuses any host other than the target, reads the credential from one environment variable, redacts transcripts before returning them, and runs only against a declared sandbox.",
  },
];
