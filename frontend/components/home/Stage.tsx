import { MARK_VIEWBOX } from "@/lib/mark";
/**
 * The card stage for 04 How it works: one card that passes through four states.
 *  0 lit:    the card under the sun with its true shadow
 *  1 marked: the approval mark on the card
 *  2 runs:   five small suns above the card
 *  3 hatch:  the hatch over what was not tested
 * Pure SVG, drawn in B's restrained linework; no raster, no animation library.
 */
export function Stage({
  state,
  className = "",
}: {
  state: 0 | 1 | 2 | 3;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 600 520"
      className={className}
      role="img"
      aria-label={STAGE_LABELS[state]}
    >
      <defs>
        <pattern
          id="stage-hatch"
          width="7"
          height="7"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(-18.4)"
        >
          <line
            x1="0"
            y1="0"
            x2="0"
            y2="7"
            stroke="#1B1814"
            strokeWidth="0.9"
            strokeOpacity="0.55"
          />
        </pattern>
        <linearGradient id="stage-shadow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6E4D22" stopOpacity="0.5" />
          <stop offset="1" stopColor="#6E4D22" stopOpacity="0.08" />
        </linearGradient>
        <linearGradient id="stage-face" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FFFEFA" />
          <stop offset="1" stopColor="#F3ECDC" />
        </linearGradient>
      </defs>
      {/* ground line */}
      <line
        x1="40"
        y1="400"
        x2="560"
        y2="400"
        stroke="#1B1814"
        strokeOpacity="0.5"
        strokeWidth="1"
      />
      {/* the sun, drawn in line: the mark as traced (lib/mark.ts), 48 units wide */}
      <g transform="translate(512 36) scale(0.095)">
        <use
          href="#suncly-mark"
          transform={`translate(${-MARK_VIEWBOX[0]} ${-MARK_VIEWBOX[1]})`}
          fill="none"
          stroke="#C8842B"
          strokeWidth={1.2 / 0.095}
          strokeLinejoin="round"
        />
      </g>
      {/* the five small suns of the runs */}
      <g opacity={state === 2 ? 1 : 0} style={{ transition: "opacity 300ms" }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i} transform={`translate(${242 + i * 32} 144) scale(0.032)`}>
            <use
              href="#suncly-mark"
              transform={`translate(${-MARK_VIEWBOX[0]} ${-MARK_VIEWBOX[1]})`}
              fill="none"
              stroke="#C8842B"
              strokeWidth={0.9 / 0.032}
              strokeLinejoin="round"
            />
          </g>
        ))}
        <text
          x="314"
          y="124"
          textAnchor="middle"
          fontFamily="var(--font-mono)"
          fontSize="11"
          fill="#5C564C"
        >
          5 runs
        </text>
      </g>
      {/* the shadow: true in states 0 to 2, hatched in state 3 */}
      <polygon
        points="250,400 370,400 300,500 180,500"
        fill={state === 3 ? "url(#stage-hatch)" : "url(#stage-shadow)"}
        stroke={state === 3 ? "#1B1814" : "none"}
        strokeOpacity="0.5"
        strokeWidth="0.8"
        style={{ transition: "fill 300ms" }}
      />
      {/* the card */}
      <rect
        x="254"
        y="184"
        width="120"
        height="216"
        rx="5"
        fill="url(#stage-face)"
        stroke="#1B1814"
        strokeWidth="1.1"
      />
      <g stroke="#1B1814" strokeOpacity="0.35" strokeWidth="1">
        <line x1="272" y1="212" x2="332" y2="212" />
        <line x1="272" y1="228" x2="352" y2="228" />
        <line x1="272" y1="244" x2="342" y2="244" />
      </g>
      {/* the approval mark */}
      <g opacity={state >= 1 ? 1 : 0} style={{ transition: "opacity 300ms" }}>
        <rect
          x="270"
          y="334"
          width="88"
          height="40"
          fill="none"
          stroke="#C8842B"
          strokeWidth="1"
          transform="rotate(-6 314 354)"
        />
        <text
          x="314"
          y="358"
          textAnchor="middle"
          fontFamily="var(--font-mono)"
          fontSize="10"
          fill="#8F4A1E"
          transform="rotate(-6 314 354)"
        >
          approved_by
        </text>
      </g>
      {/* hatch legend */}
      <g opacity={state === 3 ? 1 : 0} style={{ transition: "opacity 300ms" }}>
        <rect
          x="40"
          y="440"
          width="18"
          height="12"
          fill="url(#stage-hatch)"
          stroke="#1B1814"
          strokeOpacity="0.5"
          strokeWidth="0.8"
        />
        <text
          x="66"
          y="450"
          fontFamily="var(--font-mono)"
          fontSize="11"
          fill="#5C564C"
        >
          not tested
        </text>
      </g>
      <text
        x="560"
        y="500"
        textAnchor="end"
        fontFamily="var(--font-mono)"
        fontSize="11"
        fill="#8A8378"
      >
        18.4°
      </text>
    </svg>
  );
}

export const STAGE_LABELS = [
  "A card under one sun, with its true shadow.",
  "The same card, with the approval mark on it.",
  "The same card, with five small suns above it: five runs.",
  "The same card; the hatch covers what was not tested.",
] as const;
