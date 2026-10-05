import type { Metadata } from "next";
import { HostedOverview } from "@/components/app/hosted/HostedOverview";

export const metadata: Metadata = { title: "Hosted overview" };

export default function HostedPage() {
  return <HostedOverview />;
}
