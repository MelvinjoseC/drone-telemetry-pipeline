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

from anomaly_detector import detect_anomalies
from telemetry_model import validate_telemetry

# ── Logging ───────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log_json(level, message, extra=None):
    """Output structured JSON log to stdout for CloudWatch ingestion."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": level.upper(),
        "message": message,
    }
    if extra:
        record.update(extra)
    print(json.dumps(record))


# ── AWS Clients ───────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
s3 = boto3.client("s3", region_name=AWS_REGION)

# Read S3 bucket name from environment variable
S3_BUCKET = os.environ.get("S3_BUCKET", "drone-telemetry-data")
DEAD_LETTER_PREFIX = os.environ.get("DEAD_LETTER_PREFIX", "dead-letter")
ENABLE_QUARANTINE = os.environ.get("ENABLE_QUARANTINE", "true").lower() in (
    "true",
    "1",
    "yes",
)
AGGREGATION_MODE = os.environ.get("AGGREGATION_MODE", "RECORD").upper()


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

    validated = validate_telemetry(payload)

    # Anomaly evaluation
    anomalies = detect_anomalies(validated)
    validated["anomalies"] = anomalies
    validated["has_anomaly"] = len(anomalies) > 0

    # Add processing metadata
    validated["processed_at"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    validated["source"] = "kinesis-lambda-pipeline"

    return validated


# ── Store to S3 ───────────────────────────────────
def store_to_s3(payload):
    """Write telemetry record to S3 as JSON."""
    key = build_s3_key(payload["drone_id"], payload["timestamp"])
    body = json.dumps(payload, indent=2)

    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body, ContentType="application/json")
    return key


def store_batch_to_s3(payloads):
    """
    Micro-batch write: Aggregate multiple telemetry payloads into partition-aligned
    Newline-Delimited JSON (NDJSON) files in S3.
    Reduces S3 PutObject request volume and mitigates the small file problem.
    """
    if not payloads:
        return []

    partitions = {}
    for p in payloads:
        try:
            dt = datetime.fromisoformat(p["timestamp"].replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)

        prefix = f"telemetry/year={dt.year}/month={dt.month:02d}/day={dt.day:02d}/hour={dt.hour:02d}/"
        partitions.setdefault(prefix, []).append(p)

    written_keys = []
    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for prefix, group in partitions.items():
        ndjson_body = "\n".join(json.dumps(item) for item in group) + "\n"
        key = f"{prefix}batch_{now_str}_{len(group)}_records.ndjson"

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=ndjson_body.encode("utf-8"),
            ContentType="application/x-ndjson",
        )
        written_keys.append(key)

    return written_keys


# ── Dead-Letter Queue Quarantine ───────────────────
def quarantine_record(record, error_message, sequence_number=None):
    """
    Quarantine corrupt or invalid telemetry record to dead-letter prefix in S3.
    Prevents unrecoverable poison-pill records from stalling Kinesis shard processing.
    """
    now = datetime.now(timezone.utc)
    seq = sequence_number or "unknown"
    dt_path = f"year={now.year}/month={now.month:02d}/day={now.day:02d}"
    key = f"{DEAD_LETTER_PREFIX}/{dt_path}/dlq_{now.strftime('%Y%m%dT%H%M%SZ')}_{seq}.json"

    raw_data = ""
    try:
        raw_data = base64.b64decode(record.get("kinesis", {}).get("data", "")).decode(
            "utf-8", errors="replace"
        )
    except Exception:
        raw_data = str(record.get("kinesis", {}).get("data", ""))

    dlq_payload = {
        "quarantined_at": now.isoformat().replace("+00:00", "Z"),
        "error": str(error_message),
        "sequence_number": sequence_number,
        "approximate_arrival_timestamp": record.get("kinesis", {}).get(
            "approximateArrivalTimestamp"
        ),
        "raw_payload_preview": raw_data[:2048],
    }

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(dlq_payload, indent=2),
        ContentType="application/json",
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
    log_json(
        "INFO",
        f"Processing {len(records)} Kinesis records",
        {"batch_size": len(records)},
    )

    batch_item_failures = []
    success_count = 0
    error_count = 0
    quarantine_count = 0
    batch_payloads = []

    for record in records:
        sequence_number = record.get("kinesis", {}).get("sequenceNumber")
        try:
            payload = process_record(record)

            if AGGREGATION_MODE == "BATCH_NDJSON":
                batch_payloads.append(payload)
            else:
                s3_key = store_to_s3(payload)
                log_json(
                    "INFO",
                    "Telemetry record processed and stored successfully",
                    {
                        "drone_id": payload["drone_id"],
                        "altitude_m": payload["altitude_m"],
                        "speed_kmh": payload["speed_kmh"],
                        "battery_pct": payload["battery_pct"],
                        "s3_key": s3_key,
                    },
                )

            if payload.get("has_anomaly"):
                log_json(
                    "WARN",
                    f"Flight anomalies detected for {payload['drone_id']}",
                    {
                        "drone_id": payload["drone_id"],
                        "anomalies": payload["anomalies"],
                    },
                )

            success_count += 1

        except Exception as e:
            log_json(
                "ERROR",
                f"Failed to process record: {str(e)}",
                {"error": str(e), "sequence_number": sequence_number},
            )
            error_count += 1

            # Check if this is an unrecoverable validation/parse poison-pill
            if ENABLE_QUARANTINE and isinstance(e, (ValueError, json.JSONDecodeError)):
                try:
                    dlq_key = quarantine_record(record, str(e), sequence_number)
                    log_json(
                        "WARN",
                        f"Poison-pill record quarantined to DLQ: {dlq_key}",
                        {"dlq_key": dlq_key, "sequence_number": sequence_number},
                    )
                    quarantine_count += 1
                    continue
                except Exception as dlq_err:
                    log_json(
                        "ERROR",
                        f"Failed to quarantine record to DLQ: {str(dlq_err)}",
                        {"error": str(dlq_err)},
                    )

            if sequence_number:
                batch_item_failures.append({"itemIdentifier": sequence_number})

    # Flush aggregated batch to S3 if running in micro-batching mode
    if AGGREGATION_MODE == "BATCH_NDJSON" and batch_payloads:
        try:
            written_keys = store_batch_to_s3(batch_payloads)
            log_json(
                "INFO",
                f"Aggregated {len(batch_payloads)} records into {len(written_keys)} NDJSON batch files",
                {"s3_batch_keys": written_keys, "record_count": len(batch_payloads)},
            )
        except Exception as batch_err:
            log_json(
                "ERROR",
                f"Failed to write aggregated batch to S3: {str(batch_err)}",
                {"error": str(batch_err)},
            )
            # Re-report records as failed if batch write fails
            for record in records:
                seq = record.get("kinesis", {}).get("sequenceNumber")
                if seq and not any(
                    f["itemIdentifier"] == seq for f in batch_item_failures
                ):
                    batch_item_failures.append({"itemIdentifier": seq})

    log_json(
        "INFO",
        "Batch execution completed",
        {
            "success_count": success_count,
            "error_count": error_count,
            "quarantine_count": quarantine_count,
            "failures_reported": len(batch_item_failures),
        },
    )

    return {"batchItemFailures": batch_item_failures}
