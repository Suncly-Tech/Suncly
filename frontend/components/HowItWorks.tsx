"use client";

import { howItWorks } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";
import { Terminal } from "./Terminal";

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 bg-cream py-24 md:py-32" aria-labelledby="how-heading">
      <div className="container-site">
        <SectionHeader label={howItWorks.label} headline={howItWorks.headline} id="how-heading" />
        <div className="mt-12 grid grid-cols-1 items-start gap-12 lg:mt-16 lg:grid-cols-[minmax(0,6fr)_minmax(0,6fr)] lg:gap-16">
          <ol className="flex flex-col gap-7">
            {howItWorks.steps.map((step, i) => (
              <Reveal key={step.title} as="li" delay={i * 0.05}>
                <div className="flex gap-5">
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-sun font-mono text-[14px] font-semibold text-ink">
                    {i + 1}
                  </span>
                  <div>
                    <h3 className="text-heading-md text-ink">{step.title}</h3>
                    <p className="mt-1.5 text-body text-ink-soft">{step.body}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </ol>
          <Reveal delay={0.1} className="lg:sticky lg:top-28">
            <Terminal />
          </Reveal>
        </div>
      </div>
    </section>
  );
}
