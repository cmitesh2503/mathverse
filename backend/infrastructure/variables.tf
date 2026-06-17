variable "project_id" {
  description = "The ID of the GCP Project"
  type        = string
}

variable "firestore_project_id" {
  description = "The Firestore project ID where PDF chunks should be written"
  type        = string
  default     = ""
}

variable "region" {
  description = "The region where resources will be created"
  type        = string
}

variable "developer_user_email" {
  description = "Local developer Google account used for ADC-based backend runs."
  type        = string
  default     = ""
}

variable "processor_id" {
  description = "The ID of the Document AI processor to use for processing PDFs"
  type        = string
}

variable "processor_location" {
  description = "The location of the Document AI processor to use for processing PDFs"
  type        = string
} 