/**
 * Hand-built SVG diagrams for the four product sections.
 * Palette: sky, sun, ink, cream, signal; results in pass/partial/fail.
 */

const SKY = "#3461D1";
const SUN = "#F2C14E";
const INK = "#16171C";
const CREAM = "#FBF6EC";
const PAPER = "#FFFFFF";
const SIGNAL = "#E8662B";
const PASS = "#1F7A4D";
const FAIL = "#C2371F";
const PARTIAL = "#8A5A0B";
const LINE = "rgba(22,23,28,0.14)";

const frame = { width: 560, height: 360 };

function Base({ children, title }: { children: React.ReactNode; title: string }) {
  return (
    <svg
      viewBox={`0 0 ${frame.width} ${frame.height}`}
      role="img"
      aria-label={title}
      className="h-auto w-full"
      fontFamily="var(--font-sans)"
    >
      <title>{title}</title>
      {children}
    </svg>
  );
}

function Mark({ x, y, size }: { x: number; y: number; size: number }) {
  const id = `m-${x}-${y}`;
  return (
    <g transform={`translate(${x} ${y}) scale(${size / 120})`}>
      <defs>
        <mask id={id} maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120">
          <rect width="120" height="120" fill="#fff" />
          <polygon points="20,120 30,120 70,0 60,0" fill="#000" />
          <polygon points="50,120 60,120 100,0 90,0" fill="#000" />
        </mask>
      </defs>
      <circle cx="60" cy="60" r="44" fill={SUN} mask={`url(#${id})`} />
    </g>
  );
}

function Pill({
  x,
  y,
  kind,
}: {
  x: number;
  y: number;
  kind: "pass" | "partial" | "fail";
}) {
  const color = kind === "pass" ? PASS : kind === "fail" ? FAIL : PARTIAL;
  const bg = kind === "pass" ? "#E6F4EC" : kind === "fail" ? "#FDEBE7" : "#FBF1DC";
  const w = kind === "partial" ? 62 : 48;
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width={w} height="22" rx="11" fill={bg} />
      <text x={w / 2} y="15" fontSize="12" fontWeight="600" textAnchor="middle" fill={color}>
        {kind}
      </text>
    </g>
  );
}

function Arrow({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  return (
    <g stroke={INK} strokeOpacity="0.45" strokeWidth="2" fill="none" strokeLinecap="round">
      <path d={`M${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`} />
      <path d={`M${x2 - 8} ${y2 - 6} L${x2} ${y2} L${x2 - 8} ${y2 + 6}`} />
    </g>
  );
}

/** 01 Attest: the Agent Card's claims become a list of tested results. */
export function AttestDiagram() {
  const rows = [
    { label: "skills.reconcile-invoices", kind: "pass" as const },
    { label: "skills.export-report", kind: "pass" as const },
    { label: "capabilities.streaming", kind: "partial" as const },
    { label: "capabilities.pushNotifications", kind: "fail" as const },
  ];
  return (
    <Base title="An Agent Card's claims flow into a tested list of pass, partial and fail results">
      {/* Agent card */}
      <g transform="translate(36 48)">
        <rect width="190" height="264" rx="16" fill={PAPER} stroke={LINE} />
        <text x="20" y="34" fontSize="12" fontWeight="600" fill={INK} fillOpacity="0.55">
          agent-card.json
        </text>
        <rect x="20" y="52" width="150" height="2" fill={LINE} />
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <rect
            key={i}
            x="20"
            y={70 + i * 26}
            width={i % 3 === 0 ? 110 : i % 3 === 1 ? 140 : 90}
            height="10"
            rx="5"
            fill={i < 2 ? SKY : INK}
            fillOpacity={i < 2 ? 0.9 : 0.14}
          />
        ))}
        <text x="20" y="252" fontSize="11" fill={INK} fillOpacity="0.5">
          skills · capabilities
        </text>
      </g>

      <Arrow x1={232} y1={180} x2={282} y2={180} />
      <Mark x={238} y={120} size={40} />

      {/* Results */}
      <g transform="translate(292 48)">
        <rect width="232" height="264" rx="16" fill={CREAM} stroke={LINE} />
        <text x="20" y="34" fontSize="12" fontWeight="600" fill={INK} fillOpacity="0.55">
          attestation.json
        </text>
        {rows.map((r, i) => (
          <g key={r.label} transform={`translate(20 ${58 + i * 52})`}>
            <text y="14" fontSize="11.5" fontFamily="var(--font-mono)" fill={INK}>
              {r.label}
            </text>
            <Pill x={0} y={22} kind={r.kind} />
          </g>
        ))}
      </g>
    </Base>
  );
}

