"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field, Input, Select, Checkbox } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import { PageTitle } from "@/components/app/PageTitle";
import { formatDateTime, shortId } from "@/lib/evidence/derive";
import type { RiskLevel } from "@/lib/evidence/types";
import { ApiError } from "@/lib/api/client";
import { clientFor, currentOrganization, useApiLoad, useConnection } from "@/lib/api/connection";
import type { ContractDetail, Me, Registration } from "@/lib/api/types";
import { ApiErrorNotice, LiveBadge, LoadView } from "./States";

interface AgentsData {
  me: Me;
  agents: Registration[];
}

/** Register a sandbox agent, draft and approve its contract, start an attestation. */
export function HostedAgentsView() {
  const connection = useConnection();
  const [state, refresh] = useApiLoad<AgentsData>(
    async (client) => {
      const me = await client.me();
      const organization = currentOrganization(me, connection);
      if (!organization) return { me, agents: [] };
      return { me, agents: (await client.agents(organization.id)).agents };
    },
    [connection.organizationId],
  );

  return (
    <>
      <PageTitle
        title="Agents and contracts"
        intro="Register a sandbox endpoint, let Suncly draft the behavioural contract from its Agent Card, approve it as a named reviewer, then start an attestation within a spending limit. Nothing runs before approval."
      />
      <LoadView state={state} what="the agents">
        {({ me, agents }) => {
          const organization = currentOrganization(me, connection);
          if (!organization) return <Notice tone="info">Create an organization under Settings first.</Notice>;
          const canWrite = organization.role === "reviewer" || organization.role === "administrator";
          return (
            <div className="flex flex-col gap-6">
              <div className="flex flex-wrap items-center gap-2">
                <LiveBadge label={`Live: ${organization.name}`} />
                <Badge tone="neutral">role {organization.role ?? "member"}</Badge>
              </div>
              {canWrite ? <RegisterForm organizationId={organization.id} onDone={refresh} /> : <Notice tone="warn">Your role is {organization.role ?? "member"}: you can read agents and evidence; a reviewer registers agents and approves contracts.</Notice>}
              {agents.length ? agents.map((agent) => <AgentCard key={agent.id} organizationId={organization.id} agent={agent} canWrite={canWrite} />) : <Notice tone="info">No agent registered yet.</Notice>}
            </div>
          );
        }}
      </LoadView>
    </>
  );
}

