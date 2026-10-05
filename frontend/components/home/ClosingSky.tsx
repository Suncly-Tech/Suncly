import { ButtonLink } from "@/components/Button";
import { InView } from "@/components/InView";
import { closing } from "@/lib/content";

/**
 * 14 The closing scene. The only blue on the site, scoped to this component's variables.
 * A place with depth: high haze, a cloud deck and near wisps, moved at different speeds
 * with CSS transforms; a low sun at the brand angle; a warm horizon. It fades into paper
 * above through a long eased gradient and into dusk below, where the footer begins. The
 * layers pause off screen; under reduced motion the scene is complete and still. A scrim
 * guarantees text contrast.
 */
export function ClosingSky() {
  return (
    <InView as="section" once={false} rootMargin="0px" className="closing-sky relative isolate overflow-hidden" id="closing">
      <style>{`
        .closing-sky { --sky-high: #a9c4e4; --sky-mid: #cfdcec; --sky-low: #f0e2c8; --cloud: #f6f1e6; --cloud-shade: #d8d2c4; }
        .closing-sky .layer { animation-play-state: paused; }
        .closing-sky[data-inview="true"] .layer { animation-play-state: running; }
        @media (prefers-reduced-motion: reduce) { .closing-sky .layer { animation: none !important; } }
      `}</style>
      {/* the sky, fading in from paper and out to dusk */}
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-20"
        style={{
          background:
            "linear-gradient(180deg, #FAF7F0 0%, #FAF7F0 6%, var(--sky-high) 34%, var(--sky-mid) 56%, var(--sky-low) 76%, #C8842B 86%, #17130F 100%)",
        }}
      />
      {/* the low sun, from the brand angle */}
      <div
        aria-hidden="true"
        className="absolute -z-10 h-[52vw] w-[52vw] max-h-[620px] max-w-[620px] rounded-full"
        style={{
          right: "8%",
          bottom: "12%",
          background: "radial-gradient(circle, rgba(242,193,78,0.95) 0%, rgba(242,193,78,0.55) 22%, rgba(242,193,78,0.12) 48%, rgba(242,193,78,0) 70%)",
          transform: "translate(22%, 22%)",
        }}
      />
      {/* high haze */}
      <svg aria-hidden="true" className="layer animate-drift-slower absolute left-[-6%] top-[26%] -z-10 w-[112%] opacity-50" viewBox="0 0 1600 200" preserveAspectRatio="none">
        <defs>
          <filter id="haze-blur" x="-20%" y="-50%" width="140%" height="200%">
            <feGaussianBlur stdDeviation="26" />
          </filter>
        </defs>
        <g fill="var(--cloud)" filter="url(#haze-blur)">
          <ellipse cx="300" cy="100" rx="360" ry="40" />
          <ellipse cx="1000" cy="80" rx="420" ry="36" />
          <ellipse cx="1450" cy="120" rx="260" ry="30" />
        </g>
      </svg>
      {/* the cloud deck */}
      <svg aria-hidden="true" className="layer animate-drift-slow absolute left-[-8%] top-[48%] -z-10 w-[116%] opacity-90" viewBox="0 0 1600 320" preserveAspectRatio="none">
        <defs>
          <filter id="deck-blur" x="-20%" y="-50%" width="140%" height="200%">
            <feGaussianBlur stdDeviation="14" />
          </filter>
          <linearGradient id="deck-light" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--cloud)" />
            <stop offset="1" stopColor="var(--cloud-shade)" />
          </linearGradient>
        </defs>
        <g fill="url(#deck-light)" filter="url(#deck-blur)">
          <ellipse cx="160" cy="200" rx="260" ry="52" />
          <ellipse cx="520" cy="170" rx="300" ry="60" />
          <ellipse cx="900" cy="210" rx="340" ry="58" />
          <ellipse cx="1300" cy="180" rx="320" ry="54" />
          <ellipse cx="1600" cy="220" rx="260" ry="48" />
        </g>
      </svg>
      {/* near wisps */}
      <svg aria-hidden="true" className="layer animate-drift-fast absolute left-[-10%] top-[66%] -z-10 w-[120%] opacity-80" viewBox="0 0 1600 200" preserveAspectRatio="none">
        <defs>
          <filter id="wisp-blur" x="-20%" y="-50%" width="140%" height="200%">
            <feGaussianBlur stdDeviation="9" />
          </filter>
        </defs>
        <g fill="var(--cloud)" filter="url(#wisp-blur)">
          <ellipse cx="240" cy="120" rx="200" ry="22" />
          <ellipse cx="760" cy="90" rx="260" ry="26" />
          <ellipse cx="1340" cy="130" rx="220" ry="20" />
        </g>
      </svg>
      {/* the scrim that guarantees text contrast */}
      <div aria-hidden="true" className="absolute inset-0 -z-[5]" style={{ background: "linear-gradient(180deg, rgba(250,247,240,0.85) 0%, rgba(250,247,240,0.55) 40%, rgba(250,247,240,0) 70%)" }} />

      <div className="container-site relative flex min-h-[62svh] flex-col justify-start pb-40 pt-16 md:min-h-[78svh] md:pb-56 md:pt-28">
        <h2 className="max-w-[16ch] text-display-xl text-ink">{closing.headline}</h2>
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <ButtonLink href={closing.action.href}>{closing.action.label}</ButtonLink>
          <a href={`mailto:${closing.contact}`} className="text-[16px] text-ink underline underline-offset-4 decoration-amber hover:text-ember">
            {closing.contact}
          </a>
        </div>
      </div>
    </InView>
  );
}
