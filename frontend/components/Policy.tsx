"use client";

import { Check, Flag, AlertCircle } from "lucide-react";
import { policy } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

const icons = { approve: Check, flag: Flag, block: AlertCircle } as const;
const tones = {
  approve: "bg-[#e6f4ec] text-pass",
  flag: "bg-[#fbf1dc] text-partial",
  block: "bg-[#fdebe7] text-fail",
} as const;

export function Policy() {
  return (
    <section id="policy" className="scroll-mt-20 bg-cream py-24 md:py-32" aria-labelledby="policy-heading">
      <div className="container-site">
        <SectionHeader label={policy.label} headline={policy.headline} intro={policy.intro} id="policy-heading" />

        <div className="mt-12 grid grid-cols-1 gap-6 lg:mt-16 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-8">
          <Reveal>
            <div className="overflow-hidden rounded-card bg-paper ring-1 ring-ink/5">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-ink/8 text-[12px] font-semibold uppercase tracking-[0.06em] text-ink-soft">
                    {policy.columns.map((c) => (
                      <th key={c} scope="col" className="px-5 py-4 font-semibold md:px-6">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/8">
                  {policy.rows.map((r) => (
                    <tr key={r.risk}>
                      <th scope="row" className="px-5 py-5 align-top font-mono text-[14px] font-semibold text-ink md:px-6">
                        {r.risk}
                      </th>
                      <td className="px-5 py-5 align-top text-[15px] text-ink-soft md:px-6">{r.example}</td>
                      <td className="px-5 py-5 align-top text-[15px] text-ink md:px-6">{r.approval}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <div className="flex h-full flex-col rounded-card bg-ink p-6 text-paper md:p-8">
              <h3 className="text-heading-md text-paper">{policy.human.title}</h3>
              <ul className="mt-5 flex flex-col gap-3">
                {policy.human.items.map((it) => (
                  <li key={it} className="cuts-bullet text-sun">
                    <span className="text-body text-paper/90">{it}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>

        <ul className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3 lg:gap-6">
          {policy.outcomes.map((o, i) => {
            const Icon = icons[o.outcome];
            return (
              <Reveal key={o.outcome} as="li" delay={i * 0.06}>
                <div className="flex h-full flex-col rounded-card bg-paper p-6 ring-1 ring-ink/5">
                  <span className={`inline-flex h-8 w-fit items-center gap-2 rounded-full px-3 text-[13px] font-semibold ${tones[o.outcome]}`}>
                    <Icon size={14} strokeWidth={2.75} aria-hidden="true" />
                    {o.outcome}
                  </span>
                  <p className="mt-4 text-small text-ink-soft md:text-[15px]">{o.meaning}</p>
                </div>
              </Reveal>
            );
          })}
        </ul>
        <p className="mt-6 max-w-[720px] text-small text-ink-soft md:text-[15px]">{policy.noDecision}</p>
      </div>
    </section>
  );
}
