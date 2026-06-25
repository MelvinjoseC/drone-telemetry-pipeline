#!/usr/bin/env python3
"""
health_check.py
────────────────────────────────────────────────────────
Validates configuration, certificate existence, and DNS
resolution of the AWS IoT Core endpoint.
────────────────────────────────────────────────────────
"""

import os
import sys
import socket

# Add device-simulator directory to Python path
SIMULATOR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../device-simulator'))
sys.path.append(SIMULATOR_DIR)

def run_health_checks():
    print("[INFO] Running Drone Telemetry Pipeline Health Checks...")
    print("=" * 60)
    
    all_passed = True

    # 1. Verify Import of config.py
    try:
        import config
        print("[OK] Config module imported successfully.")
    except ImportError as e:
        print(f"[ERROR] Failed to import config.py: {e}")
        return False

    # 2. Check AWS IoT Core Endpoint Configuration
    placeholder = "YOUR_ENDPOINT.iot.us-east-1.amazonaws.com"
    endpoint = getattr(config, "AWS_IOT_ENDPOINT", "")
    
    if not endpoint or endpoint == placeholder:
        print("[ERROR] AWS IoT Core Endpoint is NOT configured in config.py.")
        print(f"        Current value: '{endpoint}'")
        all_passed = False
    else:
        print(f"[OK] AWS IoT Core Endpoint is configured: {endpoint}")

        # 3. Verify DNS Resolution of Endpoint
        try:
            # Resolve DNS
            ip_address = socket.gethostbyname(endpoint)
            print(f"[OK] DNS resolution successful for {endpoint} -> {ip_address}")
        except socket.gaierror as e:
            print(f"[ERROR] DNS resolution failed for {endpoint}: {e}")
            print("        Please check your internet connection or the endpoint spelling.")
            all_passed = False

    # 4. Check Certificate Files Existence
    cert_files = {
        "Root CA Certificate": config.ROOT_CA,
        "Device Certificate": config.CERT_FILE,
        "Private Key File": config.KEY_FILE
    }

    for name, rel_path in cert_files.items():
        # Resolve path relative to device-simulator directory
        abs_path = os.path.abspath(os.path.join(SIMULATOR_DIR, rel_path))
        if os.path.exists(abs_path):
            print(f"[OK] Found {name}: {rel_path}")
        else:
            print(f"[ERROR] Missing {name}: {rel_path}")
            print(f"        Expected path: {abs_path}")
            all_passed = False

    # 5. Check Python dependencies
    required_packages = ["paho-mqtt", "boto3"]
    for pkg in required_packages:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"[OK] Python package '{pkg}' is installed.")
        except ImportError:
            print(f"[WARN] Python package '{pkg}' is NOT installed.")
            print(f"       Run 'pip install -r device-simulator/requirements.txt' or 'pip install {pkg}'")

    print("=" * 60)
    if all_passed:
        print("[SUCCESS] All checks passed! Pipeline configuration is healthy.")
        return True
    else:
        print("[ERROR] Some health checks failed. Please fix the issues detailed above.")
        return False

if __name__ == "__main__":
    success = run_health_checks()
    # We don't exit with 1 here for config checks that fail on placeholder config files
    # since we expect fresh checkouts to have defaults, but we return status code appropriately.
    sys.exit(0 if success else 1)
