import { problem } from "@/lib/content";
import { Cuts } from "./Cuts";
import { Reveal } from "./Reveal";
import { SectionLabel } from "./SectionHeader";

export function ProblemStrip() {
  return (
    <section className="bg-cream py-24 md:py-32" aria-labelledby="problem-heading">
      <div className="container-site">
        <SectionLabel as="h2" id="problem-heading">
          {problem.label}
        </SectionLabel>
        <ul className="mt-8 grid gap-4 md:grid-cols-3 md:gap-6">
          {problem.cards.map((card, i) => (
            <Reveal key={card.title} as="li" delay={i * 0.08}>
              <article className="flex h-full flex-col rounded-card bg-paper p-6 ring-1 ring-ink/5 md:p-8">
                <Cuts
                  className={i === 2 ? "text-sun" : "text-ink/25"}
                  height={16}
                  stroke={4}
                />
                <h3 className="mt-8 text-heading-lg text-balance text-ink">{card.title}</h3>
                <p className="mt-3 text-body text-ink-soft">{card.body}</p>
              </article>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}
