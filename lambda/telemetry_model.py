"""
telemetry_model.py
────────────────────────────────────────────────────────
Defines strict schema validation, type enforcement, and
boundary constraints for incoming drone telemetry records.

Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Set

# Supported flight modes and operational statuses
VALID_FLIGHT_MODES: Set[str] = {
    "TAKEOFF",
    "AUTO",
    "LANDING",
    "HOVER",
    "RTL",
    "MANUAL",
    "EMERGENCY",
}

VALID_STATUSES: Set[str] = {
    "flying",
    "grounded",
    "emergency",
}

DRONE_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
SCHEMA_VERSION = "1.0.0"


class TelemetryValidationError(ValueError):
    """Raised when incoming telemetry data fails schema or boundary validation."""

    pass


def validate_timestamp(ts: Any) -> str:
    """Validate ISO-8601 UTC timestamp string."""
    if not isinstance(ts, str) or not ts.strip():
        raise TelemetryValidationError("Timestamp must be a non-empty string.")

    normalized = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            # Assume UTC if missing timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception as e:
        raise TelemetryValidationError(f"Invalid ISO-8601 timestamp '{ts}': {e}") from e


def validate_telemetry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize incoming telemetry payload against domain constraints.

    Returns the sanitized, validated payload dictionary.
    Raises TelemetryValidationError on schema violation.
    """
    if not isinstance(payload, dict):
        raise TelemetryValidationError(
            f"Payload must be a JSON object, got {type(payload).__name__}"
        )

    required_fields = [
        "drone_id",
        "timestamp",
        "latitude",
        "longitude",
        "altitude_m",
        "speed_kmh",
        "battery_pct",
    ]

    for field in required_fields:
        if field not in payload or payload[field] is None:
            raise TelemetryValidationError(
                f"Missing required field: '{field}' in payload"
            )

    # 1. Drone ID validation
    drone_id = str(payload["drone_id"]).strip()
    if not DRONE_ID_REGEX.match(drone_id):
        raise TelemetryValidationError(
            f"Invalid drone_id '{drone_id}'. Must be 3-32 alphanumeric characters, dashes, or underscores."
        )

    # 2. Timestamp validation
    validated_ts = validate_timestamp(payload["timestamp"])

    # 3. GPS Coordinates validation
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (ValueError, TypeError) as e:
        raise TelemetryValidationError(
            f"Latitude and longitude must be numeric: {e}"
        ) from e

    if not (-90.0 <= latitude <= 90.0):
        raise TelemetryValidationError(
            f"Latitude {latitude} out of bounds [-90.0, 90.0]"
        )
    if not (-180.0 <= longitude <= 180.0):
        raise TelemetryValidationError(
            f"Longitude {longitude} out of bounds [-180.0, 180.0]"
        )

    # 4. Altitude validation (in meters)
    try:
        altitude_m = float(payload["altitude_m"])
    except (ValueError, TypeError) as e:
        raise TelemetryValidationError(f"altitude_m must be numeric: {e}") from e

    if altitude_m < 0.0 or altitude_m > 5000.0:
        raise TelemetryValidationError(
            f"altitude_m {altitude_m} out of realistic range [0.0, 5000.0]"
        )

    # 5. Speed validation (in km/h)
    try:
        speed_kmh = float(payload["speed_kmh"])
    except (ValueError, TypeError) as e:
        raise TelemetryValidationError(f"speed_kmh must be numeric: {e}") from e

    if speed_kmh < 0.0 or speed_kmh > 400.0:
        raise TelemetryValidationError(
            f"speed_kmh {speed_kmh} out of realistic range [0.0, 400.0]"
        )

    # 6. Battery percentage validation
    try:
        battery_pct = float(payload["battery_pct"])
    except (ValueError, TypeError) as e:
        raise TelemetryValidationError(f"battery_pct must be numeric: {e}") from e

    if not (0.0 <= battery_pct <= 100.0):
        raise TelemetryValidationError(
            f"battery_pct {battery_pct} out of range [0.0, 100.0]"
        )

    # 7. Optional Heading validation
    heading_deg = payload.get("heading_deg", 0.0)
    try:
        heading_deg = float(heading_deg) % 360.0
    except (ValueError, TypeError):
        heading_deg = 0.0

    # 8. Flight mode & status normalization
    flight_mode = str(payload.get("flight_mode", "AUTO")).upper()
    if flight_mode not in VALID_FLIGHT_MODES:
        flight_mode = "AUTO"

    status = str(
        payload.get("status", "flying" if altitude_m > 0 else "grounded")
    ).lower()
    if status not in VALID_STATUSES:
        status = "flying" if altitude_m > 0 else "grounded"

    sanitized = {
        "drone_id": drone_id,
        "timestamp": validated_ts,
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "altitude_m": round(altitude_m, 2),
        "speed_kmh": round(speed_kmh, 2),
        "heading_deg": round(heading_deg, 1),
        "battery_pct": round(battery_pct, 1),
        "flight_mode": flight_mode,
        "status": status,
        "schema_version": SCHEMA_VERSION,
    }

    return sanitized
