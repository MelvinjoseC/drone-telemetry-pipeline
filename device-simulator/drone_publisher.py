"""
drone_publisher.py
────────────────────────────────────────────────────────
Simulates a drone in flight and publishes live telemetry
data to AWS IoT Core via MQTT.

Simulated data: GPS position, altitude, speed,
                heading, battery %, flight mode

Run on: Raspberry Pi OR any Python machine
Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import json
import time
import ssl
import math
import random
import datetime
import paho.mqtt.client as mqtt
from config import (
    AWS_IOT_ENDPOINT, MQTT_TOPIC, DRONE_ID,
    ROOT_CA, CERT_FILE, KEY_FILE,
    SEND_INTERVAL, START_LAT, START_LON
)

# ── Flight simulation state ───────────────────────
class DroneSimulator:
    def __init__(self):
        self.lat        = START_LAT
        self.lon        = START_LON
        self.altitude   = 0.0          # meters
        self.speed      = 0.0          # km/h
        self.heading    = 0.0          # degrees
        self.battery    = 100          # percentage
        self.flight_mode = "TAKEOFF"
        self.tick       = 0

    def update(self):
        """Simulate realistic drone flight parameters."""
        self.tick += 1

        # ── Flight phases ─────────────────────────
        if self.tick <= 5:
            # Takeoff phase
            self.flight_mode = "TAKEOFF"
            self.altitude    = min(self.altitude + 20, 100)
            self.speed       = min(self.speed + 5, 20)

        elif self.tick <= 50:
            # Cruise phase — moving in a pattern
            self.flight_mode = "AUTO"
            self.altitude    = 100 + random.uniform(-5, 5)
            self.speed       = 45 + random.uniform(-5, 5)
            self.heading     = (self.tick * 7) % 360

            # Move GPS position
            rad = math.radians(self.heading)
            self.lat += math.cos(rad) * 0.0001
            self.lon += math.sin(rad) * 0.0001

        elif self.tick <= 60:
            # Landing phase
            self.flight_mode = "LANDING"
            self.altitude    = max(self.altitude - 10, 0)
            self.speed       = max(self.speed - 5, 0)

        else:
            # Reset for next loop
            self.tick     = 0
            self.battery  = 100
            self.altitude = 0
            self.speed    = 0
            self.flight_mode = "TAKEOFF"
            print("\n🔄 New flight cycle started!\n")

        # ── Battery drain ─────────────────────────
        if self.flight_mode != "TAKEOFF":
            self.battery = max(self.battery - 0.3, 0)

        return {
            "drone_id"    : DRONE_ID,
            "timestamp"   : datetime.datetime.utcnow().isoformat() + "Z",
            "latitude"    : round(self.lat, 6),
            "longitude"   : round(self.lon, 6),
            "altitude_m"  : round(self.altitude, 2),
            "speed_kmh"   : round(self.speed, 2),
            "heading_deg" : round(self.heading, 1),
            "battery_pct" : round(self.battery, 1),
            "flight_mode" : self.flight_mode,
            "status"      : "flying" if self.altitude > 0 else "grounded"
        }

# ── MQTT Callbacks ────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core!")
    else:
        print(f"❌ Connection failed. Code: {rc}")

def on_publish(client, userdata, mid):
    pass  # silent on publish

def on_disconnect(client, userdata, rc):
    print(f"⚠️  Disconnected (rc={rc})")

# ── Setup MQTT ────────────────────────────────────
def setup_mqtt():
    client = mqtt.Client(client_id=DRONE_ID)
    client.on_connect    = on_connect
    client.on_publish    = on_publish
    client.on_disconnect = on_disconnect
    client.tls_set(
        ca_certs    = ROOT_CA,
        certfile    = CERT_FILE,
        keyfile     = KEY_FILE,
        tls_version = ssl.PROTOCOL_TLSv1_2
    )
    return client

# ── Main ──────────────────────────────────────────
def main():
    print("🚁 Drone Telemetry Publisher Starting...")
    print(f"   Drone ID : {DRONE_ID}")
    print(f"   Endpoint : {AWS_IOT_ENDPOINT}")
    print(f"   Topic    : {MQTT_TOPIC}")
    print(f"   Interval : {SEND_INTERVAL}s")
    print("─" * 50)

    drone  = DroneSimulator()
    client = setup_mqtt()

    try:
        print("🔌 Connecting to AWS IoT Core...")
        client.connect(AWS_IOT_ENDPOINT, port=8883, keepalive=60)
        client.loop_start()

        while True:
            telemetry    = drone.update()
            payload_json = json.dumps(telemetry)
            client.publish(MQTT_TOPIC, payload_json, qos=1)

            # ── Console display ───────────────────
            print(f"📡 [{telemetry['timestamp']}] Mode: {telemetry['flight_mode']}")
            print(f"   📍 GPS      : {telemetry['latitude']}, {telemetry['longitude']}")
            print(f"   ↕️  Altitude : {telemetry['altitude_m']} m")
            print(f"   💨 Speed    : {telemetry['speed_kmh']} km/h")
            print(f"   🧭 Heading  : {telemetry['heading_deg']}°")
            print(f"   🔋 Battery  : {telemetry['battery_pct']}%")
            print(f"   📤 Sent to  : {MQTT_TOPIC}")
            print("─" * 50)

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n🛑 Stopping drone publisher...")
        client.loop_stop()
        client.disconnect()
        print("✅ Disconnected cleanly.")

if __name__ == "__main__":
    main()
