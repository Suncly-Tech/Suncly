"use client";

/**
 * Hand-built SVG diagrams. Palette: sky, sun, ink, cream, signal; verdicts in
 * pass / inconclusive (amber) / fail. Each diagram is derived from SCHEMA.md
 * and docs/ARCHITECTURE.md; see CONTENT.md for the sources.
 */

const SKY = "#3461D1";
const SUN = "#F2C14E";
const INK = "#16171C";
const CREAM = "#FBF6EC";
const PAPER = "#FFFFFF";
const SIGNAL = "#E8662B";
const PASS = "#1F7A4D";
const FAIL = "#C2371F";
const AMBER = "#8A5A0B";
const LINE = "rgba(22,23,28,0.14)";
const MUTE = "rgba(22,23,28,0.55)";

const W = 560;
const H = 360;

function Base({ children, title, viewBox = `0 0 ${W} ${H}` }: { children: React.ReactNode; title: string; viewBox?: string }) {
  return (
    <svg viewBox={viewBox} role="img" aria-label={title} className="h-auto w-full" fontFamily="var(--font-sans)">
      <title>{title}</title>
      {children}
    </svg>
  );
}

function Mark({ x, y, size, id }: { x: number; y: number; size: number; id: string }) {
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

function Box({
  x, y, w, h, label, sub, fill = PAPER, stroke = LINE, dashed = false, labelColor = INK,
}: {
  x: number; y: number; w: number; h: number; label: string; sub?: string; fill?: string; stroke?: string; dashed?: boolean; labelColor?: string;
}) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width={w} height={h} rx="12" fill={fill} stroke={stroke} strokeDasharray={dashed ? "5 5" : undefined} />
      <text x={w / 2} y={sub ? h / 2 - 3 : h / 2 + 4} fontSize="12" fontWeight="600" textAnchor="middle" fill={labelColor}>
        {label}
      </text>
      {sub ? (
        <text x={w / 2} y={h / 2 + 13} fontSize="10.5" textAnchor="middle" fill={MUTE}>
          {sub}
        </text>
      ) : null}
    </g>
  );
}

function Arrow({ x1, y1, x2, y2, color = INK, dashed = false }: { x1: number; y1: number; x2: number; y2: number; color?: string; dashed?: boolean }) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len, uy = dy / len;
  const hx = x2 - ux * 8, hy = y2 - uy * 8;
  return (
    <g stroke={color} strokeOpacity="0.5" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <line x1={x1} y1={y1} x2={x2} y2={y2} strokeDasharray={dashed ? "4 5" : undefined} />
      <path d={`M${hx - uy * 5} ${hy + ux * 5} L${x2} ${y2} L${hx + uy * 5} ${hy - ux * 5}`} />
    </g>
  );
}

function Pill({ x, y, kind }: { x: number; y: number; kind: "pass" | "fail" | "inconclusive" | "approve" | "flag" | "block" }) {
  const color = kind === "pass" || kind === "approve" ? PASS : kind === "fail" || kind === "block" ? FAIL : AMBER;
  const bg = kind === "pass" || kind === "approve" ? "#E6F4EC" : kind === "fail" || kind === "block" ? "#FDEBE7" : "#FBF1DC";
  const w = kind.length * 7 + 18;
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect width={w} height="22" rx="11" fill={bg} />
      <text x={w / 2} y="15" fontSize="12" fontWeight="600" textAnchor="middle" fill={color}>{kind}</text>
    </g>
  );
}

