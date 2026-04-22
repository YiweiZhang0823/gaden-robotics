#!/usr/bin/env python3
"""Summarize third-stage GSL repeatability trials."""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev


def _float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return math.nan


def _values(rows: list[dict[str, str]], key: str) -> list[float]:
    vals = [_float(row, key) for row in rows]
    return [value for value in vals if math.isfinite(value)]


def _mean(rows: list[dict[str, str]], key: str) -> float:
    vals = _values(rows, key)
    return mean(vals) if vals else math.nan


def _std(rows: list[dict[str, str]], key: str) -> float:
    vals = _values(rows, key)
    return pstdev(vals) if len(vals) > 1 else 0.0 if vals else math.nan


def _fmt(value: float, digits: int = 3) -> str:
    if not math.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _summarize(rows: list[dict[str, str]]) -> dict[str, str]:
    first = rows[0]
    trials = len(rows)
    successes = sum(1 for row in rows if row.get("success") == "1")
    stop_reasons = Counter(row.get("stop_reason", "") for row in rows)
    return {
        "scenario": first.get("scenario", ""),
        "initial_state": first.get("initial_state", ""),
        "initial_label": first.get("initial_label", ""),
        "param_set": first.get("param_set", ""),
        "trials": str(trials),
        "successes": str(successes),
        "success_rate": _fmt(successes / trials if trials else math.nan, 2),
        "mean_time_s": _fmt(_mean(rows, "time_s"), 1),
        "std_time_s": _fmt(_std(rows, "time_s"), 1),
        "mean_path_m": _fmt(_mean(rows, "path_length_m"), 3),
        "std_path_m": _fmt(_std(rows, "path_length_m"), 3),
        "mean_min_distance_m": _fmt(_mean(rows, "min_distance_m"), 3),
        "std_min_distance_m": _fmt(_std(rows, "min_distance_m"), 3),
        "mean_final_distance_m": _fmt(_mean(rows, "final_distance_m"), 3),
        "std_final_distance_m": _fmt(_std(rows, "final_distance_m"), 3),
        "mean_final_confidence": _fmt(_mean(rows, "final_confidence"), 3),
        "std_final_confidence": _fmt(_std(rows, "final_confidence"), 3),
        "mean_final_raw": _fmt(_mean(rows, "final_raw"), 3),
        "mean_cast_steps": _fmt(_mean(rows, "cast_steps"), 1),
        "mean_surge_steps": _fmt(_mean(rows, "surge_steps"), 1),
        "mean_spiral_steps": _fmt(_mean(rows, "spiral_steps"), 1),
        "stop_reasons": "; ".join(f"{reason}:{count}" for reason, count in stop_reasons.items()),
    }


def _print_markdown(rows: list[dict[str, str]]) -> None:
    headers = [
        "scenario",
        "initial_state",
        "param_set",
        "trials",
        "successes",
        "success_rate",
        "mean_time_s",
        "std_time_s",
        "mean_path_m",
        "std_path_m",
        "mean_min_distance_m",
        "mean_final_distance_m",
        "mean_final_confidence",
        "mean_cast_steps",
        "mean_surge_steps",
        "mean_spiral_steps",
        "stop_reasons",
    ]
    print("# GSL Repeatability Summary")
    print()
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        print("| " + " | ".join(row.get(header, "") for header in headers) + " |")


def _write_csv(rows: list[dict[str, str]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize repeatability experiments.")
    parser.add_argument(
        "--csv",
        default="/home/yiwei/ros2_ws/results/gsl_repeatability_trials.csv",
        help="Input repeatability CSV.",
    )
    parser.add_argument("--output-csv", default="", help="Optional output summary CSV.")
    args = parser.parse_args()

    rows = _load_rows(Path(args.csv).expanduser())
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("scenario", ""),
            row.get("initial_state", ""),
            row.get("param_set", ""),
        )
        grouped[key].append(row)

    summary = [_summarize(group_rows) for group_rows in grouped.values()]
    summary.sort(key=lambda row: (row["scenario"], row["initial_state"], row["param_set"]))
    _print_markdown(summary)
    if args.output_csv:
        _write_csv(summary, Path(args.output_csv).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
