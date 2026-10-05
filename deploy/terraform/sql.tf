resource "random_password" "db" {
  for_each = toset(["api", "worker", "migrate"])
  length   = 32
  special  = false
}

resource "google_sql_database_instance" "db" {
  name             = "suncly-db"
  database_version = "POSTGRES_17"
  region           = var.region

  settings {
    tier              = var.environment == "production" ? "db-custom-2-7680" : "db-g1-small"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
    }

    ip_configuration {
      ipv4_enabled = false
      # Cloud Run reaches the instance through the Cloud SQL connector annotation; no
      # public address, no authorized networks.
      private_network = google_compute_network.egress.id
    }

    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  deletion_protection = var.environment == "production"

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "suncly" {
  name     = "suncly"
  instance = google_sql_database_instance.db.name
}

# Three database roles with different rights (db/README.md): migrate owns the schemas, the
# API reads and writes application rows, the worker additionally writes evidence rows.
resource "google_sql_user" "roles" {
  for_each = random_password.db
  name     = "suncly_${each.key}"
  instance = google_sql_database_instance.db.name
  password = each.value.result
}
