import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, FileText } from "lucide-react";
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
        <div className="container-site py-16 md:py-24">
          <div className="max-w-[760px]">
            <div className="flex items-center gap-3 text-eyebrow text-ink-soft">
              <Cuts className="text-sun" height={12} stroke={3} />
              {docsPage.title}
            </div>
            <h1 className="mt-6 text-display-lg text-balance text-ink">{docsPage.headline}</h1>
            <p className="mt-6 text-body text-ink-soft md:text-[19px]">{docsPage.body}</p>
            <p className="mt-4 inline-block rounded-[12px] bg-cream-deep px-4 py-3 text-small text-ink">{docsPage.status}</p>
          </div>

          <ol className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-2 lg:gap-6">
            {docsPage.docs.map((d) => (
              <li key={d.file} className="flex flex-col rounded-card bg-paper p-6 ring-1 ring-ink/5 md:p-8">
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-control bg-cream text-ink">
                    <FileText size={18} aria-hidden="true" />
                  </span>
                  <span className="font-mono text-[13px] text-ink-soft">{d.file}</span>
                </div>
                <h2 className="mt-5 text-heading-md text-ink">{d.title}</h2>
                <p className="mt-2 text-small text-ink-soft md:text-[15px]">{d.body}</p>
              </li>
            ))}
          </ol>

          <div className="mt-12 grid grid-cols-1 gap-8 rounded-card bg-ink p-6 text-paper md:p-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
            <h2 className="text-display-md text-paper">{docsPage.howToRead.title}</h2>
            <ul className="flex flex-col gap-4">
              {docsPage.howToRead.items.map((it) => (
                <li key={it} className="cuts-bullet text-sun">
                  <span className="text-body text-paper/85">{it}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="mt-12 flex flex-wrap items-center gap-4">
            <PrimaryButton href={docsPage.cta.href}>{docsPage.cta.label}</PrimaryButton>
            <a href={`mailto:${site.email}`} className="btn-base btn-ghost text-ink">
              {site.email}
            </a>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
