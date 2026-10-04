"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeftRight, ArrowRight } from "lucide-react";
import { ButtonLink } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { EmptyState } from "@/components/ui/EmptyState";
import { Notice } from "@/components/ui/Notice";
import { KeyValue } from "@/components/ui/Stat";
import { Table } from "@/components/ui/Table";
import { Badge, DecisionBadge, RiskBadge, SampleBadge, StatusBadge } from "@/components/ui/Badge";
import { SkillCoverageList } from "@/components/evidence/NotTested";
import { PageTitle, Loading } from "./PageTitle";
import { decisionState, formatDateTime, pendingActions, shortId, targetInterface, totals } from "@/lib/evidence/derive";
import { buildAttestCommand } from "@/lib/cli";
import { bundlesByAgent, useWorkspaceState } from "@/lib/workspace/store";

export function AgentPage() {
  const params = useSearchParams();
  const id = params.get("id");
  const { state, ready } = useWorkspaceState();
  if (!ready) return <Loading />;

  const history = id ? bundlesByAgent(Object.values(state.bundles)).get(id) : undefined;
  if (!history || history.length === 0) {
    return (
      <EmptyState
        title="Agent not found"
        body="No evaluation of this agent is in the workspace."
        actions={<ButtonLink href="/app">Back to the overview</ButtonLink>}
      />
    );
  }

  const latest = history[history.length - 1];
  const { result } = latest;
  const card = result.parsed_card.card;
  const iface = targetInterface(result);
  const securitySchemes = (result.parsed_card.json_object as { securitySchemes?: unknown }).securitySchemes;
  const actions = pendingActions(result, (state.reviews[result.attestation.id] ?? []).length > 0);
  const completed = history.filter((b) => b.result.attestation.status === "completed");
  const previous = completed.length >= 2 ? completed[completed.length - 2] : null;
  const latestCompleted = completed[completed.length - 1];
  const rerun = buildAttestCommand({
    cardUrl: result.card_url ?? "<card-url>",
    sandboxDeclared: true,
    runs: null,
    budget: null,
    approveAs: "<your identifier>",
    owner: "",
    riskLevel: "",
    contractPath: "",
    reportsDir: "./suncly-reports",
    needsCredential: false,
    json: false,
  });

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-4 text-[13px] text-ink-soft">
        <ol className="flex flex-wrap items-center gap-1.5">
          <li>
            <Link href="/app" className="hover:text-ink">Overview</Link>
          </li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" className="text-ink">{result.agent.name}</li>
        </ol>
      </nav>
      <PageTitle
        title={result.agent.name}
        intro={card.description}
        actions={
          previous && latestCompleted ? (
            <ButtonLink href={`/app/compare?a=${previous.result.attestation.id}&b=${latestCompleted.result.attestation.id}`} variant="secondary" size="sm">
              <ArrowLeftRight size={14} aria-hidden="true" />
              Compare last two
            </ButtonLink>
          ) : null
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          {latest.source === "sample" ? <SampleBadge /> : null}
          <RiskBadge level={result.agent.risk_level} />
          <Badge tone="neutral">owner {result.agent.owner}</Badge>
          <Badge tone="neutral">card v{card.version || "–"}</Badge>
          <Badge tone="neutral">{card.skills.length} declared skills</Badge>
          <Badge tone="neutral">{history.length} evaluation{history.length === 1 ? "" : "s"}</Badge>
        </div>
      </PageTitle>

      {actions.length ? (
        <div className="mb-6 flex flex-col gap-3">
          {actions.map((a) => (
            <Notice
              key={a.kind}
              tone={a.kind === "human_review" ? "warn" : "error"}
              title={a.title}
              action={
                <ButtonLink href={`/app/evaluation?id=${result.attestation.id}${a.kind === "human_review" ? "&tab=review" : ""}`} size="sm" variant="secondary">
                  Open latest
                </ButtonLink>
              }
            >
              {a.detail}
            </Notice>
          ))}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Declared capabilities and coverage" description="From the latest card version. Tested skills show the latest counts; untested skills say why." />
            <SkillCoverageList result={result} />
          </Card>

          <Card padded={false} className="overflow-hidden">
            <div className="p-5 pb-0 md:p-6 md:pb-0">
              <CardHeader title="Evaluation history" description="Every attestation of this card URL in the workspace, newest first. Same card hash means the same approved contract ran." />
            </div>
            <div className="p-5 pt-0 md:p-6 md:pt-0">
              <Table caption="Evaluation history for this agent">
                <thead>
                  <tr>
                    <th scope="col">Started</th>
                    <th scope="col">Card</th>
                    <th scope="col">Contract</th>
                    <th scope="col">Evaluation status</th>
                    <th scope="col">Approval status</th>
                    <th scope="col" className="num">Pass</th>
                    <th scope="col" className="num">Fail</th>
                    <th scope="col" className="num">Inconclusive</th>
                    <th scope="col"><span className="sr-only">Open</span></th>
                  </tr>
                </thead>
                <tbody>
                  {[...history].reverse().map((b, i, arr) => {
                    const sums = totals(b.result);
                    const d = decisionState(b.result);
                    const policy = d.kind === "none" ? null : d.decision;
                    const older = arr[i + 1];
                    const cardChanged = older ? older.result.card_version.card_hash !== b.result.card_version.card_hash : false;
                    return (
                      <tr key={b.result.attestation.id}>
                        <td className="whitespace-nowrap">
                          <span className="text-ink">{formatDateTime(b.result.attestation.started_at)}</span>
                          <span className="block font-mono text-[12px] text-ink-soft">{shortId(b.result.attestation.id)} · {b.result.attestation.trigger}</span>
                        </td>
                        <td>
                          <span className="font-mono text-[12px] text-ink">{b.result.card_version.card_hash.slice(7, 15)}</span>
                          {cardChanged ? <Badge tone="fail" className="ml-2">changed</Badge> : older ? <span className="ml-2 text-[12px] text-ink-soft">unchanged</span> : null}
                        </td>
                        <td className="text-ink-soft">v{b.result.contract.version}</td>
                        <td><StatusBadge status={b.result.attestation.status} /></td>
                        <td><DecisionBadge outcome={policy?.outcome ?? null} by={policy ? "policy" : undefined} /></td>
                        <td className="num text-pass">{sums.pass}</td>
                        <td className="num text-fail">{sums.fail}</td>
                        <td className="num text-partial">{sums.inconclusive}</td>
                        <td className="num">
                          <Link href={`/app/evaluation?id=${b.result.attestation.id}`} className="inline-flex h-8 items-center gap-1 rounded-full px-2.5 text-[12px] font-semibold text-ink hover:bg-cream">
                            Open <ArrowRight size={14} aria-hidden="true" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </div>
            <p className="px-5 pb-5 text-[13px] text-ink-soft md:px-6 md:pb-6">
              An unchanged card is not proof of an unchanged agent. Compare the counts, not the hash.
            </p>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Identity and source" as="h2" />
            <KeyValue
              items={[
                ["Agent id", <span key="i" className="font-mono text-[12px]">{result.agent.id}</span>],
                ["Derived from", "the card URL (UUID v5)"],
                ["Card URL", <span key="u" className="font-mono text-[12px]">{result.card_url ?? "–"}</span>],
                ["Protocol", iface ? `A2A ${iface.protocol_version} over ${iface.protocol_binding}` : "–"],
                ["Source workflow", "Any framework or model behind an A2A 1.0 Agent Card. Suncly tests the interface, not the implementation."],
                ["Latest card hash", <span key="h" className="font-mono text-[12px]">{result.card_version.card_hash}</span>],
                ["First seen in workspace", formatDateTime(history[0].result.card_version.fetched_at)],
              ]}
            />
          </Card>

          <Card>
            <CardHeader title="Access requirements" as="h2" description="What a run needs to reach this agent." />
            <KeyValue
              items={[
                ["Endpoint", <span key="e" className="font-mono text-[12px]">{iface?.url ?? "–"}</span>],
                ["Sandbox", "Declare with --sandbox. Suncly only tests sandbox or dry-run endpoints."],
                ["Credential", "If required, SUNCLY_AGENT_AUTHORIZATION in the Runner's environment; redacted from every transcript."],
                ["Declared security schemes", securitySchemes ? <pre key="s" className="font-mono text-[11px] text-ink-soft">{JSON.stringify(securitySchemes, null, 1)}</pre> : "none declared in the card"],
                ["Declared capabilities", [card.capabilities.streaming ? "streaming" : null, card.capabilities.push_notifications ? "pushNotifications" : null, card.capabilities.extended_agent_card ? "extendedAgentCard" : null].filter(Boolean).join(", ") || "none"],
              ]}
            />
          </Card>

          <Card>
            <CardHeader title="Re-evaluate" as="h2" description="Same card URL. An unchanged card reuses its approved contract; a changed card drafts a new one that needs approval." />
            <CodeBlock code={rerun} label="re-evaluation command" lines />
            <p className="mt-3 text-[13px] text-ink-soft">
              Adjust runs, budget and the contract file in <Link href="/app/new" className="font-semibold text-ink underline underline-offset-4">New evaluation</Link>. Import the new report folder when it finishes.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
