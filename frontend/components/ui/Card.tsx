import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  as: Tag = "div",
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article" | "li";
  padded?: boolean;
}) {
  return <Tag className={`surface ${padded ? "p-5 md:p-6" : ""} ${className}`}>{children}</Tag>;
}

export function CardHeader({
  title,
  description,
  action,
  as: Tag = "h2",
  id,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  as?: "h2" | "h3" | "h4";
  id?: string;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <Tag id={id} className="text-heading-md text-ink">
          {title}
        </Tag>
        {description ? <p className="mt-1 text-small text-ink-soft">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
