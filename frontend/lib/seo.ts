/**
 * Search and answer-engine optimisation: one place for the brand entity, the keyword
 * clusters, per-page metadata and the JSON-LD builders. Every statement here must stay
 * true to the implementation (see CONTENT.md); no ratings, reviews, prices or claims
 * the site does not make elsewhere.
 */

import type { Metadata } from "next";
import { hero, site } from "@/lib/content";
import { socialLinks } from "@/lib/launch";

export const BRAND = "Suncly";
export const DOMAIN = site.domain;

/** The canonical one-paragraph definition. Reused verbatim so every engine sees one entity. */
export const DEFINITION = `${site.definition} It charges only for usage of its API, and agents that meet its published criteria can carry the Suncly Certified badge, which links to the record behind it.`;

export const SHORT_DEFINITION =
  "Suncly tests A2A AI agents against their Agent Card claims before approval: repeated sandbox tests, deterministic verdicts, signed evidence and an explicit list of what was not tested.";

export const KEYWORDS = {
  brand: ["Suncly", "Suncly AI", "Suncly agent evaluation", "suncly.com"],
  core: [
    "AI agent evaluation",
    "evaluate AI agents before approval",
    "AI agent approval",
    "AI agent testing tool",
    "AI agent behavioral testing",
    "AI agent governance",
    "AI agent security review",
    "pre-deployment agent evaluation",
    "agent evaluation evidence",
  ],
  protocol: [
    "A2A protocol",
    "Agent2Agent protocol",
    "A2A agent testing",
    "Agent Card verification",
    "A2A Agent Card",
    "agent attestation",
    "A2A JSON-RPC",
  ],
  evidence: [
    "signed evidence for AI agents",
    "AI agent audit trail",
    "AI agent evaluation report",
    "regression testing for AI agents",
    "what was not tested",
    "inconclusive test results",
  ],
  audience: [
    "platform team agent approval",
    "security team AI agent review",
    "agent registry approval",
    "CI gate for AI agents",
  ],
} as const;

export const ALL_KEYWORDS: string[] = Object.values(KEYWORDS).flat();

export function absoluteUrl(path: string): string {
  return path.startsWith("http") ? path : `${DOMAIN}${path === "/" ? "" : path}`;
}

/** Metadata for one public page: title, description, canonical, keywords, Open Graph, Twitter. */
export function pageMeta({
  title,
  description,
  path,
  keywords = [],
  type = "website",
  noindex = false,
}: {
  title: string;
  description: string;
  path: string;
  keywords?: readonly string[];
  type?: "website" | "article";
  noindex?: boolean;
}): Metadata {
  const url = absoluteUrl(path);
  return {
    title,
    description,
    keywords: [...new Set([...KEYWORDS.brand, ...keywords])],
    alternates: { canonical: path },
    openGraph: {
      type,
      url,
      siteName: BRAND,
      title: `${title} — ${BRAND}`,
      description,
      locale: "en_US",
      images: [{ url: "/og.png", width: 1200, height: 630, alt: `${BRAND}. Test the agent. Then decide.` }],
    },
    twitter: { card: "summary_large_image", title: `${title} — ${BRAND}`, description, images: ["/og.png"] },
    robots: noindex ? { index: false, follow: false } : { index: true, follow: true, googleBot: { index: true, follow: true, "max-snippet": -1, "max-image-preview": "large", "max-video-preview": -1 } },
  };
}

/* ---------------------------------------------------------------------------------- */
/* JSON-LD                                                                            */
/* ---------------------------------------------------------------------------------- */

type Json = Record<string, unknown>;

export const ORGANIZATION_ID = `${DOMAIN}/#organization`;
export const WEBSITE_ID = `${DOMAIN}/#website`;
export const SOFTWARE_ID = `${DOMAIN}/#software`;

