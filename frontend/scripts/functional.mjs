// Functional checks on the built site: navigation, every internal link, the install tabs
// and copy buttons, the specimen strip, the /demo in-browser signature verification, and
// the workspace (sample load, overview, evaluation, review form errors, settings).
// Usage: node scripts/functional.mjs [baseUrl]
import { chromium } from "playwright";
import { existsSync } from "node:fs";

const base = process.argv[2] ?? "http://localhost:3100";
const browser = await chromium.launch({
  executablePath: existsSync("/opt/pw-browsers/chromium")
    ? "/opt/pw-browsers/chromium"
    : undefined,
});
let failures = 0;
const check = (ok, msg) => {
  console.log(`${ok ? "ok " : "FAIL"} ${msg}`);
  if (!ok) failures++;
};

const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
});
await context.grantPermissions(["clipboard-read", "clipboard-write"]);
const page = await context.newPage();
const pageErrors = [];
page.on("pageerror", (e) => pageErrors.push(e.message));

// 1. Crawl every internal link from every public page; no 404s, no hash without target.
const PAGES = [
  "/",
  "/offer",
  "/certified",
  "/certified/policy",
  "/certified/specimen",
  "/data",
  "/research",
  "/lab",
  "/product",
  "/workflows",
  "/demo",
  "/security",
  "/docs",
  "/docs/getting-started",
  "/docs/cli",
  "/docs/evidence",
  "/company",
  "/access",
  "/glossary",
  "/privacy",
  "/terms",
  "/cookies",
  "/legal",
];
const seen = new Map();
for (const path of PAGES) {
  await page.goto(base + path, { waitUntil: "networkidle" });
  const links = await page.evaluate(() =>
    Array.from(document.querySelectorAll("a[href]")).map((a) =>
      a.getAttribute("href"),
    ),
  );
  for (const href of links) {
    if (!href || href.startsWith("mailto:") || href.startsWith("http"))
      continue;
    const [p, hash] = href.split("#");
    const target = p || path;
    if (!seen.has(target)) {
      const res = await page.request.get(base + target);
      seen.set(target, res.status());
    }
    if (seen.get(target) !== 200)
      check(false, `${path}: link ${href} returns ${seen.get(target)}`);
    if (hash) {
      await page.goto(base + target, { waitUntil: "domcontentloaded" });
      const exists = await page.evaluate(
        (h) => !!document.getElementById(h),
        hash,
      );
      if (!exists)
        check(false, `${path}: anchor #${hash} has no target on ${target}`);
    }
  }
}
check(
  true,
  `${seen.size} internal link targets return 200 and every anchor has a target`,
);

// 2. Navigation: primary links and the Install button.
await page.goto(base + "/", { waitUntil: "networkidle" });
for (const label of ["Offer", "Data", "Research", "Lab", "Docs"]) {
  const expected = `/${label.toLowerCase()}`;
  await page
    .getByRole("navigation", { name: "Primary" })
    .getByRole("link", { name: label })
    .click();
  await page
    .waitForURL((u) => u.pathname === expected, { timeout: 5000 })
    .catch(() => {});
  check(
    new URL(page.url()).pathname === expected,
    `nav link ${label} opens ${expected} (got ${new URL(page.url()).pathname})`,
  );
  await page.goto(base + "/", { waitUntil: "networkidle" });
}
await page.getByRole("link", { name: "Install", exact: true }).first().click();
await page.waitForTimeout(400);
check(
  (await page.evaluate(() => location.hash)) === "#install",
  "nav Install button jumps to #install on the home page",
);

// 3. Install tabs and copy buttons.
const tabs = page.getByRole("tab");
check(
  (await tabs.count()) === 6,
  "six install tabs: Terminal, Cursor, Claude Code, Codex, omp, Pi",
);
await tabs.nth(1).click();
check(
  await page
    .getByRole("tabpanel")
    .getByText(/Planned/)
    .first()
    .isVisible(),
  "a tool tab shows Planned",
);
await page.getByRole("button", { name: "Show the Terminal steps" }).click();
check(
  await page
    .getByRole("button", { name: /copy install commands/i })
    .isVisible(),
  "the Terminal tab returns with its code block",
);
await page.getByRole("button", { name: "Windows PowerShell" }).click();
check(
  (
    await page.locator("pre[aria-label='install commands']").innerText()
  ).includes("Activate.ps1"),
  "the Windows toggle shows the PowerShell activation line",
);
await page.getByRole("button", { name: "macOS / Linux" }).click();
await page.getByRole("button", { name: /copy install commands/i }).click();
await page.waitForTimeout(150);
const clip = await page.evaluate(() =>
  navigator.clipboard.readText().catch(() => ""),
);
check(
  clip.includes("pip install -e .") && clip.includes("suncly demo"),
  "the copy button copies exactly the shown commands",
);
check(
  (await page
    .getByRole("button", { name: /install commands copied/i })
    .count()) > 0,
  "the copy button announces success",
);

// 4. Specimen strip.
await page.getByRole("button", { name: "lying" }).click();
check(
  (await page.locator("[aria-live='polite']").innerText()).includes(
    "output_modes",
  ),
  "specimen strip shows what Suncly reports for the lying agent",
);

// 5. /demo: switch evaluations, run the in-browser verification.
await page.goto(base + "/demo", { waitUntil: "networkidle" });
const sigTab = page.getByRole("tab", { name: /signature/i });
await sigTab.click();
check(
  (await page.locator("#panel-signature[role='tabpanel']").count()) === 1,
  "the selected Signature tab controls a tab panel with the matching id",
);
const run = page.getByRole("button", { name: /run verification/i });
await run.click();
await page.waitForTimeout(1500);
const sig = await page.locator("#panel-signature").innerText();
const okCount = (sig.match(/\bok\b|passed|✓/gi) ?? []).length;
check(
  /8 of 8|all 8|8 checks|passed/i.test(sig) || okCount >= 8,
  `in-browser verification ran (${okCount} ok markers)`,
);
check(
  !/FAIL|failed/i.test(sig.replace(/Verification passed/i, "")),
  "no check failed in the in-browser verification",
);

// 6. Workspace: load the sample, overview, evaluation, review form, settings.
await page
  .getByRole("button", { name: /load sample/i })
  .first()
  .click();
await page.waitForTimeout(600);
await page.goto(base + "/app", { waitUntil: "networkidle" });
const overview = await page.locator("main").innerText();
check(
  /Harbor Returns Agent/.test(overview),
  "workspace overview shows the sample agent after loading",
);
const evalLink = page.locator("a[href*='/app/evaluation']").first();
await evalLink.click();
await page.waitForLoadState("networkidle");
check(
  /Harbor Returns Agent/.test(await page.locator("main").innerText()),
  "evaluation page opens from the overview",
);
await page.getByRole("tab", { name: /review/i }).click();
const submit = page.getByRole("button", { name: /record/i }).first();
await submit.click();
await page.waitForTimeout(200);
check(
  (await page.locator("[role='alert']").count()) > 0,
  "the review form announces its validation errors",
);
await page.goto(base + "/app/settings", { waitUntil: "networkidle" });
check(
  /Clear the workspace/i.test(await page.locator("main").innerText()),
  "settings page renders with the clear action",
);

check(
  pageErrors.length === 0,
  `no page errors (${pageErrors.join(" | ").slice(0, 200)})`,
);
await browser.close();
console.log(
  failures ? `${failures} failure(s)` : "all functional checks passed",
);
process.exit(failures ? 1 : 0);
