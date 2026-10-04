"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeftRight, Download, Trash2 } from "lucide-react";
import { Button, ButtonLink } from "@/components/Button";
import { Dialog } from "@/components/ui/Dialog";
import { EmptyState } from "@/components/ui/EmptyState";
import { EvaluationView, type EvaluationTab } from "@/components/evidence/EvaluationView";
import { ReviewPanel } from "./ReviewPanel";
import { Loading } from "./PageTitle";
import { downloadText } from "@/lib/download";
import { bundlesByAgent, removeBundle, useWorkspaceState } from "@/lib/workspace/store";

const TABS: EvaluationTab[] = ["summary", "tests", "coverage", "card", "execution", "signature", "review"];

export function EvaluationPage() {
  const params = useSearchParams();
  const router = useRouter();
  const id = params.get("id");
  const tabParam = params.get("tab");
  const { state, ready } = useWorkspaceState();
  const [confirmRemove, setConfirmRemove] = useState(false);

  if (!ready) return <Loading />;
  const bundle = id ? state.bundles[id] : undefined;
  if (!bundle) {
    return (
      <EmptyState
        title="Evaluation not found"
        body="This attestation is not in the workspace. It may have been removed, or the link may come from another browser: the workspace stores bundles locally."
        actions={
          <>
            <ButtonLink href="/app">Back to the overview</ButtonLink>
            <ButtonLink href="/app/import" variant="secondary">
              Import a report folder
            </ButtonLink>
          </>
        }
      />
    );
  }

  const reviews = state.reviews[bundle.result.attestation.id] ?? [];
  const siblings = (bundlesByAgent(Object.values(state.bundles)).get(bundle.result.agent.id) ?? []).filter(
    (b) => b.result.attestation.id !== bundle.result.attestation.id,
  );
  const previous = siblings.filter((b) => b.result.attestation.started_at < bundle.result.attestation.started_at).pop();
  const initialTab = TABS.includes(tabParam as EvaluationTab) ? (tabParam as EvaluationTab) : "summary";

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-4 text-[13px] text-ink-soft">
        <ol className="flex flex-wrap items-center gap-1.5">
          <li>
            <Link href="/app" className="hover:text-ink">Overview</Link>
          </li>
          <li aria-hidden="true">/</li>
          <li>
            <Link href={`/app/agent?id=${bundle.result.agent.id}`} className="hover:text-ink">
              {bundle.result.agent.name}
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li aria-current="page" className="font-mono text-ink">
            {bundle.result.attestation.id.slice(0, 8)}
          </li>
        </ol>
      </nav>

      <EvaluationView
        key={bundle.result.attestation.id + initialTab}
        bundle={bundle}
        sample={bundle.source === "sample"}
        initialTab={initialTab}
        hasLocalReview={reviews.length > 0}
        review={<ReviewPanel bundle={bundle} reviews={reviews} defaultReviewer={state.settings.reviewer} sample={bundle.source === "sample"} />}
        actions={
          <>
            {previous ? (
              <ButtonLink href={`/app/compare?a=${previous.result.attestation.id}&b=${bundle.result.attestation.id}`} variant="secondary" size="sm">
                <ArrowLeftRight size={14} aria-hidden="true" />
                Compare with previous
              </ButtonLink>
            ) : null}
            <Button
              variant="secondary"
              size="sm"
              onClick={() => downloadText(`result-${bundle.result.attestation.id.slice(0, 8)}.json`, JSON.stringify(bundle.result, null, 2))}
            >
              <Download size={14} aria-hidden="true" />
              result.json
            </Button>
            <Button variant="danger" size="sm" onClick={() => setConfirmRemove(true)}>
              <Trash2 size={14} aria-hidden="true" />
              Remove
            </Button>
          </>
        }
      />

      <Dialog
        open={confirmRemove}
        onClose={() => setConfirmRemove(false)}
        title="Remove this evaluation from the workspace?"
        description="This removes the stored copy and its reviewer notes from this browser. The report folder on disk and the evidence store are not affected."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmRemove(false)}>
              Keep it
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                removeBundle(bundle.result.attestation.id);
                setConfirmRemove(false);
                router.push("/app");
              }}
            >
              Remove from workspace
            </Button>
          </>
        }
      >
        <p className="text-small text-ink-soft">
          Attestation <span className="font-mono">{bundle.result.attestation.id}</span> of {bundle.result.agent.name}
          {reviews.length ? `, with ${reviews.length} reviewer note${reviews.length === 1 ? "" : "s"}` : ""}.
        </p>
      </Dialog>
    </>
  );
}
