// Runs Lighthouse (mobile and desktop) against a served build and prints the four scores.
// Usage: node scripts/lighthouse.mjs [baseUrl]   (default http://localhost:3100)
import lighthouse from "lighthouse";
import { launch } from "chrome-launcher";
import { mkdirSync, writeFileSync } from "node:fs";

const base = process.argv[2] ?? "http://localhost:3100";
const outDir = new URL("../lighthouse/", import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const chrome = await launch({ chromeFlags: ["--headless=new", "--no-sandbox"] });
const cats = ["performance", "accessibility", "best-practices", "seo"];
const results = {};

for (const preset of ["mobile", "desktop"]) {
  for (const path of ["/", "/docs"]) {
    const flags = { logLevel: "error", output: ["html", "json"], onlyCategories: cats, port: chrome.port };
    const config =
      preset === "desktop"
        ? { extends: "lighthouse:default", settings: { formFactor: "desktop", screenEmulation: { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1, disabled: false }, throttling: { rttMs: 40, throughputKbps: 10240, cpuSlowdownMultiplier: 1 } } }
        : undefined;
    const run = await lighthouse(base + path, flags, config);
    const name = `${preset}${path === "/" ? "-home" : "-docs"}`;
    writeFileSync(`${outDir}${name}.html`, run.report[0]);
    writeFileSync(`${outDir}${name}.json`, run.report[1]);
    const scores = Object.fromEntries(cats.map((c) => [c, Math.round(run.lhr.categories[c].score * 100)]));
    results[name] = scores;
    const audits = Object.values(run.lhr.audits).filter((a) => a.score !== null && a.score < 1 && a.scoreDisplayMode !== "informative");
    console.log(name, scores);
    for (const a of audits.slice(0, 12)) console.log(`   ${a.score} ${a.id}: ${a.title}`);
  }
}

await chrome.kill();
writeFileSync(`${outDir}scores.json`, JSON.stringify(results, null, 2));
console.log("\nSummary:", JSON.stringify(results));
