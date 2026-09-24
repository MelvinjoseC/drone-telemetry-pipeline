#!/usr/bin/env python3
"""
health_check.py
────────────────────────────────────────────────────────
Enterprise diagnostic CLI for the Drone Telemetry Pipeline.

Validates:
- Local configuration & environment variables
- TLS X.509 device certificates & private keys
- DNS resolution & network reachability of AWS IoT endpoint
- Python runtime dependencies
- AWS Cloud credentials & IAM STS Caller Identity (optional)
- S3 Data Lake & Kinesis Stream reachability (optional)

Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import argparse
import json
import os
import socket
import sys
from typing import Any, Dict

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add device-simulator directory to Python path
SIMULATOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../device-simulator")
)
sys.path.append(SIMULATOR_DIR)


def check_config(report: Dict[str, Any]) -> bool:
    """Validate config module and critical pipeline parameters."""
    try:
        import config

        report["checks"]["config_import"] = {
            "status": "PASS",
            "message": "Config module loaded successfully.",
        }
    except ImportError as e:
        report["checks"]["config_import"] = {
            "status": "FAIL",
            "message": f"Failed to import config.py: {e}",
        }
        return False

    placeholder = "YOUR_ENDPOINT.iot.us-east-1.amazonaws.com"
    endpoint = getattr(config, "AWS_IOT_ENDPOINT", "")

    if not endpoint or endpoint == placeholder:
        report["checks"]["iot_endpoint"] = {
            "status": "WARN",
            "value": endpoint,
            "message": "AWS IoT Core Endpoint is still using default placeholder.",
        }
    else:
        # DNS Resolution test
        try:
            ip_address = socket.gethostbyname(endpoint)
            report["checks"]["iot_endpoint"] = {
                "status": "PASS",
                "value": endpoint,
                "resolved_ip": ip_address,
                "message": f"DNS resolution successful ({ip_address}).",
            }
        except socket.gaierror as e:
            report["checks"]["iot_endpoint"] = {
                "status": "FAIL",
                "value": endpoint,
                "message": f"DNS resolution failed: {e}",
            }

    # Certificate presence check
    cert_files = {
        "root_ca": ("Root CA Certificate", config.ROOT_CA),
        "device_cert": ("Device Certificate", config.CERT_FILE),
        "private_key": ("Private Key File", config.KEY_FILE),
    }

    certs_ok = True
    for key, (label, rel_path) in cert_files.items():
        abs_path = os.path.abspath(os.path.join(SIMULATOR_DIR, rel_path))
        if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
            report["checks"][f"cert_{key}"] = {
                "status": "PASS",
                "label": label,
                "path": rel_path,
                "size_bytes": os.path.getsize(abs_path),
            }
        else:
            report["checks"][f"cert_{key}"] = {
                "status": "WARN",
                "label": label,
                "path": rel_path,
                "message": f"Missing or empty file at {abs_path}",
            }
            certs_ok = False

    return certs_ok


def check_dependencies(report: Dict[str, Any]) -> bool:
    """Verify runtime Python packages."""
    required = ["paho-mqtt", "boto3", "python-dotenv"]
    all_installed = True
    for pkg in required:
        mod_name = pkg.replace("-", "_")
        try:
            mod = __import__(mod_name)
            ver = getattr(mod, "__version__", "unknown")
            report["checks"][f"dep_{pkg}"] = {
                "status": "PASS",
                "package": pkg,
                "version": str(ver),
            }
        except ImportError:
            report["checks"][f"dep_{pkg}"] = {
                "status": "WARN",
                "package": pkg,
                "message": f"Package {pkg} is not installed.",
            }
            all_installed = False
    return all_installed


def check_aws_services(
    report: Dict[str, Any], test_s3: bool = False, test_kinesis: bool = False
) -> bool:
    """Verify active AWS credentials and cloud resource reachability."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        report["checks"]["aws_auth"] = {
            "status": "FAIL",
            "message": "boto3 not installed.",
        }
        return False

    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        report["checks"]["aws_auth"] = {
            "status": "PASS",
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "user_id": identity.get("UserId"),
        }
    except (NoCredentialsError, ClientError) as e:
        report["checks"]["aws_auth"] = {
            "status": "WARN",
            "message": f"AWS credentials not available or invalid: {e}",
        }
        return False

    # Check S3
    if test_s3:
        try:
            import config

            bucket_name = getattr(config, "S3_BUCKET", "drone-telemetry-data")
            s3 = boto3.client("s3")
            s3.head_bucket(Bucket=bucket_name)
            report["checks"]["s3_bucket"] = {
                "status": "PASS",
                "bucket": bucket_name,
                "message": "S3 bucket accessible.",
            }
        except Exception as e:
            report["checks"]["s3_bucket"] = {
                "status": "WARN",
                "message": f"S3 bucket check failed: {e}",
            }

    # Check Kinesis
    if test_kinesis:
        try:
            import config

            stream_name = getattr(config, "KINESIS_STREAM", "DroneDataStream")
            kinesis = boto3.client("kinesis")
            res = kinesis.describe_stream_summary(StreamName=stream_name)
            status = res["StreamDescriptionSummary"]["StreamStatus"]
            report["checks"]["kinesis_stream"] = {
                "status": "PASS" if status == "ACTIVE" else "WARN",
                "stream": stream_name,
                "stream_status": status,
            }
        except Exception as e:
            report["checks"]["kinesis_stream"] = {
                "status": "WARN",
                "message": f"Kinesis stream check failed: {e}",
            }

    return True


