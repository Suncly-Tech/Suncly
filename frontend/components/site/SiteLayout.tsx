import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { Cuts } from "@/components/Cuts";

/** Inner marketing pages: solid nav, cream body, footer. */
export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <Nav />
      <main id="main" className="bg-cream">
        {children}
      </main>
      <Footer />
    </>
  );
}

export function PageHeader({
  eyebrow,
  headline,
  intro,
  children,
  tone = "cream",
}: {
  eyebrow: string;
  headline: string;
  intro?: string;
  children?: ReactNode;
  tone?: "cream" | "ink";
}) {
  const ink = tone === "ink";
  return (
    <section className={`${ink ? "bg-ink text-paper" : "bg-cream text-ink"} border-b ${ink ? "border-paper/10" : "border-line"}`}>
      <div className="container-site py-14 md:py-20">
        <div className="max-w-[820px]">
          <div className={`flex items-center gap-3 text-eyebrow ${ink ? "text-paper/70" : "text-ink-soft"}`}>
            <Cuts className="text-sun" height={12} stroke={3} />
            <span>{eyebrow}</span>
          </div>
          <h1 className={`mt-5 text-display-lg text-balance ${ink ? "text-paper" : "text-ink"}`}>{headline}</h1>
          {intro ? (
            <p className={`mt-6 max-w-[680px] text-pretty text-body md:text-[19px] ${ink ? "text-paper/75" : "text-ink-soft"}`}>{intro}</p>
          ) : null}
          {children ? <div className="mt-8">{children}</div> : null}
        </div>
      </div>
    </section>
  );
}

export function Section({
  id,
  children,
  className = "",
  tone = "cream",
  narrow = false,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
  tone?: "cream" | "paper" | "ink" | "dusk";
  narrow?: boolean;
}) {
  const bg =
    tone === "paper" ? "bg-paper" : tone === "ink" ? "bg-ink text-paper" : tone === "dusk" ? "bg-dusk text-paper" : "bg-cream";
  return (
    <section id={id} className={`scroll-mt-20 py-16 md:py-24 ${bg} ${className}`}>
      <div className={`container-site ${narrow ? "max-w-[880px]" : ""}`}>{children}</div>
    </section>
  );
}
