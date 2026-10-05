import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { cookiesPage } from "@/lib/content";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({ title: "Cookies", description: "This site sets no cookies. What the review workspace stores in your browser, as inspected.", path: "/cookies" });

export default function CookiesPage() {
  const c = cookiesPage;
  return (
    <SiteLayout>
      <PageHeader eyebrow="Legal" headline={c.headline} intro={c.intro} />
      <Section narrow>
        <article className="prose-site">
          <h2>Storage, as inspected</h2>
          <table tabIndex={0}>
            <caption className="sr-only">{c.tableCaption}</caption>
            <thead><tr>{c.columns.map((col) => <th key={col}>{col}</th>)}</tr></thead>
            <tbody>{c.rows.map((r) => <tr key={r[0]}>{r.map((cell, i) => <td key={i}>{cell}</td>)}</tr>)}</tbody>
          </table>
          <h2>Consent</h2>
          <p>{c.consent}</p>
          <h2>Fonts and scripts</h2>
          <p>Fonts are self-hosted; no font request leaves the site. There are no third-party scripts, no embedded players and no analytics. The inspection script is <code>frontend/scripts/inspect-storage.mjs</code>, and its last result is in <code>frontend/VERIFICATION.md</code>.</p>
          <p className="summary">See also the <Link href="/privacy">Privacy Policy</Link>.</p>
        </article>
      </Section>
    </SiteLayout>
  );
}
