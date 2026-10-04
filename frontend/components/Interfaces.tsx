"use client";

import { interfaces } from "@/lib/content";
import { Cuts } from "./Cuts";
import { Reveal } from "./Reveal";
import { SectionHeader } from "./SectionHeader";

const methodTone: Record<string, string> = {
  GET: "bg-[#e6f4ec] text-pass",
  POST: "bg-sky/10 text-sky",
};

export function Interfaces() {
  return (
    <section id="interfaces" className="scroll-mt-20 bg-cream py-24 md:py-32" aria-labelledby="interfaces-heading">
      <div className="container-site">
        <SectionHeader label={interfaces.label} headline={interfaces.headline} intro={interfaces.intro} id="interfaces-heading" />

        <div className="mt-12 grid grid-cols-1 gap-6 lg:mt-16 lg:grid-cols-2 lg:gap-8">
          <Reveal>
            <div className="flex h-full flex-col overflow-hidden rounded-card bg-ink text-paper ring-1 ring-paper/10">
              <div className="flex items-center gap-3 border-b border-paper/10 px-5 py-3">
                <Cuts className="text-sun" height={12} stroke={3} />
                <span className="font-mono text-[13px] text-paper/60">{interfaces.cli.title}</span>
              </div>
              <div className="p-5 md:p-6">
                <pre className="overflow-x-auto font-mono text-[14px] leading-[1.7] md:text-[15px]">
                  <code>
                    <span className="text-sun">$ </span>
                    {interfaces.cli.command}
                  </code>
                </pre>
                <dl className="mt-6 flex flex-col gap-3 border-t border-paper/10 pt-5">
                  {interfaces.cli.args.map((a) => (
                    <div key={a.name} className="grid grid-cols-[120px_1fr] gap-3 text-[14px]">
                      <dt className="font-mono text-sun">{a.name}</dt>
                      <dd className="text-paper/75">{a.note}</dd>
                    </div>
                  ))}
                </dl>
                <ul className="mt-6 flex flex-col gap-3 border-t border-paper/10 pt-5">
                  {interfaces.cli.stages.map((st) => (
                    <li key={st.stage} className="grid grid-cols-[120px_1fr] gap-3 text-[14px]">
                      <span className="font-semibold text-paper/80">{st.stage}</span>
                      <span className="text-paper/75">{st.note}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <div className="flex h-full flex-col overflow-hidden rounded-card bg-paper ring-1 ring-ink/5">
              <div className="flex items-center gap-3 border-b border-ink/8 px-5 py-3">
                <Cuts className="text-sun" height={12} stroke={3} />
                <span className="font-mono text-[13px] text-ink-soft">{interfaces.api.title}</span>
              </div>
              <ul className="divide-y divide-ink/8">
                {interfaces.api.endpoints.map((e) => (
                  <li key={e.method + e.path} className="grid grid-cols-[56px_1fr] items-center gap-3 px-5 py-3.5 md:grid-cols-[56px_minmax(0,1fr)_auto] md:px-6">
                    <span className={`inline-flex h-6 items-center justify-center rounded-full text-[11px] font-bold ${methodTone[e.method]}`}>
                      {e.method}
                    </span>
                    <span className="truncate font-mono text-[14px] text-ink">{e.path}</span>
                    <span className="col-start-2 text-[13px] text-ink-soft md:col-start-3">{e.note}</span>
                  </li>
                ))}
              </ul>
              <pre className="m-5 mt-auto whitespace-pre-wrap break-all rounded-[12px] bg-cream p-4 font-mono text-[12.5px] leading-[1.7] text-ink md:m-6">
                <code>{interfaces.api.example}</code>
              </pre>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
