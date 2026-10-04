"use client";

import { roadmap } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

export function Roadmap() {
  return (
    <section id="roadmap" className="scroll-mt-20 bg-cream-deep py-24 md:py-32" aria-labelledby="roadmap-heading">
      <div className="container-site">
        <SectionHeader label={roadmap.label} headline={roadmap.headline} intro={roadmap.intro} id="roadmap-heading" />

        <ol className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:mt-16 lg:grid-cols-3 lg:gap-6">
          {roadmap.stages.map((s, i) => (
            <Reveal key={s.number} as="li" delay={(i % 3) * 0.06}>
              <div className={`flex h-full flex-col rounded-card p-6 ring-1 ring-ink/5 ${i === 0 ? "bg-ink text-paper" : "bg-paper"}`}>
                <div className="flex items-center gap-3">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-full font-mono text-[14px] font-semibold ${i === 0 ? "bg-sun text-ink" : "bg-cream text-ink"}`}>
                    {s.number}
                  </span>
                  {i === 0 ? (
                    <span className="rounded-full border border-paper/25 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-paper/80">
                      first pilot
                    </span>
                  ) : null}
                </div>
                <h3 className={`mt-5 text-heading-md ${i === 0 ? "text-paper" : "text-ink"}`}>{s.title}</h3>
                <p className={`mt-2 text-small md:text-[15px] ${i === 0 ? "text-paper/70" : "text-ink-soft"}`}>{s.body}</p>
              </div>
            </Reveal>
          ))}
        </ol>

        <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2 lg:gap-6">
          <Reveal>
            <div className="h-full rounded-card bg-paper p-6 ring-1 ring-ink/5 md:p-8">
              <h3 className="text-heading-md text-ink">{roadmap.stack.title}</h3>
              <dl className="mt-4 divide-y divide-ink/8">
                {roadmap.stack.items.map((it) => (
                  <div key={it.k} className="grid grid-cols-[96px_1fr] gap-4 py-3 text-[15px]">
                    <dt className="font-semibold text-ink">{it.k}</dt>
                    <dd className="text-ink-soft">{it.v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </Reveal>
          <Reveal delay={0.08}>
            <div className="h-full rounded-card bg-paper p-6 ring-1 ring-ink/5 md:p-8">
              <h3 className="text-heading-md text-ink">{roadmap.outOfScope.title}</h3>
              <p className="mt-4 text-body text-ink-soft">{roadmap.outOfScope.body}</p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
