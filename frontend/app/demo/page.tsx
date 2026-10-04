import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { Notice } from "@/components/ui/Notice";
import { DemoExplorer } from "@/components/demo/DemoExplorer";
import { demoPage } from "@/lib/content";
import { SAMPLE_NOTE } from "@/lib/sample";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description =
  "A sample AI agent evaluation: a fictional A2A agent, approved tests, a pass, a failure, an inconclusive run, signed evidence, a reviewer's decision and what stayed untested.";

export const metadata: Metadata = pageMeta({
  title: "Sample AI agent evaluation: failure to decision",
  description,
  path: "/demo",
  keywords: [...KEYWORDS.core, ...KEYWORDS.evidence, "AI agent evaluation example", "agent evaluation demo"],
});

export default function DemoPage() {
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          webPageLd({ path: "/demo", name: "Sample AI agent evaluation", description }),
          breadcrumbLd([{ name: "Suncly", path: "/" }, { name: "Sample evaluation", path: "/demo" }]),
        )}
      />
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
