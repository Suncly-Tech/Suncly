import { Badge } from "@/components/ui/Badge";
import { KeyValue } from "@/components/ui/Stat";
import { formatDateTime } from "@/lib/evidence/derive";
import type { ResultDocument } from "@/lib/evidence/types";

/** The Agent Card as fetched: identity, interfaces, declared capabilities, and the raw JSON. */
export function CardPanel({ result }: { result: ResultDocument }) {
  const card = result.parsed_card.card;
  const caps = card.capabilities;
  const declared = [
    caps.streaming ? "streaming" : null,
    caps.push_notifications ? "pushNotifications" : null,
    caps.extended_agent_card ? "extendedAgentCard" : null,
    caps.extensions?.length ? `extensions (${caps.extensions.length})` : null,
  ].filter((x): x is string => Boolean(x));
  const required = ["name", "description", "supportedInterfaces", "version", "capabilities", "defaultInputModes", "defaultOutputModes", "skills"];
  const missing = required.filter((f) => !(f in result.parsed_card.json_object));
  return (
    <div className="flex flex-col gap-6">
      <KeyValue
        items={[
          ["Name", card.name],
          ["Description", card.description || "–"],
          ["Version", card.version || "–"],
          ["Card hash", <span key="h" className="font-mono text-[12px]">{result.card_version.card_hash}</span>],
          ["Fetched", formatDateTime(result.card_version.fetched_at)],
          ["Default input modes", card.default_input_modes.join(", ") || "–"],
          ["Default output modes", card.default_output_modes.join(", ") || "–"],
          ["Declared capabilities", declared.length ? declared.join(", ") + " (none exercised by tests)" : "none declared"],
          ["Required fields missing", missing.length ? missing.join(", ") : "none"],
        ]}
      />
      <div>
        <p className="text-[12px] font-semibold uppercase tracking-[0.04em] text-ink-soft">Supported interfaces</p>
        <ul className="mt-2 flex flex-col gap-2">
          {card.supported_interfaces.map((i, idx) => {
            const used = i.protocol_binding === "JSONRPC" && i.protocol_version === "1.0" && idx === card.supported_interfaces.findIndex((x) => x.protocol_binding === "JSONRPC" && x.protocol_version === "1.0");
            return (
              <li key={`${i.url}-${idx}`} className="flex flex-wrap items-center gap-2 font-mono text-[13px] text-ink">
                <Badge tone={used ? "pass" : "neutral"}>{used ? "used by the Runner" : "not used"}</Badge>
                {i.protocol_binding} {i.protocol_version} · {i.url}
              </li>
            );
          })}
        </ul>
      </div>
      <details>
        <summary className="cursor-pointer text-small font-semibold text-ink">Raw card JSON (as fetched, byte for byte)</summary>
        <pre className="code-block mt-3 max-h-[480px]">{formatRaw(result.card_version.raw_json)}</pre>
      </details>
    </div>
  );
}

function formatRaw(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
