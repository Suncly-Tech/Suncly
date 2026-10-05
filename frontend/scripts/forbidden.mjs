// Searches the built out/ folder for things that must not ship. Exit 1 on any hit.
// Usage: node scripts/forbidden.mjs   (after npm run build)
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../out/", import.meta.url).pathname;
const registered = false; // lib/launch.ts: launch.trademark === "registered"

const RULES = [
  { name: '"trusted by"', test: (t) => /trusted by/i.test(t) },
  { name: '"A2A certified" or "A2A-certified"', test: (t) => /A2A[ -]certified/i.test(t) },
  { name: '"AI Act compliant"', test: (t) => /AI Act[ -]compliant|compliant with the (EU )?AI Act/i.test(t) },
  { name: "the registered symbol while the mark is unregistered", test: (t) => !registered && /®/.test(t) },
  {
    name: '"guarantee" outside a disclaimer',
    test: (t) => {
      const hits = t.match(/[^.]*guarantee[^.]*\./gi) ?? [];
      return hits.some((s) => !/not a guarantee|no guarantee|do not guarantee|does not guarantee|never guarantee|"guaranteed"|guaranteed",|guaranteed, |not guarantee/i.test(s));
    },
  },
  { name: "a competitor name", test: (t) => /\b(AgentAuth|AgentCert|Guardrails AI|Lakera|Protect AI|HiddenLayer)\b/i.test(t) },
  { name: "a blank-input placeholder", test: (t) => /\{\{|TODO|TBD|lorem ipsum|xxx@|example\.org/i.test(t) },
  { name: "blue in the global theme", test: (t, file) => file.endsWith(".css") && /#3461d1|#1d3a97|#5f86e6|rgb\(52 97 209/i.test(t) },
  { name: '"official" or "accredited" about certification', test: (t) => /officially certified|accredited certification|official certification/i.test(t) },
  { name: "a published price", test: (t) => /€\s?\d|\d+\s?EUR\b|\$\d/.test(t) && !/EUR 1,000/.test(t) },
];

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(html|css|xml|webmanifest)$/.test(name) || /^(llms|llms-full|robots)\.txt$/.test(name) || p.endsWith(".well-known/security.txt")) files.push(p);
  }
})(root);

let failures = 0;
for (const file of files) {
  const raw = readFileSync(file, "utf8").replace(/<script[^>]*>[\s\S]*?<\/script>/g, "");
  // for HTML, test the visible text, not the markup
  const text = file.endsWith(".html") ? raw.replace(/<style[^>]*>[\s\S]*?<\/style>/g, "").replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"') : raw;
  for (const rule of RULES) {
    if (rule.test(text, file)) {
      failures++;
      console.error(`${file.replace(root, "")}: ${rule.name}`);
    }
  }
}
console.log(`${files.length} files checked, ${failures} problem(s)`);
process.exit(failures ? 1 : 0);
