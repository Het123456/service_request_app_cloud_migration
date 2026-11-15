#!/usr/bin/env bash
# Run on Linux EC2 from the repository root (NOT Windows PowerShell).
# Stage 2: bash tests/run_load.sh stage2_ec2
# Stage 3: bash tests/run_load.sh stage3_rds --rds
# Before switching stages, ensure the intended Compose stack is already up.
set -euo pipefail

LABEL="${1:-}"
MODE="${2:-}"
if [[ "$LABEL" != "stage2_ec2" && "$LABEL" != "stage3_rds" ]]; then
  echo "Usage: bash tests/run_load.sh stage2_ec2 | stage3_rds --rds" >&2
  exit 2
fi

compose=(docker compose)
if [[ "$LABEL" == "stage3_rds" ]]; then
  if [[ "$MODE" != "--rds" ]]; then
    echo "Stage 3 requires --rds to use docker-compose.rds.yml" >&2
    exit 2
  fi
  compose+=( -f docker-compose.rds.yml )
elif [[ -n "$MODE" ]]; then
  echo "Unexpected argument for Stage 2: $MODE" >&2
  exit 2
fi

if [[ ! -f tests/locustfile.py || ! -f tests/cleanup_load.py ]]; then
  echo "Run this script from the repository root with both test files present." >&2
  exit 1
fi

mkdir -p results/locust
PORT="${APP_PORT:-8000}"

# The app container must be rebuilt since Dockerfile COPYs tests/ into it.
if ! "${compose[@]}" exec -T app test -f /srv/tests/cleanup_load.py; then
  echo "cleanup_load.py is missing in the app image: rebuild it before testing." >&2
  exit 1
fi

# Check app & DB before running any load; -f makes curl fail on bad HTTP codes.
curl --fail --silent --show-error "http://localhost:${PORT}/health" >/dev/null

for USERS in 1 10 50; do
  for RUN in 1 2 3; do
    TAG="load-test-${LABEL}-u${USERS}-r${RUN}-$(date +%s)"
    PREFIX="${LABEL}_load_${USERS}_run${RUN}"
    echo "=== $LABEL: $USERS users, repetition $RUN/3 ==="

    BASELINE=$("${compose[@]}" exec -T app python /srv/tests/cleanup_load.py --count-only | tr -d '\r')
    if ! [[ "$BASELINE" =~ ^[0-9]+$ ]]; then
      echo "Unable to read baseline count: $BASELINE" >&2
      exit 1
    fi
    if [[ "$BASELINE" -ne 1000 ]]; then
      echo "Expected exactly 1,000 baseline rows; found $BASELINE. Investigate before proceeding." >&2
      exit 1
    fi

    # Never run load against another host; target is the app on the same EC2.
    # --network host is for Linux Docker Engine, NOT Windows Docker Desktop.
    LOAD_STATUS=0
    docker run --rm --network host \
      -e "LOAD_TEST_TAG=$TAG" \
      --mount "type=bind,source=$PWD,target=/mnt/locust" \
      locustio/locust \
      -f /mnt/locust/tests/locustfile.py --headless \
      -u "$USERS" -r 10 -t 60s --host "http://localhost:${PORT}" \
      --csv "/mnt/locust/results/locust/$PREFIX" --csv-full-history \
      --only-summary || LOAD_STATUS=$?

    # Always attempt cleanup, including when Locust returned non-zero.
    CLEAN_STATUS=0
    "${compose[@]}" exec -T app python /srv/tests/cleanup_load.py \
      --tag "$TAG" --expected-count "$BASELINE" || CLEAN_STATUS=$?

    if [[ "$LOAD_STATUS" -ne 0 || "$CLEAN_STATUS" -ne 0 ]]; then
      echo "FAILED: Locust status=$LOAD_STATUS, cleanup status=$CLEAN_STATUS. Stop and investigate." >&2
      exit 1
    fi
    echo "Saved results/locust/${PREFIX}_stats.csv"
  done
done

echo "Completed 9 runs for $LABEL (1, 10, 50 users x 3 repetitions)."
