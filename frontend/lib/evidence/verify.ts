/**
 * The checks of `suncly verify` (core/verify.py), run in the browser on an imported
 * bundle. Same names, same order, same meaning. A check whose result is `null` could
 * not be run here (for example Ed25519 is missing from this browser's WebCrypto); the
 * CLI remains the reference verifier.
 */

import { b64urlDecode, canonicalize, hex, sha256Hex, subtleAvailable, utf8 } from "./jcs";
import type { EvidenceBundle } from "./types";

export interface VerificationCheck {
  name: string;
  ok: boolean | null;
  detail: string;
}

export interface VerificationResult {
  checks: VerificationCheck[];
  /** True only when every check ran and passed. */
  ok: boolean;
  /** True when at least one check could not run in this browser. */
  incomplete: boolean;
}

const SIGNATURE_PREFIX = "ed25519:";
const KEY_ID_PREFIX = "ed25519-";

async function keyIdFor(publicKey: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", publicKey as BufferSource);
  return KEY_ID_PREFIX + hex(new Uint8Array(digest)).slice(0, 16);
}

async function verifyEd25519(
  publicKey: Uint8Array,
  payloadBytes: Uint8Array,
  signature: string,
): Promise<boolean | null> {
  if (!signature.startsWith(SIGNATURE_PREFIX)) return false;
  let raw: Uint8Array;
  try {
    raw = b64urlDecode(signature.slice(SIGNATURE_PREFIX.length));
  } catch {
    return false;
  }
  try {
    const key = await crypto.subtle.importKey(
      "raw",
      publicKey as BufferSource,
      { name: "Ed25519" },
      false,
      ["verify"],
    );
    return await crypto.subtle.verify({ name: "Ed25519" }, key, raw as BufferSource, payloadBytes as BufferSource);
  } catch {
    // The browser does not implement Ed25519 in WebCrypto; the CLI is the reference.
    return null;
  }
}

