// Keyboard-navigation check: tabs through the home page and reports what receives focus,
// then exercises the install tabs, the specimen strip, the FAQ and the mobile menu with
// the keyboard only. Usage: node scripts/keyboard.mjs [baseUrl]
import { chromium } from "playwright";
import { existsSync } from "node:fs";

const base = process.argv[2] ?? "http://localhost:3100";
const browser = await chromium.launch({ executablePath: existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined });
let failures = 0;
const check = (ok, msg) => {
  console.log(`${ok ? "ok " : "FAIL"} ${msg}`);
  if (!ok) failures++;
};
const describe = (page) =>
  page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return "body";
    const label = el.getAttribute("aria-label") || el.textContent?.trim().slice(0, 40) || "";
    const role = el.getAttribute("role");
    return `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}${role ? `[${role}]` : ""} ${label}`.trim();
  });
const focusRing = (page) =>
  page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return false;
    const cs = getComputedStyle(el);
    return cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0;
  });

{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(base + "/", { waitUntil: "networkidle" });
  const seen = [];
  let ringSeen = false;
  for (let i = 0; i < 80; i++) {
    await page.keyboard.press("Tab");
    const d = await describe(page);
    if (d === "body" && seen.length > 5) break;
    if (!ringSeen && (await focusRing(page))) ringSeen = true;
    seen.push(d);
  }
  console.log("Desktop tab order (first 80 stops):");
  seen.forEach((s, i) => console.log(`  ${String(i + 1).padStart(2)}  ${s}`));
  check(seen[0].includes("Skip to content"), "skip link is first in tab order");
  check(ringSeen, "a visible focus ring (outline) is shown on focus");
  check(seen.some((s) => s.includes("Install Suncly")), "primary action reachable");
  check(seen.some((s) => s.includes("[tab]")), "install tabs reachable");
  check(seen.some((s) => s.includes("Copy")), "copy button reachable");
  check(seen.some((s) => s.includes("honest")), "specimen strip reachable");
  check(seen.some((s) => s.startsWith("summary")), "FAQ summaries reachable");
  check(seen.some((s) => s.includes("Suncly on X")), "Find Suncly links reachable");

  // Install tabs: arrow keys move, panel follows
  const firstTab = page.getByRole("tab").first();
  await firstTab.focus();
  await page.keyboard.press("ArrowRight");
  const selected = await page.evaluate(() => document.activeElement?.getAttribute("aria-selected"));
  check(selected === "true", "ArrowRight selects the next install tab");

  // Copy button announces
  await page.keyboard.press("Home");
  await page.getByRole("button", { name: /copy install commands/i }).focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(100);
  const copied = await page.getByRole("button", { name: /copied/i }).count();
  check(copied > 0, "Enter on the copy button announces success");

  // Skip link works
  await page.goto(base + "/", { waitUntil: "networkidle" });
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  const hash = await page.evaluate(() => location.hash);
  check(hash === "#main", `skip link jumps to #main (hash=${hash})`);
  await page.close();
}

{
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(base + "/", { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Menu" }).focus();
  await page.keyboard.press("Enter");
  await page.waitForTimeout(200);
  check(await page.locator("#mobile-menu").isVisible(), "mobile menu opens from the keyboard");
  const stops = [];
  for (let i = 0; i < 20; i++) {
    await page.keyboard.press("Tab");
    stops.push(await describe(page));
  }
  check(stops.every((s) => s !== "body"), "focus stays inside the open menu (trapped)");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(200);
  check(!(await page.locator("#mobile-menu").isVisible()), "Escape closes the mobile menu");
  await page.close();
}

await browser.close();
console.log(failures ? `${failures} failure(s)` : "all keyboard checks passed");
process.exit(failures ? 1 : 0);
