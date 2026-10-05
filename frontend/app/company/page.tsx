import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { SectionHeader } from "@/components/SectionHeader";
import { KeyValue } from "@/components/ui/Stat";
import { Faq } from "@/components/Faq";
import { companyPage } from "@/lib/content";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbLd, faqLd, graph, pageMeta, webPageLd } from "@/lib/seo";

const description =
  "Suncly is an AI agent evaluation tool for the A2A protocol, built by a small team in Tallinn, Estonia. What we build, how we work, and how to reach us.";

export const metadata: Metadata = pageMeta({
  title: "About Suncly: AI agent evaluation from Tallinn",
  description,
  path: "/company",
  keywords: ["about Suncly", "Suncly company", "Suncly Tallinn", "Suncly contact", "who makes Suncly"],
});

export default function CompanyPage() {
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          webPageLd({ path: "/company", name: "About Suncly", description, type: "AboutPage" }),
          breadcrumbLd([{ name: "Suncly", path: "/" }, { name: "Company", path: "/company" }]),
          faqLd(companyPage.faq),
        )}
      />
      <PageHeader eyebrow={companyPage.title} headline={companyPage.headline} intro={companyPage.intro} />
      <Section>
        <SectionHeader label="How we work" headline="Three rules we apply to ourselves." />
        <ul className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
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
      <Faq items={companyPage.faq} label="About Suncly" headline="Questions about Suncly." id="about-faq" />
      <FinalCta />
    </SiteLayout>
  );
}
