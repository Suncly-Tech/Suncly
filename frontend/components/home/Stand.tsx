import { stand } from "@/lib/content";

/** 13 What we stand for, and what a pass does not cover. Normal size, normal contrast. */
export function Stand() {
  return (
    <section id="stand" aria-labelledby="stand-heading" className="container-site scroll-mt-20 py-12 md:py-24">
      <p className="text-eyebrow text-ink-soft">
        <span className="mr-3 text-ink-mute">13</span>
        Scope
      </p>
      <h2 id="stand-heading" className="mt-4 text-display-lg text-ink">
        {stand.headline}
      </h2>
      <div className="mt-10 grid grid-cols-1 gap-10 md:grid-cols-2 md:gap-16">
        <div>
          <h3 className="text-eyebrow text-ink-soft">{stand.forTitle}</h3>
          <ul className="mt-4 flex flex-col divide-y divide-line border-y border-line">
            {stand.forItems.map((line) => (
              <li key={line} className="py-2.5 font-display text-[19px] text-ink md:text-[21px]">
                {line}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-eyebrow text-ink-soft">{stand.notTitle}</h3>
          <ul className="mt-4 flex flex-col divide-y divide-line border-y border-line">
            {stand.notItems.map((line) => (
              <li key={line} className="cuts-bullet py-2.5 font-display text-[19px] text-ink md:text-[21px]">
                {line}
              </li>
            ))}
          </ul>
        </div>
      </div>
      <p className="mt-12 max-w-[68ch] text-lead text-ink">{stand.statement}</p>
    </section>
  );
}
