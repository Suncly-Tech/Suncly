import Link from "next/link";
import { TRADEMARK_SYMBOL } from "@/lib/launch";
import { LOCKUP_GAP, MARK_PATH, MARK_VIEWBOX } from "@/lib/mark";
import { WORDMARK_PATH, WORDMARK_VIEWBOX } from "@/lib/wordmark";

/**
 * The mark: the bullet-shaped sun with two diagonal cuts, exactly as traced from the original
 * lockup (lib/mark.ts). Always the logo's gold, on every background. Never redrawn,
 * recoloured or animated into something else. Like the lettering, the path is written into
 * the document once (`define`, by the navigation's or workspace shell's Logo) and reused.
 */
export function Mark({
  height = 24,
  className = "",
  define = false,
}: {
  height?: number;
  className?: string;
  define?: boolean;
}) {
  const [, , w, h] = MARK_VIEWBOX;
  const width = (height * w) / h;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={MARK_VIEWBOX.join(" ")}
      width={width}
      height={height}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {define ? (
        <defs>
          <g id="suncly-mark">
            <path d={MARK_PATH} fillRule="evenodd" />
          </g>
        </defs>
      ) : null}
      <use href="#suncly-mark" fill="#F2C14E" />
    </svg>
  );
}

/**
 * The wordmark as vector: the lettering traced from assets/suncly-black.png (see
 * design/wordmark/). A drawing, never typeset. Fills with currentColor.
 *
 * The traced lettering. The path is 4 KB, so it is written into the document once, by the
 * navigation's or workspace shell's Logo (`define`), and every other instance (the footer
 * lockup, the banner and its light mask) references it with <use>.
 */
export function Wordmark({
  height = 26,
  className = "",
  trademark = false,
  define = false,
}: {
  height?: number;
  className?: string;
  trademark?: boolean;
  define?: boolean;
}) {
  const [, , w, h] = WORDMARK_VIEWBOX;
  const width = (height * w) / h;
  return (
    <span
      className={`relative inline-block ${className}`}
      style={{ height, width }}
    >
      <svg
        viewBox={WORDMARK_VIEWBOX.join(" ")}
        width={width}
        height={height}
        fill="currentColor"
        fillRule="evenodd"
        aria-hidden="true"
        focusable="false"
      >
        {define ? (
          <defs>
            <g id="suncly-wordmark">
              <path d={WORDMARK_PATH} />
            </g>
          </defs>
        ) : null}
        <use href="#suncly-wordmark" />
      </svg>
      {trademark ? <TrademarkSymbol height={height} /> : null}
    </span>
  );
}

/**
 * The trade mark symbol: drawn, optically sized to the lettering, hairline stroke, set at the
 * top right of the last letter at ascender height. ™ by default; ® only with a registration
 * (lib/launch.ts). Appears nowhere else on the site.
 */
export function TrademarkSymbol({ height }: { height: number }) {
  const size = Math.max(8, height * 0.26);
  return (
    <span
      aria-label={
        TRADEMARK_SYMBOL === "®" ? "registered trade mark" : "trade mark"
      }
      className="absolute font-sans leading-none"
      style={{
        right: -size * 1.15,
        top: -size * 0.1,
        fontSize: size,
        fontWeight: 500,
        letterSpacing: 0,
      }}
    >
      {TRADEMARK_SYMBOL}
    </span>
  );
}

/**
 * Mark and wordmark together, at the proportions and spacing of the original lockup: the
 * mark is 345/415 of the lettering's height and sits 29/415 of it to the left, as traced.
 */
export function Lockup({
  height = 26,
  className = "",
  trademark = false,
  define = false,
}: {
  height?: number;
  className?: string;
  trademark?: boolean;
  define?: boolean;
}) {
  const [, , , wordH] = WORDMARK_VIEWBOX;
  const scale = height / wordH;
  return (
    <span
      className={`inline-flex items-center ${className}`}
      style={{ gap: LOCKUP_GAP * scale }}
    >
      <Mark height={MARK_VIEWBOX[3] * scale} define={define} />
      <Wordmark height={height} trademark={trademark} define={define} />
    </span>
  );
}

/** The linked lockup used in the navigation and the workspace shell. */
export function Logo({
  tone = "ink",
  height = 24,
  href = "/",
  className = "",
}: {
  tone?: "ink" | "paper";
  height?: number;
  href?: string;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex shrink-0 items-center no-underline ${tone === "paper" ? "text-paper" : "text-ink"} ${className}`}
      aria-label="Suncly home"
    >
      <Lockup height={height} define />
    </Link>
  );
}
