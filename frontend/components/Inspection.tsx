"use client";

import { inspection } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

/** The README's five-step definition, set large and plain. */
export function Inspection() {
  return (
    <section className="bg-cream-deep py-24 md:py-32" aria-labelledby="inspection-heading">
      <div className="container-site">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <SectionHeader
            label={inspection.label}
            headline={inspection.headline}
            intro={inspection.intro}
            id="inspection-heading"
          />
          <Reveal>
            <ol className="divide-y divide-ink/10 border-y border-ink/10">
              {inspection.steps.map((step, i) => (
                <li key={step} className="flex items-baseline gap-6 py-5 md:gap-10 md:py-6">
                  <span className="w-8 shrink-0 font-mono text-[14px] font-semibold text-sky">
                    0{i + 1}
                  </span>
                  <span className="text-heading-lg text-balance text-ink md:text-[32px] md:leading-[1.2]">
                    {step}
                  </span>
                </li>
              ))}
            </ol>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
