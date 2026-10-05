"use client";

/**
 * The reviewer's connection to a hosted API: base URL, bearer token and the organization in
 * use. Kept in this browser's localStorage, separately from the evidence workspace, so the
 * token never travels with an exported bundle. The token is sent only to the configured
 * base URL.
 */

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { ApiClient, ApiError } from "./client";
import type { Me, Organization } from "./types";

export interface Connection {
  baseUrl: string;
  token: string;
  organizationId: string | null;
}

const KEY = "suncly.api.v1";
const EMPTY: Connection = { baseUrl: "", token: "", organizationId: null };
const DEFAULT_LOCAL_URL = "http://localhost:8080";

let state: Connection = EMPTY;
let hydrated = false;
const listeners = new Set<() => void>();

function read(): Connection {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<Connection>;
    return {
      baseUrl: parsed.baseUrl ?? "",
      token: parsed.token ?? "",
      organizationId: parsed.organizationId ?? null,
    };
  } catch {
    return EMPTY;
  }
}

function hydrate(): void {
  if (hydrated || typeof window === "undefined") return;
  state = read();
  hydrated = true;
}

function subscribe(listener: () => void): () => void {
  hydrate();
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function snapshot(): Connection {
  hydrate();
  return state;
}

export function useConnection(): Connection {
  return useSyncExternalStore(subscribe, snapshot, () => EMPTY);
}

export function saveConnection(next: Partial<Connection>): void {
  hydrate();
  state = { ...state, ...next };
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Storage may be unavailable (private window); the connection then lasts for this page.
  }
  for (const listener of listeners) listener();
}

export function clearConnection(): void {
  saveConnection(EMPTY);
}

export function defaultBaseUrl(): string {
  return DEFAULT_LOCAL_URL;
}

export function isConfigured(connection: Connection): boolean {
  return Boolean(connection.baseUrl.trim() && connection.token.trim());
}

export function clientFor(connection: Connection): ApiClient | null {
  return isConfigured(connection) ? new ApiClient({ baseUrl: connection.baseUrl, token: connection.token }) : null;
}

export type LoadState<T> =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: T }
  | { kind: "error"; error: ApiError };

/**
 * Load something from the API whenever the connection or the inputs change. `deps` are the
 * values the loader reads; the loader itself is called with a client that is never null.
 */
export function useApiLoad<T>(load: (client: ApiClient) => Promise<T>, deps: readonly unknown[]): [LoadState<T>, () => void] {
  const connection = useConnection();
  const [state, setState] = useState<LoadState<T>>({ kind: "idle" });
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((n) => n + 1), []);
  const configured = isConfigured(connection);
  const baseUrl = connection.baseUrl;
  const token = connection.token;

  useEffect(() => {
    if (!configured) {
      setState({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setState({ kind: "loading" });
    const client = new ApiClient({ baseUrl, token });
    load(client).then(
      (data) => {
        if (!cancelled) setState({ kind: "ready", data });
      },
      (error: unknown) => {
        if (cancelled) return;
        const apiError = error instanceof ApiError ? error : new ApiError(0, null, (error as Error).message);
        setState({ kind: "error", error: apiError });
      },
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configured, baseUrl, token, tick, ...deps]);

  return [state, refresh];
}

export function currentOrganization(me: Me | null, connection: Connection): Organization | null {
  if (!me) return null;
  return me.organizations.find((o) => o.id === connection.organizationId) ?? me.organizations[0] ?? null;
}
