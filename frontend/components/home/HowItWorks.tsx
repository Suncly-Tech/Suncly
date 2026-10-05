import { howItWorks } from "@/lib/content";
import { Stage } from "./Stage";
import { StickyStage } from "./StickyStage";

/**
 * 04 How it works. One true story in four frames from the sample evaluation (Harbor
 * Returns Agent, skill start-return). On desktop one sticky stage passes through four
 * states as the reader scrolls; on phones, four stacked frames and no sticky behaviour.
 */
export function HowItWorks() {
  return (
    <section id="how" aria-labelledby="how-heading" className="container-site scroll-mt-20 py-12 md:py-24">
      <div className="max-w-[760px]">
        <p className="text-eyebrow text-ink-soft">
          <span className="mr-3 text-ink-mute">04</span>
          {howItWorks.label}
        </p>
        <h2 id="how-heading" className="mt-4 text-display-lg text-ink">
          {howItWorks.headline}
        </h2>
        <p className="mt-4 text-small text-ink-soft">{howItWorks.note}</p>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,6fr)_minmax(0,6fr)] lg:gap-16">
        <div className="hidden lg:block">
          <div className="sticky top-24">
            <StickyStage frameSelector="[data-frame]" />
          </div>
        </div>
        <div className="lg:hidden">
          <Stage state={3} className="w-full max-w-[420px]" />
        </div>
        <ol className="m-0 list-none p-0">
          {howItWorks.frames.map((frame, i) => (
            <li key={frame.title} data-frame={i} className="border-t border-line py-7 lg:min-h-[34vh] lg:py-10">
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-[minmax(0,1fr)_200px] lg:grid-cols-1">
                <div>
                  <p className="text-eyebrow text-ink-mute">0{i + 1}</p>
                  <h3 className="mt-2 text-display-md text-ink">{frame.title}</h3>
                  <p className="mt-3 max-w-[44ch] text-body text-ink">{frame.body}</p>
                  <p className="mt-4"><code className="text-mono-label text-ink-soft">{frame.mono}</code></p>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
