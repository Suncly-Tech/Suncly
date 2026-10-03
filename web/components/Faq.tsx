import { Plus } from "lucide-react";
import { faq } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

export function Faq() {
  return (
    <section id="faq" className="scroll-mt-20 bg-cream py-24 md:py-32" aria-labelledby="faq-heading">
      <div className="container-site">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
          <SectionHeader label={faq.label} headline={faq.headline} />
          <Reveal>
            <div className="divide-y divide-ink/10 border-y border-ink/10">
              {faq.items.map((item) => (
                <details key={item.q} className="group">
                  <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-6 py-5 text-heading-md text-ink [&::-webkit-details-marker]:hidden">
                    <span>{item.q}</span>
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-paper text-ink ring-1 ring-ink/10 transition-transform duration-200 group-open:rotate-45">
                      <Plus size={16} aria-hidden="true" />
                    </span>
                  </summary>
                  <p className="max-w-[640px] pb-6 text-body text-ink-soft">{item.a}</p>
                </details>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
