resource "google_project_service" "requited_apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "aiplatform.googleapis.com",
    "eventarc.googleapis.com",
    "firestore.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "documentai.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "curriculum_bucket" {
  name                        = "mathverse-curriculum-pdfs-${var.project_id}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

resource "google_storage_bucket" "jee_assets" {
  name                        = "${var.project_id}-jee-assets"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  versioning {
    enabled = true
  }

  depends_on = [
    google_project_service.requited_apis["documentai.googleapis.com"]
  ]

}

resource "google_storage_bucket" "function_source_bucket" {
  name                        = "mathverse-function-source-${var.project_id}"
  location                    = var.region
  uniform_bucket_level_access = true
}

resource "google_firestore_index" "pdf_chunks_vector" {
  project     = local.firestore_project_id
  database    = "(default)"
  collection  = "pdf_chunks"
  query_scope = "COLLECTION"

  fields {
    field_path = "metadata.chapter"
    order      = "ASCENDING"
  }

  fields {
    field_path = "metadata.grade"
    order      = "ASCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  fields {
    field_path = "embedding"
    vector_config {
      dimension = 768
      flat {}
    }
  }

  depends_on = [
    google_project_service.requited_apis["firestore.googleapis.com"],
  ]
}

resource "google_storage_bucket_object" "function_zip" {
  name   = "ingestion-agent-${data.archive_file.function_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name
  source = data.archive_file.function_zip.output_path
}

data "archive_file" "jee_ocr_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function_jee_ocr"
  output_path = "${path.module}/jee_ocr.zip"
}

resource "google_storage_bucket_object" "jee_extractor_zip" {
  name   = "jee-question-extractor-${data.archive_file.jee_questions_extractor_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name
  source = data.archive_file.jee_questions_extractor_zip.output_path
}

data "archive_file" "jee_questions_extractor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function_jee_extractor"
  output_path = "${path.module}/jee_question_extractor.zip"
}
resource "google_storage_bucket_object" "jee_ocr_zip" {
  name   = "jee-ocr-${data.archive_file.jee_ocr_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name
  source = data.archive_file.jee_ocr_zip.output_path
}

resource "google_storage_bucket_object" "jee_answers_extractor_zip" {
  name   = "jee-answer-extractor-${data.archive_file.jee_answers_extractor_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name
  source = data.archive_file.jee_answers_extractor_zip.output_path
}
data "archive_file" "jee_answers_extractor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function_answer_extractor"
  output_path = "${path.module}/jee_answer_extractor.zip"
}

resource "google_storage_bucket_object" "jee_solution_extractor_zip" {

  name = "jee-solution-extractor-${data.archive_file.jee_solution_extractor_zip.output_md5}.zip"

  bucket = google_storage_bucket.function_source_bucket.name

  source = data.archive_file.jee_solution_extractor_zip.output_path
}
data "archive_file" "jee_solution_extractor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function_solution_extractor"
  output_path = "${path.module}/jee_solution_extractor.zip"
}

resource "google_storage_bucket_object" "metadata_extractor_zip" {

  name = "metadata-extractor-${data.archive_file.metadata_extractor_zip.output_md5}.zip"

  bucket = google_storage_bucket.function_source_bucket.name

  source = data.archive_file.metadata_extractor_zip.output_path
}
data "archive_file" "metadata_extractor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function_metadata_extractor"
  output_path = "${path.module}/metadata_extractor.zip"
}


resource "google_project_iam_member" "docai_viewer" {
  project = var.project_id
  role    = "roles/documentai.viewer"
  member  = "serviceAccount:${google_service_account.jee_processor.email}"
}

resource "google_service_account" "ingestion_sa" {
  account_id   = "rag-ingestion-agent"
  display_name = "RAG PDF Ingestion Cloud Function SA"
}

resource "google_service_account" "jee_processor" {
  account_id   = "jee-processor"
  display_name = "JEE JEE Processor SA"

  depends_on = [
    google_project_service.requited_apis
  ]

}

locals {
  firestore_project_id      = var.firestore_project_id != "" ? var.firestore_project_id : var.project_id
  developer_user_email      = trimspace(var.developer_user_email)
  developer_user_member     = "user:${local.developer_user_email}"
  developer_user_configured = local.developer_user_email != ""
  app_access_projects       = toset([var.project_id, local.firestore_project_id])
}

resource "google_storage_bucket_iam_member" "read_pdfs" {
  bucket = google_storage_bucket.curriculum_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_storage_bucket_iam_member" "read_pdf_bucket_metadata" {
  bucket = google_storage_bucket.curriculum_bucket.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "firestore_writer" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.jee_processor.email}"
}

resource "google_project_iam_member" "docai_user" {
  project = var.project_id
  role    = "roles/documentai.apiUser"
  member  = "serviceAccount:${google_service_account.jee_processor.email}"
}

resource "google_project_iam_member" "storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.jee_processor.email}"
}

resource "google_project_iam_member" "service_usage_consumer" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "developer_firestore_user" {
  count   = local.developer_user_configured ? 1 : 0
  project = local.firestore_project_id
  role    = "roles/datastore.user"
  member  = local.developer_user_member
}

resource "google_project_iam_member" "developer_ai_user" {
  for_each = local.developer_user_configured ? local.app_access_projects : toset([])
  project  = each.value
  role     = "roles/aiplatform.user"
  member   = local.developer_user_member
}

resource "google_project_iam_member" "developer_service_usage_consumer" {
  for_each = local.developer_user_configured ? local.app_access_projects : toset([])
  project  = each.value
  role     = "roles/serviceusage.serviceUsageConsumer"
  member   = local.developer_user_member
}

