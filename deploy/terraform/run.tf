# Cloud Run resources (v2 API). The YAML manifests under deploy/cloudrun are the same
# shapes for `gcloud run ... replace`; Terraform is the source of truth for a project
# that is managed end to end.

locals {
  secret_env = {
    api = {
      DATABASE_URL          = "suncly-database-url-api"
      STRIPE_SECRET_KEY     = "suncly-stripe-secret-key"
      STRIPE_WEBHOOK_SECRET = "suncly-stripe-webhook-secret"
      STRIPE_PRICE_PILOT    = "suncly-stripe-price-pilot"
      STRIPE_PRICE_TEAM     = "suncly-stripe-price-team"
    }
    worker = {
      DATABASE_URL       = "suncly-database-url-worker"
      ANTHROPIC_API_KEY  = "suncly-model-api-key"
      SUNCLY_SIGNING_KEY = "suncly-signing-key"
    }
    dispatcher = {
      DATABASE_URL          = "suncly-database-url-api"
      STRIPE_SECRET_KEY     = "suncly-stripe-secret-key"
      STRIPE_WEBHOOK_SECRET = "suncly-stripe-webhook-secret"
    }
    migrate = {
      DATABASE_URL = "suncly-database-url-migrate"
    }
  }
}

resource "google_cloud_run_v2_service" "api" {
  name     = "suncly-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.api.email
    timeout                          = "60s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = var.environment == "production" ? 1 : 0
      max_instance_count = 10
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.db.connection_name]
      }
    }

    containers {
      image = local.image
      args  = ["api"]

      ports {
        container_port = 8080
      }

      resources {
        limits            = { cpu = "1", memory = "512Mi" }
        startup_cpu_boost = true
      }

      dynamic "env" {
        for_each = merge(local.common_env, {
          SUNCLY_PUBLIC_BASE_URL  = var.public_base_url
          SUNCLY_CORS_ORIGINS     = var.workspace_origin
          SUNCLY_BILLING_PROVIDER = "stripe"
        })
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = local.secret_env.api
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.secrets[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      startup_probe {
        http_get {
          path = "/v1/ready"
          port = 8080
        }
        initial_delay_seconds = 2
        period_seconds        = 3
        failure_threshold     = 20
      }

      liveness_probe {
        http_get {
          path = "/v1/health"
          port = 8080
        }
        period_seconds = 30
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_secret_manager_secret_iam_member.access]
}

resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "worker" {
  name     = "suncly-worker"
  location = var.region

  template {
    parallelism = var.worker_parallelism
    task_count  = var.worker_parallelism

    template {
      service_account = google_service_account.runner.email
      max_retries     = 0
      timeout         = "3300s"

      vpc_access {
        connector = google_vpc_access_connector.egress.id
        egress    = "ALL_TRAFFIC"
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.db.connection_name]
        }
      }

      containers {
        image = local.image
        args  = ["worker"]

        resources {
          limits = { cpu = "2", memory = "2Gi" }
        }

        dynamic "env" {
          for_each = merge(local.common_env, {
            SUNCLY_SECRET_MANAGER_PROJECT = var.project_id
            SUNCLY_MODEL_PROVIDER         = "anthropic"
            SUNCLY_MODEL                  = var.model_name
            SUNCLY_A2A_TCK_DIR            = "/opt/a2a-tck"
            SUNCLY_WORKER_LEASE_S         = "120"
            SUNCLY_WORKER_HEARTBEAT_S     = "20"
          })
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.secret_env.worker
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.secrets[env.value].secret_id
                version = "latest"
              }
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.access]
}

resource "google_cloud_run_v2_job" "dispatcher" {
  name     = "suncly-dispatcher"
  location = var.region

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = google_service_account.dispatcher.email
      max_retries     = 1
      timeout         = "300s"

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.db.connection_name]
        }
      }

      containers {
        image = local.image
        args  = ["tick"]

        dynamic "env" {
          for_each = merge(local.common_env, { SUNCLY_BILLING_PROVIDER = "stripe" })
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.secret_env.dispatcher
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.secrets[env.value].secret_id
                version = "latest"
              }
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.access]
}

resource "google_cloud_run_v2_job" "migrate" {
  name     = "suncly-migrate"
  location = var.region

  template {
    parallelism = 1
    task_count  = 1

    template {
      service_account = google_service_account.migrate.email
      max_retries     = 0
      timeout         = "600s"

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.db.connection_name]
        }
      }

      containers {
        image = local.image
        args  = ["migrate"]

        dynamic "env" {
          for_each = local.common_env
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.secret_env.migrate
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.secrets[env.value].secret_id
                version = "latest"
              }
            }
          }
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.access]
}
