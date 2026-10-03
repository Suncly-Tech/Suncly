import { Check, Minus, ShieldCheck, X } from "lucide-react";
import { report, type ClaimResult } from "@/lib/content";
import { Cuts } from "./Cuts";

const resultStyle: Record<ClaimResult, { label: string; cls: string; Icon: typeof Check }> = {
  pass: { label: "pass", cls: "bg-[#e6f4ec] text-pass", Icon: Check },
  partial: { label: "partial", cls: "bg-[#fbf1dc] text-partial", Icon: Minus },
  fail: { label: "fail", cls: "bg-[#fdebe7] text-fail", Icon: X },
};

export function ResultPill({ result }: { result: ClaimResult }) {
  const { label, cls, Icon } = resultStyle[result];
  return (
    <span
      className={`inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 text-[13px] font-semibold ${cls}`}
    >
      <Icon size={14} strokeWidth={3} aria-hidden="true" />
      {label}
    </span>
  );
}

/** Mocked attestation report. Field values are illustrative — align with the final schema. */
export function ProductWindow() {
  return (
    <div className="overflow-hidden rounded-card bg-paper text-ink shadow-raised ring-1 ring-ink/5">
      {/* Title bar */}
      <div className="flex items-center justify-between gap-4 border-b border-ink/8 px-5 py-3.5 md:px-6">
        <div className="flex items-center gap-3">
          <Cuts className="text-sun" height={12} stroke={3} />
          <span className="font-mono text-[13px] text-ink-soft">{report.file}</span>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-ink px-3 py-1.5 text-[13px] font-semibold text-paper">
          <ShieldCheck size={15} className="text-sun" aria-hidden="true" />
          {report.badge}
          <span className="hidden font-normal text-paper/60 sm:inline">· {report.badgeNote}</span>
        </span>
      </div>

      {/* Agent header */}
      <div className="flex flex-col gap-1 px-5 pt-5 md:flex-row md:items-baseline md:justify-between md:px-6">
        <div className="flex items-baseline gap-2.5">
          <span className="text-heading-md">{report.agent.name}</span>
          <span className="font-mono text-[13px] text-ink-soft">{report.agent.version}</span>
        </div>
        <span className="truncate font-mono text-[12px] text-ink-soft">{report.card}</span>
      </div>

      {/* Claims */}
      <div className="px-5 pt-5 md:px-6">
        <div className="hidden grid-cols-[1.35fr_1fr_auto] gap-4 border-b border-ink/8 pb-2 text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-soft md:grid">
          <span>{report.columns[0]}</span>
          <span>{report.columns[1]}</span>
          <span className="w-[88px]">{report.columns[2]}</span>
        </div>
        <ul className="divide-y divide-ink/8">
          {report.claims.map((c) => (
            <li
              key={c.path}
              className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 py-3.5 md:grid-cols-[1.35fr_1fr_auto] md:items-center"
            >
              <div className="min-w-0">
                <div className="truncate font-mono text-[13px] font-medium text-ink">{c.path}</div>
                <div className="text-[14px] text-ink-soft">{c.claim}</div>
              </div>
              <div className="col-span-2 text-[14px] text-ink-soft md:col-span-1">{c.observed}</div>
              <div className="row-start-1 col-start-2 md:row-auto md:col-auto md:w-[88px]">
                <ResultPill result={c.result} />
              </div>
            </li>
          ))}
        </ul>
      </div>

      {/* Stress-test summary */}
      <div className="mx-5 mt-2 mb-5 rounded-[12px] bg-cream p-4 md:mx-6 md:mb-6">
        <div className="flex items-center justify-between">
          <span className="text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-soft">
            {report.stress.label}
          </span>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {report.stress.stats.map((s) => (
            <div key={s.label}>
              <dt className="text-[12px] text-ink-soft">{s.label}</dt>
              <dd className="font-mono text-[20px] font-semibold leading-tight text-ink">{s.value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Footer */}
      <div className="border-t border-ink/8 bg-cream/60 px-5 py-3 text-[12px] text-ink-soft md:px-6">
        {report.footer}{" "}
        <code className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-[12px] text-ink">
          {report.footerCmd}
        </code>
      </div>
    </div>
  );
}
