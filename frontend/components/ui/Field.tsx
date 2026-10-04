import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { AlertCircle } from "lucide-react";

export function Field({
  id,
  label,
  help,
  error,
  children,
  required,
}: {
  id: string;
  label: ReactNode;
  help?: ReactNode;
  error?: string | null;
  children: ReactNode;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-small font-semibold text-ink">
        {label}
        {required ? (
          <span className="ml-1 text-fail" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {children}
      {help ? (
        <p id={`${id}-help`} className="text-[13px] leading-snug text-ink-soft">
          {help}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="flex items-start gap-1.5 text-[13px] font-medium text-fail">
          <AlertCircle size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function describedBy(id: string, hasHelp: boolean, hasError: boolean): string | undefined {
  const ids = [hasHelp ? `${id}-help` : null, hasError ? `${id}-error` : null].filter(Boolean);
  return ids.length ? ids.join(" ") : undefined;
}

export function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`input-base ${className}`} {...props} />;
}

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`input-base min-h-[120px] resize-y ${className}`} {...props} />;
}

export function Select({ className = "", children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`input-base appearance-none bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2216%22 height=%2216%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%235b5e6b%22 stroke-width=%222.5%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><path d=%22m6 9 6 6 6-6%22/></svg>')] bg-[length:16px] bg-[position:right_14px_center] bg-no-repeat pr-10 ${className}`} {...props}>
      {children}
    </select>
  );
}

export function Checkbox({
  id,
  label,
  description,
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { id: string; label: ReactNode; description?: ReactNode }) {
  return (
    <div className={`flex items-start gap-3 ${className}`}>
      <input id={id} type="checkbox" className="checkbox-base mt-0.5" {...props} />
      <label htmlFor={id} className="cursor-pointer text-[15px] leading-snug text-ink">
        <span className="font-semibold">{label}</span>
        {description ? <span className="mt-0.5 block text-[13px] text-ink-soft">{description}</span> : null}
      </label>
    </div>
  );
}
