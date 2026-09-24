# 🚁 Enterprise Drone Telemetry Data Pipeline — AWS Cloud

A high-performance, containerized, and production-ready IoT data pipeline that streams **live drone fleet telemetry** (GPS, altitude, speed, battery, heading) to AWS Cloud for real-time validation, anomaly detection, dead-letter quarantine, and analytical querying.

[![CI Pipeline](https://github.com/MelvinjoseC/drone-telemetry-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/MelvinjoseC/drone-telemetry-pipeline/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)](https://www.python.org/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform%201.6%2B-623CE4)](https://www.terraform.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📐 Enterprise Architecture

```
[Drone Fleet Simulator (Docker/LocalStack)]
                 │
                 │ Mutual TLS (MQTT 8883)
                 ▼
          [AWS IoT Core]
                 │
                 │ Topic Rule ($drone_id Partition Key)
                 ▼
   [Kinesis Data Streams (KMS Encrypted)]
                 │
                 │ Micro-batch trigger (ReportBatchItemFailures)
                 ▼
       [AWS Lambda Processor]
       ├── Strict Schema Validation (v1.0.0)
       ├── Real-time Anomaly Detection (Ceiling, Speed, Power)
       └── Micro-batching & NDJSON Aggregation
                 │
        ┌────────┴────────────────────────┐
        ▼ Valid Data                      ▼ Poison-Pill / Corrupt
 [S3 Telemetry Data Lake]       [S3 Dead-Letter Quarantine]
 • Hive Partitioning:           • Prefix: dead-letter/year=...
   telemetry/year=YYYY/...      • Zero shard blockage
 • SSE-AES256 & Versioning
 • S3 Server Access Logs
        │
        ├─────────────────────────────────┐
        ▼                                 ▼
 [AWS Glue Data Catalog]        [CloudWatch Operational Dashboard]
 • Database: drone_telemetry    • Ingestion throughput & byte rate
 • Table: telemetry_records     • Lambda duration percentiles (p50/p95/p99)
 • Partition Projection         • Real-time error & quarantine alarms
        │
        ▼
 [Amazon Athena / QuickSight]
 • Serverless SQL Analytics
 • Flight paths & fleet trends
```

---

## 🚀 Enterprise Feature Highlights

### 1. 🛸 Multi-Drone Fleet & Waypoint Simulation
- **Fleet Simulator**: Simulate multiple drones concurrently (`--fleet-size N`) with independent flight dynamics, realistic battery discharge, and staggered operational phases.
- **Flight Scenarios**: Pre-configured mission profiles (`--scenario patrol` for perimeter inspection, `--scenario delivery` for point-to-point transit and RTL).
- **Offline Dry-Run Mode**: Full simulation without live AWS network dependencies (`--dry-run --max-ticks 10`).

### 2. ⚡ Resilient & Cost-Efficient Stream Processing
- **Strict Data Model**: Schema validation enforcing domain constraints (`lat [-90, 90]`, `alt [0, 5000m]`, `speed [0, 400 km/h]`, `battery [0, 100%]`).
- **Dead-Letter Queue (DLQ) Quarantine**: Corrupt or malformed records are safely isolated to `s3://${BUCKET}/dead-letter/` with complete diagnostic metadata, preventing poison pills from stalling Kinesis shard processing.
- **Real-Time Anomaly Engine**: Detects regulatory altitude ceiling breaches (> 120m AGL), overspeed conditions, low battery warnings (< 25%), and critical failsafes (< 15%).
- **Micro-Batching Optimization**: Supports partition-aligned line-delimited JSON (`.ndjson`) batch writes, reducing S3 `PutObject` API overhead by up to 90%.

### 3. 🛡️ Hardened Infrastructure as Code (Terraform)
- **AWS Glue & Athena Data Lake**: Pre-provisioned Glue Catalog database, partitioned table with Athena Partition Projection, and analytical SQL templates.
- **Operational Dashboard as Code**: CloudWatch dashboard monitoring incoming records, byte volume, Lambda duration percentiles, error rates, and S3 activity.
- **Security Hardening**: Server access logging bucket, default AES256 server-side encryption, versioning, 90-day lifecycle expiration, and IAM least-privilege scoping.

### 4. 👷 Modern DevSecOps & Local Testing
- **LocalStack Integration**: Offline AWS cloud emulation in `docker-compose.yml` with auto-initialization script (`scripts/localstack-init.sh`).
- **Load Benchmarking Tool**: Benchmarks ingestion throughput and latency distribution (`p50`, `p90`, `p99`) across concurrent worker threads (`scripts/benchmark_publisher.py`).
- **Comprehensive Diagnostics**: Upgraded `scripts/health_check.py` with AWS STS identity, S3 access, and Kinesis status verification.
- **Developer Makefile & Pre-Commit**: Unified automation targets (`make lint`, `make test`, `make coverage`, `make tf-plan`).

---

## 📁 Repository Structure

```
drone-telemetry-pipeline/
│
├── .github/workflows/
│   └── ci.yml                      # CI pipeline (Python matrix, Ruff, Trivy, Coverage)
│
├── device-simulator/
│   ├── config.py                   # Environment-driven simulator settings
│   ├── drone_publisher.py          # Multi-drone fleet publisher with CLI flags
│   ├── scenarios.py                # Waypoint navigation & flight scenarios
│   ├── Dockerfile                  # Lightweight Python 3.11 container image
│   ├── requirements.txt            # Device runtime dependencies
│   └── certs/                      # Directory for mutual TLS X.509 certs
│
├── lambda/
│   ├── lambda_function.py          # Resilient Kinesis-S3 processor with DLQ & micro-batching
│   ├── telemetry_model.py          # Domain data model & schema validation
│   └── anomaly_detector.py         # Real-time flight limit & boundary evaluation
│
├── infrastructure/
│   ├── terraform/                  # Terraform IaC (S3, Kinesis, Lambda, Glue, Athena, Dashboard)
│   ├── athena/                     # Analytical SQL query suite
│   └── aws_setup_guide.md          # Cloud deployment operations manual
│
├── scripts/
│   ├── health_check.py             # Diagnostic CLI for config, certs, and AWS resources
│   ├── benchmark_publisher.py      # High-throughput load and latency benchmark tool
│   ├── localstack-init.sh          # Offline LocalStack AWS resource initialization
│   └── test_local_pipeline.py      # Offline end-to-end integration test runner
│
├── tests/
│   ├── test_lambda.py              # Tests for Lambda handler, DLQ, and batching
│   ├── test_simulator.py           # Tests for simulator physics, fleet, and waypoints
│   ├── test_telemetry_model.py     # Tests for data schema validation and boundaries
│   └── test_anomaly_detector.py    # Tests for altitude, speed, and battery anomalies
│
├── docker-compose.yml              # LocalStack and Simulator multi-container stack
├── Makefile                        # Unified developer automation commands
├── .pre-commit-config.yaml         # Git pre-commit linting and validation hooks
├── .coveragerc                     # Code coverage configuration
└── README.md                       # Project documentation
```

---

## ⚡ Quick Start

### 1. Developer Tooling (Makefile)

```bash
# View all available developer commands
make help

# Run linting with Ruff
make lint

# Run unit tests
make test

# Run unit tests with code coverage report
make coverage
```

### 2. Fleet Simulation & Load Benchmarking

```bash
# Run 2-drone fleet simulation locally (dry-run mode)
python device-simulator/drone_publisher.py --dry-run --fleet-size 2 --max-ticks 5

# Run waypoint mission scenario (Patrol)
python device-simulator/drone_publisher.py --dry-run --scenario patrol --max-ticks 5

# Run high-throughput ingestion benchmark (5,000 records, 4 worker threads)
python scripts/benchmark_publisher.py --records 5000 --threads 4
```

### 3. Pipeline Health Check & Offline Testing

```bash
# Run pipeline configuration and diagnostic checks
python scripts/health_check.py

# Run offline end-to-end simulation (validates S3 storage & poison-pill DLQ quarantine)
python scripts/test_local_pipeline.py
```

### 4. Terraform Infrastructure as Code

```bash
# Initialize Terraform
make tf-init

# Validate configuration
make tf-validate

# Review execution plan
make tf-plan
```

---

## 📊 Analytical Athena SQL Queries

Once telemetry is flowing to S3, query the data lake directly via Amazon Athena:

```sql
-- Query fleet flight summary by drone
SELECT 
    drone_id,
    COUNT(*) AS total_points,
    ROUND(AVG(speed_kmh), 2) AS avg_speed_kmh,
    ROUND(MAX(altitude_m), 2) AS max_altitude_m,
    ROUND(MIN(battery_pct), 1) AS min_battery_pct
FROM "drone_telemetry_db_dev"."telemetry_records"
WHERE year = '2024' AND month = '01'
GROUP BY drone_id;
```

*(See [queries.sql](infrastructure/athena/queries.sql) for additional anomaly and volume queries).*

---

## 📄 License
This project is licensed under the MIT License.
