"""Count service requests or delete ONE explicitly named Locust test batch.

Usage inside app container:
  python /srv/tests/cleanup_load.py --count-only
  python /srv/tests/cleanup_load.py --tag load-test-stage2_ec2-u1-r1-123456 \
      --expected-count 1000

Never deletes the baseline rows or other test batches by broad prefix.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from db import get_connection  # noqa: E402


def count(cur):
    cur.execute("SELECT COUNT(*) AS total FROM service_requests")
    return int(cur.fetchone()["total"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count-only", action="store_true")
    parser.add_argument("--tag", help="Exact customer_name used by this load-test run")
    parser.add_argument("--expected-count", type=int, help="Baseline count from before the test")
    args = parser.parse_args()

    if not args.count_only:
        if not args.tag or not re.fullmatch(r"load-test-[a-zA-Z0-9_-]{1,80}", args.tag):
            parser.error("For cleanup, --tag must be an exact load-test- identifier")
        if args.expected_count is None or args.expected_count < 0:
            parser.error("Cleanup requires a nonnegative --expected-count")

    with get_connection() as conn, conn.cursor() as cur:
        if args.count_only:
            print(count(cur))
            return

        # Exact equality: cannot accidentally remove legitimate seeded rows.
        deleted = cur.execute("DELETE FROM service_requests WHERE customer_name = %s", (args.tag,))
        remaining = count(cur)
        print(f"Removed {deleted} rows tagged {args.tag}; {remaining} rows remain.")
        if remaining != args.expected_count:
            print(
                f"ERROR: Expected baseline {args.expected_count}; found {remaining}. "
                "Do not run the next test until the difference is investigated.",
                file=sys.stderr,
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
