# Services the deployment needs. Nothing here creates a Stripe product, a live price or
# traffic: `terraform plan` describes the infrastructure; applying it is a separate,
# reviewed step (deploy/README.md).

locals {
  image       = "${var.region}-docker.pkg.dev/${var.project_id}/suncly/suncly@${var.image_digest}"
  bucket_name = "${var.project_id}-suncly-evidence"
  common_env = {
    SUNCLY_ENVIRONMENT     = var.environment
    SUNCLY_NETWORK_MODE    = "public"
    SUNCLY_ISSUER          = var.attestation_issuer
    SUNCLY_OIDC_ISSUER     = var.oidc_issuer
    SUNCLY_OIDC_AUDIENCE   = var.oidc_audience
    SUNCLY_OIDC_JWKS_URL   = var.oidc_jwks_url
    SUNCLY_EVIDENCE_BUCKET = local.bucket_name
  }
}

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "vpcaccess.googleapis.com",
    "iam.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "suncly"
  format        = "DOCKER"
  description   = "Suncly images; deployments reference them by digest only."

  docker_config {
    immutable_tags = true
  }

  depends_on = [google_project_service.apis]
}

# The worker's egress goes through a VPC connector so Cloud NAT gives it a fixed address
# customers can allow-list, and so the private-network deployment mode can be routed.
resource "google_compute_network" "egress" {
  name                    = "suncly-egress"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "egress" {
  name          = "suncly-egress"
  ip_cidr_range = "10.8.0.0/28"
  region        = var.region
  network       = google_compute_network.egress.id
}

resource "google_vpc_access_connector" "egress" {
  name   = "suncly-egress"
  region = var.region
  subnet {
    name = google_compute_subnetwork.egress.name
  }
  min_instances = 2
  max_instances = 3

  depends_on = [google_project_service.apis]
}

resource "google_compute_router" "egress" {
  name    = "suncly-egress"
  region  = var.region
  network = google_compute_network.egress.id
}

resource "google_compute_address" "egress" {
  name   = "suncly-egress"
  region = var.region
}

resource "google_compute_router_nat" "egress" {
  name                               = "suncly-egress"
  router                             = google_compute_router.egress.name
  region                             = var.region
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = [google_compute_address.egress.self_link]
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Egress firewall for the worker's network: the cloud metadata range and private ranges
# are refused by the Runner in code (domain/network.py) and again here, in the network.
resource "google_compute_firewall" "deny_private_egress" {
  name      = "suncly-worker-deny-private-egress"
  network   = google_compute_network.egress.name
  direction = "EGRESS"
  priority  = 900

  deny {
    protocol = "all"
  }

  destination_ranges = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "100.64.0.0/10",
  ]
}

resource "google_compute_firewall" "allow_public_https_egress" {
  name      = "suncly-worker-allow-https-egress"
  network   = google_compute_network.egress.name
  direction = "EGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["443", "8443"]
  }

  destination_ranges = ["0.0.0.0/0"]
}
