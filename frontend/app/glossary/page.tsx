import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { JsonLd } from "@/components/site/JsonLd";
import { glossary } from "@/lib/glossary";
import { breadcrumbLd, definedTermSetLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description =
  "Plain definitions for AI agent evaluation: A2A protocol, Agent Card, attestation, contract, run, verdict, inconclusive, decision, probe, sandbox, card hash, signed evidence.";

export const metadata: Metadata = pageMeta({
  title: "AI agent evaluation glossary",
  description,
  path: "/glossary",
  keywords: [...KEYWORDS.protocol, ...KEYWORDS.evidence, "AI agent evaluation glossary", "what is an Agent Card", "what is agent attestation"],
});

export default function GlossaryPage() {
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          webPageLd({ path: "/glossary", name: "AI agent evaluation glossary", description, type: "CollectionPage" }),
          breadcrumbLd([{ name: "Suncly", path: "/" }, { name: "Glossary", path: "/glossary" }]),
          definedTermSetLd(glossary.map((t) => ({ term: t.term, definition: t.definition, anchor: t.anchor }))),
        )}
      />
      <PageHeader
        eyebrow="Glossary"
        headline="The words behind an evaluation, defined once."
        intro="Each term starts with a one-sentence definition you can quote, then what it means inside Suncly. Where a term names something planned rather than built, it says so."
      />
      <Section>
        <div className="grid gap-12 lg:grid-cols-[minmax(0,3fr)_minmax(0,9fr)] lg:gap-16">
          <nav aria-label="Terms" className="lg:sticky lg:top-28 lg:self-start">
            <p className="text-eyebrow text-ink-soft">Terms</p>
            <ol className="mt-4 flex flex-col gap-1 text-small">
              {glossary.map((t) => (
                <li key={t.anchor}>
                  <Link href={`#${t.anchor}`} className="inline-block py-1 text-ink-soft hover:text-ink">
                    {t.term}
                  </Link>
                </li>
              ))}
            </ol>
          </nav>
          <dl className="flex max-w-[760px] flex-col gap-8">
            {glossary.map((t) => (
              <div key={t.anchor} id={t.anchor} className="surface-card scroll-mt-24 p-6">
                <dt className="text-heading-md text-ink">{t.term}</dt>
                <dd className="mt-3 text-body text-ink">{t.definition}</dd>
                <dd className="mt-2 text-small text-ink-soft md:text-[15px]">{t.detail}</dd>
                {t.related?.length ? (
                  <dd className="mt-3 flex flex-wrap gap-2 text-[13px]">
                    <span className="text-ink-soft">See also:</span>
                    {t.related.map((anchor) => {
                      const target = glossary.find((x) => x.anchor === anchor);
                      return target ? (
                        <Link key={anchor} href={`#${anchor}`} className="font-semibold text-ink underline-offset-4 hover:underline">
                          {target.term}
                        </Link>
                      ) : null;
                    })}
                  </dd>
                ) : null}
              </div>
            ))}
          </dl>
        </div>
      </Section>
      <FinalCta />
    </SiteLayout>
  );
}
