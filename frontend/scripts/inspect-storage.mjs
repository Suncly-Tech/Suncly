// Inspects the built site in a browser: every cookie, every storage key and every network
// request host, across the public pages and the workspace with the sample loaded. The
// cookie table on /cookies and the Privacy Policy are generated from this result.
// Usage: node scripts/inspect-storage.mjs [baseUrl]
import { chromium } from "playwright";
import { existsSync } from "node:fs";

const base = process.argv[2] ?? "http://localhost:3100";
const origin = new URL(base).host;
const PAGES = ["/", "/offer", "/certified", "/data", "/research", "/lab", "/product", "/demo", "/security", "/docs", "/privacy", "/terms", "/cookies", "/legal", "/app", "/app/settings"];
const browser = await chromium.launch({ executablePath: existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined });
const context = await browser.newContext();
const page = await context.newPage();
const hosts = new Set();
page.on("request", (r) => hosts.add(new URL(r.url()).host));
for (const path of PAGES) await page.goto(base + path, { waitUntil: "networkidle" });
const before = await page.evaluate(() => ({ local: Object.keys(localStorage), session: Object.keys(sessionStorage) }));
// load the sample into the workspace, the one action that stores anything
await page.goto(base + "/demo", { waitUntil: "networkidle" });
const loadButton = page.getByRole("button", { name: /load sample/i }).first();
if (await loadButton.count()) {
  await loadButton.click();
  await page.waitForTimeout(500);
}
const after = await page.evaluate(() => ({ local: Object.keys(localStorage).map((k) => `${k} (${(localStorage.getItem(k) ?? "").length} chars)`), session: Object.keys(sessionStorage) }));
const cookies = await context.cookies();
await browser.close();
console.log("cookies:", cookies.length ? cookies.map((c) => `${c.name} (${c.domain})`).join(", ") : "none");
console.log("localStorage before any action:", before.local.length ? before.local.join(", ") : "none");
console.log("sessionStorage:", after.session.length ? after.session.join(", ") : "none");
console.log("localStorage after loading the sample into the workspace:", after.local.length ? after.local.join(", ") : "none");
const third = [...hosts].filter((h) => h !== origin);
console.log("request hosts:", [...hosts].join(", "));
console.log("third-party hosts:", third.length ? third.join(", ") : "none");
process.exit(cookies.length || third.length ? 1 : 0);
