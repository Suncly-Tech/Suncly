"use client";

import { useState } from "react";
import { behaviours } from "@/lib/behaviours";

/**
 * The strip of eleven. Hover or tap a specimen to see its name and what Suncly reports
 * for it, taken from BEHAVIOURS in the code. Buttons, so it works from the keyboard.
 */
export function SpecimenStrip({ label }: { label: string }) {
  const [active, setActive] = useState(0);
  const current = behaviours[active];
  return (
    <div>
      <p className="text-small text-ink-soft">{label}</p>
      <div role="group" aria-label="The eleven mock agents" className="mt-4 grid grid-cols-6 gap-2 sm:grid-cols-11">
        {behaviours.map((b, i) => (
          <button
            key={b.name}
            type="button"
            onClick={() => setActive(i)}
            onMouseEnter={() => setActive(i)}
            onFocus={() => setActive(i)}
            aria-pressed={active === i}
            aria-label={b.name}
            className={`group relative flex aspect-[3/4] min-h-11 items-end justify-center rounded-[4px] ring-1 transition-colors ${
              active === i ? "bg-paper ring-ink" : "bg-cream ring-line hover:bg-paper hover:ring-line-strong"
            }`}
          >
            <span
              aria-hidden="true"
              className={`mb-2 block h-[55%] w-[46%] rounded-[2px] bg-gradient-to-br from-paper to-cream-deep shadow-[inset_0_0_0_1px_rgb(27_24_20/0.15)] ${
                b.shadow === "none" ? "" : "after:absolute after:bottom-1 after:left-[18%] after:h-[22%] after:w-[46%] after:-skew-x-[18.4deg] after:rounded-[1px] after:bg-ember/20 after:content-['']"
              } ${b.shadow === "wrong" ? "after:w-[70%] after:bg-ember/35" : ""} ${b.shadow === "two" ? "before:absolute before:bottom-1 before:left-[45%] before:h-[22%] before:w-[40%] before:-skew-x-[18.4deg] before:bg-ember/15 before:content-['']" : ""}`}
            />
          </button>
        ))}
      </div>
      <div className="mt-4 min-h-[88px] border-t border-line pt-4" aria-live="polite">
        <p className="font-mono text-[14px] text-ink">{current.name}</p>
        <p className="mt-1 text-[15px] text-ink">{current.description}</p>
        <p className="mt-1 text-small text-ink-soft">Suncly reports: {current.reports}.</p>
      </div>
    </div>
  );
}
