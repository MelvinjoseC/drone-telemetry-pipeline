# Changelog

All notable changes to the **Drone Telemetry Data Pipeline** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] — 2026-09-24

### 🚀 Added
- **Multi-Drone Fleet Simulation**: Added `FleetSimulator` class in `drone_publisher.py` supporting concurrent multi-drone simulation with independent flight dynamics, battery physics, and staggered tick offsets.
- **Waypoint Navigation & Mission Scenarios**: Introduced `scenarios.py` with Haversine distance, bearing calculations, and mission profiles (`--scenario patrol` for perimeter inspection, `--scenario delivery` for cargo drop and RTL).
- **Strict Telemetry Data Model**: Created `lambda/telemetry_model.py` enforcing schema version `1.0.0`, type casting, and physical domain boundaries (`lat [-90, 90]`, `alt [0, 5000m]`, `speed [0, 400 km/h]`, `battery [0, 100%]`).
- **Dead-Letter Queue (DLQ) Quarantine**: Implemented `quarantine_record()` in `lambda_function.py` to isolate corrupt or unparseable payloads to `dead-letter/year=...` without stalling Kinesis shard processing.
- **Real-Time Flight Anomaly Detection**: Created `lambda/anomaly_detector.py` to evaluate regulatory altitude ceiling breaches (> 120m AGL), overspeed conditions (> 100 km/h), low battery warnings (< 25%), and critical failsafes (< 15%).
- **Micro-Batch S3 Storage**: Implemented `store_batch_to_s3()` supporting partition-aligned line-delimited JSON (`.ndjson`) files, cutting S3 PUT API requests by up to 90%.
- **AWS Glue Data Catalog & Athena Table**: Provisioned Glue Database, external partitioned table with Partition Projection, and Athena Workgroup in Terraform IaC.
- **CloudWatch Operational Dashboard**: Added CloudWatch dashboard as code monitoring ingestion throughput, byte rates, Lambda duration percentiles (p50/p95/p99), and error rates.
- **S3 Server Access Logging**: Provisioned dedicated access logging bucket and lifecycle retention for CIS/compliance auditability.
- **LocalStack Offline Development**: Added LocalStack container service in `docker-compose.yml` with auto-initialization script (`scripts/localstack-init.sh`).
- **High-Throughput Load Benchmark Harness**: Added `scripts/benchmark_publisher.py` to evaluate pipeline serialization speed and latency percentiles under multi-threaded load.
- **Comprehensive Diagnostic CLI**: Overhauled `scripts/health_check.py` with AWS STS caller identity, S3 access, and Kinesis stream reachability checks.
- **Developer Automation**: Added cross-platform `Makefile` and `.pre-commit-config.yaml` git hooks.
- **Test Coverage & CI Matrix**: Expanded unit tests to 29 test cases, added `.coveragerc`, configured Python 3.11/3.12 CI matrix with pip caching, and added offline E2E pipeline test (`scripts/test_local_pipeline.py`).
- **Telemetry Schema Specification**: Added `docs/telemetry_schema.md` documenting field types, units, anomaly codes, and DLQ formats.

### 🛡️ Security
- Tightened IAM least-privilege policies for Lambda execution, restricting S3 write actions strictly to `telemetry/*` and `dead-letter/*` prefixes.
- Enforced S3 server-side encryption with AES256, versioning, and public access blocks across all buckets.

### 🔧 Fixed
- Fixed Ruff `E402` module-level import order linting issue in `tests/test_simulator.py`.
- Formatted entire Python codebase according to PEP 8 / Ruff standard formatting rules.
- Fixed S3 lifecycle rule filter block in Terraform IaC to eliminate validation deprecation warnings.

---

## [1.0.0] — 2024-01-15

### Added
- Initial release of the single drone telemetry publisher with Paho MQTT.
- AWS IoT Core topic rule routing to Amazon Kinesis Data Stream.
- AWS Lambda consumer writing individual JSON records to Amazon S3.
- Base Terraform configuration for S3, Kinesis, IAM, and Lambda.
- Basic GitHub Actions CI workflow with flake8 and unit tests.
