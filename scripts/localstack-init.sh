#!/bin/bash
# ────────────────────────────────────────────────────────
#  localstack-init.sh
#  Initializes mock AWS resources in LocalStack on startup.
# ────────────────────────────────────────────────────────

echo "[INIT] Initializing LocalStack AWS Resources for Drone Telemetry..."

# 1. Create S3 Buckets
awslocal s3 mb s3://drone-telemetry-data
awslocal s3 mb s3://drone-telemetry-data-logs
echo "[INIT] Created S3 buckets: drone-telemetry-data, drone-telemetry-data-logs"

# 2. Create Kinesis Data Stream
awslocal kinesis create-stream \
    --stream-name DroneDataStream \
    --shard-count 1
echo "[INIT] Created Kinesis stream: DroneDataStream"

# 3. List created resources
echo "[INIT] Verifying resources:"
awslocal s3 ls
awslocal kinesis list-streams

echo "[INIT] LocalStack initialization completed successfully!"
