"use client";

import { m, useReducedMotion, useScroll, useTransform } from "motion/react";

/**
 * Hand-built sky for the hero: gradient, two drifting cloud layers, and the
 * Suncly sun rising from behind the product window with soft rays.
 * Everything here is CSS/SVG; nothing is an image.
 */
export function Sky() {
  const reduce = useReducedMotion();
  const { scrollY } = useScroll();
  const rise = useTransform(scrollY, [0, 600], [0, -40]);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* Gradient sky */}
      <div className="absolute inset-0 bg-[linear-gradient(180deg,#1d3a97_0%,#3461d1_52%,#4f78de_100%)]" />

      {/* Far cloud layer */}
      <svg
        className="animate-drift-slower absolute left-[-10%] top-[12%] w-[120%] opacity-[0.16]"
        viewBox="0 0 1600 300"
        preserveAspectRatio="none"
      >
        <defs>
          <filter id="cloud-blur-far" x="-20%" y="-50%" width="140%" height="200%">
            <feGaussianBlur stdDeviation="22" />
          </filter>
        </defs>
        <g fill="#ffffff" filter="url(#cloud-blur-far)">
          <ellipse cx="220" cy="140" rx="200" ry="46" />
          <ellipse cx="640" cy="90" rx="260" ry="40" />
          <ellipse cx="1120" cy="160" rx="300" ry="50" />
          <ellipse cx="1480" cy="80" rx="180" ry="36" />
        </g>
      </svg>

      {/* Near cloud layer */}
      <svg
        className="animate-drift-slow absolute left-[-8%] top-[34%] w-[116%] opacity-[0.22]"
        viewBox="0 0 1600 320"
        preserveAspectRatio="none"
      >
        <defs>
          <filter id="cloud-blur-near" x="-20%" y="-50%" width="140%" height="200%">
            <feGaussianBlur stdDeviation="16" />
          </filter>
        </defs>
        <g fill="#ffffff" filter="url(#cloud-blur-near)">
          <ellipse cx="140" cy="170" rx="170" ry="40" />
          <ellipse cx="300" cy="140" rx="120" ry="34" />
          <ellipse cx="880" cy="200" rx="240" ry="44" />
          <ellipse cx="1020" cy="160" rx="140" ry="36" />
          <ellipse cx="1400" cy="150" rx="200" ry="40" />
        </g>
      </svg>

      {/* Sun with rays, rising behind the product window */}
      <m.div
        style={reduce ? undefined : { y: rise }}
        className="absolute left-1/2 top-full h-[min(130vw,760px)] w-[min(130vw,760px)] -translate-x-1/2 -translate-y-[82%] md:h-[min(84vw,760px)] md:w-[min(84vw,760px)] md:-translate-y-[60%]"
      >
        {/* Soft glow */}
        <div className="animate-rays absolute inset-[-30%] rounded-full bg-[radial-gradient(circle,rgba(242,193,78,0.42)_0%,rgba(242,193,78,0.16)_32%,rgba(242,193,78,0)_62%)]" />
        {/* Ray spokes, masked to a soft disc */}
        <div
          className="absolute inset-[-24%] rounded-full opacity-[0.28]"
          style={{
            background:
              "repeating-conic-gradient(from 0deg, rgba(255,255,255,0.0) 0deg 9deg, rgba(255,241,196,0.55) 9deg 11deg, rgba(255,255,255,0) 11deg 20deg)",
            WebkitMaskImage:
              "radial-gradient(circle, rgba(0,0,0,1) 36%, rgba(0,0,0,0.5) 52%, rgba(0,0,0,0) 70%)",
            maskImage:
              "radial-gradient(circle, rgba(0,0,0,1) 36%, rgba(0,0,0,0.5) 52%, rgba(0,0,0,0) 70%)",
          }}
        />
        {/* The mark, always yellow */}
        <svg viewBox="0 0 120 120" className="absolute inset-[12%] h-[76%] w-[76%]">
          <defs>
            <mask id="sky-cuts" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
              <rect width="120" height="120" fill="#fff" />
              <polygon points="20,120 30,120 70,0 60,0" fill="#000" />
              <polygon points="50,120 60,120 100,0 90,0" fill="#000" />
            </mask>
          </defs>
          <circle cx="60" cy="60" r="44" fill="#F2C14E" mask="url(#sky-cuts)" />
        </svg>
      </m.div>
    </div>
  );
}