/** The system layout from SCHEMA.md §1. */
export function SystemDiagram() {
  return (
    <Base title="System layout: Agent Card and trigger enter the Suncly core, where contract builder, orchestrator and runner feed judge, evidence store and policy engine; the runner alone talks to the agent endpoint; outputs are registry status, CI gate and evidence report" viewBox="0 0 760 420">
      {/* Inputs */}
      <Box x={40} y={24} w={150} h={44} label="Agent Card" sub="/.well-known/agent-card.json" />
      <Box x={230} y={24} w={150} h={44} label="Trigger" sub="ci · schedule · card change · manual" />
      <Box x={560} y={24} w={160} h={44} label="Agent endpoint" sub="sandbox or dry-run" fill={CREAM} />
      <Arrow x1={115} y1={68} x2={115} y2={108} />
      <Arrow x1={305} y1={68} x2={305} y2={108} />

      {/* Core */}
      <rect x="40" y="108" width="680" height="232" rx="20" fill={PAPER} stroke={INK} strokeOpacity="0.35" />
      <text x="64" y="134" fontSize="11" fontWeight="700" letterSpacing="0.08em" fill={MUTE}>SUNCLY CORE</text>
      <Mark x={668} y={120} size={36} id="sys-mark" />

      <Box x={64} y={152} w={160} h={56} label="Contract builder" sub="model drafts · human approves" fill={CREAM} />
      <Box x={260} y={152} w={160} h={56} label="Orchestrator" sub="runs · retries · budget" fill={CREAM} />
      <Box x={456} y={152} w={160} h={56} label="Runner" sub="isolated · holds credentials" fill={SKY} stroke={SKY} labelColor={PAPER} />
      <Arrow x1={224} y1={180} x2={260} y2={180} />
      <Arrow x1={420} y1={180} x2={456} y2={180} />
      {/* Runner <-> endpoint */}
      <Arrow x1={616} y1={166} x2={640} y2={68} color={SKY} />
      <Arrow x1={660} y1={68} x2={636} y2={166} color={SKY} dashed />

      <Box x={456} y={256} w={160} h={56} label="Judge" sub="deterministic · pinned model" fill={CREAM} />
      <Box x={260} y={256} w={160} h={56} label="Evidence store" sub="append-only · signed" fill={CREAM} />
      <Box x={64} y={256} w={160} h={56} label="Policy engine" sub="approve · flag · block" fill={CREAM} />
      <Arrow x1={536} y1={208} x2={536} y2={256} />
      <Arrow x1={456} y1={284} x2={420} y2={284} />
      <Arrow x1={260} y1={284} x2={224} y2={284} />

      {/* Outputs */}
      <Arrow x1={144} y1={340} x2={144} y2={372} />
      <text x="40" y="402" fontSize="12.5" fontWeight="600" fill={INK}>
        Registry status
        <tspan fill={MUTE} fontWeight="400">  ·  </tspan>
        CI gate
        <tspan fill={MUTE} fontWeight="400">  ·  </tspan>
        Evidence report
      </text>
      <text x="420" y="402" fontSize="11" fill={MUTE}>adapters: thin, outside the core, never decide</text>
    </Base>
  );
}

/** 01 Contract: card → drafted test cases → human approval → immutable contract. */
export function ContractDiagram() {
  return (
    <Base title="An Agent Card is hashed, a model drafts test cases per skill, a human approves them, and the contract becomes an immutable version">
      <g transform="translate(28 60)">
        <rect width="140" height="200" rx="14" fill={PAPER} stroke={LINE} />
        <text x="16" y="28" fontSize="11" fontWeight="600" fill={MUTE}>agent-card.json</text>
        <rect x="16" y="42" width="108" height="2" fill={LINE} />
        {["skills[0]", "skills[1]", "skills[2]"].map((s, i) => (
          <g key={s} transform={`translate(16 ${58 + i * 34})`}>
            <rect width="108" height="24" rx="6" fill={SKY} fillOpacity="0.1" />
            <text x="10" y="16" fontSize="11" fontFamily="var(--font-mono)" fill={SKY}>{s}</text>
          </g>
        ))}
        <text x="16" y="186" fontSize="10.5" fontFamily="var(--font-mono)" fill={MUTE}>card_hash 7f3a…c1</text>
      </g>
      <Arrow x1={176} y1={160} x2={214} y2={160} />

      {/* Drafting */}
      <g transform="translate(220 60)">
        <rect width="150" height="200" rx="14" fill={CREAM} stroke={LINE} />
        <text x="16" y="28" fontSize="11" fontWeight="600" fill={MUTE}>draft · by model</text>
        {[0, 1, 2, 3, 4].map((i) => (
          <g key={i} transform={`translate(16 ${46 + i * 28})`}>
            <rect width="118" height="18" rx="5" fill={INK} fillOpacity={i < 3 ? 0.12 : 0.06} />
            <text x="8" y="13" fontSize="10" fontFamily="var(--font-mono)" fill={INK} fillOpacity="0.75">
              {i < 3 ? `test_case · skills[${i}]` : i === 3 ? "probe_injection" : "probe_failure"}
            </text>
          </g>
        ))}
      </g>

      {/* Human approval */}
      <g transform="translate(395 118)">
        <circle cx="26" cy="26" r="26" fill={SUN} />
        <circle cx="26" cy="18" r="7" fill={INK} />
        <path d="M12 42 C12 30 40 30 40 42" fill={INK} />
        <text x="26" y="72" fontSize="11" textAnchor="middle" fill={INK} fontWeight="600">human approves</text>
      </g>
      <Arrow x1={378} y1={160} x2={394} y2={150} />
      <Arrow x1={447} y1={150} x2={466} y2={160} />

      {/* Contract */}
      <g transform="translate(468 96)">
        <rect width="72" height="128" rx="12" fill={INK} />
        <text x="36" y="40" fontSize="11" fontWeight="600" textAnchor="middle" fill={PAPER}>contract</text>
        <text x="36" y="58" fontSize="13" fontFamily="var(--font-mono)" fontWeight="600" textAnchor="middle" fill={SUN}>v1</text>
        <rect x="24" y="82" width="24" height="18" rx="4" fill="none" stroke={PAPER} strokeOpacity="0.7" strokeWidth="2" />
        <path d="M29 82 V76 a7 7 0 0 1 14 0 V82" fill="none" stroke={PAPER} strokeOpacity="0.7" strokeWidth="2" />
        <text x="36" y="118" fontSize="9.5" textAnchor="middle" fill={PAPER} fillOpacity="0.6">immutable</text>
      </g>
      <text x="280" y="310" fontSize="11.5" textAnchor="middle" fill={MUTE}>a changed card is a new hash, a new draft, and a new approval</text>
    </Base>
  );
}

