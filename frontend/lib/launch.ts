/**
 * Launch state and founder inputs. One place for the facts that change the wording and
 * the status label of a section without changing whether the section exists.
 *
 * Every value here comes from the founder inputs block of the website brief (2026-10-05)
 * or from the repository. A blank means unknown; unknown facts never become public
 * claims. Changing a status later is a one-line edit here.
 */

export type RepositoryVisibility = "public" | "private";
export type LaunchState = "available" | "pilot" | "planned" | "not-live" | "live" | "not-open" | "open";

export const launch = {
  /** Checked on 2026-10-05: `git ls-remote` succeeds without credentials; GitHub reports visibility public. */
  repositoryVisibility: "public" as RepositoryVisibility,
  /** The CLI exists and is used with pilots. */
  cli: "pilot" as const,
  /** docs/ROADMAP.md stage 5; src/suncly/api.py is a placeholder. */
  httpApi: "planned" as "planned" | "pilot" | "live",
  /** Inputs block 4: usage-only billing, not live. */
  usageBilling: "not-live" as "not-live" | "live",
  /** Inputs block 3: the certification programme is not open. */
  certificationProgramme: "not-open" as "not-open" | "pilot" | "open",
  /** Inputs block 4: connecting costs nothing; the badge itself is free. */
  connectingFee: "none" as const,
  badgeFee: "none" as const,
  /** Inputs block 2: no registration exists. Anything but "registered" ships as ™. */
  trademark: "unregistered" as "unregistered" | "registered",
  /** Inputs block 3: no coding-agent integration in the repository. */
  codingAgentIntegration: "none" as "none" | string,
  /** Inputs block 3: "yes" only after a real run in that tool, recorded in VERIFICATION.md. */
  testedIn: {
    cursor: false,
    "claude-code": false,
    codex: false,
    omp: false,
    pi: false,
  } as Record<"cursor" | "claude-code" | "codex" | "omp" | "pi", boolean>,
  /** Inputs block 5: target markets. UK, CH and US sections exist only if named here. */
  targetMarkets: ["EU"] as const,
  /** Inputs block 5: vendors that gave written permission to show their logo. */
  logoPermissionsOnFile: [] as string[],
  /** Inputs block 8. */
  labName: "Suncly Lab",
  /** The legal pages lose their draft label only when the company facts exist and counsel has signed off. */
  legalPublished: false,
} as const;

/** ® only with a real registration (brief section 16). */
export const TRADEMARK_SYMBOL: "™" | "®" = launch.trademark === "registered" ? "®" : "™";

/** Where to install from: a public repository gets "Install", a private one "Request pilot access". */
export const PRIMARY_ACTION =
  launch.repositoryVisibility === "public"
    ? { label: "Install Suncly", short: "Install", href: "/#install" }
    : { label: "Request pilot access", short: "Request access", href: "/access#request" };

/**
 * Find Suncly. Supplied by the founder on 2026-10-05, replacing the blank inputs. A blank
 * link is not rendered. The Hacker News entry stays blank: the value supplied
 * ("Suncly.com") identifies no profile or submission, and no URL is invented.
 */
export interface SocialLink {
  id: "x" | "linkedin" | "github" | "hackernews" | "reddit";
  name: string;
  /** Accessible name, "Suncly on X". */
  label: string;
  url: string | null;
  /** Minimal text abbreviation shown while platform glyph usage is unconfirmed. */
  abbreviation: string;
}

export const social: readonly SocialLink[] = [
  { id: "x", name: "X", label: "Suncly on X", url: "https://x.com/Suncly_com", abbreviation: "X" },
  { id: "linkedin", name: "LinkedIn", label: "Suncly on LinkedIn", url: "https://www.linkedin.com/company/suncly/", abbreviation: "in" },
  { id: "github", name: "GitHub", label: "Suncly on GitHub", url: "https://github.com/Suncly-Tech", abbreviation: "gh" },
  { id: "hackernews", name: "Hacker News", label: "Suncly on Hacker News", url: null, abbreviation: "hn" },
  { id: "reddit", name: "Reddit", label: "Suncly on Reddit", url: "https://www.reddit.com/user/Suncly_com/", abbreviation: "r/" },
] as const;

export const socialLinks = social.filter((s): s is SocialLink & { url: string } => typeof s.url === "string" && s.url.length > 0);

/** Facts the founder has not supplied. Rendered as named blanks in drafts, never guessed. */
export const company = {
  name: "Suncly",
  legalEntityName: null as string | null,
  registryCode: null as string | null,
  registeredOffice: null as string | null,
  vatNumber: null as string | null,
  city: "Tallinn, Estonia",
  contactEmail: "team@suncly.com",
  privacyContactEmail: null as string | null,
  securityContactEmail: null as string | null,
  governingLawAndCourt: null as string | null,
  hosting: { provider: "Vercel", confirmed: false, regions: null as string | null },
  dns: { provider: "Cloudflare", confirmed: false },
  database: { provider: "Supabase", confirmed: false, regions: null as string | null },
  pilotFormEndpointAndStorage: null as string | null,
  analytics: "none" as const,
  subprocessors: null as string | null,
  retentionPeriods: null as string | null,
  repositoryLicence: null as string | null,
} as const;

export const pricing = {
  model: "usage-only" as const,
  billableUnit: null as string | null,
  priceAndCurrency: null as string | null,
  billingPeriodAndPaymentMethod: null as string | null,
  pilotTerms: null as string | null,
} as const;

/** Certification profile v0.1 is a proposal (REDESIGN_PLAN.md §9), not accepted criteria. */
export const certification = {
  criteriaAccepted: false,
  criteriaVersion: "0.1 (proposed)",
  validFor: null as string | null,
  retestTriggers: null as string | null,
  whoDecides: null as string | null,
  correctionsAndAppealsContact: null as string | null,
} as const;

/** Blanks that block the draft label coming off a legal page. */
export function missingLegalFacts(): string[] {
  const missing: string[] = [];
  if (!company.legalEntityName) missing.push("legal entity name");
  if (!company.registryCode) missing.push("registry code");
  if (!company.registeredOffice) missing.push("registered office");
  if (!company.vatNumber) missing.push("VAT number");
  if (!company.privacyContactEmail) missing.push("privacy contact address");
  if (!company.securityContactEmail) missing.push("security contact address");
  if (!company.governingLawAndCourt) missing.push("governing law and court");
  if (!company.pilotFormEndpointAndStorage) missing.push("pilot form endpoint and storage");
  if (!company.subprocessors) missing.push("sub-processors");
  if (!company.retentionPeriods) missing.push("retention periods");
  if (!company.repositoryLicence) missing.push("repository licence");
  return missing;
}
