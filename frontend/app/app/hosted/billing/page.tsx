import type { Metadata } from "next";
import { HostedBillingView } from "@/components/app/hosted/HostedBillingView";

export const metadata: Metadata = { title: "Usage and billing" };

export default function HostedBillingPage() {
  return <HostedBillingView />;
}
