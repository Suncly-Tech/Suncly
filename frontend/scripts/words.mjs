// Counts the visible words on the home page against the brief's budget (800), excluding
// navigation, code, collapsed FAQ answers, the footer and the legal line. Per-section
// counts are printed so a section over its budget is easy to find.
// Usage: node scripts/words.mjs [baseUrl]
import { chromium } from "playwright";
import { existsSync } from "node:fs";

const base = process.argv[2] ?? "http://localhost:3100";
const BUDGET = 800;
const browser = await chromium.launch({ executablePath: existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(base + "/", { waitUntil: "networkidle" });
const result = await page.evaluate(() => {
  const main = document.querySelector("main");
  const sections = Array.from(main.children);
  const count = (el) => {
    const clone = el.cloneNode(true);
    clone.querySelectorAll("pre, code, details > :not(summary), nav, script, style, [aria-hidden='true'], .sr-only, table").forEach((e) => e.remove());
    return clone.innerText.split(/\s+/).filter(Boolean).length;
  };
  return sections.map((s) => ({ id: s.id || s.getAttribute("aria-label") || s.getAttribute("aria-labelledby") || s.tagName, words: count(s) }));
});
await browser.close();
const total = result.reduce((n, s) => n + s.words, 0);
for (const s of result) console.log(String(s.words).padStart(5), s.id);
console.log(`total ${total} of ${BUDGET}`);
if (total > BUDGET) {
  console.error(`FAIL: home page has ${total} visible words; the budget is ${BUDGET}`);
  process.exit(1);
}
