// Runs axe-core (WCAG 2.2 AA rules) on every public page at desktop and phone width.
// Usage: node scripts/axe.mjs [baseUrl]
import { chromium } from "playwright";
import { createRequire } from "node:module";
import { existsSync } from "node:fs";

const require = createRequire(import.meta.url);
const axeSource = require("fs").readFileSync(
  require.resolve("axe-core/axe.min.js"),
  "utf8",
);
const base = process.argv[2] ?? "http://localhost:3100";
const PAGES = [
  "/",
  "/offer",
  "/certified",
  "/certified/policy",
  "/certified/specimen",
  "/data",
  "/research",
  "/lab",
  "/product",
  "/workflows",
  "/demo",
  "/security",
  "/docs",
  "/docs/getting-started",
  "/docs/cli",
  "/docs/evidence",
  "/company",
  "/access",
  "/glossary",
  "/privacy",
  "/terms",
  "/cookies",
  "/legal",
  "/app",
];
const browser = await chromium.launch({
  executablePath: existsSync("/opt/pw-browsers/chromium")
    ? "/opt/pw-browsers/chromium"
    : undefined,
});
let total = 0;
for (const width of [1440, 390]) {
  const page = await browser.newPage({
    viewport: { width, height: width < 768 ? 844 : 900 },
  });
  for (const path of PAGES) {
    await page.goto(base + path, { waitUntil: "networkidle" });
    await page.addScriptTag({ content: axeSource });
    const results = await page.evaluate(
      async () =>
        await window.axe.run(document, {
          runOnly: {
            type: "tag",
            values: [
              "wcag2a",
              "wcag2aa",
              "wcag21a",
              "wcag21aa",
              "wcag22aa",
              "best-practice",
            ],
          },
        }),
    );
    const serious = results.violations.filter(
      (v) =>
        v.impact === "serious" ||
        v.impact === "critical" ||
        v.impact === "moderate",
    );
    total += serious.length;
    console.log(
      `${path} ${width}: ${results.violations.length} violation(s), ${serious.length} moderate or worse`,
    );
    for (const v of serious)
      console.log(
        `   ${v.id} (${v.impact}): ${v.help} · ${v.nodes.length} node(s) · ${v.nodes[0]?.target?.join(" ")}`,
      );
  }
  await page.close();
}
await browser.close();
process.exit(total ? 1 : 0);
