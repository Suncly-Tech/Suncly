import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { SectionHeader } from "@/components/SectionHeader";
import { AvailabilityBadge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { Notice } from "@/components/ui/Notice";
import { byGroup, type Availability } from "@/lib/capabilities";
import { workflowsPage } from "@/lib/content";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description =
  "What Suncly can test: A2A 1.0 over JSON-RPC 2.0, Agent Card verification, agents built on any model or framework, and the integrations available today and planned.";

export const metadata: Metadata = pageMeta({
  title: "A2A protocol coverage and integrations",
  description,
  path: "/workflows",
  keywords: [...KEYWORDS.protocol, ...KEYWORDS.audience, "model-agnostic agent testing", "A2A integrations"],
});

export default function WorkflowsPage() {
  const w = workflowsPage;
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          webPageLd({ path: "/workflows", name: "A2A protocol coverage and integrations", description }),
          breadcrumbLd([{ name: "Suncly", path: "/" }, { name: "Workflows", path: "/workflows" }]),
        )}
      />
      <PageHeader eyebrow={w.title} headline={w.headline} intro={w.intro} />

      <Section id="protocol">
        <SectionHeader label="Protocol" headline={w.protocol.title} intro={w.protocol.intro} />
        <div className="mt-10">
          <CoverageTable rows={w.protocol.rows} caption="A2A protocol coverage" />
        </div>
      </Section>

      <Section id="models" tone="paper">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-2 lg:gap-16">
          <SectionHeader label="Model providers" headline={w.models.title} intro={w.models.intro} />
          <div className="flex flex-col gap-5">
            <ul className="flex flex-wrap gap-2" aria-label="Examples of models an evaluated agent may use">
              {w.models.names.map((name) => (
                <li key={name} className="rounded-full bg-cream px-4 py-2 text-[14px] font-semibold text-ink ring-1 ring-line">
                  {name}
                </li>
              ))}
            </ul>
            <Notice tone="info">{w.models.disclaimer}</Notice>
            <p className="text-small text-ink-soft">{w.models.futureNote}</p>
          </div>
        </div>
      </Section>

      <Section id="frameworks">
        <SectionHeader label="Frameworks and tools" headline={w.frameworks.title} intro={w.frameworks.intro} />
        <div className="mt-10">
          <CoverageTable rows={w.frameworks.rows} caption="Agent frameworks and coding tools" />
        </div>
      </Section>

      <Section id="integrations" tone="paper">
        <SectionHeader label="Integrations" headline={w.integrations.title} intro={w.integrations.intro} />
        <ul className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2">
          {byGroup("integration").map((item) => (
            <li key={item.id} className="surface flex flex-col gap-2 p-5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="text-heading-md text-ink">{item.name}</h3>
                <AvailabilityBadge status={item.status} />
              </div>
              <p className="text-small text-ink">{item.summary}</p>
              {item.limit ? <p className="text-[13px] text-ink-soft">{item.limit}</p> : null}
            </li>
          ))}
        </ul>
      </Section>

      <Section id="bundled">
        <SectionHeader label="Bundled" headline={w.mocks.title} intro={w.mocks.intro} />
        <div className="mt-10 max-w-[960px]">
          <Table caption="Bundled mock agents and their expected results">
            <thead>
              <tr>
                <th scope="col">Mock agent</th>
                <th scope="col">Behaviour</th>
                <th scope="col">Expected result</th>
              </tr>
            </thead>
            <tbody>
              {w.mocks.rows.map(([name, behaviour, expected]) => (
                <tr key={name}>
                  <td className="font-mono text-[13px] text-ink">{name}</td>
                  <td className="text-ink">{behaviour}</td>
                  <td className="text-ink-soft">{expected}</td>
                </tr>
              ))}
            </tbody>
          </Table>
          <p className="mt-4 text-small text-ink-soft">
            Start one yourself: <code className="code-inline">python -m suncly.mock_agents honest --port 8701</code>, then evaluate it with <code className="code-inline">suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox</code>.
          </p>
        </div>
      </Section>

      <FinalCta />
    </SiteLayout>
  );
}

function CoverageTable({
  rows,
  caption,
}: {
  rows: ReadonlyArray<{ item: string; status: string; note: string }>;
  caption: string;
}) {
  return (
    <Table caption={caption}>
      <thead>
        <tr>
          <th scope="col">Item</th>
          <th scope="col">Status</th>
          <th scope="col">What Suncly does with it</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.item}>
            <td className="font-semibold text-ink">{row.item}</td>
            <td>
              <AvailabilityBadge status={row.status as Availability} />
            </td>
            <td className="text-ink-soft">{row.note}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
