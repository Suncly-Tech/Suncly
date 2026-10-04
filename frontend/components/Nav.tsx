"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { nav } from "@/lib/content";

/**
 * Site navigation. On the home page it starts transparent over the blue hero and turns
 * solid on scroll; on every other page it is solid from the start.
 */
export function Nav({ variant = "solid" }: { variant?: "hero" | "solid" }) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const solid = variant === "solid" || scrolled || open;

  useEffect(() => {
    if (variant !== "hero") return;
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [variant]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onResize = () => {
      if (window.innerWidth >= 1024) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  const isCurrent = (href: string) => pathname === href || (href !== "/" && pathname.startsWith(href + "/"));

  return (
    <header className={variant === "hero" ? "fixed inset-x-0 top-0 z-50" : "sticky top-0 z-50"}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-control focus:bg-paper focus:px-4 focus:py-2 focus:text-ink"
      >
        Skip to content
      </a>

      <div
        className={`relative z-10 transition-[background-color,box-shadow] duration-200 ${
          solid ? "bg-cream/90 backdrop-blur-md hairline-b" : "bg-transparent"
        }`}
      >
        <div className="container-site flex h-16 items-center justify-between gap-6 md:h-[72px]">
          <Logo tone={solid ? "ink" : "paper"} />

          <nav aria-label="Primary" className="hidden items-center gap-4 lg:flex xl:gap-6">
            {nav.links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                aria-current={isCurrent(l.href) ? "page" : undefined}
                className={`inline-flex min-h-11 items-center whitespace-nowrap border-b-2 text-[14px] font-semibold transition-colors duration-200 xl:text-[15px] ${
                  isCurrent(l.href)
                    ? solid
                      ? "border-sun text-ink"
                      : "border-sun text-paper"
                    : solid
                      ? "border-transparent text-ink/75 hover:text-ink"
                      : "border-transparent text-paper/85 hover:text-paper"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>

          <div className="hidden items-center gap-3 lg:flex">
            <Link
              href={nav.workspace.href}
              className={`hidden min-h-11 items-center whitespace-nowrap px-2 text-[15px] font-semibold xl:inline-flex ${
                solid ? "text-ink/75 hover:text-ink" : "text-paper/85 hover:text-paper"
              }`}
            >
              {nav.workspace.label}
            </Link>
            <Link href={nav.cta.href} className="btn-base btn-primary h-11 min-h-11 px-4 text-[14px] xl:px-5 xl:text-[15px]">
              {nav.cta.label}
            </Link>
          </div>

          <button
            type="button"
            className={`inline-flex h-11 w-11 items-center justify-center rounded-control lg:hidden ${
              solid ? "text-ink" : "text-paper"
            }`}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? nav.menuClose : nav.menuOpen}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
          </button>
        </div>
      </div>

      <div id="mobile-menu" hidden={!open} className="fixed inset-x-0 top-16 bottom-0 z-0 overflow-y-auto bg-cream lg:hidden">
        <nav aria-label="Mobile" className="container-site flex min-h-full flex-col justify-between py-8">
          <ul className="flex flex-col gap-1">
            {nav.links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  aria-current={isCurrent(l.href) ? "page" : undefined}
                  className="cuts-bullet block py-3 font-display text-[32px] leading-tight text-ink"
                >
                  {l.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                href={nav.workspace.href}
                onClick={() => setOpen(false)}
                className="cuts-bullet block py-3 font-display text-[32px] leading-tight text-ink-soft"
              >
                {nav.workspace.label}
              </Link>
            </li>
          </ul>
          <Link href={nav.cta.href} onClick={() => setOpen(false)} className="btn-base btn-primary mt-8 w-full">
            {nav.cta.label}
          </Link>
        </nav>
      </div>
    </header>
  );
}
