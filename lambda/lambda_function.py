"""
lambda_function.py
────────────────────────────────────────────────────────
AWS Lambda triggered by Kinesis Data Stream.
Processes drone telemetry records and stores to S3.

Trigger : Kinesis Data Stream (DroneDataStream)
Output  : S3 bucket (drone-telemetry-data)
          Path: telemetry/YYYY/MM/DD/HH/drone_id_timestamp.json
Author  : Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import os
import json
import boto3
import base64
import logging
from datetime import datetime, timezone

# ── Logging ───────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_json(level, message, extra=None):
    """Output structured JSON log to stdout for CloudWatch ingestion."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": level.upper(),
        "message": message
    }
    if extra:
        record.update(extra)
    print(json.dumps(record))

# ── AWS Clients ───────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
s3 = boto3.client("s3", region_name=AWS_REGION)

# Read S3 bucket name from environment variable
S3_BUCKET = os.environ.get("S3_BUCKET", "drone-telemetry-data")

# ── S3 Key Builder ────────────────────────────────
def build_s3_key(drone_id, timestamp_str):
    """
    Build a Hive-compatible partitioned S3 path for easy querying via Athena/Glue.
    Example: telemetry/year=2024/month=01/day=15/hour=10/DRONE-001_2024-01-15T10-30-00Z.json
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    return (
        f"telemetry/"
        f"year={dt.year}/month={dt.month:02d}/day={dt.day:02d}/hour={dt.hour:02d}/"
        f"{drone_id}_{timestamp_str.replace(':', '-')}.json"
    )

# ── Process single record ─────────────────────────
def process_record(record):
    """Decode and validate one Kinesis record."""
    try:
        # Kinesis data is base64 encoded
        raw = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to base64 decode record data: {str(e)}")

    try:
        payload = json.loads(raw)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON payload: {str(e)}")

    required = ["drone_id", "timestamp", "latitude", "longitude",
                "altitude_m", "speed_kmh", "battery_pct"]
    for field in required:
        if field not in payload or payload[field] is None:
            raise ValueError(f"Missing required field: '{field}' in payload")

    # Add processing metadata
    payload["processed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["source"]       = "kinesis-lambda-pipeline"

    return payload

# ── Store to S3 ───────────────────────────────────
def store_to_s3(payload):
    """Write telemetry record to S3 as JSON."""
    key  = build_s3_key(payload["drone_id"], payload["timestamp"])
    body = json.dumps(payload, indent=2)

    s3.put_object(
        Bucket      = S3_BUCKET,
        Key         = key,
        Body        = body,
        ContentType = "application/json"
    )
    return key

# ── Main handler ──────────────────────────────────
def lambda_handler(event, context):
    """
    Triggered by Kinesis stream.
    Processes batch of drone telemetry records.
    Supports ReportBatchItemFailures for resilient processing.
    """
    records = event.get("Records", [])
    log_json("INFO", f"Processing {len(records)} Kinesis records", {"batch_size": len(records)})

    batch_item_failures = []
    success_count = 0
    error_count   = 0

    for record in records:
        sequence_number = record.get("kinesis", {}).get("sequenceNumber")
        try:
            payload = process_record(record)
            s3_key  = store_to_s3(payload)

            log_json("INFO", "Telemetry record processed and stored successfully", {
                "drone_id": payload["drone_id"],
                "altitude_m": payload["altitude_m"],
                "speed_kmh": payload["speed_kmh"],
                "battery_pct": payload["battery_pct"],
                "s3_key": s3_key
            })
            success_count += 1

        except Exception as e:
            log_json("ERROR", f"Failed to process record: {str(e)}", {
                "error": str(e),
                "sequence_number": sequence_number
            })
            error_count += 1
            if sequence_number:
                batch_item_failures.append({"itemIdentifier": sequence_number})

    log_json("INFO", "Batch execution completed", {
        "success_count": success_count,
        "error_count": error_count,
        "failures_reported": len(batch_item_failures)
    })

    return {
        "batchItemFailures": batch_item_failures
    }
