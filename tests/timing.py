"""Database timing test: INSERT, SELECT and UPDATE.

Runs each operation N times over one connection and reports the median,
p95 and mean in milliseconds. Results are appended to results/<label>.csv.

Usage (inside the app container):
    python /srv/tests/timing.py --label stage1_local
    python /srv/tests/timing.py --label stage1_local --runs 500
"""
import argparse
import csv
import os
import random
import statistics
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from db import get_connection  # noqa: E402
from config import DB_CONFIG  # noqa: E402

TEST_NAME = "timing-test"


def p95(values):
    values = sorted(values)
    return values[max(0, int(round(0.95 * len(values))) - 1)]


def timed(cur, sql, params=None):
    start = time.perf_counter()
    cur.execute(sql, params)
    cur.fetchall()
    return (time.perf_counter() - start) * 1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="e.g. stage1_local, stage2_ec2, stage3_rds")
    parser.add_argument("--runs", type=int, default=500)
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "results"))
    args = parser.parse_args()

    times = {"INSERT": [], "SELECT_LIST": [], "SELECT_BY_ID": [], "UPDATE": []}

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT MIN(id) AS lo, MAX(id) AS hi FROM service_requests")
        row = cur.fetchone()
        if not row["hi"]:
            sys.exit("Table is empty. Run db/seed.py first.")
        lo, hi = row["lo"], row["hi"]

        # Warm up so the first slow call doesn't skew results.
        for _ in range(10):
            cur.execute("SELECT 1")
            cur.fetchall()

        for i in range(args.runs):
            times["INSERT"].append(timed(
                cur,
                "INSERT INTO service_requests (customer_name, product_name, issue) VALUES (%s, %s, %s)",
                (TEST_NAME, "Tata Nexon", f"timing run {i}"),
            ))
            times["SELECT_LIST"].append(timed(
                cur,
                "SELECT id, customer_name, product_name, issue, status, created_at "
                "FROM service_requests ORDER BY id DESC LIMIT 50",
            ))
            times["SELECT_BY_ID"].append(timed(
                cur, "SELECT * FROM service_requests WHERE id = %s", (random.randint(lo, hi),)
            ))
            times["UPDATE"].append(timed(
                cur,
                "UPDATE service_requests SET status = %s WHERE id = %s",
                (random.choice(["Pending", "In Progress", "Completed"]), random.randint(lo, hi)),
            ))

        # Remove the test rows so every stage starts from the same dataset.
        cur.execute("DELETE FROM service_requests WHERE customer_name = %s", (TEST_NAME,))

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for op, vals in times.items():
        rows.append({
            "label": args.label, "operation": op, "runs": len(vals),
            "median_ms": round(statistics.median(vals), 3),
            "p95_ms": round(p95(vals), 3),
            "mean_ms": round(statistics.mean(vals), 3),
            "min_ms": round(min(vals), 3), "max_ms": round(max(vals), 3),
            "db_host": DB_CONFIG["host"], "timestamp": stamp,
        })

    print(f"\nDB timing: {args.label}  (host={DB_CONFIG['host']}, runs={args.runs})")
    print(f"{'operation':<14}{'median ms':>11}{'p95 ms':>10}{'mean ms':>10}")
    for r in rows:
        print(f"{r['operation']:<14}{r['median_ms']:>11}{r['p95_ms']:>10}{r['mean_ms']:>10}")

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{args.label}_db.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        if new:
            writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved to {os.path.normpath(path)}")


if __name__ == "__main__":
    main()
