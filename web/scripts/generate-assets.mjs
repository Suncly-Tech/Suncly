// Derives favicons and the OG image from public/mark.svg.
// The mark stays yellow; it sits on a sky-blue field for contrast.
import sharp from "sharp";
import { readFileSync, writeFileSync } from "node:fs";

const SKY = "#3461D1";
const mark = readFileSync(new URL("../public/mark.svg", import.meta.url), "utf8");
const markInner = mark.replace(/<svg[^>]*>/, "").replace("</svg>", "");

function tile(size, radius, pad) {
  const inner = size - pad * 2;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}">
  <rect width="${size}" height="${size}" rx="${radius}" fill="${SKY}"/>
  <svg x="${pad}" y="${pad}" width="${inner}" height="${inner}" viewBox="0 0 120 120">${markInner}</svg>
</svg>`;
}

// Favicon SVG (rounded blue tile with the mark)
writeFileSync("public/favicon.svg", tile(64, 14, 8));

const png = async (svg, size, out) =>
  sharp(Buffer.from(svg)).resize(size, size).png().toFile(out);

await png(tile(64, 14, 8), 32, "public/favicon-32.png");
await png(tile(180, 40, 24), 180, "public/apple-touch-icon.png");
await png(tile(192, 42, 26), 192, "public/icon-192.png");
await png(tile(512, 112, 68), 512, "public/icon-512.png");

// OG image 1200x630: mark on blue, wordmark in Manrope-like fallback is avoided;
// we draw only the mark so the image never depends on a font being present.
const og = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1D3A97"/>
      <stop offset="1" stop-color="${SKY}"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#sky)"/>
  <circle cx="600" cy="400" r="330" fill="#ffffff" opacity="0.06"/>
  <circle cx="600" cy="400" r="240" fill="#ffffff" opacity="0.06"/>
  <svg x="470" y="185" width="260" height="260" viewBox="0 0 120 120">${markInner}</svg>
</svg>`;
await sharp(Buffer.from(og)).png().toFile("public/og.png");

console.log("assets written");
