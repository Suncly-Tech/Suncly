"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Badge, VerdictBadge } from "@/components/ui/Badge";
import { Notice } from "@/components/ui/Notice";
import { Table } from "@/components/ui/Table";
import {
  checkLabel,
  checkState,
  expectedObserved,
  formatDateTime,
  runViews,
  shortId,
  type RunView,
} from "@/lib/evidence/derive";
import type { CheckResult, EvidenceBundle } from "@/lib/evidence/types";

/** Every recorded run, with its deterministic checks and redacted transcript on demand. */
export function RunsTable({
  bundle,
  testCaseId,
  initiallyOpen,
}: {
  bundle: EvidenceBundle;
  testCaseId?: string | null;
  initiallyOpen?: string | null;
}) {
  const views = runViews(bundle).filter((v) => !testCaseId || v.run.test_case_id === testCaseId);
  const [open, setOpen] = useState<string | null>(initiallyOpen ?? null);

  if (views.length === 0) {
    return <p className="text-small text-ink-soft">No runs were recorded for this selection.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <Table caption="Recorded runs with verdict, latency, outcome and checks">
        <thead>
          <tr>
            <th scope="col">Skill</th>
            <th scope="col" className="num">
              Attempt
            </th>
            <th scope="col">Verdict</th>
            <th scope="col">Judge</th>
            <th scope="col" className="num">
              Latency
            </th>
            <th scope="col">Summary</th>
            <th scope="col">
              <span className="sr-only">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {views.map((view) => {
            const isOpen = open === view.run.id;
            return (
              <RunRow key={view.run.id} view={view} open={isOpen} onToggle={() => setOpen(isOpen ? null : view.run.id)} />
            );
          })}
        </tbody>
      </Table>
    </div>
  );
}

