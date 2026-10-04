"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/Button";
import { Badge, StatusBadge, DecisionBadge } from "@/components/ui/Badge";
import { EvaluationView } from "@/components/evidence/EvaluationView";
import { ComparisonView } from "@/components/evidence/Comparison";
import { ReviewRecordCard } from "@/components/evidence/ReviewRecordCard";
import { SectionLabel } from "@/components/SectionHeader";
import { formatDateTime, shortId, totals } from "@/lib/evidence/derive";
import { sampleBundles } from "@/lib/sample";
import { demoPage } from "@/lib/content";
import { addBundle, markSampleLoaded, useWorkspaceState } from "@/lib/workspace/store";

/** The three sample attestations, the comparison, the reviewer's record, and the gaps. */
export function DemoExplorer() {
  const [index, setIndex] = useState(1);
  const bundle = sampleBundles[index];
  const story = demoPage.story[index];
  const { state, ready } = useWorkspaceState();
  const [loaded, setLoaded] = useState(false);
  const alreadyInWorkspace = ready && sampleBundles.every((b) => b.result.attestation.id in state.bundles);

  function loadIntoWorkspace() {
    for (const b of sampleBundles) addBundle(b, "sample", "Sample data set (frontend/lib/sample)");
    markSampleLoaded(true);
    setLoaded(true);
  }

  return (
    <div className="flex flex-col gap-12">
      <div>
        <SectionLabel as="h2" id="pick-evaluation">
          Three evaluations of one agent
        </SectionLabel>
        <ol className="mt-5 grid gap-3 md:grid-cols-3" aria-labelledby="pick-evaluation">
          {sampleBundles.map((b, i) => {
            const sums = totals(b.result);
            const selected = i === index;
            return (
              <li key={b.sample.label}>
                <button
                  type="button"
                  onClick={() => setIndex(i)}
                  aria-pressed={selected}
                  className={`flex h-full w-full flex-col gap-3 rounded-[16px] p-5 text-left transition-shadow ${
                    selected ? "bg-paper shadow-raised ring-2 ring-sun" : "bg-paper ring-1 ring-line hover:ring-line-strong"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-[12px] text-ink-soft">
                      {i + 1} · {shortId(b.result.attestation.id)} · {formatDateTime(b.result.attestation.started_at)}
                    </span>
                  </div>
                  <span className="text-heading-md text-ink">{demoPage.story[i].title.replace(/^Evaluation \d: /, "")}</span>
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge status={b.result.attestation.status} />
                    <DecisionBadge outcome={b.result.decisions[0]?.outcome ?? null} by={b.result.decisions[0] ? "policy" : undefined} />
                  </div>
                  <p className="font-mono text-[13px] text-ink-soft">
                    <span className="text-pass">{sums.pass} pass</span> · <span className="text-fail">{sums.fail} fail</span> ·{" "}
                    <span className="text-partial">{sums.inconclusive} inconclusive</span>
                    {sums.notExecuted ? <span className="text-fail"> · {sums.notExecuted} never ran</span> : null}
                  </p>
                </button>
              </li>
            );
          })}
        </ol>
        <p className="mt-5 max-w-[760px] text-body text-ink-soft">{story.body}</p>
      </div>

      <EvaluationView
        key={bundle.result.attestation.id}
        bundle={bundle}
        sample
        heading="h2"
        review={
          index === 1 ? (
            <Card>
              <CardHeader title={demoPage.reviewer.title} description={demoPage.reviewer.note} />
              <ReviewRecordCard
                decision={demoPage.reviewer.record.decision}
                reviewer={demoPage.reviewer.record.reviewer}
                rationale={demoPage.reviewer.record.rationale}
                attestationId={bundle.result.attestation.id}
                sample
              />
            </Card>
          ) : undefined
        }
      />

      <div className="flex flex-col gap-5">
        <div>
          <SectionLabel as="h2">What changed between evaluation 1 and 2</SectionLabel>
          <p className="mt-3 max-w-[760px] text-body text-ink-soft">
            The card hash is identical, so the same approved contract ran both times. The counts are comparable; the agent is not the same.
          </p>
        </div>
        <Card>
          <ComparisonView older={sampleBundles[0].result} newer={sampleBundles[1].result} />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title={demoPage.reviewer.title} description={demoPage.reviewer.note} />
          <ReviewRecordCard
            decision={demoPage.reviewer.record.decision}
            reviewer={demoPage.reviewer.record.reviewer}
            rationale={demoPage.reviewer.record.rationale}
            attestationId={sampleBundles[1].result.attestation.id}
            sample
          />
        </Card>
        <Card>
          <CardHeader title={demoPage.untested.title} />
          <ul className="flex flex-col gap-3">
            {demoPage.untested.items.map((item) => (
              <li key={item} className="cuts-bullet text-sun">
                <span className="text-small text-ink md:text-[15px]">{item}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="surface-card flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between md:p-8">
        <div>
          <h2 className="text-heading-md text-ink">Work with these in the review workspace</h2>
          <p className="mt-1 max-w-[560px] text-small text-ink-soft">
            The workspace is where your own report folders go. Load the sample to try the overview, the agent history, the comparison and the review note. Everything loaded from here carries a sample badge.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          {alreadyInWorkspace || loaded ? (
            <>
              <Badge tone="pass" dot className="self-center">
                Loaded
              </Badge>
              <Link href="/app" className="btn-base btn-primary">
                Open workspace
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </>
          ) : (
            <Button onClick={loadIntoWorkspace}>Load sample into workspace</Button>
          )}
        </div>
      </div>
    </div>
  );
}
