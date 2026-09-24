# ─────────────────────────────────────────────────
#  outputs.tf — Terraform Output Values
# ─────────────────────────────────────────────────

output "s3_bucket_name" {
  value       = aws_s3_bucket.telemetry.id
  description = "Name of the S3 bucket storing drone telemetry data"
}

output "s3_bucket_arn" {
  value       = aws_s3_bucket.telemetry.arn
  description = "ARN of the S3 bucket storing drone telemetry data"
}

output "kinesis_stream_name" {
  value       = aws_kinesis_stream.telemetry_stream.name
  description = "Name of the Kinesis Data Stream"
}

output "kinesis_stream_arn" {
  value       = aws_kinesis_stream.telemetry_stream.arn
  description = "ARN of the Kinesis Data Stream"
}

output "lambda_function_name" {
  value       = aws_lambda_function.telemetry_processor.function_name
  description = "Name of the Lambda function"
}

output "lambda_function_arn" {
  value       = aws_lambda_function.telemetry_processor.arn
  description = "ARN of the Lambda function"
}

output "iot_thing_name" {
  value       = aws_iot_thing.drone_thing.name
  description = "Name of the IoT Thing created for the drone"
}

output "iot_policy_name" {
  value       = aws_iot_policy.drone_policy.name
  description = "Name of the IoT device policy"
}

output "iot_rule_name" {
  value       = aws_iot_topic_rule.drone_to_kinesis.name
  description = "Name of the IoT Core routing rule"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.pipeline_alerts.arn
  description = "ARN of the SNS topic used for pipeline monitoring alarms"
}

output "glue_database_name" {
  value       = aws_glue_catalog_database.telemetry_db.name
  description = "Name of the Glue Catalog database for Athena queries"
}

output "glue_table_name" {
  value       = aws_glue_catalog_table.telemetry_records.name
  description = "Name of the Glue Catalog table for telemetry records"
}

output "athena_workgroup_name" {
  value       = aws_athena_workgroup.telemetry_analytics.name
  description = "Name of the Athena workgroup for analytical queries"
}

output "cloudwatch_dashboard_name" {
  value       = aws_cloudwatch_dashboard.pipeline_dashboard.dashboard_name
  description = "Name of the operational CloudWatch dashboard for pipeline monitoring"
}
