"use client";

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
  intro,
  tone = "ink",
  className = "",
  id,
}: {
  label: string;
  headline: string;
  intro?: string;
  tone?: "ink" | "paper";
  className?: string;
  id?: string;
}) {
  const paper = tone === "paper";
  return (
    <div className={`max-w-[760px] ${className}`}>
      <SectionLabel tone={tone}>{label}</SectionLabel>
      <h2 id={id} className={`mt-5 text-display-lg text-balance ${paper ? "text-paper" : "text-ink"}`}>
        {headline}
      </h2>
      {intro ? (
        <p className={`mt-6 max-w-[640px] text-pretty text-body md:text-[19px] ${paper ? "text-paper/70" : "text-ink-soft"}`}>
          {intro}
        </p>
      ) : null}
    </div>
  );
}
