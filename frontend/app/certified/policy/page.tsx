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
import { site } from "@/lib/content";
import { certification, company, launch } from "@/lib/launch";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Certification Policy",
  description:
    "The rules of the Suncly Certified programme: who issues the badge, the criteria, what is tested and not, validity, re-tests, suspension, the public record, the badge licence, and appeals.",
  path: "/certified/policy",
  noindex: !launch.legalPublished,
});

const toc = [
  { id: "issuer", title: "Who issues the badge" },
  { id: "nature", title: "A private, voluntary programme" },
  { id: "criteria", title: "The criteria and their version" },
  { id: "tested", title: "What is tested, and what is not" },
  { id: "validity", title: "Validity, expiry and re-tests" },
  { id: "suspension", title: "Suspension and revocation" },
  { id: "record", title: "The public record" },
  { id: "licence", title: "Licence to display the badge" },
  { id: "prohibited", title: "Prohibited uses and words" },
  { id: "fees", title: "No pay-to-pass" },
  { id: "appeals", title: "Corrections and appeals" },
  { id: "changes", title: "Changes" },
];

export default function CertificationPolicyPage() {
  const missing = [
    "legal entity name",
    "corrections and appeals contact",
    "validity period",
    "re-test triggers",
    "response times",
  ];
  if (!certification.criteriaAccepted) missing.push("adopted criteria");
  return (
    <SiteLayout>
      <PageHeader
        eyebrow="Legal"
        headline="Certification Policy"
        intro="What Suncly Certified means, in the form a lawyer can sign off. The same statements appear on the home page, on every record page and in the Terms."
      />
      <Section narrow>
        <DraftNotice page="Certification Policy" needs={missing} />
        <article className="prose-site">
          <DocMeta
            version="0.1 (draft)"
            effective={null}
            changes={[
              {
                date: "2026-10-05",
                note: "First complete draft. No criteria adopted; the proposed first profile stays in the internal plan.",
              },
            ]}
          />
          <Toc items={toc} />

          <h2 id="issuer">1. Who issues the badge</h2>
          <Summary>
            Suncly issues it, and a named person at Suncly decides.
          </Summary>
          <p>
            The Suncly Certified badge is issued by{" "}
            {company.legalEntityName ?? <Blank what="legal entity name" />},{" "}
            {site.city} ("Suncly", "we"). Each certification decision is taken
            by a named Suncly reviewer, recorded on the record:{" "}
            {certification.whoDecides ?? (
              <Blank what="who decides, from founder inputs block 6" />
            )}
            .
          </p>

          <h2 id="nature">2. A private, voluntary programme</h2>
          <Summary>
            It is our statement about a test we ran. It is neither official nor
            accredited, and it certifies nothing under any law or standard.
          </Summary>
          <p>
            Suncly Certified is a private, voluntary evaluation programme run by
            Suncly. It is not an accredited conformity assessment, not a
            certification under any law or standard, and not a mark of approval
            by any public body, standards body, foundation or vendor. The badge
            does not mean "compliant", "secure", "safe" or "approved by". It
            does not relate to the EU Artificial Intelligence Act's conformity
            assessment, CE marking or notified bodies, and we never describe it
            as such.
          </p>
          <p>
            Certification is Suncly's statement that a named agent version met a
            named, published set of criteria on a date, on a sandbox endpoint.
            It is not the customer's approval, not a rating, not a score and not
            a tier. The Suncly software itself never approves or blocks an
            agent; the programme's decision is a separate, human decision by
            Suncly about the evidence.
          </p>

          <h2 id="criteria">3. The criteria and their version</h2>
          <Summary>
            Every record names the criteria version it was tested against. No
            criteria are published yet.
          </Summary>
          <p>
            Criteria are published here with a version number before any record
            is issued under them, and a record keeps its criteria version until
            it expires.{" "}
            {certification.criteriaAccepted
              ? `The current criteria are version ${certification.criteriaVersion}.`
              : "No criteria have been adopted. A first profile, built only from checks that exist in the Suncly software today, is in founder review; it will be published here with its version number if and when it is accepted, and nothing is certified before then."}
          </p>

          <h2 id="tested">4. What is tested, and what is not</h2>
          <Summary>
            The record says exactly which agent, operator, endpoint, card,
            protocol version, date and run counts. The gaps are listed too.
          </Summary>
          <p>
            Each record states: the agent and its operator; the sandbox endpoint
            tested; the card hash and the A2A protocol version; the date of the
            evaluation; the number of test cases and runs, with the pass, fail
            and inconclusive counts; the criteria version; and the Suncly
            reviewer.
          </p>
          <p>
            Each record also states what was not tested, taken from the
            evaluation report. In the current version that always includes: the
            production endpoint, which is never called; whether the content of
            an answer is correct in meaning; prompt-injection,
            undeclared-behaviour and failure-handling probes; A2A bindings other
            than JSON-RPC; and declared capabilities no test exercised, such as
            streaming or push notifications.
          </p>

          <h2 id="validity">5. Validity, expiry and re-tests</h2>
          <Summary>
            A record is valid for a stated period or until the card changes,
            whichever comes first.
          </Summary>
          <p>
            A record is valid for{" "}
            {certification.validFor ?? (
              <Blank what="validity period, from founder inputs block 6" />
            )}
            , or until the agent's card hash changes, whichever comes first. An
            expired record stays visible, marked expired.
          </p>
          <p>
            A re-test is required when:{" "}
            {certification.retestTriggers ?? (
              <Blank what="re-test triggers, from founder inputs block 6" />
            )}
            . A changed Agent Card (a different hash) always ends the record's
            validity.
          </p>

          <h2 id="suspension">6. Suspension and revocation</h2>
          <Summary>
            We can pause or withdraw a record, and we say why on the record.
          </Summary>
          <p>
            Suncly may suspend a record while it investigates a report that the
            agent's behaviour contradicts the record, or that the operator
            breached this policy. Suncly revokes a record when the investigation
            confirms the report, when the operator used the badge in a
            prohibited way and did not correct it within fourteen days of
            notice, or when the evidence behind the record is found to be
            invalid. A suspended or revoked record stays visible with its status
            and the date, and the operator must stop displaying the badge at
            once.
          </p>

          <h2 id="record">7. The public record</h2>
          <Summary>
            The record page is the single source of truth. The badge is only a
            pointer to it.
          </Summary>
          <p>
            Every issued badge has a short record id and a public page at{" "}
            <code>suncly.com/certified/&lt;id&gt;</code>. The record page is the
            only authoritative statement of what was certified, when, under
            which criteria, with which gaps, and whether the record is valid. If
            a badge and a record disagree, the record wins. The limits of
            certification appear on the record page itself.
          </p>

          <h2 id="licence">8. Licence to display the badge</h2>
          <Summary>
            You may show the badge for the certified version, while the record
            is valid, unaltered and linked to its record.
          </Summary>
          <p>
            While a record is valid, Suncly grants its operator a non-exclusive,
            non-transferable, revocable licence to display the Suncly Certified
            badge, in the files provided at{" "}
            <Link href="/certified">/certified</Link>, only in connection with
            the certified agent version, only while the record is valid,
            unaltered, and always linked to the record page. The licence ends
            when the record expires, is suspended or is revoked, and the
            operator must then remove the badge within seven days. No other
            right in the Suncly name or marks is granted.
          </p>

          <h2 id="prohibited">9. Prohibited uses and words</h2>
          <Summary>
            Do not use the badge to claim more than the record says.
          </Summary>
          <ul>
            <li>
              Do not alter the badge: no recolouring, cropping, rotation,
              effects, added words, tiers, stars or laurels.
            </li>
            <li>
              Do not display it for a different agent, a different version, or a
              production endpoint.
            </li>
            <li>
              Do not place it next to, or describe it with, the words
              "guaranteed", "secure", "safe", "compliant", "approved by",
              "official", "accredited" or "certified by the Linux Foundation",
              or any statement that it is a legal, security or regulatory
              certification.
            </li>
            <li>
              Do not imply that Suncly, the Linux Foundation, the A2A project or
              any vendor endorses the agent or its operator.
            </li>
            <li>
              Do not use it in a way that suggests the customer's own approval
              decision has been made for them.
            </li>
          </ul>

          <h2 id="fees">10. No pay-to-pass</h2>
          <Summary>
            The badge is free, and the outcome does not change what you pay.
          </Summary>
          <p>
            The badge itself costs nothing
            {launch.badgeFee === "none"
              ? ""
              : " (subject to the fee published on /offer)"}
            . Where Suncly charges for usage of the Suncly API, the fees are the
            same whether an agent passes or fails, and no fee is charged for the
            certification decision. Nobody at Suncly is paid by the outcome of a
            decision.
          </p>

          <h2 id="appeals">11. Corrections and appeals</h2>
          <Summary>
            Tell us what is wrong. How fast we answer is not yet set.
          </Summary>
          <p>
            An operator, or anyone who relies on a record, may ask for a
            correction or appeal a decision by writing to{" "}
            {certification.correctionsAndAppealsContact ?? (
              <Blank what="corrections and appeals contact, from founder inputs block 6" />
            )}
            . Response times:{" "}
            <Blank what="acknowledgement and answer periods, to be set by the founders" />
            . We correct a record when the facts on it are wrong, and we say on
            the record what was corrected and when. Where we learn that
            information on a record is incorrect, we correct or withdraw it
            without being asked.
          </p>

          <h2 id="changes">12. Changes</h2>
          <Summary>We version this policy and give notice of changes.</Summary>
          <p>
            Changes to this policy are published here with a new version number
            and effective date. A change to the criteria creates a new criteria
            version; existing records keep their version until they expire.
            Operators with a valid record are notified by e-mail at least thirty
            days before a change that affects their licence to display the
            badge.
          </p>
        </article>
      </Section>
    </SiteLayout>
  );
}
