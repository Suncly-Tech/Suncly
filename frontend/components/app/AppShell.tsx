"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { ArrowLeftRight, Download, FilePlus2, LayoutGrid, Settings, ExternalLink, Cloud, Bot, CreditCard } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Badge } from "@/components/ui/Badge";
import { useWorkspaceState } from "@/lib/workspace/store";
import { isConfigured, useConnection } from "@/lib/api/connection";

const items = [
  { href: "/app", label: "Overview", Icon: LayoutGrid, exact: true },
  { href: "/app/new", label: "New evaluation", Icon: FilePlus2 },
  { href: "/app/import", label: "Import report", Icon: Download },
  { href: "/app/compare", label: "Compare", Icon: ArrowLeftRight },
  { href: "/app/settings", label: "Settings", Icon: Settings },
];

const hostedItems = [
  { href: "/app/hosted", label: "Hosted overview", Icon: Cloud, exact: true },
  { href: "/app/hosted/agents", label: "Agents and contracts", Icon: Bot },
  { href: "/app/hosted/billing", label: "Usage and billing", Icon: CreditCard },
];

/** The review workspace frame: sidebar on desktop, a scrolling tab row on phones. */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { state, ready } = useWorkspaceState();
  const connection = useConnection();
  const connected = isConfigured(connection);
  const hasSample = ready && Object.values(state.bundles).some((b) => b.source === "sample");
  const current = (href: string, exact?: boolean) => (exact ? pathname === href : pathname === href || pathname.startsWith(href + "/"));

  return (
    <div className="min-h-dvh bg-cream text-ink">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-control focus:bg-paper focus:px-4 focus:py-2 focus:text-ink"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 bg-cream/90 backdrop-blur-md hairline-b">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-4 px-4 md:px-6">
          <div className="flex min-w-0 items-center gap-4">
            <Logo height={26} />
            <span className="hidden h-5 w-px bg-line-strong sm:block" aria-hidden="true" />
            <div className="hidden min-w-0 flex-col sm:flex">
              <span className="text-[14px] font-semibold leading-tight text-ink">Review workspace</span>
              <span className="text-[12px] leading-tight text-ink-soft">{connected ? "Connected to a Suncly API; imported evidence stays in this browser." : "Offline: evidence stays in this browser. Connect an API under Settings."}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {hasSample ? (
              <Badge tone="sun" title="Sample bundles are loaded; every one carries a sample badge">
                Sample data loaded
              </Badge>
            ) : null}
            {connected ? (
              <Badge tone="info" dot title={`Live pages read ${connection.baseUrl}`}>
                API connected
              </Badge>
            ) : null}
            <Link href="/" className="inline-flex min-h-10 items-center gap-1.5 text-[14px] font-semibold text-ink-soft hover:text-ink">
              Website
              <ExternalLink size={14} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] grid-cols-[minmax(0,1fr)] gap-6 px-4 py-6 md:px-6 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10 lg:py-8">
        <nav aria-label="Workspace" className="min-w-0 max-w-full lg:sticky lg:top-24 lg:self-start">
          <ul className="-mx-4 flex gap-1 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-col lg:px-0 lg:pb-0">
            {items.map(({ href, label, Icon, exact }) => (
              <li key={href} className="shrink-0">
                <Link href={href} className="app-sidebar-link" aria-current={current(href, exact) ? "page" : undefined}>
                  <Icon size={16} aria-hidden="true" />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
          <p className="mt-6 hidden px-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-soft lg:block">Hosted</p>
          <ul className="-mx-4 mt-1 flex gap-1 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-col lg:px-0 lg:pb-0">
            {hostedItems.map(({ href, label, Icon, exact }) => (
              <li key={href} className="shrink-0">
                <Link href={href} className="app-sidebar-link" aria-current={current(href, exact) ? "page" : undefined}>
                  <Icon size={16} aria-hidden="true" />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-8 hidden rounded-[14px] bg-paper p-4 text-[13px] text-ink-soft ring-1 ring-line lg:block">
            <p className="font-semibold text-ink">How this fits</p>
            <p className="mt-1">
              Offline pages read report folders the <code className="code-inline">suncly</code> CLI wrote. Hosted pages talk to a Suncly API where a worker runs attestations against your sandboxes.
            </p>
          </div>
        </nav>
        <main id="main" className="min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
