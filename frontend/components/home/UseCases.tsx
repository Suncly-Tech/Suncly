import { useCases } from "@/lib/content";

/** 07 Use cases. Four examples, labelled as examples. Typographic cards with index numerals and hairlines. */
export function UseCases() {
  return (
    <section aria-labelledby="usecases-heading" className="container-site py-12 md:py-24">
      <p className="text-eyebrow text-ink-soft">
        <span className="mr-3 text-ink-mute">07</span>
        {useCases.label}
      </p>
      <h2 id="usecases-heading" className="mt-4 max-w-[760px] text-display-lg text-ink">
        {useCases.headline}
      </h2>
      <ol className="mt-12 grid grid-cols-1 list-none gap-x-10 gap-y-0 p-0 md:grid-cols-2">
        {useCases.items.map((item, i) => (
          <li key={item.title} className="grid grid-cols-1 gap-3 border-t border-line py-7 md:grid-cols-[48px_minmax(0,1fr)]">
            <span className="text-eyebrow text-ink-mute">0{i + 1}</span>
            <div>
              <h3 className="text-display-md text-ink">{item.title}</h3>
              <dl className="mt-4 grid grid-cols-1 gap-3 text-[15.5px]">
                <div>
                  <dt className="text-eyebrow text-ink-soft">{useCases.todayLabel}</dt>
                  <dd className="mt-1 text-ink">{item.today}</dd>
                </div>
                <div className="hatch -ml-2 pl-2">
                  <dt className="text-eyebrow text-ink-soft">{useCases.outsideLabel}</dt>
                  <dd className="mt-1 text-ink-soft">{item.outside}</dd>
                </div>
              </dl>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
