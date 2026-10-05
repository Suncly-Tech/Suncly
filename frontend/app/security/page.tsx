import type { Metadata } from "next";
import Link from "next/link";
import { SiteLayout, PageHeader, Section } from "@/components/site/SiteLayout";
import { FinalCta } from "@/components/site/FinalCta";
import { Notice } from "@/components/ui/Notice";
import { limitations, securityPage } from "@/lib/content";
import { JsonLd } from "@/components/site/JsonLd";
import { breadcrumbLd, graph, KEYWORDS, pageMeta, techArticleLd, webPageLd } from "@/lib/seo";

const description =
  "What Suncly accesses, where credentials are held and redacted, what reaches model providers (nothing), what evidence is stored, retention, deployment and evaluation limits.";

export const metadata: Metadata = pageMeta({
  title: "Security and data handling for AI agent evaluation",
  description,
  path: "/security",
  type: "article",
  keywords: [...KEYWORDS.evidence, "AI agent security review", "credential redaction", "sandbox testing AI agents", "self-hosted agent evaluation"],
});

const sections = [
  { id: "data", title: "What Suncly accesses" },
  { id: "credentials", title: "Where credentials are handled" },
  { id: "providers", title: "What goes to external model providers" },
  { id: "evidence", title: "What evidence is stored, and where" },
  { id: "retention", title: "Retention and deletion" },
  { id: "deployment", title: "Deployment options" },
  { id: "sandbox", title: "Sandbox requirements" },
  { id: "rules", title: "The non-negotiable rules" },
  { id: "limits", title: "Evaluation limitations" },
];

