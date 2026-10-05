"use client";

import { useEffect, useState } from "react";
import { Stage } from "./Stage";

/**
 * Desktop only: the stage sticks while the four frames scroll past, and its state follows
 * the frame nearest the middle of the viewport. On phones the frames carry their own
 * small stage and this component is not rendered.
 */
export function StickyStage({ frameSelector }: { frameSelector: string }) {
  const [state, setState] = useState<0 | 1 | 2 | 3>(0);
  useEffect(() => {
    const frames = Array.from(document.querySelectorAll<HTMLElement>(frameSelector));
    if (!frames.length || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const i = Number(entry.target.getAttribute("data-frame"));
            if (i >= 0 && i <= 3) setState(i as 0 | 1 | 2 | 3);
          }
        }
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 },
    );
    frames.forEach((f) => io.observe(f));
    return () => io.disconnect();
  }, [frameSelector]);
  return <Stage state={state} className="w-full" />;
}
