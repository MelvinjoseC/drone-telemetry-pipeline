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

import json
import boto3
import base64
import logging
from datetime import datetime

# ── Logging ───────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── AWS Clients ───────────────────────────────────
s3 = boto3.client("s3", region_name="us-east-1")

S3_BUCKET = "drone-telemetry-data"

# ── S3 Key Builder ────────────────────────────────
def build_s3_key(drone_id, timestamp_str):
    """
    Build a partitioned S3 path for easy querying.
    Example: telemetry/2024/01/15/10/DRONE-001_2024-01-15T10:30:00Z.json
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.utcnow()

    return (
        f"telemetry/"
        f"{dt.year}/{dt.month:02d}/{dt.day:02d}/{dt.hour:02d}/"
        f"{drone_id}_{timestamp_str.replace(':', '-')}.json"
    )

# ── Process single record ─────────────────────────
def process_record(record):
    """Decode and validate one Kinesis record."""
    # Kinesis data is base64 encoded
    raw     = base64.b64decode(record["kinesis"]["data"]).decode("utf-8")
    payload = json.loads(raw)

    required = ["drone_id", "timestamp", "latitude", "longitude",
                "altitude_m", "speed_kmh", "battery_pct"]
    for field in required:
        if field not in payload:
            raise ValueError(f"Missing field: {field}")

    # Add processing metadata
    payload["processed_at"] = datetime.utcnow().isoformat() + "Z"
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
    """
    records = event.get("Records", [])
    logger.info(f"Processing {len(records)} Kinesis records")

    success_count = 0
    error_count   = 0

    for record in records:
        try:
            payload = process_record(record)
            s3_key  = store_to_s3(payload)

            logger.info(
                f"✅ Stored: {payload['drone_id']} | "
                f"Alt={payload['altitude_m']}m | "
                f"Speed={payload['speed_kmh']}km/h | "
                f"Battery={payload['battery_pct']}% | "
                f"S3: {s3_key}"
            )
            success_count += 1

        except Exception as e:
            logger.error(f"❌ Failed to process record: {e}")
            error_count += 1

    logger.info(f"Batch complete: {success_count} success, {error_count} errors")

    return {
        "statusCode"   : 200,
        "success_count": success_count,
        "error_count"  : error_count
    }
