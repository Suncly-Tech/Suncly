import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { JsonLd } from "@/components/site/JsonLd";
import { Picture } from "@/components/Picture";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Table } from "@/components/ui/Table";
import { labPage } from "@/lib/content";
import { behaviours } from "@/lib/behaviours";
import { installCommands } from "@/lib/install";
import { launch } from "@/lib/launch";
import contract from "@/lib/sample/harbor-contract.json";
import {
  breadcrumbLd,
  graph,
  KEYWORDS,
  pageMeta,
  techArticleLd,
} from "@/lib/seo";

const description =
  "The Suncly Lab: eleven mock A2A agents that misbehave on purpose, how to run each one, the sample generator, and an example contract file.";

export const metadata: Metadata = pageMeta({
  title: `${launch.labName}: agents that misbehave on purpose`,
  description,
  path: "/lab",
  type: "article",
  keywords: [...KEYWORDS.protocol, "mock A2A agents", "sandbox agents"],
});

export default function LabPage() {
  const l = labPage;
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          techArticleLd({ path: "/lab", headline: l.headline, description }),
          breadcrumbLd([{ name: launch.labName, path: "/lab" }]),
        )}
      />
      <PageHeader
        eyebrow={launch.labName}
        headline={l.headline}
        intro={l.intro}
      />
      <Section>
        <Picture
          name="specimens"
          alt="Eleven small forms in a row at golden hour. Most cast true shadows; one casts a wrong shadow, one casts two, one casts none."
          sizes="100vw"
          className="aspect-[9/4]"
        />
        <div className="mt-12 grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
          <div>
            <h2 className="text-display-md text-ink">The eleven</h2>
            <div className="mt-4">
              <Table caption="The eleven mock agents, from BEHAVIOURS in src/suncly/mock_agents/behaviours.py">
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">What it does</th>
                    <th scope="col">What Suncly reports</th>
                  </tr>
                </thead>
                <tbody>
                  {behaviours.map((b) => (
                    <tr key={b.name}>
                      <td>
                        <code className="code-inline whitespace-nowrap">
                          {b.name}
                        </code>
                      </td>
                      <td>{b.description}</td>
                      <td>{b.reports}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          </div>
          <div className="flex flex-col gap-10">
            <div>
              <h2 className="text-display-md text-ink">{l.run.title}</h2>
              <p className="mt-3 text-body text-ink-soft">{l.run.body}</p>
              <CodeBlock
                code={`${installCommands.mock}\n${installCommands.attestLocal}`}
                label="mock agent commands"
                lines
                className="mt-4"
              />
            </div>
            <div>
              <h2 className="text-display-md text-ink">{l.sample.title}</h2>
              <p className="mt-3 text-body text-ink-soft">{l.sample.body}</p>
              <CodeBlock
                code=".venv/bin/python frontend/scripts/make-sample.py"
                label="sample generator command"
                lines
                className="mt-4"
              />
            </div>
            <div>
              <h2 className="text-display-md text-ink">Planned</h2>
              <ul className="mt-3 flex flex-col gap-2">
                {l.planned.map((p) => (
                  <li key={p} className="cuts-bullet text-body text-ink-soft">
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
        <div className="mt-14">
          <h2 className="text-display-md text-ink">{l.contract.title}</h2>
          <p className="mt-3 max-w-[64ch] text-body text-ink-soft">
            {l.contract.body} The file format is documented in{" "}
            <Link
              href="/docs/cli"
              className="underline underline-offset-4 decoration-amber"
            >
              the command reference
            </Link>
            .
          </p>
          <CodeBlock
            code={JSON.stringify(contract, null, 2)}
            label="example contract file"
            className="mt-4 max-h-[520px] overflow-y-auto"
          />
        </div>
      </Section>
    </SiteLayout>
  );
}
