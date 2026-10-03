// Minimal static server for the exported site, behaving like Cloudflare Pages / Vercel:
// clean URLs (/docs -> docs.html), index.html for directories, 404.html, and
// immutable caching for hashed assets. Usage: node scripts/serve.mjs [port]
import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";

const port = Number(process.argv[2] ?? 3100);
const root = new URL("../out/", import.meta.url).pathname;

const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml",
  ".webmanifest": "application/manifest+json",
};

function resolve(urlPath) {
  const clean = normalize(decodeURIComponent(urlPath.split("?")[0])).replace(/^(\.\.[/\\])+/, "");
  const candidates = [
    join(root, clean),
    join(root, clean + ".html"),
    join(root, clean, "index.html"),
  ];
  for (const c of candidates) {
    if (existsSync(c) && statSync(c).isFile()) return c;
  }
  return null;
}

createServer((req, res) => {
  const file = resolve(req.url ?? "/");
  if (!file) {
    res.writeHead(404, { "Content-Type": types[".html"] });
    createReadStream(join(root, "404.html")).pipe(res);
    return;
  }
  const ext = extname(file);
  const headers = { "Content-Type": types[ext] ?? "application/octet-stream" };
  headers["Cache-Control"] = file.includes("/_next/static/")
    ? "public, max-age=31536000, immutable"
    : "public, max-age=0, must-revalidate";
  res.writeHead(200, headers);
  createReadStream(file).pipe(res);
}).listen(port, () => console.log(`serving ${root} on http://localhost:${port}`));
