import Link from "next/link";
import { Picture } from "@/components/Picture";
import { certified, offer } from "@/lib/content";
import { launch } from "@/lib/launch";

/**
 * 08 Suncly Offer and 09 Suncly Certified: side by side on desktop as one band no taller
 * than half the viewport, stacked on phones. No pricing grid; no agent shown as certified.
 */
export function OfferCertified() {
  const billingLive = launch.usageBilling === "live";
  const programmeOpen = launch.certificationProgramme === "open";
  return (
    <section aria-label="Suncly Offer and Suncly Certified" className="bg-cream-deep/60">
      <div className="container-site grid grid-cols-1 gap-12 py-12 lg:grid-cols-2 lg:gap-16 lg:py-20">
        <div id="offer" className="scroll-mt-20">
          <p className="text-eyebrow text-ink-soft">
            <span className="mr-3 text-ink-mute">08</span>
            {offer.label}
          </p>
          <h2 className="mt-4 text-display-lg text-ink">{offer.headline}</h2>
          <p className="mt-5 max-w-[40ch] text-body text-ink">
            {offer.body} {offer.free}
          </p>
          <p className="mt-3 max-w-[40ch] text-small text-ink-soft">{billingLive ? null : offer.notLive}</p>
          <Link href={billingLive ? offer.liveLink.href : offer.notLiveLink.href} className="mt-4 inline-block text-[15.5px] underline underline-offset-4 decoration-amber hover:text-ember">
            {billingLive ? offer.liveLink.label : offer.notLiveLink.label}
          </Link>
        </div>

        <div id="certified" className="grid scroll-mt-20 gap-6 sm:grid-cols-[minmax(0,1fr)_200px] lg:grid-cols-[minmax(0,1fr)_240px]">
          <div>
            <p className="text-eyebrow text-ink-soft">
              <span className="mr-3 text-ink-mute">09</span>
              {certified.label}
            </p>
            {!programmeOpen ? <p className="mt-3 text-eyebrow text-ember">{certified.eyebrowNotOpen}</p> : null}
            <h2 className="mt-3 text-display-lg text-ink">{certified.headline}</h2>
            <p className="mt-5 max-w-[36ch] text-body text-ink">{certified.body}</p>
            <Link href={certified.link.href} className="mt-4 inline-block text-[15.5px] underline underline-offset-4 decoration-amber hover:text-ember">
              {certified.link.label}
            </Link>
          </div>
          <figure className="m-0 w-[200px] sm:w-auto">
            <Picture name="seal" alt={certified.sealAlt} sizes="(min-width: 640px) 240px, 200px" className="aspect-square rounded-full" />
            {!programmeOpen ? <figcaption className="mt-2 text-center text-eyebrow text-ink-mute">{certified.specimen}</figcaption> : null}
          </figure>
        </div>
      </div>
    </section>
  );
}
