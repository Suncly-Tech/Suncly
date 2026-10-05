// Derives the favicons and the social preview from public/mark.svg and the traced wordmark
// (design/wordmark/wordmark-trace.svg). The mark stays its own gold on a paper tile; no
// blue anywhere. No text is drawn, so the output never depends on a font being present.
import sharp from "sharp";
import { readFileSync, writeFileSync } from "node:fs";

const PAPER = "#FAF7F0";
const INK = "#1B1814";
const mark = readFileSync(new URL("../public/mark.svg", import.meta.url), "utf8");
const markInner = mark.replace(/<svg[^>]*>/, "").replace("</svg>", "");
const wordmark = readFileSync(new URL("../design/wordmark/wordmark-trace.svg", import.meta.url), "utf8");
const wordVb = wordmark.match(/viewBox="([^"]+)"/)[1];
const wordPath = wordmark.match(/<path d="([^"]+)"/)[1];

function tile(size, radius, pad) {
  const inner = size - pad * 2;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
  <rect width="${size}" height="${size}" rx="${radius}" fill="${PAPER}"/>
  <svg x="${pad}" y="${pad}" width="${inner}" height="${inner}" viewBox="0 0 120 120">${markInner}</svg>
</svg>`;
}

writeFileSync("public/favicon.svg", tile(64, 14, 6));
const png = async (svg, size, out) => sharp(Buffer.from(svg)).resize(size, size).png().toFile(out);
await png(tile(64, 14, 6), 32, "public/favicon-32.png");
await png(tile(180, 40, 20), 180, "public/apple-touch-icon.png");
await png(tile(192, 42, 22), 192, "public/icon-192.png");
await png(tile(512, 112, 60), 512, "public/icon-512.png");

// Social preview 1200x630: dawn paper, the lockup large, the horizon hairline the name stands on.
const og = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <radialGradient id="sun" cx="1.02" cy="-0.1" r="1.1">
      <stop offset="0" stop-color="#F2C14E" stop-opacity="0.55"/>
      <stop offset="0.5" stop-color="#F2C14E" stop-opacity="0.12"/>
      <stop offset="1" stop-color="#F2C14E" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="horizon" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#F2C14E" stop-opacity="0.9"/>
      <stop offset="1" stop-color="#1B1814" stop-opacity="0.08"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="${PAPER}"/>
  <rect width="1200" height="630" fill="url(#sun)"/>
  <svg x="120" y="222" width="170" height="170" viewBox="0 0 120 120">${markInner}</svg>
  <svg x="330" y="238" width="430" height="148" viewBox="${wordVb}" preserveAspectRatio="xMinYMid meet"><path d="${wordPath}" fill="${INK}" fill-rule="evenodd"/></svg>
  <rect x="120" y="420" width="960" height="1.5" fill="url(#horizon)"/>
</svg>`;
await sharp(Buffer.from(og)).png().toFile("public/og.png");

console.log("assets written");
