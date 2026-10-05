import { AVAILABILITY_LABEL, anyAgentVerified, codingAgents } from "@/lib/capabilities";
import { worksWith } from "@/lib/content";

/**
 * 03 Works with. One hairline row with exactly five names in this order and spelling. A
 * tool counts as supported only when an install path exists in the repository and a
 * recorded run in that tool is in VERIFICATION.md; status comes from the capability map.
 * Plain names in the interface font; no logos, no trade mark symbols, never "Trusted by".
 */
export function WorksWith() {
  const verified = anyAgentVerified();
  const agents = codingAgents();
  return (
    <section aria-labelledby="works-heading" className="container-site">
      <div className="border-y border-line py-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-baseline lg:justify-between lg:gap-10">
          <div className="min-w-0">
            <h2 id="works-heading" className="text-eyebrow text-ink-soft">
              {verified ? worksWith.headingVerified : worksWith.headingUnverified}
            </h2>
            {!verified ? <p className="mt-1 text-small text-ink-soft">{worksWith.lineUnverified}</p> : null}
          </div>
          <ul className="flex flex-wrap gap-x-7 gap-y-2 text-[15.5px] text-ink">
            {agents.map((agent) => (
              <li key={agent.id} className="flex items-baseline gap-2">
                {agent.status === "available" ? (
                  <a href={`#install-${agent.id.replace("agent-", "")}`} className="underline-offset-4 hover:underline">
                    {agent.name}
                  </a>
                ) : (
                  <span>{agent.name}</span>
                )}
                {agent.status !== "available" ? (
                  <span className="text-eyebrow text-[11px] text-ink-mute">{AVAILABILITY_LABEL[agent.status]}</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-3 text-[13px] text-ink-mute">{worksWith.disclaimer}</p>
      </div>
    </section>
  );
}
