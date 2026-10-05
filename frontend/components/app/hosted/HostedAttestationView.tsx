"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field, Select, Textarea } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import { KeyValue, Meter } from "@/components/ui/Stat";
import { EvaluationView } from "@/components/evidence/EvaluationView";
import { PageTitle, Loading } from "@/components/app/PageTitle";
import { formatDateTime } from "@/lib/evidence/derive";
import type { DecisionOutcome } from "@/lib/evidence/types";
import { ApiError } from "@/lib/api/client";
import { clientFor, currentOrganization, useApiLoad, useConnection } from "@/lib/api/connection";
import type { AttestationItem, Evidence, Me, Verification } from "@/lib/api/types";
import { ApiErrorNotice, LiveBadge, LoadView } from "./States";

interface AttestationData {
  me: Me;
  organizationId: string;
  item: AttestationItem;
  evidence: Evidence | null;
  verification: Verification | null;
}

const FINAL = new Set(["completed", "failed", "cancelled", "invalidated"]);

/** One hosted attestation: live progress while it runs, then the evidence, the verification layers and the decision. */
export function HostedAttestationView() {
  const params = useSearchParams();
  const id = params.get("id");
  const connection = useConnection();
  const [state, refresh] = useApiLoad<AttestationData>(
    async (client) => {
      const me = await client.me();
      const organization = currentOrganization(me, connection);
      if (!organization || !id) throw new ApiError(404, null, "No attestation id in the link.");
      const item = await client.attestation(organization.id, id);
      const final = FINAL.has(item.attestation.status);
      const [evidence, verification] = final ? await Promise.all([client.evidence(organization.id, id), client.verification(organization.id, id).catch(() => null)]) : [null, null];
      return { me, organizationId: organization.id, item, evidence, verification };
    },
    [id, connection.organizationId],
  );

  // Poll while the job is not final.
  useEffect(() => {
    if (state.kind !== "ready" || FINAL.has(state.data.item.attestation.status)) return;
    const timer = window.setTimeout(refresh, 2500);
    return () => window.clearTimeout(timer);
  }, [state, refresh]);

  if (!id) return <Notice tone="warn">No attestation id in the link.</Notice>;

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-4 text-[13px] text-ink-soft">
        <ol className="flex flex-wrap items-center gap-1.5">
          <li>
            <Link href="/app/hosted" className="hover:text-ink">
              Hosted overview
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" className="font-mono">
            {id.slice(0, 8)}
          </li>
        </ol>
      </nav>
      <LoadView state={state} what="the attestation">
        {({ me, organizationId, item, evidence, verification }) => {
          const organization = currentOrganization(me, connection);
          const canResolve = organization?.role === "reviewer" || organization?.role === "administrator";
          const progress = item.progress;
          const planned = Number(progress.planned_runs ?? item.meta.runs_planned ?? 0);
          const recorded = Number(progress.recorded_runs ?? 0);
          return (
            <div className="flex flex-col gap-6">
              <PageTitle
                title="Attestation"
                intro={
                  <span className="flex flex-wrap items-center gap-2">
                    <LiveBadge />
                    <StatusBadge status={item.attestation.status} />
                    {item.job ? <Badge tone="neutral">job {item.job.status}, attempt {item.job.attempts}/{item.job.max_attempts}</Badge> : null}
                    {item.job?.cancel_requested ? <Badge tone="inconclusive">cancellation requested</Badge> : null}
                  </span>
                }
                actions={
                  !FINAL.has(item.attestation.status) && canResolve ? (
                    <CancelButton organizationId={organizationId} attestationId={item.attestation.id} onDone={refresh} />
                  ) : (
                    <Button size="sm" variant="secondary" onClick={refresh}>
                      Refresh
                    </Button>
                  )
                }
              />
              {!FINAL.has(item.attestation.status) ? (
                <Card>
                  <CardHeader title="Progress" description="Persisted by the worker after every run; a worker that dies resumes here without repeating a recorded run." />
                  <Meter value={recorded} max={Math.max(planned, 1)} label={`${recorded} of ${planned} runs recorded`} />
                  <KeyValue
                    className="mt-4"
                    items={[
                      ["Phase", String(progress.phase ?? "queued")],
                      ["Started", formatDateTime(item.attestation.started_at)],
                      ["Started by", item.meta.created_by],
                      ["Contract", `v${item.contract.version} · ${item.contract.content_hash.slice(0, 23)}…`],
                      ["Suite / judge", `${item.meta.suite_version} · ${item.meta.judge_version}`],
                      ["Last error", item.job?.last_error ?? "–"],
                    ]}
                  />
                </Card>
              ) : null}
              {verification ? <VerificationCard verification={verification} /> : null}
              {evidence ? (
                <EvaluationView
                  bundle={{ result: evidence.result, transcripts: evidence.transcripts }}
                  heading="h2"
                  review={canResolve ? <ResolveForm organizationId={organizationId} attestationId={item.attestation.id} evidence={evidence} onDone={refresh} /> : <Notice tone="info">A reviewer or administrator records the human decision.</Notice>}
                  hasLocalReview={Boolean(item.meta.decided_by_reviewer)}
                />
              ) : FINAL.has(item.attestation.status) ? (
                <Loading label="Loading the evidence" />
              ) : null}
            </div>
          );
        }}
      </LoadView>
    </>
  );
}

