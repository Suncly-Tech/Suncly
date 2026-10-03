// Full-page screenshots at three widths, plus the open mobile menu.
// Usage: node scripts/screenshots.mjs [baseUrl]   (default http://localhost:3000)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const base = process.argv[2] ?? "http://localhost:3000";
const outDir = new URL("../screenshots/", import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const widths = [1440, 1024, 390];
const browser = await chromium.launch({ channel: "chrome" });

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
  const height = await page.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < height; y += 600) {
    await page.evaluate((v) => window.scrollTo(0, v), y);
    await page.waitForTimeout(60);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${outDir}home-${width}.png`, fullPage: true });

  if (width < 768) {
    await page.click('button[aria-controls="mobile-menu"]');
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${outDir}menu-${width}.png`, fullPage: false });
    await page.keyboard.press("Escape");
  }

  await page.goto(base + "/docs", { waitUntil: "networkidle" });
  await page.screenshot({ path: `${outDir}docs-${width}.png`, fullPage: true });

  console.log(`${width}px  height=${height}  console errors=${errors.length}`);
  for (const e of errors) console.log("   ", e);
  await context.close();
}

await browser.close();