/** 02 Stress-test: normal and adversarial inputs hit the agent; outcomes are counted. */
export function StressDiagram() {
  const cols = 9;
  const rowsN = 5;
  const adversarial = new Set([3, 7, 12, 16, 21, 25, 30, 34, 38, 41]);
  return (
    <Base title="A stream of normal and adversarial inputs enters the agent and comes out as counted outcomes">
      {/* Inputs grid */}
      <g transform="translate(36 70)">
        {Array.from({ length: cols * rowsN }).map((_, i) => {
          const c = i % cols;
          const r = Math.floor(i / cols);
          const adv = adversarial.has(i);
          return (
            <g key={i} transform={`translate(${c * 22} ${r * 26})`}>
              {adv ? (
                <path d="M8 0 L16 14 L0 14 Z" fill={SIGNAL} />
              ) : (
                <circle cx="8" cy="7" r="6" fill={SKY} fillOpacity="0.85" />
              )}
            </g>
          );
        })}
        <g transform="translate(0 150)" fontSize="11.5" fill={INK} fillOpacity="0.6">
          <circle cx="6" cy="-4" r="5" fill={SKY} />
          <text x="18" y="0">
            normal
          </text>
          <path d="M84 -10 L92 2 L76 2 Z" fill={SIGNAL} />
          <text x="98" y="0">
            adversarial
          </text>
        </g>
      </g>

      <Arrow x1={238} y1={130} x2={276} y2={130} />

      {/* Agent */}
      <g transform="translate(284 84)">
        <rect width="96" height="96" rx="20" fill={PAPER} stroke={LINE} />
        <Mark x={28} y={28} size={40} />
        <text x="48" y="124" fontSize="12" textAnchor="middle" fill={INK} fillOpacity="0.6">
          your agent
        </text>
      </g>

      <Arrow x1={388} y1={130} x2={424} y2={130} />

      {/* Outcome bins */}
      <g transform="translate(430 56)">
        {[
          { label: "ok", kind: PASS, w: 86 },
          { label: "timeout", kind: PARTIAL, w: 28 },
          { label: "crash", kind: FAIL, w: 0 },
        ].map((b, i) => (
          <g key={b.label} transform={`translate(0 ${i * 52})`}>
            <text y="12" fontSize="12" fill={INK} fillOpacity="0.6">
              {b.label}
            </text>
            <rect y="20" width="94" height="12" rx="6" fill={INK} fillOpacity="0.08" />
            {b.w > 0 && <rect y="20" width={b.w} height="12" rx="6" fill={b.kind} />}
          </g>
        ))}
      </g>

      <text x="280" y="320" fontSize="12" fill={INK} fillOpacity="0.5" textAnchor="middle">
        every crash, timeout and wrong answer is recorded
      </text>
    </Base>
  );
}

