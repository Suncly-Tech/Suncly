"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Stat } from "@/components/ui/Stat";
import { Badge, RiskBadge, StatusBadge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/Button";
import { PageTitle } from "@/components/app/PageTitle";
import { formatDateTime, shortId } from "@/lib/evidence/derive";
import { currentOrganization, useApiLoad, useConnection } from "@/lib/api/connection";
import type { AttestationItem, Me, Registration } from "@/lib/api/types";
import { LiveBadge, LoadView } from "./States";

interface OverviewData {
  me: Me;
  agents: Registration[];
  attestations: AttestationItem[];
}

export function HostedOverview() {
  const connection = useConnection();
  const [state, refresh] = useApiLoad<OverviewData>(
    async (client) => {
      const me = await client.me();
      const organization = currentOrganization(me, connection);
      if (!organization) return { me, agents: [], attestations: [] };
      const [agents, attestations] = await Promise.all([client.agents(organization.id), client.attestations(organization.id)]);
      return { me, agents: agents.agents, attestations: attestations.attestations };
    },
    [connection.organizationId],
  );

  return (
    <>
      <PageTitle
        title="Hosted overview"
        intro="What the connected Suncly API holds for your organization: registered sandbox agents, attestations and the ones waiting on a person. Execution status and approval status stay separate."
        actions={
          <>
            <ButtonLink href="/app/hosted/agents" size="sm">
              Agents and contracts
            </ButtonLink>
            <ButtonLink href="/app/hosted/billing" size="sm" variant="secondary">
              Usage and billing
            </ButtonLink>
          </>
        }
      />
      <LoadView state={state} what="the overview">
        {({ me, agents, attestations }) => {
          const organization = currentOrganization(me, connection);
          if (!organization) {
            return <EmptyState title="No organization" body="Create one under Settings; you become its administrator." actions={<ButtonLink href="/app/settings#connection">Settings</ButtonLink>} />;
          }
          const running = attestations.filter((a) => !["completed", "failed", "cancelled", "invalidated"].includes(a.attestation.status));
          const flagged = attestations.filter((a) => a.attestation.status === "completed" && a.meta.decided_by_reviewer === null && lastDecision(a) === "flag");
          return (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <LiveBadge label={`Live: ${organization.name}`} />
                <Badge tone="neutral">role {organization.role ?? "member"}</Badge>
                <button type="button" className="btn-base btn-ghost btn-sm" onClick={refresh}>
                  Refresh
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <Stat label="Agents" value={agents.filter((a) => !a.archived_at).length} hint="registered sandboxes" />
                <Stat label="Attestations" value={attestations.length} hint="in this organization" />
                <Stat label="Running or queued" value={running.length} tone={running.length ? "inconclusive" : "ink"} />
                <Stat label="Flagged, unresolved" value={flagged.length} tone={flagged.length ? "fail" : "ink"} hint="waiting on a reviewer" />
              </div>
              <Card className="mt-6" padded={false}>
                <div className="p-5 pb-0 md:p-6 md:pb-0">
                  <CardHeader title="Recent attestations" description="Newest first. Open one for its live progress, evidence, verification layers and decision." />
                </div>
                {attestations.length ? (
                  <ul className="divide-y divide-line">
                    {attestations.slice(0, 20).map((item) => (
                      <li key={item.attestation.id} className="flex flex-col gap-2 px-5 py-4 md:flex-row md:items-center md:justify-between md:px-6">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-ink">{agentName(agents, item.registration_id)}</span>
                            <StatusBadge status={item.attestation.status} />
                            {lastDecision(item) ? <Badge tone={lastDecision(item) === "approve" ? "pass" : lastDecision(item) === "block" ? "fail" : "inconclusive"}>{lastDecision(item)}</Badge> : null}
                            {item.job && item.job.status === "running" ? <Badge tone="info">running: {String(item.progress.recorded_runs ?? 0)}/{String(item.progress.planned_runs ?? "?")} runs</Badge> : null}
                          </div>
                          <p className="mt-1 font-mono text-[12px] text-ink-soft">
                            {shortId(item.attestation.id)} · {formatDateTime(item.attestation.started_at)} · trigger {item.attestation.trigger} · by {item.meta.created_by}
                          </p>
                        </div>
                        <Link href={`/app/hosted/attestation?id=${item.attestation.id}`} className="btn-base btn-secondary btn-sm shrink-0">
                          Open
                          <ArrowRight size={14} aria-hidden="true" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="px-5 pb-5 text-small text-ink-soft md:px-6 md:pb-6">No attestation yet. Register an agent, approve its contract and start one.</p>
                )}
              </Card>
              <Card className="mt-6">
                <CardHeader title="Agents" description="Registered sandbox endpoints and their risk level." />
                {agents.length ? (
                  <ul className="flex flex-col gap-2">
                    {agents.map((agent) => (
                      <li key={agent.id} className="flex flex-wrap items-center justify-between gap-2 text-small">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-ink">{agent.name}</span>
                          <RiskBadge level={agent.risk_level} />
                          {agent.archived_at ? <Badge tone="neutral">archived</Badge> : null}
                          {!agent.sandbox_declared ? <Badge tone="fail">not declared a sandbox</Badge> : null}
                        </span>
                        <span className="font-mono text-[12px] text-ink-soft">{agent.card_url}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-small text-ink-soft">No agent registered yet.</p>
                )}
              </Card>
            </>
          );
        }}
      </LoadView>
    </>
  );
}

function agentName(agents: Registration[], registrationId: string): string {
  return agents.find((a) => a.id === registrationId)?.name ?? shortId(registrationId);
}

export function lastDecision(item: AttestationItem): string | null {
  const evaluation = item.progress.policy_evaluation as { outcome?: string } | null | undefined;
  if (item.meta.decided_by_reviewer) return "resolved";
  return evaluation?.outcome ?? null;
}
