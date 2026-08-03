# 🚁 Production-Grade Drone Telemetry Data Pipeline — AWS Cloud

A high-performance, containerized, and production-ready IoT data pipeline that streams **live drone telemetry** (GPS, altitude, speed, battery) to AWS Cloud for real-time processing, storage, and analytics. 

This repository represents an enterprise-grade refactor incorporating modern DevOps practices, security hardening, robust error handling, Infrastructure as Code (IaC), and fully-featured CI/CD pipelines.

---

## 📐 Architecture & Telemetry Data Flow

```
[Drone Simulator (Docker)]
         │
         │ MQTT via TLS (port 8883)
         ▼
  [AWS IoT Core]
         │
         │ IoT Topic Rule ($drone_id Partition Key)
         ▼
[Kinesis Data Streams (KMS Encrypted)]
         │
         │ triggers (ReportBatchItemFailures)
         ▼
    [AWS Lambda] ──(Structured JSON logs)──► [CloudWatch Log Group (14-day retention)]
         │
         │ stores Hive-partitioned files
         ▼
[AWS S3 Bucket (SSE-KMS Encryption, Versioned, Lifecycle Policies)]
         │
         │ data source
         ▼
[AWS QuickSight / Athena]
```

---

## 🚀 Key Production Overhaul Enhancements

As part of transforming this into an enterprise-ready DevOps implementation, the following updates were made:

### 1. 🐳 Containerization & Easy Local Development
- **Dockerfile**: Added a lightweight, multi-stage-friendly `Dockerfile` based on `python:3.11-slim`.
- **Docker Compose**: Pre-configured `docker-compose.yml` to launch the simulator with custom credentials, variables, and mounted local certificate folder.
- **Environment variables**: Migrated all hardcoded values in the simulator's `config.py` to support env-based configuration and automatic `.env` loading.

### 2. ⚡ Resilient & Cost-Efficient AWS Lambda
- **Structured JSON Logging**: Implemented JSON structured logging format, making logs immediately searchable and parseable in CloudWatch Log Insights.
- **Hive-Compatible Partitioning**: Changed file keys to `telemetry/year=YYYY/month=MM/day=DD/hour=HH/...`, allowing seamless data cataloging via AWS Glue and ultra-fast SQL queries in Athena.
- **Batch Error Resiliency**: Configured `ReportBatchItemFailures` inside the Kinesis event consumer. If a single telemetry record fails, only that record is retried by Kinesis, preventing pipeline blockage and saving computation costs.
- **Zero Hardcoding**: Dynamically loads configuration (S3 buckets, regions) via environment variables.

### 3. 🛡️ Hardened Infrastructure as Code (IaC)
- **S3 Security**: Enforced versioning, blocked all public access, configured default AES256 server-side encryption, and created a 90-day expiration/30-day Glacier transition lifecycle policy.
- **Kinesis Encryption**: Enabled server-side encryption for the Kinesis Data Stream using AWS KMS.
- **Log Management**: Explicitly declared CloudWatch Log Groups for the Lambda function with a 14-day retention limit to control storage costs.
- **Real-Time Monitoring**: Deployed CloudWatch alarms for Lambda errors and Kinesis stream throttles, publishing alerts to an SNS Topic.

### 4. 👷 Modern CI/CD Pipeline
- **Upgraded Actions**: Migrated the workflows to v4/v5 GitHub Actions.
- **Linting & Code Quality**: Replaced `flake8` with **Ruff** for blazingly fast Python linting and styling checks.
- **IaC Security Scanning**: Integrated **Trivy** directly into the GitHub Actions flow to check for misconfigurations and security vulnerabilities before infrastructure changes are applied.

---

## 📁 Project Structure

```
drone-telemetry-pipeline/
│
├── .github/workflows/
│   └── ci.yml                  # GitHub Actions pipeline (Ruff + Trivy + Tests)
│
├── device-simulator/
│   ├── Dockerfile              # Docker recipe for simulator run
│   ├── config.py               # Env-based simulator configurations
│   ├── drone_publisher.py      # Telemetry publisher (Paho-MQTT client)
│   ├── requirements.txt        # Python dependencies
│   └── certs/                  # Place AWS IoT certificate credentials here
│
├── lambda/
│   └── lambda_function.py      # Resilient Kinesis-S3 event processor
│
├── infrastructure/
│   ├── aws_setup_guide.md      # Terraform & Docker deployment guide
│   └── terraform/              # Terraform scripts (main, variables, outputs)
│
├── tests/
│   ├── test_lambda.py          # Lambda function unit tests
│   └── test_simulator.py       # Simulator unit tests
│
├── docker-compose.yml          # Local container run setup
└── README.md                   # Project description
```

---

## ⚡ Quick Start

For detailed step-by-step setup instructions, please consult the [AWS Deployment & Operations Guide](file:///c:/Users/User/Desktop/DRONE%20TELEMETRY/infrastructure/aws_setup_guide.md).

```bash
# Clone the repository
git clone https://github.com/MelvinjoseC/drone-telemetry-pipeline.git
cd drone-telemetry-pipeline

# Run local test suite
python -m unittest discover -s tests
```

---

## 📄 License
This project is licensed under the MIT License.
