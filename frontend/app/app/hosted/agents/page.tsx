import type { Metadata } from "next";
import { HostedAgentsView } from "@/components/app/hosted/HostedAgentsView";

export const metadata: Metadata = { title: "Agents and contracts" };

export default function HostedAgentsPage() {
  return <HostedAgentsView />;
}
