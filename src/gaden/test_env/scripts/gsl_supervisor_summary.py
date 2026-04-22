#!/usr/bin/env python3
"""Summarize supervisor-style GSL initial-state experiments."""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import yaml
from ament_index_python.packages import get_package_share_directory


STATE_ORDER = [
    "far_off_plume",
    "far_near_edge",
    "far_inside_plume",
    "near_source_outside_plume",
    "near_source_upwind",
]


def _float(row: dict[str, str], key: str) -> float:
    try:
        value = float(row.get(key, "nan"))
    except ValueError:
        return math.nan
    return value


def _mean(rows: list[dict[str, str]], key: str) -> float:
    values = [_float(row, key) for row in rows]
    values = [v for v in values if math.isfinite(v)]
    return mean(values) if values else math.nan


def _fmt(value: float, digits: int = 2) -> str:
    if not math.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def _load_design() -> dict:
    path = (
        Path(get_package_share_directory("test_env"))
        / "scenarios"
        / "10x6_empty_room"
        / "initial_states.yaml"
    )
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_trials(path: Path, scenario: str) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row for row in rows if row.get("scenario") == scenario]


def _state_meta(design: dict, scenario: str, state: str) -> dict:
    return design["scenarios"].get(scenario, {}).get("states", {}).get(state, {})


def _summarize_state(
    design: dict, scenario: str, state: str, rows: list[dict[str, str]]
) -> dict[str, str]:
    meta = _state_meta(design, scenario, state)
    trials = len(rows)
    successes = sum(1 for row in rows if row.get("success") == "1")
    stop_reasons = Counter(row.get("stop_reason", "") for row in rows)
    return {
        "initial_state": state,
        "label": str(meta.get("label", "")),
        "source_relation": str(meta.get("source_relation", rows[0].get("source_relation", "") if rows else "")),
        "plume_relation": str(meta.get("plume_relation", rows[0].get("plume_relation", "") if rows else "")),
        "wind_relation": str(meta.get("wind_relation", rows[0].get("wind_relation", "") if rows else "")),
        "expected_gas_cue": str(meta.get("expected_gas_cue", rows[0].get("expected_gas_cue", "") if rows else "")),
        "trials": str(trials),
        "success_rate": _fmt(successes / trials if trials else math.nan, 2),
        "mean_time_s": _fmt(_mean(rows, "time_s"), 1),
        "mean_path_m": _fmt(_mean(rows, "path_length_m"), 2),
        "mean_initial_dist_m": _fmt(_mean(rows, "initial_distance_m"), 2),
        "mean_min_dist_m": _fmt(_mean(rows, "min_distance_m"), 2),
        "mean_final_raw": _fmt(_mean(rows, "final_raw"), 2),
        "mean_final_conf": _fmt(_mean(rows, "final_confidence"), 2),
        "mean_cast_steps": _fmt(_mean(rows, "cast_steps"), 1),
        "mean_surge_steps": _fmt(_mean(rows, "surge_steps"), 1),
        "mean_spiral_steps": _fmt(_mean(rows, "spiral_steps"), 1),
        "stop_reasons": "; ".join(f"{k}:{v}" for k, v in stop_reasons.items()) if rows else "",
    }


def _print_markdown(summary: list[dict[str, str]], scenario: str) -> None:
    print(f"# GSL supervisor initial-state summary: {scenario}")
    print()
    headers = [
        "initial_state",
        "label",
        "source_relation",
        "plume_relation",
        "wind_relation",
        "trials",
        "success_rate",
        "mean_time_s",
        "mean_path_m",
        "mean_min_dist_m",
        "mean_final_raw",
        "mean_final_conf",
        "mean_cast_steps",
        "mean_surge_steps",
        "mean_spiral_steps",
        "stop_reasons",
    ]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in summary:
        print("| " + " | ".join(row[h] for h in headers) + " |")


def _write_csv(summary: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize success/time/path/plume-contact metrics by initial state."
    )
    parser.add_argument(
        "--csv",
        default="/home/yiwei/ros2_ws/results/gsl_supervisor_trials.csv",
        help="Input trial CSV written by surge_cast_spiral_gsl.",
    )
    parser.add_argument(
        "--scenario",
        default="exp3_advection",
        help="Scenario key to summarize.",
    )
    parser.add_argument(
        "--output-csv",
        default="",
        help="Optional CSV path for the summarized table.",
    )
    args = parser.parse_args()

    design = _load_design()
    trials = _load_trials(Path(args.csv).expanduser(), args.scenario)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in trials:
        grouped[row.get("initial_state", "")].append(row)

    summary = [
        _summarize_state(design, args.scenario, state, grouped.get(state, []))
        for state in STATE_ORDER
    ]
    _print_markdown(summary, args.scenario)
    if args.output_csv:
        _write_csv(summary, Path(args.output_csv).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

