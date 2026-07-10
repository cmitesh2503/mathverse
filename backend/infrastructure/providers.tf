terraform {
  required_version = ">= 0.14"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.8"
    }

    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
