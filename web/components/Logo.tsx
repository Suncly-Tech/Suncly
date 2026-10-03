import Link from "next/link";
import { site } from "@/lib/content";

/** The sun with two diagonal cuts. Always yellow, on every background. */
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

export function Logo({
  tone = "ink",
  size = 28,
  href = "/",
}: {
  tone?: "ink" | "paper";
  size?: number;
  href?: string;
}) {
  const color = tone === "paper" ? "text-paper" : "text-ink";
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2.5 ${color} no-underline`}
      aria-label="Suncly home"
    >
      <Mark size={size} />
      <span
        className="font-sans font-bold leading-none"
        style={{ fontSize: size * 0.95, letterSpacing: "-0.03em" }}
      >
        {site.name}
      </span>
    </Link>
  );
}
