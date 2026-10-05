import { preload } from "react-dom";
import { ButtonLink } from "@/components/Button";
import { Picture } from "@/components/Picture";
import { hero } from "@/lib/content";
import { heroStatusLine } from "@/lib/capabilities";

export const HERO_SIZES = "(min-width: 1024px) 54vw, 100vw";

/**
 * 02 Hero. Dawn. A security lead understands the product from the picture and the
 * headline alone. No table, no dashboard; the evidence moves to section 06.
 */
export function Hero() {
  const status = heroStatusLine();
  // the hero picture is the first thing painted: preload it with the same srcset and sizes
  preload("/art/two-cards-1280.avif", {
    as: "image",
    fetchPriority: "high",
    imageSrcSet: [640, 1280, 1920].map((w) => `/art/two-cards-${w}.avif ${w}w`).join(", "),
    imageSizes: HERO_SIZES,
  });
  return (
    <section
      className="relative isolate overflow-hidden"
      style={{
        background:
          "radial-gradient(120% 70% at 92% -10%, rgb(242 193 78 / 0.32) 0%, rgb(242 193 78 / 0.1) 40%, transparent 70%), linear-gradient(180deg, #FBF6EA 0%, #FAF7F0 60%)",
      }}
    >
      <div className="container-site grid grid-cols-1 gap-8 pb-12 pt-6 lg:min-h-[calc(100svh-72px)] lg:grid-cols-[minmax(0,6fr)_minmax(0,6fr)] lg:items-center lg:gap-14 lg:pb-8 lg:pt-0">
        <div className="animate-settle grid content-center gap-6">
          <p className="text-eyebrow text-ink-soft">{hero.eyebrow}</p>
          <h1 className="text-display-xl text-ink">
            {hero.headline.map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </h1>
          <p className="text-lead max-w-[38ch] text-ink">{hero.subhead}</p>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
            <ButtonLink href={hero.primary.href}>{hero.primary.label}</ButtonLink>
            <ButtonLink href={hero.secondary.href} variant="ghost" arrow>
              {hero.secondary.label}
            </ButtonLink>
          </div>
          <p className="text-mono-label text-ink-soft">
            {status.map((part, i) => (
              <span key={part}>
                {i > 0 ? <span aria-hidden="true"> &nbsp;·&nbsp; </span> : null}
                {part}
              </span>
            ))}
          </p>
        </div>
        <figure className="relative m-0 lg:h-[64svh] lg:min-h-[460px]">
          <Picture name="two-cards" alt={hero.pictureAlt} sizes={HERO_SIZES} priority className="aspect-[13/9] lg:aspect-auto lg:h-full" imgClassName="animate-settle-move" />
          <figcaption className="mt-3 text-mono-label text-ember lg:absolute lg:bottom-5 lg:right-5 lg:mt-0 lg:rounded-sm lg:bg-cream/80 lg:px-2.5 lg:py-1.5 lg:backdrop-blur-sm">
            <span className="sr-only">Evidence line from a suncly demo run: </span>
            <code>{hero.caption}</code>
          </figcaption>
        </figure>
      </div>
    </section>
  );
}
