import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { ClaimChain, Coverage, ManualComparison, Problem, Process, Scope } from "@/components/home/Sections";
import { Faq } from "@/components/Faq";
import { FinalCta } from "@/components/site/FinalCta";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <>
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
