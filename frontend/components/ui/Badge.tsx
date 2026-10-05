import type { ReactNode } from "react";
import type {
  AttestationStatus,
  DecisionOutcome,
  RiskLevel,
  RunVerdict,
} from "@/lib/evidence/types";
import type { Availability } from "@/lib/capabilities";
import { AVAILABILITY_LABEL } from "@/lib/capabilities";
import { STATUS_LABEL } from "@/lib/evidence/derive";

export type Tone = "pass" | "fail" | "inconclusive" | "info" | "neutral" | "ink" | "sun";

const toneClass: Record<Tone, string> = {
  pass: "bg-pass-soft text-pass",
  fail: "bg-fail-soft text-fail",
  inconclusive: "bg-partial-soft text-partial",
  info: "bg-info-soft text-ink-soft",
  neutral: "bg-cream-deep text-ink-soft",
  ink: "bg-ink text-paper",
  sun: "bg-sun text-ink",
};

export function Badge({
  tone = "neutral",
  children,
  dot = false,
  className = "",
  title,
}: {
  tone?: Tone;
  children: ReactNode;
  dot?: boolean;
  className?: string;
  title?: string;
}) {
  return (
    <span className={`badge ${toneClass[tone]} ${className}`} title={title}>
      {dot ? <span className="badge-dot" aria-hidden="true" /> : null}
      {children}
    </span>
  );
}

export function VerdictBadge({ verdict, count }: { verdict: RunVerdict; count?: number }) {
  const label = verdict === "pass" ? "Pass" : verdict === "fail" ? "Fail" : "Inconclusive";
  return (
    <Badge tone={verdict} dot>
      {count !== undefined ? `${count} ${label.toLowerCase()}` : label}
    </Badge>
  );
}

const statusTone: Record<AttestationStatus, Tone> = {
  queued: "neutral",
  running: "info",
  completed: "pass",
  failed: "fail",
  cancelled: "neutral",
  invalidated: "fail",
};

/** Evaluation status: what happened to the run itself. Never implies approval. */
export function StatusBadge({ status }: { status: AttestationStatus }) {
  return (
    <Badge tone={statusTone[status]} dot title="Evaluation status">
      {STATUS_LABEL[status]}
    </Badge>
  );
}

const outcomeTone: Record<DecisionOutcome, Tone> = {
  approve: "pass",
  flag: "inconclusive",
  block: "fail",
};

/** Approval status: the recorded decision. `by` distinguishes policy from a human. */
export function DecisionBadge({
  outcome,
  by,
}: {
  outcome: DecisionOutcome | null;
  by?: "policy" | "human" | "local";
}) {
  if (outcome === null) {
    return (
      <Badge tone="neutral" title="No decision was recorded">
        No decision
      </Badge>
    );
  }
  const label = outcome === "flag" ? "Flag: human review" : outcome === "approve" ? "Approve" : "Block";
  const suffix = by === "policy" ? " · policy" : by === "human" ? " · reviewer" : by === "local" ? " · local note" : "";
  return (
    <Badge tone={outcomeTone[outcome]} dot title="Approval status">
      {label}
      {suffix}
    </Badge>
  );
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const tone: Tone = level === "high" ? "fail" : level === "medium" ? "inconclusive" : "pass";
  return (
    <Badge tone={tone} title="agent.risk_level, recorded on first sight; does not change the outcome yet">
      Risk {level}
    </Badge>
  );
}

export function AvailabilityBadge({ status }: { status: Availability }) {
  const tone: Tone = status === "available" ? "pass" : status === "pilot" ? "inconclusive" : "neutral";
  return (
    <Badge tone={tone} dot>
      {AVAILABILITY_LABEL[status]}
    </Badge>
  );
}

export function SampleBadge({ className = "" }: { className?: string }) {
  return (
    <Badge tone="sun" className={className} title="Synthetic sample data, not a customer evaluation">
      Sample data
    </Badge>
  );
}
