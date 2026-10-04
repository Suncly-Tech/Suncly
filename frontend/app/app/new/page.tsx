import type { Metadata } from "next";
import { SetupForm } from "@/components/app/SetupForm";

export const metadata: Metadata = { title: "New evaluation" };

export default function NewEvaluationPage() {
  return <SetupForm />;
}
