"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Field, Select } from "@/components/ui/Field";
import { ButtonLink } from "@/components/Button";
import { ComparisonView } from "@/components/evidence/Comparison";
import { PageTitle, Loading } from "./PageTitle";
import { formatDateTime, shortId } from "@/lib/evidence/derive";
import { bundlesByAgent, useWorkspaceState, type StoredBundle } from "@/lib/workspace/store";

/** The last two completed attestations when there are two; otherwise the last two of any status. */
function defaultPair(list: StoredBundle[]): [string, string] {
  const completed = list.filter((b) => b.result.attestation.status === "completed");
  const pool = completed.length >= 2 ? completed : list;
  return [pool[Math.max(pool.length - 2, 0)]?.result.attestation.id ?? "", pool[pool.length - 1]?.result.attestation.id ?? ""];
}

export function ComparePage() {
  const params = useSearchParams();
  const { state, ready } = useWorkspaceState();
  const all = Object.values(state.bundles);
  const groups = bundlesByAgent(all);
  const initialA = params.get("a");
  const initialB = params.get("b");
  const initialAgent = initialA ? state.bundles[initialA]?.result.agent.id : undefined;
  const [agentId, setAgentId] = useState<string>(initialAgent ?? [...groups.keys()][0] ?? "");
  const list = groups.get(agentId) ?? [];
  const defaults = defaultPair(list);
  const [a, setA] = useState<string>(initialA ?? defaults[0]);
  const [b, setB] = useState<string>(initialB ?? defaults[1]);

  if (!ready) return <Loading />;
  if (all.length < 2) {
    return (
      <>
        <PageTitle title="Compare evaluations" intro="Put two evaluations of the same agent side by side." />
        <EmptyState
          title="Two evaluations are needed"
          body="Load at least two report folders of the same agent. The comparison matches test cases by content, so it survives a new contract version."
          actions={<ButtonLink href="/app/import">Import a report folder</ButtonLink>}
        />
      </>
    );
  }

  const older = state.bundles[a];
  const newer = state.bundles[b];
  const ordered = older && newer && older.result.attestation.started_at > newer.result.attestation.started_at ? [newer, older] : [older, newer];

  return (
    <>
      <PageTitle
        title="Compare evaluations"
        intro="Two attestations of one agent, test case by test case. Regressions, improvements and changed test conditions are told apart. An unchanged Agent Card is never treated as proof of an unchanged agent."
      />
      <Card className="mb-6">
        <CardHeader title="Pick two evaluations" as="h2" />
        <div className="grid gap-4 md:grid-cols-3">
          <Field id="cmp-agent" label="Agent">
            <Select
              id="cmp-agent"
              value={agentId}
              onChange={(e) => {
                const next = e.target.value;
                setAgentId(next);
                const [nextA, nextB] = defaultPair(groups.get(next) ?? []);
                setA(nextA);
                setB(nextB);
              }}
            >
              {[...groups.entries()].map(([id, l]) => (
                <option key={id} value={id}>
                  {l[0].result.agent.name} ({l.length})
                </option>
              ))}
            </Select>
          </Field>
          <Field id="cmp-a" label="Earlier">
            <Select id="cmp-a" value={a} onChange={(e) => setA(e.target.value)}>
              {list.map((x) => (
                <option key={x.result.attestation.id} value={x.result.attestation.id}>
                  {shortId(x.result.attestation.id)} · {formatDateTime(x.result.attestation.started_at)} · {x.result.attestation.status}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="cmp-b" label="Later">
            <Select id="cmp-b" value={b} onChange={(e) => setB(e.target.value)}>
              {list.map((x) => (
                <option key={x.result.attestation.id} value={x.result.attestation.id}>
                  {shortId(x.result.attestation.id)} · {formatDateTime(x.result.attestation.started_at)} · {x.result.attestation.status}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Card>
      {ordered[0] && ordered[1] && ordered[0] !== ordered[1] ? (
        <Card>
          <ComparisonView older={ordered[0].result} newer={ordered[1].result} />
        </Card>
      ) : (
        <EmptyState title="Pick two different evaluations" body="Choose an earlier and a later attestation of the same agent." />
      )}
    </>
  );
}