/** 02 Runs: test cases × repetitions against a sandbox, inside a budget. */
export function RunsDiagram() {
  const cols = 10, rows = 5;
  return (
    <Base title="Each test case is run many times against a sandbox endpoint, every run has a deterministic key, and the attestation stops at its budget">
      <g transform="translate(36 56)">
        <text y="-8" fontSize="11" fontWeight="600" fill={MUTE}>test cases × repetitions</text>
        {Array.from({ length: cols * rows }).map((_, i) => {
          const c = i % cols, r = Math.floor(i / cols);
          const idle = i >= 44;
          return (
            <rect key={i} x={c * 22} y={r * 22} width="16" height="16" rx="4" fill={idle ? INK : SKY} fillOpacity={idle ? 0.08 : 0.85} />
          );
        })}
        <text y="132" fontSize="10" fontFamily="var(--font-mono)" fill={MUTE}>run key = (attestation, test_case, attempt)</text>
      </g>
      <Arrow x1={268} y1={106} x2={312} y2={106} />

      {/* Sandbox */}
      <g transform="translate(318 44)">
        <rect width="212" height="124" rx="16" fill={CREAM} stroke={INK} strokeOpacity="0.4" strokeDasharray="5 5" />
        <text x="16" y="24" fontSize="11" fontWeight="600" fill={MUTE}>sandbox / dry-run endpoint</text>
        <rect x="56" y="40" width="100" height="64" rx="14" fill={PAPER} stroke={LINE} />
        <Mark x={86} y={52} size={40} id="runs-mark" />
        <text x="106" y="120" fontSize="10.5" textAnchor="middle" fill={MUTE}>nothing real is booked, paid or deleted</text>
      </g>

      {/* Budget */}
      <g transform="translate(36 236)">
        <text y="-8" fontSize="11" fontWeight="600" fill={MUTE}>budget_limit 25.0</text>
        <rect width="494" height="14" rx="7" fill={INK} fillOpacity="0.08" />
        <rect width="68" height="14" rx="7" fill={SKY} />
        <text x="76" y="11" fontSize="10.5" fontFamily="var(--font-mono)" fill={INK}>cost_total 3.42</text>
        <line x1="494" y1="-4" x2="494" y2="18" stroke={SIGNAL} strokeWidth="2" />
        <text x="494" y="36" fontSize="10.5" textAnchor="end" fill={SIGNAL}>stops here · no decision</text>
      </g>
      <text x="280" y="322" fontSize="11.5" textAnchor="middle" fill={MUTE}>retries reuse the run key, so nothing is counted twice</text>
    </Base>
  );
}

