# 📐 Architecture — Drone Telemetry Pipeline

A resilient, scalable, and production-grade IoT telemetry pipeline streaming live drone data to AWS Cloud for real-time analytics, automated anomaly detection, and long-term storage in a Hive-partitioned S3 data lake.

---

## 1. End-to-End System Architecture

```
┌──────────────────────────────────────┐
│  Drone Fleet Simulator               │
│  (Docker / LocalStack / Python)      │
│  • Multi-drone concurrent fleet      │
│  • Waypoint navigation (Patrol/Drop) │
│  • Realistic aerodynamics & battery  │
└──────────────────┬───────────────────┘
                   │ MQTT over TLS (Port 8883)
                   │ Mutual TLS (X.509 Device Certificates)
                   ▼
┌──────────────────────────────────────┐
│  AWS IoT Core                        │
│  • Thing Registry & IoT Policies     │
│  • IoT Topic Rule: 'drones/telemetry'│
│  • Partition Key: ${drone_id}        │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  Kinesis Data Streams (KMS Encrypted)│
│  • On-Demand Streaming Throughput    │
│  • Shard Ordering Guarantees         │
│  • 24-Hour Buffer Retention          │
└──────────────────┬───────────────────┘
                   │ Batch Trigger (10 records)
                   │ Supports ReportBatchItemFailures
                   ▼
┌────────────────────────────────────────────────────────┐
│  AWS Lambda (Telemetry Processor)                      │
│  • Strict schema & boundary validation                 │
│  • Real-time anomaly detection (Ceiling, Speed, Power) │
│  • Micro-batching & NDJSON aggregation support         │
│  • Structured JSON logs with CloudWatch Insights       │
└────────────┬─────────────────────────────┬─────────────┘
             │                             │
             │ Normal Telemetry            │ Poison-Pills / Corrupted
             ▼                             ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│  S3 Telemetry Data Lake       │ │  S3 Dead-Letter Quarantine    │
│  • SSE-AES256 Encryption      │ │  Prefix: dead-letter/year=... │
│  • Hive Partitioning:         │ │  • Prevents shard retries     │
│    telemetry/year=YYYY/...    │ │  • Enables root-cause audit   │
│  • 30d Glacier / 90d Expiry   │ └───────────────────────────────┘
│  • Server Access Logging      │
└────────────┬──────────────────┘
             │
             ├────────────────────────────────┐
             ▼                                ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│  AWS Glue Data Catalog        │ │  CloudWatch & SNS Alerts      │
│  • Database: drone_telemetry  │ │  • CloudWatch Metric Alarms   │
│  • Table: telemetry_records   │ │  • Operational Dashboard      │
│  • Partition Projection       │ │  • Real-time SNS Alerts Topic │
└────────────┬──────────────────┘ └───────────────────────────────┘
             │
             ▼
┌───────────────────────────────┐
│  Amazon Athena / QuickSight   │
│  • Serverless SQL Analytics   │
│  • Live Fleet Maps & Trends   │
└───────────────────────────────┘
```

---

## 2. Key Architecture Design Principles

### Why Kinesis Data Streams Over Direct Ingestion?

| Design Decision | Without Kinesis Buffer | With Kinesis Data Streams |
|---|---|---|
| **Spike Resiliency** | Sudden drone traffic spikes throttle Lambda concurrency. | Millions of records buffered safely with zero data loss. |
| **Record Ordering** | No strict guarantee across multiple concurrent lambdas. | Telemetry strictly ordered per drone via `${drone_id}` partition key. |
| **Compute Efficiency** | 1 Lambda invocation per MQTT packet (costly). | Ingests micro-batches (10–500 records), slashing invocation costs. |

### Dead-Letter Queue (DLQ) & Poison-Pill Isolation

Unparseable packets or out-of-range payloads are intercepted by `quarantine_record()` and immediately stored in `s3://${BUCKET}/dead-letter/` with full debug context. The Lambda returns clean batch item IDs to Kinesis, preventing poison records from stalling shard consumer throughput.

### Hive-Compatible Partition Projection

Using S3 key formatting:
```
telemetry/year=YYYY/month=MM/day=DD/hour=HH/drone_id_timestamp.json
```
Coupled with AWS Glue Partition Projection, Amazon Athena avoids costly S3 metadata crawls (`MSCK REPAIR TABLE`), executing queries across millions of records in milliseconds.
