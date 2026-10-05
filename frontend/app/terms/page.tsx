import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import {
  Blank,
  DocMeta,
  DraftNotice,
  Summary,
  Toc,
} from "@/components/site/Legal";
import { site, stand } from "@/lib/content";
import { certification, company, launch, pricing } from "@/lib/launch";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Terms of Service",
  description:
    "The terms on which Suncly provides the command-line tool, the pilot, and the planned hosted API with usage-only billing.",
  path: "/terms",
  noindex: !launch.legalPublished,
});

const toc = [
  { id: "parties", title: "Parties and business use" },
  { id: "service", title: "The service and its status" },
  { id: "accounts", title: "Accounts, API keys and acceptable use" },
  { id: "authority", title: "Authority to test" },
  { id: "fees", title: "Fees" },
  { id: "evidence", title: "Evidence, reports and intellectual property" },
  { id: "certification", title: "Certification" },
  { id: "confidentiality", title: "Confidentiality and data protection" },
  { id: "warranties", title: "Warranties and disclaimers" },
  { id: "liability", title: "Liability" },
  { id: "changes", title: "Changes to these terms" },
  { id: "term", title: "Term, suspension and termination" },
  { id: "law", title: "Governing law and court" },
  { id: "conclusion", title: "How the contract is concluded" },
];

