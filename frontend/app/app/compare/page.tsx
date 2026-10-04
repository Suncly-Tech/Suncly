import type { Metadata } from "next";
import { Suspense } from "react";
import { ComparePage } from "@/components/app/ComparePage";
import { Loading } from "@/components/app/PageTitle";

export const metadata: Metadata = { title: "Compare" };

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <ComparePage />
    </Suspense>
  );
}
