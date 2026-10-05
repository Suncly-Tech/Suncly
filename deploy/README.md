# Deployment

Everything under `deploy/` is **configured, validated, and not deployed**. No
project, instance, bucket, secret, Stripe object or DNS record was created while
writing it; applying it is a reviewed, separate step. The checks that can run
without cloud credentials run in CI (`python deploy/validate.py`).

| Piece | File | What it does |
|---|---|---|
| Image | `Dockerfile`, `entrypoint.sh` | One image; `api`, `worker`, `tick`, `migrate` select the process. |
| Pinned tools | `tools/promptfoo/package.json`, Dockerfile `A2A_TCK_REF` | Promptfoo 0.123.1 (MIT), A2A TCK tag `1.0.0.alpha2` at commit `29063fe9` (Apache-2.0). |
| Cloud Run manifests | `cloudrun/*.yaml` | API service, worker job, dispatcher job, migrate job, for `gcloud run ... replace`. |
| Terraform | `terraform/*.tf` | Project services, Artifact Registry, Cloud SQL (Postgres 17, private IP), evidence bucket, secrets, identities and bindings, Cloud Run, Scheduler, egress NAT and firewall, alerts. |
| Local development | `../compose.yaml` | Postgres, API, worker, dispatcher, with local authentication and the fake billing provider. |
| Validation | `validate.py` | Manifest rules, compose shape, `terraform fmt`/`validate`, `docker build --check`. |

## Processes and identities

| Process | Cloud Run | Identity | Secrets it can read | Cannot read |
|---|---|---|---|---|
| API | service `suncly-api` | `suncly-api` | database (API role), Stripe key, webhook secret, price ids | signing key, model key, any agent credential |
| Worker (Runner boundary, Judge, signer, ledger) | job `suncly-worker` | `suncly-runner` | database (worker role), model key, signing key, `suncly-agent-*` credentials | Stripe secrets |
| Dispatcher / recovery | job `suncly-dispatcher` | `suncly-dispatcher` | database (API role), Stripe key (meter reporting), webhook secret | signing key, model key, agent credentials |
| Migrations | job `suncly-migrate` | `suncly-migrate` | database (migrate role) | everything else |
| Scheduler | Cloud Scheduler | `suncly-scheduler` | nothing; may start the worker and dispatcher jobs | — |

The agent credential for a registration is a Secret Manager secret named
`suncly-agent-<registration id>`; the registration stores the resource name
only (`CredentialReference`). Inside the worker, the Runner subprocess
receives it on stdin in a `RunEnvelope` and nothing else from the worker's
environment (`adapters/scoped_executor.py`); an external tool receives it in
the Runner's one variable through `adapters/external/process.py`. The judge
holds the model key and no agent credential; the API process holds neither.

The signing key is one Secret Manager secret whose versions are keys; the
worker reads the latest version into `SUNCLY_SIGNING_KEY`
(`adapters/secret_keys.py`). `suncly trust rotate` adds a version and
registers the new public key; `suncly trust revoke` marks a key revoked in
the registry the API serves at `GET /v1/keys`. A hardware-backed key (Cloud
KMS) is deferred: the signing interface takes any `Signer`, and the
verification side already separates cryptographic validity from issuer trust.

## Egress controls for the hosted Runner

In code, the Runner refuses every target that is not a public `https` host
on 443 or 8443, re-checks every resolved address at connection time and on
every redirect, and bounds sizes, redirects and deadlines
(`domain/network.py`, `runner/http_transport.py`). The deployment adds:

- a VPC connector with Cloud NAT and a fixed egress address customers can
  allow-list (`terraform/main.tf`);
- an egress firewall on that network denying private, link-local and
  carrier-grade ranges, and allowing TCP 443 and 8443 only;
- the private-network mode (`SUNCLY_NETWORK_MODE=private_network`) is a
  separate deployment on a separate network, never a per-agent option; it is
  not part of this configuration.

## Rollout and rollback

1. Build and push the image; record its digest. The Artifact Registry
   repository has immutable tags, and the manifests and Terraform refuse
   anything but `@sha256:` references.
2. Run the migrate job (`suncly db migrate`): migrations are applied in
   order and recognised from the catalog; an already applied file is
   skipped. The three migrations in this repository are additive. Migration
   0002 enables row level security on the core tables with no policies, so
   every process connects as the table owner until policies exist; the
   per-process database secrets all carry that role's URL for now.
3. Deploy the API revision; the startup probe waits for `/v1/ready` (the
   database answers). Traffic moves to the new revision only when it is
   ready.
4. Deploy the worker and dispatcher jobs. A running worker execution
   finishes its leased jobs under the old image; a job it does not finish
   is recovered by the reaper and re-run by the new image under the same
   logical id (no duplicate evidence, no duplicate ledger line).
5. Rollback: `gcloud run services update-traffic suncly-api --to-revisions
   <previous>=100` and redeploy the jobs with the previous digest. The
   migrations are not rolled back; they are additive and the previous image
   runs against them.

## Validation without applying

```
python deploy/validate.py
```

- Manifest rules always run: digest-pinned image, dedicated service
  account, secrets only by reference, no local authentication or local
  network mode, the worker never retries at the platform level, and the
  API/worker secret boundaries above.
- `terraform fmt -check` runs wherever Terraform is installed. `terraform
  validate` needs the provider registry; where the registry is not reachable
  the validator reports the step as **skipped**, never as passed. In GitHub
  Actions (`.github/workflows/ci.yml`, job `deploy-config`) it runs.
- `docker build --check` runs where a BuildKit daemon is usable and is
  skipped otherwise. The build needs no privileged daemon.

What has **not** been exercised: a real Cloud Run deployment, Cloud SQL
connectivity, the Secret Manager bindings, the Scheduler triggers and the
alert policies. They are written from the provider documentation and
validated syntactically only.

## Local development

```
docker compose up --build
suncly auth local-token --subject dev-1 --email dev@example.test
```

`compose.yaml` runs Postgres, the migrate job, the API on
`http://localhost:8080` with `SUNCLY_LOCAL_AUTH_ENABLED=1`, the worker in
local network mode (loopback sandboxes allowed), and a dispatcher loop. The
frontend runs separately with `npm --prefix frontend run dev` and connects to
the API from its Settings page. The local token verifier refuses to start in
a production environment, and `SUNCLY_ENVIRONMENT=production` refuses the
local network mode, so none of these settings can be promoted by mistake.
