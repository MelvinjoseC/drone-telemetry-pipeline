import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../lambda")))

from telemetry_model import (  # noqa: E402
    TelemetryValidationError,
    validate_telemetry,
    validate_timestamp,
)


class TestTelemetryModel(unittest.TestCase):
    def setUp(self):
        self.valid_payload = {
            "drone_id": "DRONE-001",
            "timestamp": "2024-01-15T10:30:00Z",
            "latitude": 10.8505,
            "longitude": 76.2711,
            "altitude_m": 85.5,
            "speed_kmh": 42.0,
            "heading_deg": 180.0,
            "battery_pct": 92.5,
            "flight_mode": "AUTO",
            "status": "flying",
        }

    def test_valid_payload_sanitization(self):
        sanitized = validate_telemetry(self.valid_payload)
        self.assertEqual(sanitized["drone_id"], "DRONE-001")
        self.assertEqual(sanitized["latitude"], 10.8505)
        self.assertEqual(sanitized["schema_version"], "1.0.0")

    def test_invalid_drone_id(self):
        bad_payload = dict(self.valid_payload, drone_id="!")
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_latitude_out_of_bounds(self):
        bad_payload = dict(self.valid_payload, latitude=95.0)
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_longitude_out_of_bounds(self):
        bad_payload = dict(self.valid_payload, longitude=-195.0)
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_altitude_negative(self):
        bad_payload = dict(self.valid_payload, altitude_m=-10.0)
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_speed_negative(self):
        bad_payload = dict(self.valid_payload, speed_kmh=-5.0)
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_battery_range(self):
        bad_payload = dict(self.valid_payload, battery_pct=110.0)
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

        bad_payload2 = dict(self.valid_payload, battery_pct=-1.0)
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload2)

    def test_missing_required_fields(self):
        bad_payload = dict(self.valid_payload)
        del bad_payload["latitude"]
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_invalid_timestamp(self):
        bad_payload = dict(self.valid_payload, timestamp="invalid-date")
        with self.assertRaises(TelemetryValidationError):
            validate_telemetry(bad_payload)

    def test_validate_timestamp_helper(self):
        ts = validate_timestamp("2024-06-01T12:00:00Z")
        self.assertEqual(ts, "2024-06-01T12:00:00Z")
        with self.assertRaises(TelemetryValidationError):
            validate_timestamp("")


if __name__ == "__main__":
    unittest.main()
