import type { ReactNode } from "react";
import { Cuts } from "@/components/Cuts";

export function EmptyState({
  title,
  body,
  actions,
  className = "",
}: {
  title: string;
  body?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`surface-sunken flex flex-col items-start gap-4 p-6 md:p-8 ${className}`}>
      <Cuts className="text-sun" height={16} stroke={4} />
      <div>
        <h2 className="text-heading-md text-ink">{title}</h2>
        {body ? <div className="mt-2 max-w-[560px] text-body text-ink-soft">{body}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}
