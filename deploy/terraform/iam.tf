# Least privilege: one identity per process, each bound to the secrets it needs and nothing
# more. The API cannot read agent credentials or the signing key; the worker (the Runner
# boundary) cannot manage billing secrets; the dispatcher can run jobs but read no agent secret.

resource "google_service_account" "api" {
  account_id   = "suncly-api"
  display_name = "Suncly API"
}

resource "google_service_account" "runner" {
  account_id   = "suncly-runner"
  display_name = "Suncly worker (Runner boundary, Judge, signer)"
}

resource "google_service_account" "dispatcher" {
  account_id   = "suncly-dispatcher"
  display_name = "Suncly dispatcher / recovery"
}

resource "google_service_account" "migrate" {
  account_id   = "suncly-migrate"
  display_name = "Suncly migrations"
}

resource "google_service_account" "scheduler" {
  account_id   = "suncly-scheduler"
  display_name = "Cloud Scheduler invoker for Suncly jobs"
}

locals {
  secret_access = {
    api = [
      "suncly-database-url-api",
      "suncly-stripe-secret-key",
      "suncly-stripe-webhook-secret",
      "suncly-stripe-price-pilot",
      "suncly-stripe-price-team",
    ]
    runner = [
      "suncly-database-url-worker",
      "suncly-model-api-key",
      "suncly-signing-key",
    ]
    dispatcher = [
      "suncly-database-url-api",
      "suncly-stripe-secret-key",
      "suncly-stripe-webhook-secret",
    ]
    migrate = ["suncly-database-url-migrate"]
  }
  accounts = {
    api        = google_service_account.api.email
    runner     = google_service_account.runner.email
    dispatcher = google_service_account.dispatcher.email
    migrate    = google_service_account.migrate.email
  }
  secret_bindings = flatten([
    for who, names in local.secret_access : [
      for name in names : { who = who, secret = name }
    ]
  ])
}

resource "google_secret_manager_secret_iam_member" "access" {
  for_each  = { for b in local.secret_bindings : "${b.who}/${b.secret}" => b }
  secret_id = google_secret_manager_secret.secrets[each.value.secret].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.accounts[each.value.who]}"
}

# Agent credential secrets (suncly-agent-*) are readable by the runner only, through an IAM
# condition on the secret name prefix.
resource "google_project_iam_member" "runner_agent_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runner.email}"

  condition {
    title       = "agent-credentials-only"
    description = "Only secrets named suncly-agent-<registration id>."
    expression  = "resource.name.startsWith(\"projects/${var.project_id}/secrets/suncly-agent-\")"
  }
}

resource "google_project_iam_member" "cloudsql_clients" {
  for_each = local.accounts
  project  = var.project_id
  role     = "roles/cloudsql.client"
  member   = "serviceAccount:${each.value}"
}

resource "google_storage_bucket_iam_member" "evidence_reader_api" {
  bucket = google_storage_bucket.evidence.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.api.email}"
}

resource "google_storage_bucket_iam_member" "evidence_writer_runner" {
  for_each = toset(["roles/storage.objectCreator", "roles/storage.objectViewer"])
  bucket   = google_storage_bucket.evidence.name
  role     = each.key
  member   = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_project_iam_member" "log_writers" {
  for_each = local.accounts
  project  = var.project_id
  role     = "roles/logging.logWriter"
  member   = "serviceAccount:${each.value}"
}

resource "google_project_iam_member" "metric_writers" {
  for_each = local.accounts
  project  = var.project_id
  role     = "roles/monitoring.metricWriter"
  member   = "serviceAccount:${each.value}"
}

# The scheduler may start exactly the two jobs it schedules.
resource "google_cloud_run_v2_job_iam_member" "scheduler_runs_worker" {
  name     = google_cloud_run_v2_job.worker.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_runs_dispatcher" {
  name     = google_cloud_run_v2_job.dispatcher.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}
