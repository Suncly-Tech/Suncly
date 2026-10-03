import { Cuts } from "./Cuts";

export function SectionLabel({
  children,
  tone = "ink",
  as: Tag = "div",
  id,
}: {
  children: React.ReactNode;
  tone?: "ink" | "paper";
  as?: "div" | "h2";
  id?: string;
}) {
  const color = tone === "paper" ? "text-paper/70" : "text-ink-soft";
  return (
    <Tag id={id} className={`flex items-center gap-3 text-eyebrow ${color}`}>
      <Cuts className="text-sun" height={12} stroke={3} />
      <span>{children}</span>
    </Tag>
  );
}

export function SectionHeader({
  label,
  headline,
  tone = "ink",
  className = "",
}: {
  label: string;
  headline: string;
  tone?: "ink" | "paper";
  className?: string;
}) {
  return (
    <div className={`max-w-[720px] ${className}`}>
      <SectionLabel tone={tone}>{label}</SectionLabel>
      <h2
        className={`mt-5 text-display-lg text-balance ${tone === "paper" ? "text-paper" : "text-ink"}`}
      >
        {headline}
      </h2>
    </div>
  );
}
