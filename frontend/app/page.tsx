import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { ClaimChain, Coverage, ManualComparison, Problem, Process, Scope } from "@/components/home/Sections";
import { Faq } from "@/components/Faq";
import { FinalCta } from "@/components/site/FinalCta";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/site/JsonLd";
import { faq, site } from "@/lib/content";
import { faqLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";
import type { Metadata } from "next";

export const metadata: Metadata = {
  ...pageMeta({
    title: "Evaluate AI agents before you approve them",
    description: site.description,
    path: "/",
    keywords: [...KEYWORDS.core, ...KEYWORDS.protocol],
  }),
  title: { absolute: site.title },
};

export default function Home() {
  return (
    <>
      <JsonLd
        data={graph(
          webPageLd({ path: "/", name: "Evaluate AI agents before you approve them", description: site.description }),
          faqLd(faq.items),
        )}
      />
      <Nav variant="hero" />
      <main id="main">
        <Hero />
        <Problem />
        <ClaimChain />
        <Process />
        <ManualComparison />
        <Coverage />
        <Scope />
        <Faq />
        <FinalCta />
      </main>
      <Footer />
    </>
  );
}
