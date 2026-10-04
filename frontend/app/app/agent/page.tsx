import type { Metadata } from "next";
import { Suspense } from "react";
import { AgentPage } from "@/components/app/AgentPage";
import { Loading } from "@/components/app/PageTitle";

export const metadata: Metadata = { title: "Agent" };

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <AgentPage />
    </Suspense>
  );
}
