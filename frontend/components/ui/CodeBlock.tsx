"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export function CodeBlock({
  code,
  label,
  className = "",
  lines,
}: {
  code: string;
  /** Short name of what the block holds, used for the copy button's accessible label. */
  label: string;
  className?: string;
  /** Render as individual lines with a prompt glyph. */
  lines?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className={`relative ${className}`}>
      <pre className="code-block pr-14" tabIndex={0} aria-label={label}>
        {lines ? (
          code.split("\n").map((line, i) => (
            <span key={i} className="block">
              <span className="select-none text-sun/80" aria-hidden="true">
                {line.startsWith("#") || line.startsWith("//") ? "  " : "$ "}
              </span>
              {line}
            </span>
          ))
        ) : (
          <code>{code}</code>
        )}
      </pre>
      <button
        type="button"
        onClick={copy}
        className="absolute right-2.5 top-2.5 inline-flex h-9 items-center gap-1.5 rounded-full bg-paper/10 px-3 text-[12px] font-semibold text-paper ring-1 ring-paper/20 transition-colors hover:bg-paper/20 focus-visible:outline-sun"
        aria-label={copied ? `${label} copied` : `Copy ${label}`}
      >
        {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

export function InlineCode({ children }: { children: React.ReactNode }) {
  return <code className="code-inline">{children}</code>;
}
