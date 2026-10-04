import type { Metadata } from "next";
import { AppShell } from "@/components/app/AppShell";

export const metadata: Metadata = {
  title: { default: "Review workspace", template: "%s — Suncly workspace" },
  description: "Read Suncly report folders in your browser: overview, agent history, evidence per run, verification, comparison and review notes.",
  robots: { index: false, follow: false },
  alternates: { canonical: "/app" },
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
