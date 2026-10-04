import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle, FlaskConical } from "lucide-react";

type Tone = "info" | "warn" | "error" | "success" | "sample";

const styles: Record<Tone, { cls: string; Icon: typeof Info }> = {
  info: { cls: "bg-info-soft text-ink ring-sky/15", Icon: Info },
  warn: { cls: "bg-partial-soft text-ink ring-partial/20", Icon: AlertTriangle },
  error: { cls: "bg-fail-soft text-ink ring-fail/20", Icon: XCircle },
  success: { cls: "bg-pass-soft text-ink ring-pass/20", Icon: CheckCircle2 },
  sample: { cls: "bg-paper text-ink ring-sun", Icon: FlaskConical },
};

const iconColor: Record<Tone, string> = {
  info: "text-sky-deep",
  warn: "text-partial",
  error: "text-fail",
  success: "text-pass",
  sample: "text-ink",
};

export function Notice({
  tone = "info",
  title,
  children,
  className = "",
  role,
  action,
}: {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
  role?: "status" | "alert";
  action?: ReactNode;
}) {
  const { cls, Icon } = styles[tone];
  return (
    <div role={role} className={`flex gap-3 rounded-[14px] p-4 ring-1 ${cls} ${className}`}>
      <Icon size={18} className={`mt-0.5 shrink-0 ${iconColor[tone]}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 text-small">
        {title ? <p className="font-semibold text-ink">{title}</p> : null}
        {children ? <div className={`${title ? "mt-1" : ""} text-ink-soft [&_a]:underline [&_a]:text-ink`}>{children}</div> : null}
      </div>
      {action ? <div className="shrink-0 self-center">{action}</div> : null}
    </div>
  );
}