export default function SecurityPage() {
  return (
    <SiteLayout>
      <JsonLd
        data={graph(
          webPageLd({ path: "/security", name: "Security and data handling", description }),
          techArticleLd({ path: "/security", headline: securityPage.headline, description }),
          breadcrumbLd([{ name: "Suncly", path: "/" }, { name: "Security", path: "/security" }]),
        )}
      />
      <PageHeader eyebrow={securityPage.title} headline={securityPage.headline} intro={securityPage.intro} />
      <Section>
        <div className="grid gap-12 lg:grid-cols-[minmax(0,3fr)_minmax(0,9fr)] lg:gap-16">
          <nav aria-label="On this page" className="lg:sticky lg:top-28 lg:self-start">
            <p className="text-eyebrow text-ink-soft">On this page</p>
            <ol className="mt-4 flex flex-col gap-1 text-small">
              {sections.map((s) => (
                <li key={s.id}>
                  <Link href={`#${s.id}`} className="inline-block py-1 text-ink-soft hover:text-ink">
                    {s.title}
                  </Link>
                </li>
              ))}
            </ol>
          </nav>

          <article className="prose-site max-w-[760px]">
            <h2 id="data">What Suncly accesses</h2>
            <p>Suncly touches three things, and nothing else on your network:</p>
            <ul>
              <li>
                <strong>The Agent Card URL you give it.</strong> Fetched over https (plain http is accepted only for loopback addresses, where local sandboxes run), with a timeout and a size limit (1 MB by default). The body is kept byte for byte as <code>card_version.raw_json</code>.
              </li>
              <li>
                <strong>The agent endpoint named in the card.</strong> The Runner refuses any request whose host is not the target agent's host; one test enforces this in the one place that makes HTTP calls. It speaks A2A 1.0 over JSON-RPC: <code>SendMessage</code>, then <code>GetTask</code> until a terminal or interrupted state.
              </li>
              <li>
                <strong>One credential, if the sandbox needs one.</strong> The full value of the Authorization header, read from the environment variable <code>SUNCLY_AGENT_AUTHORIZATION</code>.
              </li>
            </ul>
            <p>Suncly never calls a registry, a gateway, an identity provider or Suncly's own servers: there are none in this version.</p>

            <h2 id="credentials">Where credentials are handled</h2>
            <p>
              The Runner is the only component that holds the agent credential. It runs as a separate process started for each run; the job it receives on stdin carries no credential (a test checks the job schema has no such field), and the process reads the variable itself. A test proves that exactly one source module names the variable.
            </p>
            <p>
              Before a transcript leaves the Runner it is redacted as data, over every string in every request and response: the credential value and its token part, the values of sensitive header keys (authorization, cookie, set-cookie, x-api-key, api-key, x-auth-token, proxy-authorization), documented token patterns (bearer tokens, JWTs, common provider key prefixes) and <code>key=value</code> secrets. Each rule that fired is named in the transcript's redaction summary. If redaction itself fails, the transcript is withheld and the run is not recorded. Nothing from the Runner's stderr is surfaced.
            </p>
            <p>Credentials never appear in command lines, request bodies, report files or logs. The bundled <code>leaky</code> mock agent, which echoes the header back, is part of the test suite to prove it.</p>

            <h2 id="providers">What goes to external model providers</h2>
            <p>
              <strong>Nothing, in this version.</strong> The test plan is drafted deterministically from the card's declared examples, and every verdict is deterministic. Suncly makes no call to any model provider and needs no model key.
            </p>
            <p>
              Later stages add a model-based drafter and a model-based judge (Layer 2). They are designed to use your own model keys, with the judge model pinned by version so that a verdict measures the agent, not drift in the judge. Which provider is yours to choose. Until those stages exist, every report lists semantic correctness under what was not tested.
            </p>

            <h2 id="evidence">What evidence is stored, and where</h2>
            <p>Everything is written on the machine that runs Suncly, under the Suncly home folder (<code>~/.suncly</code> by default, or <code>SUNCLY_HOME</code>) and the reports folder (<code>./suncly-reports</code> by default):</p>
            <ul>
              <li><code>store/</code>: the seven entity records (agent, card version, contract, test cases, attestation, runs, decisions) as files, or in Postgres when <code>DATABASE_URL</code> is set.</li>
              <li><code>transcripts/</code>: one evidence document per run: the redacted transcript and its judgement. Write-once; its SHA-256 is in the signed payload.</li>
              <li><code>keys/</code>: the deployment's Ed25519 signing key. The private key is never printed; the public key travels in every result.json.</li>
              <li><code>suncly-reports/&lt;attestation-id&gt;/</code>: <code>result.json</code>, the transcript files, <code>report.md</code> and a self-contained <code>report.html</code>.</li>
            </ul>
            <p>The store is append-only: run and decision records cannot be updated or deleted, and the Postgres migration enforces this with triggers. Corrections are new records.</p>

            <h2 id="retention">Retention and deletion</h2>
            <p>
              Suncly defines no retention period and has no delete operation, because the evidence store is append-only by design. Evidence stays where Suncly wrote it until you remove the files or drop the database. Because the software runs on your machine or in your network, you decide where the folders live, who can read them, and when they go.
            </p>
            <Notice tone="warn" title="Owner input pending">
              Retention and deletion commitments for a hosted offering, if one is introduced, are not defined and are not promised anywhere on this site.
            </Notice>

            <h2 id="deployment">Deployment options</h2>
            <ul>
              <li><strong>A developer machine.</strong> Python 3.12 or newer; <code>pip install -e .</code>; the file store.</li>
              <li><strong>A CI runner.</strong> The CLI with <code>--approve-as</code>, <code>--json</code> and documented exit codes; the report folder archived as a build artefact.</li>
              <li><strong>A server inside your network.</strong> The same CLI with <code>DATABASE_URL</code> pointing at your Postgres (any PostgreSQL 13 or newer; the schema is applied with <code>suncly db migrate</code>). Transcripts stay on that machine's disk until an object-storage adapter exists.</li>
            </ul>
            <p>
              <strong>A hosted deployment.</strong> The API, a worker in the trusted Runner boundary and a dispatcher, configured for Google Cloud Run under <code>deploy/</code>: separate identities per process, secrets by reference only, the Runner's egress restricted to public https hosts, evidence in a versioned bucket. This configuration is validated in CI and has not been deployed; this website sends no data to Suncly and creates no account.
            </p>

            <h2 id="sandbox">Sandbox requirements</h2>
            <p>
              Nothing runs unless the caller declares the endpoint a sandbox or dry-run endpoint (<code>--sandbox</code>). The Runner refuses undeclared targets a second time. Tests send the card's own example inputs, and later probes will deliberately send injected instructions and failure conditions; against production that could book, pay or delete something real. Suncly cannot verify that an endpoint is a sandbox; the declaration is yours and the report records it as a declaration.
            </p>

            <h2 id="rules">The non-negotiable rules</h2>
            <p>Seven decision records the system is built around. Each one has a test named after it.</p>
            <ol>
              <li><strong>Idempotent runs.</strong> Every run has a deterministic key; retries never double count.</li>
              <li><strong>Evidence is immutable.</strong> Records are never edited; corrections are new records.</li>
              <li><strong>Secrets never leave the Runner.</strong> Transcripts are redacted before storage.</li>
              <li><strong>The judge model is pinned.</strong> A new judge model is a configuration change, not drift (applies once Layer 2 exists).</li>
              <li><strong>Budget caps live in the Orchestrator.</strong> The component that starts runs is the one that stops them.</li>
              <li><strong>Tests hit a sandbox or dry-run endpoint.</strong> Never production.</li>
              <li><strong>Reports state what was NOT tested.</strong> No score hides the gaps.</li>
            </ol>

            <h2 id="limits">Evaluation limitations</h2>
            <ul>
              {limitations.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p>
              The full architecture, with each component's “must never” list and failure behaviour, is in the repository documents listed on the <Link href="/docs">documentation page</Link>.
            </p>
          </article>
        </div>
      </Section>
      <FinalCta />
    </SiteLayout>
  );
}
