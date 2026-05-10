# ☁️ AWS Setup Guide — Drone Telemetry Pipeline

Follow these steps in order. Takes about 45–60 minutes.

---

## Step 1 — Create S3 Bucket

1. Go to **AWS Console → S3 → Create Bucket**
2. Bucket name: `drone-telemetry-data` (must be globally unique — add your name e.g. `drone-telemetry-melvin`)
3. Region: `us-east-1`
4. Block all public access: ✅ Keep checked
5. Click **Create Bucket**

---

## Step 2 — Create Kinesis Data Stream

1. Go to **AWS Console → Kinesis → Data Streams → Create**
2. Stream name: `DroneDataStream`
3. Capacity mode: **On-demand** (free tier friendly)
4. Click **Create**

---

## Step 3 — Create IAM Role for Lambda

1. Go to **IAM → Roles → Create Role**
2. Trusted entity: **AWS Service → Lambda**
3. Add permissions:
   - `AmazonS3FullAccess`
   - `AWSLambdaKinesisExecutionRole`
   - `AWSLambdaBasicExecutionRole`
   - `AWSIoTFullAccess`
4. Role name: `drone-lambda-role`
5. Click **Create**

---

## Step 4 — Create Lambda Function

1. Go to **Lambda → Create Function**
2. Name: `DroneTelemetryProcessor`
3. Runtime: **Python 3.11**
4. Execution role: `drone-lambda-role`
5. Click **Create Function**
6. Paste code from `lambda/lambda_function.py`
7. Update `S3_BUCKET` variable with your actual bucket name
8. Click **Deploy**

### Add Kinesis Trigger to Lambda
1. In Lambda → click **Add Trigger**
2. Source: **Kinesis**
3. Stream: `DroneDataStream`
4. Batch size: `10`
5. Starting position: **Latest**
6. Click **Add**

---

## Step 5 — Set Up AWS IoT Core

### 5a — Create IoT Thing
1. Go to **IoT Core → Manage → Things → Create Thing**
2. Name: `DRONE-001`
3. Auto-generate certificate → Next
4. **Download all certificates** → put in `device-simulator/certs/`

### 5b — Create IoT Policy
1. **IoT Core → Security → Policies → Create**
2. Name: `DroneDevicePolicy`
3. JSON:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["iot:Connect", "iot:Publish", "iot:Subscribe", "iot:Receive"],
      "Resource": "*"
    }
  ]
}
```

### 5c — Create IoT Rule (IoT Core → Kinesis)
1. **IoT Core → Message Routing → Rules → Create**
2. Name: `DroneToKinesis`
3. SQL:
```sql
SELECT * FROM 'drones/telemetry'
```
4. Action: **Kinesis Data Streams**
5. Stream: `DroneDataStream`
6. Partition key: `${drone_id}`
7. Create new IAM role for this rule
8. Click **Create**

### 5d — Get IoT Endpoint
1. **IoT Core → Settings**
2. Copy **Device data endpoint**
3. Paste into `device-simulator/config.py`

---

## Step 6 — Connect QuickSight to S3

1. Go to **AWS QuickSight → New Dataset → S3**
2. Connect to your `drone-telemetry-data` bucket
3. Build charts:
   - **Line chart**: timestamp vs altitude
   - **Line chart**: timestamp vs speed
   - **Map**: latitude/longitude flight path
   - **Gauge**: battery percentage

---

## Step 7 — Run the Simulator

```bash
cd device-simulator
pip install -r requirements.txt
python drone_publisher.py
```

---

## ✅ Verify Pipeline

```
drone_publisher.py runs
→ IoT Core receives MQTT messages
→ IoT Rule forwards to Kinesis
→ Kinesis triggers Lambda
→ Lambda stores JSON to S3
→ QuickSight shows flight data
→ CloudWatch shows Lambda metrics
```

---

## 💰 Cost Estimate (Free Tier)

| Service | Free Tier |
|---|---|
| IoT Core | 250K messages/month |
| Kinesis | 1 shard × 1 month free |
| Lambda | 1M requests/month |
| S3 | 5 GB storage free |
| QuickSight | 1 user free for 30 days |

**Total cost: ~$0** within free tier ✅
