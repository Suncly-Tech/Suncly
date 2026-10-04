import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { ProblemStrip } from "@/components/ProblemStrip";
import { Inspection } from "@/components/Inspection";
import { HowItWorks } from "@/components/HowItWorks";
import { Architecture } from "@/components/Architecture";
import { ProductSections } from "@/components/ProductSections";
import { Policy } from "@/components/Policy";
import { Rules } from "@/components/Rules";
import { OpenStandard } from "@/components/OpenStandard";
import { Interfaces } from "@/components/Interfaces";
import { Roadmap } from "@/components/Roadmap";
import { DevResources } from "@/components/DevResources";
import { EarlyAccess } from "@/components/EarlyAccess";
import { Faq } from "@/components/Faq";
import { Footer } from "@/components/Footer";
import { CutsDivider } from "@/components/Cuts";

export default function Home() {
  return (
    <>
      <Nav />
      <main id="main">
        <Hero />
        <ProblemStrip />
        <Inspection />
        <HowItWorks />
        <Architecture />
        <ProductSections />
        <Policy />
        <Rules />
        <OpenStandard />
        <Interfaces />
        <Roadmap />
        <CutsDivider />
        <DevResources />
        <EarlyAccess />
        <Faq />
      </main>
      <Footer />
    </>
  );
}
