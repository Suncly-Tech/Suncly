import type { ReactNode } from "react";
import { DecisionBadge, RiskBadge, SampleBadge, StatusBadge } from "@/components/ui/Badge";
import { decisionState, formatDateTime, shortId, STATUS_EXPLANATION } from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";

/**
 * The top of an evaluation: identity, then evaluation status and approval status side by
 * side, because they answer different questions.
 */
export function EvaluationHeader({
  result,
  sample = false,
  actions,
  heading = "h1",
}: {
  result: ResultDocument;
  sample?: boolean;
  actions?: ReactNode;
  heading?: "h1" | "h2";
}) {
  const Tag = heading;
  const decision = decisionState(result);
  const policy = decision.kind === "none" ? null : decision.decision;
  return (
    <header className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {sample ? <SampleBadge /> : null}
            <span className="font-mono text-[13px] text-ink-soft">
              attestation {shortId(result.attestation.id)} · trigger {result.attestation.trigger}
            </span>
          </div>
          <Tag className="mt-2 text-heading-lg text-ink md:text-[32px]">{result.agent.name}</Tag>
          <p className="mt-1 text-small text-ink-soft">
            Card version {result.parsed_card.card.version || "–"} · owner {result.agent.owner} · started{" "}
            {formatDateTime(result.attestation.started_at)}
          </p>
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="surface p-4">
          <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Evaluation status</p>
          <div className="mt-2 flex items-center gap-2">
            <StatusBadge status={result.attestation.status} />
          </div>
          <p className="mt-2 text-[13px] leading-snug text-ink-soft">{STATUS_EXPLANATION[result.attestation.status]}</p>
        </div>
        <div className="surface p-4">
          <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Approval status</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <DecisionBadge outcome={policy?.outcome ?? null} by={policy ? "policy" : undefined} />
            <RiskBadge level={result.agent.risk_level} />
          </div>
          <p className="mt-2 text-[13px] leading-snug text-ink-soft">
            {decision.kind === "none"
              ? decision.reason
              : decision.kind === "automatic_flag"
                ? "Automatic decision by the Policy engine. No policy is configured, so a human must review this result. Approve and block are never produced automatically in this version."
                : `Automatic decision recorded by the Policy engine under policy_version ${decision.decision.policy_version}.`}
          </p>
        </div>
      </div>
    </header>
  );
}
