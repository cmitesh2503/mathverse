resource "google_project_service" "requited_apis" {
  for_each = toset([
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
  ])
  service = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "curriculum_bucket" {
  name          = "mathverse-curriculum-pdfs-${var.project_id}"
  location      = var.region
  uniform_bucket_level_access = true
  force_destroy = true
}

resource "google_storage_bucket" "function_source_bucket" {
  name          = "mathverse-function-source-${var.project_id}"
  location      = var.region
  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "function_zip" {
  name          = "ingestion-agent-${data.archive_file.function_zip.output_md5}.zip"
  bucket        = google_storage_bucket.function_source_bucket.name
  source        = data.archive_file.function_zip.output_path
}

resource "google_service_account" "ingestion_sa" {
  account_id   = "rag-ingestion-agent"
  display_name = "RAG PDF Ingestion Cloud Function SA"
}

resource "google_storage_bucket_iam_member" "read_pdfs" {
  bucket  = google_storage_bucket.curriculum_bucket.name
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "firestore_writer" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}
# Give the service account permission to trigger the Cloud Run function
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}
resource "google_project_iam_member" "event_receiver" {
  project     = var.project_id
  role        = "roles/eventarc.eventReceiver"
  member      = "serviceAccount:${google_service_account.ingestion_sa.email}"
}
# 1. Look up the hidden Cloud Storage Service Account
data "google_storage_project_service_account" "gcs_account" {
  project = var.project_id
}

# 2. Give it permission to tell Eventarc when a file is dropped
resource "google_project_iam_member" "gcs_pubsub_publishing" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}
resource "google_cloudfunctions2_function" "pdf_ingestion_agent" {
  name        = "mathverse-pdf-indexer"
  location      = var.region
  project     = var.project_id
  description = "Triggered by new PDFs. Parses, embeds, and writes to Firestore."
  # Tell Terraform to wait for the IAM permission to finish first
  depends_on  = [google_project_iam_member.gcs_pubsub_publishing]

build_config {
    runtime = "python311"
    entry_point = "process_new_pdf"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.function_zip.name
      }
    }
}

service_config {
    timeout_seconds = 540
    max_instance_count = 5
    available_memory = "2G"
    service_account_email = google_service_account.ingestion_sa.email

    environment_variables = {
        PROJECT_ID    = var.project_id
        FIRESTORE_COL = "pdf_chunks"
        REGION        = var.region
        EMBEDDING_MODEL = "text-embedding-004"
    }
}

event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"
    retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = google_service_account.ingestion_sa.email
    event_filters {
        attribute = "bucket"
         value     = google_storage_bucket.curriculum_bucket.name
        }
    }
}

data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function"
  output_path = "${path.module}/function_source.zip"
}
    