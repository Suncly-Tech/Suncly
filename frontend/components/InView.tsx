"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Sets data-inview="true" on its element once it enters the viewport (or toggles it when
 * `once` is false). Used to start the one-time entrance light in the hero and the footer
 * banner, and to pause the sky's animation while it is off screen. No layout work.
 */
export function InView({
  children,
  className = "",
  once = true,
  rootMargin = "0px 0px -10% 0px",
  as: Tag = "div",
  id,
}: {
  children: ReactNode;
  className?: string;
  once?: boolean;
  rootMargin?: string;
  as?: "div" | "section" | "footer";
  id?: string;
}) {
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      el?.setAttribute("data-inview", "true");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            el.setAttribute("data-inview", "true");
            if (once) io.disconnect();
          } else if (!once) {
            el.setAttribute("data-inview", "false");
          }
        }
      },
      { rootMargin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [once, rootMargin]);
  const Element = Tag as "div";
  return (
    <Element ref={ref as React.RefObject<HTMLDivElement>} id={id} className={className} data-inview="false">
      {children}
    </Element>
  );
}
