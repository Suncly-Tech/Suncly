import { Badge } from "@/components/ui/Badge";
import { KeyValue, Meter } from "@/components/ui/Stat";
import {
  budgetUsage,
  durationSeconds,
  formatDateTime,
  notExecutedByReason,
  targetInterface,
  totals,
} from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";

const RECHECK_LABEL: Record<ResultDocument["card_recheck"]["outcome"], string> = {
  unchanged: "Unchanged: the card served the same hash at the end of the run.",
  changed: "Changed: the card served a different hash at the end. The attestation is invalidated.",
  unavailable: "Unavailable: the card could not be re-fetched. The attestation failed.",
  not_performed: "Not performed: the attestation ended before the re-check.",
};

/** Execution environment, configuration, budget and timestamps, from the record itself. */
export function ExecutionPanel({ result }: { result: ResultDocument }) {
  const iface = targetInterface(result);
  const budget = budgetUsage(result);
  const sums = totals(result);
  const reasons = notExecutedByReason(result);
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="flex flex-col gap-5">
        <Meter
          value={budget.cost}
          max={budget.limit}
          label="Budget used (attempts, retries included)"
          tone={budget.cost >= budget.limit ? "fail" : "ink"}
        />
        <div className="grid grid-cols-3 gap-3">
          <div className="surface-sunken p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Planned</p>
            <p className="font-mono text-[22px] text-ink">{sums.planned ?? "–"}</p>
          </div>
          <div className="surface-sunken p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Recorded</p>
            <p className="font-mono text-[22px] text-ink">{sums.recorded}</p>
          </div>
          <div className="surface-sunken p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Never executed</p>
            <p className={`font-mono text-[22px] ${sums.notExecuted ? "text-fail" : "text-ink"}`}>{sums.notExecuted}</p>
          </div>
        </div>
        {sums.notExecuted > 0 ? (
          <div className="flex flex-wrap gap-2">
            {Object.entries(reasons).map(([reason, count]) => (
              <Badge key={reason} tone="fail">
                {count} because of {reason.replace("_", " ")}
              </Badge>
            ))}
          </div>
        ) : null}
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Card re-check at the end</p>
          <p className="mt-1 text-small text-ink">{RECHECK_LABEL[result.card_recheck.outcome]}</p>
          {result.card_recheck.detail ? <p className="mt-1 font-mono text-[12px] text-ink-soft">{result.card_recheck.detail}</p> : null}
        </div>
      </div>

      <KeyValue
        items={[
          ["Interface used", <span key="i" className="font-mono text-[13px]">{iface ? `${iface.protocol_binding} ${iface.protocol_version} at ${iface.url}` : "–"}</span>],
          ["Sandbox", result.sandbox_declared ? "Declared by the caller with --sandbox (DR-006). Suncly cannot verify a sandbox." : "Not declared"],
          ["Card URL", <span key="u" className="font-mono text-[13px]">{result.card_url ?? "–"}</span>],
          ["Card hash", <span key="h" className="font-mono text-[12px]">{result.card_version.card_hash}</span>],
          ["Hash scheme", "SHA-256 of the RFC 8785 form of the card without the signatures field"],
          ["Card fetched", formatDateTime(result.card_version.fetched_at)],
          ["Contract", `version ${result.contract.version} · ${result.contract.status} · approved by ${result.contract.approved_by ?? "–"} at ${formatDateTime(result.contract.approved_at)}`],
          ["Test plan source", result.drafter_name ?? "–"],
          ["Started", formatDateTime(result.attestation.started_at)],
          ["Finished", formatDateTime(result.attestation.finished_at)],
          ["Duration", durationSeconds(result.attestation.started_at, result.attestation.finished_at)],
          ["Report generated", formatDateTime(result.generated_at)],
          ["Format", <span key="f" className="font-mono text-[13px]">{result.format}</span>],
        ]}
      />
    </div>
  );
}

/** The proposals in effect for this run, as the report lists them. */
export function ProposalsList({ result }: { result: ResultDocument }) {
  return (
    <details className="group">
      <summary className="cursor-pointer text-small font-semibold text-ink">
        Proposals in effect for this run ({result.proposals.length}) — open questions the code implements a proposal for; none is decided by this report
      </summary>
      <ul className="mt-3 flex flex-col gap-1.5 pl-4 text-[13px] text-ink-soft">
        {result.proposals.map((p) => (
          <li key={p} className="list-disc">
            {p}
          </li>
        ))}
      </ul>
    </details>
  );
}
