"use client";

import { Plus } from "lucide-react";
import { questions } from "@/lib/content";

/** 14 Questions: five at most, collapsed answers under 50 words. */
export function Questions() {
  return (
    <section id="questions" aria-labelledby="questions-heading" className="container-site scroll-mt-20 py-12 md:py-20">
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
        <h2 id="questions-heading" className="text-display-lg text-ink">
          {questions.label}
        </h2>
        <div className="divide-y divide-line border-y border-line">
          {questions.items.map((item) => (
            <details key={item.q} className="group">
              <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-6 py-4 font-display text-[22px] text-ink [&::-webkit-details-marker]:hidden">
                <span>{item.q}</span>
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink ring-1 ring-line transition-transform duration-200 group-open:rotate-45">
                  <Plus size={16} aria-hidden="true" />
                </span>
              </summary>
              <p className="max-w-[60ch] pb-5 text-body text-ink">{item.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
