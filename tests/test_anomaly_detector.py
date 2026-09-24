import os
import sys
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../lambda")))

from anomaly_detector import detect_anomalies  # noqa: E402


class TestAnomalyDetector(unittest.TestCase):
    def test_nominal_flight_no_anomalies(self):
        payload = {
            "altitude_m": 80.0,
            "speed_kmh": 45.0,
            "battery_pct": 85.0,
            "flight_mode": "AUTO",
            "status": "flying",
        }
        anomalies = detect_anomalies(payload)
        self.assertEqual(len(anomalies), 0)

    def test_altitude_ceiling_breach(self):
        payload = {
            "altitude_m": 135.0,  # exceeds 120m
            "speed_kmh": 45.0,
            "battery_pct": 85.0,
            "flight_mode": "AUTO",
        }
        anomalies = detect_anomalies(payload, max_altitude=120.0)
        codes = [a["code"] for a in anomalies]
        self.assertIn("ALTITUDE_CEILING_BREACH", codes)
        self.assertEqual(anomalies[0]["severity"], "HIGH")

    def test_low_battery_and_critical_battery(self):
        # Low battery
        low_payload = {
            "altitude_m": 50.0,
            "speed_kmh": 30.0,
            "battery_pct": 22.0,  # between 15% and 25%
        }
        low_anomalies = detect_anomalies(low_payload)
        self.assertEqual(low_anomalies[0]["code"], "LOW_BATTERY_WARNING")
        self.assertEqual(low_anomalies[0]["severity"], "WARNING")

        # Critical battery
        crit_payload = {
            "altitude_m": 50.0,
            "speed_kmh": 30.0,
            "battery_pct": 11.0,  # below 15%
        }
        crit_anomalies = detect_anomalies(crit_payload)
        self.assertEqual(crit_anomalies[0]["code"], "CRITICAL_BATTERY")
        self.assertEqual(crit_anomalies[0]["severity"], "CRITICAL")

    def test_overspeed_detection(self):
        payload = {
            "altitude_m": 50.0,
            "speed_kmh": 115.0,  # exceeds 100 km/h
            "battery_pct": 60.0,
        }
        anomalies = detect_anomalies(payload, max_speed=100.0)
        codes = [a["code"] for a in anomalies]
        self.assertIn("OVERSPEED_CONDITION", codes)

    def test_emergency_state_detection(self):
        payload = {
            "altitude_m": 40.0,
            "speed_kmh": 20.0,
            "battery_pct": 50.0,
            "flight_mode": "EMERGENCY",
        }
        anomalies = detect_anomalies(payload)
        codes = [a["code"] for a in anomalies]
        self.assertIn("EMERGENCY_STATE_ACTIVE", codes)


if __name__ == "__main__":
    unittest.main()
