import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { Blank, DocMeta, DraftNotice, Summary, Toc } from "@/components/site/Legal";
import { site } from "@/lib/content";
import { company, launch, missingLegalFacts } from "@/lib/launch";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Privacy Policy",
  description: "How this website, the pilot form, the Suncly command-line tool and the planned hosted API handle personal data.",
  path: "/privacy",
  noindex: !launch.legalPublished,
});

const toc = [
  { id: "who", title: "Who we are" },
  { id: "contexts", title: "Three contexts" },
  { id: "data", title: "The data we handle" },
  { id: "purposes", title: "Purposes and legal bases" },
  { id: "recipients", title: "Recipients, processors and transfers" },
  { id: "retention", title: "Retention and deletion" },
  { id: "rights", title: "Your rights" },
  { id: "cookies", title: "Cookies and storage" },
  { id: "automated", title: "Automated decisions" },
  { id: "children", title: "Children" },
  { id: "security", title: "Security" },
  { id: "roles", title: "When a customer tests an agent with us" },
  { id: "hosted", title: "The hosted API, accounts and billing" },
  { id: "changes", title: "Changes and version history" },
];

export default function PrivacyPage() {
  const hosted = launch.httpApi === "live";
  const missing = missingLegalFacts().filter((m) => !["repository licence", "governing law and court"].includes(m));
  return (
    <SiteLayout>
      <PageHeader eyebrow="Legal" headline="Privacy Policy" intro="Three contexts, kept apart because they differ in fact: this website and the pilot form; the Suncly command-line tool on your own machines; and the hosted API, accounts and billing, which do not exist yet." />
      <Section narrow>
        <DraftNotice page="Privacy Policy" needs={missing} />
        <article className="prose-site">
          <DocMeta version="0.2 (draft)" effective={null} changes={[{ date: "2026-10-04", note: "First draft." }, { date: "2026-10-05", note: "Complete draft in the new structure, with the hosted sections written and switched off." }]} />
          <Toc items={toc} />

          <h2 id="who">1. Who we are and how to reach us</h2>
          <Summary>Suncly, in Tallinn. Write to us by e-mail.</Summary>
          <p>
            The controller for the data described in sections 3 to 11 is {company.legalEntityName ?? <Blank what="legal entity name" />}, registry code {company.registryCode ?? <Blank what="registry code" />}, {company.registeredOffice ?? <Blank what="registered office" />}, {site.city} ("Suncly", "we"). Contact: <a href={`mailto:${site.email}`}>{site.email}</a>. Privacy questions: {company.privacyContactEmail ?? <Blank what="privacy contact address" />}. We have not appointed a data protection officer; nothing in our processing requires one today.
          </p>

          <h2 id="contexts">2. Three contexts</h2>
          <Summary>The website and the pilot form collect a little. The command-line tool sends us nothing. The hosted API does not exist yet.</Summary>
          <ol>
            <li><strong>This website and the pilot form.</strong> Sections 3 to 11 describe it.</li>
            <li><strong>The Suncly command-line tool.</strong> It runs on your own machine or network. In this version it has no hosted component and sends no data to Suncly: it fetches the Agent Card URL you give it and calls the agent endpoint named in that card, and nothing else (verified in the code, see <Link href="/data">/data</Link>). Whatever it stores, it stores where you configured; you are the controller of that data, and section 12 says what that means.</li>
            <li><strong>The hosted API, accounts and billing.</strong> Planned. Section 13 is written now and applies from the day those exist; until then it describes nothing that happens.</li>
          </ol>

          <h2 id="data">3. The data we handle and where it comes from</h2>
          <Summary>A work e-mail address and an optional note from the pilot form; server logs from the host; nothing from the tool.</Summary>
          <table tabIndex={0}>
            <thead><tr><th>Data</th><th>Source</th><th>Context</th></tr></thead>
            <tbody>
              <tr><td>Work e-mail address and the optional note you type (which may name your employer and the agent you want to evaluate)</td><td>You, through the pilot form on <Link href="/access">/access</Link>, or your own e-mail client when the form opens one</td><td>Website</td></tr>
              <tr><td>Correspondence with us</td><td>You</td><td>Website, pilot</td></tr>
              <tr><td>Technical data any web request carries: IP address, user agent, requested page, time</td><td>Your browser, received by the hosting provider's servers</td><td>Website</td></tr>
              <tr><td>Personal data that may appear inside agent transcripts (for example a name or an order reference an agent returns in a sandbox answer)</td><td>The agent under test; stored by the tool on your machine, never sent to us in this version</td><td>Command-line tool (you are the controller)</td></tr>
            </tbody>
          </table>
          <p>We do not buy, enrich or receive personal data about you from third parties.</p>

          <h2 id="purposes">4. Purposes and legal bases</h2>
          <Summary>We answer your request, keep the site running, and keep records the law requires. One table.</Summary>
          <table tabIndex={0}>
            <thead><tr><th>Purpose</th><th>Data</th><th>Legal basis (GDPR Article 6(1))</th></tr></thead>
            <tbody>
              <tr><td>Answering a pilot request and arranging a pilot</td><td>E-mail, note, correspondence</td><td>(b) steps at your request before a contract, or (f) our legitimate interest in answering a business enquiry</td></tr>
              <tr><td>Serving the website securely and diagnosing faults</td><td>Server logs</td><td>(f) our legitimate interest in a working, secure site</td></tr>
              <tr><td>Keeping accounting records</td><td>Invoices and contracts, once any exist</td><td>(c) legal obligation (Accounting Act, seven years)</td></tr>
              <tr><td>Sending you news about Suncly</td><td>E-mail</td><td>(a) your consent, asked separately; every message carries an opt-out. We do not send marketing e-mail today.</td></tr>
            </tbody>
          </table>

          <h2 id="recipients">5. Recipients, processors and transfers</h2>
          <Summary>Our hosting, DNS, database and e-mail providers see what they must to run the service. Their names, locations and safeguards are listed here once confirmed.</Summary>
          <table tabIndex={0}>
            <thead><tr><th>Role</th><th>Provider</th><th>Location and transfer safeguard</th></tr></thead>
            <tbody>
              <tr><td>Hosting of this website</td><td>{company.hosting.provider}{company.hosting.confirmed ? "" : " (to be confirmed)"}</td><td>{company.hosting.regions ?? <Blank what="hosting regions and transfer safeguard" />}</td></tr>
              <tr><td>DNS</td><td>{company.dns.provider}{company.dns.confirmed ? "" : " (to be confirmed)"}</td><td><Blank what="DNS provider location and safeguard" /></td></tr>
              <tr><td>Database (hosted service, when it exists)</td><td>{company.database.provider}{company.database.confirmed ? "" : " (to be confirmed)"}</td><td>{company.database.regions ?? <Blank what="database regions" />}</td></tr>
              <tr><td>Pilot form endpoint and storage</td><td>{company.pilotFormEndpointAndStorage ?? <Blank what="pilot form endpoint and where submissions are stored" />}</td><td><Blank what="location and safeguard" /></td></tr>
              <tr><td>E-mail</td><td><Blank what="e-mail provider" /></td><td><Blank what="location and safeguard" /></td></tr>
              <tr><td>Payments (when billing is live)</td><td><Blank what="payment provider" /></td><td><Blank what="location and safeguard" /></td></tr>
              <tr><td>Model providers</td><td>None. The software calls no model provider in this version.</td><td>Not applicable</td></tr>
            </tbody>
          </table>
          <p>Each processor acts under a written agreement meeting GDPR Article 28. Where a provider processes data outside the European Economic Area, we rely on an adequacy decision or the European Commission's standard contractual clauses, named in the table. We do not sell personal data and we run no analytics ({company.analytics}).</p>

          <h2 id="retention">6. Retention and deletion by category</h2>
          <Summary>We keep enquiries while we deal with them, logs briefly, invoices for seven years.</Summary>
          <table tabIndex={0}>
            <thead><tr><th>Category</th><th>Retention</th><th>Deletion</th></tr></thead>
            <tbody>
              <tr><td>Pilot requests and correspondence</td><td>{company.retentionPeriods ?? <Blank what="retention period for enquiries" />}</td><td>Deleted from our mailbox and the form's storage at the end of the period, or earlier on request</td></tr>
              <tr><td>Server logs</td><td><Blank what="hosting provider's log retention" /></td><td>Rotated by the provider</td></tr>
              <tr><td>Accounting records</td><td>Seven years from the end of the financial year (Accounting Act)</td><td>Deleted after the period</td></tr>
              <tr><td>Data the command-line tool stores on your machine</td><td>Yours to decide</td><td>You delete files or drop the database; see <Link href="/data">/data</Link></td></tr>
            </tbody>
          </table>

          <h2 id="rights">7. Your rights, how to use them, and how to complain</h2>
          <Summary>Access, correction, deletion, restriction, portability, objection. We answer within one month. You can complain to the Estonian Data Protection Inspectorate.</Summary>
          <p>You have the rights GDPR gives you: to access the personal data we hold about you, to have it corrected or deleted, to restrict or object to its processing, to receive it in a portable form, and to withdraw a consent at any time without affecting what was done before. Write to <a href={`mailto:${site.email}`}>{site.email}</a> or to {company.privacyContactEmail ?? <Blank what="privacy contact address" />}. We answer without undue delay and at the latest within one month; if a request is complex we may extend that by two months and will tell you why.</p>
          <p>You may complain to the Estonian Data Protection Inspectorate (Andmekaitse Inspektsioon), Tatari 39, 10134 Tallinn, <a href="mailto:info@aki.ee">info@aki.ee</a>, <a href="https://www.aki.ee/en" rel="noopener noreferrer">aki.ee</a>, or to the supervisory authority of the EU country where you live or work.</p>

          <h2 id="cookies">8. Cookies and storage, as inspected</h2>
          <Summary>No cookies, no trackers. The workspace keeps its data in your browser only.</Summary>
          <p>This site sets no cookies and loads nothing from third parties; fonts are self-hosted. The review workspace at <Link href="/app">/app</Link> stores the evaluation bundles and review notes you load in your browser's local storage only, at your request; nothing you load there is sent to Suncly. The inspected table is on <Link href="/cookies">/cookies</Link>.</p>

          <h2 id="automated">9. Automated decisions</h2>
          <Summary>None about people. Evaluations concern software.</Summary>
          <p>We make no decision about a person by automated means. Suncly's evaluations and the Suncly Certified programme concern software agents; the evaluation's decision record is always <code>flag</code> in this version, which means a human reviews it, and a certification decision is taken by a named person.</p>

          <h2 id="children">10. Children</h2>
          <Summary>This is a business service.</Summary>
          <p>The website and the service are for business use and are not directed at children. We do not knowingly collect personal data from anyone under 16; if you believe we have, write to us and we will delete it.</p>

          <h2 id="security">11. Security in summary</h2>
          <Summary>Few data, few places, and the measures on the security page.</Summary>
          <p>We hold little personal data and keep it in as few places as possible. The command-line tool's measures (one credential read only by an isolated Runner process, redaction of every transcript, append-only evidence, signing) are described on <Link href="/security">/security</Link>, together with how to report a vulnerability. If a personal data breach is likely to result in a risk to you, we notify the Data Protection Inspectorate within 72 hours of becoming aware of it and inform you where the risk is high.</p>

          <h2 id="roles">12. When a customer tests an agent with us</h2>
          <Summary>Today you run the tool and you are the controller. Once we host it, we are your processor under a written agreement.</Summary>
          <p>In this version the customer runs the Suncly tool on its own machines. Everything the tool stores (the card, the test plan, redacted transcripts, reports) is stored where the customer configured, and the customer is the controller of any personal data in it. Suncly receives none of it.</p>
          <p>Once Suncly hosts evaluations (section 13), the customer remains the controller of the data it submits and of the transcripts the agent returns, and Suncly acts as its processor under a data processing agreement meeting GDPR Article 28, with the sub-processor list published at that time. Suncly will act as a controller only for account, contact and billing data.</p>

          <h2 id="hosted">13. The hosted API, accounts and billing</h2>
          <Summary>Written now, in force only when these exist.</Summary>
          {!hosted ? <p><strong>This section does not apply yet.</strong> There is no hosted API, no account system and no billing. It will apply from the day they go live, and this policy's version and effective date will change then.</p> : null}
          <p>When the hosted API exists: we will process an account holder's name, work e-mail, organisation and API keys to provide the service (Article 6(1)(b)); usage records per API key to meter and invoice usage (Article 6(1)(b) and (c)); billing details through a payment provider named in section 5 (we will not store card numbers); and, as a processor, the Agent Cards, test plans, redacted transcripts and reports of evaluations run through the API, under the customer's instructions. Evidence stored by Suncly is append-only by design; the data processing agreement will state how erasure requests are met against append-only evidence, a question recorded as open in our handoff notes until counsel settles it.</p>

          <h2 id="changes">14. Changes and version history</h2>
          <Summary>Versions and dates are at the top of this page.</Summary>
          <p>We change this policy when the facts change: at the latest when the hosted API, accounts or billing go live. Every change gets a new version number and effective date in the table at the top, and a material change is announced on this page thirty days before it takes effect.</p>
        </article>
      </Section>
    </SiteLayout>
  );
}
