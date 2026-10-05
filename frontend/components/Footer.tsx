import Link from "next/link";
import { Lockup } from "./Logo";
import { TRADEMARK_SYMBOL } from "@/lib/launch";
import { InView } from "./InView";
import { FindSuncly } from "./home/FindSuncly";
import { banner, footer, site } from "@/lib/content";
import { company } from "@/lib/launch";
import { WORDMARK_PATH, WORDMARK_VIEWBOX } from "@/lib/wordmark";

/**
 * Compact footer navigation in four columns, the legal line, and the signature banner:
 * the sun mark and the name at monumental scale, standing on the bottom edge of the page
 * like a horizon. Dusk surface, "Last light".
 */
export function Footer({ withFind = false }: { withFind?: boolean }) {
  const legalLine = [site.copyright, company.legalEntityName, company.registryCode, company.registeredOffice, site.city]
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
                      <a href={link.href} className="inline-block py-1.5 text-paper/85 transition-colors duration-200 hover:text-sun">
                        {link.label}
                      </a>
                    ) : (
                      <Link href={link.href} className="inline-block py-1.5 text-paper/85 transition-colors duration-200 hover:text-sun">
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
  const [vx, vy, vw, vh] = WORDMARK_VIEWBOX;
  // the mark (public/mark.svg, 120 units) scaled to the lettering's height, a gap, then the lettering
  const scale = vh / 120;
  const markW = 120 * scale;
  const gap = vh * 0.28;
  const totalW = markW + gap + vw;
  return (
    <InView as="div" className="relative" once>
      <div className="container-site flex items-center justify-between gap-6 pb-5">
        <p className="text-eyebrow text-paper/70">{banner.line}</p>
        <Lockup height={18} className="text-paper" trademark />
      </div>
      <div className="relative mx-auto w-[92vw] max-w-none" aria-hidden="true">
        <svg
          viewBox={`0 0 ${totalW + vh * 0.2} ${vh}`}
          className="block w-full text-paper"
          fill="currentColor"
          fillRule="evenodd"
          preserveAspectRatio="xMinYMax meet"
        >
          <defs>
            <mask id="banner-cuts" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
              <rect width="120" height="120" fill="#fff" />
              <polygon points="20,120 30,120 70,0 60,0" fill="#000" />
              <polygon points="50,120 60,120 100,0 90,0" fill="#000" />
            </mask>
            <linearGradient id="banner-light" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" stopColor="#F2C14E" stopOpacity="0" />
              <stop offset="0.5" stopColor="#F2C14E" stopOpacity="0.85" />
              <stop offset="1" stopColor="#F2C14E" stopOpacity="0" />
            </linearGradient>
            <mask id="banner-word">
              <g transform={`translate(${markW + gap - vx} ${-vy})`}>
                <path d={WORDMARK_PATH} fill="#fff" />
              </g>
            </mask>
          </defs>
          <g transform={`scale(${scale})`}>
            <circle cx="60" cy="60" r="44" fill="#F2C14E" mask="url(#banner-cuts)" />
          </g>
          <g transform={`translate(${markW + gap - vx} ${-vy})`}>
            <path d={WORDMARK_PATH} />
          </g>
          <g mask="url(#banner-word)">
            <rect x={-vw * 0.6} y="0" width={vw * 0.5} height={vh} fill="url(#banner-light)" className="banner-edge-light" />
          </g>
          {/* the trade mark symbol, drawn: hairline stroke, at the top right of the last letter, at ascender height */}
          <g transform={`translate(${totalW + vh * 0.03} ${vh * 0.02}) scale(0.55)`} fill="none" stroke="currentColor" strokeWidth={vh * 0.014} strokeLinecap="round" strokeLinejoin="round">
            {TRADEMARK_SYMBOL === "®" ? (
              <>
                <circle cx={vh * 0.11} cy={vh * 0.11} r={vh * 0.1} />
                <path d={`M${vh * 0.075} ${vh * 0.16} V${vh * 0.06} h${vh * 0.04} a${vh * 0.025} ${vh * 0.025} 0 0 1 0 ${vh * 0.05} h-${vh * 0.04} m${vh * 0.04} 0 l${vh * 0.03} ${vh * 0.05}`} />
              </>
            ) : (
              <>
                <path d={`M0 ${vh * 0.03} h${vh * 0.09} m-${vh * 0.045} 0 v${vh * 0.16}`} />
                <path d={`M${vh * 0.12} ${vh * 0.19} v-${vh * 0.16} l${vh * 0.055} ${vh * 0.1} l${vh * 0.055} -${vh * 0.1} v${vh * 0.16}`} />
              </>
            )}
          </g>
        </svg>
        <div className="mt-[-1px] h-px w-full bg-gradient-to-r from-sun/80 via-paper/25 to-paper/5" />
      </div>
      <style>{`
        .banner-edge-light { opacity: 0; }
        [data-inview="true"] .banner-edge-light { animation: banner-pass 1.1s cubic-bezier(0.22, 1, 0.36, 1) 150ms 1 both; }
        @keyframes banner-pass { from { transform: translateX(0); opacity: 1; } to { transform: translateX(${(totalW + vw) }px); opacity: 1; } }
        @media (prefers-reduced-motion: reduce) { .banner-edge-light { animation: none !important; opacity: 0 !important; } }
      `}</style>
    </InView>
  );
}
