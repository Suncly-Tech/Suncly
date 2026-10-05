"use client";

import { useState } from "react";
import { Button } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { Badge } from "@/components/ui/Badge";
import { KeyValue } from "@/components/ui/Stat";
import { Table } from "@/components/ui/Table";
import { PageTitle } from "@/components/app/PageTitle";
import { formatDateTime, shortId } from "@/lib/evidence/derive";
import { ApiError } from "@/lib/api/client";
import { clientFor, currentOrganization, useApiLoad, useConnection } from "@/lib/api/connection";
import type { Me, Plans, Subscription, Usage } from "@/lib/api/types";
import { ApiErrorNotice, LiveBadge, LoadView, minor } from "./States";

interface BillingData {
  me: Me;
  organizationId: string;
  usage: Usage;
  subscription: Subscription;
  plans: Plans;
}

/** Entitlement, the period's ledger, reservations, the hard limit, and checkout in test mode. */
export function HostedBillingView() {
  const connection = useConnection();
  const [state, refresh] = useApiLoad<BillingData>(
    async (client) => {
      const me = await client.me();
      const organization = currentOrganization(me, connection);
      if (!organization) throw new ApiError(404, null, "No organization is selected.");
      const [usage, subscription, plans] = await Promise.all([client.usage(organization.id), client.subscription(organization.id), client.plans()]);
      return { me, organizationId: organization.id, usage, subscription, plans };
    },
    [connection.organizationId],
  );
  const [limit, setLimit] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  async function act(label: string, work: (client: NonNullable<ReturnType<typeof clientFor>>) => Promise<void>) {
    const client = clientFor(connection);
    if (!client) return;
    setBusy(label);
    setError(null);
    try {
      await work(client);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, null, (e as Error).message));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageTitle title="Usage and billing" intro="An append-only ledger in whole minor units, reservations held under a hard limit, the plan's included allowance, and overage reported to the billing provider in test mode." />
      <LoadView state={state} what="usage">
        {({ me, organizationId, usage, subscription, plans }) => {
          const organization = currentOrganization(me, connection);
          const admin = organization?.role === "administrator";
          const entitlement = usage.entitlement;
          const currency = entitlement.currency ?? "EUR";
          const held = usage.reservations.filter((r) => r.state === "held");
          return (
            <div className="flex flex-col gap-6">
              <div className="flex flex-wrap items-center gap-2">
                <LiveBadge label={`Live: ${organization?.name ?? ""}`} />
                <Badge tone={entitlement.can_start_attestations ? "pass" : "fail"}>{entitlement.can_start_attestations ? "can start attestations" : "cannot start attestations"}</Badge>
                <span className="text-small text-ink-soft">{entitlement.reason}</span>
              </div>
              {error ? <ApiErrorNotice error={error} what="update billing" /> : null}
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader title="Subscription" description={`Catalog ${plans.catalog_version}, price table ${plans.price_table_version}. ${plans.note}`} />
                  <KeyValue
                    items={[
                      ["Status", entitlement.subscription_status],
                      ["Plan", entitlement.plan_id ?? "none"],
                      ["Included allowance", String(plans.plans.find((p) => p.id === entitlement.plan_id)?.included_allowance_minor ?? "–") + " minor units"],
                    ]}
                  />
                  {admin ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {plans.plans.map((plan) => (
                        <Button
                          key={plan.id}
                          size="sm"
                          variant="secondary"
                          disabled={busy !== null}
                          onClick={() =>
                            act(plan.id, async (c) => {
                              const session = await c.checkout(organizationId, plan.id);
                              window.open(session.url, "_blank", "noopener");
                            })
                          }
                        >
                          Checkout: {plan.name}
                        </Button>
                      ))}
                      {subscription.subscription ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy !== null}
                          onClick={() =>
                            act("portal", async (c) => {
                              const session = await c.portal(organizationId);
                              window.open(session.url, "_blank", "noopener");
                            })
                          }
                        >
                          Billing portal
                        </Button>
                      ) : null}
                    </div>
                  ) : (
                    <Notice tone="info" className="mt-4">
                      An administrator manages the subscription and the spending limit.
                    </Notice>
                  )}
                </Card>
                <Card>
                  <CardHeader title="Hard spending limit" description="Reservations that would exceed it are refused before a job is queued." />
                  {admin ? (
                    <form
                      className="flex flex-wrap items-end gap-3"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const value = Number(limit);
                        if (!Number.isInteger(value) || value < 0) return;
                        void act("limit", async (c) => void (await c.setSpendingLimit(organizationId, value)));
                      }}
                    >
                      <Field id="limit" label={`Period limit (minor units of ${currency})`} help="Whole units; 10000 is 100.00.">
                        <Input id="limit" type="number" min={0} step={1} value={limit} onChange={(e) => setLimit(e.target.value)} inputMode="numeric" />
                      </Field>
                      <Button type="submit" size="sm" disabled={busy !== null || limit === ""}>
                        Set limit
                      </Button>
                    </form>
                  ) : (
                    <p className="text-small text-ink-soft">Only an administrator changes it.</p>
                  )}
                  <KeyValue className="mt-4" items={[["Held reservations", `${held.length} (${minor(held.reduce((n, r) => n + r.amount_minor, 0), currency)})`]]} />
                </Card>
              </div>
              <Card padded={false}>
                <div className="p-5 pb-0 md:p-6 md:pb-0">
                  <CardHeader title="Ledger" description="Every line is append-only; a correction is a new line. Unknown outcomes carry no billable amount and keep their reservation held." />
                </div>
                {usage.events.length ? (
                  <Table caption="Usage ledger lines">
                    <thead>
                      <tr>
                        <th>Recorded</th>
                        <th>Attestation</th>
                        <th>Operation</th>
                        <th>Outcome</th>
                        <th>Billable</th>
                        <th>Allowance</th>
                        <th>Settlement</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...usage.events].reverse().map((event) => (
                        <tr key={event.id}>
                          <td className="whitespace-nowrap">{formatDateTime(event.recorded_at)}</td>
                          <td className="font-mono text-[12px]">{event.attestation_id ? shortId(event.attestation_id) : "–"}</td>
                          <td>{event.operation}</td>
                          <td>{event.outcome}</td>
                          <td className="tabular-nums">{minor(event.billable_minor, currency)}</td>
                          <td className="tabular-nums">{minor(event.allowance_minor, currency)}</td>
                          <td>{event.settlement}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                ) : (
                  <p className="px-5 pb-5 text-small text-ink-soft md:px-6 md:pb-6">No usage recorded in this period.</p>
                )}
              </Card>
            </div>
          );
        }}
      </LoadView>
    </>
  );
}
