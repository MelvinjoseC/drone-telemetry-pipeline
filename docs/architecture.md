# 📐 Architecture — Drone Telemetry Pipeline

## Data Flow

```
┌──────────────────────────┐
│  Drone Simulator          │
│  (Raspberry Pi / PC)      │
│                           │
│  Simulates:               │
│  • GPS lat/lon            │
│  • Altitude (meters)      │
│  • Speed (km/h)           │
│  • Heading (degrees)      │
│  • Battery %              │
│  • Flight mode            │
└────────────┬─────────────┘
             │ MQTT over TLS
             │ Topic: drones/telemetry
             ▼
┌──────────────────────────┐
│  AWS IoT Core             │
│  • Authenticates device   │
│  • IoT Rule fires on msg  │
│  • Routes → Kinesis       │
└────────────┬─────────────┘
             │ IoT Rule → Kinesis
             ▼
┌──────────────────────────┐
│  Kinesis Data Streams     │
│  DroneDataStream          │
│  • Buffers real-time data │
│  • Ordered stream         │
│  • Triggers Lambda        │
└────────────┬─────────────┘
             │ Batch trigger (10 records)
             ▼
┌──────────────────────────┐
│  AWS Lambda               │
│  DroneTelemetryProcessor  │
│  • Decodes base64 records │
│  • Validates fields       │
│  • Adds metadata          │
│  • Writes to S3           │
└────────────┬─────────────┘
             │ put_object()
             ▼
┌──────────────────────────┐
│  AWS S3                   │
│  drone-telemetry-data     │
│                           │
│  Path structure:          │
│  telemetry/               │
│  └── 2024/                │
│      └── 01/              │
│          └── 15/          │
│              └── 10/      │
│                 └── *.json│
└────────────┬─────────────┘
             │ data source
             ▼
┌──────────────────────────┐
│  AWS QuickSight           │
│  • Flight path map        │
│  • Altitude over time     │
│  • Speed trends           │
│  • Battery monitoring     │
└──────────────────────────┘

     ↕ monitors all stages
┌──────────────────────────┐
│  AWS CloudWatch           │
│  • Lambda invocations     │
│  • Kinesis throughput     │
│  • Error alarms           │
└──────────────────────────┘
```

## Why Kinesis Instead of Direct Lambda?

| Without Kinesis | With Kinesis |
|---|---|
| Lambda called per message | Lambda called per batch |
| Can miss messages if Lambda fails | Messages buffered safely |
| Not scalable | Handles thousands of drones |
| No ordering guarantee | Ordered per partition key |

Kinesis makes this a **production-grade** pipeline, not just a toy project.

## S3 Partitioning Strategy

Data stored as `telemetry/YYYY/MM/DD/HH/` so you can:
- Query by date range cheaply
- Use AWS Athena for SQL queries on S3
- Feed QuickSight efficiently
