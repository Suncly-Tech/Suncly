import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { JsonLd } from "@/components/site/JsonLd";
import { Picture } from "@/components/Picture";
import { researchPage } from "@/lib/content";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description = "Suncly Research: short notes on what a signed evaluation of an A2A agent proves and what it cannot, drafted from facts the repository verifies.";

export const metadata: Metadata = pageMeta({ title: "Research: what evidence can tell you", description, path: "/research", keywords: [...KEYWORDS.evidence, "AI agent evaluation research"] });

export default function ResearchPage() {
  const r = researchPage;
  return (
    <SiteLayout>
      <JsonLd data={graph(webPageLd({ path: "/research", name: "Research", description }), breadcrumbLd([{ name: "Research", path: "/research" }]))} />
      <PageHeader eyebrow="Suncly Research" headline={r.headline} intro={r.intro} />
      <Section>
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,6fr)_minmax(0,6fr)] lg:gap-16">
          <div>
            <p className="text-eyebrow text-ember">{r.state}</p>
            <ol className="mt-6 flex list-none flex-col divide-y divide-line border-y border-line p-0">
              {r.drafts.map((note, i) => (
                <li key={note.title} className="grid grid-cols-1 gap-2 py-6 sm:grid-cols-[48px_minmax(0,1fr)]">
                  <span className="text-eyebrow text-ink-mute">0{i + 1}</span>
                  <div>
                    <h2 className="font-display text-[26px] leading-tight text-ink">{note.title}</h2>
                    <p className="mt-2 max-w-[52ch] text-body text-ink-soft">{note.summary}</p>
                    <p className="mt-2 text-eyebrow text-ink-mute">Draft · in founder review · not published</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-6 max-w-[60ch] text-small text-ink-soft">
              Every published note will carry its author, date, method, limits and sources, and will enter the sitemap only then.
            </p>
          </div>
          <Picture name="analemma" alt="Small brass discs pinned to a plaster wall in a figure of eight, each with its own shadow: the sun's analemma." sizes="(min-width: 1024px) 45vw, 100vw" className="aspect-[4/3]" />
        </div>
      </Section>
    </SiteLayout>
  );
}
