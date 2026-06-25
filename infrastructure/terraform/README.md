# 🛠️ Terraform AWS Setup — Drone Telemetry Pipeline

This directory contains the Terraform configuration to fully automate the provisioning of the AWS IoT and data streaming pipeline.

## 📋 Prerequisites

Before running the Terraform script, ensure you have:
1. **Terraform CLI** (v1.2.0 or later) installed.
2. **AWS CLI** installed and configured with appropriate permissions.
3. Your AWS credentials set up locally (`aws configure`).

---

## 🚀 Deployment Steps

### Step 1 — Initialize Terraform
Install the required AWS and Archive providers:
```bash
terraform init
```

### Step 2 — Plan the Infrastructure
Review the resources that will be created:
```bash
terraform plan
```

### Step 3 — Apply Changes
Deploy the pipeline to AWS:
```bash
terraform apply
```
*Note: S3 bucket names must be globally unique. If the default name is taken, override it:*
```bash
terraform apply -var="s3_bucket_name=drone-telemetry-data-YOURNAME"
```

---

## 🧹 Clean Up

To tear down all resources and avoid continuing charges on AWS:
```bash
terraform destroy
```
*(Warning: This will permanently delete the S3 bucket and any telemetry data stored inside it.)*