# Give the service account permission to trigger the Cloud Run function
resource "google_project_iam_member" "run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}
resource "google_project_iam_member" "event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
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
  location    = var.region
  project     = var.project_id
  description = "Triggered by new PDFs. Parses, embeds, and writes to Firestore."
  # The function create API can race ahead of freshly-enabled services and IAM bindings.
  depends_on = [
    google_project_service.requited_apis,
    google_project_iam_member.gcs_pubsub_publishing,
    google_project_iam_member.firestore_writer,
    google_project_iam_member.service_usage_consumer,
    google_project_iam_member.run_invoker,
    google_project_iam_member.event_receiver,
    google_storage_bucket_iam_member.read_pdfs,
    google_storage_bucket_iam_member.read_pdf_bucket_metadata,

  ]

  build_config {
    runtime     = "python311"
    entry_point = "process_new_pdf"
    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.function_zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = 540
    max_instance_count    = 5
    available_memory      = "2G"
    service_account_email = google_service_account.ingestion_sa.email

    environment_variables = {
      PROJECT_ID           = local.firestore_project_id
      FIRESTORE_PROJECT_ID = local.firestore_project_id
      FIRESTORE_COL        = "pdf_chunks"
      REGION               = var.region
      EMBEDDING_MODEL      = "text-embedding-004"
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_DO_NOT_RETRY"
    service_account_email = google_service_account.ingestion_sa.email
    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.curriculum_bucket.name
    }
  }
}

resource "google_cloudfunctions2_function" "jee_pdf_ocr" {

  name     = "jee-pdf-ocr"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python311"
    entry_point = "process_pdf"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.jee_ocr_zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = 540
    available_memory      = "2G"
    max_instance_count    = 5
    service_account_email = google_service_account.jee_processor.email

    environment_variables = {
      PROJECT_ID         = var.project_id
      PROCESSOR_ID       = var.processor_id
      PROCESSOR_LOCATION = var.processor_location
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.jee_assets.name
    }
  }

  depends_on = [
    google_project_service.requited_apis,
    google_project_iam_member.docai_user,
    google_project_iam_member.firestore_user,
    google_project_iam_member.storage_object_admin,
  ]
}

resource "google_cloudfunctions2_function" "jee_question_extractor" {

  name     = "jee-question-extractor"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python311"
    entry_point = "process_ocr_json"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.jee_extractor_zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = 540
    available_memory      = "2G"
    max_instance_count    = 5
    service_account_email = google_service_account.jee_processor.email

    environment_variables = {
      PROJECT_ID = var.project_id
    }

  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.jee_assets.name
    }
  }

  depends_on = [
    google_project_service.requited_apis,
    google_project_iam_member.firestore_user,
    google_project_iam_member.storage_object_admin,
  ]
}

resource "google_cloudfunctions2_function" "jee_answer_extractor" {

  name     = "jee-answer-extractor"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python311"
    entry_point = "process_answers"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.jee_answers_extractor_zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = 540
    available_memory      = "2G"
    max_instance_count    = 5
    service_account_email = google_service_account.jee_processor.email

    environment_variables = {
      PROJECT_ID = var.project_id
    }

  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.jee_assets.name
    }
  }

  depends_on = [
    google_project_service.requited_apis,
    google_project_iam_member.firestore_user,
    google_project_iam_member.storage_object_admin,
  ]


}

resource "google_cloudfunctions2_function" "jee_solution_extractor" {

  name     = "jee-solution-extractor"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python311"
    entry_point = "process_solutions"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.jee_solution_extractor_zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = 540
    available_memory      = "2G"
    max_instance_count    = 5
    service_account_email = google_service_account.jee_processor.email

    environment_variables = {
      PROJECT_ID = var.project_id
    }

  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.jee_assets.name
    }
  }

  depends_on = [
    google_project_service.requited_apis,
    google_project_iam_member.firestore_user,
    google_project_iam_member.storage_object_admin,
  ]


}

resource "google_cloudfunctions2_function" "jee_metadata_extractor" {

  name     = "jee-metadata-extractor"
  location = var.region
  project  = var.project_id

  build_config {
    runtime     = "python311"
    entry_point = "process_metadata"

    source {
      storage_source {
        bucket = google_storage_bucket.function_source_bucket.name
        object = google_storage_bucket_object.metadata_extractor_zip.name
      }
    }
  }

  service_config {
    timeout_seconds       = 540
    available_memory      = "2G"
    max_instance_count    = 5
    service_account_email = google_service_account.jee_processor.email

    environment_variables = {
      PROJECT_ID = var.project_id
    }

  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.storage.object.v1.finalized"

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.jee_assets.name
    }
  }

  depends_on = [
    google_project_service.requited_apis,
    google_project_iam_member.firestore_user,
    google_project_iam_member.storage_object_admin,
  ]


}

resource "google_project_iam_member" "firestore_writer_cross_project" {
  count   = local.firestore_project_id != var.project_id ? 1 : 0
  project = local.firestore_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "ai_user_cross_project" {
  count   = local.firestore_project_id != var.project_id ? 1 : 0
  project = local.firestore_project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

resource "google_project_iam_member" "service_usage_consumer_cross_project" {
  count   = local.firestore_project_id != var.project_id ? 1 : 0
  project = local.firestore_project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.ingestion_sa.email}"
}

data "archive_file" "function_zip" {
  type        = "zip"
  source_dir  = "${path.module}/cloud_function"
  output_path = "${path.module}/function_source.zip"
}
