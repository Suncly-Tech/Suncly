import type { Metadata } from "next";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { DraftNotice, Blank } from "@/components/site/Legal";
import { legalNoticePage, site } from "@/lib/content";
import { company, launch } from "@/lib/launch";
import { pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({ title: "Legal notice", description: "Company details for Suncly, and a summary in Estonian of what Suncly offers.", path: "/legal", noindex: !launch.legalPublished });

export default function LegalNoticePage() {
  const l = legalNoticePage;
  const facts: Array<[string, string | null]> = [
    ["Business name", company.legalEntityName],
    ["Registry code and register", company.registryCode ? `${company.registryCode}, Estonian Commercial Register` : null],
    ["Registered office", company.registeredOffice],
    ["VAT number", company.vatNumber],
    ["E-mail", company.contactEmail],
    ["Location", site.city],
  ];
  return (
    <SiteLayout>
      <PageHeader eyebrow="Legal" headline={l.headline} intro={l.intro} />
      <Section narrow>
        <DraftNotice page="legal notice" needs={["legal entity name", "registry code", "registered office", "VAT number"]} />
        <article className="prose-site">
          <h2>Company details</h2>
          <table tabIndex={0}>
            <tbody>
              {facts.map(([k, v]) => (
                <tr key={k}>
                  <th scope="row">{k}</th>
                  <td>{v ?? <Blank what={k.toLowerCase()} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h2>{l.estonianTitle}</h2>
          <p lang="et">{l.estonian}</p>
          <p className="summary">The Estonian summary is a draft for founder review; the Language Act asks for a summary in Estonian of the field of activity on a foreign-language site of an Estonian company.</p>
          <h2>Trade marks and attribution</h2>
          <p>Suncly and the sun mark are trade marks of the company named above. No registration is claimed. Agent2Agent (A2A) is an open-source project of the Linux Foundation; Suncly is independent and is not affiliated with, endorsed by or certified by the Linux Foundation or the A2A project. Other names belong to their owners and are used only to say where Suncly runs or what it tests.</p>
        </article>
      </Section>
    </SiteLayout>
  );
}
