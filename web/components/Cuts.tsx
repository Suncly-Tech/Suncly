/** The two diagonal cuts from the mark, used as a divider or inline glyph. */
export function Cuts({
  className = "",
  height = 14,
  stroke = 4,
}: {
  className?: string;
  height?: number;
  stroke?: number;
}) {
  const width = height * 1.6;
  const slope = height * 0.45;
  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <line x1={slope} y1={height} x2={slope * 2} y2={0} stroke="currentColor" strokeWidth={stroke} />
      <line
        x1={slope * 2 + stroke * 1.6}
        y1={height}
        x2={slope * 3 + stroke * 1.6}
        y2={0}
        stroke="currentColor"
        strokeWidth={stroke}
      />
    </svg>
  );
}

/** Section divider: a hairline with the cuts sitting on it. */
export function CutsDivider({ className = "" }: { className?: string }) {
  return (
    <div className={`container-site ${className}`} aria-hidden="true">
      <div className="flex items-center gap-4">
        <div className="h-px flex-1 bg-ink/10" />
        <Cuts className="text-sun" height={16} stroke={4} />
        <div className="h-px flex-1 bg-ink/10" />
      </div>
    </div>
  );
}
