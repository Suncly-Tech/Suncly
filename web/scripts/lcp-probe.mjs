// Records every LCP candidate under mobile throttling so we can see which paint
// becomes the final LCP and when. Usage: node scripts/lcp-probe.mjs [url]
import { chromium } from "playwright";

const url = process.argv[2] ?? "http://localhost:3100/";
const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: 412, height: 823 },
  deviceScaleFactor: 1.75,
  isMobile: true,
});
const page = await context.newPage();
const cdp = await context.newCDPSession(page);
await cdp.send("Network.enable");
await cdp.send("Network.emulateNetworkConditions", {
  offline: false,
  latency: 150,
  downloadThroughput: (1.6 * 1024 * 1024) / 8,
  uploadThroughput: (750 * 1024) / 8,
});
await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });

await page.addInitScript(() => {
  window.__lcp = [];
  new PerformanceObserver((list) => {
    for (const e of list.getEntries()) {
      const el = e.element;
      window.__lcp.push({
        t: Math.round(e.startTime),
        size: e.size,
        tag: el?.tagName,
        text: (el?.textContent ?? "").trim().slice(0, 50),
        url: e.url || "",
      });
    }
  }).observe({ type: "largest-contentful-paint", buffered: true });
});

await page.goto(url, { waitUntil: "load" });
await page.waitForTimeout(6000);

const lcp = await page.evaluate(() => window.__lcp);
const resources = await page.evaluate(() =>
  performance
    .getEntriesByType("resource")
    .map((r) => ({ name: r.name.split("/").slice(-1)[0].slice(0, 40), start: Math.round(r.startTime), end: Math.round(r.responseEnd), size: r.transferSize }))
    .sort((a, b) => a.end - b.end),
);
const nav = await page.evaluate(() => {
  const n = performance.getEntriesByType("navigation")[0];
  return { ttfb: Math.round(n.responseStart), domContentLoaded: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd), html: n.transferSize };
});
const paint = await page.evaluate(() => performance.getEntriesByType("paint").map((p) => `${p.name}=${Math.round(p.startTime)}`));

console.log("nav", nav, paint.join(" "));
console.log("LCP candidates:");
for (const c of lcp) console.log(`  ${String(c.t).padStart(5)}ms size=${c.size} <${c.tag}> ${c.text} ${c.url}`);
console.log("resources (by end):");
for (const r of resources) console.log(`  ${String(r.end).padStart(5)}ms  start=${String(r.start).padStart(5)}  ${String(r.size).padStart(7)}B  ${r.name}`);

await browser.close();
