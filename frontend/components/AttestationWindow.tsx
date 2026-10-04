"use client";

import { Check, ShieldCheck, Flag, UserCheck, AlertCircle } from "lucide-react";
import { attestation } from "@/lib/content";
import { Cuts } from "./Cuts";

const outcomeStyle = {
  approve: { cls: "bg-[#e6f4ec] text-pass", Icon: Check },
  flag: { cls: "bg-[#fbf1dc] text-partial", Icon: Flag },
  block: { cls: "bg-[#fdebe7] text-fail", Icon: AlertCircle },
} as const;

function Outcome({ outcome }: { outcome: keyof typeof outcomeStyle }) {
  const { cls, Icon } = outcomeStyle[outcome];
  return (
    <span className={`inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 text-[13px] font-semibold ${cls}`}>
      <Icon size={14} strokeWidth={2.75} aria-hidden="true" />
      {outcome}
    </span>
  );
}

/** The hero window: one completed attestation, built from the example in docs/API.md. */
export function AttestationWindow() {
  const a = attestation;
  return (
    <div className="overflow-hidden rounded-card bg-paper text-ink shadow-raised ring-1 ring-ink/5">
      {/* Title bar */}
      <div className="flex items-center justify-between gap-4 border-b border-ink/8 px-5 py-3.5 md:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <Cuts className="shrink-0 text-sun" height={12} stroke={3} />
          <span className="truncate font-mono text-[13px] text-ink-soft">
            {a.title} {a.id}… · trigger {a.trigger} · {a.status}
          </span>
        </div>
        <span className="inline-flex shrink-0 items-center gap-2 rounded-full bg-ink px-3 py-1.5 text-[13px] font-semibold text-paper">
          <ShieldCheck size={15} className="text-sun" aria-hidden="true" />
          {a.signed}
        </span>
      </div>

      {/* Agent header */}
      <div className="grid gap-3 px-5 pt-5 md:grid-cols-[1fr_auto] md:items-end md:px-6">
        <div>
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-heading-md">{a.agent.name}</span>
            <span className="text-small text-ink-soft">owner {a.agent.owner}</span>
            <span className="rounded-full bg-cream px-2 py-0.5 font-mono text-[12px] text-ink">
              risk {a.agent.risk}
            </span>
          </div>
          <div className="mt-1 truncate font-mono text-[12px] text-ink-soft">{a.card}</div>
        </div>
        <div className="font-mono text-[12px] text-ink-soft">{a.contract}</div>
      </div>

      {/* Results */}
      <div className="px-5 pt-5 md:px-6">
        <div className="grid grid-cols-[1fr_repeat(3,56px)] gap-2 border-b border-ink/8 pb-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-soft sm:grid-cols-[1fr_repeat(3,96px)] sm:text-[12px]">
          <span>{a.columns[0]}</span>
          <span className="text-right">{a.columns[1]}</span>
          <span className="text-right">{a.columns[2]}</span>
          <span className="text-right">{a.columns[3]}</span>
        </div>
        <ul className="divide-y divide-ink/8">
          {a.results.map((r) => (
            <li
              key={r.id}
              className="grid grid-cols-[1fr_repeat(3,56px)] items-center gap-2 py-3 sm:grid-cols-[1fr_repeat(3,96px)]"
            >
              <div className="min-w-0">
                <div className="truncate font-mono text-[13px] font-medium text-ink">
                  {r.skill} <span className="text-ink-soft">· {r.id}</span>
                </div>
                <div className="text-[13px] text-ink-soft">kind {r.kind}</div>
              </div>
              <span className="text-right font-mono text-[15px] font-semibold text-pass">{r.pass}</span>
              <span className={`text-right font-mono text-[15px] font-semibold ${r.fail ? "text-fail" : "text-ink-soft"}`}>
                {r.fail}
              </span>
              <span className={`text-right font-mono text-[15px] font-semibold ${r.inconclusive ? "text-partial" : "text-ink-soft"}`}>
                {r.inconclusive}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Decisions + budget */}
      <div className="grid gap-3 px-5 pt-4 md:grid-cols-[1fr_auto] md:px-6">
        <ol className="flex flex-col gap-2">
          {a.decisions.map((d, i) => (
            <li key={i} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
              <Outcome outcome={d.outcome} />
              <span className="inline-flex items-center gap-1.5 text-ink-soft">
                {d.by === "policy" ? (
                  <ShieldCheck size={14} aria-hidden="true" />
                ) : (
                  <UserCheck size={14} aria-hidden="true" />
                )}
                decided_by {d.by}
              </span>
              <span className="font-mono text-[12px] text-ink-soft">{d.at}</span>
            </li>
          ))}
        </ol>
        <div className="rounded-[12px] bg-cream px-4 py-3 md:min-w-[180px]">
          <div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-soft">{a.budget.label}</div>
          <div className="mt-1 font-mono text-[15px] text-ink">
            <span className="font-semibold">{a.budget.cost}</span>
            <span className="text-ink-soft"> of {a.budget.limit}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/10" aria-hidden="true">
            <div className="h-full rounded-full bg-sky" style={{ width: "14%" }} />
          </div>
        </div>
      </div>

      {/* Not tested */}
      <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1.5 border-t border-ink/8 bg-cream/60 px-5 py-3 text-[12px] text-ink-soft md:px-6">
        <span className="whitespace-nowrap font-semibold uppercase tracking-[0.06em] text-ink">{a.notTested.label}</span>
        {a.notTested.items.map((item) => (
          <code key={item} className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-[12px] text-ink">
            {item}
          </code>
        ))}
      </div>
    </div>
  );
}
