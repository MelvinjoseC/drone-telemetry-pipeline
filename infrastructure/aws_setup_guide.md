# ☁️ AWS Deployment & Operations Guide — Drone Telemetry Pipeline

This guide outlines how to provision and operate the production-ready Drone Telemetry Pipeline using **Terraform (Infrastructure as Code)**, **Docker**, and **Docker Compose**.

---

## 🛠️ Prerequisites
Before starting, ensure you have the following installed:
- [AWS CLI](https://aws.amazon.com/cli/) (configured with administrator credentials)
- [Terraform](https://www.terraform.io/) (v1.6.0+)
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)

---

## 🚀 Step 1 — Automated Resource Provisioning via Terraform

Instead of manually creating AWS services, provision the entire architecture securely using Terraform:

1. Navigate to the Terraform directory:
   ```bash
   cd infrastructure/terraform
   ```

2. Initialize Terraform and download providers:
   ```bash
   terraform init
   ```

3. Plan the deployment to verify the resources that will be created:
   ```bash
   terraform plan -var="s3_bucket_name=drone-telemetry-melvin" -var="alert_email=your-email@example.com"
   ```
   > [!TIP]
   > Replace `drone-telemetry-melvin` with a globally unique bucket name. Enter a valid email address under `alert_email` to receive CloudWatch monitoring alerts.

4. Apply the configuration to deploy the infrastructure to AWS:
   ```bash
   terraform apply -var="s3_bucket_name=drone-telemetry-melvin" -var="alert_email=your-email@example.com" -auto-approve
   ```

5. Note down the outputs from Terraform:
   - S3 Bucket Name & Kinesis Stream Name
   - Lambda Function Name
   - IoT Thing Name (`DRONE-001`)
   - SNS Topic ARN (for pipeline alerts)

---

## 🔑 Step 2 — AWS IoT Device Certificates Setup

Because AWS IoT requires certificate-based mutual TLS (mTLS), you must generate and register device credentials:

1. Open the **AWS Console → IoT Core → Manage → All devices → Things**.
2. Click on the Terraform-created IoT Thing `DRONE-001`.
3. Go to the **Certificates** tab and click **Create certificate** (or generate one manually using `aws iot create-keys-and-certificate`).
4. **Download all generated certificate files**:
   - Device Certificate (`device-certificate.pem.crt`)
   - Private Key File (`private.pem.key`)
   - Amazon Root CA 1 (`AmazonRootCA1.pem` - from AWS CA downloads page)
5. Place these files inside the simulator's certificates directory:
   ```
   device-simulator/certs/
   ├── AmazonRootCA1.pem
   ├── device-certificate.pem.crt
   └── private.pem.key
   ```
6. **Activate the certificate** in AWS Console and attach the Terraform-created policy (`DroneDevicePolicy`) to the certificate.

---

## 🐳 Step 3 — Run the Simulator via Docker Compose

Once the certificates are in place, spin up the simulator without needing to configure local Python environments:

1. Create a `.env` file in the root directory:
   ```env
   AWS_IOT_ENDPOINT=your-endpoint.iot.us-east-1.amazonaws.com
   AWS_REGION=us-east-1
   MQTT_TOPIC=drones/telemetry
   DRONE_ID=DRONE-001
   SEND_INTERVAL=2
   SIMULATE_FLIGHT=true
   ```
   *(Retrieve your IoT endpoint via AWS Console → IoT Core → Settings → Device data endpoint)*

2. Start the simulator container in the background:
   ```bash
   docker compose up --build -d
   ```

3. View live flight telemetry logs:
   ```bash
   docker compose logs -f drone-simulator
   ```

4. To stop the simulator:
   ```bash
   docker compose down
   ```

---

## 📊 Step 4 — Visualizing Data with AWS QuickSight

1. Connect **S3** to **AWS QuickSight** as a datasource.
2. Point QuickSight to the partitioned data path: `s3://<your-bucket>/telemetry/`.
3. Create dashboards mapping GPS coordinates, flight paths, battery depletion rates, and speed.

---

## 🗑️ Tear Down Infrastructure

When finished testing, prevent ongoing AWS charges by destroying all provisioned resources:

```bash
cd infrastructure/terraform
terraform destroy -var="s3_bucket_name=drone-telemetry-melvin" -auto-approve
```
