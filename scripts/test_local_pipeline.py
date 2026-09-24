#!/usr/bin/env python3
"""
test_local_pipeline.py
────────────────────────────────────────────────────────
Offline / LocalStack end-to-end integration test runner.

Simulates an end-to-end flow:
1. Generates telemetry using DroneSimulator
2. Packages payload into simulated Kinesis event records
3. Executes lambda_handler
4. Verifies S3 ingestion or quarantine outputs

Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import base64
import json
import os
import sys
from unittest.mock import MagicMock

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Setup paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(BASE_DIR, "device-simulator"))
sys.path.append(os.path.join(BASE_DIR, "lambda"))

import lambda_function  # noqa: E402
from drone_publisher import DroneSimulator  # noqa: E402


def run_pipeline_e2e_simulation():
    print("[INFO] Starting Offline End-to-End Pipeline Verification...")
    print("=" * 60)

    # 1. Mock S3 client to verify put_object calls
    mock_s3 = MagicMock()
    lambda_function.s3 = mock_s3

    # 2. Generate nominal telemetry
    drone = DroneSimulator(drone_id="DRONE-E2E-001")
    telemetry_records = [drone.update() for _ in range(5)]
    print(f"[OK] Generated {len(telemetry_records)} sample telemetry points.")

    # 3. Create simulated Kinesis event
    kinesis_records = []
    for idx, item in enumerate(telemetry_records):
        data_bytes = json.dumps(item).encode("utf-8")
        encoded_b64 = base64.b64encode(data_bytes).decode("utf-8")
        kinesis_records.append(
            {
                "kinesis": {
                    "data": encoded_b64,
                    "sequenceNumber": f"seq-{idx + 1:04d}",
                    "approximateArrivalTimestamp": 1700000000.0 + idx,
                }
            }
        )

    # Add 1 poisoned/malformed record to test quarantine
    kinesis_records.append(
        {
            "kinesis": {
                "data": base64.b64encode(b"poison-pill-bad-json").decode("utf-8"),
                "sequenceNumber": "seq-9999",
                "approximateArrivalTimestamp": 1700000010.0,
            }
        }
    )

    event = {"Records": kinesis_records}
    print(
        f"[INFO] Invoking lambda_handler with {len(kinesis_records)} Kinesis records (including 1 poison pill)..."
    )

    result = lambda_function.lambda_handler(event, None)
    print(f"[INFO] Execution returned: {result}")

    # 4. Verify Assertions
    # 5 successful records written + 1 quarantined record written to S3 = 6 calls
    call_count = mock_s3.put_object.call_count
    print(f"[OK] Total S3 put_object invocations: {call_count}")

    if call_count == 6:
        print(
            "[SUCCESS] All 5 telemetry records stored and 1 poison-pill quarantined successfully!"
        )
        return True
    else:
        print(f"[ERROR] Expected 6 S3 put_object calls, got {call_count}")
        return False


if __name__ == "__main__":
    ok = run_pipeline_e2e_simulation()
    sys.exit(0 if ok else 1)
