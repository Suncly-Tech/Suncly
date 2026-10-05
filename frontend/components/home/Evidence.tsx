import Link from "next/link";
import { TestCaseTable } from "@/components/evidence/TestCaseTable";
import { SampleBadge } from "@/components/ui/Badge";
import { evidence } from "@/lib/content";
import { sampleByLabel } from "@/lib/sample";
import { totals } from "@/lib/evidence/derive";

/**
 * 06 Evidence. One compact evidence card built from the sample bundle with the real
 * workspace components: Passed, Failed, Inconclusive, Not tested. The last is visibly
 * different, using the hatch. Counts in type. No chart.
 */
export function Evidence() {
  const bundle = sampleByLabel("2-regression");
  if (!bundle) return null;
  const result = bundle.result;
  const sums = totals(result);
  const counts = [
    { label: "Passed", value: sums.pass, cls: "text-pass" },
    { label: "Failed", value: sums.fail, cls: "text-fail" },
    { label: "Inconclusive", value: sums.inconclusive, cls: "text-partial" },
  ];
  return (
    <section id="evidence" aria-labelledby="evidence-heading" className="container-site scroll-mt-20 py-12 md:py-24">
      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
        <div>
          <p className="text-eyebrow text-ink-soft">
            <span className="mr-3 text-ink-mute">06</span>
            {evidence.label}
          </p>
          <h2 id="evidence-heading" className="mt-4 text-display-lg text-ink">
            {evidence.headline}
          </h2>
          <p className="mt-5 max-w-[40ch] text-body text-ink">{evidence.body}</p>
          <p className="mt-5 text-small text-ink-soft">
            {evidence.verify} <code className="code-inline">{evidence.verifyCommand}</code>
          </p>
          <Link href={evidence.link.href} className="mt-4 inline-block text-[15.5px] underline underline-offset-4 decoration-amber hover:text-ember">
            {evidence.link.label}
          </Link>
        </div>

        <div className="surface-card p-4 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-small text-ink-soft">
              {result.agent.name} · evaluation 2 · card unchanged
            </p>
            <SampleBadge />
          </div>
          <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {counts.map((c) => (
              <div key={c.label} className="border-t border-line pt-3">
                <dt className="text-eyebrow text-ink-soft">{c.label}</dt>
                <dd className={`mt-1 font-display text-[36px] leading-none ${c.cls}`}>{c.value}</dd>
              </div>
            ))}
            <div className="hatch border-t border-line pt-3 pl-2">
              <dt className="text-eyebrow text-ink-soft">Not tested</dt>
              <dd className="mt-1 font-display text-[36px] leading-none text-ink">{result.not_tested.length}</dd>
            </div>
          </dl>
          <div className="mt-6">
            <TestCaseTable result={result} compact />
          </div>
          <h3 className="mt-6 text-eyebrow text-ink-soft">{evidence.notTestedHeading}</h3>
          <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
            {result.not_tested.map((item) => (
              <li key={item.category} className="cuts-bullet text-small text-ink" title={item.detail}>
                {item.category}
              </li>
            ))}
          </ul>
          <p className="mt-6 border-t border-line pt-4 text-body text-ink">{evidence.fixed}</p>
        </div>
      </div>
    </section>
  );
}
