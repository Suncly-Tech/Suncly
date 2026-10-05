"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { Notice } from "@/components/ui/Notice";
import { EmptyState } from "@/components/ui/EmptyState";
import { ButtonLink } from "@/components/Button";
import { Badge } from "@/components/ui/Badge";
import { Loading } from "@/components/app/PageTitle";
import type { ApiError } from "@/lib/api/client";
import type { LoadState } from "@/lib/api/connection";

/** The four states every live page distinguishes: not connected, loading, error, empty. */

export function NotConnected() {
  return (
    <EmptyState
      title="Not connected to a Suncly API"
      body={
        <>
          The live pages read from a hosted (or locally running) Suncly API. Save its URL and a bearer token under Settings. The sample and imported evaluations on the other pages keep
          working offline.
        </>
      }
      actions={<ButtonLink href="/app/settings#connection">Open connection settings</ButtonLink>}
    />
  );
}

export function ApiErrorNotice({ error, what }: { error: ApiError; what: string }) {
  if (error.unauthenticated) {
    return (
      <Notice tone="error" role="alert" title="The API did not accept the token">
        {error.message} {error.nextStep} Update the token under <Link href="/app/settings#connection">Settings</Link>.
      </Notice>
    );
  }
  if (error.forbidden) {
    return (
      <Notice tone="warn" role="status" title="Your role does not allow this">
        {error.message} {error.nextStep}
      </Notice>
    );
  }
  if (error.status === 404) {
    return (
      <Notice tone="warn" role="status" title={`${what}: not found in this organization`}>
        {error.message} A record of another organization is reported as not found, never as forbidden.
      </Notice>
    );
  }
  return (
    <Notice tone="error" role="alert" title={`Could not ${what}`}>
      {error.message}
      {error.nextStep ? ` ${error.nextStep}` : ""}
      {error.requestId ? (
        <>
          {" "}
          Request id <code className="code-inline">{error.requestId}</code>.
        </>
      ) : null}
    </Notice>
  );
}

export function LiveBadge({ label = "Live" }: { label?: string }) {
  return (
    <Badge tone="info" dot title="Read from the connected Suncly API; nothing here is sample data">
      {label}
    </Badge>
  );
}

export function LoadView<T>({
  state,
  what,
  empty,
  children,
}: {
  state: LoadState<T>;
  what: string;
  /** Rendered when the loaded data is empty according to `isEmpty`. */
  empty?: { isEmpty: (data: T) => boolean; view: ReactNode };
  children: (data: T) => ReactNode;
}) {
  if (state.kind === "idle") return <NotConnected />;
  if (state.kind === "loading") return <Loading label={`Loading ${what}`} />;
  if (state.kind === "error") return <ApiErrorNotice error={state.error} what={`load ${what}`} />;
  if (empty && empty.isEmpty(state.data)) return <>{empty.view}</>;
  return <>{children(state.data)}</>;
}

export function minor(amount: number, currency: string | null | undefined): string {
  const code = currency ?? "";
  return `${(amount / 100).toFixed(2)} ${code}`.trim();
}
