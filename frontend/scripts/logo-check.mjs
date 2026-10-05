// The brand mark and the badge, checked on the built site:
//  1. public/mark.svg carries exactly the path traced from the original lockup;
//  2. no page in out/ still draws the previous circular mark;
//  3. every page defines the mark once and reuses it;
//  4. the certification badge files are byte-identical to the baseline commit.
// Usage: node scripts/logo-check.mjs
import { readFileSync, readdirSync, statSync } from "node:fs";
import { execSync } from "node:child_process";
import { join } from "node:path";

const BASELINE = "dd03931"; // the last commit before the mark changed; the badge must not move
let failures = 0;
const check = (ok, msg) => { console.log(`${ok ? "ok " : "FAIL"} ${msg}`); if (!ok) failures++; };
const path = (svg) => svg.match(/<path[^>]*\sd="([^"]+)"/)[1];

const traced = path(readFileSync("design/wordmark/mark-trace.svg", "utf8"));
const shipped = path(readFileSync("public/mark.svg", "utf8"));
check(traced === shipped, "public/mark.svg is the traced bullet mark, unaltered");
const lib = readFileSync("lib/mark.ts", "utf8");
check(lib.includes(`"${traced}"`), "lib/mark.ts carries the same path");

const walk = (d) => readdirSync(d).flatMap((n) => { const p = join(d, n); return statSync(p).isDirectory() ? walk(p) : p.endsWith(".html") ? [p] : []; });
const pages = walk("out").filter((p) => !p.endsWith("404.html") && !p.includes("_not-found"));
let circular = 0, missingDef = [], multiDef = [];
for (const p of pages) {
  const html = readFileSync(p, "utf8");
  if (/suncly-cuts|banner-cuts|<circle cx="60" cy="60" r="44"/.test(html)) circular++;
  const defs = (html.match(/id="suncly-mark"/g) ?? []).length;
  if (defs === 0) missingDef.push(p); else if (defs > 1) multiDef.push(p);
}
check(circular === 0, `no page draws the previous circular mark (${pages.length} pages)`);
check(missingDef.length === 0, `every page defines the mark once${missingDef.length ? ": missing in " + missingDef.join(", ") : ""}`);
check(multiDef.length === 0, `no page defines the mark twice${multiDef.length ? ": " + multiDef.join(", ") : ""}`);

const badgeDiff = execSync(`git diff --stat ${BASELINE} -- public/brand/badge`, { encoding: "utf8" }).trim();
check(badgeDiff === "", `certification badge files are byte-identical to ${BASELINE}${badgeDiff ? "\n" + badgeDiff : ""}`);
const badgeSrc = readFileSync("design/badge/mark.svg", "utf8");
check(/r="44"/.test(badgeSrc) && readFileSync("scripts/generate-badge.py", "utf8").includes("design/badge/mark.svg"), "the badge generator reads its own circular mark, apart from the brand mark");

console.log(failures ? `${failures} failure(s)` : "logo check passed");
process.exit(failures ? 1 : 0);
