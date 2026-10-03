import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  href: string;
  children: ReactNode;
  className?: string;
};

export function PrimaryButton({ href, children, className = "" }: Props) {
  return (
    <Link href={href} className={`btn-base btn-primary ${className}`}>
      {children}
    </Link>
  );
}

export function GhostButton({ href, children, className = "" }: Props) {
  return (
    <Link href={href} className={`btn-base btn-ghost ${className}`}>
      {children}
      <ArrowRight size={18} strokeWidth={2.25} aria-hidden="true" />
    </Link>
  );
}
