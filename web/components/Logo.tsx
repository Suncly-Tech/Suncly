import Link from "next/link";
import logo from "@/public/brand/logo.json";

/**
 * The brand lockup from assets/ (mark + wordmark), keyed to transparency by
 * scripts/generate-logo.mjs. Both tones are rendered and toggled with CSS so
 * the nav can switch on scroll without a flash.
 */
export function Logo({
  tone = "ink",
  height = 30,
  href = "/",
  className = "",
}: {
  tone?: "ink" | "paper";
  height?: number;
  href?: string;
  className?: string;
}) {
  const width = Math.round(height * logo.aspect);
  return (
    <Link
      href={href}
      className={`inline-flex shrink-0 items-center no-underline ${className}`}
      aria-label="Suncly home"
      style={{ width, height }}
    >
      <img
        src="/brand/logo-light.webp"
        alt=""
        width={width}
        height={height}
        decoding="async"
        fetchPriority="low"
        className={tone === "paper" ? "block" : "hidden"}
      />
      <img
        src="/brand/logo-dark.webp"
        alt=""
        width={width}
        height={height}
        decoding="async"
        fetchPriority="low"
        className={tone === "ink" ? "block" : "hidden"}
      />
    </Link>
  );
}

/** The sun with two diagonal cuts, as vector. Always yellow, on every background. */
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
