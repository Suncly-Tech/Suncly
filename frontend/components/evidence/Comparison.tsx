import { Badge, StatusBadge, DecisionBadge } from "@/components/ui/Badge";
import { Notice } from "@/components/ui/Notice";
import { Table } from "@/components/ui/Table";
import { compareEvaluations } from "@/lib/evidence/compare";
import { formatDateTime, shortId } from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";

const CHANGE_LABEL = {
  regressed: { label: "Regressed", tone: "fail" },
  improved: { label: "Improved", tone: "pass" },
  unchanged: { label: "Unchanged", tone: "neutral" },
  mixed: { label: "Mixed", tone: "inconclusive" },
  no_runs: { label: "No runs recorded", tone: "inconclusive" },
  added: { label: "Added", tone: "info" },
  removed: { label: "Removed", tone: "neutral" },
} as const;

function counts(r: { pass_count: number; fail_count: number; inconclusive_count: number } | null) {
  if (!r) return <span className="text-ink-mute">–</span>;
  return (
    <span className="font-mono text-[13px]">
      <span className="text-pass">{r.pass_count}</span> / <span className="text-fail">{r.fail_count}</span> /{" "}
      <span className="text-partial">{r.inconclusive_count}</span>
    </span>
  );
}

/** Two attestations of one agent, test case by test case. */
export function ComparisonView({ older, newer }: { older: ResultDocument; newer: ResultDocument }) {
  const c = compareEvaluations(older, newer);
  return (
    <div className="flex flex-col gap-6">
      {!c.sameAgent ? (
        <Notice tone="warn" title="Different agents">
          These two attestations are for different agents (different card URLs). The comparison is shown, but it does not describe a change in one agent.
        </Notice>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        {[
          { label: "Earlier", result: older },
          { label: "Later", result: newer },
        ].map(({ label, result }) => (
          <div key={label} className="surface p-4">
            <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">{label}</p>
            <p className="mt-1 font-mono text-[13px] text-ink">attestation {shortId(result.attestation.id)}</p>
            <p className="text-[13px] text-ink-soft">{formatDateTime(result.attestation.started_at)}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusBadge status={result.attestation.status} />
              <DecisionBadge outcome={result.decisions[0]?.outcome ?? null} by={result.decisions[0] ? "policy" : undefined} />
            </div>
          </div>
        ))}
      </div>

      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Fact label="Agent Card" value={c.cardHashChanged ? "Changed" : "Unchanged"} tone={c.cardHashChanged ? "fail" : "pass"} note={c.cardHashChanged ? "Different card_hash. The later run needed a new approved contract." : "Same card_hash. An unchanged card is not proof of an unchanged agent; the results below are."} />
        <Fact label="Test conditions" value={c.contractChanged ? "Different contract" : "Same contract"} tone={c.contractChanged ? "inconclusive" : "pass"} note={c.contractChanged ? "The two runs used different contracts; compare test cases by content, not by id." : `Contract version ${newer.contract.version}, approved by ${newer.contract.approved_by ?? "–"}.`} />
        <Fact label="Evaluation status" value={c.statusChanged ? `${older.attestation.status} → ${newer.attestation.status}` : newer.attestation.status} tone={c.statusChanged ? "inconclusive" : "neutral"} />
        <Fact label="Test cases" value={`${c.summary.regressed} regressed · ${c.summary.improved} improved`} tone={c.summary.regressed ? "fail" : c.summary.improved ? "pass" : "neutral"} note={`${c.summary.unchanged} unchanged, ${c.summary.mixed} mixed, ${c.summary.no_runs} without runs on one side, ${c.summary.added} added, ${c.summary.removed} removed`} />
      </ul>

      <Table caption="Per test case comparison of pass, fail and inconclusive counts">
        <thead>
          <tr>
            <th scope="col">Skill</th>
            <th scope="col">Test input</th>
            <th scope="col">Earlier (pass / fail / inconclusive)</th>
            <th scope="col">Later (pass / fail / inconclusive)</th>
            <th scope="col">Change</th>
          </tr>
        </thead>
        <tbody>
          {c.testCases.map((row) => {
            const change = CHANGE_LABEL[row.change];
            return (
              <tr key={row.key}>
                <td>
                  <span className="font-semibold text-ink">{row.skillName}</span>
                  <span className="block font-mono text-[12px] text-ink-soft">{row.skillId ?? "probe"}</span>
                </td>
                <td className="max-w-[300px] text-ink">
                  <span className="line-clamp-2">“{row.input}”</span>
                </td>
                <td>{counts(row.before)}</td>
                <td>{counts(row.after)}</td>
                <td>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge tone={change.tone} dot>
                      {change.label}
                    </Badge>
                    {row.criteriaChanged ? (
                      <Badge tone="inconclusive" title="Same skill and input, different criteria">
                        Criteria changed
                      </Badge>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </Table>

      {c.notTestedAdded.length || c.notTestedRemoved.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="surface p-4">
            <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Newly not tested</p>
            {c.notTestedAdded.length ? (
              <ul className="mt-2 flex flex-col gap-1.5 text-[13px] text-ink-soft">
                {c.notTestedAdded.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-[13px] text-ink-soft">Nothing.</p>
            )}
          </div>
          <div className="surface p-4">
            <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">No longer listed as not tested</p>
            {c.notTestedRemoved.length ? (
              <ul className="mt-2 flex flex-col gap-1.5 text-[13px] text-ink-soft">
                {c.notTestedRemoved.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-[13px] text-ink-soft">Nothing.</p>
            )}
          </div>
        </div>
      ) : null}

      <p className="text-[13px] text-ink-soft">
        Computed in this workspace from the two signed bundles. Suncly's evidence store has no comparison operation; what counts as a “drop” for the Policy engine is an open question (OQ-PO2).
      </p>
    </div>
  );
}

function Fact({ label, value, tone, note }: { label: string; value: string; tone: "pass" | "fail" | "inconclusive" | "neutral"; note?: string }) {
  return (
    <li className="surface flex flex-col gap-1.5 p-4">
      <span className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">{label}</span>
      <Badge tone={tone} dot className="self-start">
        {value}
      </Badge>
      {note ? <span className="text-[13px] leading-snug text-ink-soft">{note}</span> : null}
    </li>
  );
}
