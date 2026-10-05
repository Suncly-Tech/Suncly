"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Field, Input } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { KeyValue } from "@/components/ui/Stat";
import { AvailabilityBadge } from "@/components/ui/Badge";
import { PageTitle, Loading } from "./PageTitle";
import { ConnectionCard } from "./hosted/ConnectionCard";
import { sampleBundles } from "@/lib/sample";
import {
  addBundle,
  clearWorkspace,
  markSampleLoaded,
  removeSampleBundles,
  setReviewer,
  useWorkspaceState,
  workspaceSize,
} from "@/lib/workspace/store";

export function SettingsView() {
  const { state, ready } = useWorkspaceState();
  const [reviewer, setReviewerName] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [saved, setSaved] = useState(false);
  if (!ready) return <Loading />;

  const bundles = Object.values(state.bundles);
  const samples = bundles.filter((b) => b.source === "sample").length;
  const imported = bundles.length - samples;
  const reviews = Object.values(state.reviews).reduce((n, list) => n + list.length, 0);
  const size = workspaceSize();
  const current = reviewer ?? state.settings.reviewer;

  return (
    <>
      <PageTitle title="Settings" intro="The API connection for the hosted pages, workspace storage, sample data, your reviewer identity, and where accounts and billing stand." />
      <div className="mb-6">
        <ConnectionCard />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Workspace storage" description="Everything the workspace knows lives in this browser's local storage." />
          <KeyValue
            items={[
              ["Imported evaluations", String(imported)],
              ["Sample evaluations", String(samples)],
              ["Reviewer notes", String(reviews)],
              ["Approximate size", `${(size / 1024).toFixed(0)} KB`],
              ["Location", "localStorage of this browser profile, key suncly.workspace.v1"],
              ["Sent to a server", "never"],
            ]}
          />
          <div className="mt-5 flex flex-wrap gap-3">
            <Button variant="danger" size="sm" onClick={() => setConfirmClear(true)} disabled={bundles.length === 0 && reviews === 0}>
              Clear the workspace
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader title="Sample data" description="Three evaluations of the fictional Harbor Returns Agent, produced by the real code path. Every record carries a sample badge." />
          <div className="flex flex-wrap gap-3">
            {samples ? (
              <Button variant="secondary" size="sm" onClick={removeSampleBundles}>
                Remove sample data
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => {
                  for (const b of sampleBundles) addBundle(b, "sample", "Sample data set (frontend/lib/sample)");
                  markSampleLoaded(true);
                }}
              >
                Load sample data
              </Button>
            )}
            <Link href="/demo" className="btn-base btn-ghost btn-sm">
              About the sample
            </Link>
          </div>
        </Card>

        <Card>
          <CardHeader title="Reviewer identity" description="Pre-fills the reviewer field on offline review notes. Stored locally. Hosted decisions use the identity of the connected API token instead." />
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              setReviewer(current.trim());
              setSaved(true);
              setTimeout(() => setSaved(false), 1500);
            }}
          >
            <Field id="settings-reviewer" label="Default reviewer identifier" help="For example your work email, the same value you would pass to --approve-as.">
              <Input id="settings-reviewer" value={current} onChange={(e) => setReviewerName(e.target.value)} placeholder="reviewer@company.com" autoComplete="email" />
            </Field>
            <div className="flex items-center gap-3">
              <Button type="submit" size="sm">
                Save
              </Button>
              {saved ? (
                <span role="status" className="text-[13px] text-pass">
                  Saved.
                </span>
              ) : null}
            </div>
          </form>
        </Card>

        <Card>
          <CardHeader title="Account, usage and billing" description="Where these stand in the current version." />
          <ul className="flex flex-col gap-3 text-small">
            <li className="flex items-start justify-between gap-4">
              <span className="text-ink">
                <span className="font-semibold">Accounts and sign-in.</span> The hosted API verifies OpenID Connect tokens from your identity provider and keeps organizations with administrator, reviewer and viewer roles. Suncly runs no identity system of its own; local tokens exist for development only.
              </span>
              <AvailabilityBadge status="available" />
            </li>
            <li className="flex items-start justify-between gap-4">
              <span className="text-ink">
                <span className="font-semibold">Usage.</span> The hosted ledger records every Runner and judge call in whole minor units against a reservation held under your hard limit; the Usage page shows it. Offline, the CLI still counts attempts against a budget.
              </span>
              <AvailabilityBadge status="available" />
            </li>
            <li className="flex items-start justify-between gap-4">
              <span className="text-ink">
                <span className="font-semibold">Billing.</span> Subscriptions with an included allowance and explicit overage run through the billing provider in test mode: checkout, portal and verified webhooks work against test prices. No live product or price exists yet; access to a hosted deployment is arranged with the team.
              </span>
              <AvailabilityBadge status="limited" />
            </li>
          </ul>
          <Notice tone="info" className="mt-5">
            To request access or discuss a pilot, write to <a href="mailto:team@suncly.com" className="font-semibold">team@suncly.com</a> or use the <Link href="/access" className="font-semibold">access page</Link>.
          </Notice>
        </Card>
      </div>

      <Dialog
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Clear the whole workspace?"
        description="Removes every stored evaluation and reviewer note from this browser. Report folders on disk and the evidence store are not affected."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmClear(false)}>
              Keep everything
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                clearWorkspace();
                setConfirmClear(false);
              }}
            >
              Clear workspace
            </Button>
          </>
        }
      >
        <p className="text-small text-ink-soft">
          {bundles.length} evaluation{bundles.length === 1 ? "" : "s"} and {reviews} reviewer note{reviews === 1 ? "" : "s"} will be removed.
        </p>
      </Dialog>
    </>
  );
}
