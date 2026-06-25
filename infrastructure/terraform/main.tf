# ─────────────────────────────────────────────────
#  main.tf — Terraform Infrastructure Provisioning
# ─────────────────────────────────────────────────

terraform {
  required_version = ">= 1.2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── S3 Bucket (Data Lake Storage) ────────────────
resource "aws_s3_bucket" "telemetry" {
  bucket        = var.s3_bucket_name
  force_destroy = true # Allows clean tear-down of the environment

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Drone-Telemetry"
  }
}

resource "aws_s3_bucket_public_access_block" "telemetry_privacy" {
  bucket = aws_s3_bucket.telemetry.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── Kinesis Data Stream (Ingestion Stream) ───────
resource "aws_kinesis_stream" "telemetry_stream" {
  name             = var.kinesis_stream_name
  shard_count      = var.environment == "prod" ? 2 : 1 # Shard count for dev/prod
  retention_period = 24

  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Drone-Telemetry"
  }
}

# ── IAM Role & Policies for Lambda ───────────────
resource "aws_iam_role" "lambda_role" {
  name = "drone-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# S3 Policy for Lambda
resource "aws_iam_policy" "lambda_s3_policy" {
  name        = "drone-lambda-s3-policy"
  description = "Allows Lambda to write processed drone telemetry to S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.telemetry.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_s3_policy.arn
}

# Kinesis Execution Policy for Lambda (Read and log)
resource "aws_iam_role_policy_attachment" "lambda_kinesis" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole"
}

# Basic Execution Policy for Lambda (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ── AWS Lambda (Processor Function) ──────────────
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../../lambda/lambda_function.py"
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "telemetry_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  function_name    = var.lambda_function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.telemetry.id
    }
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Kinesis Trigger
resource "aws_lambda_event_source_mapping" "kinesis_trigger" {
  event_source_arn  = aws_kinesis_stream.telemetry_stream.arn
  function_name     = aws_lambda_function.telemetry_processor.function_name
  starting_position = "LATEST"
  batch_size        = 10
}

# ── AWS IoT Core (Device Connection) ─────────────
resource "aws_iot_thing" "drone_thing" {
  name = var.drone_id
}

# IoT Policy
resource "aws_iot_policy" "drone_policy" {
  name = "DroneDevicePolicy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:Connect", "iot:Publish", "iot:Subscribe", "iot:Receive"]
        Resource = "*"
      }
    ]
  })
}

# IAM Role for IoT Core Routing Rule
resource "aws_iam_role" "iot_kinesis_role" {
  name = "drone-iot-kinesis-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "iot.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# IoT Kinesis Access Policy
resource "aws_iam_policy" "iot_kinesis_policy" {
  name        = "drone-iot-kinesis-policy"
  description = "Allows IoT Core to publish to Kinesis Stream"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords"
        ]
        Resource = aws_kinesis_stream.telemetry_stream.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "iot_kinesis" {
  role       = aws_iam_role.iot_kinesis_role.name
  policy_arn = aws_iam_policy.iot_kinesis_policy.arn
}

# IoT Rule (Ingest MQTT -> Stream Kinesis)
resource "aws_iot_topic_rule" "drone_to_kinesis" {
  name        = "DroneToKinesis"
  description = "Route telemetry data from drones to Kinesis Stream"
  enabled     = true
  sql         = "SELECT * FROM 'drones/telemetry'"
  sql_version = "2016-03-23"

  kinesis {
    stream_name   = aws_kinesis_stream.telemetry_stream.name
    role_arn      = aws_iam_role.iot_kinesis_role.arn
    partition_key = "$${drone_id}" # Escaped for Terraform
  }
}
