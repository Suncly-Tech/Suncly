"use client";

import { useState } from "react";
import { Button } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field, Input, Select } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { KeyValue } from "@/components/ui/Stat";
import { ApiClient, ApiError } from "@/lib/api/client";
import { clearConnection, defaultBaseUrl, saveConnection, useConnection } from "@/lib/api/connection";
import type { Me } from "@/lib/api/types";

/**
 * Where the workspace connects to. The token is stored in this browser only and sent to the
 * configured base URL only. "Test" calls GET /v1/me and lists the organizations the token
 * belongs to.
 */
export function ConnectionCard() {
  const connection = useConnection();
  const [baseUrl, setBaseUrl] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [slug, setSlug] = useState("");
  const [creating, setCreating] = useState(false);

  const url = baseUrl ?? (connection.baseUrl || defaultBaseUrl());
  const tok = token ?? connection.token;

  async function test() {
    setTesting(true);
    setError(null);
    try {
      const client = new ApiClient({ baseUrl: url, token: tok });
      const answer = await client.me();
      setMe(answer);
      saveConnection({
        baseUrl: url.trim(),
        token: tok.trim(),
        organizationId: connection.organizationId && answer.organizations.some((o) => o.id === connection.organizationId) ? connection.organizationId : (answer.organizations[0]?.id ?? null),
      });
    } catch (e) {
      setMe(null);
      setError(e instanceof ApiError ? e : new ApiError(0, null, (e as Error).message));
    } finally {
      setTesting(false);
    }
  }

  async function create() {
    if (!slug.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const client = new ApiClient({ baseUrl: url, token: tok });
      const organization = await client.createOrganization(slug.trim(), slug.trim());
      saveConnection({ baseUrl: url.trim(), token: tok.trim(), organizationId: organization.id });
      setMe(await client.me());
      setSlug("");
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, null, (e as Error).message));
    } finally {
      setCreating(false);
    }
  }

  const organizations = me?.organizations ?? [];

  return (
    <Card as="section">
      <CardHeader
        id="connection"
        title="Suncly API connection"
        description="The live pages (Agents, Attestations, Usage) read from this API. Locally, start it with docker compose and mint a token with `suncly auth local-token`."
      />
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          void test();
        }}
      >
        <Field id="api-url" label="API base URL" help="For example http://localhost:8080 for the compose setup, or your hosted deployment.">
          <Input id="api-url" value={url} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.example.com" inputMode="url" autoComplete="off" />
        </Field>
        <Field id="api-token" label="Bearer token" help="An OpenID Connect token for the hosted API, or a local token in development. Stored in this browser only.">
          <Input id="api-token" type="password" value={tok} onChange={(e) => setToken(e.target.value)} autoComplete="off" />
        </Field>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" size="sm" disabled={testing || !url.trim() || !tok.trim()}>
            {testing ? "Testing…" : "Test and save"}
          </Button>
          {connection.baseUrl ? (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                clearConnection();
                setMe(null);
                setBaseUrl(null);
                setToken(null);
              }}
            >
              Disconnect
            </Button>
          ) : null}
        </div>
      </form>

      {error ? (
        <Notice tone="error" role="alert" className="mt-4" title="Connection failed">
          {error.message} {error.nextStep}
          {error.requestId ? ` Request id ${error.requestId}.` : ""}
        </Notice>
      ) : null}

      {me ? (
        <div className="mt-5 flex flex-col gap-4">
          <KeyValue
            items={[
              ["Signed in as", me.principal.email ?? me.principal.subject],
              ["Verified by", me.principal.verified_by === "local" ? "local token verifier (development only)" : `OpenID Connect (${me.principal.issuer})`],
              ["Organizations", String(organizations.length)],
            ]}
          />
          {organizations.length ? (
            <Field id="api-org" label="Organization in use" help="Every live page reads this organization; your role in it decides what you can do.">
              <Select id="api-org" value={connection.organizationId ?? organizations[0].id} onChange={(e) => saveConnection({ organizationId: e.target.value })}>
                {organizations.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name} ({o.role ?? "member"})
                  </option>
                ))}
              </Select>
            </Field>
          ) : (
            <Notice tone="info" title="No organization yet">
              Create one; you become its administrator.
            </Notice>
          )}
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void create();
            }}
          >
            <Field id="api-new-org" label="New organization slug" help="Lowercase letters, digits and dashes.">
              <Input id="api-new-org" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="acme" pattern="[a-z0-9][a-z0-9-]*" />
            </Field>
            <Button type="submit" variant="secondary" size="sm" disabled={creating || !slug.trim()}>
              {creating ? "Creating…" : "Create organization"}
            </Button>
          </form>
        </div>
      ) : null}
    </Card>
  );
}
