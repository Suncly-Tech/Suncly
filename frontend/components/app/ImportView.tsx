"use client";

import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import Link from "next/link";
import { FolderOpen, Upload } from "lucide-react";
import { Button, ButtonLink } from "@/components/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Notice } from "@/components/ui/Notice";
import { KeyValue } from "@/components/ui/Stat";
import { StatusBadge } from "@/components/ui/Badge";
import { PageTitle } from "./PageTitle";
import { formatDateTime, shortId } from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";
import { addBundle, parseResultText, StorageFullError, useWorkspaceState } from "@/lib/workspace/store";

interface Staged {
  result: ResultDocument;
  transcripts: Record<string, string>;
  resultFileName: string;
  ignored: string[];
  missingTranscripts: string[];
  unmatchedTranscripts: string[];
}

/** Drop a report folder (or its files). Validated here; stored in this browser only. */
export function ImportView() {
  const { state } = useWorkspaceState();
  const [staged, setStaged] = useState<Staged | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);

  async function handleFiles(list: FileList | File[]) {
    setError(null);
    setDone(null);
    setStaged(null);
    const files = Array.from(list).filter((f) => f.name.toLowerCase().endsWith(".json"));
    if (files.length === 0) {
      setError("No JSON files were selected. Drop result.json and the transcripts folder from a suncly report folder.");
      return;
    }
    const texts = await Promise.all(files.map(async (f) => ({ file: f, text: await f.text() })));

    let result: ResultDocument | null = null;
    let resultFileName = "";
    const candidates: Array<{ file: File; text: string }> = [];
    const errors: string[] = [];
    for (const entry of texts) {
      const parsed = parseResultText(entry.text);
      if ("result" in parsed) {
        if (result) {
          errors.push(`More than one result.json was selected (${resultFileName} and ${entry.file.name}). Import one report folder at a time.`);
        } else {
          result = parsed.result;
          resultFileName = entry.file.name;
        }
      } else {
        candidates.push(entry);
      }
    }
    if (errors.length) {
      setError(errors.join(" "));
      return;
    }
    if (!result) {
      const single = texts.length === 1 ? parseResultText(texts[0].text) : null;
      setError(
        single && "error" in single
          ? single.error
          : "No result.json was found among the selected files. The result document is the file suncly attest writes to <report folder>/result.json.",
      );
      return;
    }

    const expected = new Set(result.runs.map((r) => r.run.id));
    const transcripts: Record<string, string> = {};
    const ignored: string[] = [];
    const unmatched: string[] = [];
    for (const { file, text } of candidates) {
      const stem = file.name.replace(/\.json$/i, "");
      if (expected.has(stem)) {
        transcripts[stem] = text;
      } else if (/^[0-9a-f-]{36}$/i.test(stem)) {
        unmatched.push(file.name);
      } else {
        ignored.push(file.name);
      }
    }
    const missing = [...expected].filter((id) => !(id in transcripts));
    setStaged({ result, transcripts, resultFileName, ignored, missingTranscripts: missing, unmatchedTranscripts: unmatched });
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    void handleFiles(e.dataTransfer.files);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    if (e.target.files) void handleFiles(e.target.files);
    e.target.value = "";
  }

  function commit() {
    if (!staged) return;
    try {
      addBundle({ result: staged.result, transcripts: staged.transcripts }, "import", `Imported from ${staged.resultFileName}`);
      setDone(staged.result.attestation.id);
      setStaged(null);
    } catch (err) {
      setError(err instanceof StorageFullError ? err.message : `The bundle could not be stored: ${String(err)}`);
    }
  }

  const duplicate = staged ? staged.result.attestation.id in state.bundles : false;

  return (
    <>
      <PageTitle
        title="Import a report folder"
        intro="Select the folder suncly attest wrote, or drop result.json together with the files from transcripts/. The workspace validates the format and keeps the transcript text byte for byte so hashes can be re-checked. Nothing is uploaded; the bundle is stored in this browser."
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <div className="flex flex-col gap-6">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex flex-col items-center justify-center gap-4 rounded-card border-2 border-dashed p-10 text-center transition-colors ${
              dragging ? "border-sky bg-info-soft" : "border-line-strong bg-paper"
            }`}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-sun text-ink">
              <Upload size={22} aria-hidden="true" />
            </span>
            <div>
              <p className="text-heading-md text-ink">Drop the report folder here</p>
              <p className="mt-1 text-small text-ink-soft">result.json and transcripts/*.json. report.md and report.html are ignored.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-3">
              <Button variant="secondary" onClick={() => folderInput.current?.click()}>
                <FolderOpen size={16} aria-hidden="true" />
                Select a folder
              </Button>
              <Button variant="ghost" onClick={() => fileInput.current?.click()}>
                Select files
              </Button>
            </div>
            <input ref={fileInput} type="file" accept=".json,application/json" multiple className="sr-only" onChange={onChange} aria-label="Select result.json and transcript files" />
            <input
              ref={folderInput}
              type="file"
              className="sr-only"
              onChange={onChange}
              aria-label="Select a report folder"
              // Folder selection where the browser supports it; falls back to multiple files.
              {...({ webkitdirectory: "", directory: "", multiple: true } as Record<string, string | boolean>)}
            />
          </div>

          {error ? (
            <Notice tone="error" title="Nothing was imported" role="alert">
              {error}
            </Notice>
          ) : null}

          {done ? (
            <Notice
              tone="success"
              title="Imported"
              role="status"
              action={
                <ButtonLink href={`/app/evaluation?id=${done}`} size="sm">
                  Open evaluation
                </ButtonLink>
              }
            >
              Attestation {shortId(done)} is in the workspace. <Link href="/app" className="underline">Back to the overview</Link>.
            </Notice>
          ) : null}

          {staged ? (
            <Card>
              <CardHeader
                title="Ready to add"
                description="Check that this is the report you meant, then add it to the workspace."
                action={
                  <Button onClick={commit} size="sm">
                    {duplicate ? "Replace in workspace" : "Add to workspace"}
                  </Button>
                }
              />
              {duplicate ? (
                <Notice tone="warn" className="mb-4">
                  An evaluation with this attestation id is already in the workspace. Adding it again replaces the stored copy; review notes are kept.
                </Notice>
              ) : null}
              <KeyValue
                items={[
                  ["Agent", staged.result.agent.name],
                  ["Attestation", <span key="a" className="font-mono text-[13px]">{staged.result.attestation.id}</span>],
                  ["Status", <StatusBadge key="s" status={staged.result.attestation.status} />],
                  ["Started", formatDateTime(staged.result.attestation.started_at)],
                  ["Runs recorded", String(staged.result.runs.length)],
                  ["Transcripts matched", `${Object.keys(staged.transcripts).length} of ${staged.result.runs.length}`],
                  ["Signed", staged.result.attestation.signature ? `yes, key ${staged.result.attestation.signing_key_id}` : "no"],
                  ["Format", <span key="f" className="font-mono text-[13px]">{staged.result.format}</span>],
                ]}
              />
              {staged.missingTranscripts.length ? (
                <Notice tone="warn" className="mt-4" title={`${staged.missingTranscripts.length} transcript file(s) missing`}>
                  The run evidence and the transcript hash check need them. Select the whole report folder, or add the transcripts/ files to the selection.
                </Notice>
              ) : null}
              {staged.unmatchedTranscripts.length ? (
                <Notice tone="warn" className="mt-4" title="Transcript files from another attestation were ignored">
                  {staged.unmatchedTranscripts.join(", ")}
                </Notice>
              ) : null}
              {staged.ignored.length ? <p className="mt-4 text-[13px] text-ink-soft">Ignored: {staged.ignored.join(", ")}</p> : null}
            </Card>
          ) : null}
        </div>

        <Card className="lg:sticky lg:top-24 lg:self-start">
          <CardHeader title="Where the folder is" as="h2" />
          <p className="text-small text-ink-soft">
            After <code className="code-inline">suncly attest</code> finishes it prints <code className="code-inline">Report: suncly-reports/&lt;attestation-id&gt;</code>. That folder holds:
          </p>
          <ul className="mt-3 flex flex-col gap-1.5 font-mono text-[13px] text-ink">
            <li>result.json</li>
            <li>transcripts/&lt;run-id&gt;.json</li>
            <li className="text-ink-soft">report.md, report.html (not needed here)</li>
          </ul>
          <p className="mt-4 text-small text-ink-soft">
            The evidence store itself (files under ~/.suncly or Postgres) is not read by this workspace; the report folder is the exchange format, and <code className="code-inline">suncly verify</code> works on the same folder.
          </p>
          <p className="mt-4 text-small text-ink-soft">
            Format details are in <Link href="/docs/evidence" className="font-semibold text-ink underline underline-offset-4">Evidence and reports</Link>.
          </p>
        </Card>
      </div>
    </>
  );
}
