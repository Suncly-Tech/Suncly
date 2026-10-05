import type { Metadata } from "next";
import { Suspense } from "react";
import { HostedAttestationView } from "@/components/app/hosted/HostedAttestationView";
import { Loading } from "@/components/app/PageTitle";

export const metadata: Metadata = { title: "Attestation" };

export default function HostedAttestationPage() {
  return (
    <Suspense fallback={<Loading />}>
      <HostedAttestationView />
    </Suspense>
  );
}
