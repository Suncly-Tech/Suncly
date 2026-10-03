import { product } from "@/lib/content";
import { Reveal } from "./Reveal";
import { SectionLabel } from "./SectionHeader";
import { AttestDiagram, StressDiagram, GateDiagram, ApproveDiagram } from "./Diagrams";

const diagrams = [AttestDiagram, StressDiagram, GateDiagram, ApproveDiagram];

export function ProductSections() {
  return (
    <section id="product" className="scroll-mt-20 bg-cream pb-24 md:pb-32" aria-labelledby="product-heading">
      <div className="container-site">
        <SectionLabel as="h2" id="product-heading">
          {product.label}
        </SectionLabel>

        <div className="mt-8 flex flex-col gap-6 md:gap-8">
          {product.sections.map((s, i) => {
            const Diagram = diagrams[i];
            const flip = i % 2 === 1;
            return (
              <Reveal key={s.number} as="article">
                <div
                  className={`grid grid-cols-1 items-center gap-8 rounded-card bg-paper p-6 ring-1 ring-ink/5 md:p-10 lg:grid-cols-2 lg:gap-14 lg:p-14 ${
                    flip ? "lg:[&>*:first-child]:order-2" : ""
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-[14px] font-semibold text-sky">{s.number}</span>
                      <span className="h-px w-6 bg-ink/15" aria-hidden="true" />
                      <span className="text-small font-semibold uppercase tracking-[0.08em] text-ink-soft">
                        {s.name}
                      </span>
                    </div>
                    <h3 className="mt-5 text-display-md text-balance text-ink">{s.title}</h3>
                    <p className="mt-5 max-w-[480px] text-body text-ink-soft">{s.body}</p>
                  </div>
                  <div className="rounded-[12px] bg-cream/70 p-2 md:p-4">
                    <Diagram />
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
