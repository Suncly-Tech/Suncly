import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { Notice } from "@/components/ui/Notice";
import { DemoExplorer } from "@/components/demo/DemoExplorer";
import { demoPage } from "@/lib/content";
import { SAMPLE_NOTE } from "@/lib/sample";

export const metadata: Metadata = {
  title: "Sample evaluation",
  description:
    "Explore a complete Suncly evaluation of a fictional agent: declared skills, approved tests, passes, failures, inconclusive runs, evidence, a reviewer's decision, and what stayed untested.",
  alternates: { canonical: "/demo" },
};

export default function DemoPage() {
  return (
    <SiteLayout>
      <PageHeader eyebrow={demoPage.eyebrow} headline={demoPage.headline} intro={demoPage.intro}>
        <Notice tone="sample" title="Sample data, kept separate from real evaluations">
          {SAMPLE_NOTE} Loading it into the workspace marks every record as a sample.
        </Notice>
      </PageHeader>
      <Section tone="cream" className="pt-10!">
        <DemoExplorer />
      </Section>
      <FinalCta />
    </SiteLayout>
  );
}
