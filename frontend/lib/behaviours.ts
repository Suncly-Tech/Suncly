/**
 * The eleven mock agents, from BEHAVIOURS in src/suncly/mock_agents/behaviours.py
 * (lines 377 to 389 on 2026-10-05): the name, the class description, and what the code
 * says Suncly reports for each. CODE. Keep in the file's order.
 */
export interface Behaviour {
  name: string;
  description: string;
  reports: string;
  /** Which of the three odd shadows this one is in the Lab picture, for the strip's caption. */
  shadow?: "wrong" | "two" | "none";
}

export const behaviours: readonly Behaviour[] = [
  { name: "honest", description: "Does what its card says.", reports: "every run passes" },
  { name: "honest-async", description: "Completes tasks asynchronously; the client has to poll GetTask.", reports: "every run passes after polling GetTask" },
  { name: "unreachable", description: "Serves a card whose endpoint refuses connections.", reports: "no run passes; runs are inconclusive", shadow: "none" },
  { name: "lying", description: "Declares skills and output modes it does not honour.", reports: "every run fails the output_modes check", shadow: "wrong" },
  { name: "flaky", description: "Succeeds on odd calls and fails on even calls.", reports: "odd calls pass, even calls fail", shadow: "two" },
  { name: "slow", description: "Answers correctly, but slowly.", reports: "every run fails the latency limit" },
  { name: "direct-message", description: "Answers with a direct Message instead of a Task.", reports: "handled without error; not a pass" },
  { name: "interrupted", description: "Always asks for more input.", reports: "recorded as fail; never a pass" },
  { name: "leaky", description: "Echoes the Authorization header back in its answer.", reports: "the credential appears in no transcript, report or log" },
  { name: "card-changer", description: "Changes its card while an attestation runs.", reports: "the attestation ends invalidated" },
  { name: "no-examples", description: "One of its skills declares no examples.", reports: "the skill without examples is listed as not tested" },
] as const;
