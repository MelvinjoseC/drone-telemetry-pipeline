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

resource "aws_s3_bucket_versioning" "telemetry_versioning" {
  bucket = aws_s3_bucket.telemetry.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "telemetry_encryption" {
  bucket = aws_s3_bucket.telemetry.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "telemetry_lifecycle" {
  bucket = aws_s3_bucket.telemetry.id

  rule {
    id     = "archive-old-telemetry"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }
}

# ── Kinesis Data Stream (Ingestion Stream) ───────
resource "aws_kinesis_stream" "telemetry_stream" {
  name             = var.kinesis_stream_name
  shard_count      = var.environment == "prod" ? 2 : 1 # Shard count for dev/prod
  retention_period = 24
  encryption_type  = "KMS"
  kms_key_id       = "alias/aws/kinesis"

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

# Explicit CloudWatch Log Group to manage retention
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
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

  depends_on = [
    aws_cloudwatch_log_group.lambda_log_group
  ]

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Lambda Kinesis Trigger
resource "aws_lambda_event_source_mapping" "kinesis_trigger" {
  event_source_arn        = aws_kinesis_stream.telemetry_stream.arn
  function_name           = aws_lambda_function.telemetry_processor.function_name
  starting_position       = "LATEST"
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
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

# ── Monitoring & Alerts ──────────────────────────

# SNS Topic for alerts
resource "aws_sns_topic" "pipeline_alerts" {
  name = "drone-pipeline-alerts-topic"

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Drone-Telemetry"
  }
}

# Email subscription if alert_email is configured
resource "aws_sns_topic_subscription" "email_sub" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.pipeline_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Lambda Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_errors_alarm" {
  alarm_name          = "drone-lambda-errors-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60 # 1 minute
  statistic           = "Sum"
  threshold           = 0 # Alarm if any error occurs
  alarm_description   = "This alarm fires if the Lambda telemetry processor fails to execute."
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.telemetry_processor.function_name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Drone-Telemetry"
  }
}

# Kinesis Throttles Alarm
resource "aws_cloudwatch_metric_alarm" "kinesis_throttles_alarm" {
  alarm_name          = "drone-kinesis-throttles-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ReadProvisionedThroughputExceeded"
  namespace           = "AWS/Kinesis"
  period              = 60
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "This alarm fires if the Kinesis telemetry stream read throughput is exceeded."
  alarm_actions       = [aws_sns_topic.pipeline_alerts.arn]

  dimensions = {
    StreamName = aws_kinesis_stream.telemetry_stream.name
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Drone-Telemetry"
  }
}

# ── AWS Glue Catalog & Athena Data Lake ──────────

resource "aws_glue_catalog_database" "telemetry_db" {
  name        = "drone_telemetry_db_${var.environment}"
  description = "Glue Data Catalog database for drone telemetry analytical queries"
}

resource "aws_glue_catalog_table" "telemetry_records" {
  name          = "telemetry_records"
  database_name = aws_glue_catalog_database.telemetry_db.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"            = "json"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = "2024,2030"
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.month.digits"   = "2"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "projection.day.digits"     = "2"
    "projection.hour.type"      = "integer"
    "projection.hour.range"     = "0,23"
    "projection.hour.digits"    = "2"
    "storage.location.template" = "s3://${aws_s3_bucket.telemetry.id}/telemetry/year=$${year}/month=$${month}/day=$${day}/hour=$${hour}"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.telemetry.id}/telemetry/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      name                  = "json-serde"
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
      parameters = {
        "ignore.malformed.json" = "true"
      }
    }

    columns {
      name = "drone_id"
      type = "string"
    }
    columns {
      name = "timestamp"
      type = "string"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "altitude_m"
      type = "double"
    }
    columns {
      name = "speed_kmh"
      type = "double"
    }
    columns {
      name = "heading_deg"
      type = "double"
    }
    columns {
      name = "battery_pct"
      type = "double"
    }
    columns {
      name = "flight_mode"
      type = "string"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "schema_version"
      type = "string"
    }
    columns {
      name = "processed_at"
      type = "string"
    }
    columns {
      name = "source"
      type = "string"
    }
    columns {
      name = "has_anomaly"
      type = "boolean"
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
  partition_keys {
    name = "hour"
    type = "string"
  }
}

resource "aws_athena_workgroup" "telemetry_analytics" {
  name        = "drone-telemetry-workgroup-${var.environment}"
  description = "Athena workgroup for querying drone telemetry S3 data lake"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.telemetry.id}/athena-results/"
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Drone-Telemetry"
  }
}

# ── CloudWatch Operational Dashboard ─────────────

resource "aws_cloudwatch_dashboard" "pipeline_dashboard" {
  dashboard_name = "drone-telemetry-pipeline-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Kinesis", "IncomingRecords", "StreamName", aws_kinesis_stream.telemetry_stream.name, { stat = "Sum", period = 60, title = "Incoming Records/min" }],
            [".", "IncomingBytes", ".", ".", { stat = "Sum", period = 60, yAxis = "right", title = "Incoming Bytes" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Telemetry Stream Ingestion Volume"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.telemetry_processor.function_name, { stat = "Sum", period = 60 }],
            [".", "Errors", ".", ".", { stat = "Sum", period = 60, color = "#d62728" }],
            [".", "Throttles", ".", ".", { stat = "Sum", period = 60, color = "#ff7f0e" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Processor Invocations & Errors"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.telemetry_processor.function_name, { stat = "p50", period = 60, label = "p50 Duration (ms)" }],
            ["...", { stat = "p90", period = 60, label = "p90 Duration (ms)" }],
            ["...", { stat = "p99", period = 60, label = "p99 Duration (ms)" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Execution Latency Percentiles"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/S3", "AllRequests", "BucketName", aws_s3_bucket.telemetry.id, "FilterId", "EntireBucket", { stat = "Sum", period = 300 }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "S3 Ingestion Activity"
        }
      }
    ]
  })
}
