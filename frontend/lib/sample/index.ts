/**
 * The sample evaluation: three attestations of a fictional agent, produced by
 * frontend/scripts/make-sample.py through the real Suncly code path. Synthetic data,
 * clearly labelled wherever it is shown. Regenerate with the script; do not edit by hand.
 */

import type { EvidenceBundle, ResultDocument } from "@/lib/evidence/types";
import baseline from "./harbor-1-baseline.json";
import regression from "./harbor-2-regression.json";
import budgetStop from "./harbor-3-budget-stop.json";

export interface SampleBundle extends EvidenceBundle {
  sample: { label: string; behaviour: string; generated_by: string; note: string };
  report_md: string;
}

function asBundle(raw: unknown): SampleBundle {
  const value = raw as { sample: SampleBundle["sample"]; result: ResultDocument; transcripts: Record<string, string>; report_md: string };
  return { sample: value.sample, result: value.result, transcripts: value.transcripts, report_md: value.report_md };
}

export const sampleBundles: SampleBundle[] = [asBundle(baseline), asBundle(regression), asBundle(budgetStop)];

export const sampleByLabel = (label: string): SampleBundle | undefined =>
  sampleBundles.find((b) => b.sample.label === label);

export const sampleAgentName = sampleBundles[0].result.agent.name;

export const SAMPLE_NOTE =
  "Sample data. A fictional agent evaluated by the real Suncly code path on a developer machine. Not a customer evaluation.";
