import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { SectionHeader, SectionLabel } from "@/components/SectionHeader";
import { AccessForm } from "@/components/site/AccessForm";
import { Notice } from "@/components/ui/Notice";
import { accessPage } from "@/lib/content";

export const metadata: Metadata = {
  title: "Access",
  description: accessPage.intro,
  alternates: { canonical: "/access" },
};

export default function AccessPage() {
  const a = accessPage;
  return (
    <SiteLayout>
      <PageHeader eyebrow={a.title} headline={a.headline} intro={a.intro} />
      <Section>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="surface-card p-6 md:p-8">
            <h2 className="text-heading-md text-ink">{a.whatYouGet.title}</h2>
            <ul className="mt-4 flex flex-col gap-3">
              {a.whatYouGet.items.map((item) => (
                <li key={item} className="cuts-bullet text-sun">
                  <span className="text-small text-ink md:text-[15px]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="surface-card p-6 md:p-8">
            <h2 className="text-heading-md text-ink">{a.whatYouNeed.title}</h2>
            <ul className="mt-4 flex flex-col gap-3">
              {a.whatYouNeed.items.map((item) => (
                <li key={item} className="cuts-bullet text-sun">
                  <span className="text-small text-ink md:text-[15px]">{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="surface-card p-6 md:p-8">
            <h2 className="text-heading-md text-ink">{a.billing.title}</h2>
            <p className="mt-4 text-small text-ink-soft md:text-[15px]">{a.billing.body}</p>
            <Notice tone="info" className="mt-4">
              No prices are published, no checkout exists, and no payment details are collected anywhere on this site.
            </Notice>
          </div>
        </div>
      </Section>
      <Section id="request" tone="ink">
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <SectionLabel tone="paper">Pilot</SectionLabel>
            <h2 className="mt-5 text-display-lg text-paper">{a.form.headline}</h2>
            <p className="mt-6 max-w-[480px] text-body text-paper/70">{a.form.body}</p>
          </div>
          <AccessForm />
        </div>
      </Section>
      <Section tone="paper" narrow>
        <SectionHeader label="Already have access?" headline="Install the CLI and run the demo." intro="The getting-started guide takes five minutes and ends with a signed, verifiable report on your machine." />
        <a href="/docs/getting-started" className="btn-base btn-secondary mt-8">
          Getting started
        </a>
      </Section>
    </SiteLayout>
  );
}
