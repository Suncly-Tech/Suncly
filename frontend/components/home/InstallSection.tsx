"use client";

import Link from "next/link";
import { useState } from "react";
import { Tabs, TabPanel } from "@/components/ui/Tabs";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { install } from "@/lib/content";
import { demoOutput, installCommands } from "@/lib/install";
import { AVAILABILITY_LABEL, codingAgents } from "@/lib/capabilities";

/**
 * 05 Install. A developer reaches a first result without leaving the page. Terminal tab:
 * prerequisites, the quickstart commands (macOS/Linux and Windows), the captured output
 * of `suncly demo`, the next step and a link to the full guide. Tool tabs show exact
 * steps where a tool is verified in the capability map, otherwise "Planned".
 */
export function InstallSection() {
  const agents = codingAgents();
  const items = [
    { id: "terminal", label: "Terminal" },
    ...agents.map((a) => ({ id: a.id.replace("agent-", ""), label: a.name })),
  ];
  const [tab, setTab] = useState("terminal");
  const [os, setOs] = useState<"unix" | "windows">("unix");
  const activeAgent = agents.find((a) => a.id === `agent-${tab}`);

  return (
    <section
      id="install"
      aria-labelledby="install-heading"
      className="scroll-mt-20 bg-cream-deep/60 py-12 md:py-24"
    >
      <div className="container-site">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div className="min-w-0">
            <p className="text-eyebrow text-ink-soft">
              <span className="mr-3 text-ink-mute">05</span>
              {install.label}
            </p>
            <h2 id="install-heading" className="mt-4 text-display-lg text-ink">
              {install.headline}
            </h2>
            <p className="mt-5 max-w-[40ch] text-body text-ink">
              {install.prerequisites} {install.timing}
            </p>
            <p className="mt-4 max-w-[44ch] text-small text-ink-soft">
              {install.local}
            </p>
          </div>

          <div className="min-w-0">
            <Tabs
              items={items}
              value={tab}
              onChange={setTab}
              label="Where to install"
            />
            <TabPanel id="terminal" active={tab === "terminal"}>
              <div className="flex items-center gap-2">
                {(["unix", "windows"] as const).map((o) => (
                  <button
                    key={o}
                    type="button"
                    onClick={() => setOs(o)}
                    aria-pressed={os === o}
                    className={`inline-flex min-h-9 items-center rounded-full px-3 text-[13px] ring-1 transition-colors ${
                      os === o
                        ? "bg-ink text-paper ring-ink"
                        : "text-ink-soft ring-line hover:text-ink"
                    }`}
                  >
                    {o === "unix" ? "macOS / Linux" : "Windows PowerShell"}
                  </button>
                ))}
              </div>
              <CodeBlock
                code={installCommands[os]}
                label="install commands"
                lines
                className="mt-4"
              />
              {os === "windows" ? (
                <p className="mt-2 text-[13px] text-ink-mute">
                  The Windows commands come from docs/QUICKSTART.md and were not
                  run during this build.
                </p>
              ) : null}
              <p className="mt-6 text-eyebrow text-ink-soft">
                {install.demoHeading}
              </p>
              <pre
                className="code-block mt-3 max-h-[300px] overflow-auto text-[12.5px] md:max-h-[420px] md:whitespace-pre"
                tabIndex={0}
                aria-label="Output of suncly demo"
              >
                {demoOutput}
              </pre>
              <p className="mt-6 text-body text-ink">
                {install.next}{" "}
                <code className="code-inline">{installCommands.attest}</code>{" "}
                <Link
                  href={install.guide.href}
                  className="underline underline-offset-4 decoration-amber hover:text-ember"
                >
                  {install.guide.label}
                </Link>
              </p>
            </TabPanel>
            {agents.map((agent) => (
              <TabPanel
                key={agent.id}
                id={agent.id.replace("agent-", "")}
                active={activeAgent?.id === agent.id}
              >
                <p className="text-eyebrow text-ink-mute">
                  {AVAILABILITY_LABEL[agent.status]}
                </p>
                <p className="mt-3 max-w-[52ch] text-body text-ink">
                  {agent.status === "available"
                    ? agent.summary
                    : install.toolPlanned(agent.name)}
                </p>
                {agent.status !== "available" ? (
                  <button
                    type="button"
                    onClick={() => setTab("terminal")}
                    className="mt-4 text-[15px] underline underline-offset-4 decoration-amber hover:text-ember"
                  >
                    Show the Terminal steps
                  </button>
                ) : null}
              </TabPanel>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
