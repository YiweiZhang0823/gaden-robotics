#!/usr/bin/env python3
"""Print launch and trial commands for open-field initial-state presets."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import yaml
from ament_index_python.packages import get_package_share_directory


def _load_presets() -> dict:
    path = (
        Path(get_package_share_directory("test_env"))
        / "scenarios"
        / "10x6_empty_room"
        / "initial_states.yaml"
    )
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fmt_vec(values: list[float]) -> str:
    return " ".join(f"{float(v):.4g}" for v in values)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print terminal commands for a thesis open-field initial state."
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        help="Scenario key, e.g. exp1_diffusion, exp2_time_varying, exp3_advection",
    )
    parser.add_argument(
        "state",
        nargs="?",
        help="State key, e.g. far_off_plume, far_near_edge, far_inside_plume",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scenario/state keys.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=300.0,
        help="Trial timeout passed to surge_cast_spiral_gsl.",
    )
    parser.add_argument(
        "--initial-settle-s",
        type=float,
        default=8.0,
        help="Seconds to hold the requested initial TCP pose before trial clock starts.",
    )
    parser.add_argument(
        "--output-csv",
        default="/home/yiwei/ros2_ws/results/gsl_supervisor_trials.csv",
        help="CSV file for supervisor-style initial-state experiments.",
    )
    parser.add_argument(
        "--param-set",
        default="supervisor_initial_state_matrix",
        help="Parameter-set label stored in the CSV.",
    )
    args = parser.parse_args()

    data = _load_presets()
    scenarios = data["scenarios"]

    if args.list or not args.scenario or not args.state:
        print("Available presets:")
        for scenario_key, scenario in scenarios.items():
            print(f"  {scenario_key}:")
            for state_key, state in scenario["states"].items():
                print(f"    {state_key}: {state['label']}")
        if args.list:
            return 0
        print(
            "\nUsage example:\n"
            "  ros2 run test_env open_field_initial_state_commands "
            "exp3_advection far_inside_plume",
            file=sys.stderr,
        )
        return 2

    if args.scenario not in scenarios:
        print(f"Unknown scenario: {args.scenario}", file=sys.stderr)
        return 2
    scenario = scenarios[args.scenario]
    if args.state not in scenario["states"]:
        print(f"Unknown state: {args.state}", file=sys.stderr)
        return 2

    state = scenario["states"][args.state]
    base_x, base_y, base_yaw = state["base_pose"]
    ee_x, ee_y, ee_z = state["ee_target"]
    src_x, src_y, src_z = data["source"]
    base_to_source = math.hypot(float(src_x) - float(base_x), float(src_y) - float(base_y))
    ee_to_source = math.sqrt(
        (float(src_x) - float(ee_x)) ** 2
        + (float(src_y) - float(ee_y)) ** 2
        + (float(src_z) - float(ee_z)) ** 2
    )
    preset = data.get("default_ee_preset", "tilt_x_90")

    print(f"# {args.scenario} / {args.state}")
    print(f"# {state['label']}")
    print(f"# base_to_source_xy={base_to_source:.3f} m, initial_ee_to_source={ee_to_source:.3f} m")
    print("# Terminal 1:")
    print("cd /home/yiwei/ros2_ws")
    print("source install/setup.bash")
    print(
        f"ros2 launch test_env {scenario['launch']} "
        "align_base_from_gas_yaml:=false "
        f"map_x:={base_x:.4g} map_y:={base_y:.4g} map_yaw:={base_yaw:.4g} "
        "joint_state_mode:=interactive franka_joint_max_velocity:=0.15"
    )
    print()
    print("# Terminal 2:")
    print("cd /home/yiwei/ros2_ws")
    print("source install/setup.bash")
    print("mkdir -p results")
    print(
        "stdbuf -oL ros2 run test_env surge_cast_spiral_gsl --ros-args \\"
    )
    print(f"  -p scenario_key:={args.scenario} \\")
    print(f"  -p initial_state_key:={args.state} \\")
    print(f"  -p param_set:={args.param_set} \\")
    print(f"  -p output_csv:={args.output_csv} \\")
    print(f"  -p timeout_s:={args.timeout_s:.1f} \\")
    print("  -p success_radius:=0.25 \\")
    print("  -p required_confidence:=0.6 \\")
    print("  -p control_period:=1.0 \\")
    print(f"  -p initial_settle_s:={args.initial_settle_s:.1f} \\")
    print(f"  -p goal_preset:={preset} \\")
    print("  -p search_heading_yaw:=3.1416 \\")
    print(
        "  2>&1 | tee "
        f"/home/yiwei/ros2_ws/results/{args.scenario}_{args.state}.log"
    )
    print()
    print("# Optional: only place the TCP at the initial state without running the trial.")
    print(
        f"ros2 run test_env publish_ee_goal {_fmt_vec([ee_x, ee_y, ee_z])} "
        f"--frame map --preset {preset}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
