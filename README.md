# 🚁 Drone Telemetry Data Pipeline — AWS Cloud

A production-style IoT data pipeline that streams **live drone telemetry** (GPS, altitude, speed, battery) to AWS Cloud for real-time processing, storage, and visualization.

---

## 📐 Architecture

```
[Raspberry Pi / Simulator]
  Drone Telemetry Data
  (GPS, Altitude, Speed, Battery)
        |
        | MQTT (port 8883)
        ↓
[AWS IoT Core]
        |
        | IoT Rule → Kinesis
        ↓
[Kinesis Data Streams]
        |
        | triggers
        ↓
[AWS Lambda]
        |
        | stores processed data
        ↓
[AWS S3 Bucket]
        |
        | data source
        ↓
[AWS QuickSight Dashboard]

      +
[CloudWatch] ← monitors Lambda & Kinesis
```

---

## 🛠️ AWS Services Used

| Service | Purpose |
|---|---|
| AWS IoT Core | Receives MQTT telemetry from drone/Pi |
| Kinesis Data Streams | Real-time data stream ingestion |
| AWS Lambda | Processes & transforms telemetry data |
| AWS S3 | Stores processed telemetry as JSON/CSV |
| AWS QuickSight | Visualizes drone flight data |
| AWS CloudWatch | Monitors pipeline health |
| AWS IAM | Roles and permissions |

---

## 📁 Project Structure

```
drone-telemetry-pipeline/
│
├── device-simulator/
│   ├── drone_publisher.py     # Simulates & sends drone telemetry
│   ├── config.py              # AWS IoT configuration
│   ├── requirements.txt
│   └── certs/                 # Place AWS IoT certs here
│
├── lambda/
│   ├── lambda_function.py     # Processes Kinesis stream → S3
│   └── requirements.txt
│
├── infrastructure/
│   └── aws_setup_guide.md     # Step-by-step AWS setup
│
└── docs/
    └── architecture.md        # Detailed architecture
```

---

## 🚀 Quick Start

### Step 1 — Set up AWS
```
Follow infrastructure/aws_setup_guide.md
```

### Step 2 — Run Drone Simulator (Raspberry Pi or PC)
```bash
cd device-simulator
pip install -r requirements.txt
# Add AWS certs to device-simulator/certs/
# Edit config.py with your endpoint
python drone_publisher.py
```

### Step 3 — View Data
- **S3**: AWS Console → S3 → your bucket → telemetry files
- **QuickSight**: Connect to S3 and build flight dashboard

---

## 📊 Telemetry Data Format

```json
{
  "drone_id"    : "DRONE-001",
  "timestamp"   : "2024-01-15T10:30:00Z",
  "latitude"    : 10.8505,
  "longitude"   : 76.2711,
  "altitude_m"  : 120.5,
  "speed_kmh"   : 45.2,
  "heading_deg" : 270.0,
  "battery_pct" : 78,
  "flight_mode" : "AUTO",
  "status"      : "flying"
}
```

---

## 🔧 Hardware / Run Options

| Option | How |
|---|---|
| Raspberry Pi | Run `drone_publisher.py` on Pi |
| Laptop/PC | Run simulator on any Python machine |
| ESP32 | Use MicroPython version (coming soon) |

---

## 👤 Author

**Melvin Chacko Jose**
- Email: melvinjose025@gmail.com

> 💡 This project is inspired by real-world R&D work integrating drone telemetry data with AWS cloud infrastructure.

---

## 📄 License
MIT License
