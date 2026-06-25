# ─────────────────────────────────────────────────
#  variables.tf — Terraform Input Variables
# ─────────────────────────────────────────────────

variable "aws_region" {
  type        = string
  description = "AWS Region to deploy resources into"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Environment name (e.g., dev, staging, prod)"
  default     = "dev"
}

variable "drone_id" {
  type        = string
  description = "Unique identifier for the drone (IoT Thing Name)"
  default     = "DRONE-001"
}

variable "s3_bucket_name" {
  type        = string
  description = "Name of the S3 bucket for processed telemetry data. Must be globally unique."
  default     = "drone-telemetry-data-melvinjosec"
}

variable "kinesis_stream_name" {
  type        = string
  description = "Name of the Kinesis Data Stream for ingesting telemetry"
  default     = "DroneDataStream"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the Lambda function that processes streams to S3"
  default     = "DroneTelemetryProcessor"
}
