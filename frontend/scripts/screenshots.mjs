// Full-page screenshots at three widths, plus the open mobile menu and /docs.
// Pages taller than Chrome's 16384px capture limit are shot in clips and stitched,
// and every page is also written as 1000px-tall tiles for review.
// Usage: node scripts/screenshots.mjs [baseUrl]   (default http://localhost:3000)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import sharp from "sharp";

const base = process.argv[2] ?? "http://localhost:3000";
const outDir = new URL("../screenshots/", import.meta.url).pathname;
const tileDir = `${outDir}tiles/`;
mkdirSync(tileDir, { recursive: true });

const TILE = 1000;
const widths = [1440, 1024, 390];
const browser = await chromium.launch({ channel: "chrome" });

async function captureFull(page, width, stem) {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  const tiles = [];
  for (let y = 0, i = 0; y < height; y += TILE, i++) {
    const h = Math.min(TILE, height - y);
    const buf = await page.screenshot({ fullPage: true, clip: { x: 0, y, width, height: h } });
    const path = `${tileDir}${stem}-${String(i).padStart(2, "0")}.png`;
    await sharp(buf).toFile(path);
    tiles.push({ input: buf, top: y, left: 0 });
  }
  await sharp({ create: { width, height, channels: 4, background: "#FBF6EC" } })
    .composite(tiles)
    .png()
    .toFile(`${outDir}${stem}.png`);
  return height;
}

for (const width of widths) {
  const context = await browser.newContext({
    viewport: { width, height: width < 768 ? 844 : 900 },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
  });
  const page = await context.newPage();
  const errors = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto(base + "/", { waitUntil: "networkidle" });
  // Scroll through so whileInView reveals have fired, then return to top.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < height; y += 500) {
    await page.evaluate((v) => window.scrollTo({ top: v, behavior: "instant" }), y);
    await page.waitForTimeout(80);
  }
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  // Let the terminal finish typing and streaming before the capture.
  await page.waitForTimeout(9000);
  const h = await captureFull(page, width, `home-${width}`);

  if (width < 768) {
    await page.click('button[aria-controls="mobile-menu"]');
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${outDir}menu-${width}.png`, fullPage: false });
    await page.keyboard.press("Escape");
  }

  await page.goto(base + "/docs", { waitUntil: "networkidle" });
  await captureFull(page, width, `docs-${width}`);

  console.log(`${width}px  height=${h}  console errors=${errors.length}`);
  for (const e of errors) console.log("   ", e);
  await context.close();
}

await browser.close();
