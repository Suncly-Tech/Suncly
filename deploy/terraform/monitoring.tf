# Logs are structured JSON on stdout (Cloud Run collects them). Two signals get alerts:
# failed job attempts and recovered leases, both written by the worker and the dispatcher.

resource "google_logging_metric" "job_failures" {
  name        = "suncly/job_failures"
  description = "Attestation job attempts that failed (worker log lines)."
  filter      = "resource.type=\"cloud_run_job\" AND jsonPayload.event=\"attempt_failed\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

resource "google_logging_metric" "recovered_leases" {
  name        = "suncly/recovered_leases"
  description = "Jobs whose lease expired and were requeued (a worker died or stalled)."
  filter      = "resource.type=\"cloud_run_job\" AND jsonPayload.event=\"lease_recovered\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "Suncly operators"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_alert_policy" "job_failures" {
  display_name = "Suncly: attestation jobs failing"
  combiner     = "OR"

  conditions {
    display_name = "more than 3 failed attempts in 10 minutes"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.job_failures.name}\" AND resource.type=\"cloud_run_job\""
      comparison      = "COMPARISON_GT"
      threshold_value = 3
      duration        = "600s"

      aggregations {
        alignment_period   = "600s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

resource "google_monitoring_alert_policy" "api_errors" {
  display_name = "Suncly: API 5xx responses"
  combiner     = "OR"

  conditions {
    display_name = "5xx responses in 5 minutes"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"${google_cloud_run_v2_service.api.name}\" AND metric.label.response_code_class=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 5
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}
