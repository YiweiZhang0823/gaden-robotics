#!/usr/bin/env python3
"""Print commands for the third-stage repeatability experiments."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from ament_index_python.packages import get_package_share_directory


REPEAT_CASES: list[dict[str, Any]] = [
    {
        "case_id": "case1_baseline",
        "label": "Case 1 baseline repeat",
        "scenario": "exp3_advection",
        "state": "far_inside_plume",
        "param_set": "sensitivity_baseline",
        "why": "验证平流主导场景中，已经在羽流内部时 baseline 是否稳定成功。",
        "overrides": {
            "required_confidence": 0.6,
        },
    },
    {
        "case_id": "case3_baseline",
        "label": "Case 3 baseline repeat",
        "scenario": "exp2_time_varying",
        "state": "far_near_edge",
        "param_set": "sensitivity_baseline",
        "why": "验证时变风场羽流边缘状态下 baseline 是否稳定。",
        "overrides": {
            "required_confidence": 0.6,
        },
    },
    {
        "case_id": "case3_threshold_low",
        "label": "Case 3 threshold-low repeat",
        "scenario": "exp2_time_varying",
        "state": "far_near_edge",
        "param_set": "sensitivity_threshold_low",
        "why": "验证降低检测阈值后，远离气源的 stop_mode_confirmed 是否稳定出现，即 false positive 风险。",
        "overrides": {
            "auto_thresholds": False,
            "theta_low": 0.25,
            "theta_mid": 1.0,
            "theta_high": 2.5,
            "contact_threshold": 0.02,
            "required_confidence": 0.6,
        },
    },
    {
        "case_id": "case3_loss_tolerant",
        "label": "Case 3 loss-tolerant repeat",
        "scenario": "exp2_time_varying",
        "state": "far_near_edge",
        "param_set": "sensitivity_loss_tolerant",
        "why": "验证放宽 plume loss 后，SURGE 过长和远离气源的失败是否稳定出现。",
        "overrides": {
            "surge_loss_steps": 8,
            "surge_peak_drop_abs": 0.7,
            "surge_peak_drop_ratio": 0.7,
            "required_confidence": 0.6,
        },
    },
]


def _load_presets() -> dict[str, Any]:
    path = (
        Path(get_package_share_directory("test_env"))
        / "scenarios"
        / "10x6_empty_room"
        / "initial_states.yaml"
    )
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fmt_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _select_cases(case_ids: list[str] | None) -> list[dict[str, Any]]:
    if not case_ids:
        return REPEAT_CASES
    requested = set(case_ids)
    selected = [case for case in REPEAT_CASES if case["case_id"] in requested]
    missing = requested - {case["case_id"] for case in selected}
    if missing:
        raise KeyError("Unknown repeat case(s): " + ", ".join(sorted(missing)))
    return selected


def _print_list(data: dict[str, Any]) -> None:
    print("Third-stage repeatability cases:")
    for case in REPEAT_CASES:
        scenario = data["scenarios"][case["scenario"]]
        state = scenario["states"][case["state"]]
        print(f"  {case['case_id']}:")
        print(f"    scenario/state: {case['scenario']} / {case['state']}")
        print(f"    label: {state['label']}")
        print(f"    param_set: {case['param_set']}")
        print(f"    why: {case['why']}")
        overrides = ", ".join(
            f"{key}:={_fmt_value(value)}" for key, value in case["overrides"].items()
        )
        print(f"    overrides: {overrides}")


def _print_launch_block(case: dict[str, Any], data: dict[str, Any]) -> None:
    scenario = data["scenarios"][case["scenario"]]
    state = scenario["states"][case["state"]]
    base_x, base_y, base_yaw = state["base_pose"]
    ee_x, ee_y, ee_z = state["ee_target"]
    print("# Terminal 1: launch once for this repeat case")
    print(f"# Initial TCP: ({ee_x}, {ee_y}, {ee_z})")
    print("cd /home/yiwei/ros2_ws")
    print("source install/setup.bash")
    print(
        f"ros2 launch test_env {scenario['launch']} "
        "align_base_from_gas_yaml:=false "
        f"map_x:={base_x:.4g} map_y:={base_y:.4g} map_yaw:={base_yaw:.4g} "
        "joint_state_mode:=interactive franka_joint_max_velocity:=0.15"
    )
    print()


def _print_trial_block(
    args: argparse.Namespace,
    case: dict[str, Any],
    rep_idx: int,
    preset: str,
) -> None:
    scenario = case["scenario"]
    state = case["state"]
    param_set = case["param_set"]
    log_name = f"repeat_{case['case_id']}_rep{rep_idx}.log"
    print(f"# Terminal 2: {case['case_id']} repeat {rep_idx}/{args.repeats}")
    print(f"# {case['why']}")
    print("cd /home/yiwei/ros2_ws")
    print("source install/setup.bash")
    print("mkdir -p results")
    print("stdbuf -oL ros2 run test_env surge_cast_spiral_gsl --ros-args \\")
    print(f"  -p scenario_key:={scenario} \\")
    print(f"  -p initial_state_key:={state} \\")
    print(f"  -p param_set:={param_set} \\")
    print(f"  -p output_csv:={args.output_csv} \\")
    print(f"  -p timeout_s:={args.timeout_s:.1f} \\")
    print("  -p success_radius:=0.25 \\")
    print("  -p control_period:=1.0 \\")
    print(f"  -p initial_settle_s:={args.initial_settle_s:.1f} \\")
    print(f"  -p goal_preset:={preset} \\")
    print("  -p search_heading_yaw:=3.1416 \\")
    for key, value in case["overrides"].items():
        print(f"  -p {key}:={_fmt_value(value)} \\")
    print(f"  2>&1 | tee /home/yiwei/ros2_ws/results/{log_name}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print third-stage repeatability experiment commands."
    )
    parser.add_argument(
        "--case",
        action="append",
        help="Run only one repeat case id. Can be repeated.",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Number of repeats per case.")
    parser.add_argument(
        "--output-csv",
        default="/home/yiwei/ros2_ws/results/gsl_repeatability_trials.csv",
        help="Separate CSV for repeatability trials.",
    )
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--initial-settle-s", type=float, default=8.0)
    parser.add_argument("--list", action="store_true", help="List repeat cases.")
    args = parser.parse_args()

    data = _load_presets()
    if args.list:
        _print_list(data)
        return 0

    try:
        cases = _select_cases(args.case)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    preset = data.get("default_ee_preset", "tilt_x_90")
    print("# GSL third-stage repeatability experiment commands")
    print("# Build once before running if scripts changed:")
    print("cd /home/yiwei/ros2_ws")
    print("colcon build --packages-select test_env --symlink-install")
    print("source install/setup.bash")
    print()
    print(f"# Output CSV: {args.output_csv}")
    print("# Summarize after running:")
    print(
        "ros2 run test_env gsl_repeatability_summary "
        f"--csv {args.output_csv} "
        "--output-csv /home/yiwei/ros2_ws/results/gsl_repeatability_summary.csv"
    )
    print()

    for case_idx, case in enumerate(cases, start=1):
        scenario = data["scenarios"][case["scenario"]]
        state = scenario["states"][case["state"]]
        print("#" * 72)
        print(f"# Repeat case {case_idx}/{len(cases)}: {case['case_id']}")
        print(f"# {case['scenario']} / {case['state']} / {case['param_set']}")
        print(f"# 导师要求对应情况: {state['label']}")
        print(f"# 目的: {case['why']}")
        print("#" * 72)
        _print_launch_block(case, data)
        for rep_idx in range(1, args.repeats + 1):
            _print_trial_block(args, case, rep_idx, preset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