export async function verifyBundle(
  bundle: EvidenceBundle,
  publicKeyOverride?: Uint8Array,
): Promise<VerificationResult> {
  const checks: VerificationCheck[] = [];
  const { result, transcripts } = bundle;
  const attestation = result.attestation;
  const signature = attestation.signature;
  const signingKeyId = attestation.signing_key_id;
  const payload = result.signature_payload;

  if (!subtleAvailable()) {
    return {
      checks: [
        {
          name: "web crypto",
          ok: null,
          detail: "this browser offers no WebCrypto; run suncly verify on the report folder",
        },
      ],
      ok: false,
      incomplete: true,
    };
  }

  checks.push({
    name: "signature present",
    ok: Boolean(signature) && Boolean(signingKeyId),
    detail: signature ? `signing_key_id ${signingKeyId}` : "the attestation carries no signature",
  });

  let keyBytes: Uint8Array | null = publicKeyOverride ?? null;
  if (!keyBytes && typeof result.signer_public_key === "string") {
    try {
      keyBytes = b64urlDecode(result.signer_public_key);
    } catch {
      keyBytes = null;
    }
  }
  if (!keyBytes) {
    checks.push({ name: "public key", ok: false, detail: "no public key is available" });
  } else {
    const fingerprint = await keyIdFor(keyBytes);
    checks.push({
      name: "public key matches signing_key_id",
      ok: fingerprint === signingKeyId,
      detail: `the key's fingerprint is ${fingerprint}, the attestation names ${signingKeyId}`,
    });
  }

  if (!payload || typeof payload !== "object") {
    checks.push({ name: "signature payload present", ok: false, detail: "no signature_payload" });
    return finish(checks);
  }

  if (keyBytes && typeof signature === "string") {
    const valid = await verifyEd25519(keyBytes, utf8(canonicalize(payload)), signature);
    checks.push({
      name: "signature valid",
      ok: valid,
      detail:
        valid === null
          ? "this browser cannot verify Ed25519 signatures; run suncly verify on the report folder"
          : valid
            ? "the signature matches the payload"
            : "the signature does not match the payload: the payload, the signature or the key was altered",
    });
  }

  // card_hash: SHA-256 of the RFC 8785 form of the card without `signatures`.
  let recomputed: string | null = null;
  try {
    const card = JSON.parse(result.card_version.raw_json) as Record<string, unknown>;
    const withoutSignatures = Object.fromEntries(
      Object.entries(card).filter(([key]) => key !== "signatures"),
    );
    recomputed = await sha256Hex(utf8(canonicalize(withoutSignatures)));
  } catch {
    recomputed = null;
  }
  const recorded = result.card_version.card_hash;
  checks.push({
    name: "card_hash",
    ok: recomputed !== null && recomputed === payload.card_hash && payload.card_hash === recorded,
    detail: `recomputed ${recomputed ?? "-"}; payload ${payload.card_hash}; record ${recorded}`,
  });

  checks.push({
    name: "attestation and contract ids",
    ok:
      payload.attestation_id === attestation.id &&
      payload.contract?.id === result.contract.id &&
      payload.contract?.version === result.contract.version,
    detail: `payload attestation ${payload.attestation_id}, contract ${payload.contract?.id} v${payload.contract?.version}`,
  });

  const payloadHashes = payload.transcript_hashes ?? {};
  const problems: string[] = [];
  const runIds = result.runs.map((entry) => entry.run.id);
  for (const entry of result.runs) {
    const runId = entry.run.id;
    const expected = payloadHashes[runId];
    const text = transcripts[runId];
    if (text === undefined) {
      problems.push(`run ${runId}: transcript file missing`);
      continue;
    }
    const actual = await sha256Hex(utf8(text));
    if (actual !== expected) {
      problems.push(`run ${runId}: transcript hash ${actual} differs from signed ${expected}`);
    }
    if (entry.document_hash !== actual) {
      problems.push(`run ${runId}: result document records ${entry.document_hash}`);
    }
  }
  const missingInResult = Object.keys(payloadHashes)
    .filter((id) => !runIds.includes(id))
    .sort();
  if (missingInResult.length) {
    problems.push(`signed runs absent from the result: ${missingInResult.join(", ")}`);
  }
  checks.push({
    name: "transcript hashes",
    ok: problems.length === 0,
    detail: problems.length
      ? problems.join("; ")
      : `${result.runs.length} transcript(s) match the signed hashes`,
  });

  const first = result.decisions[0];
  const recordedDecision = first
    ? { outcome: first.outcome, policy_version: first.policy_version }
    : null;
  const signedDecision = payload.decision ?? null;
  const decisionMatches =
    (signedDecision === null && recordedDecision === null) ||
    (signedDecision !== null &&
      recordedDecision !== null &&
      signedDecision.outcome === recordedDecision.outcome &&
      signedDecision.policy_version === recordedDecision.policy_version);
  checks.push({
    name: "decision",
    ok: decisionMatches,
    detail: `signed ${JSON.stringify(signedDecision)}; recorded ${JSON.stringify(recordedDecision)}`,
  });

  const counts = new Map<string, number>();
  for (const entry of result.runs) {
    const key = `${entry.run.test_case_id}|${entry.run.verdict}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const mismatched: string[] = [];
  for (const entry of payload.results ?? []) {
    for (const verdict of ["pass", "fail", "inconclusive"] as const) {
      const seen = counts.get(`${entry.test_case_id}|${verdict}`) ?? 0;
      if (entry[verdict] !== seen) {
        mismatched.push(
          `test case ${entry.test_case_id}: signed ${verdict}=${entry[verdict]}, runs show ${seen}`,
        );
      }
    }
  }
  checks.push({
    name: "aggregated results",
    ok: mismatched.length === 0,
    detail: mismatched.length ? mismatched.join("; ") : "the signed counts match the recorded runs",
  });

  return finish(checks);
}

function finish(checks: VerificationCheck[]): VerificationResult {
  const incomplete = checks.some((check) => check.ok === null);
  const ok = checks.every((check) => check.ok === true);
  return { checks, ok, incomplete };
}
