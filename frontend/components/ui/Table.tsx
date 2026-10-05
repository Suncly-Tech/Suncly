import type { ReactNode } from "react";

export function Table({
  children,
  caption,
  className = "",
}: {
  children: ReactNode;
  /** Visually hidden caption for screen readers. */
  caption: string;
  className?: string;
}) {
  return (
    <div className={`table-wrap ${className}`} tabIndex={0} aria-label={caption}>
      <table className="table-base">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}
