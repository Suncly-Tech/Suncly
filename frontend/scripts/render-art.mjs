// Render the picture set from frontend/art/<name>/scene.svg to public/art/ as AVIF and
// WebP at three widths, plus the badge PNGs. Every picture can be made again from its
// scene file. Usage, from frontend/:  node scripts/render-art.mjs [name...]
import sharp from "sharp";
import { readdirSync, readFileSync, mkdirSync, existsSync, statSync } from "node:fs";
import { resolve, join } from "node:path";

const root = resolve(import.meta.dirname, "..");
const artDir = join(root, "art");
const outDir = join(root, "public/art");
mkdirSync(outDir, { recursive: true });

const WIDTHS = [640, 1280, 1920];
const only = process.argv.slice(2);
const names = readdirSync(artDir).filter((n) => statSync(join(artDir, n)).isDirectory() && existsSync(join(artDir, n, "scene.svg")));

for (const name of names) {
  if (only.length && !only.includes(name)) continue;
  const svg = readFileSync(join(artDir, name, "scene.svg"));
  const meta = await sharp(svg).metadata();
  for (const w of WIDTHS) {
    const density = Math.max(72, Math.ceil((w / (meta.width ?? 1000)) * 72));
    const base = sharp(svg, { density }).resize({ width: w });
    const webp = await base.clone().webp({ quality: 82, effort: 5 }).toBuffer();
    const avif = await base.clone().avif({ quality: 56, effort: 6 }).toBuffer();
    await sharp(webp).toFile(join(outDir, `${name}-${w}.webp`));
    await sharp(avif).toFile(join(outDir, `${name}-${w}.avif`));
    console.log(name, w, `webp ${(webp.length / 1024).toFixed(0)} KB`, `avif ${(avif.length / 1024).toFixed(0)} KB`);
  }
}

// Badge PNGs from the generated SVGs.
const badgeDir = join(root, "public/brand/badge");
if (existsSync(badgeDir)) {
  for (const f of readdirSync(badgeDir).filter((f) => f.endsWith(".svg"))) {
    for (const size of [64, 128, 256, 512]) {
      const out = join(badgeDir, f.replace(".svg", `-${size}.png`));
      await sharp(readFileSync(join(badgeDir, f)), { density: Math.ceil((size / 512) * 72 * 2) }).resize(size, size).png().toFile(out);
    }
    console.log("badge", f, "-> 64/128/256/512 png");
  }
}
