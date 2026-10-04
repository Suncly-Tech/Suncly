import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "md" | "sm";

const variantClass: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

type LinkProps = {
  href: string;
  children: ReactNode;
  className?: string;
  variant?: Variant;
  size?: Size;
  arrow?: boolean;
  external?: boolean;
};

export function ButtonLink({
  href,
  children,
  className = "",
  variant = "primary",
  size = "md",
  arrow = false,
  external = false,
}: LinkProps) {
  const cls = `btn-base ${variantClass[variant]} ${size === "sm" ? "btn-sm" : ""} ${className}`;
  const content = (
    <>
      {children}
      {arrow ? <ArrowRight size={18} strokeWidth={2.25} aria-hidden="true" /> : null}
    </>
  );
  if (external || href.startsWith("mailto:")) {
    return (
      <a href={href} className={cls}>
        {content}
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {content}
    </Link>
  );
}

export function Button({
  children,
  className = "",
  variant = "primary",
  size = "md",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      type={type}
      className={`btn-base ${variantClass[variant]} ${size === "sm" ? "btn-sm" : ""} disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

/* Kept for the existing marketing sections. */
export function PrimaryButton({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <ButtonLink href={href} variant="primary" className={className}>
      {children}
    </ButtonLink>
  );
}

export function GhostButton({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <ButtonLink href={href} variant="ghost" arrow className={className}>
      {children}
    </ButtonLink>
  );
}
