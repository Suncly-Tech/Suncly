import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { SectionHeader } from "@/components/SectionHeader";
import { Badge } from "@/components/ui/Badge";
import { docsPage } from "@/lib/content";

export const metadata: Metadata = {
  title: "Documentation",
  description: docsPage.intro,
  alternates: { canonical: "/docs" },
};

export default function DocsPage() {
  return (
    <SiteLayout>
      <PageHeader eyebrow={docsPage.title} headline={docsPage.headline} intro={docsPage.intro} />

      <Section>
        <SectionHeader label="Guides" headline="Start here." />
        <ul className="mt-10 grid gap-4 md:grid-cols-3">
          {docsPage.guides.map((g) => (
            <li key={g.href}>
              <Link href={g.href} className="surface-card group flex h-full flex-col gap-3 p-6 transition-shadow hover:shadow-raised">
                <h3 className="text-heading-md text-ink">{g.title}</h3>
                <p className="text-small text-ink-soft md:text-[15px]">{g.body}</p>
                <span className="mt-auto inline-flex items-center gap-1.5 text-[14px] font-semibold text-ink">
                  Read
                  <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section tone="paper">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeader label="Repository documents" headline="Eleven documents. One source of truth." intro="In the repository today. Access to the repository comes with the pilot." />
          <Badge tone="info">With pilot access</Badge>
        </div>
        <ol className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {docsPage.repositoryDocs.map((d) => (
            <li key={d.file} className="surface flex flex-col p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-control bg-cream text-ink">
                  <FileText size={16} aria-hidden="true" />
                </span>
                <span className="font-mono text-[12px] text-ink-soft">{d.file}</span>
              </div>
              <h3 className="mt-4 text-heading-md text-ink">{d.title}</h3>
              <p className="mt-1.5 text-small text-ink-soft">{d.body}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section tone="ink">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <h2 className="text-display-md text-paper">{docsPage.howToRead.title}</h2>
          <ul className="flex flex-col gap-4">
            {docsPage.howToRead.items.map((it) => (
              <li key={it} className="cuts-bullet text-sun">
                <span className="text-body text-paper/85">{it}</span>
              </li>
            ))}
          </ul>
        </div>
      </Section>
      <FinalCta />
    </SiteLayout>
  );
}
