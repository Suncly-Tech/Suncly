# Cloud Scheduler starts the two jobs through the Cloud Run Jobs API with the scheduler's
# own identity. The worker trigger is a safety net: an execution that is still running
# makes the next trigger a no-op (the API returns 409, retried later), so a long queue is
# served by the running tasks and an empty queue costs nothing.

locals {
  run_jobs_api = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs"
}

resource "google_cloud_scheduler_job" "dispatcher" {
  name        = "suncly-dispatcher-tick"
  description = "Recover expired leases, enqueue due re-evaluations, relay the outbox, report usage."
  schedule    = var.dispatcher_schedule
  time_zone   = "Etc/UTC"
  region      = var.region

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "${local.run_jobs_api}/${google_cloud_run_v2_job.dispatcher.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "worker" {
  name        = "suncly-worker-start"
  description = "Start a worker execution when none is running."
  schedule    = var.worker_schedule
  time_zone   = "Etc/UTC"
  region      = var.region

  retry_config {
    retry_count = 0
  }

  http_target {
    http_method = "POST"
    uri         = "${local.run_jobs_api}/${google_cloud_run_v2_job.worker.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler.email
    }
  }

  depends_on = [google_project_service.apis]
}
