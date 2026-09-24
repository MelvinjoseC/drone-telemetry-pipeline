"""
anomaly_detector.py
────────────────────────────────────────────────────────
Real-time telemetry stream anomaly detection engine for
unmanned aerial vehicles (UAVs / drones).

Evaluates safety ceilings, power limits, speed thresholds,
and emergency flight states.

Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import os
from typing import Any, Dict, List

# Configurable regulatory and safety thresholds
DEFAULT_MAX_ALTITUDE = float(os.environ.get("MAX_ALTITUDE_METERS", "120.0"))
DEFAULT_MAX_SPEED = float(os.environ.get("MAX_SPEED_KMH", "100.0"))
DEFAULT_LOW_BATTERY = float(os.environ.get("LOW_BATTERY_THRESHOLD", "25.0"))
DEFAULT_CRITICAL_BATTERY = float(os.environ.get("CRITICAL_BATTERY_THRESHOLD", "15.0"))


def detect_anomalies(
    payload: Dict[str, Any],
    max_altitude: float = DEFAULT_MAX_ALTITUDE,
    max_speed: float = DEFAULT_MAX_SPEED,
    low_battery: float = DEFAULT_LOW_BATTERY,
    critical_battery: float = DEFAULT_CRITICAL_BATTERY,
) -> List[Dict[str, Any]]:
    """
    Evaluate telemetry against regulatory safety boundaries and flight limits.

    Returns a list of anomaly incident descriptors (if any).
    """
    anomalies: List[Dict[str, Any]] = []

    altitude = float(payload.get("altitude_m", 0.0))
    speed = float(payload.get("speed_kmh", 0.0))
    battery = float(payload.get("battery_pct", 100.0))
    flight_mode = str(payload.get("flight_mode", "AUTO")).upper()
    status = str(payload.get("status", "flying")).lower()

    # 1. Regulatory Altitude Ceiling Breach (FAA / DGCA 120m / 400ft AGL)
    if altitude > max_altitude:
        anomalies.append(
            {
                "code": "ALTITUDE_CEILING_BREACH",
                "severity": "HIGH",
                "message": (
                    f"Altitude {altitude}m exceeds legal regulatory ceiling of"
                    f" {max_altitude}m"
                ),
                "metric_value": altitude,
                "threshold": max_altitude,
            }
        )

    # 2. Overspeed Condition
    if speed > max_speed:
        anomalies.append(
            {
                "code": "OVERSPEED_CONDITION",
                "severity": "MEDIUM",
                "message": (
                    f"Ground speed {speed} km/h exceeds maximum safe operational limit of"
                    f" {max_speed} km/h"
                ),
                "metric_value": speed,
                "threshold": max_speed,
            }
        )

    # 3. Battery Degradation & Critical Low Power
    if battery <= critical_battery:
        anomalies.append(
            {
                "code": "CRITICAL_BATTERY",
                "severity": "CRITICAL",
                "message": (
                    f"Battery at {battery}% is below emergency return-to-home"
                    f" threshold of {critical_battery}%"
                ),
                "metric_value": battery,
                "threshold": critical_battery,
            }
        )
    elif battery <= low_battery:
        anomalies.append(
            {
                "code": "LOW_BATTERY_WARNING",
                "severity": "WARNING",
                "message": (
                    f"Battery at {battery}% requires immediate landing"
                    f" preparation (threshold {low_battery}%)"
                ),
                "metric_value": battery,
                "threshold": low_battery,
            }
        )

    # 4. Emergency State
    if flight_mode == "EMERGENCY" or status == "emergency":
        anomalies.append(
            {
                "code": "EMERGENCY_STATE_ACTIVE",
                "severity": "CRITICAL",
                "message": f"Drone is in an active emergency state (mode={flight_mode}, status={status})",
                "metric_value": 1.0,
                "threshold": 0.0,
            }
        )

    return anomalies
