import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { testCaseRows, totals } from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";

/**
 * Per-test-case counts, exactly as the report shows them: pass, fail and inconclusive
 * side by side, never combined. Inconsistent and undecided rows are called out.
 */
export function TestCaseTable({
  result,
  selected,
  onSelect,
  compact = false,
}: {
  result: ResultDocument;
  selected?: string | null;
  onSelect?: (testCaseId: string) => void;
  compact?: boolean;
}) {
  const rows = testCaseRows(result);
  const sums = totals(result);
  return (
    <div className="flex flex-col gap-3">
      <Table caption="Results per test case: pass, fail and inconclusive counts">
        <thead>
          <tr>
            <th scope="col">Skill</th>
            <th scope="col">Test input</th>
            {!compact ? <th scope="col">Signal</th> : null}
            <th scope="col" className="num">
              Pass
            </th>
            <th scope="col" className="num">
              Fail
            </th>
            <th scope="col" className="num">
              Inconclusive
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isSelected = selected === row.testCase.id;
            const content = (
              <>
                <td>
                  <span className="font-semibold text-ink">{row.skillName}</span>
                  <span className="block font-mono text-[12px] text-ink-soft">{row.testCase.skill_id ?? row.testCase.kind}</span>
                </td>
                <td className="max-w-[320px] text-ink">
                  <span className="line-clamp-2">“{row.inputText}”</span>
                </td>
                {!compact ? (
                  <td>
                    {row.inconsistent ? (
                      <Badge tone="fail" title="Both pass and fail recorded for the same input">
                        Inconsistent
                      </Badge>
                    ) : row.undecided ? (
                      <Badge tone="inconclusive" title="Every run was inconclusive">
                        Undecided
                      </Badge>
                    ) : row.result.fail_count > 0 ? (
                      <Badge tone="fail">Failing</Badge>
                    ) : row.result.pass_count > 0 ? (
                      <Badge tone="pass">Passing</Badge>
                    ) : (
                      <Badge tone="neutral">No runs</Badge>
                    )}
                  </td>
                ) : null}
                <td className={`num ${row.result.pass_count ? "text-pass" : "text-ink-mute"}`}>{row.result.pass_count}</td>
                <td className={`num ${row.result.fail_count ? "text-fail" : "text-ink-mute"}`}>{row.result.fail_count}</td>
                <td className={`num ${row.result.inconclusive_count ? "text-partial" : "text-ink-mute"}`}>
                  {row.result.inconclusive_count}
                </td>
              </>
            );
            if (onSelect) {
              return (
                <tr
                  key={row.testCase.id}
                  className={`cursor-pointer ${isSelected ? "[&>td]:bg-info-soft" : ""}`}
                  onClick={() => onSelect(row.testCase.id)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(row.testCase.id);
                    }
                  }}
                  aria-selected={isSelected}
                >
                  {content}
                </tr>
              );
            }
            return <tr key={row.testCase.id}>{content}</tr>;
          })}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={compact ? 2 : 3} className="text-[13px] text-ink-soft">
              Totals across {rows.length} test case{rows.length === 1 ? "" : "s"}. Counts, not a score.
            </td>
            <td className="num text-pass">{sums.pass}</td>
            <td className="num text-fail">{sums.fail}</td>
            <td className="num text-partial">{sums.inconclusive}</td>
          </tr>
        </tfoot>
      </Table>
    </div>
  );
}
