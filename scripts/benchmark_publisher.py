"""
benchmark_publisher.py
────────────────────────────────────────────────────────
High-throughput telemetry benchmark and load test generator.

Simulates thousands of concurrent drone telemetry messages,
evaluating serialization overhead, throughput (records/sec),
and latency percentiles (p50, p90, p99).

Author: Melvin Chacko Jose
────────────────────────────────────────────────────────
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add lambda & simulator directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(BASE_DIR, "device-simulator"))
sys.path.append(os.path.join(BASE_DIR, "lambda"))

try:
    from drone_publisher import DroneSimulator
    from telemetry_model import validate_telemetry
except ImportError as err:
    print(f"[ERROR] Failed to import pipeline modules: {err}")
    sys.exit(1)


def generate_worker_batch(
    worker_id: int, records_per_worker: int, validate: bool = True
) -> Dict[str, Any]:
    """Generate and benchmark a batch of telemetry records."""
    drone = DroneSimulator(
        drone_id=f"DRONE-BM-{worker_id:03d}",
        start_lat=10.8505 + (worker_id * 0.001),
        start_lon=76.2711 + (worker_id * 0.001),
    )

    latencies_ms: List[float] = []
    total_bytes = 0
    valid_count = 0

    t_start = time.perf_counter()
    for _ in range(records_per_worker):
        rec_start = time.perf_counter()
        data = drone.update()
        if validate:
            data = validate_telemetry(data)
            valid_count += 1

        payload_bytes = json.dumps(data).encode("utf-8")
        rec_end = time.perf_counter()

        total_bytes += len(payload_bytes)
        latencies_ms.append((rec_end - rec_start) * 1000.0)

    elapsed = time.perf_counter() - t_start

    return {
        "worker_id": worker_id,
        "count": records_per_worker,
        "valid_count": valid_count,
        "total_bytes": total_bytes,
        "elapsed_sec": elapsed,
        "latencies_ms": latencies_ms,
    }


def run_benchmark(
    total_records: int = 10000,
    concurrency: int = 4,
    validate: bool = True,
) -> Dict[str, Any]:
    """Run full load benchmark across concurrent worker threads."""
    records_per_worker = total_records // concurrency
    actual_records = records_per_worker * concurrency

    print("[INFO] Starting Drone Telemetry Ingestion Benchmark...")
    print(f"   Target Records : {actual_records:,}")
    print(f"   Worker Threads : {concurrency}")
    print(f"   Validation     : {'Enabled' if validate else 'Disabled'}")
    print("-" * 60)

    overall_start = time.perf_counter()
    all_latencies: List[float] = []
    total_bytes = 0
    total_valid = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(generate_worker_batch, wid, records_per_worker, validate)
            for wid in range(concurrency)
        ]

        for fut in futures:
            res = fut.result()
            all_latencies.extend(res["latencies_ms"])
            total_bytes += res["total_bytes"]
            total_valid += res["valid_count"]

    overall_elapsed = time.perf_counter() - overall_start
    all_latencies.sort()

    p50 = all_latencies[int(len(all_latencies) * 0.50)] if all_latencies else 0.0
    p90 = all_latencies[int(len(all_latencies) * 0.90)] if all_latencies else 0.0
    p99 = all_latencies[int(len(all_latencies) * 0.99)] if all_latencies else 0.0

    throughput_rps = actual_records / overall_elapsed if overall_elapsed > 0 else 0
    throughput_mb_s = (
        (total_bytes / (1024 * 1024)) / overall_elapsed if overall_elapsed > 0 else 0
    )

    results = {
        "total_records": actual_records,
        "valid_records": total_valid,
        "total_bytes": total_bytes,
        "elapsed_seconds": round(overall_elapsed, 4),
        "throughput_records_per_sec": round(throughput_rps, 1),
        "throughput_mb_per_sec": round(throughput_mb_s, 2),
        "latency_p50_ms": round(p50, 4),
        "latency_p90_ms": round(p90, 4),
        "latency_p99_ms": round(p99, 4),
    }

    print("\n" + "=" * 60)
    print("           DRONE TELEMETRY BENCHMARK REPORT")
    print("=" * 60)
    print(f"Total Records Processed   : {results['total_records']:,}")
    print(f"Validation Accuracy       : {(total_valid / actual_records) * 100:.1f}%")
    print(f"Total Data Generated      : {total_bytes / 1024:.1f} KB")
    print(f"Elapsed Wall Time         : {results['elapsed_seconds']} s")
    print(
        f"Throughput                :"
        f" {results['throughput_records_per_sec']:,} rec/sec"
        f" ({results['throughput_mb_per_sec']} MB/s)"
    )
    print(f"Latency (p50)             : {results['latency_p50_ms']} ms")
    print(f"Latency (p90)             : {results['latency_p90_ms']} ms")
    print(f"Latency (p99)             : {results['latency_p99_ms']} ms")
    print("=" * 60 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Telemetry Publisher Throughput & Latency Benchmark"
    )
    parser.add_argument(
        "--records",
        type=int,
        default=5000,
        help="Total number of records to generate",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of concurrent worker threads",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Disable schema validation during benchmarking",
    )
    parser.add_argument(
        "--json-output",
        type=str,
        default="",
        help="Optional path to write benchmark results JSON",
    )

    args = parser.parse_args()
    results = run_benchmark(
        total_records=args.records,
        concurrency=args.threads,
        validate=not args.no_validate,
    )

    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[OK] Saved benchmark report to {args.json_output}")


if __name__ == "__main__":
    main()
