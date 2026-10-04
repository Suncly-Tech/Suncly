"use client";

import { useState } from "react";
import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/Button";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { KeyValue } from "@/components/ui/Stat";
import { Notice } from "@/components/ui/Notice";
import { verifyBundle, type VerificationResult } from "@/lib/evidence/verify";
import type { EvidenceBundle } from "@/lib/evidence/types";

/**
 * What the signature covers, and a verifier that runs the checks of `suncly verify` in the
 * browser. The CLI stays the reference; this is a convenience for reviewers.
 */
export function SignaturePanel({ bundle }: { bundle: EvidenceBundle }) {
  const { result } = bundle;
  const attestation = result.attestation;
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [running, setRunning] = useState(false);
  const transcriptsPresent = result.runs.every((r) => r.run.id in bundle.transcripts);

  async function run() {
    setRunning(true);
    try {
      setVerification(await verifyBundle(bundle));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <KeyValue
        items={[
          ["Signed", attestation.signature ? "Yes" : "No"],
          ["Signing key", <span key="k" className="font-mono text-[13px]">{attestation.signing_key_id ?? "–"}</span>],
          ["Signature", <span key="s" className="break-all font-mono text-[12px]">{attestation.signature ?? "–"}</span>],
          ["Public key", <span key="p" className="break-all font-mono text-[12px]">{result.signer_public_key ?? "–"}</span>],
          [
            "Payload covers",
            "attestation id, card_hash, contract id and version, per-test-case counts, the SHA-256 of every transcript file, and the decision outcome with its policy_version (schema §11)",
          ],
          ["Does not cover", "later human decisions, the report's prose, or anything about the agent's future behaviour"],
        ]}
      />

      <div className="flex flex-col gap-3">
        <p className="text-small text-ink-soft">Verify from the report folder with the CLI, the reference verifier:</p>
        <CodeBlock code={`suncly verify suncly-reports/${attestation.id}`} label="verify command" lines />
      </div>

      <div className="surface-sunken flex flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold text-ink">Verify in this browser</p>
            <p className="text-[13px] text-ink-soft">
              Runs the same checks on the loaded bundle: key fingerprint, Ed25519 signature over the RFC 8785 payload, card hash, transcript hashes, decision and counts.
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={run} disabled={running}>
            {running ? "Verifying…" : verification ? "Verify again" : "Run verification"}
          </Button>
        </div>
        {!transcriptsPresent ? (
          <Notice tone="warn">Some transcript files are not in this bundle; the transcript hash check will report them as missing.</Notice>
        ) : null}
        {verification ? <VerificationOutput verification={verification} /> : null}
      </div>
    </div>
  );
}

function VerificationOutput({ verification }: { verification: VerificationResult }) {
  const Icon = verification.ok ? ShieldCheck : verification.incomplete ? ShieldQuestion : ShieldAlert;
  const tone = verification.ok ? "text-pass" : verification.incomplete ? "text-partial" : "text-fail";
  return (
    <div role="status" className="flex flex-col gap-3">
      <p className={`flex items-center gap-2 font-semibold ${tone}`}>
        <Icon size={18} aria-hidden="true" />
        {verification.ok
          ? "Verification passed."
          : verification.incomplete && verification.checks.every((c) => c.ok !== false)
            ? "Every check that could run passed; one or more checks could not run in this browser."
            : "Verification FAILED."}
      </p>
      <ul className="flex flex-col divide-y divide-line rounded-[12px] bg-paper ring-1 ring-line">
        {verification.checks.map((check) => (
          <li key={check.name} className="flex flex-col gap-1 px-4 py-2.5 sm:flex-row sm:items-start sm:gap-3">
            <Badge tone={check.ok === true ? "pass" : check.ok === false ? "fail" : "inconclusive"} className="shrink-0">
              {check.ok === true ? "ok" : check.ok === false ? "FAIL" : "not run"}
            </Badge>
            <span className="text-[13px] font-semibold text-ink">{check.name}</span>
            <span className="break-all font-mono text-[12px] text-ink-soft">{check.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
