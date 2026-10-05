// Lighthouse on the home page, mobile, twice: once with the default simulated throttling
// (the score Lighthouse reports) and once with devtools throttling (observed metrics under
// a real throttled connection). Prints LCP, CLS, TBT and the LCP element for both.
// Usage: CHROME_PATH=/opt/pw-browsers/chromium node scripts/lcp-probe.mjs [url]
import lighthouse from "lighthouse";
import { launch } from "chrome-launcher";

const url = process.argv[2] ?? "http://localhost:3100/";
const chrome = await launch({
  chromeFlags: ["--headless=new", "--no-sandbox"],
});
const run = async (throttlingMethod) => {
  const { lhr, artifacts } = await lighthouse(url, {
    logLevel: "error",
    output: "json",
    onlyCategories: ["performance"],
    port: chrome.port,
    formFactor: "mobile",
    throttlingMethod,
    screenEmulation: {
      mobile: true,
      width: 412,
      height: 823,
      deviceScaleFactor: 1.75,
      disabled: false,
    },
  });
  const m = lhr.audits.metrics.details.items[0];
  const lcpEl = artifacts?.TraceElements?.find(
    (e) => e.traceEventType === "largest-contentful-paint",
  );
  return {
    throttlingMethod,
    score: Math.round(lhr.categories.performance.score * 100),
    lcp: Math.round(m.largestContentfulPaint),
    observedLcp: Math.round(m.observedLargestContentfulPaint),
    fcp: Math.round(m.firstContentfulPaint),
    tbt: Math.round(m.totalBlockingTime),
    cls: lhr.audits["cumulative-layout-shift"].numericValue,
    tti: Math.round(m.interactive),
    lcpElement: lcpEl
      ? `${lcpEl.node?.nodeLabel ?? ""} ${lcpEl.node?.selector ?? ""}`.trim()
      : "(not attributed)",
    lcpType: lcpEl?.type,
  };
};
const simulated = await run("simulate");
const devtools = await run("devtools");
await chrome.kill();
console.log(JSON.stringify({ simulated, devtools }, null, 2));
