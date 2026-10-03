import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { ProblemStrip } from "@/components/ProblemStrip";
import { HowItWorks } from "@/components/HowItWorks";
import { ProductSections } from "@/components/ProductSections";
import { OpenStandard } from "@/components/OpenStandard";
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
        <CutsDivider />
        <HowItWorks />
        <ProductSections />
        <OpenStandard />
        <DevResources />
        <EarlyAccess />
        <Faq />
      </main>
      <Footer />
    </>
  );
}
