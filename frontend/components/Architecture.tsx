"use client";

import { architecture } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";
import { SystemDiagram } from "./Diagrams";

export function Architecture() {
  return (
    <section id="architecture" className="scroll-mt-20 bg-cream-deep py-24 md:py-32" aria-labelledby="arch-heading">
      <div className="container-site">
        <SectionHeader label={architecture.label} headline={architecture.headline} intro={architecture.intro} id="arch-heading" />

        <Reveal className="mt-12 lg:mt-16">
          <div className="rounded-card bg-paper p-4 ring-1 ring-ink/5 md:p-8">
            <SystemDiagram />
          </div>
        </Reveal>

        <ul className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 lg:gap-6">
          {architecture.components.map((c, i) => (
            <Reveal key={c.name} as="li" delay={(i % 3) * 0.06}>
              <article className="flex h-full flex-col rounded-card bg-paper p-6 ring-1 ring-ink/5">
                <h3 className="text-heading-md text-ink">{c.name}</h3>
                <p className="mt-3 text-small text-ink-soft md:text-[15px]">{c.does}</p>
                <p className="mt-auto pt-5 text-small">
                  <span className="mr-2 rounded-full bg-ink px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-sun">
                    never
                  </span>
                  <span className="text-ink">{c.never}</span>
                </p>
              </article>
            </Reveal>
          ))}
        </ul>

        <Reveal className="mt-6">
          <div className="flex flex-col gap-4 rounded-card bg-ink p-6 text-paper md:flex-row md:items-center md:justify-between md:p-8">
            <div className="max-w-[560px]">
              <h3 className="text-heading-md text-paper">{architecture.adapters.title}</h3>
              <p className="mt-2 text-small text-paper/70 md:text-[15px]">{architecture.adapters.body}</p>
            </div>
            <ul className="flex flex-wrap gap-2">
              {architecture.outputs.map((o) => (
                <li key={o} className="rounded-full border border-paper/20 px-3 py-1.5 text-[13px] font-semibold text-paper">
                  {o}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