function RegisterForm({ organizationId, onDone }: { organizationId: string; onDone: () => void }) {
  const connection = useConnection();
  const [name, setName] = useState("");
  const [cardUrl, setCardUrl] = useState("");
  const [risk, setRisk] = useState<RiskLevel>("high");
  const [sandbox, setSandbox] = useState(false);
  const [idempotent, setIdempotent] = useState(false);
  const [provider, setProvider] = useState<"none" | "secret-manager" | "env">("none");
  const [ref, setRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function submit() {
    const client = clientFor(connection);
    if (!client) return;
    setBusy(true);
    setError(null);
    try {
      await client.registerAgent(organizationId, {
        name: name.trim(),
        card_url: cardUrl.trim(),
        risk_level: risk,
        owner: "unspecified",
        sandbox_declared: sandbox,
        sandbox_idempotent: idempotent,
        credential: provider === "none" ? { provider: "none", ref: "" } : { provider, ref: ref.trim() },
        bring_your_own_model_key: false,
      });
      setName("");
      setCardUrl("");
      setSandbox(false);
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, null, (e as Error).message));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="section">
      <CardHeader title="Register a sandbox agent" description="The card URL must be reachable under the deployment's network mode (https to a public host in production). The credential is a reference, never the secret itself." />
      <form
        className="grid gap-4 md:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <Field id="reg-name" label="Name" required>
          <Input id="reg-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={200} />
        </Field>
        <Field id="reg-url" label="Agent Card URL" required help="…/.well-known/agent-card.json">
          <Input id="reg-url" value={cardUrl} onChange={(e) => setCardUrl(e.target.value)} required inputMode="url" />
        </Field>
        <Field id="reg-risk" label="Risk level" help="High-risk agents are never approved automatically.">
          <Select id="reg-risk" value={risk} onChange={(e) => setRisk(e.target.value as RiskLevel)}>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </Select>
        </Field>
        <Field id="reg-cred" label="Credential reference" help="Secret Manager resource name, or an environment variable name in development.">
          <div className="flex gap-2">
            <Select id="reg-cred-provider" aria-label="Credential provider" value={provider} onChange={(e) => setProvider(e.target.value as typeof provider)}>
              <option value="none">none</option>
              <option value="secret-manager">secret-manager</option>
              <option value="env">env (development)</option>
            </Select>
            <Input id="reg-cred" value={ref} onChange={(e) => setRef(e.target.value)} disabled={provider === "none"} placeholder={provider === "env" ? "SANDBOX_AGENT_TOKEN" : "projects/…/secrets/suncly-agent-…/versions/latest"} />
          </div>
        </Field>
        <div className="flex flex-col gap-3 md:col-span-2">
          <Checkbox id="reg-sandbox" checked={sandbox} onChange={(e) => setSandbox(e.target.checked)} label="This endpoint is a sandbox or dry-run endpoint (DR-006). Suncly cannot verify this; the declaration is recorded with every attestation." />
          <Checkbox id="reg-idem" checked={idempotent} onChange={(e) => setIdempotent(e.target.checked)} label="Repeating a call to this sandbox is harmless, so a run whose outcome is unknown may be repeated." />
        </div>
        {error ? (
          <div className="md:col-span-2">
            <ApiErrorNotice error={error} what="register the agent" />
          </div>
        ) : null}
        <div className="md:col-span-2">
          <Button type="submit" size="sm" disabled={busy || !name.trim() || !cardUrl.trim()}>
            {busy ? "Registering…" : "Register"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function AgentCard({ organizationId, agent, canWrite }: { organizationId: string; agent: Registration; canWrite: boolean }) {
  const connection = useConnection();
  const [contracts, refreshContracts] = useApiLoad<ContractDetail["contract"][]>(async (client) => (await client.contracts(organizationId, agent.id)).contracts, [agent.id]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [started, setStarted] = useState<string | null>(null);
  const [runs, setRuns] = useState(5);
  const [tck, setTck] = useState(false);

  async function act(label: string, work: (client: NonNullable<ReturnType<typeof clientFor>>) => Promise<void>) {
    const client = clientFor(connection);
    if (!client) return;
    setBusy(label);
    setError(null);
    try {
      await work(client);
      refreshContracts();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, null, (e as Error).message));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card as="article">
      <CardHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {agent.name}
            <RiskBadge level={agent.risk_level} />
            {agent.archived_at ? <Badge tone="neutral">archived</Badge> : null}
            {agent.sandbox_declared ? <Badge tone="pass">sandbox declared</Badge> : <Badge tone="fail">not a declared sandbox</Badge>}
          </span>
        }
        description={
          <span className="font-mono text-[12px]">
            {agent.card_url} · registered {formatDateTime(agent.created_at)} by {agent.created_by} · network mode {agent.deployment_mode}
          </span>
        }
        action={
          canWrite && !agent.archived_at ? (
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="secondary" disabled={busy !== null} onClick={() => act("draft", async (c) => void (await c.draftContract(organizationId, agent.id, "deterministic")))}>
                {busy === "draft" ? "Drafting…" : "Draft contract"}
              </Button>
              <Button size="sm" variant="secondary" disabled={busy !== null} onClick={() => act("model", async (c) => void (await c.draftContract(organizationId, agent.id, "model")))}>
                {busy === "model" ? "Drafting…" : "Draft with the model"}
              </Button>
              <Button size="sm" variant="danger" disabled={busy !== null} onClick={() => act("archive", async (c) => void (await c.archiveAgent(organizationId, agent.id)))}>
                Archive
              </Button>
            </div>
          ) : null
        }
      />
      {error ? <ApiErrorNotice error={error} what="update the agent" /> : null}
      {started ? (
        <Notice tone="success" role="status" title="Attestation queued">
          <Link href={`/app/hosted/attestation?id=${started}`}>Follow its progress</Link>.
        </Notice>
      ) : null}
      <div className="mt-3">
        <LoadView state={contracts} what="the contracts" empty={{ isEmpty: (list) => list.length === 0, view: <p className="text-small text-ink-soft">No contract yet. Draft one from the card.</p> }}>
          {(list) => (
            <ul className="flex flex-col gap-2">
              {list.map((contract) => (
                <li key={contract.id} className="surface-sunken flex flex-wrap items-center justify-between gap-3 p-3 text-small">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[12px]">v{contract.version} · {shortId(contract.id)}</span>
                    <Badge tone={contract.status === "approved" ? "pass" : contract.status === "draft" ? "inconclusive" : "neutral"}>{contract.status}</Badge>
                    {contract.approved_by ? <span className="text-ink-soft">approved by {contract.approved_by}</span> : null}
                  </span>
                  {canWrite && !agent.archived_at ? (
                    <span className="flex flex-wrap items-center gap-2">
                      {contract.status === "draft" ? (
                        <>
                          <Button size="sm" disabled={busy !== null} onClick={() => act("approve", async (c) => void (await c.approveContract(organizationId, contract.id)))}>
                            Approve as me
                          </Button>
                          <Button size="sm" variant="ghost" disabled={busy !== null} onClick={() => act("reject", async (c) => void (await c.rejectContract(organizationId, contract.id)))}>
                            Reject
                          </Button>
                        </>
                      ) : null}
                      {contract.status === "approved" && agent.sandbox_declared ? (
                        <>
                          <label className="flex items-center gap-1 text-[13px]">
                            runs
                            <Input aria-label="Runs per test case" type="number" min={1} max={200} value={runs} onChange={(e) => setRuns(Number(e.target.value) || 1)} className="w-20" />
                          </label>
                          <label className="flex items-center gap-1 text-[13px]">
                            <input type="checkbox" checked={tck} onChange={(e) => setTck(e.target.checked)} /> A2A TCK
                          </label>
                          <Button
                            size="sm"
                            disabled={busy !== null}
                            onClick={() =>
                              act("start", async (c) => {
                                const item = await c.startAttestation(organizationId, {
                                  registration_id: agent.id,
                                  contract_id: contract.id,
                                  runs,
                                  trigger: "manual",
                                  external_tools: tck ? ["a2a-tck"] : [],
                                });
                                setStarted(item.attestation.id);
                              })
                            }
                          >
                            {busy === "start" ? "Starting…" : "Start attestation"}
                          </Button>
                        </>
                      ) : null}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </LoadView>
      </div>
    </Card>
  );
}
