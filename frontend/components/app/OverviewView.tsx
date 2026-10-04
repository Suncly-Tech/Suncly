"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button, ButtonLink } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Notice } from "@/components/ui/Notice";
import { Stat } from "@/components/ui/Stat";
import { Table } from "@/components/ui/Table";
import { Badge, DecisionBadge, RiskBadge, SampleBadge, StatusBadge } from "@/components/ui/Badge";
import { PageTitle, Loading } from "./PageTitle";
import { compareEvaluations } from "@/lib/evidence/compare";
import { decisionState, formatDateTime, shortId, totals } from "@/lib/evidence/derive";
import { sampleBundles } from "@/lib/sample";
import { addBundle, bundlesByAgent, markSampleLoaded, sortedByStart, useWorkspaceState } from "@/lib/workspace/store";

export function OverviewView() {
  const { state, ready } = useWorkspaceState();
  if (!ready) return <Loading />;

  const bundles = Object.values(state.bundles);
  if (bundles.length === 0) return <FirstRun />;

  const byAgent = bundlesByAgent(bundles);
  const recent = sortedByStart(bundles);
  const outstanding = recent.filter((b) => {
    const d = decisionState(b.result);
    return d.kind === "automatic_flag" && d.human.length === 0 && !(state.reviews[b.result.attestation.id]?.length);
  });
  const noDecision = recent.filter((b) => decisionState(b.result).kind === "none");
  const hasSample = bundles.some((b) => b.source === "sample");

  const changes = [...byAgent.entries()]
    .map(([agentId, list]) => {
      const completed = list.filter((b) => b.result.attestation.status === "completed");
      if (completed.length < 2) return null;
      const older = completed[completed.length - 2];
      const newer = completed[completed.length - 1];
      const c = compareEvaluations(older.result, newer.result);
      return { agentId, name: newer.result.agent.name, older, newer, c, sample: newer.source === "sample" };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null);

  return (
    <>
      <PageTitle
        title="Overview"
        intro="Evaluated agents, recent evaluations, reviews waiting on a person, and what changed since last time. Evaluation status and approval status are shown separately: a completed evaluation is not an approval."
        actions={
          <>
            <ButtonLink href="/app/import" variant="secondary" size="sm">
              Import report
            </ButtonLink>
            <ButtonLink href="/app/new" size="sm">
              New evaluation
            </ButtonLink>
          </>
        }
      >
        {hasSample ? (
          <Notice tone="sample" title="Sample data is loaded">
            Bundles marked “Sample data” are synthetic and come from the fictional Harbor Returns Agent. Remove them from <Link href="/app/settings">Settings</Link> when you load real reports.
          </Notice>
        ) : null}
      </PageTitle>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Agents" value={byAgent.size} hint="distinct card URLs" />
        <Stat label="Evaluations" value={bundles.length} hint="report folders loaded" />
        <Stat label="Awaiting human review" value={outstanding.length} tone={outstanding.length ? "inconclusive" : "ink"} hint="flagged, no reviewer note yet" />
        <Stat label="Without a decision" value={noDecision.length} tone={noDecision.length ? "fail" : "ink"} hint="failed, invalidated or cancelled" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <Card padded={false} className="overflow-hidden">
          <div className="p-5 pb-0 md:p-6 md:pb-0">
            <CardHeader title="Outstanding reviews" description="The Policy engine recorded flag and nobody has recorded a decision in this workspace." />
          </div>
          {outstanding.length ? (
            <ul className="divide-y divide-line">
              {outstanding.map((b) => {
                const sums = totals(b.result);
                return (
                  <li key={b.result.attestation.id} className="flex flex-col gap-2 px-5 py-4 md:flex-row md:items-center md:justify-between md:px-6">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">{b.result.agent.name}</span>
                        {b.source === "sample" ? <SampleBadge /> : null}
                        <RiskBadge level={b.result.agent.risk_level} />
                      </div>
                      <p className="mt-1 font-mono text-[12px] text-ink-soft">
                        {shortId(b.result.attestation.id)} · {formatDateTime(b.result.attestation.started_at)} ·{" "}
                        <span className="text-pass">{sums.pass} pass</span> · <span className="text-fail">{sums.fail} fail</span> ·{" "}
                        <span className="text-partial">{sums.inconclusive} inconclusive</span>
                      </p>
                    </div>
                    <Link href={`/app/evaluation?id=${b.result.attestation.id}&tab=review`} className="btn-base btn-secondary btn-sm shrink-0">
                      Review evidence
                      <ArrowRight size={14} aria-hidden="true" />
                    </Link>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="px-5 pb-5 text-small text-ink-soft md:px-6 md:pb-6">Nothing is waiting. Every flagged evaluation has a reviewer note.</p>
          )}
        </Card>

        <Card>
          <CardHeader title="What changed" description="Latest two completed evaluations per agent, compared test case by test case." />
          {changes.length ? (
            <ul className="flex flex-col gap-3">
              {changes.map(({ agentId, name, older, newer, c, sample }) => (
                <li key={agentId} className="surface-sunken p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-ink">{name}</span>
                    {sample ? <SampleBadge /> : null}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    <Badge tone={c.cardHashChanged ? "fail" : "neutral"}>Card {c.cardHashChanged ? "changed" : "unchanged"}</Badge>
                    {c.summary.regressed ? <Badge tone="fail" dot>{c.summary.regressed} regressed</Badge> : null}
                    {c.summary.improved ? <Badge tone="pass" dot>{c.summary.improved} improved</Badge> : null}
                    {!c.summary.regressed && !c.summary.improved ? <Badge tone="neutral">No change in counts</Badge> : null}
                  </div>
                  <Link
                    href={`/app/compare?a=${older.result.attestation.id}&b=${newer.result.attestation.id}`}
                    className="mt-3 inline-flex items-center gap-1 text-[13px] font-semibold text-ink underline-offset-4 hover:underline"
                  >
                    Open comparison
                    <ArrowRight size={14} aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-small text-ink-soft">Load two completed evaluations of the same agent to see what changed between them.</p>
          )}
        </Card>
      </div>

      <Card padded={false} className="mt-6 overflow-hidden">
        <div className="p-5 pb-0 md:p-6 md:pb-0">
          <CardHeader title="Recent evaluations" description="Newest first. Evaluation status says what happened to the run; approval status says what was decided." />
        </div>
        <div className="p-5 pt-0 md:p-6 md:pt-0">
          <Table caption="Recent evaluations with status, decision and counts">
            <thead>
              <tr>
                <th scope="col">Agent</th>
                <th scope="col">Started</th>
                <th scope="col">Evaluation status</th>
                <th scope="col">Approval status</th>
                <th scope="col" className="num">Pass</th>
                <th scope="col" className="num">Fail</th>
                <th scope="col" className="num">Inconclusive</th>
                <th scope="col"><span className="sr-only">Open</span></th>
              </tr>
            </thead>
            <tbody>
              {recent.map((b) => {
                const sums = totals(b.result);
                const d = decisionState(b.result);
                const policy = d.kind === "none" ? null : d.decision;
                return (
                  <tr key={b.result.attestation.id}>
                    <td>
                      <div className="flex flex-wrap items-center gap-2">
                        <Link href={`/app/agent?id=${b.result.agent.id}`} className="font-semibold text-ink underline-offset-4 hover:underline">
                          {b.result.agent.name}
                        </Link>
                        {b.source === "sample" ? <SampleBadge /> : null}
                      </div>
                      <span className="font-mono text-[12px] text-ink-soft">{shortId(b.result.attestation.id)}</span>
                    </td>
                    <td className="whitespace-nowrap text-ink-soft">{formatDateTime(b.result.attestation.started_at)}</td>
                    <td><StatusBadge status={b.result.attestation.status} /></td>
                    <td><DecisionBadge outcome={policy?.outcome ?? null} by={policy ? "policy" : undefined} /></td>
                    <td className="num text-pass">{sums.pass}</td>
                    <td className="num text-fail">{sums.fail}</td>
                    <td className="num text-partial">{sums.inconclusive}</td>
                    <td className="num">
                      <Link href={`/app/evaluation?id=${b.result.attestation.id}`} className="inline-flex h-8 items-center gap-1 rounded-full px-2.5 text-[12px] font-semibold text-ink hover:bg-cream">
                        Open
                        <ArrowRight size={14} aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      </Card>

      <Card className="mt-6">
        <CardHeader title="Agents" description="One entry per card URL. Open an agent for its declared skills, access requirements and full history." />
        <ul className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {[...byAgent.entries()].map(([agentId, list]) => {
            const latest = list[list.length - 1];
            return (
              <li key={agentId}>
                <Link href={`/app/agent?id=${agentId}`} className="surface-sunken group flex h-full flex-col gap-2 p-4 transition-shadow hover:shadow-raised">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-ink">{latest.result.agent.name}</span>
                    {latest.source === "sample" ? <SampleBadge /> : null}
                  </div>
                  <span className="text-[13px] text-ink-soft">
                    {list.length} evaluation{list.length === 1 ? "" : "s"} · card v{latest.result.parsed_card.card.version || "–"} · {latest.result.parsed_card.card.skills.length} skills
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    <RiskBadge level={latest.result.agent.risk_level} />
                    <StatusBadge status={latest.result.attestation.status} />
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </Card>
    </>
  );
}

function FirstRun() {
  function loadSample() {
    for (const b of sampleBundles) addBundle(b, "sample", "Sample data set (frontend/lib/sample)");
    markSampleLoaded(true);
  }
  return (
    <>
      <PageTitle title="Overview" intro="This workspace reads the report folders the suncly CLI writes. It is empty until you load one." />
      <EmptyState
        title="No evaluations yet"
        body={
          <ol className="flex flex-col gap-3">
            <li>
              <span className="font-semibold text-ink">1. Run an evaluation</span> with the CLI against a sandbox agent. <Link href="/app/new" className="underline underline-offset-4">New evaluation</Link> builds the exact command for you.
            </li>
            <li>
              <span className="font-semibold text-ink">2. Import the report folder</span> it writes: <code className="code-inline">result.json</code> plus the <code className="code-inline">transcripts</code> folder. Nothing is uploaded.
            </li>
            <li>
              <span className="font-semibold text-ink">3. Or look around first</span> with the sample data set: three evaluations of a fictional agent, clearly marked as sample.
            </li>
          </ol>
        }
        actions={
          <>
            <Button onClick={loadSample}>Load sample data</Button>
            <ButtonLink href="/app/import" variant="secondary">
              Import a report folder
            </ButtonLink>
            <ButtonLink href="/app/new" variant="ghost" arrow>
              Set up an evaluation
            </ButtonLink>
          </>
        }
      />
    </>
  );
}
