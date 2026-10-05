terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # State lives in a bucket created out of band; set it with `terraform init -backend-config`.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
