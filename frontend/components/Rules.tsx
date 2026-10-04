"use client";

import { rules } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

export function Rules() {
  return (
    <section id="rules" className="scroll-mt-20 bg-ink py-24 text-paper md:py-32" aria-labelledby="rules-heading">
      <div className="container-site">
        <SectionHeader label={rules.label} headline={rules.headline} intro={rules.intro} tone="paper" id="rules-heading" />
        <ol className="mt-12 divide-y divide-paper/10 border-y border-paper/10 lg:mt-16">
          {rules.items.map((r, i) => (
            <Reveal key={r.id} as="li" delay={Math.min(i, 3) * 0.05}>
              <div className="grid grid-cols-1 gap-2 py-6 md:grid-cols-[88px_minmax(0,5fr)_minmax(0,7fr)] md:gap-8 md:py-7">
                <span className="font-mono text-[13px] text-sun">{r.id}</span>
                <h3 className="text-heading-lg text-paper md:text-[26px]">{r.rule}</h3>
                <p className="text-body text-paper/70">{r.why}</p>
              </div>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
