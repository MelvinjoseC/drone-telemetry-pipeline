# 📡 Drone Telemetry Data Schema & Protocol Specification

This document details the telemetry packet structure, validation rules, anomaly definitions, and dead-letter queue storage format for the **Drone Telemetry Data Pipeline**.

---

## 1. Telemetry Payload Schema (`version: 1.0.0`)

Incoming telemetry packets are transmitted over MQTT as UTF-8 encoded JSON payloads.

### Field Definitions

| Field | Type | Required | Range / Enum | Description |
|---|---|---|---|---|
| `drone_id` | `string` | **Yes** | `^[A-Za-z0-9_-]{3,32}$` | Unique identifier of the UAV / drone thing. |
| `timestamp` | `string` | **Yes** | ISO-8601 UTC (e.g. `2024-01-15T10:30:00Z`) | Device timestamp when telemetry was captured. |
| `latitude` | `float` | **Yes** | `[-90.0, 90.0]` | WGS84 GPS latitude (6 decimal places precision). |
| `longitude` | `float` | **Yes** | `[-180.0, 180.0]` | WGS84 GPS longitude (6 decimal places precision). |
| `altitude_m` | `float` | **Yes** | `[0.0, 5000.0]` | Altitude Above Ground Level (AGL) in meters. |
| `speed_kmh` | `float` | **Yes** | `[0.0, 400.0]` | Ground speed in kilometers per hour. |
| `heading_deg` | `float` | No | `[0.0, 360.0)` | Compass heading in degrees (0° = North, 90° = East). |
| `battery_pct` | `float` | **Yes** | `[0.0, 100.0]` | Current battery state of charge (SoC). |
| `flight_mode` | `string` | No | `TAKEOFF`, `AUTO`, `LANDING`, `HOVER`, `RTL`, `MANUAL`, `EMERGENCY` | Autopilot flight control mode. |
| `status` | `string` | No | `flying`, `grounded`, `emergency` | High-level operational status. |
| `schema_version` | `string` | Auto | `1.0.0` | Semantic version of telemetry schema. |
| `processed_at` | `string` | Auto | ISO-8601 UTC | Ingestion timestamp added by AWS Lambda processor. |
| `source` | `string` | Auto | `kinesis-lambda-pipeline` | Ingestion pipeline source provenance. |
| `has_anomaly` | `boolean` | Auto | `true` / `false` | Flag indicating whether flight limits were violated. |
| `anomalies` | `list` | Auto | List of anomaly objects | Details of detected flight boundary violations. |

---

## 2. Sample Telemetry Payload

```json
{
  "drone_id": "DRONE-001",
  "timestamp": "2024-01-15T10:30:00Z",
  "latitude": 10.8505,
  "longitude": 76.2711,
  "altitude_m": 85.5,
  "speed_kmh": 45.2,
  "heading_deg": 182.4,
  "battery_pct": 78.5,
  "flight_mode": "AUTO",
  "status": "flying",
  "schema_version": "1.0.0",
  "processed_at": "2024-01-15T10:30:01.215Z",
  "source": "kinesis-lambda-pipeline",
  "has_anomaly": false,
  "anomalies": []
}
```

---

## 3. Real-Time Flight Anomalies

The Lambda stream processor continuously tests incoming records against regulatory flight limits and safety thresholds:

| Anomaly Code | Severity | Trigger Threshold | Recommended Action |
|---|---|---|---|
| `ALTITUDE_CEILING_BREACH` | `HIGH` | `altitude_m > 120.0` | Alert operator; execute immediate descent to legal ceiling. |
| `OVERSPEED_CONDITION` | `MEDIUM` | `speed_kmh > 100.0` | Throttle motors back to cruise velocity. |
| `LOW_BATTERY_WARNING` | `WARNING` | `battery_pct <= 25.0` | Notify ground station; prepare landing coordinates. |
| `CRITICAL_BATTERY` | `CRITICAL` | `battery_pct <= 15.0` | Trigger automated Return-To-Launch (RTL). |
| `EMERGENCY_STATE_ACTIVE` | `CRITICAL` | `flight_mode == 'EMERGENCY'` | Broadcast emergency telemetry; initiate failsafe landing. |

---

## 4. Dead-Letter Queue (DLQ) Quarantine Schema

When a payload cannot be parsed or violates structural validation constraints, it is quarantined to S3 rather than stalling the Kinesis shard:

- **S3 Prefix**: `dead-letter/year=YYYY/month=MM/day=DD/dlq_{timestamp}_{sequence}.json`

### Quarantine Record Format

```json
{
  "quarantined_at": "2024-01-15T10:30:02.100Z",
  "error": "Missing required field: 'battery_pct' in payload",
  "sequence_number": "4954511000000000000001",
  "approximate_arrival_timestamp": 1705314601.5,
  "raw_payload_preview": "{\"drone_id\": \"DRONE-001\", \"latitude\": 10.85}"
}
```
