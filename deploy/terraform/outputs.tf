output "api_url" {
  description = "The Cloud Run URL of the API; map the public hostname to it."
  value       = google_cloud_run_v2_service.api.uri
}

output "egress_address" {
  description = "The fixed address the worker's egress uses; customers may allow-list it."
  value       = google_compute_address.egress.address
}

output "evidence_bucket" {
  value = google_storage_bucket.evidence.name
}

output "database_connection_name" {
  value = google_sql_database_instance.db.connection_name
}

output "service_accounts" {
  value = local.accounts
}
