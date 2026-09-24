import os
import sys
import json
import base64
import unittest
from unittest.mock import MagicMock, patch

# Add lambda directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../lambda")))

import lambda_function


class TestLambdaFunction(unittest.TestCase):
    def test_build_s3_key(self):
        # Test standard ISO timestamp parsing (Hive partition style)
        key = lambda_function.build_s3_key("DRONE-001", "2024-01-15T10:30:00Z")
        self.assertEqual(
            key,
            "telemetry/year=2024/month=01/day=15/hour=10/DRONE-001_2024-01-15T10-30-00Z.json",
        )

        # Test fallback on invalid timestamp
        key_fallback = lambda_function.build_s3_key("DRONE-001", "invalid-time")
        self.assertTrue(key_fallback.startswith("telemetry/year="))
        self.assertTrue(key_fallback.endswith(".json"))

    def test_process_record_success(self):
        # Create a valid payload
        payload = {
            "drone_id": "DRONE-001",
            "timestamp": "2024-01-15T10:30:00Z",
            "latitude": 10.8505,
            "longitude": 76.2711,
            "altitude_m": 120.5,
            "speed_kmh": 45.2,
            "battery_pct": 78,
        }
        raw_bytes = json.dumps(payload).encode("utf-8")
        encoded = base64.b64encode(raw_bytes).decode("utf-8")

        record = {"kinesis": {"data": encoded}}

        processed = lambda_function.process_record(record)
        self.assertEqual(processed["drone_id"], "DRONE-001")
        self.assertEqual(processed["source"], "kinesis-lambda-pipeline")
        self.assertIn("processed_at", processed)

    def test_process_record_missing_field(self):
        # Payload missing required "battery_pct"
        payload = {
            "drone_id": "DRONE-001",
            "timestamp": "2024-01-15T10:30:00Z",
            "latitude": 10.8505,
            "longitude": 76.2711,
            "altitude_m": 120.5,
            "speed_kmh": 45.2,
        }
        raw_bytes = json.dumps(payload).encode("utf-8")
        encoded = base64.b64encode(raw_bytes).decode("utf-8")

        record = {"kinesis": {"data": encoded}}

        with self.assertRaises(ValueError):
            lambda_function.process_record(record)

    @patch("lambda_function.s3")
    def test_store_to_s3(self, mock_s3):
        payload = {
            "drone_id": "DRONE-001",
            "timestamp": "2024-01-15T10:30:00Z",
            "latitude": 10.8505,
            "longitude": 76.2711,
            "altitude_m": 120.5,
            "speed_kmh": 45.2,
            "battery_pct": 78,
        }

        # Test default bucket name config
        key = lambda_function.store_to_s3(payload)
        mock_s3.put_object.assert_called_once()
        call_kwargs = mock_s3.put_object.call_args[1]
        self.assertEqual(call_kwargs["Bucket"], "drone-telemetry-data")
        self.assertEqual(call_kwargs["Key"], key)
        self.assertIn("DRONE-001", call_kwargs["Body"])

    def test_lambda_handler(self):
        # Directly monkeypatch functions to isolate handler test
        original_process = lambda_function.process_record
        original_store = lambda_function.store_to_s3

        try:
            lambda_function.process_record = MagicMock(
                return_value={
                    "drone_id": "DRONE-001",
                    "altitude_m": 100,
                    "speed_kmh": 40,
                    "battery_pct": 80,
                    "timestamp": "2024-01-15",
                }
            )
            lambda_function.store_to_s3 = MagicMock(return_value="telemetry/path.json")

            event = {
                "Records": [
                    {"kinesis": {"data": "dummy1", "sequenceNumber": "seq1"}},
                    {"kinesis": {"data": "dummy2", "sequenceNumber": "seq2"}},
                ]
            }

            result = lambda_function.lambda_handler(event, None)

            # Verify batchItemFailures is empty for success
            self.assertEqual(result["batchItemFailures"], [])
            self.assertEqual(lambda_function.process_record.call_count, 2)
            self.assertEqual(lambda_function.store_to_s3.call_count, 2)

            # Test failure case
            lambda_function.process_record.side_effect = Exception("Mock Error")
            result_error = lambda_function.lambda_handler(event, None)

            # Verify batchItemFailures returns the failed sequences
            self.assertEqual(len(result_error["batchItemFailures"]), 2)
            self.assertEqual(
                result_error["batchItemFailures"][0]["itemIdentifier"], "seq1"
            )
            self.assertEqual(
                result_error["batchItemFailures"][1]["itemIdentifier"], "seq2"
            )

        finally:
            # Restore original state
            lambda_function.process_record = original_process
            lambda_function.store_to_s3 = original_store

    @patch("lambda_function.s3")
    def test_quarantine_record(self, mock_s3):
        record = {
            "kinesis": {
                "data": base64.b64encode(b"malformed json payload").decode("utf-8"),
                "sequenceNumber": "seq-999",
                "approximateArrivalTimestamp": 1700000000.0,
            }
        }
        dlq_key = lambda_function.quarantine_record(
            record, "JSONDecodeError: invalid format", "seq-999"
        )
        self.assertTrue(dlq_key.startswith("dead-letter/year="))
        self.assertTrue(dlq_key.endswith(".json"))
        mock_s3.put_object.assert_called_once()
        kwargs = mock_s3.put_object.call_args[1]
        self.assertEqual(kwargs["Bucket"], "drone-telemetry-data")
        self.assertIn("seq-999", kwargs["Body"])
        self.assertIn("JSONDecodeError", kwargs["Body"])

    @patch("lambda_function.s3")
    def test_store_batch_to_s3(self, mock_s3):
        payloads = [
            {
                "drone_id": "DRONE-001",
                "timestamp": "2024-01-15T10:30:00Z",
                "latitude": 10.8505,
                "longitude": 76.2711,
                "altitude_m": 100.0,
                "speed_kmh": 40.0,
                "battery_pct": 90.0,
            },
            {
                "drone_id": "DRONE-002",
                "timestamp": "2024-01-15T10:30:05Z",
                "latitude": 10.8510,
                "longitude": 76.2715,
                "altitude_m": 105.0,
                "speed_kmh": 42.0,
                "battery_pct": 89.0,
            },
        ]
        keys = lambda_function.store_batch_to_s3(payloads)
        self.assertEqual(len(keys), 1)
        self.assertTrue(
            keys[0].startswith("telemetry/year=2024/month=01/day=15/hour=10/")
        )
        self.assertTrue(keys[0].endswith(".ndjson"))
        mock_s3.put_object.assert_called_once()
        body = mock_s3.put_object.call_args[1]["Body"].decode("utf-8")
        lines = [line for line in body.strip().split("\n") if line]
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