/** 03 Probes: three probe kinds aimed at the agent, inside the sandbox rule. */
export function ProbesDiagram() {
  const probes = [
    { k: "probe_undeclared", t: "behaviour the card does not declare" },
    { k: "probe_injection", t: "injected instructions" },
    { k: "probe_failure", t: "failure conditions" },
  ];
  return (
    <Base title="Three probe kinds, undeclared behaviour, injected instructions and failure conditions, are sent to the agent inside the sandbox, after the same human approval as skill tests">
      {probes.map((p, i) => (
        <g key={p.k} transform={`translate(28 ${56 + i * 80})`}>
          <rect width="236" height="60" rx="12" fill={PAPER} stroke={LINE} />
          <path d="M18 18 L30 30 L18 42 Z" fill={SIGNAL} />
          <text x="44" y="27" fontSize="12" fontFamily="var(--font-mono)" fontWeight="600" fill={INK}>{p.k}</text>
          <text x="44" y="44" fontSize="10.5" fill={MUTE}>{p.t}</text>
          <Arrow x1={264} y1={30} x2={318} y2={30 + (1 - i) * -0 + (i - 1) * 0} color={SIGNAL} />
        </g>
      ))}
      <g transform="translate(324 92)">
        <rect width="208" height="164" rx="16" fill={CREAM} stroke={INK} strokeOpacity="0.4" strokeDasharray="5 5" />
        <text x="16" y="24" fontSize="11" fontWeight="600" fill={MUTE}>sandbox</text>
        <rect x="54" y="48" width="100" height="72" rx="14" fill={PAPER} stroke={LINE} />
        <Mark x={84} y={64} size={40} id="probe-mark" />
        <text x="104" y="144" fontSize="10.5" textAnchor="middle" fill={MUTE}>same human approval</text>
      </g>
      <g transform="translate(28 300)">
        <rect width="504" height="30" rx="8" fill={INK} fillOpacity="0.05" />
        <text x="252" y="19" fontSize="11" textAnchor="middle" fill={MUTE}>test_case.kind: skill · probe_undeclared · probe_injection · probe_failure</text>
      </g>
    </Base>
  );
}

/** 04 Judge: transcript → Layer 1 checks → Layer 2 pinned model → verdict. */
export function JudgeDiagram() {
  const checks = ["valid schema", "final task state", "required fields", "latency limit"];
  return (
    <Base title="A transcript passes through deterministic Layer 1 checks, then a pinned model with a fixed rubric only where needed, producing a pass, fail or inconclusive verdict">
      <g transform="translate(28 100)">
        <rect width="110" height="150" rx="12" fill={PAPER} stroke={LINE} />
        <text x="14" y="24" fontSize="11" fontWeight="600" fill={MUTE}>transcript</text>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <rect key={i} x="14" y={38 + i * 17} width={i % 2 ? 60 : 82} height="8" rx="4" fill={INK} fillOpacity="0.12" />
        ))}
        <text x="14" y="140" fontSize="9.5" fill={MUTE}>redacted</text>
      </g>
      <Arrow x1={138} y1={175} x2={172} y2={175} />

      <g transform="translate(178 60)">
        <rect width="170" height="230" rx="14" fill={CREAM} stroke={LINE} />
        <text x="16" y="26" fontSize="11" fontWeight="700" fill={INK}>Layer 1 · deterministic</text>
        {checks.map((c, i) => (
          <g key={c} transform={`translate(16 ${44 + i * 32})`}>
            <circle cx="8" cy="8" r="8" fill={PASS} />
            <path d="M4.5 8 L7 10.5 L11.5 5.5" stroke={PAPER} strokeWidth="2" fill="none" strokeLinecap="round" />
            <text x="24" y="12" fontSize="11.5" fill={INK}>{c}</text>
          </g>
        ))}
        <rect x="16" y="178" width="138" height="34" rx="8" fill={INK} />
        <text x="85" y="192" fontSize="10.5" fontWeight="600" textAnchor="middle" fill={PAPER}>Layer 2 · pinned model</text>
        <text x="85" y="205" fontSize="9.5" textAnchor="middle" fill={PAPER} fillOpacity="0.6">fixed rubric · rationale stored</text>
      </g>
      <Arrow x1={348} y1={175} x2={386} y2={175} />

      <g transform="translate(392 112)">
        <text y="0" fontSize="11" fontWeight="600" fill={MUTE}>verdict per run</text>
        <Pill x={0} y={14} kind="pass" />
        <Pill x={0} y={50} kind="fail" />
        <Pill x={0} y={86} kind="inconclusive" />
        <text x="0" y="134" fontSize="10.5" fill={AMBER} fontWeight="600">never counted as a pass</text>
      </g>
    </Base>
  );
}

