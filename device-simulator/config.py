# ─────────────────────────────────────────────────
#  config.py — Drone Telemetry Pipeline Config
#  Edit these values with your AWS IoT settings or
#  define them in a .env file.
# ─────────────────────────────────────────────────

import os
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

# AWS IoT Core endpoint
# Find: AWS Console → IoT Core → Settings
AWS_IOT_ENDPOINT = os.getenv("AWS_IOT_ENDPOINT", "YOUR_ENDPOINT.iot.us-east-1.amazonaws.com")

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# MQTT Topic
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "drones/telemetry")

# Drone device name (Thing Name in AWS IoT)
DRONE_ID = os.getenv("DRONE_ID", "DRONE-001")

# Certificate paths
CERT_DIR  = os.getenv("CERT_DIR", "./certs")
ROOT_CA   = os.getenv("ROOT_CA", f"{CERT_DIR}/AmazonRootCA1.pem")
CERT_FILE = os.getenv("CERT_FILE", f"{CERT_DIR}/device-certificate.pem.crt")
KEY_FILE  = os.getenv("KEY_FILE", f"{CERT_DIR}/private.pem.key")

# Simulation settings
SEND_INTERVAL = int(os.getenv("SEND_INTERVAL", "2"))       # Send telemetry every 2 seconds
SIMULATE_FLIGHT = os.getenv("SIMULATE_FLIGHT", "True").lower() in ("true", "1", "t", "y", "yes")

# Starting GPS coordinates (Kochi, Kerala)
START_LAT = float(os.getenv("START_LAT", "10.8505"))
START_LON = float(os.getenv("START_LON", "76.2711"))

# S3 bucket name (create this in AWS)
S3_BUCKET = os.getenv("S3_BUCKET", "drone-telemetry-data")

# Kinesis stream name
KINESIS_STREAM = os.getenv("KINESIS_STREAM", "DroneDataStream")
