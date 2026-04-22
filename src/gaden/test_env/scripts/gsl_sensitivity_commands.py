#!/usr/bin/env python3
"""Print terminal commands for GSL hyper-parameter sensitivity trials."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from ament_index_python.packages import get_package_share_directory


STATE_ORDER = [
    "far_off_plume",
    "far_near_edge",
    "far_inside_plume",
    "near_source_outside_plume",
    "near_source_upwind",
]

FOCUSED_CASES = [
    (
        "exp3_advection",
        "far_inside_plume",
        "平流主导场景中已经进入羽流，但 baseline 靠近气源后 confidence 不稳定。",
    ),
    (
        "exp3_advection",
        "far_off_plume",
        "平流主导场景中离羽流边缘也较远，baseline 基本只在 CAST 中无气味搜索。",
    ),
    (
        "exp2_time_varying",
        "far_near_edge",
        "时变风场中靠近羽流边缘，baseline 能靠近气源但确认条件不稳定。",
    ),
]

PARAM_VARIANTS: list[dict[str, Any]] = [
    {
        "name": "sensitivity_baseline",
        "description": "原始参数，用作对照组。",
        "overrides": {
            "required_confidence": 0.6,
        },
    },
    {
        "name": "sensitivity_conf_low",
        "description": "降低成功确认所需 confidence，检查失败是否主要来自确认条件过严。",
        "overrides": {
            "required_confidence": 0.3,
        },
    },
    {
        "name": "sensitivity_conf_high",
        "description": "提高成功确认所需 confidence，检查结果是否对确认条件高度敏感。",
        "overrides": {
            "required_confidence": 0.8,
        },
    },
    {
        "name": "sensitivity_threshold_low",
        "description": "关闭自适应阈值并降低气味检测阈值，检查弱气味/边缘状态是否被漏检。",
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
        "name": "sensitivity_loss_tolerant",
        "description": "放宽 SURGE 中的羽流丢失判定，检查时变/间歇羽流是否需要更长记忆。",
        "overrides": {
            "surge_loss_steps": 8,
            "surge_peak_drop_abs": 0.7,
            "surge_peak_drop_ratio": 0.7,
            "required_confidence": 0.6,
        },
    },
    {
        "name": "sensitivity_spiral_easy",
        "description": "降低进入 SPIRAL 的门槛，检查局部精搜索是否更早介入会改善定位。",
        "overrides": {
            "spiral_enter_confidence": 0.25,
            "spiral_enter_steps": 2,
            "spiral_loss_steps": 6,
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


def _select_cases(args: argparse.Namespace, data: dict[str, Any]) -> list[tuple[str, str, str]]:
    scenarios = data["scenarios"]
    if args.scenario and args.state:
        if args.scenario not in scenarios:
            raise KeyError(f"Unknown scenario: {args.scenario}")
        if args.state not in scenarios[args.scenario]["states"]:
            raise KeyError(f"Unknown state for {args.scenario}: {args.state}")
        return [(args.scenario, args.state, "手动选择的单个敏感性测试状态。")]

    if args.scenario:
        if args.scenario not in scenarios:
            raise KeyError(f"Unknown scenario: {args.scenario}")
        return [
            (args.scenario, state, scenarios[args.scenario]["states"][state]["label"])
            for state in STATE_ORDER
            if state in scenarios[args.scenario]["states"]
        ]

    if args.cases == "focused":
        return FOCUSED_CASES
    if args.cases == "exp3_all":
        scenario = "exp3_advection"
        return [
            (scenario, state, scenarios[scenario]["states"][state]["label"])
            for state in STATE_ORDER
        ]
    if args.cases == "all15":
        return [
            (scenario, state, scenarios[scenario]["states"][state]["label"])
            for scenario in ("exp1_diffusion", "exp2_time_varying", "exp3_advection")
            for state in STATE_ORDER
        ]
    raise KeyError(f"Unknown case set: {args.cases}")


def _select_params(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not args.param:
        return PARAM_VARIANTS
    requested = set(args.param)
    selected = [variant for variant in PARAM_VARIANTS if variant["name"] in requested]
    missing = requested - {variant["name"] for variant in selected}
    if missing:
        raise KeyError("Unknown param variant(s): " + ", ".join(sorted(missing)))
    return selected


def _print_list(data: dict[str, Any]) -> None:
    print("Case presets:")
    print("  focused: exp3/far_inside, exp3/far_off, exp2/far_near_edge")
    print("  exp3_all: all five initial states in exp3_advection")
    print("  all15: all five initial states in exp1/exp2/exp3")
    print()
    print("Available scenarios/states:")
    for scenario_key, scenario in data["scenarios"].items():
        print(f"  {scenario_key}:")
        for state_key in STATE_ORDER:
            state = scenario["states"].get(state_key)
            if state:
                print(f"    {state_key}: {state['label']}")
    print()
    print("Parameter variants:")
    for variant in PARAM_VARIANTS:
        overrides = ", ".join(
            f"{key}:={_fmt_value(value)}" for key, value in variant["overrides"].items()
        )
        print(f"  {variant['name']}: {variant['description']}")
        print(f"    {overrides}")


def _print_launch_block(
    scenario_key: str,
    state_key: str,
    state: dict[str, Any],
    scenario: dict[str, Any],
) -> None:
    base_x, base_y, base_yaw = state["base_pose"]
    print("# Terminal 1: launch this once for this initial state")
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
    scenario_key: str,
    state_key: str,
    variant: dict[str, Any],
    preset: str,
) -> None:
    log_name = f"sensitivity_{scenario_key}_{state_key}_{variant['name']}.log"
    print(f"# Terminal 2: {variant['name']}")
    print(f"# {variant['description']}")
    print("cd /home/yiwei/ros2_ws")
    print("source install/setup.bash")
    print("mkdir -p results")
    print("stdbuf -oL ros2 run test_env surge_cast_spiral_gsl --ros-args \\")
    print(f"  -p scenario_key:={scenario_key} \\")
    print(f"  -p initial_state_key:={state_key} \\")
    print(f"  -p param_set:={variant['name']} \\")
    print(f"  -p output_csv:={args.output_csv} \\")
    print(f"  -p timeout_s:={args.timeout_s:.1f} \\")
    print("  -p success_radius:=0.25 \\")
    print("  -p control_period:=1.0 \\")
    print(f"  -p initial_settle_s:={args.initial_settle_s:.1f} \\")
    print(f"  -p goal_preset:={preset} \\")
    print("  -p search_heading_yaw:=3.1416 \\")
    overrides = dict(variant["overrides"])
    for key, value in overrides.items():
        print(f"  -p {key}:={_fmt_value(value)} \\")
    print(f"  2>&1 | tee /home/yiwei/ros2_ws/results/{log_name}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print reproducible terminal commands for GSL parameter sensitivity analysis."
    )
    parser.add_argument(
        "--cases",
        choices=["focused", "exp3_all", "all15"],
        default="focused",
        help="Which initial-state cases to print when --scenario/--state are not used.",
    )
    parser.add_argument("--scenario", default="", help="Restrict to one scenario.")
    parser.add_argument("--state", default="", help="Restrict to one state; requires --scenario.")
    parser.add_argument(
        "--param",
        action="append",
        help="Run only one named parameter variant. Can be repeated.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=180.0,
        help="Trial timeout for each sensitivity run.",
    )
    parser.add_argument(
        "--initial-settle-s",
        type=float,
        default=8.0,
        help="Seconds to hold the initial TCP pose before trial metrics start.",
    )
    parser.add_argument(
        "--output-csv",
        default="/home/yiwei/ros2_ws/results/gsl_sensitivity_trials.csv",
        help="Separate CSV for sensitivity trials.",
    )
    parser.add_argument("--list", action="store_true", help="List available cases and parameter variants.")
    args = parser.parse_args()

    data = _load_presets()
    if args.list:
        _print_list(data)
        return 0

    if args.state and not args.scenario:
        print("--state requires --scenario", file=sys.stderr)
        return 2

    try:
        cases = _select_cases(args, data)
        variants = _select_params(args)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("# GSL hyper-parameter sensitivity experiment commands")
    print("# Build once before running these commands:")
    print("cd /home/yiwei/ros2_ws")
    print("colcon build --packages-select test_env --symlink-install")
    print("source install/setup.bash")
    print()
    print(f"# Output CSV: {args.output_csv}")
    print("# After running trials, summarize with:")
    print(
        "ros2 run test_env gsl_sensitivity_summary "
        f"--csv {args.output_csv} "
        "--output-csv /home/yiwei/ros2_ws/results/gsl_sensitivity_summary.csv"
    )
    print()

    preset = data.get("default_ee_preset", "tilt_x_90")
    for case_idx, (scenario_key, state_key, why) in enumerate(cases, start=1):
        scenario = data["scenarios"][scenario_key]
        state = scenario["states"][state_key]
        ee_x, ee_y, ee_z = state["ee_target"]
        print("#" * 72)
        print(f"# Case {case_idx}/{len(cases)}: {scenario_key} / {state_key}")
        print(f"# 导师要求对应情况: {state['label']}")
        print(f"# 初始末端位置: ({ee_x}, {ee_y}, {ee_z})")
        print(f"# 为什么选它: {why}")
        print("#" * 72)
        _print_launch_block(scenario_key, state_key, state, scenario)
        for variant in variants:
            _print_trial_block(args, scenario_key, state_key, variant, preset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
