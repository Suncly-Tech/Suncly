import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { Cuts } from "@/components/Cuts";
import { DecisionBadge, SampleBadge, StatusBadge } from "@/components/ui/Badge";
import { TestCaseTable } from "@/components/evidence/TestCaseTable";
import { decisionState, shortId } from "@/lib/evidence/derive";
import { sampleByLabel } from "@/lib/sample";
import { hero } from "@/lib/content";

/**
 * The hero window: a real result document from the sample set, rendered with the same
 * components the workspace uses. Server component, so the JSON never ships to the client.
 */
export function EvaluationPreview() {
  const bundle = sampleByLabel("2-regression");
  if (!bundle) return null;
  const { result } = bundle;
  const decision = decisionState(result);
  const policy = decision.kind === "none" ? null : decision.decision;
  const notTested = result.not_tested.slice(0, 3);
  return (
    <figure className="overflow-hidden rounded-card bg-paper text-ink shadow-raised ring-1 ring-ink/5">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3.5 md:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <Cuts className="shrink-0 text-sun" height={12} stroke={3} />
          <span className="truncate font-mono text-[13px] text-ink-soft">
            attestation {shortId(result.attestation.id)} · {result.agent.name} · card v{result.parsed_card.card.version}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <SampleBadge />
          <span className="inline-flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-[12px] font-semibold text-paper">
            <ShieldCheck size={14} className="text-sun" aria-hidden="true" />
            Signed · {result.attestation.signing_key_id}
          </span>
        </div>
      </div>

      <div className="grid gap-4 px-5 pt-5 md:grid-cols-2 md:px-6">
        <div className="surface-sunken p-4">
          <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Evaluation status</p>
          <div className="mt-2">
            <StatusBadge status={result.attestation.status} />
          </div>
          <p className="mt-2 text-[13px] text-ink-soft">
            {result.runs.length} of {result.planned_runs} planned runs recorded · card re-check {result.card_recheck.outcome}
          </p>
        </div>
        <div className="surface-sunken p-4">
          <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Approval status</p>
          <div className="mt-2">
            <DecisionBadge outcome={policy?.outcome ?? null} by={policy ? "policy" : undefined} />
          </div>
          <p className="mt-2 text-[13px] text-ink-soft">No policy is configured, so a human must review this result.</p>
        </div>
      </div>

      <div className="px-5 pt-5 md:px-6">
        <TestCaseTable result={result} compact />
      </div>

      <div className="flex flex-col gap-3 px-5 py-5 md:flex-row md:items-start md:justify-between md:px-6">
        <div className="min-w-0">
          <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">What was not tested</p>
          <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-[13px] text-ink-soft">
            {notTested.map((item) => (
              <li key={item.category} className="cuts-bullet text-ink-soft">
                <span className="text-ink">{item.category}</span>
              </li>
            ))}
            {result.not_tested.length > notTested.length ? <li className="text-ink-soft">+{result.not_tested.length - notTested.length} more</li> : null}
          </ul>
        </div>
        <Link href="/demo" className="inline-flex shrink-0 items-center gap-1.5 text-[14px] font-semibold text-ink underline-offset-4 hover:underline">
          Open the full sample
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </div>
      <figcaption className="border-t border-line bg-cream px-5 py-3 text-[13px] text-ink-soft md:px-6">{hero.previewCaption}</figcaption>
    </figure>
  );
}
