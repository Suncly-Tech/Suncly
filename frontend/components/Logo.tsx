import Link from "next/link";
import { TRADEMARK_SYMBOL } from "@/lib/launch";
import { WORDMARK_PATH, WORDMARK_VIEWBOX } from "@/lib/wordmark";

/**
 * The sun with two diagonal cuts, exactly as drawn in public/mark.svg. Always the logo's
 * gold, on every background. Never redrawn, recoloured or animated into something else.
 */
export function Mark({ size = 28, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 120 120"
      width={size}
      height={size}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <mask id="suncly-cuts" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
          <rect width="120" height="120" fill="#fff" />
          <polygon points="20,120 30,120 70,0 60,0" fill="#000" />
          <polygon points="50,120 60,120 100,0 90,0" fill="#000" />
        </mask>
      </defs>
      <circle cx="60" cy="60" r="44" fill="#F2C14E" mask="url(#suncly-cuts)" />
    </svg>
  );
}

/**
 * The wordmark as vector: the lettering traced from assets/suncly-black.png (see
 * design/wordmark/). A drawing, never typeset. Fills with currentColor.
 */
export function Wordmark({ height = 26, className = "", trademark = false }: { height?: number; className?: string; trademark?: boolean }) {
  const [, , w, h] = WORDMARK_VIEWBOX;
  const width = (height * w) / h;
  return (
    <span className={`relative inline-block ${className}`} style={{ height, width }}>
      <svg viewBox={WORDMARK_VIEWBOX.join(" ")} width={width} height={height} fill="currentColor" fillRule="evenodd" aria-hidden="true" focusable="false">
        <path d={WORDMARK_PATH} />
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
      aria-label={TRADEMARK_SYMBOL === "®" ? "registered trade mark" : "trade mark"}
      className="absolute font-sans leading-none"
      style={{ right: -size * 1.15, top: -size * 0.1, fontSize: size, fontWeight: 500, letterSpacing: 0 }}
    >
      {TRADEMARK_SYMBOL}
    </span>
  );
}

/** Mark and wordmark together. */
export function Lockup({ height = 26, className = "", trademark = false }: { height?: number; className?: string; trademark?: boolean }) {
  return (
    <span className={`inline-flex items-center ${className}`} style={{ gap: height * 0.32 }}>
      <Mark size={height * 1.08} />
      <Wordmark height={height * 0.82} trademark={trademark} />
    </span>
  );
}

/** The linked lockup used in the navigation and the workspace shell. */
export function Logo({
  tone = "ink",
  height = 26,
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
      <Lockup height={height} />
    </Link>
  );
}
