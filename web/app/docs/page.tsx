import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Footer } from "@/components/Footer";
import { Logo } from "@/components/Logo";
import { Cuts } from "@/components/Cuts";
import { PrimaryButton } from "@/components/Button";
import { docsPage, site } from "@/lib/content";

export const metadata: Metadata = {
  title: docsPage.title,
  description: docsPage.body,
  alternates: { canonical: "/docs" },
};

export default function DocsPage() {
  return (
    <>
      <header className="bg-cream hairline-b">
        <div className="container-site flex h-16 items-center justify-between md:h-20">
          <Logo />
          <Link
            href={docsPage.back.href}
            className="inline-flex min-h-11 items-center gap-2 text-[15px] font-semibold text-ink/80 hover:text-ink"
          >
            <ArrowLeft size={16} aria-hidden="true" />
            {docsPage.back.label}
          </Link>
        </div>
      </header>
      <main id="main" className="bg-cream">
        <div className="container-site py-20 md:py-32">
          <div className="max-w-2xl">
            <div className="flex items-center gap-3 text-eyebrow text-ink-soft">
              <Cuts className="text-sun" height={12} stroke={3} />
              {docsPage.title}
            </div>
            <h1 className="mt-6 text-display-lg text-ink">{docsPage.headline}</h1>
            <p className="mt-6 text-body text-ink-soft md:text-[19px]">{docsPage.body}</p>
            <div className="mt-10 flex flex-wrap items-center gap-4">
              <PrimaryButton href={docsPage.cta.href}>{docsPage.cta.label}</PrimaryButton>
              <a
                href={`mailto:${site.email}`}
                className="btn-base btn-ghost text-ink"
              >
                {site.email}
              </a>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
