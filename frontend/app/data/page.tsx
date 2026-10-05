import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { JsonLd } from "@/components/site/JsonLd";
import { Picture } from "@/components/Picture";
import { dataPage } from "@/lib/content";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, techArticleLd } from "@/lib/seo";

const description = "What enters a Suncly test and what leaves it: the data inventory, the anatomy of a report folder, how deletion works, and what changes when the hosted API arrives.";

export const metadata: Metadata = pageMeta({ title: "Data: what enters a test, and what leaves it", description, path: "/data", type: "article", keywords: [...KEYWORDS.evidence, "AI agent test data handling", "redacted transcripts"] });

export default function DataPage() {
  const d = dataPage;
  return (
    <SiteLayout>
      <JsonLd data={graph(techArticleLd({ path: "/data", headline: d.headline, description }), breadcrumbLd([{ name: "Data", path: "/data" }]))} />
      <PageHeader eyebrow="Suncly Data" headline={d.headline} intro={d.intro} />
      <Section>
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
          <article className="prose-site">
            <h2>{d.inventory.title}</h2>
            <table tabIndex={0}>
              <thead><tr>{d.inventory.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>{d.inventory.rows.map((r) => <tr key={r[0]}>{r.map((c, i) => <td key={i}>{c}</td>)}</tr>)}</tbody>
            </table>
            <h2>{d.anatomy.title}</h2>
            <table tabIndex={0}>
              <thead><tr><th>File</th><th>Contents</th></tr></thead>
              <tbody>{d.anatomy.rows.map((r) => <tr key={r[0]}><td><code>{r[0]}</code></td><td>{r[1]}</td></tr>)}</tbody>
            </table>
            <h2>{d.deletion.title}</h2>
            <p>{d.deletion.body}</p>
            <h2>{d.hosted.title}</h2>
            <ul>{d.hosted.items.map((i) => <li key={i}>{i}</li>)}</ul>
            <p className="summary">
              Verified against <code>src/suncly</code> on 2026-10-05. The security page covers credentials, redaction and the non-negotiable rules: <Link href="/security">/security</Link>. The Privacy Policy covers this website: <Link href="/privacy">/privacy</Link>.
            </p>
          </article>
          <div className="lg:sticky lg:top-24 lg:self-start">
            <Picture name="aperture" alt="A closed box with one narrow slit. A single blade of light leaves it toward the lower left." sizes="(min-width: 1024px) 40vw, 100vw" className="aspect-[4/3]" />
          </div>
        </div>
      </Section>
    </SiteLayout>
  );
}
