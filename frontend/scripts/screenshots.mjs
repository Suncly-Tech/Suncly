// Full-page screenshots of every public page at 1440, 1024, 768 and 390 px, plus the open
// mobile menu, written to screenshots/<page>-<width>.png and 1000px tiles for review.
// Usage: node scripts/screenshots.mjs [baseUrl] [--pages=/,/offer] [--widths=1440,390]
import { chromium } from "playwright";
import { mkdirSync, existsSync } from "node:fs";
import sharp from "sharp";

const args = process.argv.slice(2);
const base = args.find((a) => !a.startsWith("--")) ?? "http://localhost:3100";
const opt = (name, fallback) => {
  const a = args.find((x) => x.startsWith(`--${name}=`));
  return a ? a.slice(name.length + 3).split(",") : fallback;
};
const ALL_PAGES = [
  "/", "/offer", "/certified", "/certified/policy", "/data", "/research", "/lab", "/product", "/workflows", "/demo",
  "/security", "/docs", "/docs/getting-started", "/docs/cli", "/docs/evidence", "/company", "/access", "/glossary",
  "/privacy", "/terms", "/cookies", "/legal", "/app", "/app/new", "/app/settings",
];
const pages = opt("pages", ALL_PAGES);
const widths = opt("widths", ["1440", "1024", "768", "390"]).map(Number);
const outDir = new URL("../screenshots/", import.meta.url).pathname;
const tileDir = `${outDir}tiles/`;
mkdirSync(tileDir, { recursive: true });

const TILE = 1000;
const executablePath = existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined;
const browser = await chromium.launch({ executablePath });
const stem = (path) => (path === "/" ? "home" : path.replace(/^\//, "").replace(/\//g, "-"));

async function captureFull(page, width, name) {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const tiles = [];
  for (let y = 0, i = 0; y < height; y += TILE, i++) {
    const h = Math.min(TILE, height - y);
    const buf = await page.screenshot({ fullPage: true, clip: { x: 0, y, width, height: h } });
    await sharp(buf).toFile(`${tileDir}${name}-${String(i).padStart(2, "0")}.png`);
    tiles.push({ input: buf, top: y, left: 0 });
  }
  await sharp({ create: { width, height, channels: 4, background: "#FAF7F0" } }).composite(tiles).png().toFile(`${outDir}${name}.png`);
  return height;
}

const report = [];
for (const width of widths) {
  const context = await browser.newContext({ viewport: { width, height: width < 768 ? 844 : 900 }, deviceScaleFactor: 1, reducedMotion: "no-preference" });
  const page = await context.newPage();
  for (const path of pages) {
    const errors = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));
    const res = await page.goto(base + path, { waitUntil: "networkidle" });
    if (!res || res.status() >= 400) {
      report.push(`${path} ${width}: HTTP ${res?.status()}`);
      continue;
    }
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0; y < height; y += 600) {
      await page.evaluate((v) => window.scrollTo({ top: v, behavior: "instant" }), y);
      await page.waitForTimeout(60);
    }
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.waitForTimeout(500);
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    const h = await captureFull(page, width, `${stem(path)}-${width}`);
    report.push(`${path} ${width}: ${h}px tall${scrollWidth > width ? ` OVERFLOW ${scrollWidth}` : ""}${errors.length ? ` errors: ${errors.join(" | ")}` : ""}`);
    if (path === "/" && width < 1024) {
      await page.click('button[aria-controls="mobile-menu"]');
      await page.waitForTimeout(300);
      await page.screenshot({ path: `${outDir}home-${width}-menu.png` });
      await page.keyboard.press("Escape");
    }
  }
  await context.close();
}
await browser.close();
console.log(report.join("\n"));
