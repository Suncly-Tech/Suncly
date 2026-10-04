"use client";

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { resources } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

export function DevResources() {
  return (
    <section id="developers" className="scroll-mt-20 bg-cream py-24 md:py-32" aria-labelledby="dev-heading">
      <div className="container-site">
        <SectionHeader label={resources.label} headline={resources.headline} intro={resources.intro} id="dev-heading" />
        <ul className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
          {resources.cards.map((card, i) => (
            <Reveal key={card.title} as="li" delay={(i % 4) * 0.05}>
              <Link
                href={card.href}
                className="flex h-full flex-col rounded-card bg-paper p-6 ring-1 ring-ink/5 transition-transform duration-200 hover:-translate-y-0.5"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="rounded-full border border-ink/15 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-soft">
                    {resources.comingLabel}
                  </span>
                  <ArrowUpRight size={18} className="shrink-0 text-ink-soft" aria-hidden="true" />
                </div>
                <h3 className="mt-6 text-heading-md text-ink">{card.title}</h3>
                <p className="mt-2 text-small text-ink-soft">{card.body}</p>
              </Link>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}
