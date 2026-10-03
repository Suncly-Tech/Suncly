import { standard } from "@/lib/content";
import { Cuts } from "./Cuts";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

function FieldList({
  title,
  items,
}: {
  title: string;
  items: ReadonlyArray<{ field: string; note: string }>;
}) {
  return (
    <div>
      <h3 className="text-heading-md text-ink">{title}</h3>
      <ul className="mt-4 flex flex-col gap-3">
        {items.map((it) => (
          <li key={it.field} className="cuts-bullet text-sun">
            <div className="font-mono text-[14px] font-medium text-ink">{it.field}</div>
            <div className="text-small text-ink-soft">{it.note}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function OpenStandard() {
  return (
    <section id="standard" className="scroll-mt-20 bg-cream-deep py-24 md:py-32" aria-labelledby="standard-heading">
      <div className="container-site">
        <SectionHeader label={standard.label} headline={standard.headline} />
        <p className="mt-6 max-w-[640px] text-body text-ink-soft md:text-[19px]">{standard.intro}</p>

        <div className="mt-12 grid items-start gap-10 lg:mt-16 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div className="flex flex-col gap-10">
            <Reveal>
              <FieldList title={standard.reads.title} items={standard.reads.items} />
            </Reveal>
            <Reveal delay={0.08}>
              <FieldList title={standard.emits.title} items={standard.emits.items} />
            </Reveal>
          </div>

          <Reveal delay={0.1}>
            <div className="overflow-hidden rounded-card bg-ink text-paper shadow-raised ring-1 ring-paper/10">
              <div className="flex items-center gap-3 border-b border-paper/10 px-5 py-3">
                <Cuts className="text-sun" height={12} stroke={3} />
                <span className="font-mono text-[13px] text-paper/60">attestation.json</span>
              </div>
              <pre className="overflow-x-auto p-5 font-mono text-[13px] leading-[1.7] text-paper/90 md:text-[14px]">
                <code>{standard.json}</code>
              </pre>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
