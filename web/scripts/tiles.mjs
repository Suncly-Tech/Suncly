// Slice a tall full-page screenshot into viewport-height tiles for review.
// Usage: node scripts/tiles.mjs screenshots/home-390.png 900
import sharp from "sharp";
import { basename, dirname, join } from "node:path";
import { mkdirSync } from "node:fs";

const [file, tileH = "900"] = process.argv.slice(2);
const h = Number(tileH);
const img = sharp(file);
const meta = await img.metadata();
const out = join(dirname(file), "tiles");
mkdirSync(out, { recursive: true });
const stem = basename(file, ".png");
let i = 0;
for (let y = 0; y < meta.height; y += h) {
  const height = Math.min(h, meta.height - y);
  await sharp(file).extract({ left: 0, top: y, width: meta.width, height }).toFile(`${out}/${stem}-${String(i).padStart(2, "0")}.png`);
  i++;
}
console.log(`${file}: ${i} tiles of ${meta.width}x${h}`);
