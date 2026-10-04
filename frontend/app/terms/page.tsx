import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { Notice } from "@/components/ui/Notice";
import { legal, site } from "@/lib/content";

export const metadata: Metadata = {
  title: "Terms",
  description: "Terms for using this website and taking part in the Suncly pilot.",
  alternates: { canonical: "/terms" },
  robots: { index: false },
};

export default function TermsPage() {
  return (
    <SiteLayout>
      <PageHeader eyebrow="Legal" headline="Terms" intro="Terms for using this website and taking part in the Suncly pilot." />
      <Section narrow>
        <Notice tone="warn" title="Draft, pending owner review" className="mb-10">
          {legal.draftNotice} No commercial terms, warranties or liability provisions are stated here until the owners supply them.
        </Notice>
        <article className="prose-site">
          <h2>Who we are</h2>
          <p>
            Suncly, {site.city}. Contact: <a href={`mailto:${site.email}`}>{site.email}</a>. Legal entity: <em>{legal.pending}</em>.
          </p>

          <h2>This website</h2>
          <p>
            The website describes the Suncly software and offers a way to request pilot access. The sample evaluation and the review workspace use synthetic data or data you load yourself; neither creates an account, and nothing on the site collects payment details.
          </p>

          <h2>The pilot</h2>
          <ul>
            <li>Pilot access is arranged by email and governed by the written agreement made for each pilot. Terms of that agreement: <em>{legal.pending}</em>.</li>
            <li>The software is in pilot. Its current capabilities and limits are stated on the <Link href="/product">product page</Link>; features marked planned are not promised for any date.</li>
            <li>You evaluate only agents and endpoints you are authorised to test, and you declare an endpoint a sandbox only when it is one. Suncly cannot verify a sandbox declaration.</li>
            <li>A completed evaluation, a signature or a decision record is evidence for your own review. It is not a certification, not a guarantee of the agent's future behaviour, and not a decision made by Suncly on your behalf.</li>
          </ul>

          <h2>Software licence</h2>
          <p>No licence has been chosen for the repository yet. Use during the pilot is under the pilot agreement. Licence: <em>{legal.pending}</em>.</p>

          <h2>Governing law</h2>
          <p><em>{legal.pending}</em>.</p>

          <h2>Changes</h2>
          <p>These terms will be replaced when the commercial offering and payment layer are introduced. Effective date: <em>{legal.pending}</em>.</p>
        </article>
      </Section>
    </SiteLayout>
  );
}
