// Keyboard-navigation check: tabs through the page and reports what receives focus,
// then exercises the mobile menu and the FAQ with the keyboard only.
// Usage: node scripts/keyboard.mjs [baseUrl]
import { chromium } from "playwright";

const base = process.argv[2] ?? "http://localhost:3000";
const browser = await chromium.launch({ channel: "chrome" });
let failures = 0;
const check = (ok, msg) => {
  console.log(`${ok ? "ok " : "FAIL"} ${msg}`);
  if (!ok) failures++;
};

const describe = (page) =>
  page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return "body";
    const label =
      el.getAttribute("aria-label") ||
      el.textContent?.trim().replace(/\s+/g, " ").slice(0, 40) ||
      el.getAttribute("placeholder") ||
      "";
    return `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""} "${label}"`;
  });

// Desktop: tab order through the whole page
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base + "/", { waitUntil: "networkidle" });
  const seen = [];
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press("Tab");
    const d = await describe(page);
    if (d === "body" && seen.length > 5) break;
    seen.push(d);
  }
  console.log("Desktop tab order:");
  seen.forEach((s, i) => console.log(`  ${String(i + 1).padStart(2)}  ${s}`));
  check(seen[0].includes("Skip to content"), "skip link is first in tab order");
  check(seen.some((s) => s.includes("Get early access")), "primary CTA reachable");
  check(seen.some((s) => s.startsWith("summary")), "FAQ summaries reachable");

  // Terminal replay button: disabled while the demo runs, reachable and working once done.
  await page.locator("#how-it-works").scrollIntoViewIfNeeded();
  await page.waitForTimeout(9000);
  const replay = page.locator('button[aria-label="Run again"]');
  check(await replay.isEnabled(), "terminal replay button enabled after the demo finishes");
  await replay.focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(300);
  check(!(await replay.isEnabled()), "Enter on replay restarts the demo (button disabled again)");
  check(seen.some((s) => s.startsWith("input#email")), "email input reachable");

  // Skip link works
  await page.goto(base + "/", { waitUntil: "networkidle" });
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  const hash = await page.evaluate(() => location.hash);
  check(hash === "#main", `skip link jumps to #main (hash=${hash})`);

  // FAQ opens with Enter and Space
  const summary = page.locator("#faq summary").first();
  await summary.focus();
  await page.keyboard.press("Enter");
  check(await page.locator("#faq details").first().evaluate((d) => d.open), "FAQ item opens with Enter");
  await page.keyboard.press("Space");
  check(!(await page.locator("#faq details").first().evaluate((d) => d.open)), "FAQ item closes with Space");

  // Focus ring visible on primary button
  await page.locator('a.btn-primary').first().focus();
  const outline = await page.locator("a.btn-primary").first().evaluate((el) => getComputedStyle(el).outlineStyle);
  check(outline !== "none", `focus-visible outline on primary CTA (${outline})`);
  await page.close();
}

// Mobile: menu button, Escape, focus stays usable
{
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(base + "/", { waitUntil: "networkidle" });
  const btn = page.locator('button[aria-controls="mobile-menu"]');
  await btn.focus();
  await page.keyboard.press("Enter");
  check((await btn.getAttribute("aria-expanded")) === "true", "menu opens from keyboard");
  check(await page.locator("#mobile-menu").isVisible(), "menu panel visible");
  await page.keyboard.press("Tab");
  const inMenu = await describe(page);
  check(inMenu.includes("Product"), `first Tab inside open menu lands on first link (${inMenu})`);
  await page.keyboard.press("Escape");
  check((await btn.getAttribute("aria-expanded")) === "false", "Escape closes the menu");
  check(!(await page.locator("#mobile-menu").isVisible()), "menu panel hidden after Escape");
  await page.close();
}

await browser.close();
console.log(failures ? `\n${failures} keyboard check(s) failed` : "\nAll keyboard checks passed");
process.exit(failures ? 1 : 0);
