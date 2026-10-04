import type { ReactNode } from "react";

/** A labelled count. Counts only, never a score: the label says what was counted. */
export function Stat({
  label,
  value,
  hint,
  tone = "ink",
  className = "",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "ink" | "pass" | "fail" | "inconclusive" | "soft";
  className?: string;
}) {
  const color =
    tone === "pass"
      ? "text-pass"
      : tone === "fail"
        ? "text-fail"
        : tone === "inconclusive"
          ? "text-partial"
          : tone === "soft"
            ? "text-ink-soft"
            : "text-ink";
  return (
    <div className={`surface flex min-w-0 flex-col gap-1 p-4 ${className}`}>
      <span className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">{label}</span>
      <span className={`font-mono text-[28px] leading-none tabular-nums ${color}`}>{value}</span>
      {hint ? <span className="text-[13px] text-ink-soft">{hint}</span> : null}
    </div>
  );
}

export function KeyValue({ items, className = "" }: { items: Array<[ReactNode, ReactNode]>; className?: string }) {
  return (
    <dl className={`kv ${className}`}>
      {items.map(([k, v], i) => (
        <div key={i} className="contents">
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Meter({
  value,
  max,
  label,
  tone = "ink",
}: {
  value: number;
  max: number;
  label: string;
  tone?: "ink" | "fail" | "pass";
}) {
  const fraction = max > 0 ? Math.min(value / max, 1) : 0;
  const bar = tone === "fail" ? "bg-fail" : tone === "pass" ? "bg-pass" : "bg-ink";
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3 text-[13px]">
        <span className="text-ink-soft">{label}</span>
        <span className="font-mono tabular-nums text-ink">
          {value} / {max}
        </span>
      </div>
      <div
        className="meter-track"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={max}
        aria-valuenow={value}
        aria-label={label}
      >
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${fraction * 100}%` }} />
      </div>
    </div>
  );
}
