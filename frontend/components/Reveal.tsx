"use client";

import { useEffect, useRef, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: "div" | "section" | "li" | "article";
};

/**
 * Fade and a 10px rise, once, when the element enters the viewport. CSS only (no
 * animation library): a data attribute flips when the element is seen, and the transition
 * in the stylesheet does the rest. Off under reduced motion, where the element is simply
 * shown.
 */
export function Reveal({ children, className = "", delay = 0, as = "div" }: Props) {
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.setAttribute("data-reveal", "seen");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          el.setAttribute("data-reveal", "seen");
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const Tag = as as "div";
  return (
    <Tag ref={ref as React.RefObject<HTMLDivElement>} className={`reveal ${className}`} data-reveal="unseen" style={delay ? { transitionDelay: `${delay * 1000}ms` } : undefined}>
      {children}
    </Tag>
  );
}
