import Link from "next/link";
import { Lockup } from "./Logo";
import { TRADEMARK_SYMBOL } from "@/lib/launch";
import { InView } from "./InView";
import { FindSuncly } from "./home/FindSuncly";
import { banner, footer, site } from "@/lib/content";
import { company } from "@/lib/launch";
import { LOCKUP_VIEWBOX } from "@/lib/mark";

/**
 * Compact footer navigation in four columns, the legal line, and the signature banner:
 * the sun mark and the name at monumental scale, standing on the bottom edge of the page
 * like a horizon. Dusk surface, "Last light".
 */
export function Footer({ withFind = false }: { withFind?: boolean }) {
  const legalLine = [
    site.copyright,
    company.legalEntityName,
    company.registryCode,
    company.registeredOffice,
    site.city,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <footer className="on-dark relative overflow-hidden bg-dusk text-paper">
      {withFind ? <FindSuncly tone="dusk" /> : null}
      <div className="container-site pb-16 pt-14 md:pt-20">
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4 lg:gap-8">
          {footer.groups.map((group) => (
            <div key={group.title}>
              <h2 className="text-eyebrow text-paper/60">{group.title}</h2>
              <ul className="mt-3 flex flex-col gap-1">
                {group.links.map((link) => (
                  <li key={link.href} className="text-[15px]">
                    {link.href.startsWith("mailto:") ? (
                      <a
                        href={link.href}
                        className="inline-block py-1.5 text-paper/85 transition-colors duration-200 hover:text-sun"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="inline-block py-1.5 text-paper/85 transition-colors duration-200 hover:text-sun"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 flex flex-col gap-3 border-t border-paper/10 pt-6 text-[13.5px] leading-relaxed text-paper/65">
          <p>{legalLine}</p>
          <p className="max-w-[72ch]">{footer.attribution}</p>
        </div>
      </div>

      <Banner />
    </footer>
  );
}

/**
 * The signature banner. The wordmark spans at least 90% of the viewport width at every
 * breakpoint, sized in viewport units; every letter stays whole. One pass of edge light
 * crosses the word when it enters view, once, about a second, absent under reduced motion.
 */
export function Banner() {
  // the lockup as traced: the mark and the lettering share one coordinate system (lib/mark.ts)
  const [lx, ly, lw, lh] = LOCKUP_VIEWBOX;
  return (
    <InView as="div" className="relative" once>
      <div className="container-site flex items-center justify-between gap-6 pb-5">
        <p className="text-eyebrow text-paper/70">{banner.line}</p>
        <Lockup height={15} className="text-paper" trademark />
      </div>
      <div className="relative mx-auto w-[92vw] max-w-none" aria-hidden="true">
        <svg
          viewBox={`${lx} ${ly} ${lw + lh * 0.2} ${lh}`}
          className="block w-full text-paper"
          fill="currentColor"
          fillRule="evenodd"
          preserveAspectRatio="xMinYMax meet"
        >
          <defs>
            <linearGradient id="banner-light" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#F2C14E" stopOpacity="0" />
              <stop offset="0.5" stopColor="#F2C14E" stopOpacity="0.85" />
              <stop offset="1" stopColor="#F2C14E" stopOpacity="0" />
            </linearGradient>
            <mask id="banner-word">
              <use href="#suncly-wordmark" fill="#fff" />
            </mask>
          </defs>
          <use href="#suncly-mark" fill="#F2C14E" />
          <use href="#suncly-wordmark" />
          <g mask="url(#banner-word)">
            <rect
              x={lx - lw * 0.6}
              y={ly}
              width={lw * 0.5}
              height={lh}
              fill="url(#banner-light)"
              className="banner-edge-light"
            />
          </g>
          {/* the trade mark symbol, drawn: hairline stroke, at the top right of the last letter, at ascender height */}
          <g
            transform={`translate(${lx + lw + lh * 0.03} ${ly + lh * 0.02}) scale(0.55)`}
            fill="none"
            stroke="currentColor"
            strokeWidth={lh * 0.014}
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {TRADEMARK_SYMBOL === "®" ? (
              <>
                <circle cx={lh * 0.11} cy={lh * 0.11} r={lh * 0.1} />
                <path
                  d={`M${lh * 0.075} ${lh * 0.16} V${lh * 0.06} h${lh * 0.04} a${lh * 0.025} ${lh * 0.025} 0 0 1 0 ${lh * 0.05} h-${lh * 0.04} m${lh * 0.04} 0 l${lh * 0.03} ${lh * 0.05}`}
                />
              </>
            ) : (
              <>
                <path
                  d={`M0 ${lh * 0.03} h${lh * 0.09} m-${lh * 0.045} 0 v${lh * 0.16}`}
                />
                <path
                  d={`M${lh * 0.12} ${lh * 0.19} v-${lh * 0.16} l${lh * 0.055} ${lh * 0.1} l${lh * 0.055} -${lh * 0.1} v${lh * 0.16}`}
                />
              </>
            )}
          </g>
        </svg>
        <div className="mt-[-1px] h-px w-full bg-gradient-to-r from-sun/80 via-paper/25 to-paper/5" />
      </div>
      <style>{`
        .banner-edge-light { opacity: 0; }
        [data-inview="true"] .banner-edge-light { animation: banner-pass 1.1s cubic-bezier(0.22, 1, 0.36, 1) 150ms 1 both; }
        @keyframes banner-pass { from { transform: translateX(0); opacity: 1; } to { transform: translateX(${lw * 1.3}px); opacity: 1; } }
        @media (prefers-reduced-motion: reduce) { .banner-edge-light { animation: none !important; opacity: 0 !important; } }
      `}</style>
    </InView>
  );
}
