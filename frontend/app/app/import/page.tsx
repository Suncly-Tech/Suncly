import type { Metadata } from "next";
import { ImportView } from "@/components/app/ImportView";

export const metadata: Metadata = { title: "Import report" };

export default function ImportPage() {
  return <ImportView />;
}
