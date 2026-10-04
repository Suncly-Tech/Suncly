import { Badge } from "@/components/ui/Badge";
import { skillCoverage } from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";

/** The report's "What was NOT tested" section, verbatim categories and details. */
export function NotTestedList({ result, compact = false }: { result: ResultDocument; compact?: boolean }) {
  if (result.not_tested.length === 0) {
    return <p className="text-small text-ink-soft">The report lists nothing under “What was NOT tested”.</p>;
  }
  return (
    <ul className="flex flex-col divide-y divide-line">
      {result.not_tested.map((item, i) => (
        <li key={i} className={`flex flex-col gap-1 ${compact ? "py-2.5" : "py-3"} sm:flex-row sm:gap-4`}>
          <span className="w-56 shrink-0 text-[13px] font-semibold text-ink">{item.category}</span>
          <span className="text-small text-ink-soft">{item.detail}</span>
        </li>
      ))}
    </ul>
  );
}

/** Declared skills with their coverage: tested with counts, or untested with the reason. */
export function SkillCoverageList({ result }: { result: ResultDocument }) {
  const skills = skillCoverage(result);
  return (
    <ul className="grid gap-3 md:grid-cols-2">
      {skills.map((skill) => (
        <li key={skill.id} className="surface flex flex-col gap-2 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="font-semibold text-ink">{skill.name}</p>
              <p className="font-mono text-[12px] text-ink-soft">{skill.id}</p>
            </div>
            {skill.tested ? (
              <Badge tone="pass" dot>
                {skill.testCases.length} test case{skill.testCases.length === 1 ? "" : "s"}
              </Badge>
            ) : (
              <Badge tone="fail" dot>
                Not tested
              </Badge>
            )}
          </div>
          <p className="text-[13px] text-ink-soft">{skill.description}</p>
          {skill.tested ? (
            <p className="font-mono text-[12px] text-ink-soft">
              <span className="text-pass">{skill.verdicts.pass} pass</span> ·{" "}
              <span className="text-fail">{skill.verdicts.fail} fail</span> ·{" "}
              <span className="text-partial">{skill.verdicts.inconclusive} inconclusive</span>
            </p>
          ) : (
            <p className="text-[13px] text-fail">{skill.reason}</p>
          )}
          {skill.tags.length ? (
            <div className="flex flex-wrap gap-1.5">
              {skill.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-cream-deep px-2 py-0.5 text-[11px] font-semibold text-ink-soft">
                  {tag}
                </span>
              ))}
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
