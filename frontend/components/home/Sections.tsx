import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { SectionHeader, SectionLabel } from "@/components/SectionHeader";
import { Reveal } from "@/components/Reveal";
import { Cuts } from "@/components/Cuts";
import { AvailabilityBadge, Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { byGroup } from "@/lib/capabilities";
import { chain, limitations, manualVsSuncly, problem, process, scopeLines, workflowsPage } from "@/lib/content";

export function Problem() {
  return (
    <section id="problem" className="scroll-mt-20 bg-cream pb-20 pt-16 md:pb-28 md:pt-24" aria-labelledby="problem-heading">
      <div className="container-site">
        <SectionHeader label={problem.label} headline={problem.headline} id="problem-heading" />
        <div className="mt-12 grid gap-4 md:grid-cols-3 lg:gap-6">
          {problem.cards.map((card, i) => (
            <Reveal key={card.title} delay={i * 0.06} as="article" className="surface-card flex flex-col gap-3 p-6 md:p-8">
              <span className="font-mono text-[13px] text-ink-soft">0{i + 1}</span>
              <h3 className="text-heading-md text-ink">{card.title}</h3>
              <p className="text-body text-ink-soft">{card.body}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

export function ClaimChain() {
  return (
    <section id="chain" className="scroll-mt-20 bg-paper py-20 md:py-28" aria-labelledby="chain-heading">
      <div className="container-site">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <SectionHeader label={chain.label} headline={chain.headline} intro={chain.intro} id="chain-heading" />
            <Link href="/demo" className="mt-8 inline-flex items-center gap-2 text-[15px] font-semibold text-ink underline-offset-4 hover:underline">
              See the whole sample evaluation
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <ol className="relative flex flex-col gap-6 border-l border-line pl-8">
            {chain.steps.map((step, i) => (
              <Reveal key={step.title} as="li" delay={i * 0.05} className="relative">
                <span className="absolute -left-[41px] top-1 flex h-5 w-5 items-center justify-center rounded-full bg-paper ring-1 ring-line">
                  <Cuts className={i === 2 ? "text-fail" : "text-sun"} height={8} stroke={2.5} />
                </span>
                <h3 className="text-heading-md text-ink">
                  <span className="mr-2 font-mono text-[13px] text-ink-soft">0{i + 1}</span>
                  {step.title}
                </h3>
                <p className="mt-2 max-w-[640px] text-body text-ink-soft">{step.body}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

export function Process() {
  return (
    <section id="how-it-works" className="scroll-mt-20 bg-cream py-20 md:py-28" aria-labelledby="process-heading">
      <div className="container-site">
        <SectionHeader label={process.label} headline={process.headline} id="process-heading" />
        <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6">
          {process.steps.map((step, i) => (
            <Reveal key={step.title} as="li" delay={i * 0.04} className="surface-card flex flex-col gap-3 p-6">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-sun font-mono text-[14px] font-semibold text-ink">
                {i + 1}
              </span>
              <h3 className="text-heading-md text-ink">{step.title}</h3>
              <p className="text-small text-ink-soft md:text-[15px]">{step.body}</p>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function ManualComparison() {
  return (
    <section id="compared" className="scroll-mt-20 bg-paper py-20 md:py-28" aria-labelledby="compared-heading">
      <div className="container-site">
        <SectionHeader label={manualVsSuncly.label} headline={manualVsSuncly.headline} intro={manualVsSuncly.intro} id="compared-heading" />
        <div className="mt-12">
          <Table caption="Manual review compared with Suncly, topic by topic">
            <thead>
              <tr>
                {manualVsSuncly.columns.map((c, i) => (
                  <th key={i} scope="col" className={i === 2 ? "text-ink" : ""}>
                    {c || <span className="sr-only">Topic</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {manualVsSuncly.rows.map((row) => (
                <tr key={row.topic}>
                  <th scope="row" className="bg-paper! normal-case! tracking-normal! text-[14px]! text-ink!">
                    {row.topic}
                  </th>
                  <td className="text-ink-soft">{row.manual}</td>
                  <td className="text-ink">{row.suncly}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      </div>
    </section>
  );
}

export function Coverage() {
  const integrations = byGroup("integration");
  return (
    <section id="coverage" className="scroll-mt-20 bg-cream py-20 md:py-28" aria-labelledby="coverage-heading">
      <div className="container-site">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <SectionHeader
              label="Verified coverage"
              headline={workflowsPage.headline}
              intro="Suncly evaluates agents through the A2A protocol, version 1.0 over JSON-RPC. The model or framework behind the agent does not change what it can test."
              id="coverage-heading"
            />
            <div className="mt-8 flex flex-wrap gap-2" aria-label="Models an evaluated agent may be built on">
              {workflowsPage.models.names.map((name) => (
                <span key={name} className="rounded-full bg-paper px-3 py-1.5 text-[13px] font-semibold text-ink ring-1 ring-line">
                  {name}
                </span>
              ))}
            </div>
            <p className="mt-3 max-w-[560px] text-[13px] text-ink-soft">{workflowsPage.models.disclaimer}</p>
            <Link href="/workflows" className="mt-6 inline-flex items-center gap-2 text-[15px] font-semibold text-ink underline-offset-4 hover:underline">
              Protocol coverage, frameworks and integrations in detail
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
          <div>
            <SectionLabel>Interfaces and integrations</SectionLabel>
            <ul className="mt-5 flex flex-col divide-y divide-line surface-card px-5 md:px-6">
              {integrations.map((item) => (
                <li key={item.id} className="flex flex-col gap-1.5 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
                  <div className="min-w-0">
                    <p className="font-semibold text-ink">{item.name}</p>
                    <p className="mt-0.5 text-[13px] text-ink-soft">{item.status === "planned" ? item.limit : item.summary}</p>
                  </div>
                  <AvailabilityBadge status={item.status} />
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Scope() {
  return (
    <section id="scope" className="scroll-mt-20 bg-ink py-20 text-paper md:py-28" aria-labelledby="scope-heading">
      <div className="container-site">
        <SectionHeader label={scopeLines.label} headline={scopeLines.headline} tone="paper" id="scope-heading" />
        <div className="mt-12 grid gap-4 md:grid-cols-3 lg:gap-6">
          {scopeLines.items.map((item) => (
            <article key={item.name} className="flex flex-col gap-3 rounded-card bg-paper/5 p-6 ring-1 ring-paper/15 md:p-8">
              <Badge tone={item.tone as "pass" | "inconclusive" | "neutral"} dot className="self-start">
                {item.status}
              </Badge>
              <h3 className="text-heading-md text-paper">{item.name}</h3>
              <p className="text-small text-paper/70 md:text-[15px]">{item.body}</p>
            </article>
          ))}
        </div>
        <div className="mt-16 grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <SectionLabel tone="paper">{limitations.label}</SectionLabel>
            <h3 className="mt-5 text-display-md text-paper">{limitations.headline}</h3>
          </div>
          <ul className="flex flex-col gap-4">
            {limitations.items.map((item) => (
              <li key={item} className="cuts-bullet text-sun">
                <span className="text-body text-paper/85">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
