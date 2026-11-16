"""Create migration-performance charts from the repository's measured CSV files.

Run from the repository root:
    python results/make_charts.py

The script does not create or simulate benchmark data. Missing Stage 1/2/3
benchmark files are reported as errors. The Locust chart is skipped until the
Stage 2 and Stage 3 Locust aggregate CSV files are available.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
CHARTS_DIR = RESULTS_DIR / "generated_charts"
SUMMARY_DIR = RESULTS_DIR / "summary_tables"

STAGE_FILES = {
    "stage1_local": {
        "label": "Stage 1: Local",
        "database": "stage1_local_db.csv",
        "page": "stage1_local_page.csv",
    },
    "stage2_ec2": {
        "label": "Stage 2: EC2 + MySQL",
        "database": "stage2_ec2_db.csv",
        "page": "stage2_ec2_page.csv",
    },
    "stage3_rds": {
        "label": "Stage 3: EC2 + RDS",
        "database": "stage3_rds_db.csv",
        "page": "stage3_rds_page.csv",
    },
}

STAGE_ORDER = list(STAGE_FILES)
OPERATION_ORDER = ["INSERT", "SELECT_LIST", "SELECT_BY_ID", "UPDATE"]


class DataValidationError(ValueError):
    """Raised when a benchmark CSV is present but cannot be compared safely."""


def _read_csv(path: Path, required_columns: Iterable[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required benchmark file is missing: {path}")

    frame = pd.read_csv(path)
    missing = sorted(set(required_columns) - set(frame.columns))
    if missing:
        raise DataValidationError(
            f"{path.name} is missing required column(s): {', '.join(missing)}"
        )
    if frame.empty:
        raise DataValidationError(f"{path.name} contains a header but no data rows")
    return frame


def _validate_numeric(frame: pd.DataFrame, columns: Iterable[str], filename: str) -> None:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any():
            raise DataValidationError(
                f"{filename} contains blank or non-numeric values in '{column}'"
            )


def load_database_results() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    required = ["label", "operation", "runs", "median_ms", "p95_ms"]

    for stage, details in STAGE_FILES.items():
        path = RESULTS_DIR / details["database"]
        frame = _read_csv(path, required)
        _validate_numeric(frame, ["runs", "median_ms", "p95_ms"], path.name)

        frame["stage"] = stage
        valid_operations = set(OPERATION_ORDER)
        unknown = sorted(set(frame["operation"].astype(str)) - valid_operations)
        if unknown:
            raise DataValidationError(
                f"{path.name} contains unknown operation(s): {', '.join(unknown)}"
            )
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)
    if set(combined["stage"].unique()) != set(STAGE_ORDER):
        raise DataValidationError("Database results do not contain all three stages")
    return combined


def summarize_database(frame: pd.DataFrame) -> pd.DataFrame:
    """Use the median across recorded run-level statistics for each stage."""
    summary = (
        frame.groupby(["stage", "operation"], as_index=False)
        .agg(
            median_ms=("median_ms", "median"),
            p95_ms=("p95_ms", "median"),
            recorded_batches=("median_ms", "size"),
            timed_operations_per_batch=("runs", "median"),
        )
    )
    summary["stage_label"] = summary["stage"].map(
        {key: value["label"] for key, value in STAGE_FILES.items()}
    )
    return summary.sort_values(
        ["operation", "stage"],
        key=lambda col: col.map(
            {name: index for index, name in enumerate(OPERATION_ORDER)}
            if col.name == "operation"
            else {name: index for index, name in enumerate(STAGE_ORDER)}
        ),
    )


def load_page_results() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    required = ["label", "runs", "median_ms", "p95_ms"]

    for stage, details in STAGE_FILES.items():
        path = RESULTS_DIR / details["page"]
        frame = _read_csv(path, required)
        _validate_numeric(frame, ["runs", "median_ms", "p95_ms"], path.name)
        frame["stage"] = stage
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


def summarize_page(frame: pd.DataFrame) -> pd.DataFrame:
    summary = (
        frame.groupby("stage", as_index=False)
        .agg(
            median_ms=("median_ms", "median"),
            p95_ms=("p95_ms", "median"),
            recorded_batches=("median_ms", "size"),
            requests_per_batch=("runs", "median"),
        )
    )
    summary["stage_label"] = summary["stage"].map(
        {key: value["label"] for key, value in STAGE_FILES.items()}
    )
    return summary.set_index("stage").reindex(STAGE_ORDER).reset_index()


def plot_database_metric(summary: pd.DataFrame, metric: str, output_name: str) -> None:
    figure, axis = plt.subplots(figsize=(10, 6))
    x_positions = list(range(len(OPERATION_ORDER)))

    for stage in STAGE_ORDER:
        stage_data = summary[summary["stage"] == stage].set_index("operation")
        y_values = [
            float(stage_data.loc[operation, metric])
            if operation in stage_data.index
            else float("nan")
            for operation in OPERATION_ORDER
        ]
        axis.plot(
            x_positions,
            y_values,
            marker="o",
            linewidth=2,
            label=STAGE_FILES[stage]["label"],
        )

    axis.set_xticks(x_positions, OPERATION_ORDER)
    axis.set_ylabel("Response time (ms)")
    axis.set_xlabel("Database operation")
    axis.set_title(f"Database {'median' if metric == 'median_ms' else 'P95'} time by operation and stage")
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(CHARTS_DIR / output_name, dpi=160, bbox_inches="tight")
    plt.close(figure)


def plot_page_results(summary: pd.DataFrame) -> None:
    figure, axis = plt.subplots(figsize=(9, 6))
    x_positions = list(range(len(summary)))
    width = 0.36

    axis.bar(
        [position - width / 2 for position in x_positions],
        summary["median_ms"],
        width,
        label="Median",
    )
    axis.bar(
        [position + width / 2 for position in x_positions],
        summary["p95_ms"],
        width,
        label="P95",
    )

    axis.set_xticks(
        x_positions,
        [STAGE_FILES[stage]["label"] for stage in summary["stage"]],
        rotation=10,
        ha="right",
    )
    axis.set_ylabel("Page response time (ms)")
    axis.set_title("Main page response time by stage")
    axis.grid(True, axis="y", alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(CHARTS_DIR / "page_response_times.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def _find_locust_aggregate(frame: pd.DataFrame, path: Path) -> pd.Series:
    required = {
        "Name",
        "Request Count",
        "Failure Count",
        "Median Response Time",
        "95%",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise DataValidationError(
            f"{path.name} is missing Locust column(s): {', '.join(missing)}"
        )

    aggregate = frame[frame["Name"].astype(str).str.strip().str.lower() == "aggregated"]
    if aggregate.empty:
        raise DataValidationError(
            f"{path.name} has no 'Aggregated' row. Do not combine endpoint p95 values manually."
        )
    return aggregate.iloc[0]


def load_locust_results() -> pd.DataFrame:
    locust_dir = RESULTS_DIR / "locust"
    if not locust_dir.is_dir():
        return pd.DataFrame()

    records: list[dict[str, float | int | str]] = []
    pattern = re.compile(
        r"^(stage2_ec2|stage3_rds)_(?:load_)?u?(\d+)(?:_run\d+)?(?:_\d{8}T\d{6})?_stats\.csv$",
        re.IGNORECASE,
    )

    for path in sorted(locust_dir.glob("*_stats.csv")):
        match = pattern.match(path.name)
        if not match:
            continue

        stage = match.group(1).lower()
        users = int(match.group(2))
        frame = pd.read_csv(path)
        aggregate = _find_locust_aggregate(frame, path)

        numeric_columns = [
            "Request Count",
            "Failure Count",
            "Median Response Time",
            "95%",
        ]
        values = {
            column: pd.to_numeric(aggregate[column], errors="coerce")
            for column in numeric_columns
        }
        if any(pd.isna(value) for value in values.values()):
            raise DataValidationError(
                f"{path.name} contains blank/non-numeric aggregate statistics"
            )

        request_count = int(values["Request Count"])
        failure_count = int(values["Failure Count"])
        records.append(
            {
                "stage": stage,
                "users": users,
                "requests": request_count,
                "failures": failure_count,
                "failure_pct": (failure_count / request_count * 100)
                if request_count
                else 0.0,
                "median_ms": float(values["Median Response Time"]),
                "p95_ms": float(values["95%"]),
                "source_file": path.name,
            }
        )

    return pd.DataFrame.from_records(records)


def plot_locust_results(summary: pd.DataFrame) -> None:
    if summary.empty:
        print(
            "Locust chart skipped: no matching Stage 2/Stage 3 files found. "
            "Expected names such as stage2_ec2_load_10_run1_20261115T100000_stats.csv."
        )
        return

    figure, axis = plt.subplots(figsize=(10, 6))
    for stage in ("stage2_ec2", "stage3_rds"):
        stage_data = summary[summary["stage"] == stage].sort_values("users")
        if stage_data.empty:
            continue
        stage_label = STAGE_FILES[stage]["label"]
        axis.plot(
            stage_data["users"],
            stage_data["median_ms"],
            marker="o",
            linewidth=2,
            label=f"{stage_label} (median)",
        )
        axis.plot(
            stage_data["users"],
            stage_data["p95_ms"],
            marker="s",
            linestyle="--",
            linewidth=2,
            label=f"{stage_label} (P95)",
        )

    axis.set_xlabel("Concurrent Locust users")
    axis.set_ylabel("Response time (ms)")
    axis.set_title("Load test response time by number of users")
    axis.grid(True, alpha=0.3)
    axis.legend()
    figure.tight_layout()
    figure.savefig(CHARTS_DIR / "load_test_response_vs_users.png", dpi=160, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    try:
        database = load_database_results()
        database_summary = summarize_database(database)
        database_summary.to_csv(SUMMARY_DIR / "database_summary.csv", index=False)
        plot_database_metric(database_summary, "median_ms", "database_median_by_operation.png")
        plot_database_metric(database_summary, "p95_ms", "database_p95_by_operation.png")

        page = load_page_results()
        page_summary = summarize_page(page)
        page_summary.to_csv(SUMMARY_DIR / "page_summary.csv", index=False)
        plot_page_results(page_summary)

        locust_runs = load_locust_results()
        if not locust_runs.empty:
            locust_runs.to_csv(SUMMARY_DIR / "load_test_runs.csv", index=False)
            locust_summary = (
                locust_runs.groupby(["stage", "users"], as_index=False)
                .agg(
                    median_ms=("median_ms", "median"),
                    p95_ms=("p95_ms", "median"),
                    requests=("requests", "median"),
                    failures=("failures", "median"),
                    failure_pct=("failure_pct", "median"),
                    recorded_repetitions=("source_file", "count"),
                )
                .sort_values(["stage", "users"])
            )
            locust_summary.to_csv(SUMMARY_DIR / "load_test_summary.csv", index=False)
            plot_locust_results(locust_summary)
        else:
            plot_locust_results(locust_runs)

    except (FileNotFoundError, DataValidationError, pd.errors.ParserError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Charts saved to: {CHARTS_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Summary tables saved to: {SUMMARY_DIR.relative_to(PROJECT_ROOT)}")
    print("The load-test chart is produced when compatible Locust CSVs are present; verify both cloud stages before using it in the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