export function organizationLd(): Json {
  return {
    "@type": "Organization",
    "@id": ORGANIZATION_ID,
    name: BRAND,
    legalName: BRAND,
    url: DOMAIN,
    logo: { "@type": "ImageObject", url: `${DOMAIN}/icon-512.png`, width: 512, height: 512 },
    image: `${DOMAIN}/og.png`,
    description: DEFINITION,
    sameAs: socialLinks.map((s) => s.url),
    email: site.email,
    foundingLocation: { "@type": "Place", name: "Tallinn, Estonia" },
    address: { "@type": "PostalAddress", addressLocality: "Tallinn", addressCountry: "EE" },
    contactPoint: [{ "@type": "ContactPoint", contactType: "sales", email: site.email, availableLanguage: ["en"] }],
    disambiguatingDescription: SHORT_DEFINITION,
    slogan: hero.headline.join(" "),
    knowsLanguage: "en",
    knowsAbout: knowsAbout(),
    brand: {
      "@type": "Brand",
      name: "Suncly Certified",
      url: `${DOMAIN}/certified`,
      description:
        "A private, voluntary badge for A2A agents that met Suncly's published criteria on a date, on a sandbox. The badge links to the record behind it.",
    },
    keywords: [...KEYWORDS.core, ...KEYWORDS.protocol].join(", "),
    mainEntityOfPage: `${DOMAIN}/company`,
    // sameAs profiles come from lib/launch.ts (X, LinkedIn, GitHub, Reddit); Hacker News is blank. See SEO.md.
  };
}

/** The A2A specification the tool implements (A2A 1.0 over JSON-RPC 2.0; docs/ and README cite v1.0.1). */
const A2A_SPEC_URLS = [
  "https://a2a-protocol.org/latest/specification/",
  "https://github.com/a2aproject/A2A",
] as const;

/**
 * What the organisation knows about: one named topic per entry, each pointing at the page
 * on this site that defines or documents it, and the protocol also at its public
 * specification. Only subjects the implementation covers (CONTENT.md): Suncly evaluates
 * A2A agents; it does no authentication, issues no identities and does not speak the
 * Model Context Protocol, so none of those are listed.
 */
export function knowsAbout(): Json[] {
  const about = (name: string, path: string, extra: Json = {}): Json => ({ "@type": "Thing", name, url: absoluteUrl(path), ...extra });
  return [
    about("Agent2Agent (A2A) protocol", "/glossary#a2a-protocol", { sameAs: [...A2A_SPEC_URLS] }),
    about("A2A Agent Card", "/glossary#agent-card"),
    about("A2A JSON-RPC 2.0 binding", "/workflows"),
    about("AI agent evaluation", "/glossary#ai-agent-evaluation"),
    about("AI agent approval", "/product"),
    about("AI agent governance", "/product"),
    about("signed attestation", "/glossary#attestation"),
    about("Ed25519 signatures", "/glossary#signed-evidence"),
    about("sandbox testing of AI agents", "/glossary#sandbox"),
  ];
}

export function websiteLd(): Json {
  return {
    "@type": "WebSite",
    "@id": WEBSITE_ID,
    url: DOMAIN,
    name: BRAND,
    alternateName: ["Suncly AI", "suncly.com"],
    description: SHORT_DEFINITION,
    inLanguage: "en",
    publisher: { "@id": ORGANIZATION_ID },
  };
}

export function softwareLd(): Json {
  return {
    "@type": "SoftwareApplication",
    "@id": SOFTWARE_ID,
    name: BRAND,
    alternateName: "suncly CLI",
    applicationCategory: "DeveloperApplication",
    applicationSubCategory: "AI agent evaluation",
    operatingSystem: "Windows, macOS, Linux",
    softwareRequirements: "Python 3.12 or newer",
    softwareVersion: "0.1.0 (pilot)",
    description: DEFINITION,
    url: DOMAIN,
    downloadUrl: `${DOMAIN}/access`,
    installUrl: `${DOMAIN}/docs/getting-started`,
    softwareHelp: { "@type": "CreativeWork", url: `${DOMAIN}/docs` },
    featureList: [
      "Reads and hashes the A2A Agent Card",
      "Drafts one test case per declared skill example",
      "Human approval of the test plan, recorded with the approver's identity",
      "Repeated runs against a declared sandbox endpoint",
      "Deterministic verdicts: pass, fail, inconclusive",
      "Ed25519-signed evidence verifiable offline with suncly verify",
      "Every report states what was NOT tested",
      "Budget and execution controls per attestation",
    ],
    author: { "@id": ORGANIZATION_ID },
    publisher: { "@id": ORGANIZATION_ID },
    isAccessibleForFree: false,
    // No offers: no price is published. No aggregateRating: no reviews exist.
  };
}

