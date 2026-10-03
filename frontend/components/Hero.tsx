import { PrimaryButton, GhostButton } from "./Button";
import { ProductWindow } from "./ProductWindow";
import { Sky } from "./Sky";
import { hero } from "@/lib/content";

/**
 * Full-viewport blue sky with a serif headline; the product window hangs
 * over the hero's bottom edge into the cream section below.
 */
export function Hero() {
  return (
    <>
      <section className="relative isolate flex min-h-[100svh] flex-col justify-end overflow-hidden bg-sky text-paper">
        <Sky />
        <div className="container-site relative z-10 pt-28 md:pt-36">
          <div className="mx-auto max-w-[840px] text-center">
            <span className="inline-flex items-center gap-2 rounded-full border border-paper/25 bg-paper/10 px-3 py-1.5 text-small font-semibold text-paper">
              <span className="h-1.5 w-1.5 rounded-full bg-sun" aria-hidden="true" />
              {hero.eyebrow}
            </span>
            <h1 className="mt-6 text-display-xl text-paper">
              {hero.headline.map((line) => (
                <span key={line} className="block">
                  {line}
                </span>
              ))}
            </h1>
            <p className="mx-auto mt-6 max-w-[600px] text-body text-paper/85 md:text-[19px]">
              {hero.subhead}
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <PrimaryButton href={hero.primary.href}>{hero.primary.label}</PrimaryButton>
              <GhostButton href={hero.secondary.href} className="text-paper">
                {hero.secondary.label}
              </GhostButton>
            </div>
          </div>
        </div>
        {/* Spacer the window overlaps into */}
        <div className="relative z-10 h-[300px] md:h-[340px]" aria-hidden="true" />
      </section>

      <div className="relative z-20 bg-cream">
        <div className="container-site -mt-[260px] md:-mt-[300px]">
          <div className="mx-auto max-w-[920px]">
            <ProductWindow />
          </div>
        </div>
      </div>
    </>
  );
}