export default function TermsPage() {
  const billing = launch.usageBilling === "live";
  const hosted = launch.httpApi === "live";
  const missing = [
    "legal entity name",
    "registry code",
    "registered office",
    "governing law and court",
    "repository licence",
  ];
  if (!pricing.billableUnit)
    missing.push("billable unit, price, billing period");
  return (
    <SiteLayout>
      <PageHeader
        eyebrow="Legal"
        headline="Terms of Service"
        intro="For businesses that use the Suncly command-line tool, take part in a pilot, or, once it exists, use the hosted Suncly API. Plain English, one summary line per section."
      />
      <Section narrow>
        <DraftNotice page="Terms of Service" needs={missing} />
        <article className="prose-site">
          <DocMeta
            version="0.2 (draft)"
            effective={null}
            changes={[
              { date: "2026-10-04", note: "First draft." },
              {
                date: "2026-10-05",
                note: "Complete draft: authority to test, usage-only fees, certification by reference, liability with carve-outs, hosted sections switched off.",
              },
            ]}
          />
          <Toc items={toc} />

          <h2 id="parties">1. Parties and business use</h2>
          <Summary>
            A contract between your business and Suncly. Not for consumers.
          </Summary>
          <p>
            These terms are a contract between{" "}
            {company.legalEntityName ?? <Blank what="legal entity name" />},
            registry code{" "}
            {company.registryCode ?? <Blank what="registry code" />},{" "}
            {company.registeredOffice ?? <Blank what="registered office" />},{" "}
            {site.city} ("Suncly", "we") and the organisation that uses the
            service ("you", "the customer"). The service is for business use
            only; by using it you confirm that you act in the course of a
            business and that the person accepting these terms may bind you.
          </p>

          <h2 id="service">2. The service and its status</h2>
          <Summary>
            A command-line tool in pilot. The hosted API, model-based judging
            and probes are planned, and nothing here promises them.
          </Summary>
          <p>
            Suncly tests an A2A agent against what its Agent Card claims and
            produces signed evidence. Today the service is the Suncly
            command-line tool, provided from the public repository and used with
            pilot customers. Features marked "Pilot" on the site exist and are
            used with pilots; features marked "Planned" (the hosted HTTP API,
            model-based judging, probes, automatic approve or block decisions,
            registry adapters) are not provided, and we promise no date. No
            service level is offered for the pilot; if a service level is
            offered later it will be written into a separate order.
          </p>

          <h2 id="accounts">3. Accounts, API keys and acceptable use</h2>
          <Summary>
            No accounts exist yet. When they do, keep keys secret and use the
            service only for testing agents you are allowed to test.
          </Summary>
          {!hosted ? (
            <p>
              <strong>Accounts and API keys do not exist yet.</strong> The
              following applies from the day the hosted API goes live.
            </p>
          ) : null}
          <p>
            You are responsible for the people who use your account and for
            keeping API keys confidential; tell us at once if a key is
            compromised. You will not use the service to test a system you have
            no authority to test (section 4), to interfere with the service or
            other customers, to circumvent rate or budget limits, to resell the
            service, or in breach of law. We may set reasonable rate and budget
            limits and will publish them.
          </p>

          <h2 id="authority">4. Authority to test</h2>
          <Summary>
            You confirm you may test the agent, the endpoint is a sandbox, and
            you will stop if we ask. Testing without authority can be a crime.
          </Summary>
          <p>
            By pointing Suncly at an agent you confirm that you operate that
            agent or have the operator's permission to test it, and that the
            endpoint you declare is a sandbox or dry-run endpoint where nothing
            real is booked, paid or deleted. Suncly cannot verify that an
            endpoint is a sandbox; the declaration is yours and is recorded as
            such. You accept the rate and budget limits in force, you will stop
            testing at our request, and we may suspend the service where we
            reasonably believe this section is breached. Testing a system
            without authority can be a criminal offence under Estonian law and
            elsewhere; you bear that responsibility, and you will indemnify us
            against claims that arise from a test you had no authority to run.
          </p>

          <h2 id="fees">5. Fees</h2>
          <Summary>
            Usage of the Suncly API, nothing else. Connecting and the badge are
            free. Nothing is charged yet.
          </Summary>
          <p>
            Suncly charges only for your usage of the Suncly API: no seats and
            no plans. Connecting an agent costs nothing
            {launch.connectingFee === "none"
              ? ""
              : " (subject to the fee published on /offer)"}
            , and the Suncly Certified badge is free
            {launch.badgeFee === "none"
              ? ""
              : " (subject to the fee published on /offer)"}
            . Running the command-line tool on your own machines, reading a
            report and verifying a report are never charged.
          </p>
          {!billing ? (
            <p>
              <strong>No fees are charged yet.</strong> Billing starts when the
              hosted API does. We will give you at least thirty days' written
              notice of the date charging starts, together with the unit, the
              rate schedule, the billing period and the payment method,
              published on <Link href="/offer">/offer</Link> and in a new
              version of these terms; nothing is charged for usage before that
              date.
            </p>
          ) : null}
          <table tabIndex={0}>
            <thead>
              <tr>
                <th>Item</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Billable unit</td>
                <td>
                  {pricing.billableUnit ?? <Blank what="billable unit" />}
                </td>
              </tr>
              <tr>
                <td>Rate schedule</td>
                <td>
                  {pricing.priceAndCurrency ?? (
                    <Blank what="price and currency" />
                  )}
                </td>
              </tr>
              <tr>
                <td>Billing period and payment method</td>
                <td>
                  {pricing.billingPeriodAndPaymentMethod ?? (
                    <Blank what="billing period and payment method" />
                  )}
                </td>
              </tr>
              <tr>
                <td>Taxes</td>
                <td>Prices exclude VAT, which is added where it applies.</td>
              </tr>
              <tr>
                <td>Invoices</td>
                <td>
                  Issued by the entity in section 1, by e-mail, per billing
                  period, itemised per API key.
                </td>
              </tr>
              <tr>
                <td>Failed calls and retries</td>
                <td>
                  A call the service rejects before any run starts is not
                  charged. Retries the service makes on its own account are not
                  charged twice.
                </td>
              </tr>
              <tr>
                <td>Disputes</td>
                <td>
                  Tell us within thirty days of the invoice; we answer within
                  fourteen days; undisputed parts remain due.
                </td>
              </tr>
              <tr>
                <td>How to stop</td>
                <td>
                  Stop calling the API. No minimum term, no cancellation fee.
                </td>
              </tr>
              <tr>
                <td>Pilot terms</td>
                <td>
                  {pricing.pilotTerms ??
                    "Agreed per pilot by e-mail and prevailing over this section for that pilot."}
                </td>
              </tr>
            </tbody>
          </table>

          <h2 id="evidence">6. Evidence, reports and intellectual property</h2>
          <Summary>
            A pass means what the report says, on that day. Report folders are
            yours. The software is ours, and you may run it to evaluate agents.
          </Summary>
          <p>
            A result (pass, fail or inconclusive) is a statement about one run
            of one test against one sandbox endpoint on one day, judged by the
            deterministic checks described in the documentation. A completed
            evaluation's decision record is <code>flag</code> in this version;
            Suncly never approves or blocks an agent, never produces a score,
            and never substitutes for your own approval decision. Every report
            states what was not tested.
          </p>
          <p>
            Report folders the tool writes, and the evidence in them, belong to
            you. The Suncly software, its documentation, its name and marks, and
            the website belong to Suncly. The repository is public and no
            open-source licence has been chosen yet
            {company.repositoryLicence ? (
              ` (${company.repositoryLicence})`
            ) : (
              <Blank what="repository licence, once chosen" />
            )}
            ; until a licence is published, Suncly grants you a non-exclusive,
            non-transferable licence to download, install and run the software
            for evaluating agents in accordance with these terms, and no other
            right. You may not remove notices, redistribute modified versions as
            Suncly, or use our marks except as the Certification Policy allows.
          </p>

          <h2 id="certification">7. Certification</h2>
          <Summary>
            The Certification Policy governs the badge. It is our statement, not
            your approval.
          </Summary>
          <p>
            The Suncly Certified programme is governed by the{" "}
            <Link href="/certified/policy">Certification Policy</Link>, which
            forms part of these terms for operators that hold or seek a record.
            Certification is Suncly's statement that a named agent version met a
            named, published set of criteria on a date, on a sandbox. It is not
            the customer's approval, not a rating, not a tier, not a security
            certification, not legal compliance and not insurance; it does not
            make Suncly responsible for what an agent does.
            {certification.criteriaAccepted
              ? ""
              : " No criteria have been adopted or published yet and no record has been issued; this section applies from the day the first criteria are published."}
          </p>

          <h2 id="confidentiality">8. Confidentiality and data protection</h2>
          <Summary>
            What you tell us in a pilot stays confidential. Data protection is
            in the Privacy Policy and, once hosted, a processing agreement.
          </Summary>
          <p>
            Each party keeps the other's non-public information confidential and
            uses it only for the contract, for three years after the contract
            ends, except where disclosure is required by law. Personal data is
            handled as described in the{" "}
            <Link href="/privacy">Privacy Policy</Link>. In this version the
            tool sends Suncly nothing; once Suncly hosts evaluations, a data
            processing agreement meeting GDPR Article 28 will apply and a
            sub-processor list will be published.
          </p>

          <h2 id="warranties">9. Warranties and disclaimers</h2>
          <Summary>
            The same statement as on the home page, in legal form.
          </Summary>
          <p>{stand.statement}</p>
          <p>
            Suncly warrants that it will provide the service with reasonable
            skill and care and that the evidence it signs was not altered after
            signing. Beyond that, and to the extent the law allows, the service
            is provided as it is: Suncly does not warrant that an agent that
            passed will behave the same in production or in future, that a
            report is complete beyond what it states, or that the service is
            free of errors or interruptions. A pass is not a guarantee of future
            behaviour, says nothing about a production endpoint, and is not a
            security certification, legal compliance or insurance. No
            endorsement by any foundation or vendor is implied.
          </p>

          <h2 id="liability">10. Liability</h2>
          <Summary>
            Capped at what you paid in the last twelve months, with the
            exceptions the law requires.
          </Summary>
          <p>
            Nothing in these terms excludes or limits liability for intentional
            breach, for gross negligence where the law does not allow its
            exclusion, for death or personal injury, or for any other liability
            that cannot be limited under the applicable law. Subject to that,
            Suncly's total liability under or in connection with this contract
            in any twelve-month period is limited to the fees you paid to Suncly
            in that period, or, where no fees were paid, to EUR 1,000; and
            neither party is liable for loss of profit, loss of business, or
            indirect or consequential loss. The limits in this section reflect
            the fact that the customer, not Suncly, decides what gets access,
            and that certifying or evaluating an agent does not make Suncly
            responsible for what the agent does.
          </p>

          <h2 id="changes">11. Changes to these terms</h2>
          <Summary>Reasons, notice, and the right to leave.</Summary>
          <p>
            We may change these terms to reflect changes in the service, the law
            or our business. We publish the new version here with its effective
            date and the reasons, and we e-mail account holders at least thirty
            days before a material change takes effect. If you do not accept a
            change you may end the contract before the effective date at no
            cost; using the service after that date is acceptance.
          </p>

          <h2 id="term">12. Term, suspension, termination and data</h2>
          <Summary>
            Open-ended. Either side can end it. Your data stays yours.
          </Summary>
          <p>
            The contract runs until ended. You may end it at any time by
            stopping use and, where an account exists, closing it. We may
            suspend the service where section 3 or 4 is breached or where
            required to protect the service, and we may end the contract on
            thirty days' notice. On termination, report folders on your machines
            are unaffected; where Suncly holds evaluation data for you under
            section 13 of the Privacy Policy, you may export it in a structured,
            commonly used, machine-readable format for thirty days after
            termination, after which we delete it, subject to the append-only
            nature of evidence described in the data processing agreement and to
            legal retention duties.
          </p>

          <h2 id="law">13. Governing law and court</h2>
          <Summary>
            Estonian law and an Estonian court, to be confirmed by counsel.
          </Summary>
          <p>
            This contract is governed by{" "}
            {company.governingLawAndCourt ?? (
              <>
                the law of{" "}
                <Blank what="governing law (counsel to confirm; Estonian law is usual)" />{" "}
                and disputes are brought before{" "}
                <Blank what="court (counsel to confirm; Harju County Court is usual)" />
              </>
            )}
            , without prejudice to mandatory rules that apply regardless of the
            chosen law.
          </p>

          <h2 id="conclusion">
            14. How the contract is concluded, and how to keep these terms
          </h2>
          <Summary>
            By using the service, or by accepting an order. Save this page;
            versions are dated.
          </Summary>
          <p>
            The contract is concluded when you first use the Suncly software or
            the hosted API, or when you accept a pilot order by e-mail,
            whichever comes first. These terms are published in English; you can
            save or print this page, and every version is identified by its
            number and effective date at the top so you can keep the one you
            accepted. The Estonian Law of Obligations Act's rules on standard
            terms apply; a term that is surprising or unreasonably detrimental
            to you is not part of the contract.
          </p>
        </article>
      </Section>
    </SiteLayout>
  );
}
