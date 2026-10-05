import { findSuncly } from "@/lib/content";
import { socialLinks } from "@/lib/launch";

/**
 * 15 Find Suncly. One quiet row: the small heading and a link per platform, in order. A
 * blank link is not rendered (lib/launch.ts). Each link is a real anchor with an
 * accessible name, a 44 px target, visible focus and a hover that is a change of light.
 *
 * Glyphs: the platforms' own logos appear only once their usage guidelines have been
 * confirmed (HANDOFF.md). Until then each link carries a minimal text abbreviation in a
 * monochrome ring, drawn inline; no external icon script.
 */
export function FindSuncly({ tone = "dusk" }: { tone?: "dusk" | "paper" }) {
  if (!socialLinks.length) return null;
  const dark = tone === "dusk";
  return (
    <section aria-labelledby="find-heading" className={`${dark ? "border-b border-paper/10" : "border-y border-line"}`}>
      <div className="container-site flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 id="find-heading" className={`text-eyebrow ${dark ? "text-paper/70" : "text-ink-soft"}`}>
            {findSuncly.heading}
          </h2>
          <p className={`mt-1 text-[13px] ${dark ? "text-paper/50" : "text-ink-mute"}`}>{findSuncly.note}</p>
        </div>
        <ul className="flex flex-wrap items-center gap-2">
          {socialLinks.map((s) => (
            <li key={s.id}>
              <a
                href={s.url}
                rel="me noopener noreferrer"
                target="_blank"
                aria-label={s.abbreviation.length > 1 && !s.name.toLowerCase().includes(s.abbreviation.toLowerCase()) ? `${s.label} (${s.abbreviation})` : s.label}
                title={s.label}
                className={`group inline-flex h-11 w-11 items-center justify-center rounded-full ring-1 transition-colors duration-200 ${
                  dark ? "text-paper/80 ring-paper/25 hover:bg-paper/10 hover:text-sun hover:ring-sun/60" : "text-ink ring-line-strong hover:bg-sun/20 hover:ring-ink"
                }`}
              >
                <svg viewBox="0 0 44 44" width="44" height="44" aria-hidden="true" focusable="false" className="block">
                  <text x="22" y="22" textAnchor="middle" dominantBaseline="central" fontFamily="var(--font-mono)" fontSize={s.abbreviation.length > 1 ? 13 : 15} fontWeight="500" fill="currentColor">
                    {s.abbreviation}
                  </text>
                </svg>
              </a>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
