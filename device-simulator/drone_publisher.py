"""
drone_publisher.py
────────────────────────────────────────────────────────
Simulates single drone or drone fleet in flight and
publishes live telemetry data to AWS IoT Core via MQTT.

Simulated data: GPS position, altitude, speed,
                heading, battery %, flight mode

Run on: Raspberry Pi, Docker, or any Python machine
Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import argparse
import datetime
import json
import math
import os
import random
import ssl
import sys
import time
from typing import List, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import paho.mqtt.client as mqtt
from config import (
    AWS_IOT_ENDPOINT,
    CERT_FILE,
    DRONE_ID,
    KEY_FILE,
    MQTT_TOPIC,
    ROOT_CA,
    SEND_INTERVAL,
    START_LAT,
    START_LON,
)


# ── Flight simulation state ───────────────────────
class DroneSimulator:
    def __init__(
        self,
        drone_id: str = DRONE_ID,
        start_lat: float = START_LAT,
        start_lon: float = START_LON,
        tick_offset: int = 0,
    ):
        self.drone_id = drone_id
        self.lat = start_lat
        self.lon = start_lon
        self.altitude = 0.0  # meters
        self.speed = 0.0  # km/h
        self.heading = 0.0  # degrees
        self.battery = 100.0  # percentage
        self.flight_mode = "TAKEOFF"
        self.tick = tick_offset

    def update(self) -> dict:
        """Simulate realistic drone flight parameters."""
        self.tick += 1

        # ── Flight phases ─────────────────────────
        if self.tick <= 5:
            # Takeoff phase
            self.flight_mode = "TAKEOFF"
            self.altitude = min(self.altitude + 20.0, 100.0)
            self.speed = min(self.speed + 5.0, 20.0)

        elif self.tick <= 50:
            # Cruise phase — moving in a pattern
            self.flight_mode = "AUTO"
            self.altitude = 100.0 + random.uniform(-5.0, 5.0)
            self.speed = 45.0 + random.uniform(-5.0, 5.0)
            self.heading = (self.tick * 7.0) % 360.0

            # Move GPS position
            rad = math.radians(self.heading)
            self.lat += math.cos(rad) * 0.0001
            self.lon += math.sin(rad) * 0.0001

        elif self.tick <= 60:
            # Landing phase
            self.flight_mode = "LANDING"
            self.altitude = max(self.altitude - 10.0, 0.0)
            self.speed = max(self.speed - 5.0, 0.0)

        else:
            # Reset for next loop
            self.tick = 0
            self.battery = 100.0
            self.altitude = 0.0
            self.speed = 0.0
            self.flight_mode = "TAKEOFF"
            print(f"\n[CYCLE] [{self.drone_id}] New flight cycle started!\n")

        # ── Battery drain ─────────────────────────
        if self.flight_mode != "TAKEOFF":
            self.battery = max(self.battery - 0.3, 0.0)

        return {
            "drone_id": self.drone_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "altitude_m": round(self.altitude, 2),
            "speed_kmh": round(self.speed, 2),
            "heading_deg": round(self.heading, 1),
            "battery_pct": round(self.battery, 1),
            "flight_mode": self.flight_mode,
            "status": "flying" if self.altitude > 0 else "grounded",
        }


# ── Fleet Simulator ───────────────────────────────
class FleetSimulator:
    """Manages coordinated simulation for multiple autonomous drones."""

    def __init__(
        self,
        drone_ids: Optional[List[str]] = None,
        fleet_size: int = 1,
        start_lat: float = START_LAT,
        start_lon: float = START_LON,
    ):
        if drone_ids and len(drone_ids) > 0:
            self.drones = [
                DroneSimulator(
                    drone_id=d_id,
                    start_lat=start_lat + (i * 0.002),
                    start_lon=start_lon + (i * 0.002),
                    tick_offset=i * 3,
                )
                for i, d_id in enumerate(drone_ids)
            ]
        else:
            self.drones = [
                DroneSimulator(
                    drone_id=f"DRONE-{i + 1:03d}",
                    start_lat=start_lat + (i * 0.002),
                    start_lon=start_lon + (i * 0.002),
                    tick_offset=i * 3,
                )
                for i in range(max(1, fleet_size))
            ]

    def update_all(self) -> List[dict]:
        """Update and retrieve telemetry from all drones in the fleet."""
        return [drone.update() for drone in self.drones]


# ── MQTT Callbacks ────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[OK] Connected to AWS IoT Core!")
    else:
        print(f"[ERROR] Connection failed. Code: {rc}")


def on_publish(client, userdata, mid):
    pass  # silent on publish


def on_disconnect(client, userdata, rc):
    print(f"[WARN] Disconnected (rc={rc})")


# ── Setup MQTT ────────────────────────────────────
def setup_mqtt(client_id: str = DRONE_ID):
    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect
    client.tls_set(
        ca_certs=ROOT_CA,
        certfile=CERT_FILE,
        keyfile=KEY_FILE,
        tls_version=ssl.PROTOCOL_TLSv1_2,
    )
    return client


# ── CLI Argument Parser ───────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Drone Telemetry Simulator & Publisher"
    )
    parser.add_argument(
        "--drone-id",
        type=str,
        default=DRONE_ID,
        help="Primary drone identifier",
    )
    parser.add_argument(
        "--fleet-size",
        type=int,
        default=int(os.getenv("FLEET_SIZE", "1")),
        help="Number of drones to simulate concurrently in fleet mode",
    )
    parser.add_argument(
        "--drone-ids",
        type=str,
        default=os.getenv("DRONE_IDS", ""),
        help="Comma-separated list of drone IDs (overrides fleet-size)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(SEND_INTERVAL),
        help="Send interval in seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate telemetry output without connecting to AWS IoT Core",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=0,
        help="Exit after N update ticks (0 runs indefinitely)",
    )
    return parser.parse_args()


# ── Main ──────────────────────────────────────────
def main():
    args = parse_args()

    drone_ids = [d.strip() for d in args.drone_ids.split(",") if d.strip()]
    if not drone_ids and args.fleet_size <= 1:
        drone_ids = [args.drone_id]

    fleet = FleetSimulator(
        drone_ids=drone_ids,
        fleet_size=args.fleet_size,
    )

    print("[INFO] Drone Telemetry Publisher Starting...")
    print(f"   Fleet Size : {len(fleet.drones)}")
    print(f"   Drones     : {[d.drone_id for d in fleet.drones]}")
    print(f"   Endpoint   : {AWS_IOT_ENDPOINT}")
    print(f"   Topic      : {MQTT_TOPIC}")
    print(f"   Interval   : {args.interval}s")
    print(f"   Dry Run    : {args.dry_run}")
    print("-" * 50)

    client = None
    if not args.dry_run:
        client = setup_mqtt(client_id=fleet.drones[0].drone_id)
        try:
            print("[INFO] Connecting to AWS IoT Core...")
            client.connect(AWS_IOT_ENDPOINT, port=8883, keepalive=60)
            client.loop_start()
        except Exception as conn_err:
            print(f"[ERROR] MQTT Connection error: {conn_err}")
            print("   (Use --dry-run to simulate without network connection)")
            return

    tick_count = 0
    try:
        while True:
            records = fleet.update_all()
            for telemetry in records:
                payload_json = json.dumps(telemetry)
                if client:
                    client.publish(MQTT_TOPIC, payload_json, qos=1)

                # ── Console display ───────────────────
                print(
                    f"[TELEMETRY] [{telemetry['timestamp']}] {telemetry['drone_id']} | Mode: {telemetry['flight_mode']}"
                )
                print(
                    f"   GPS      : {telemetry['latitude']}, {telemetry['longitude']}"
                )
                print(f"   Altitude : {telemetry['altitude_m']} m")
                print(f"   Speed    : {telemetry['speed_kmh']} km/h")
                print(f"   Heading  : {telemetry['heading_deg']} deg")
                print(f"   Battery  : {telemetry['battery_pct']}%")
                if not args.dry_run:
                    print(f"   Sent to  : {MQTT_TOPIC}")
                print("-" * 50)

            tick_count += 1
            if args.max_ticks > 0 and tick_count >= args.max_ticks:
                print(
                    f"[INFO] Reached maximum requested ticks ({args.max_ticks}). Exiting."
                )
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[INFO] Stopping drone publisher...")
    finally:
        if client:
            client.loop_stop()
            client.disconnect()
            print("[OK] Disconnected cleanly.")


if __name__ == "__main__":
    main()
