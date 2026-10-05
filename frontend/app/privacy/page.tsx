import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { Notice } from "@/components/ui/Notice";
import { legal, site } from "@/lib/content";

export const metadata: Metadata = {
  title: "Privacy",
  description: "How this website and the Suncly software handle data.",
  alternates: { canonical: "/privacy" },
  robots: { index: false },
};

export default function PrivacyPage() {
  return (
    <SiteLayout>
      <PageHeader eyebrow="Legal" headline="Privacy notice" intro="How this website and the Suncly software handle data." />
      <Section narrow>
        <Notice tone="warn" title="Draft, pending owner review" className="mb-10">
          {legal.draftNotice}
        </Notice>
        <article className="prose-site">
          <h2>Who is responsible</h2>
          <p>
            Suncly, {site.city}. Contact: <a href={`mailto:${site.email}`}>{site.email}</a>. Legal entity name, registration number and registered address: <em>{legal.pending}</em>.
          </p>

          <h2>This website</h2>
          <ul>
            <li>The site is static. It sets no cookies of its own and runs no analytics or advertising scripts.</li>
            <li>The hosting provider receives the technical data any web request carries (IP address, user agent, requested page) in its server logs. Provider and log retention: <em>{legal.pending}</em>.</li>
            <li>
              The pilot access form sends the email address and optional note you enter either to the endpoint configured for the site or, when none is configured, to your own mail client addressed to {site.email}. We use it only to reply to you about pilot access. Storage location and retention of these requests: <em>{legal.pending}</em>.
            </li>
            <li>
              The review workspace at <Link href="/app">/app</Link> stores the evaluation bundles and review notes you load in your browser's local storage only. Nothing you load there is sent to Suncly or to any server. You can remove it from the workspace settings or by clearing your browser's site data.
            </li>
          </ul>

          <h2>The Suncly software</h2>
          <p>Suncly is a command-line tool you run on your own machine or network. In its current version it has no hosted component and sends no data to Suncly. What it reads, stores and redacts is described on the <Link href="/security">security and data handling page</Link>, in summary:</p>
          <ul>
            <li>It fetches the Agent Card URL you give it and calls the agent endpoint named in that card, and nothing else.</li>
            <li>It reads one credential from an environment variable inside the Runner process and redacts it from every transcript before storage.</li>
            <li>It writes evidence (entity records, redacted transcripts, signing keys, report folders) to the folders or database you configure. The evidence store is append-only; deletion is done by you, by removing files or dropping the database.</li>
            <li>It makes no call to any model provider in this version.</li>
          </ul>
          <p>Transcripts may contain whatever the agent under test sends back. If an agent returns personal data in a sandbox response, that data is in your transcripts; the redaction rules target credentials and tokens, not personal data in general.</p>

          <h2>Your rights and how to contact us</h2>
          <p>
            Requests about personal data held in connection with pilot access can be sent to <a href={`mailto:${site.email}`}>{site.email}</a>. Applicable law and supervisory authority: <em>{legal.pending}</em>.
          </p>

          <h2>Changes</h2>
          <p>This notice will be updated before a hosted deployment accepts customer data; its account model (OpenID Connect identities, organizations) and billing in test mode exist in the software but no hosted service is operated today. Effective date: <em>{legal.pending}</em>.</p>
        </article>
      </Section>
    </SiteLayout>
  );
}
