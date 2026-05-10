# ─────────────────────────────────────────────────
#  config.py — Drone Telemetry Pipeline Config
#  Edit these values with your AWS IoT settings
# ─────────────────────────────────────────────────

# AWS IoT Core endpoint
# Find: AWS Console → IoT Core → Settings
AWS_IOT_ENDPOINT = "YOUR_ENDPOINT.iot.us-east-1.amazonaws.com"

# AWS Region
AWS_REGION = "us-east-1"

# MQTT Topic
MQTT_TOPIC = "drones/telemetry"

# Drone device name (Thing Name in AWS IoT)
DRONE_ID = "DRONE-001"

# Certificate paths
CERT_DIR  = "./certs"
ROOT_CA   = f"{CERT_DIR}/AmazonRootCA1.pem"
CERT_FILE = f"{CERT_DIR}/device-certificate.pem.crt"
KEY_FILE  = f"{CERT_DIR}/private.pem.key"

# Simulation settings
SEND_INTERVAL = 2       # Send telemetry every 2 seconds
SIMULATE_FLIGHT = True  # True = simulate GPS movement

# Starting GPS coordinates (Kochi, Kerala)
START_LAT = 10.8505
START_LON = 76.2711

# S3 bucket name (create this in AWS)
S3_BUCKET = "drone-telemetry-data"

# Kinesis stream name
KINESIS_STREAM = "DroneDataStream"
