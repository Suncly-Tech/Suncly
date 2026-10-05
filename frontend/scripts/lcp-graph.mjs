// Why Lighthouse's simulated LCP is what it is. Runs Lighthouse (mobile, simulated
// throttling) on one page, then asks Lighthouse's own Lantern model for the optimistic and
// pessimistic LCP graphs it averaged, lists every network node in the pessimistic graph with
// its simulated finish time, and re-simulates the pessimistic graph with chosen resources
// removed to show what each would buy. Evidence, not a tuning tool.
// Usage: CHROME_PATH=/opt/pw-browsers/chromium node scripts/lcp-graph.mjs [url]
import lighthouse from "lighthouse";
import { launch } from "chrome-launcher";
import { LanternLargestContentfulPaint } from "lighthouse/core/computed/metrics/lantern-largest-contentful-paint.js";
import { LoadSimulator } from "lighthouse/core/computed/load-simulator.js";

const url = process.argv[2] ?? "http://localhost:3100/";
const chrome = await launch({
  chromeFlags: ["--headless=new", "--no-sandbox"],
});
const { lhr, artifacts } = await lighthouse(url, {
  logLevel: "error",
  output: "json",
  onlyCategories: ["performance"],
  port: chrome.port,
  formFactor: "mobile",
  throttlingMethod: "simulate",
  screenEmulation: {
    mobile: true,
    width: 412,
    height: 823,
    deviceScaleFactor: 1.75,
    disabled: false,
  },
});
await chrome.kill();

const settings = lhr.configSettings;
const data = {
  trace: artifacts.Trace ?? artifacts.traces?.defaultPass,
  devtoolsLog: artifacts.DevtoolsLog ?? artifacts.devtoolsLogs?.defaultPass,
  gatherContext: artifacts.GatherContext ?? { gatherMode: "navigation" },
  settings,
  URL: artifacts.URL,
  SourceMaps: artifacts.SourceMaps ?? [],
  HostDPR: artifacts.HostDPR ?? 1,
};
const context = { computedCache: new Map() };
const lcp = await LanternLargestContentfulPaint.request(data, context);
const simulator = await LoadSimulator.request(
  { devtoolsLog: data.devtoolsLog, settings },
  context,
);
const short = (u) =>
  u
    .replace(/^https?:\/\/[^/]+/, "")
    .replace(/^\/_next\/static\/(chunks|media)\//, "…/")
    .slice(0, 58);

console.log(
  `Lighthouse LCP ${Math.round(lhr.audits["largest-contentful-paint"].numericValue)} ms = 0.5 × optimistic ${Math.round(lcp.optimisticEstimate.timeInMs)} + 0.5 × pessimistic ${Math.round(lcp.pessimisticEstimate.timeInMs)} (floored at FCP); throttling ${settings.throttling.throughputKbps} Kbps, RTT ${settings.throttling.rttMs} ms, CPU ×${settings.throttling.cpuSlowdownMultiplier}`,
);
const rows = [];
for (const [node, t] of lcp.pessimisticEstimate.nodeTimings) {
  if (node.type !== "network") continue;
  rows.push({
    url: short(node.request.url),
    kb: node.request.transferSize / 1024,
    type: node.request.resourceType,
    start: t.startTime,
    end: t.endTime,
  });
}
rows.sort((a, b) => a.end - b.end);
console.log("\nPessimistic graph, network nodes (simulated ms):");
console.log("  start    end     KB  type        url");
let total = 0;
for (const r of rows) {
  total += r.kb;
  console.log(
    `${String(Math.round(r.start)).padStart(7)} ${String(Math.round(r.end)).padStart(6)} ${r.kb.toFixed(1).padStart(6)}  ${String(r.type).padEnd(10)}  ${r.url}`,
  );
}
console.log(
  `  ${rows.length} requests, ${total.toFixed(0)} KB transferred before the observed paint`,
);
const cpu = Array.from(lcp.pessimisticEstimate.nodeTimings).filter(
  ([n]) => n.type === "cpu",
);
console.log(
  `  plus ${cpu.length} CPU tasks treated as render-blocking (layout); last ends at ${Math.round(Math.max(...cpu.map(([, t]) => t.endTime)))} ms`,
);
console.log(
  "\nCPU tasks in the pessimistic graph (simulated ms; duration is the trace's × CPU slowdown):",
);
for (const [n, t] of cpu.sort((a, b) => a[1].startTime - b[1].startTime)) {
  const kinds = {};
  for (const e of n.childEvents ?? [])
    kinds[e.name] = (kinds[e.name] ?? 0) + (e.dur ?? 0) / 1000;
  const top = Object.entries(kinds)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([k, v]) => `${k} ${v.toFixed(0)}ms`)
    .join(", ");
  const urls = new Set(
    (n.childEvents ?? []).map((e) => e.args?.data?.url).filter(Boolean),
  );
  console.log(
    `${String(Math.round(t.startTime)).padStart(7)} ${String(Math.round(t.endTime)).padStart(6)}  ${(n.event?.name ?? "task").padEnd(12)} dur ${String(Math.round(n.duration ?? 0)).padStart(4)} ms raw  [${top}]${urls.size ? " " + Array.from(urls).map(short).join(" ") : ""}`,
  );
}

// What-ifs: re-simulate the pessimistic graph without a class of resources.
const graph = lcp.pessimisticGraph;
const whatIf = (label, drop) => {
  const clone = graph.cloneWithRelationships(
    (n) => !(n.type === "network" && drop(n.request)),
  );
  const sim = simulator.simulate(clone, { label });
  const pess = Math.max(
    ...Array.from(sim.nodeTimings.values()).map((t) => t.endTime),
  );
  const est = Math.max(
    0.5 * lcp.optimisticEstimate.timeInMs + 0.5 * pess,
    lhr.audits["first-contentful-paint"].numericValue,
  );
  console.log(
    `${label.padEnd(44)} pessimistic ${String(Math.round(pess)).padStart(5)} ms → simulated LCP ≈ ${Math.round(est)} ms`,
  );
};
console.log(
  "\nWhat-ifs (pessimistic graph re-simulated without the resources named; optimistic unchanged):",
);
whatIf("as built", () => false);
whatIf("without the three fonts", (r) => r.resourceType === "Font");
whatIf("without every script", (r) => r.resourceType === "Script");
whatIf(
  "without the two framework chunks only",
  (r) => r.resourceType === "Script" && r.transferSize > 50000,
);
whatIf(
  "without fonts and scripts",
  (r) => r.resourceType === "Font" || r.resourceType === "Script",
);
