import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { JsonLd } from "@/components/site/JsonLd";
import { Notice } from "@/components/ui/Notice";
import { Picture } from "@/components/Picture";
import { certifiedPage } from "@/lib/content";
import { certificationRecords } from "@/lib/certified";
import { launch } from "@/lib/launch";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

const description = "Suncly Certified: a private, voluntary badge for A2A agents that met Suncly's published criteria on a date, on a sandbox. The badge files, the usage rules and the public registry.";

export const metadata: Metadata = pageMeta({ title: "Suncly Certified: a badge with the evidence behind it", description, path: "/certified", keywords: [...KEYWORDS.evidence, "Suncly Certified", "AI agent certification badge"] });

export default function CertifiedPage() {
  const c = certifiedPage;
  const open = launch.certificationProgramme === "open";
  return (
    <SiteLayout>
      <JsonLd data={graph(webPageLd({ path: "/certified", name: "Suncly Certified", description }), breadcrumbLd([{ name: "Certified", path: "/certified" }]))} />
      <PageHeader eyebrow="Suncly Certified" headline={c.headline} intro={c.intro} />
      <Section>
        {!open ? (
          <Notice tone="warn" title="Opening with our pilots" className="mb-10">
            {c.state} A first set of criteria is in founder review and is not published; the <Link href="/certified/policy">Certification Policy</Link> (a draft) describes how the programme will work once criteria are adopted.
          </Notice>
        ) : null}
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
          <article className="prose-site">
            <h2 id="registry">{c.registry.title}</h2>
            {certificationRecords.length === 0 ? (
              <p>{c.registry.empty}</p>
            ) : (
              <table tabIndex={0}>
                <thead><tr><th>Record</th><th>Agent</th><th>Operator</th><th>Evaluated</th><th>Valid until</th><th>Status</th></tr></thead>
                <tbody>
                  {certificationRecords.map((r) => (
                    <tr key={r.id}>
                      <td><Link href={`/certified/${r.id}`}>{r.id}</Link></td>
                      <td>{r.agentName} {r.agentVersion}</td>
                      <td>{r.operator}</td>
                      <td>{r.evaluatedOn}</td>
                      <td>{r.validUntil}</td>
                      <td>{r.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <h2 id="record">{c.record.title}</h2>
            <ul>{c.record.items.map((i) => <li key={i}>{i}</li>)}</ul>
            <h2 id="limits">{c.limits.title}</h2>
            <ul>{c.limits.items.map((i) => <li key={i}>{i}</li>)}</ul>
            <p>The full rules, including validity, re-tests, suspension, revocation and appeals, are in the <Link href="/certified/policy">Certification Policy</Link>. Suncly never approves or blocks an agent and never gives a score; certification is Suncly's statement about a named version on a date, not a rating and not a tier.</p>
            <h2 id="badge">{c.badge.title}</h2>
            <p>{c.badge.intro}</p>
            <ul>{c.badge.rules.map((i) => <li key={i}>{i}</li>)}</ul>
            <h3>Files</h3>
            <ul>
              {c.badge.files.map((f) => (
                <li key={f.href}><a href={f.href} download>{f.label}</a></li>
              ))}
            </ul>
            <p className="summary">The files are provided for agents that hold a valid record. No record exists, so every badge shown on this site is a specimen.</p>
          </article>
          <div className="flex flex-col gap-8 lg:sticky lg:top-24 lg:self-start">
            <figure className="m-0">
              <Picture name="seal" alt="The Suncly Certified badge blind-embossed in heavy paper. A specimen." sizes="(min-width: 1024px) 36vw, 100vw" className="aspect-square" />
              {!open ? <figcaption className="mt-2 text-eyebrow text-ink-mute">Specimen</figcaption> : null}
            </figure>
            <div className="grid grid-cols-3 gap-4">
              {(["paper", "dusk", "mono"] as const).map((v) => (
                <figure key={v} className={`m-0 rounded-[12px] p-4 ${v === "dusk" ? "bg-dusk" : "bg-paper ring-1 ring-line"}`}>
                  <img src={`/brand/badge/suncly-certified-${v}.svg`} alt={`Suncly Certified badge, ${v} version`} width={128} height={128} loading="lazy" className="mx-auto h-auto w-full max-w-[128px]" />
                  <figcaption className={`mt-2 text-center text-eyebrow ${v === "dusk" ? "text-paper/70" : "text-ink-soft"}`}>{v}</figcaption>
                </figure>
              ))}
            </div>
          </div>
        </div>
      </Section>
    </SiteLayout>
  );
}
