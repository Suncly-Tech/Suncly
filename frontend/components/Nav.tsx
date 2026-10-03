"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { nav } from "@/lib/content";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const solid = scrolled || open;

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
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onResize = () => {
      if (window.innerWidth >= 768) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("resize", onResize);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-control focus:bg-paper focus:px-4 focus:py-2 focus:text-ink"
      >
        Skip to content
      </a>

      {/* The bar carries the blur; the menu panel sits outside it so `fixed` still means the viewport. */}
      <div
        className={`relative z-10 transition-[background-color,box-shadow] duration-200 ${
          solid ? "bg-cream/85 backdrop-blur-md hairline-b" : "bg-transparent"
        }`}
      >
        <div className="container-site flex h-16 items-center justify-between md:h-20">
          <Logo tone={solid ? "ink" : "paper"} />

          <nav aria-label="Primary" className="hidden items-center gap-8 md:flex">
            {nav.links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`inline-flex min-h-11 items-center text-[15px] font-semibold transition-colors duration-200 ${
                  solid ? "text-ink/80 hover:text-ink" : "text-paper/85 hover:text-paper"
                }`}
              >
                {l.label}
              </Link>
            ))}
            <Link href={nav.cta.href} className="btn-base btn-primary h-11 min-h-11 px-5 text-[15px]">
              {nav.cta.label}
            </Link>
          </nav>

          <button
            type="button"
            className={`inline-flex h-11 w-11 items-center justify-center rounded-control md:hidden ${
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

      <div
        id="mobile-menu"
        hidden={!open}
        className="fixed inset-x-0 top-16 bottom-0 z-0 bg-cream md:hidden"
      >
        <nav aria-label="Mobile" className="container-site flex h-full flex-col justify-between py-8">
          <ul className="flex flex-col gap-1">
            {nav.links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="cuts-bullet block py-3 font-display text-[36px] leading-tight text-ink"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
          <Link
            href={nav.cta.href}
            onClick={() => setOpen(false)}
            className="btn-base btn-primary w-full"
          >
            {nav.cta.label}
          </Link>
        </nav>
      </div>
    </header>
  );
}
