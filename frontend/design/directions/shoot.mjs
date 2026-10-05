// Screenshots of the three art-direction drafts at 1440 and 390 px, plus a comparison board.
// Usage: node design/directions/shoot.mjs   (from frontend/)
import { chromium } from "playwright";
import sharp from "sharp";
import { mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const dir = resolve("design/directions");
mkdirSync(`${dir}/shots`, { recursive: true });
const pages = ["a-daylight", "b-instrument", "c-print"];
const widths = [1440, 390];
const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
const out = {};
for (const name of pages) {
  for (const width of widths) {
    const ctx = await browser.newContext({ viewport: { width, height: width < 768 ? 844 : 900 }, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(`file://${dir}/${name}.html`, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    const hero = `${dir}/shots/${name}-${width}-hero.png`;
    await page.screenshot({ path: hero, fullPage: false });
    const full = `${dir}/shots/${name}-${width}-full.png`;
    await page.screenshot({ path: full, fullPage: true });
    out[`${name}-${width}`] = { hero, full };
    if (errors.length) console.log(name, width, "page errors:", errors);
    await ctx.close();
  }
}
await browser.close();

// Board: one row per direction; desktop full page scaled to 720 wide, phone full page scaled to 240 wide.
const rows = [];
for (const name of pages) {
  const d = await sharp(out[`${name}-1440`].full).resize({ width: 720 }).png().toBuffer();
  const p = await sharp(out[`${name}-390`].full).resize({ width: 240 }).png().toBuffer();
  const dm = await sharp(d).metadata();
  const pm = await sharp(p).metadata();
  const h = Math.max(dm.height, pm.height);
  const row = await sharp({ create: { width: 1000, height: h + 40, channels: 4, background: "#E9E3D6" } })
    .composite([{ input: d, left: 20, top: 20 }, { input: p, left: 760, top: 20 }])
    .png().toBuffer();
  rows.push(row);
}
let top = 0; const comps = []; let total = 0;
for (const r of rows) { const m = await sharp(r).metadata(); comps.push({ input: r, left: 0, top }); top += m.height; total = top; }
await sharp({ create: { width: 1000, height: total, channels: 4, background: "#E9E3D6" } }).composite(comps).png().toFile(`${dir}/board.png`);
console.log("board written", total);
