"use client";

import { LazyMotion, domAnimation } from "motion/react";
import type { ReactNode } from "react";

/** Loads Motion's DOM animation features lazily so the initial bundle stays small. */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={domAnimation} strict>
      {children}
    </LazyMotion>
  );
}
