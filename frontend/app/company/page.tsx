import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { SectionHeader } from "@/components/SectionHeader";
import { KeyValue } from "@/components/ui/Stat";
import { companyPage } from "@/lib/content";

export const metadata: Metadata = {
  title: "Company",
  description: companyPage.intro,
  alternates: { canonical: "/company" },
};

export default function CompanyPage() {
  return (
    <SiteLayout>
      <PageHeader eyebrow={companyPage.title} headline={companyPage.headline} intro={companyPage.intro} />
      <Section>
        <SectionHeader label="How we work" headline="Three rules we apply to ourselves." />
        <ul className="mt-10 grid gap-4 md:grid-cols-3">
          {companyPage.principles.map((p) => (
            <li key={p.title} className="surface-card flex flex-col gap-3 p-6 md:p-8">
              <h3 className="text-heading-md text-ink">{p.title}</h3>
              <p className="text-body text-ink-soft">{p.body}</p>
            </li>
          ))}
        </ul>
      </Section>
      <Section tone="paper" narrow>
        <SectionHeader label="Contact" headline={companyPage.contact.title} />
        <div className="mt-8 surface p-6">
          <KeyValue
            items={[
              ["Email", <a key="e" href={`mailto:${companyPage.contact.email}`} className="font-semibold text-ink underline underline-offset-4">{companyPage.contact.email}</a>],
              ["Location", companyPage.contact.location],
              ["Registration", <span key="r" className="text-ink-soft">{companyPage.contact.registration}</span>],
            ]}
          />
        </div>
      </Section>
      <FinalCta />
    </SiteLayout>
  );
}
