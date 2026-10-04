import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { SectionHeader } from "@/components/SectionHeader";
import { AvailabilityBadge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { Faq } from "@/components/Faq";
import { byGroup, type Capability } from "@/lib/capabilities";
import { faq, productPage } from "@/lib/content";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbLd, faqLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description =
  "AI agent evaluation with Suncly: tests from declared A2A skills, human-approved plans, repeated sandbox runs, deterministic verdicts, signed evidence and explicit coverage gaps.";

export const metadata: Metadata = pageMeta({
  title: "AI agent evaluation: tests, evidence and approval",
  description,
  path: "/product",
  keywords: [...KEYWORDS.core, ...KEYWORDS.evidence],
});

export default function ProductPage() {
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          webPageLd({ path: "/product", name: "AI agent evaluation: tests, evidence and approval", description }),
          breadcrumbLd([{ name: "Suncly", path: "/" }, { name: "Product", path: "/product" }]),
          faqLd(faq.items),
        )}
      />
      <PageHeader eyebrow={productPage.title} headline={productPage.headline} intro={productPage.intro}>
        <dl className="grid gap-3 sm:grid-cols-3">
          {(["available", "limited", "planned"] as const).map((status) => (
            <div key={status} className="surface flex flex-col gap-2 p-4">
              <dt>
                <AvailabilityBadge status={status} />
              </dt>
              <dd className="text-[13px] leading-snug text-ink-soft">{productPage.legend[status]}</dd>
            </div>
          ))}
        </dl>
      </PageHeader>

      {productPage.groups.map((group, i) => (
        <Section key={group.id} id={group.id} tone={i % 2 === 0 ? "cream" : "paper"}>
          <div className="grid gap-10 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
            <div className="lg:sticky lg:top-28 lg:self-start">
              <SectionHeader label={group.title} headline={group.body} />
              <nav aria-label={`${group.title} sections`} className="mt-6 hidden lg:block">
                <ul className="flex flex-col gap-1 text-small text-ink-soft">
                  {productPage.groups.map((g) => (
                    <li key={g.id}>
                      <Link href={`#${g.id}`} className={`inline-block py-1 hover:text-ink ${g.id === group.id ? "font-semibold text-ink" : ""}`}>
                        {g.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            </div>
            <ul className="flex flex-col gap-4">
              {byGroup(group.id as Capability["group"]).map((item) => (
                <CapabilityCard key={item.id} item={item} />
              ))}
            </ul>
          </div>
        </Section>
      ))}

      <Section tone="ink">
        <SectionHeader
          label="Risk levels and policy"
          headline="Risk is recorded today. It decides nothing yet."
          intro="Every agent carries a risk level, recorded on first sight (default high). The default approval policy below is the design; its thresholds are a customer configuration that does not exist yet, so every decision is flag."
          tone="paper"
        />
        <div className="mt-10 max-w-[820px]">
          <Table caption="Default approval policy by risk level, as designed">
            <thead>
              <tr>
                <th scope="col">Risk level</th>
                <th scope="col">Example</th>
                <th scope="col">Approval, as designed</th>
                <th scope="col">Today</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["low", "read-only lookup", "automatic on pass"],
                ["medium", "writes to internal systems", "automatic on pass, human on any drop"],
                ["high", "payments, personal data", "human sign-off every time"],
              ].map(([level, example, approval]) => (
                <tr key={level}>
                  <td className="font-mono text-[13px]">{level}</td>
                  <td className="text-ink-soft">{example}</td>
                  <td className="text-ink">{approval}</td>
                  <td className="text-ink-soft">flag; a human decides</td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p className="mt-4 text-small text-paper/70">
            A human is always required for the first contract approval, for new or changed skills, for borderline or dropping results, and for every evaluation of a high-risk agent. Suncly ships no threshold numbers of its own.
          </p>
        </div>
      </Section>

      <Faq />
      <FinalCta />
    </SiteLayout>
  );
}

function CapabilityCard({ item }: { item: Capability }) {
  return (
    <li className="surface-card flex flex-col gap-3 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h3 className="text-heading-md text-ink">{item.name}</h3>
        <AvailabilityBadge status={item.status} />
      </div>
      <p className="text-body text-ink">{item.summary}</p>
      <p className="text-small text-ink-soft">
        <span className="font-semibold text-ink">Why it matters: </span>
        {item.benefit}
      </p>
      {item.limit ? (
        <p className="rounded-[12px] bg-cream px-4 py-3 text-small text-ink">
          <span className="font-semibold">{item.status === "planned" ? "Not yet: " : "Limit: "}</span>
          {item.limit}
        </p>
      ) : null}
      <details className="text-[13px] text-ink-soft">
        <summary className="cursor-pointer font-semibold text-ink-soft hover:text-ink">Where this lives in the code</summary>
        <p className="mt-1 font-mono">{item.evidence}</p>
      </details>
    </li>
  );
}
