import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/site/JsonLd";
import { Hero } from "@/components/home/Hero";
import { WorksWith } from "@/components/home/WorksWith";
import { HowItWorks } from "@/components/home/HowItWorks";
import { InstallSection } from "@/components/home/InstallSection";
import { Evidence } from "@/components/home/Evidence";
import { UseCases } from "@/components/home/UseCases";
import { OfferCertified } from "@/components/home/OfferCertified";
import { Data, Lab, Research } from "@/components/home/DataResearchLab";
import { Stand } from "@/components/home/Stand";
import { Questions } from "@/components/home/Questions";
import { ClosingSky } from "@/components/home/ClosingSky";
import { questions, site } from "@/lib/content";
import { faqLd, graph, KEYWORDS, pageMeta, webPageLd } from "@/lib/seo";

export const metadata: Metadata = {
  ...pageMeta({
    title: "Test the agent. Then decide.",
    description: site.description,
    path: "/",
    keywords: [...KEYWORDS.core, ...KEYWORDS.protocol],
  }),
  title: { absolute: site.title },
};

export default function Home() {
  return (
    <>
      <JsonLd data={graph(webPageLd({ path: "/", name: "Test the agent. Then decide.", description: site.description }), faqLd(questions.items))} />
      <Nav />
      <main id="main">
        <Hero />
        <WorksWith />
        <HowItWorks />
        <InstallSection />
        <Evidence />
        <UseCases />
        <OfferCertified />
        <Data />
        <Research />
        <Lab />
        <Stand />
        <Questions />
        <ClosingSky />
      </main>
      <Footer withFind />
    </>
  );
}