/** 03 Gate: only agents with a signed attestation pass into your network. */
export function GateDiagram() {
  return (
    <Base title="Agents approach a gate; those with a signed attestation pass into your network, one without is held">
      {/* Network */}
      <g transform="translate(330 44)">
        <rect width="194" height="272" rx="20" fill={SKY} fillOpacity="0.08" stroke={SKY} strokeOpacity="0.35" strokeDasharray="6 6" />
        <text x="97" y="30" fontSize="12" fontWeight="600" textAnchor="middle" fill={SKY}>
          your network
        </text>
        {[
          [52, 92],
          [142, 120],
          [78, 196],
          [150, 232],
        ].map(([x, y], i) => (
          <g key={i} transform={`translate(${x} ${y})`}>
            <circle r="18" fill={PAPER} stroke={LINE} />
            <Mark x={-9} y={-9} size={18} />
          </g>
        ))}
      </g>

      {/* Gate */}
      <g transform="translate(286 44)">
        <rect width="4" height="272" rx="2" fill={INK} fillOpacity="0.8" />
        <rect x="-6" y="118" width="16" height="36" rx="4" fill={SUN} />
      </g>

      {/* Approaching agents */}
      <g transform="translate(40 96)">
        {/* attested, passing */}
        <g>
          <circle cx="40" cy="30" r="22" fill={PAPER} stroke={LINE} />
          <Mark x={29} y={19} size={22} />
          <g transform="translate(54 44)">
            <circle r="9" fill={PASS} />
            <path d="M-4 0 L-1 3 L4 -3" stroke={PAPER} strokeWidth="2" fill="none" strokeLinecap="round" />
          </g>
          <Arrow x1={72} y1={30} x2={236} y2={30} />
        </g>
        {/* attested, passing */}
        <g transform="translate(0 86)">
          <circle cx="40" cy="30" r="22" fill={PAPER} stroke={LINE} />
          <Mark x={29} y={19} size={22} />
          <g transform="translate(54 44)">
            <circle r="9" fill={PASS} />
            <path d="M-4 0 L-1 3 L4 -3" stroke={PAPER} strokeWidth="2" fill="none" strokeLinecap="round" />
          </g>
          <Arrow x1={72} y1={30} x2={236} y2={30} />
        </g>
        {/* not attested, held */}
        <g transform="translate(0 172)">
          <circle cx="40" cy="30" r="22" fill={PAPER} stroke={LINE} />
          <circle cx="40" cy="30" r="9" fill={INK} fillOpacity="0.12" />
          <g transform="translate(54 44)">
            <circle r="9" fill={FAIL} />
            <path d="M-3 -3 L3 3 M3 -3 L-3 3" stroke={PAPER} strokeWidth="2" strokeLinecap="round" />
          </g>
          <g stroke={INK} strokeOpacity="0.3" strokeWidth="2" strokeDasharray="4 6" strokeLinecap="round">
            <path d="M72 30 L190 30" />
          </g>
          <text x="140" y="56" fontSize="11.5" fill={INK} fillOpacity="0.55">
            no attestation
          </text>
        </g>
      </g>
    </Base>
  );
}

/** 04 Approve: a signed report moves from builder to approver and is verified. */
export function ApproveDiagram() {
  return (
    <Base title="A signed attestation report travels from the builder to the approver, who verifies the signature">
      {/* Builder */}
      <g transform="translate(36 128)">
        <rect width="120" height="104" rx="16" fill={PAPER} stroke={LINE} />
        <text x="60" y="48" fontSize="12" fontWeight="600" textAnchor="middle" fill={INK}>
          builder
        </text>
        <text x="60" y="68" fontSize="11" textAnchor="middle" fill={INK} fillOpacity="0.55">
          runs suncly
        </text>
      </g>

      <Arrow x1={162} y1={180} x2={208} y2={180} />

      {/* Report */}
      <g transform="translate(214 74)">
        <rect width="134" height="212" rx="16" fill={CREAM} stroke={LINE} />
        <text x="18" y="30" fontSize="11" fontWeight="600" fill={INK} fillOpacity="0.55">
          attestation.json
        </text>
        {[0, 1, 2, 3].map((i) => (
          <g key={i} transform={`translate(18 ${46 + i * 24})`}>
            <rect width="62" height="8" rx="4" fill={INK} fillOpacity="0.14" />
            <circle
              cx="90"
              cy="4"
              r="5"
              fill={i === 2 ? PARTIAL : i === 3 ? FAIL : PASS}
            />
          </g>
        ))}
        {/* Signature seal */}
        <g transform="translate(67 172)">
          <circle r="26" fill={SUN} />
          <circle r="26" fill="none" stroke={INK} strokeOpacity="0.2" strokeDasharray="3 3" />
          <path d="M-9 1 L-3 7 L10 -7" stroke={INK} strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <text x="67" y="206" fontSize="10.5" textAnchor="middle" fill={INK} fillOpacity="0.55">
          signed
        </text>
      </g>

      <Arrow x1={354} y1={180} x2={400} y2={180} />

      {/* Approver */}
      <g transform="translate(406 128)">
        <rect width="120" height="104" rx="16" fill={PAPER} stroke={LINE} />
        <text x="60" y="44" fontSize="12" fontWeight="600" textAnchor="middle" fill={INK}>
          approver
        </text>
        <g transform="translate(60 70)">
          <rect x="-44" y="-11" width="88" height="22" rx="11" fill="#E6F4EC" />
          <text y="4" fontSize="11" fontWeight="600" textAnchor="middle" fill={PASS}>
            verified
          </text>
        </g>
      </g>
    </Base>
  );
}
