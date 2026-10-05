variable "project_id" {
  description = "The Google Cloud project that hosts Suncly."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, Cloud SQL, Artifact Registry and the evidence bucket."
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Deployment environment; only `production` and `staging` are deployable."
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "environment must be production or staging; development and test never run on Cloud Run."
  }
}

variable "image_digest" {
  description = "The digest (sha256:...) of the suncly image in Artifact Registry. Tags are refused."
  type        = string

  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "image_digest must be the full sha256 digest; a tag is not an immutable reference."
  }
}

variable "oidc_issuer" {
  description = "The OpenID Connect issuer whose tokens the API accepts."
  type        = string
  default     = "https://accounts.google.com"
}

variable "oidc_audience" {
  description = "The audience (client id) the API requires in every token."
  type        = string
}

variable "oidc_jwks_url" {
  description = "The issuer's JWKS endpoint."
  type        = string
  default     = "https://www.googleapis.com/oauth2/v3/certs"
}

variable "attestation_issuer" {
  description = "The issuer name bound into every signed payload (SUNCLY_ISSUER)."
  type        = string
}

variable "public_base_url" {
  description = "The public URL of the API, for links and the workspace's CORS origin."
  type        = string
}

variable "workspace_origin" {
  description = "The origin of the hosted workspace (CORS)."
  type        = string
}

variable "model_name" {
  description = "The pinned judge model. Usage is paid; the key comes from Secret Manager."
  type        = string
  default     = "claude-opus-5-5"
}

variable "worker_parallelism" {
  description = "Worker tasks per execution; each claims jobs under the tenant limits."
  type        = number
  default     = 3
}

variable "worker_schedule" {
  description = "Cron (Cloud Scheduler) that starts a worker execution when none is running."
  type        = string
  default     = "*/5 * * * *"
}

variable "dispatcher_schedule" {
  description = "Cron for the dispatcher / recovery pass."
  type        = string
  default     = "* * * * *"
}

variable "evidence_retention_days" {
  description = "Days before evidence objects become deletable (bucket retention policy)."
  type        = number
  default     = 400
}

variable "alert_email" {
  description = "Where job failure alerts go."
  type        = string
}
