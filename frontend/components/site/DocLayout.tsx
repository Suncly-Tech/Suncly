import Link from "next/link";
import type { ReactNode } from "react";
import { SiteLayout, PageHeader } from "./SiteLayout";
import { FinalCta } from "./FinalCta";

const guides = [
  { href: "/docs", label: "Documentation" },
  { href: "/docs/getting-started", label: "Getting started" },
  { href: "/docs/cli", label: "Command reference" },
  { href: "/docs/evidence", label: "Evidence and reports" },
];

export function DocLayout({
  eyebrow,
  headline,
  intro,
  current,
  toc,
  children,
}: {
  eyebrow: string;
  headline: string;
  intro: string;
  current: string;
  toc: Array<{ id: string; title: string }>;
  children: ReactNode;
}) {
  return (
    <SiteLayout>
      <PageHeader eyebrow={eyebrow} headline={headline} intro={intro} />
      <section className="py-12 md:py-16">
        <div className="container-site grid gap-12 lg:grid-cols-[minmax(0,3fr)_minmax(0,9fr)] lg:gap-16">
          <aside className="flex flex-col gap-8 lg:sticky lg:top-28 lg:self-start">
            <nav aria-label="Guides">
              <p className="text-eyebrow text-ink-soft">Guides</p>
              <ul className="mt-4 flex flex-col gap-1 text-small">
                {guides.map((g) => (
                  <li key={g.href}>
                    <Link
                      href={g.href}
                      aria-current={g.href === current ? "page" : undefined}
                      className={`inline-block py-1 hover:text-ink ${g.href === current ? "font-semibold text-ink" : "text-ink-soft"}`}
                    >
                      {g.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
            {toc.length ? (
              <nav aria-label="On this page" className="hidden lg:block">
                <p className="text-eyebrow text-ink-soft">On this page</p>
                <ol className="mt-4 flex flex-col gap-1 text-small">
                  {toc.map((t) => (
                    <li key={t.id}>
                      <Link href={`#${t.id}`} className="inline-block py-1 text-ink-soft hover:text-ink">
                        {t.title}
                      </Link>
                    </li>
                  ))}
                </ol>
              </nav>
            ) : null}
          </aside>
          <article className="prose-site min-w-0 max-w-[760px]">{children}</article>
        </div>
      </section>
      <FinalCta />
    </SiteLayout>
  );
}
