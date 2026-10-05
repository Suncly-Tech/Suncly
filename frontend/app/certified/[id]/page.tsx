import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { certifiedPage } from "@/lib/content";
import { certificationRecords, recordById } from "@/lib/certified";
import { pageMeta } from "@/lib/seo";

/**
 * One page per issued record, generated statically from lib/certified/records.json. The
 * static export needs at least one path, so with zero records a single "specimen" page is
 * generated: it shows the record format, states that no agent is certified, and is noindex.
 */
export const dynamicParams = false;
const SPECIMEN = "specimen";

export function generateStaticParams() {
  return certificationRecords.length ? certificationRecords.map((r) => ({ id: r.id })) : [{ id: SPECIMEN }];
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const r = recordById(id);
  return pageMeta({
    title: r ? `Certification record ${r.id}: ${r.agentName} ${r.agentVersion}` : "Specimen certification record",
    description: r ? `Suncly Certified record ${r.id}: ${r.agentName} ${r.agentVersion}, evaluated ${r.evaluatedOn} under criteria ${r.criteriaVersion}.` : "The format of a Suncly Certified record. No agent is certified yet.",
    path: `/certified/${id}`,
    noindex: !r,
  });
}

export default async function RecordPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const found = recordById(id);
  if (!found && id !== SPECIMEN) notFound();
  const r = found ?? {
    id: "specimen",
    agentName: "Specimen (fictional, no agent)",
    operator: "Specimen (fictional, no operator)",
    agentVersion: "",
    cardHash: "the agent's card hash will appear here",
    a2aVersion: "the A2A version will appear here",
    sandboxEndpoint: "the declared sandbox endpoint will appear here",
    evaluatedOn: "the date will appear here",
    validUntil: "the expiry will appear here",
    criteriaVersion: "no criteria adopted yet",
    runs: { testCases: 0, perTestCase: 0, pass: 0, fail: 0, inconclusive: 0 },
    notTested: ["Every record lists what the report listed under What was NOT tested."],
    decidedBy: "the named Suncly reviewer will appear here",
    status: "specimen" as const,
  };
  const rows: Array<[string, string]> = [
    ["Record", r.id],
    ["Status", found ? r.status : "specimen: fictional, certifies nothing"],
    ["Agent", `${r.agentName} ${r.agentVersion}`],
    ["Operator", r.operator],
    ["Sandbox endpoint tested", r.sandboxEndpoint],
    ["Card hash", r.cardHash],
    ["A2A version", r.a2aVersion],
    ["Evaluated on", r.evaluatedOn],
    ["Valid until", r.validUntil],
    ["Criteria version", r.criteriaVersion],
    ["Runs", `${r.runs.testCases} test cases × ${r.runs.perTestCase} runs: ${r.runs.pass} pass, ${r.runs.fail} fail, ${r.runs.inconclusive} inconclusive`],
    ["Decided by", r.decidedBy],
  ];
  return (
    <SiteLayout>
      <PageHeader eyebrow={found ? "Suncly Certified · record" : "Suncly Certified · fictional specimen"} headline={found ? `${r.agentName} ${r.agentVersion}` : "Specimen record (fictional)"} intro={found ? `Record ${r.id}. This page is the single source of truth for this badge.` : "A fictional specimen showing the format of a record. No agent is certified, no criteria are adopted, and this page certifies nothing."} />
      <Section narrow>
        <article className="prose-site">
          <table tabIndex={0}>
            <tbody>
              {rows.map(([k, v]) => (
                <tr key={k}>
                  <th scope="row">{k}</th>
                  <td>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>What was not tested</h2>
          <ul>{r.notTested.map((n) => <li key={n}>{n}</li>)}</ul>
          <h2>{certifiedPage.limits.title}</h2>
          <ul>{certifiedPage.limits.items.map((i) => <li key={i}>{i}</li>)}</ul>
          <p className="summary">
            The rules are in the <Link href="/certified/policy">Certification Policy</Link>. Suncly never approves or blocks an agent and never gives a score.
          </p>
        </article>
      </Section>
    </SiteLayout>
  );
}
