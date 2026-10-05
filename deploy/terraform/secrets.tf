# Secrets are created here as containers; their values are added out of band
# (`gcloud secrets versions add`) by a person, never from Terraform state or a file.
locals {
  secrets = {
    "suncly-database-url-api"      = "DATABASE_URL for the API role"
    "suncly-database-url-worker"   = "DATABASE_URL for the worker role"
    "suncly-database-url-migrate"  = "DATABASE_URL for the migrate role"
    "suncly-stripe-secret-key"     = "Stripe secret key (test mode until the launch review)"
    "suncly-stripe-webhook-secret" = "Stripe webhook signing secret"
    "suncly-stripe-price-pilot"    = "Stripe price id for the pilot plan"
    "suncly-stripe-price-team"     = "Stripe price id for the team plan"
    "suncly-model-api-key"         = "Judge model provider key (worker only)"
    "suncly-signing-key"           = "Ed25519 signing key material (worker only)"
  }
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = local.secrets
  secret_id = each.key

  replication {
    auto {}
  }

  labels = {
    app = "suncly"
  }

  depends_on = [google_project_service.apis]
}

# Agent credentials live in secrets named suncly-agent-<registration id>; the registration
# references them by resource name. Only the runner identity may read them (iam.tf).
