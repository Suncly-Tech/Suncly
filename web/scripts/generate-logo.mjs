// Derives web-ready logo lockups from the brand files in ../assets:
//   public/brand/logo-light.webp  white wordmark + yellow mark, transparent (for blue/ink surfaces)
//   public/brand/logo-dark.webp   ink wordmark + yellow mark, transparent (for cream/paper surfaces)
//   public/og.png                the lockup on the brand blue, 1200x630
// Source: assets/suncly-black.png (white + yellow on pure black), keyed on luminance.
import sharp from "sharp";
import { writeFileSync } from "node:fs";

const SRC = new URL("../../assets/suncly-black.png", import.meta.url).pathname;
const INK = [22, 23, 28];
const OG_BLUE = { r: 43, g: 102, b: 209 }; // sampled from assets/suncly-blue.png

const { data, info } = await sharp(SRC).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
const light = Buffer.alloc(data.length);
const dark = Buffer.alloc(data.length);

for (let i = 0; i < data.length; i += 4) {
  const r = data[i], g = data[i + 1], b = data[i + 2];
  let a = Math.max(r, g, b); // on black, coverage == brightest channel
  if (a < 28) continue; // drop faint noise from the upscaled source
  if (a > 236) a = 255; // snap near-solid pixels so the alpha channel compresses well
  const yellow = r - b > 60; // mark pixels; everything else is the wordmark
  // un-premultiply against black
  const ur = Math.min(255, Math.round((r * 255) / a));
  const ug = Math.min(255, Math.round((g * 255) / a));
  const ub = Math.min(255, Math.round((b * 255) / a));
  light[i] = ur; light[i + 1] = ug; light[i + 2] = ub; light[i + 3] = a;
  if (yellow) { dark[i] = ur; dark[i + 1] = ug; dark[i + 2] = ub; }
  else { dark[i] = INK[0]; dark[i + 1] = INK[1]; dark[i + 2] = INK[2]; }
  dark[i + 3] = a;
}

const raw = { raw: { width: info.width, height: info.height, channels: 4 } };
const make = (buf) => sharp(buf, raw).trim({ threshold: 8 }).png();

const lightTrim = await make(light).toBuffer({ resolveWithObject: true });
const W = 384;
const H = Math.round((lightTrim.info.height / lightTrim.info.width) * W);
await sharp(lightTrim.data).resize(W, H, { fit: "fill" }).webp({ quality: 86, alphaQuality: 90 }).toFile("public/brand/logo-light.webp");
const darkTrim = await make(dark).toBuffer();
await sharp(darkTrim).resize(W, H, { fit: "fill" }).webp({ quality: 86, alphaQuality: 90 }).toFile("public/brand/logo-dark.webp");

// OG: lockup centred on the brand blue
const ogW = 1200, ogH = 630, lockW = 760;
const lock = await sharp(lightTrim.data).resize(lockW).png().toBuffer();
const lockMeta = await sharp(lock).metadata();
await sharp({ create: { width: ogW, height: ogH, channels: 4, background: OG_BLUE } })
  .composite([{ input: lock, left: Math.round((ogW - lockW) / 2), top: Math.round((ogH - lockMeta.height) / 2) }])
  .png()
  .toFile("public/og.png");

writeFileSync("public/brand/logo.json", JSON.stringify({ width: W, height: H, aspect: +(W / H).toFixed(4) }, null, 2) + "\n");
console.log("lockup", lightTrim.info.width + "x" + lightTrim.info.height, "->", W + "x" + H, "og", ogW + "x" + ogH);
