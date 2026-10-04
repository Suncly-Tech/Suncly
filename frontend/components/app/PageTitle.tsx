import type { ReactNode } from "react";

export function PageTitle({ title, intro, actions, children }: { title: string; intro?: ReactNode; actions?: ReactNode; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:mb-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-[720px]">
          <h1 className="text-heading-lg text-ink md:text-[32px]">{title}</h1>
          {intro ? <p className="mt-2 text-body text-ink-soft">{intro}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      {children}
    </div>
  );
}

export function Loading({ label = "Loading the workspace" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-3">
      <span className="sr-only">{label}</span>
      <div className="h-8 w-64 animate-pulse rounded-[8px] bg-cream-deep" aria-hidden="true" />
      <div className="h-24 animate-pulse rounded-[16px] bg-cream-deep" aria-hidden="true" />
      <div className="h-48 animate-pulse rounded-[16px] bg-cream-deep" aria-hidden="true" />
    </div>
  );
}
