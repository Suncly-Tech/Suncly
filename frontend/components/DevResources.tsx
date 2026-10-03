import Link from "next/link";
import { BookOpen, Braces, Package, History, ArrowUpRight } from "lucide-react";
import { resources } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

const icons = [BookOpen, Braces, Package, History];

export function DevResources() {
  return (
    <section id="developers" className="scroll-mt-20 bg-cream py-24 md:py-32" aria-labelledby="dev-heading">
      <div className="container-site">
        <SectionHeader label={resources.label} headline={resources.headline} />
        <ul className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
          {resources.cards.map((card, i) => {
            const Icon = icons[i];
            const body = (
              <>
                <div className="flex items-start justify-between">
                  <span className="flex h-11 w-11 items-center justify-center rounded-control bg-cream text-ink">
                    <Icon size={20} aria-hidden="true" />
                  </span>
                  {card.href ? (
                    <ArrowUpRight size={18} className="text-ink-soft" aria-hidden="true" />
                  ) : (
                    <span className="rounded-full border border-ink/15 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-ink-soft">
                      {resources.comingLabel}
                    </span>
                  )}
                </div>
                <h3 className="mt-8 text-heading-md text-ink">{card.title}</h3>
                <p className="mt-2 text-small text-ink-soft">{card.body}</p>
              </>
            );
            const cls = "flex h-full flex-col rounded-card bg-paper p-6 ring-1 ring-ink/5";
            return (
              <Reveal key={card.title} as="li" delay={i * 0.06}>
                {card.href ? (
                  <Link
                    href={card.href}
                    className={`${cls} transition-transform duration-200 hover:-translate-y-0.5`}
                  >
                    {body}
                  </Link>
                ) : (
                  <div className={cls} aria-label={`${card.title}: ${resources.comingLabel}`}>
                    {body}
                  </div>
                )}
              </Reveal>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