function VerificationCard({ verification }: { verification: Verification }) {
  const layers: Array<[string, keyof Verification, string]> = [
    ["Cryptographic validity", "cryptographic", "signature, hashes and counts"],
    ["Issuer trust", "issuer_trust", "the key is in the deployment's registry and not revoked"],
    ["Freshness", "freshness", "issued and not expired"],
    ["Policy acceptability", "policy", "the latest decision approves under the policy in force"],
  ];
  return (
    <Card>
      <CardHeader title="Verification layers" description="Four separate answers, as the CI gate reads them. A valid signature never implies approval." />
      <ul className="grid gap-2 md:grid-cols-2">
        {layers.map(([label, key, hint]) => {
          const layer = verification[key] as { ok?: boolean; checks?: Array<{ name: string; ok: boolean; detail: string }> } | undefined;
          const ok = layer?.ok === true;
          const failing = (layer?.checks ?? []).filter((c) => !c.ok);
          return (
            <li key={key} className="surface-sunken flex items-start gap-3 p-3">
              <Badge tone={ok ? "pass" : "fail"}>{ok ? "ok" : "no"}</Badge>
              <span className="min-w-0 text-small">
                <span className="font-semibold text-ink">{label}</span>
                <span className="block text-ink-soft">{failing.length ? failing.map((c) => `${c.name}: ${c.detail}`).join("; ") : hint}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function CancelButton({ organizationId, attestationId, onDone }: { organizationId: string; attestationId: string; onDone: () => void }) {
  const connection = useConnection();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  return (
    <div className="flex flex-col items-end gap-2">
      <Button
        size="sm"
        variant="danger"
        disabled={busy}
        onClick={async () => {
          const client = clientFor(connection);
          if (!client) return;
          setBusy(true);
          try {
            await client.cancelAttestation(organizationId, attestationId);
            onDone();
          } catch (e) {
            setError(e instanceof ApiError ? e : new ApiError(0, null, (e as Error).message));
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Cancelling…" : "Cancel attestation"}
      </Button>
      {error ? <ApiErrorNotice error={error} what="cancel" /> : null}
    </div>
  );
}

function ResolveForm({ organizationId, attestationId, evidence, onDone }: { organizationId: string; attestationId: string; evidence: Evidence; onDone: () => void }) {
  const connection = useConnection();
  const decisions = evidence.result.decisions;
  const latest = decisions[decisions.length - 1];
  const [outcome, setOutcome] = useState<DecisionOutcome>("approve");
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const notes = evidence.result.decision_notes ?? [];

  if (evidence.result.attestation.status !== "completed") {
    return <Notice tone="info">A {evidence.result.attestation.status} attestation carries no decision and cannot be resolved; run a new one.</Notice>;
  }
  if (!latest || latest.outcome !== "flag") {
    return (
      <div className="flex flex-col gap-3">
        <Notice tone={latest?.outcome === "approve" ? "success" : "warn"} title={`Latest decision: ${latest?.outcome ?? "none"}`}>
          {latest ? `By ${latest.decided_by} on ${formatDateTime(latest.decided_at)} under policy ${latest.policy_version}.` : "No decision was recorded."}
        </Notice>
        {notes.map((note, i) => (
          <div key={i} className="surface-sunken p-3 text-small">
            <span className="font-semibold">{String(note.reviewer_subject)}</span>: {String(note.rationale)}
          </div>
        ))}
      </div>
    );
  }
  return (
    <Card>
      <CardHeader title="Resolve the flag" description="Your decision is recorded as a second decision with your verified identity and an append-only note. The first decision is never edited." />
      <form
        className="flex flex-col gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          const client = clientFor(connection);
          if (!client) return;
          setBusy(true);
          setError(null);
          try {
            await client.resolve(organizationId, attestationId, outcome, rationale.trim());
            setRationale("");
            onDone();
          } catch (err) {
            setError(err instanceof ApiError ? err : new ApiError(0, null, (err as Error).message));
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field id="resolve-outcome" label="Outcome">
          <Select id="resolve-outcome" value={outcome} onChange={(e) => setOutcome(e.target.value as DecisionOutcome)}>
            <option value="approve">approve</option>
            <option value="block">block</option>
          </Select>
        </Field>
        <Field id="resolve-rationale" label="Rationale" help="At least 20 characters a colleague could act on." required>
          <Textarea id="resolve-rationale" value={rationale} onChange={(e) => setRationale(e.target.value)} rows={4} minLength={20} required />
        </Field>
        {error ? <ApiErrorNotice error={error} what="record the decision" /> : null}
        <div>
          <Button type="submit" size="sm" disabled={busy || rationale.trim().length < 20}>
            {busy ? "Recording…" : "Record decision"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
