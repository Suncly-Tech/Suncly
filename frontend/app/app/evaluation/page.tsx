import type { Metadata } from "next";
import { Suspense } from "react";
import { EvaluationPage } from "@/components/app/EvaluationPage";
import { Loading } from "@/components/app/PageTitle";

export const metadata: Metadata = { title: "Evaluation" };

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <EvaluationPage />
    </Suspense>
  );
}