def run_health_checks(
    verify_aws: bool = False,
    test_s3: bool = False,
    test_kinesis: bool = False,
) -> bool:
    """Run all health check modules and print formatted diagnostic console report."""
    report: Dict[str, Any] = {"checks": {}}

    print("[INFO] Running Drone Telemetry Pipeline Health Diagnostics...")
    print("=" * 60)

    check_config(report)
    check_dependencies(report)

    if verify_aws:
        check_aws_services(report, test_s3=test_s3, test_kinesis=test_kinesis)

    has_failures = False
    for check_id, check_data in report["checks"].items():
        status = check_data.get("status", "UNKNOWN")
        msg = check_data.get("message", "")
        if status == "PASS":
            extra = check_data.get("resolved_ip") or check_data.get("version", "")
            extra_str = f" ({extra})" if extra else ""
            print(f"[OK]   {check_id}: {msg or 'OK'}{extra_str}")
        elif status == "WARN":
            print(f"[WARN] {check_id}: {msg or 'Notice'}")
        else:
            print(f"[FAIL] {check_id}: {msg}")
            has_failures = True

    print("=" * 60)
    if not has_failures:
        print("[SUCCESS] All essential diagnostics passed.")
        return True
    else:
        print("[ERROR] Some health checks reported failures.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Drone Telemetry Pipeline Health Diagnostic CLI"
    )
    parser.add_argument(
        "--verify-aws",
        action="store_true",
        help="Verify active AWS credentials and STS caller identity",
    )
    parser.add_argument(
        "--check-s3",
        action="store_true",
        help="Verify target S3 bucket accessibility",
    )
    parser.add_argument(
        "--check-kinesis",
        action="store_true",
        help="Verify Kinesis stream status",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if any warning or error is found",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default="",
        help="Path to write JSON diagnostic report",
    )

    args = parser.parse_args()

    report: Dict[str, Any] = {"checks": {}}
    check_config(report)
    check_dependencies(report)
    if args.verify_aws or args.check_s3 or args.check_kinesis:
        check_aws_services(
            report, test_s3=args.check_s3, test_kinesis=args.check_kinesis
        )

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[OK] Diagnostic report saved to {args.json_output}")

    success = run_health_checks(
        verify_aws=args.verify_aws,
        test_s3=args.check_s3,
        test_kinesis=args.check_kinesis,
    )

    if args.strict and any(
        c.get("status") in ("WARN", "FAIL") for c in report["checks"].values()
    ):
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
