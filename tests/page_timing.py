"""Page load test: requests the main page N times and reports response times.

Usage (inside the app container):
    python /srv/tests/page_timing.py --label stage1_local
    python /srv/tests/page_timing.py --label stage2_ec2 --url http://localhost:8000/ --runs 100
"""
import argparse
import csv
import os
import statistics
import time
import urllib.request
from datetime import datetime


def p95(values):
    values = sorted(values)
    return values[max(0, int(round(0.95 * len(values))) - 1)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--url", default="http://localhost:8000/")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "results"))
    args = parser.parse_args()

    urllib.request.urlopen(args.url).read()  # warm-up
    times = []
    for _ in range(args.runs):
        start = time.perf_counter()
        with urllib.request.urlopen(args.url) as resp:
            resp.read()
        times.append((time.perf_counter() - start) * 1000)

    row = {
        "label": args.label, "url": args.url, "runs": args.runs,
        "median_ms": round(statistics.median(times), 3),
        "p95_ms": round(p95(times), 3),
        "mean_ms": round(statistics.mean(times), 3),
        "min_ms": round(min(times), 3), "max_ms": round(max(times), 3),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    print(f"\nPage timing: {args.label}  ({args.url}, runs={args.runs})")
    print(f"median {row['median_ms']} ms | p95 {row['p95_ms']} ms | mean {row['mean_ms']} ms")

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{args.label}_page.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if new:
            writer.writeheader()
        writer.writerow(row)
    print(f"Saved to {os.path.normpath(path)}")


if __name__ == "__main__":
    main()
