"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { nav } from "@/lib/content";

/**
 * Site navigation. Paper background, a hairline once the page has scrolled, inverted over
 * dark bands (tone="paper"). On phones, a full-screen sheet with a visible close control,
 * trapped focus and Escape to close.
 */
export function Nav({ tone = "ink" }: { tone?: "ink" | "paper" }) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const dark = tone === "paper" && !open;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const sheet = document.getElementById("mobile-menu");
    const focusables = () =>
      Array.from(sheet?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? []).concat(
        Array.from(document.querySelectorAll<HTMLElement>('[data-menu-toggle]')),
      );
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
      if (e.key === "Tab") {
        const items = focusables();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
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

  const isCurrent = (href: string) => pathname === href || (href !== "/" && !href.startsWith("/#") && pathname.startsWith(href + "/"));
  const text = dark ? "text-paper" : "text-ink";
  const soft = dark ? "text-paper/80 hover:text-paper" : "text-ink/75 hover:text-ink";

  return (
    <header className={`sticky top-0 z-50 ${dark ? "on-dark" : ""}`}>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-control focus:bg-paper focus:px-4 focus:py-2 focus:text-ink"
      >
        Skip to content
      </a>

      <div
        className={`relative z-10 transition-[background-color,box-shadow] duration-200 ${
          open ? "bg-cream" : dark ? "bg-transparent" : scrolled ? "bg-cream/92 backdrop-blur-md hairline-b" : "bg-transparent"
        }`}
      >
        <div className="container-site flex h-16 items-center justify-between gap-6 md:h-[72px]">
          <Logo tone={dark ? "paper" : "ink"} />

          <nav aria-label="Primary" className="hidden items-center gap-7 lg:flex">
            {nav.links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                aria-current={isCurrent(l.href) ? "page" : undefined}
                className={`inline-flex min-h-11 items-center whitespace-nowrap border-b text-[15px] transition-colors duration-200 ${
                  isCurrent(l.href) ? `border-current ${text}` : `border-transparent ${soft}`
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>

          <div className="hidden items-center gap-3 lg:flex">
            <Link href={nav.cta.href} className="btn-base btn-primary h-11 min-h-11 px-5 text-[14.5px]">
              {nav.cta.label}
            </Link>
          </div>

          <button
            type="button"
            data-menu-toggle
            className={`inline-flex h-11 w-11 items-center justify-center rounded-control lg:hidden ${text}`}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? nav.menuClose : nav.menuOpen}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
          </button>
        </div>
      </div>

      <div id="mobile-menu" hidden={!open} className="fixed inset-x-0 bottom-0 top-16 z-0 overflow-y-auto bg-cream lg:hidden">
        <nav aria-label="Mobile" className="container-site flex min-h-full flex-col justify-between py-8">
          <div>
            <ul className="flex flex-col gap-1">
              {nav.links.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    onClick={() => setOpen(false)}
                    aria-current={isCurrent(l.href) ? "page" : undefined}
                    className="cuts-bullet block py-3 font-display text-[34px] leading-tight text-ink"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
            <ul className="mt-8 grid grid-cols-2 gap-x-6 gap-y-1 border-t border-line pt-6">
              {[...nav.more, nav.workspace].map((l) => (
                <li key={l.href}>
                  <Link href={l.href} onClick={() => setOpen(false)} className="block py-2 text-[16px] text-ink-soft">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <Link href={nav.cta.href} onClick={() => setOpen(false)} className="btn-base btn-primary mt-8 w-full">
            {nav.cta.label}
          </Link>
        </nav>
      </div>
    </header>
  );
}
