#!/usr/bin/env python3
"""Generate randomized initial-state YAML files and runnable terminal commands."""
from __future__ import annotations

import argparse
import copy
import random
import sys
from pathlib import Path
from typing import Any

import yaml
from ament_index_python.packages import get_package_share_directory


def _load_presets() -> tuple[Path, dict[str, Any]]:
    path = (
        Path(get_package_share_directory("test_env"))
        / "scenarios"
        / "10x6_empty_room"
        / "initial_states.yaml"
    )
    with path.open(encoding="utf-8") as f:
        return path, yaml.safe_load(f)


def _fmt_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _fmt_vec(values: list[float]) -> str:
    return " ".join(f"{float(v):.4g}" for v in values)


def _default_sigma(state: dict[str, Any]) -> tuple[float, float, float]:
    defaults = state.get("sampling_defaults", {})
    sigma = defaults.get("sigma_xyz", [0.0, 0.0, 0.0])
    return (float(sigma[0]), float(sigma[1]), float(sigma[2]))


def _sample_box(
    nominal: tuple[float, float, float],
    sigma: tuple[float, float, float],
    rng: random.Random,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    offsets = tuple(rng.uniform(-s, s) if s > 0.0 else 0.0 for s in sigma)
    sampled = tuple(n + d for n, d in zip(nominal, offsets))
    return sampled, offsets


def _workspace_ok(sampled: tuple[float, float, float]) -> bool:
    x, y, z = sampled
    return -0.1 <= x <= 10.0 and -0.1 <= y <= 6.1 and 0.25 <= z <= 1.15


def _make_sampled_yaml(
    data: dict[str, Any],
    scenario_key: str,
    state_key: str,
    sample_count: int,
    seed: int,
    sigma: tuple[float, float, float],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sampled_data = copy.deepcopy(data)
    scenario = sampled_data["scenarios"][scenario_key]
    base_state = scenario["states"][state_key]
    nominal = tuple(float(v) for v in base_state["ee_target"])
    mode = str(base_state.get("sampling_defaults", {}).get("mode", "box"))
    if mode != "box":
        raise ValueError(f"Unsupported sampling mode: {mode}")

    rng = random.Random(seed)
    generated_samples: list[dict[str, Any]] = []
    for sample_idx in range(1, sample_count + 1):
        sampled = None
        offsets = None
        for _ in range(100):
            sampled_candidate, offsets_candidate = _sample_box(nominal, sigma, rng)
            if _workspace_ok(sampled_candidate):
                sampled = sampled_candidate
                offsets = offsets_candidate
                break
        if sampled is None or offsets is None:
            raise RuntimeError("Could not generate a sampled target within workspace bounds.")

        sample_key = f"{state_key}__sample_{sample_idx:03d}"
        sample_state = copy.deepcopy(base_state)
        sample_state["label"] = f"{base_state['label']} [sample {sample_idx:03d}]"
        sample_state["parent_initial_state"] = state_key
        sample_state["sample_id"] = f"{sample_idx:03d}"
        sample_state["sampling_seed"] = seed
        sample_state["sampling_mode"] = mode
        sample_state["nominal_ee_target"] = [round(v, 6) for v in nominal]
        sample_state["sampling_sigma_xyz"] = [round(v, 6) for v in sigma]
        sample_state["sampling_offset_xyz"] = [round(v, 6) for v in offsets]
        sample_state["ee_target"] = [round(v, 6) for v in sampled]
        scenario["states"][sample_key] = sample_state
        generated_samples.append(
            {
                "sample_key": sample_key,
                "sample_id": f"{sample_idx:03d}",
                "sampled": [round(v, 6) for v in sampled],
                "offsets": [round(v, 6) for v in offsets],
            }
        )

    return sampled_data, generated_samples


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def _print_list(data: dict[str, Any]) -> None:
    print("Available scenario/state presets with sampling defaults:")
    for scenario_key, scenario in data["scenarios"].items():
        print(f"  {scenario_key}:")
        for state_key, state in scenario["states"].items():
            sigma = state.get("sampling_defaults", {}).get("sigma_xyz")
            sigma_text = f" sigma={sigma}" if sigma else ""
            print(f"    {state_key}: {state['label']}{sigma_text}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate randomized initial-state samples and print runnable commands."
    )
    parser.add_argument("scenario", nargs="?", help="Scenario key, e.g. exp2_time_varying")
    parser.add_argument("state", nargs="?", help="State key, e.g. far_near_edge")
    parser.add_argument("--list", action="store_true", help="List available presets.")
    parser.add_argument("--samples", type=int, default=5, help="How many randomized samples to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed used for reproducible sampling.")
    parser.add_argument("--sigma-x", type=float, default=None, help="Override x perturbation half-width.")
    parser.add_argument("--sigma-y", type=float, default=None, help="Override y perturbation half-width.")
    parser.add_argument("--sigma-z", type=float, default=None, help="Override z perturbation half-width.")
    parser.add_argument(
        "--output-yaml",
        default="",
        help="Optional output YAML path. Defaults to results/randomized_initial_states/<scenario>_<state>_seed<seed>.yaml",
    )
    parser.add_argument(
        "--output-csv",
        default="/home/yiwei/ros2_ws/results/gsl_randomized_trials.csv",
        help="CSV file for randomized trial results.",
    )
    parser.add_argument(
        "--param-set",
        default="randomized_initial_state_batch",
        help="Parameter-set label stored in the output CSV.",
    )
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--initial-settle-s", type=float, default=8.0)
    args = parser.parse_args()

    presets_path, data = _load_presets()
    if args.list or not args.scenario or not args.state:
        _print_list(data)
        if args.list:
            return 0
        print(
            "\nUsage example:\n"
            "  ros2 run test_env gsl_randomized_initial_state_commands "
            "exp2_time_varying far_near_edge --samples 5 --seed 42",
            file=sys.stderr,
        )
        return 2

    scenarios = data["scenarios"]
    if args.scenario not in scenarios:
        print(f"Unknown scenario: {args.scenario}", file=sys.stderr)
        return 2
    scenario = scenarios[args.scenario]
    if args.state not in scenario["states"]:
        print(f"Unknown state: {args.state}", file=sys.stderr)
        return 2

    state = scenario["states"][args.state]
    sigma_default = _default_sigma(state)
    sigma = (
        sigma_default[0] if args.sigma_x is None else float(args.sigma_x),
        sigma_default[1] if args.sigma_y is None else float(args.sigma_y),
        sigma_default[2] if args.sigma_z is None else float(args.sigma_z),
    )
    if any(value < 0.0 for value in sigma):
        print(
            "Sampling sigma must be non-negative in all axes.",
            file=sys.stderr,
        )
        return 2

    sampled_data, samples = _make_sampled_yaml(
        data,
        args.scenario,
        args.state,
        args.samples,
        args.seed,
        sigma,
    )

    if args.output_yaml:
        output_yaml = Path(args.output_yaml).expanduser()
    else:
        output_yaml = (
            Path("/home/yiwei/ros2_ws/results/randomized_initial_states")
            / f"{args.scenario}_{args.state}_seed{args.seed}.yaml"
        )
    _write_yaml(output_yaml, sampled_data)

    base_x, base_y, base_yaw = state["base_pose"]
    preset = sampled_data.get("default_ee_preset", "tilt_x_90")

    print("# Randomized initial-state batch")
    print(f"# Source presets file: {presets_path}")
    print(f"# Generated sampled file: {output_yaml}")
    print(f"# Scenario/state template: {args.scenario} / {args.state}")
    print(f"# Label: {state['label']}")
    print(f"# Seed: {args.seed}")
    print(f"# Sigma xyz: {_fmt_vec(list(sigma))}")
    if all(value == 0.0 for value in sigma):
        print("# Note: sigma is zero in all axes, so this batch is a fixed-point regression check.")
    print()
    print("# Generated samples")
    print("| sample_id | sample_key | sampled_ee_target | offsets |")
    print("| --- | --- | --- | --- |")
    for sample in samples:
        sampled_text = "(" + ", ".join(f"{value:.4f}" for value in sample["sampled"]) + ")"
        offsets_text = "(" + ", ".join(f"{value:+.4f}" for value in sample["offsets"]) + ")"
        print(f"| {sample['sample_id']} | `{sample['sample_key']}` | `{sampled_text}` | `{offsets_text}` |")
    print()
    print("# Terminal 1: launch once for this batch")
    print("cd /home/yiwei/ros2_ws")
    print("source install/setup.bash")
    print(
        f"ros2 launch test_env {scenario['launch']} "
        "align_base_from_gas_yaml:=false "
        f"map_x:={base_x:.4g} map_y:={base_y:.4g} map_yaw:={base_yaw:.4g} "
        "joint_state_mode:=interactive franka_joint_max_velocity:=0.15"
    )
    print()
    for sample in samples:
        log_name = f"randomized_{args.scenario}_{sample['sample_key']}.log"
        print(f"# Terminal 2: sample {sample['sample_id']}")
        print("cd /home/yiwei/ros2_ws")
        print("source install/setup.bash")
        print("mkdir -p results")
        print("stdbuf -oL ros2 run test_env surge_cast_spiral_gsl --ros-args \\")
        print(f"  -p scenario_key:={args.scenario} \\")
        print(f"  -p initial_state_key:={sample['sample_key']} \\")
        print(f"  -p initial_states_file:={output_yaml} \\")
        print(f"  -p param_set:={args.param_set} \\")
        print(f"  -p output_csv:={args.output_csv} \\")
        print(f"  -p timeout_s:={args.timeout_s:.1f} \\")
        print("  -p success_radius:=0.25 \\")
        print("  -p required_confidence:=0.6 \\")
        print("  -p control_period:=1.0 \\")
        print(f"  -p initial_settle_s:={args.initial_settle_s:.1f} \\")
        print(f"  -p goal_preset:={preset} \\")
        print("  -p search_heading_yaw:=3.1416 \\")
        print(f"  2>&1 | tee /home/yiwei/ros2_ws/results/{log_name}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