function RunRow({ view, open, onToggle }: { view: RunView; open: boolean; onToggle: () => void }) {
  const judgement = view.document?.judgement;
  const transcript = view.document?.transcript;
  return (
    <>
      <tr>
        <td>
          <span className="font-semibold text-ink">{view.skillName}</span>
          <span className="block font-mono text-[12px] text-ink-soft">{shortId(view.run.id)}</span>
        </td>
        <td className="num">{view.run.attempt}</td>
        <td>
          <VerdictBadge verdict={view.run.verdict} />
        </td>
        <td className="text-ink-soft">{view.run.judge_layer === "deterministic" ? "Deterministic" : "Model"}</td>
        <td className="num">{view.run.latency_ms !== null ? `${view.run.latency_ms} ms` : "no response"}</td>
        <td className="max-w-[360px] text-ink-soft">
          <span className="line-clamp-2">{judgement?.summary ?? view.parseError ?? "–"}</span>
        </td>
        <td className="num">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={open}
            aria-controls={`run-${view.run.id}`}
            className="inline-flex h-8 items-center gap-1 rounded-full px-2.5 text-[12px] font-semibold text-ink hover:bg-cream"
          >
            {open ? "Hide" : "Evidence"}
            <ChevronDown size={14} className={`transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
          </button>
        </td>
      </tr>
      {open ? (
        <tr id={`run-${view.run.id}`}>
          <td colSpan={7} className="bg-cream/60">
            {view.document && judgement && transcript ? (
              <RunEvidence view={view} />
            ) : (
              <Notice tone="warn" title="Transcript not available in this bundle">
                {view.parseError}. Load the transcripts folder next to result.json to see the checks and the exchange.
              </Notice>
            )}
          </td>
        </tr>
      ) : null}
    </>
  );
}

function RunEvidence({ view }: { view: RunView }) {
  const document = view.document!;
  const { judgement, transcript } = document;
  const [showExchanges, setShowExchanges] = useState(false);
  return (
    <div className="flex flex-col gap-5 py-2">
      <div>
        <h4 className="text-[13px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Checks: expected versus observed</h4>
        <ul className="mt-2 flex flex-col divide-y divide-line rounded-[12px] bg-paper ring-1 ring-line">
          {judgement.checks.map((check) => (
            <CheckLine key={check.name} check={check} />
          ))}
        </ul>
        <p className="mt-2 text-[13px] text-ink-soft">
          {judgement.judge_layer === "deterministic"
            ? "All checks are deterministic (Judge Layer 1). No model took part in this verdict."
            : `Model judgement. Rationale: ${view.run.rationale ?? "–"}`}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <dl className="kv rounded-[12px] bg-paper p-4 ring-1 ring-line">
          <dt>Outcome</dt>
          <dd className="font-mono text-[13px]">{transcript.outcome}</dd>
          <dt>Final task state</dt>
          <dd className="font-mono text-[13px]">{transcript.final_task_state ?? "–"}</dd>
          <dt>Task id</dt>
          <dd className="font-mono text-[13px]">{transcript.task_id ?? "–"}</dd>
          <dt>Target</dt>
          <dd className="font-mono text-[13px]">
            {transcript.protocol_binding} {transcript.protocol_version} · {transcript.target_url}
          </dd>
          <dt>Started</dt>
          <dd>{formatDateTime(transcript.started_at)}</dd>
          <dt>Finished</dt>
          <dd>{formatDateTime(transcript.finished_at)}</dd>
          <dt>Redaction</dt>
          <dd>
            {transcript.redaction.replacements} replacement{transcript.redaction.replacements === 1 ? "" : "s"}
            {transcript.redaction.rules.length ? ` (${transcript.redaction.rules.join(", ")})` : ""}
          </dd>
          <dt>Failure</dt>
          <dd>{transcript.failure ?? "–"}</dd>
          <dt>Evidence hash</dt>
          <dd className="font-mono text-[12px]">{view.documentHash}</dd>
        </dl>
        <div className="rounded-[12px] bg-paper p-4 ring-1 ring-line">
          <h4 className="text-[13px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Final response</h4>
          <pre className="mt-2 max-h-64 overflow-auto font-mono text-[12px] leading-relaxed text-ink">
            {transcript.final_response ? JSON.stringify(transcript.final_response, null, 2) : "(none)"}
          </pre>
        </div>
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowExchanges((v) => !v)}
          aria-expanded={showExchanges}
          className="inline-flex min-h-9 items-center gap-1.5 text-[13px] font-semibold text-ink underline-offset-4 hover:underline"
        >
          <ChevronDown size={14} className={`transition-transform ${showExchanges ? "rotate-180" : ""}`} aria-hidden="true" />
          {showExchanges ? "Hide" : "Show"} the redacted exchange ({transcript.exchanges.length} message
          {transcript.exchanges.length === 1 ? "" : "s"})
        </button>
        {showExchanges ? (
          <ol className="mt-3 flex flex-col gap-2">
            {transcript.exchanges.map((exchange, i) => (
              <li key={i} className="rounded-[12px] bg-paper p-3 ring-1 ring-line">
                <div className="flex flex-wrap items-center gap-2 text-[12px]">
                  <Badge tone={exchange.direction === "request" ? "info" : "neutral"}>
                    {exchange.direction === "request" ? "Runner → agent" : "agent → Runner"}
                  </Badge>
                  <span className="font-mono text-ink-soft">
                    {exchange.method ?? ""} {exchange.http_status !== null ? `HTTP ${exchange.http_status}` : ""} ·{" "}
                    {formatDateTime(exchange.at)}
                  </span>
                </div>
                <details className="mt-2">
                  <summary className="cursor-pointer text-[12px] font-semibold text-ink-soft">Headers</summary>
                  <pre className="mt-1 overflow-auto font-mono text-[11px] text-ink-soft">
                    {JSON.stringify(exchange.headers, null, 2)}
                  </pre>
                </details>
                <pre className="mt-2 max-h-72 overflow-auto font-mono text-[12px] leading-relaxed text-ink">
                  {JSON.stringify(exchange.body, null, 2)}
                </pre>
              </li>
            ))}
          </ol>
        ) : null}
      </div>
    </div>
  );
}

function CheckLine({ check }: { check: CheckResult }) {
  const state = checkState(check);
  const tone = state === "passed" ? "pass" : state === "failed" ? "fail" : "inconclusive";
  const pair = expectedObserved(check);
  return (
    <li className="grid gap-2 px-4 py-3 sm:grid-cols-[minmax(0,1.2fr)_auto_minmax(0,2fr)] sm:items-start">
      <span className="text-[14px] font-semibold text-ink">{checkLabel(check.name)}</span>
      <Badge tone={tone} dot>
        {state === "passed" ? "Passed" : state === "failed" ? "Failed" : "Undecided"}
      </Badge>
      {pair ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 font-mono text-[12px]">
          <dt className="text-ink-soft">expected</dt>
          <dd className="text-ink">{pair.expected}</dd>
          <dt className="text-ink-soft">observed</dt>
          <dd className={state === "failed" ? "text-fail" : "text-ink"}>{pair.observed}</dd>
        </dl>
      ) : (
        <span className="text-[13px] text-ink-soft">{check.detail}</span>
      )}
    </li>
  );
}
