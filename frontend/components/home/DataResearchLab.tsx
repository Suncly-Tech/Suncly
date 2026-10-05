import Link from "next/link";
import { Picture } from "@/components/Picture";
import { data, lab, research } from "@/lib/content";
import { SpecimenStrip } from "./SpecimenStrip";

const PICTURE_SIZES = "(min-width: 1024px) 50vw, 100vw";

function Heading({ index, label, headline, id }: { index: string; label: string; headline: string; id: string }) {
  return (
    <>
      <p className="text-eyebrow text-ink-soft">
        <span className="mr-3 text-ink-mute">{index}</span>
        {label}
      </p>
      <h2 id={id} className="mt-4 text-display-lg text-ink">
        {headline}
      </h2>
    </>
  );
}

function MoreLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="mt-5 inline-block text-[15.5px] underline underline-offset-4 decoration-amber hover:text-ember">
      {label}
    </Link>
  );
}

/** 10 Suncly Data. Clear daylight; "The aperture" as a dark last-light plate inside the pale section. */
export function Data() {
  return (
    <section id="data" aria-labelledby="data-heading" className="container-site scroll-mt-20 py-12 md:py-24">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-2 lg:items-center lg:gap-16">
        <Picture name="aperture" alt={data.pictureAlt} sizes={PICTURE_SIZES} className="aspect-[4/3] lg:min-h-[55vh]" />
        <div>
          <Heading index="10" label={data.label} headline={data.headline} id="data-heading" />
          <p className="mt-5 max-w-[40ch] text-body text-ink">{data.body}</p>
          <ul className="mt-6 flex flex-col gap-2.5">
            {data.facts.map((fact) => (
              <li key={fact} className="cuts-bullet text-mono-label text-ink-soft">
                {fact}
              </li>
            ))}
          </ul>
          <MoreLink href={data.link.href} label={data.link.label} />
        </div>
      </div>
    </section>
  );
}

/** 11 Suncly Research. Golden hour. "Analemma": repeated observation is the method. */
export function Research() {
  return (
    <section id="research" aria-labelledby="research-heading" className="scroll-mt-20 bg-cream-deep/70 py-12 md:py-24">
      <div className="container-site grid grid-cols-1 gap-10 lg:grid-cols-2 lg:items-center lg:gap-16">
        <div className="lg:order-2">
          <Picture name="analemma" alt={research.pictureAlt} sizes={PICTURE_SIZES} className="aspect-[4/3] lg:min-h-[55vh]" />
        </div>
        <div className="lg:order-1">
          <Heading index="11" label={research.label} headline={research.headline} id="research-heading" />
          <p className="mt-5 max-w-[40ch] text-body text-ink">{research.body}</p>
          <ul className="mt-6 flex flex-col divide-y divide-line border-y border-line">
            {research.notes.map((title) => (
              <li key={title} className="flex items-baseline justify-between gap-4 py-3">
                <span className="font-display text-[20px] text-ink">{title}</span>
                <span className="text-eyebrow shrink-0 text-ink-mute">{research.inReview}</span>
              </li>
            ))}
          </ul>
          <MoreLink href={research.link.href} label={research.link.label} />
        </div>
      </div>
    </section>
  );
}

/** 12 Suncly Lab. Golden hour. "Eleven specimens" and the interactive strip of the eleven mock agents. */
export function Lab() {
  return (
    <section id="lab" aria-labelledby="lab-heading" className="scroll-mt-20 bg-cream-deep/70 pb-12 md:pb-24">
      <div className="container-site">
        <Picture name="specimens" alt={lab.pictureAlt} sizes="100vw" className="aspect-[9/4] lg:min-h-[50vh]" />
        <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <Heading index="12" label={lab.label} headline={lab.headline} id="lab-heading" />
            <p className="mt-5 max-w-[40ch] text-body text-ink">{lab.body}</p>
            <p className="mt-4 text-small text-ink-soft">
              {lab.planned}: <span className="text-eyebrow">Planned</span>
            </p>
            <MoreLink href={lab.link.href} label={lab.link.label} />
          </div>
          <SpecimenStrip label={lab.stripLabel} />
        </div>
      </div>
    </section>
  );
}
