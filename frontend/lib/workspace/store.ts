"use client";

/**
 * The review workspace: evidence bundles and reviewer notes kept in this browser.
 *
 * Suncly's evidence lives where the CLI wrote it (the report folder, the file store or
 * Postgres). This workspace is a reading room for those bundles. It stores nothing on a
 * server, and nothing it stores changes the signed evidence. Reviewer notes recorded here
 * are local: the backend has no interface yet for recording a human decision (OQ-P2), so a
 * note is exported and routed by the reviewer, never written into the attestation.
 */

import { useSyncExternalStore } from "react";
import { isResultDocument } from "@/lib/evidence/derive";
import type { EvidenceBundle, ResultDocument } from "@/lib/evidence/types";

export type BundleSource = "sample" | "import";

export interface StoredBundle extends EvidenceBundle {
  source: BundleSource;
  importedAt: string;
  /** How the bundle arrived, for the audit line in the UI. */
  origin: string;
}

export type ReviewDecision = "approve" | "block" | "needs_more_evidence";

export interface ReviewRecord {
  id: string;
  attestationId: string;
  decision: ReviewDecision;
  reviewer: string;
  rationale: string;
  recordedAt: string;
  /** Copied from the attestation so the note can be matched to the signed evidence later. */
  signature: string | null;
  signingKeyId: string | null;
  cardHash: string;
}

export interface WorkspaceSettings {
  /** Default reviewer identifier for new review notes. Local to this browser. */
  reviewer: string;
}

export interface WorkspaceState {
  bundles: Record<string, StoredBundle>;
  reviews: Record<string, ReviewRecord[]>;
  sampleLoaded: boolean;
  settings: WorkspaceSettings;
}

const KEY = "suncly.workspace.v1";
const EMPTY: WorkspaceState = { bundles: {}, reviews: {}, sampleLoaded: false, settings: { reviewer: "" } };

interface Snapshot {
  state: WorkspaceState;
  ready: boolean;
}

let state: WorkspaceState = EMPTY;
let hydrated = false;
let snapshotCache: Snapshot = { state: EMPTY, ready: false };
const SERVER_SNAPSHOT: Snapshot = { state: EMPTY, ready: false };
const listeners = new Set<() => void>();

function read(): WorkspaceState {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return EMPTY;
    const parsed = JSON.parse(raw) as Partial<WorkspaceState>;
    return {
      bundles: parsed.bundles ?? {},
      reviews: parsed.reviews ?? {},
      sampleLoaded: Boolean(parsed.sampleLoaded),
      settings: { reviewer: parsed.settings?.reviewer ?? "" },
    };
  } catch {
    return EMPTY;
  }
}

function setState(next: WorkspaceState): void {
  state = next;
  snapshotCache = { state: next, ready: true };
}

export class StorageFullError extends Error {
  constructor() {
    super("This browser's storage is full. Remove an evaluation from the workspace and try again.");
    this.name = "StorageFullError";
  }
}

function write(next: WorkspaceState): void {
  const previous = state;
  setState(next);
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch (error) {
    setState(previous);
    if (error instanceof DOMException && (error.name === "QuotaExceededError" || error.code === 22)) {
      throw new StorageFullError();
    }
    throw error;
  }
  for (const listener of listeners) listener();
}

function hydrate(): void {
  if (hydrated || typeof window === "undefined") return;
  setState(read());
  hydrated = true;
}

function subscribe(listener: () => void): () => void {
  hydrate();
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === KEY) {
      setState(read());
      listener();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

function snapshot(): Snapshot {
  hydrate();
  return snapshotCache;
}

export function useWorkspaceState(): Snapshot {
  return useSyncExternalStore(subscribe, snapshot, () => SERVER_SNAPSHOT);
}

export function addBundle(bundle: EvidenceBundle, source: BundleSource, origin: string): StoredBundle {
  hydrate();
  const stored: StoredBundle = { ...bundle, source, importedAt: new Date().toISOString(), origin };
  write({
    ...state,
    bundles: { ...state.bundles, [bundle.result.attestation.id]: stored },
  });
  return stored;
}

export function removeBundle(attestationId: string): void {
  hydrate();
  const bundles = { ...state.bundles };
  delete bundles[attestationId];
  const reviews = { ...state.reviews };
  delete reviews[attestationId];
  write({ ...state, bundles, reviews });
}

export function addReview(record: Omit<ReviewRecord, "id" | "recordedAt">): ReviewRecord {
  hydrate();
  const full: ReviewRecord = {
    ...record,
    id: crypto.randomUUID(),
    recordedAt: new Date().toISOString(),
  };
  const existing = state.reviews[record.attestationId] ?? [];
  write({
    ...state,
    reviews: { ...state.reviews, [record.attestationId]: [...existing, full] },
  });
  return full;
}

export function setReviewer(reviewer: string): void {
  hydrate();
  write({ ...state, settings: { ...state.settings, reviewer } });
}

export function markSampleLoaded(loaded: boolean): void {
  hydrate();
  write({ ...state, sampleLoaded: loaded });
}

export function clearWorkspace(): void {
  hydrate();
  write(EMPTY);
}

export function removeSampleBundles(): void {
  hydrate();
  const bundles = Object.fromEntries(
    Object.entries(state.bundles).filter(([, bundle]) => bundle.source !== "sample"),
  );
  const reviews = Object.fromEntries(
    Object.entries(state.reviews).filter(([id]) => id in bundles),
  );
  write({ ...state, bundles, reviews, sampleLoaded: false });
}

/** Approximate size of the stored workspace in bytes. */
export function workspaceSize(): number {
  try {
    return new Blob([window.localStorage.getItem(KEY) ?? ""]).size;
  } catch {
    return 0;
  }
}

/** Parse the text of a result.json. Returns the document or a message a person can act on. */
export function parseResultText(text: string): { result: ResultDocument } | { error: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return { error: "This file is not valid JSON. Suncly's result.json is a JSON object." };
  }
  if (!isResultDocument(parsed)) {
    return {
      error:
        "This JSON is not a Suncly result document. Expected format \"suncly-result/1\" with attestation, runs and results, as suncly attest writes to <report folder>/result.json.",
    };
  }
  return { result: parsed };
}

export function bundlesByAgent(bundles: StoredBundle[]): Map<string, StoredBundle[]> {
  const groups = new Map<string, StoredBundle[]>();
  for (const bundle of bundles) {
    const key = bundle.result.agent.id;
    const list = groups.get(key) ?? [];
    list.push(bundle);
    groups.set(key, list);
  }
  for (const list of groups.values()) {
    list.sort((a, b) => a.result.attestation.started_at.localeCompare(b.result.attestation.started_at));
  }
  return groups;
}

export function sortedByStart(bundles: StoredBundle[], direction: "asc" | "desc" = "desc"): StoredBundle[] {
  return [...bundles].sort((a, b) => {
    const cmp = a.result.attestation.started_at.localeCompare(b.result.attestation.started_at);
    return direction === "asc" ? cmp : -cmp;
  });
}
