import { ButtonLink } from "@/components/Button";
import { SectionLabel } from "@/components/SectionHeader";
import { finalCta, site } from "@/lib/content";

export function FinalCta() {
  return (
    <section id="get-started" className="scroll-mt-20 bg-ink py-20 text-paper md:py-28" aria-labelledby="final-cta-heading">
      <div className="container-site">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-end lg:gap-16">
          <div>
            <SectionLabel tone="paper">Pilot</SectionLabel>
            <h2 id="final-cta-heading" className="mt-5 text-display-lg text-paper">
              {finalCta.headline}
            </h2>
            <p className="mt-6 max-w-[560px] text-body text-paper/70">{finalCta.body}</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:justify-end">
            <ButtonLink href={finalCta.primary.href}>{finalCta.primary.label}</ButtonLink>
            <ButtonLink href={finalCta.secondary.href} variant="ghost" arrow className="text-paper">
              {finalCta.secondary.label}
            </ButtonLink>
          </div>
        </div>
        <p className="mt-10 text-small text-paper/50">
          Or write to <a href={`mailto:${site.email}`} className="text-paper/80 underline underline-offset-4 hover:text-sun">{site.email}</a>.
        </p>
      </div>
    </section>
  );
}
