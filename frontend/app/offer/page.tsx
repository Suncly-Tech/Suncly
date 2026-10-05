import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { JsonLd } from "@/components/site/JsonLd";
import { Notice } from "@/components/ui/Notice";
import { offerPage } from "@/lib/content";
import { launch, pricing } from "@/lib/launch";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description = "Suncly charges for usage of the Suncly API and for nothing else: no seats, no plans. Connecting and the badge are free. Billing is not live yet.";

export const metadata: Metadata = pageMeta({ title: "Offer: usage-only pricing", description, path: "/offer", keywords: [...KEYWORDS.core, "Suncly pricing", "usage-based pricing"] });

export default function OfferPage() {
  const live = launch.usageBilling === "live";
  const s = offerPage.sections;
  return (
    <SiteLayout>
      <JsonLd data={graph(webPageLd({ path: "/offer", name: "Offer", description }), breadcrumbLd([{ name: "Offer", path: "/offer" }]))} />
      <PageHeader eyebrow="Suncly Offer" headline={offerPage.headline} intro={offerPage.intro} />
      <Section narrow>
        {!live ? (
          <Notice tone="info" title="Billing is not live" className="mb-10">
            No fees are charged yet. Pilot access is arranged with the team at <Link href="/access">/access</Link>. When charging starts, the Terms describe the notice you get.
          </Notice>
        ) : null}
        <article className="prose-site">
          <h2>{s.get.title}</h2>
          <ul>{s.get.items.map((i) => <li key={i}>{i}</li>)}</ul>
          <h2>{s.connect.title}</h2>
          <ul>{s.connect.items.map((i) => <li key={i}>{i}</li>)}</ul>
          <h2>{s.usage.title}</h2>
          <p>{s.usage.body}</p>
          <table tabIndex={0}>
            <thead><tr><th>Fact</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Model</td><td>Usage of the Suncly API only. No seats, no plans.</td></tr>
              <tr><td>Billable unit</td><td>{pricing.billableUnit ?? <em className="blank">not yet published</em>}</td></tr>
              <tr><td>Price and currency</td><td>{pricing.priceAndCurrency ?? <em className="blank">not yet published</em>}</td></tr>
              <tr><td>Billing period and payment method</td><td>{pricing.billingPeriodAndPaymentMethod ?? <em className="blank">not yet published</em>}</td></tr>
              <tr><td>Connecting an agent</td><td>Free.</td></tr>
              <tr><td>The badge</td><td>Free.</td></tr>
              <tr><td>Pilot terms</td><td>{pricing.pilotTerms ?? "Agreed per pilot, by email."}</td></tr>
            </tbody>
          </table>
          <h2>{s.never.title}</h2>
          <ul>{s.never.items.map((i) => <li key={i}>{i}</li>)}</ul>
          <h2>{s.invoices.title}</h2>
          <p>{s.invoices.body}</p>
          <h2>{s.stop.title}</h2>
          <p>{s.stop.body}</p>
          <p className="summary">The usage model is fixed; the numbers are not. Nothing on this page is a price until it says so.</p>
        </article>
      </Section>
    </SiteLayout>
  );
}
