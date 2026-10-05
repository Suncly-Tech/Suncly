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
      <PageTitle title="Settings" intro="Workspace storage, sample data, your reviewer identity, and where accounts and billing stand." />
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
          <CardHeader title="Reviewer identity" description="Pre-fills the reviewer field on review notes. Stored locally; there is no account system in this version." />
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
                <span className="font-semibold">Accounts and sign-in.</span> None. Reviewer identity is an identifier you type; identity systems are out of scope for Suncly, and an external source will supply identities later (OQ-P3).
              </span>
              <AvailabilityBadge status="planned" />
            </li>
            <li className="flex items-start justify-between gap-4">
              <span className="text-ink">
                <span className="font-semibold">Usage.</span> Every attestation records its cost in attempts against its budget; that is the unit the code counts today. There is no aggregate usage view across a team yet.
              </span>
              <AvailabilityBadge status="available" />
            </li>
            <li className="flex items-start justify-between gap-4">
              <span className="text-ink">
                <span className="font-semibold">Billing.</span> A payment layer is planned. Nothing here collects payment details, and no price is published. Access is arranged with the team.
              </span>
              <AvailabilityBadge status="planned" />
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
