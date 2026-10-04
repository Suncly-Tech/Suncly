"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field, Input, Select, Textarea, describedBy } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { DecisionBadge } from "@/components/ui/Badge";
import { ReviewRecordCard, REVIEW_LABEL } from "@/components/evidence/ReviewRecordCard";
import { decisionState, formatDateTime, totals } from "@/lib/evidence/derive";
import type { EvidenceBundle } from "@/lib/evidence/types";
import { downloadText } from "@/lib/download";
import { addReview, setReviewer, type ReviewDecision, type ReviewRecord } from "@/lib/workspace/store";

/**
 * Record and route a reviewer's decision. The record is local: Suncly's evidence store has
 * no interface for a human decision yet (OQ-P2, stage 5), so the note is exported and
 * attached to the signed report by the reviewer.
 */
export function ReviewPanel({
  bundle,
  reviews,
  defaultReviewer,
  sample = false,
}: {
  bundle: EvidenceBundle;
  reviews: ReviewRecord[];
  defaultReviewer: string;
  sample?: boolean;
}) {
  const { result } = bundle;
  const decision = decisionState(result);
  const [outcome, setOutcome] = useState<ReviewDecision>("needs_more_evidence");
  const [reviewer, setReviewerName] = useState(defaultReviewer);
  const [rationale, setRationale] = useState("");
  const [errors, setErrors] = useState<{ reviewer?: string; rationale?: string }>({});
  const [saved, setSaved] = useState<ReviewRecord | null>(null);

  const canDecide = decision.kind !== "none";

  function submit() {
    const next: typeof errors = {};
    if (!reviewer.trim()) next.reviewer = "Enter the identifier your review process recognises.";
    if (rationale.trim().length < 20) next.rationale = "Write the rationale a colleague could act on (at least 20 characters).";
    setErrors(next);
    if (Object.keys(next).length) return;
    const record = addReview({
      attestationId: result.attestation.id,
      decision: outcome,
      reviewer: reviewer.trim(),
      rationale: rationale.trim(),
      signature: result.attestation.signature,
      signingKeyId: result.attestation.signing_key_id,
      cardHash: result.card_version.card_hash,
    });
    setReviewer(reviewer.trim());
    setSaved(record);
    setRationale("");
  }

  function exportRecord(record: ReviewRecord, format: "json" | "md") {
    const sums = totals(result);
    const base = `suncly-review-${result.attestation.id.slice(0, 8)}`;
    if (format === "json") {
      downloadText(
        `${base}.json`,
        JSON.stringify(
          {
            kind: "suncly-review-note/1",
            note: "A human decision recorded outside the signed attestation. Match it to the attestation by id, signature and card_hash.",
            review: record,
            attestation: {
              id: result.attestation.id,
              status: result.attestation.status,
              agent: result.agent,
              card_hash: result.card_version.card_hash,
              contract_version: result.contract.version,
              policy_decision: result.decisions[0] ?? null,
              totals: sums,
              not_tested: result.not_tested,
            },
          },
          null,
          2,
        ),
      );
      return;
    }
    const lines = [
      `# Review of attestation ${result.attestation.id}`,
      "",
      `**Agent:** ${result.agent.name} (owner ${result.agent.owner}, risk ${result.agent.risk_level})`,
      `**Card hash:** ${result.card_version.card_hash}`,
      `**Evaluation status:** ${result.attestation.status}`,
      `**Policy decision:** ${result.decisions[0] ? `${result.decisions[0].outcome} by ${result.decisions[0].decided_by} (${result.decisions[0].policy_version})` : "none"}`,
      `**Counts:** ${sums.pass} pass, ${sums.fail} fail, ${sums.inconclusive} inconclusive, ${sums.notExecuted} never executed`,
      `**Signature:** ${result.attestation.signature ?? "none"} (key ${result.attestation.signing_key_id ?? "none"})`,
      "",
      `## Reviewer decision: ${REVIEW_LABEL[record.decision]}`,
      "",
      `Recorded by ${record.reviewer} at ${record.recordedAt}.`,
      "",
      record.rationale,
      "",
      "## What was NOT tested",
      "",
      ...result.not_tested.map((i) => `- **${i.category}:** ${i.detail}`),
      "",
      "_This note is a human decision kept outside the signed attestation. Suncly's evidence store cannot record human decisions yet (stage 5)._",
      "",
    ];
    downloadText(`${base}.md`, lines.join("\n"), "text/markdown");
  }

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader
          title="Automated recommendation"
          description="What the Policy engine recorded, and why. It is signed with the attestation."
        />
        <div className="flex flex-wrap items-center gap-3">
          <DecisionBadge outcome={decision.kind === "none" ? null : decision.decision.outcome} by={decision.kind === "none" ? undefined : "policy"} />
          <p className="text-small text-ink-soft">
            {decision.kind === "none"
              ? decision.reason + " A failed, invalidated or cancelled attestation gets no decision, and no decision is never an approval."
              : `Recorded by '${decision.decision.decided_by}' at ${formatDateTime(decision.decision.decided_at)} under policy_version '${decision.decision.policy_version}'. No policy is configured, so a human must review this result.`}
          </p>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Reviewer decision"
          description="Your decision and rationale, under your name. Kept in this browser and exported as a file to attach to the signed report or your ticket."
        />
        <Notice tone="info" className="mb-5">
          Suncly's evidence store has no interface yet for recording a human decision (planned, stage 5). This note is not part of the signed attestation and does not change it; it carries the attestation id, signature and card hash so it can be matched to the evidence later.
        </Notice>
        {!canDecide ? (
          <Notice tone="warn" className="mb-5" title="This attestation has no policy decision">
            You can still record a note, for example to request a re-run with a higher budget. It will not be an approval of anything.
          </Notice>
        ) : null}
        {sample ? (
          <Notice tone="sample" className="mb-5">
            Sample data. Notes you record here are stored locally and marked as belonging to a sample attestation.
          </Notice>
        ) : null}
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          noValidate
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="review-outcome" label="Decision" required>
              <Select id="review-outcome" value={outcome} onChange={(e) => setOutcome(e.target.value as ReviewDecision)}>
                <option value="approve">Approve</option>
                <option value="block">Block</option>
                <option value="needs_more_evidence">Needs more evidence</option>
              </Select>
            </Field>
            <Field id="review-reviewer" label="Reviewer identifier" required error={errors.reviewer} help="For example your work email. Reused as the default next time.">
              <Input id="review-reviewer" value={reviewer} onChange={(e) => setReviewerName(e.target.value)} placeholder="reviewer@company.com" autoComplete="email" aria-invalid={errors.reviewer ? true : undefined} aria-describedby={describedBy("review-reviewer", true, Boolean(errors.reviewer))} />
            </Field>
          </div>
          <Field id="review-rationale" label="Rationale" required error={errors.rationale} help="Say what in the evidence drove the decision and what would change it. Name the gaps you accept.">
            <Textarea id="review-rationale" value={rationale} onChange={(e) => setRationale(e.target.value)} rows={5} aria-invalid={errors.rationale ? true : undefined} aria-describedby={describedBy("review-rationale", true, Boolean(errors.rationale))} />
          </Field>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit">Record decision note</Button>
            <span className="text-[13px] text-ink-soft">Stored in this browser only.</span>
          </div>
        </form>
        {saved ? (
          <Notice tone="success" className="mt-5" role="status" title="Recorded" action={
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => exportRecord(saved, "md")}>
                <Download size={14} aria-hidden="true" /> Markdown
              </Button>
              <Button variant="secondary" size="sm" onClick={() => exportRecord(saved, "json")}>
                <Download size={14} aria-hidden="true" /> JSON
              </Button>
            </div>
          }>
            Export the note and attach it to the report folder or your approval ticket.
          </Notice>
        ) : null}
      </Card>

      <Card>
        <CardHeader title="Decision history" description="Automatic decisions from the attestation first, then reviewer notes recorded in this workspace." />
        <ol className="flex flex-col gap-3">
          {result.decisions.map((d) => (
            <li key={d.id} className="surface-sunken flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <DecisionBadge outcome={d.outcome} by={d.decided_by === "policy" ? "policy" : "human"} />
                <span className="text-small text-ink-soft">
                  by {d.decided_by} · policy_version {d.policy_version}
                </span>
              </div>
              <span className="font-mono text-[12px] text-ink-soft">{formatDateTime(d.decided_at)}</span>
            </li>
          ))}
          {reviews.map((r) => (
            <li key={r.id} className="flex flex-col gap-2">
              <ReviewRecordCard decision={r.decision} reviewer={r.reviewer} rationale={r.rationale} recordedAt={r.recordedAt} attestationId={r.attestationId} sample={sample} />
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => exportRecord(r, "md")}>
                  <Download size={14} aria-hidden="true" /> Export Markdown
                </Button>
                <Button variant="ghost" size="sm" onClick={() => exportRecord(r, "json")}>
                  <Download size={14} aria-hidden="true" /> Export JSON
                </Button>
              </div>
            </li>
          ))}
          {reviews.length === 0 ? <li className="text-small text-ink-soft">No reviewer note yet.</li> : null}
        </ol>
      </Card>
    </div>
  );
}