export function webPageLd({
  path,
  name,
  description,
  type = "WebPage",
  datePublished = "2026-10-05",
  dateModified = "2026-10-05",
}: {
  path: string;
  name: string;
  description: string;
  type?: "WebPage" | "AboutPage" | "ContactPage" | "FAQPage" | "CollectionPage";
  datePublished?: string;
  dateModified?: string;
}): Json {
  const url = absoluteUrl(path);
  return {
    "@type": type,
    "@id": `${url}#webpage`,
    url,
    name: `${name} — ${BRAND}`,
    description,
    isPartOf: { "@id": WEBSITE_ID },
    about: { "@id": type === "AboutPage" || type === "ContactPage" ? ORGANIZATION_ID : SOFTWARE_ID },
    inLanguage: "en",
    datePublished,
    dateModified,
    primaryImageOfPage: { "@type": "ImageObject", url: `${DOMAIN}/og.png` },
  };
}

export function breadcrumbLd(items: Array<{ name: string; path: string }>): Json {
  return {
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: absoluteUrl(item.path),
    })),
  };
}

export function faqLd(items: ReadonlyArray<{ q: string; a: string }>): Json {
  return {
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };
}

export function howToLd({
  name,
  description,
  path,
  steps,
  totalTime,
}: {
  name: string;
  description: string;
  path: string;
  steps: Array<{ name: string; text: string; anchor?: string }>;
  totalTime?: string;
}): Json {
  return {
    "@type": "HowTo",
    name,
    description,
    totalTime,
    tool: [{ "@type": "HowToTool", name: "Python 3.12 or newer" }, { "@type": "HowToTool", name: "suncly CLI" }],
    step: steps.map((step, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: step.name,
      text: step.text,
      url: absoluteUrl(path) + (step.anchor ? `#${step.anchor}` : ""),
    })),
  };
}

export function techArticleLd({
  path,
  headline,
  description,
  datePublished = "2026-10-05",
  dateModified = "2026-10-05",
}: {
  path: string;
  headline: string;
  description: string;
  datePublished?: string;
  dateModified?: string;
}): Json {
  return {
    "@type": "TechArticle",
    "@id": `${absoluteUrl(path)}#article`,
    headline,
    description,
    url: absoluteUrl(path),
    mainEntityOfPage: absoluteUrl(path),
    author: { "@id": ORGANIZATION_ID },
    publisher: { "@id": ORGANIZATION_ID },
    datePublished,
    dateModified,
    inLanguage: "en",
    about: { "@id": SOFTWARE_ID },
    proficiencyLevel: "Expert",
  };
}

export function definedTermSetLd(terms: ReadonlyArray<{ term: string; definition: string; anchor: string }>): Json {
  return {
    "@type": "DefinedTermSet",
    "@id": `${DOMAIN}/glossary#terms`,
    name: "Suncly glossary: AI agent evaluation terms",
    url: `${DOMAIN}/glossary`,
    hasDefinedTerm: terms.map((t) => ({
      "@type": "DefinedTerm",
      "@id": `${DOMAIN}/glossary#${t.anchor}`,
      name: t.term,
      description: t.definition,
      inDefinedTermSet: `${DOMAIN}/glossary#terms`,
    })),
  };
}

/** Wrap one or more nodes in a @graph with the schema.org context. */
export function graph(...nodes: Json[]): Json {
  return { "@context": "https://schema.org", "@graph": nodes };
}