/** 05 Evidence: append-only ledger, signature, not-tested statement. */
export function EvidenceDiagram() {
  const rows = [
    ["run · attempt 1", "pass"],
    ["run · attempt 2", "pass"],
    ["run · attempt 3", "inconclusive"],
    ["decision · policy", "flag"],
    ["decision · reviewer", "approve"],
  ] as const;
  return (
    <Base title="An append-only evidence ledger of runs and decisions, a signature over card hash, contract version, results and transcript hashes, and a statement of what was not tested">
      <g transform="translate(28 48)">
        <rect width="300" height="236" rx="14" fill={PAPER} stroke={LINE} />
        <text x="16" y="26" fontSize="11" fontWeight="600" fill={MUTE}>evidence store · append-only</text>
        {rows.map(([label, kind], i) => (
          <g key={label} transform={`translate(16 ${42 + i * 36})`}>
            <rect width="268" height="28" rx="6" fill={CREAM} />
            <text x="12" y="18" fontSize="11" fontFamily="var(--font-mono)" fill={INK}>{label}</text>
            <Pill x={268 - (kind.length * 7 + 18) - 6} y={3} kind={kind} />
          </g>
        ))}
        <text x="16" y="226" fontSize="9.5" fill={MUTE}>records are never edited · corrections are new records</text>
      </g>

      <g transform="translate(360 48)">
        <circle cx="80" cy="60" r="44" fill={SUN} />
        <circle cx="80" cy="60" r="44" fill="none" stroke={INK} strokeOpacity="0.25" strokeDasharray="3 3" />
        <path d="M62 60 L74 72 L100 46" stroke={INK} strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <text x="80" y="124" fontSize="11" fontWeight="600" textAnchor="middle" fill={INK}>signed</text>
        {["card_hash", "contract version", "aggregated results", "transcript hashes", "decision · policy_version"].map((s, i) => (
          <text key={s} x="80" y={146 + i * 15} fontSize="10" textAnchor="middle" fill={MUTE}>{s}</text>
        ))}
      </g>

      <g transform="translate(28 300)">
        <rect width="504" height="32" rx="8" fill={INK} />
        <text x="14" y="20" fontSize="11" fontWeight="700" fill={SUN}>NOT TESTED</text>
        <text x="110" y="20" fontSize="11" fontFamily="var(--font-mono)" fill={PAPER} fillOpacity="0.85">capabilities.streaming · production endpoint</text>
      </g>
    </Base>
  );
}

/** 06 Decision: risk level × results → approve / flag / block → registry, CI, report. */
export function DecisionDiagram() {
  const risks = [
    ["low", "automatic on pass"],
    ["medium", "human on any drop"],
    ["high", "human every time"],
  ];
  const outs = ["Registry status", "CI gate", "Evidence report"];
  return (
    <Base title="The policy engine combines the agent's risk level with aggregated results into approve, flag or block, and adapters push the decision to a registry, a CI pipeline and a report">
      <g transform="translate(28 56)">
        <text y="-8" fontSize="11" fontWeight="600" fill={MUTE}>agent.risk_level</text>
        {risks.map(([r, t], i) => (
          <g key={r} transform={`translate(0 ${i * 48})`}>
            <rect width="170" height="38" rx="10" fill={PAPER} stroke={LINE} />
            <text x="12" y="17" fontSize="12" fontFamily="var(--font-mono)" fontWeight="600" fill={INK}>{r}</text>
            <text x="12" y="31" fontSize="10" fill={MUTE}>{t}</text>
          </g>
        ))}
      </g>
      <Arrow x1={198} y1={120} x2={234} y2={120} />

      <g transform="translate(240 70)">
        <rect width="120" height="100" rx="14" fill={INK} />
        <text x="60" y="44" fontSize="12" fontWeight="600" textAnchor="middle" fill={PAPER}>Policy engine</text>
        <text x="60" y="62" fontSize="10" textAnchor="middle" fill={PAPER} fillOpacity="0.6">your thresholds</text>
        <text x="60" y="76" fontSize="10" textAnchor="middle" fill={PAPER} fillOpacity="0.6">per risk level</text>
      </g>

      <g transform="translate(392 62)">
        <Pill x={0} y={0} kind="approve" />
        <Pill x={0} y={40} kind="flag" />
        <Pill x={0} y={80} kind="block" />
        <text x="76" y="55" fontSize="10" fill={MUTE}>→ human decides</text>
      </g>
      <Arrow x1={360} y1={100} x2={386} y2={78} />
      <Arrow x1={360} y1={120} x2={386} y2={118} />
      <Arrow x1={360} y1={140} x2={386} y2={158} />

      {outs.map((o, i) => (
        <g key={o} transform={`translate(${28 + i * 172} 252)`}>
          <rect width="160" height="56" rx="12" fill={CREAM} stroke={LINE} />
          <text x="80" y="25" fontSize="12" fontWeight="600" textAnchor="middle" fill={INK}>{o}</text>
          <text x="80" y="42" fontSize="10" textAnchor="middle" fill={MUTE}>
            {i === 0 ? "written by adapter" : i === 1 ? "pass or fail" : "states what was not tested"}
          </text>
        </g>
      ))}
      <Arrow x1={300} y1={170} x2={108} y2={250} />
      <Arrow x1={300} y1={170} x2={280} y2={250} />
      <Arrow x1={300} y1={170} x2={452} y2={250} />
    </Base>
  );
}
