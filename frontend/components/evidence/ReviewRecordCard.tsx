import { Badge } from "@/components/ui/Badge";
import { formatDateTime } from "@/lib/evidence/derive";
import type { ReviewDecision } from "@/lib/workspace/store";

export const REVIEW_LABEL: Record<ReviewDecision, string> = {
  approve: "Approve",
  block: "Block",
  needs_more_evidence: "Needs more evidence",
};

/** A reviewer's decision note. Always marked as a human decision outside the signed evidence. */
export function ReviewRecordCard({
  decision,
  reviewer,
  rationale,
  recordedAt,
  attestationId,
  sample = false,
}: {
  decision: ReviewDecision;
  reviewer: string;
  rationale: string;
  recordedAt?: string;
  attestationId: string;
  sample?: boolean;
}) {
  const tone = decision === "approve" ? "pass" : decision === "block" ? "fail" : "inconclusive";
  return (
    <article className="surface flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={tone} dot>
          {REVIEW_LABEL[decision]} · reviewer
        </Badge>
        <Badge tone="neutral">Human decision, outside the signed evidence</Badge>
        {sample ? <Badge tone="sun">Sample</Badge> : null}
      </div>
      <p className="text-body text-ink">{rationale}</p>
      <p className="font-mono text-[12px] text-ink-soft">
        {reviewer}
        {recordedAt ? ` · ${formatDateTime(recordedAt)}` : ""} · attestation {attestationId}
      </p>
    </article>
  );
}
