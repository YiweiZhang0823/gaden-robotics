#!/usr/bin/env python3
"""Summarize GSL hyper-parameter sensitivity trials."""
from __future__ import annotations

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean


STATE_ORDER = [
    "far_off_plume",
    "far_near_edge",
    "far_inside_plume",
    "near_source_outside_plume",
    "near_source_upwind",
]

PARAM_ORDER = [
    "sensitivity_baseline",
    "sensitivity_conf_low",
    "sensitivity_conf_high",
    "sensitivity_threshold_low",
    "sensitivity_loss_tolerant",
    "sensitivity_spiral_easy",
]


def _float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return math.nan


def _mean(rows: list[dict[str, str]], key: str) -> float:
    values = [_float(row, key) for row in rows]
    values = [value for value in values if math.isfinite(value)]
    return mean(values) if values else math.nan


def _fmt(value: float, digits: int = 3) -> str:
    if not math.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def _sort_key(row: dict[str, str]) -> tuple[str, int, int, str]:
    state = row["initial_state"]
    param = row["param_set"]
    state_idx = STATE_ORDER.index(state) if state in STATE_ORDER else len(STATE_ORDER)
    param_idx = PARAM_ORDER.index(param) if param in PARAM_ORDER else len(PARAM_ORDER)
    return row["scenario"], state_idx, param_idx, param


def _load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _summarize_group(rows: list[dict[str, str]]) -> dict[str, str]:
    first = rows[0]
    trials = len(rows)
    successes = sum(1 for row in rows if row.get("success") == "1")
    stop_reasons = Counter(row.get("stop_reason", "") for row in rows)
    return {
        "scenario": first.get("scenario", ""),
        "initial_state": first.get("initial_state", ""),
        "initial_label": first.get("initial_label", ""),
        "plume_relation": first.get("plume_relation", ""),
        "wind_relation": first.get("wind_relation", ""),
        "param_set": first.get("param_set", ""),
        "trials": str(trials),
        "success_rate": _fmt(successes / trials if trials else math.nan, 2),
        "mean_time_s": _fmt(_mean(rows, "time_s"), 1),
        "mean_path_m": _fmt(_mean(rows, "path_length_m"), 3),
        "mean_min_distance_m": _fmt(_mean(rows, "min_distance_m"), 3),
        "mean_final_distance_m": _fmt(_mean(rows, "final_distance_m"), 3),
        "mean_final_raw": _fmt(_mean(rows, "final_raw"), 3),
        "mean_final_confidence": _fmt(_mean(rows, "final_confidence"), 3),
        "mean_max_margin_seen": _fmt(_mean(rows, "max_margin_seen"), 3),
        "mean_cast_steps": _fmt(_mean(rows, "cast_steps"), 1),
        "mean_surge_steps": _fmt(_mean(rows, "surge_steps"), 1),
        "mean_spiral_steps": _fmt(_mean(rows, "spiral_steps"), 1),
        "stop_reasons": "; ".join(f"{reason}:{count}" for reason, count in stop_reasons.items()),
    }


def _score(summary: dict[str, str]) -> tuple[float, float, float, float]:
    success = float(summary["success_rate"]) if summary["success_rate"] != "NA" else 0.0
    time_s = float(summary["mean_time_s"]) if summary["mean_time_s"] != "NA" else 1e9
    path = float(summary["mean_path_m"]) if summary["mean_path_m"] != "NA" else 1e9
    final_conf = float(summary["mean_final_confidence"]) if summary["mean_final_confidence"] != "NA" else 0.0
    return success, -time_s, -path, final_conf


def _print_table(rows: list[dict[str, str]], title: str, headers: list[str]) -> None:
    print(f"# {title}")
    print()
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        print("| " + " | ".join(row.get(header, "") for header in headers) + " |")
    print()


def _write_csv(rows: list[dict[str, str]], path: Path) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize sensitivity trials by parameter set.")
    parser.add_argument(
        "--csv",
        default="/home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv",
        help="Input sensitivity CSV written by surge_cast_spiral_gsl.",
    )
    parser.add_argument("--scenario", default="", help="Optional scenario filter.")
    parser.add_argument("--state", default="", help="Optional initial-state filter.")
    parser.add_argument("--output-csv", default="", help="Optional summary CSV output path.")
    args = parser.parse_args()

    rows = _load_rows(Path(args.csv).expanduser())
    if args.scenario:
        rows = [row for row in rows if row.get("scenario") == args.scenario]
    if args.state:
        rows = [row for row in rows if row.get("initial_state") == args.state]

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row.get("scenario", ""), row.get("initial_state", ""), row.get("param_set", ""))].append(row)

    summary = [_summarize_group(group_rows) for group_rows in grouped.values()]
    summary.sort(key=_sort_key)

    headers = [
        "scenario",
        "initial_state",
        "param_set",
        "trials",
        "success_rate",
        "mean_time_s",
        "mean_path_m",
        "mean_min_distance_m",
        "mean_final_distance_m",
        "mean_final_raw",
        "mean_final_confidence",
        "mean_spiral_steps",
        "stop_reasons",
    ]
    _print_table(summary, "GSL Sensitivity Summary", headers)

    best_rows = []
    by_case: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in summary:
        by_case[(row["scenario"], row["initial_state"])].append(row)
    for (scenario, state), case_rows in sorted(by_case.items()):
        best = max(case_rows, key=_score)
        best_rows.append(
            {
                "scenario": scenario,
                "initial_state": state,
                "best_param_set": best["param_set"],
                "success_rate": best["success_rate"],
                "mean_time_s": best["mean_time_s"],
                "mean_path_m": best["mean_path_m"],
                "mean_final_confidence": best["mean_final_confidence"],
                "why_best": "highest success rate, then lower time/path, then higher final confidence",
            }
        )
    _print_table(
        best_rows,
        "Best Variant Per Initial State",
        [
            "scenario",
            "initial_state",
            "best_param_set",
            "success_rate",
            "mean_time_s",
            "mean_path_m",
            "mean_final_confidence",
            "why_best",
        ],
    )

    if args.output_csv:
        _write_csv(summary, Path(args.output_csv).expanduser())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
