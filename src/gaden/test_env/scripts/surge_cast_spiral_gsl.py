#!/usr/bin/env python3
"""Thesis-inspired CAST/SURGE/SPIRAL gas-source localization runner for Franka."""
from __future__ import annotations

import csv
import math
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from olfaction_msgs.msg import GasSensor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _norm2(x: float, y: float) -> tuple[float, float]:
    n = math.hypot(x, y)
    if n < 1e-9:
        return 1.0, 0.0
    return x / n, y / n


def _dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    idx = round((len(vals) - 1) * q)
    return vals[int(idx)]


def _vector_mean(samples: list[tuple[float, tuple[float, float, float]]]) -> tuple[float, tuple[float, float, float]]:
    if not samples:
        return 0.0, (0.0, 0.0, 0.0)
    w_sum = sum(max(0.0, s[0]) for s in samples)
    if w_sum <= 1e-9:
        return mean(s[0] for s in samples), (0.0, 0.0, 0.0)
    x = sum(max(0.0, m) * off[0] for m, off in samples) / w_sum
    y = sum(max(0.0, m) * off[1] for m, off in samples) / w_sum
    z = sum(max(0.0, m) * off[2] for m, off in samples) / w_sum
    return mean(s[0] for s in samples), (x, y, z)


class SurgeCastSpiralGSL(Node):
    def __init__(self):
        super().__init__("surge_cast_spiral_gsl")
        self._declare_params()

        self.fixed_frame = self.get_parameter("fixed_frame").value
        self.sensor_frame = self.get_parameter("sensor_frame").value
        self.source = (
            float(self.get_parameter("source_x").value),
            float(self.get_parameter("source_y").value),
            float(self.get_parameter("source_z").value),
        )
        self.output_csv = Path(str(self.get_parameter("output_csv").value)).expanduser()
        self.output_csv.parent.mkdir(parents=True, exist_ok=True)

        self.scenario_key = str(self.get_parameter("scenario_key").value)
        self.initial_state_key = str(self.get_parameter("initial_state_key").value)
        self.param_set = str(self.get_parameter("param_set").value)

        self.control_period = float(self.get_parameter("control_period").value)
        self.timeout_s = float(self.get_parameter("timeout_s").value)
        self.success_radius = float(self.get_parameter("success_radius").value)
        self.required_confidence = float(self.get_parameter("required_confidence").value)
        self.goal_z = float(self.get_parameter("goal_z").value)
        self.goal_preset = str(self.get_parameter("goal_preset").value)

        yaw = float(self.get_parameter("search_heading_yaw").value)
        self.heading = _norm2(math.cos(yaw), math.sin(yaw))
        self.lateral = (-self.heading[1], self.heading[0])

        self.theta_low = float(self.get_parameter("theta_low").value)
        self.theta_mid = float(self.get_parameter("theta_mid").value)
        self.theta_high = float(self.get_parameter("theta_high").value)
        self.contact_threshold = float(self.get_parameter("contact_threshold").value)
        self.auto_thresholds = bool(self.get_parameter("auto_thresholds").value)

        self.long_window = deque(maxlen=int(self.get_parameter("long_window_samples").value))
        self.short_window = deque(maxlen=int(self.get_parameter("short_window_samples").value))
        self.pose_history: list[tuple[float, tuple[float, float, float]]] = []
        self.recent_pose_margins = deque(maxlen=int(self.get_parameter("local_gradient_window_samples").value))

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        self.goal_pub = self.create_publisher(PoseStamped, "/franka_ee_goal", qos)
        self.gas_topic = str(self.get_parameter("gas_sensor_topic").value)
        self.create_subscription(
            GasSensor,
            self.gas_topic,
            self._on_gas,
            20,
        )

        self.gas_msg_count = 0
        self.first_gas_time = None
        self.last_gas_time = None
        self.raw = 0.0
        self.margin = 0.0
        self.baseline = 0.0
        self.strength = 0.0
        self.persistence = 0.0
        self.stability = 0.0
        self.trend = 0.0
        self.zone = "far"
        self.phase = "no_contact"
        self.confidence = 0.0
        self.max_margin_seen = 0.0

        self.state = "CAST"
        self.state_counts = {"CAST": 0, "SURGE": 0, "SPIRAL": 0}
        self.anchor: tuple[float, float, float] | None = None
        self.cast_samples: dict[str, list[tuple[float, tuple[float, float, float]]]] = {
            "right": [],
            "left": [],
            "up": [],
            "down": [],
            "forward": [],
            "backward": [],
        }
        self.cast_pattern_idx = 0
        self.active_probe: list[tuple[str, tuple[float, float, float]]] | None = None
        self.cast_theta = 0.0
        self.cast_last_offset = (0.0, 0.0, 0.0)
        self.surge_dir = (-1.0, 0.0, 0.0)
        self.surge_start_elapsed = 0.0
        self.surge_peak_margin = -1e9
        self.surge_lost_count = 0
        self.spiral_enter_count = 0
        self.spiral_mode = "PROBE"
        self.spiral_angle = 0.0
        self.spiral_radius = float(self.get_parameter("spiral_radius").value)
        self.spiral_probe_scale = float(self.get_parameter("spiral_probe_scale").value)
        self.spiral_drift_scale = float(self.get_parameter("spiral_drift_scale").value)
        self.spiral_probe_idx = 0
        self.spiral_probe_samples: dict[str, list[tuple[float, tuple[float, float, float]]]] = {
            "right": [],
            "left": [],
            "up": [],
            "down": [],
        }
        self.spiral_gradient = (0.0, 0.0, 0.0)
        self.spiral_loss_count = 0
        self.spiral_confirm_count = 0
        self.spiral_converged_count = 0
        self.spiral_cycle_best_margin = -1e9
        self.best_margin = -1e9
        self.best_pose: tuple[float, float, float] | None = None

        self.start_time = self.get_clock().now()
        self.last_control_time = self.start_time
        self.finished = False
        self.success = False
        self.stop_reason = "running"
        self.min_distance = float("inf")
        self.min_distance_confidence = 0.0
        self.min_distance_time = 0.0
        self.min_distance_pose: tuple[float, float, float] | None = None
        self.distance_confidence_satisfied = False
        self.path_length = 0.0
        self.last_pose: tuple[float, float, float] | None = None

        self.initial_state_meta: dict[str, object] = {}
        self.initial_ee_target: tuple[float, float, float] | None = None
        self.initial_goal = self._load_initial_goal()
        self.initial_goal_sent_time = None
        self.search_started = self.initial_goal is None
        self.timer = self.create_timer(0.2, self._tick)
        self.get_logger().info(
            "CAST/SURGE/SPIRAL runner started. "
            f"scenario={self.scenario_key}, state={self.initial_state_key}, "
            f"source={self.source}, success_radius={self.success_radius}m, "
            f"gas_topic={self.gas_topic}"
        )

    def _declare_params(self) -> None:
        self.declare_parameter("fixed_frame", "map")
        self.declare_parameter("sensor_frame", "fp3_hand_tcp")
        self.declare_parameter("gas_sensor_topic", "/fake_gas_sensor/Sensor_reading")
        self.declare_parameter("source_x", 1.0)
        self.declare_parameter("source_y", 4.95)
        self.declare_parameter("source_z", 0.7)
        self.declare_parameter("scenario_key", "manual")
        self.declare_parameter("initial_state_key", "manual")
        self.declare_parameter("param_set", "baseline")
        self.declare_parameter("output_csv", "/home/yiwei/ros2_ws/results/gsl_trials.csv")
        self.declare_parameter("timeout_s", 600.0)
        self.declare_parameter("success_radius", 0.25)
        self.declare_parameter("required_confidence", 0.6)
        self.declare_parameter("control_period", 2.0)
        self.declare_parameter("goal_z", 0.65)
        self.declare_parameter("goal_preset", "tilt_x_90")
        # pi means initial reach/probing axis points along -x, matching upwind for exp2/exp3.
        self.declare_parameter("search_heading_yaw", math.pi)
        self.declare_parameter("auto_start_from_initial_state", True)
        self.declare_parameter("initial_states_file", "")
        self.declare_parameter("initial_settle_s", 8.0)
        self.declare_parameter("require_gas_messages", True)
        self.declare_parameter("gas_wait_timeout_s", 30.0)

        self.declare_parameter("long_window_samples", 240)
        self.declare_parameter("short_window_samples", 25)
        self.declare_parameter("baseline_percentile", 0.10)
        self.declare_parameter("theta_low", 0.5)
        self.declare_parameter("theta_mid", 2.0)
        self.declare_parameter("theta_high", 5.0)
        self.declare_parameter("contact_threshold", 0.05)
        self.declare_parameter("auto_thresholds", True)
        self.declare_parameter("phase_confirm_persistence", 0.55)
        self.declare_parameter("phase_candidate_persistence", 0.15)
        self.declare_parameter("confidence_alpha", 0.12)
        self.declare_parameter("confidence_lambda_cv", 0.8)
        self.declare_parameter("local_gradient_window_samples", 30)

        self.declare_parameter("cast_step", 0.16)
        self.declare_parameter("cast_vertical_step", 0.10)
        self.declare_parameter("cast_probe_angle_deg", 16.0)
        self.declare_parameter("cast_switch_lambda", 0.75)
        self.declare_parameter("cast_min_side_samples", 3)
        self.declare_parameter("cast_yaw_radius_m", 0.24)
        self.declare_parameter("cast_pitch_radius_m", 0.16)
        self.declare_parameter("cast_reach_radius_m", 0.18)
        self.declare_parameter("surge_step_far", 0.16)
        self.declare_parameter("surge_step_near", 0.12)
        self.declare_parameter("surge_step_edge", 0.09)
        self.declare_parameter("surge_step_core", 0.05)
        self.declare_parameter("surge_weight_tau_s", 12.0)
        self.declare_parameter("surge_peak_drop_abs", 0.35)
        self.declare_parameter("surge_peak_drop_ratio", 0.35)
        self.declare_parameter("surge_loss_steps", 3)
        self.declare_parameter("spiral_enter_confidence", 0.45)
        self.declare_parameter("spiral_enter_steps", 3)
        self.declare_parameter("spiral_radius", 0.12)
        self.declare_parameter("spiral_probe_scale", 0.12)
        self.declare_parameter("spiral_drift_scale", 0.06)
        self.declare_parameter("spiral_radius_decay", 0.92)
        self.declare_parameter("spiral_min_radius", 0.03)
        self.declare_parameter("spiral_probe_steps", 16)
        self.declare_parameter("spiral_min_probe_scale", 0.025)
        self.declare_parameter("spiral_min_drift_scale", 0.015)
        self.declare_parameter("spiral_gradient_epsilon", 0.03)
        self.declare_parameter("spiral_converged_cycles", 3)
        self.declare_parameter("spiral_confirm_steps", 5)
        self.declare_parameter("spiral_loss_steps", 3)
        self.declare_parameter("workspace_min_x", -0.1)
        self.declare_parameter("workspace_max_x", 10.0)
        self.declare_parameter("workspace_min_y", -0.1)
        self.declare_parameter("workspace_max_y", 6.1)
        self.declare_parameter("workspace_min_z", 0.25)
        self.declare_parameter("workspace_max_z", 1.15)

    def _load_initial_goal(self) -> tuple[float, float, float] | None:
        if not bool(self.get_parameter("auto_start_from_initial_state").value):
            return None
        path_param = str(self.get_parameter("initial_states_file").value)
        if path_param:
            path = Path(path_param).expanduser()
        else:
            path = (
                Path(get_package_share_directory("test_env"))
                / "scenarios"
                / "10x6_empty_room"
                / "initial_states.yaml"
            )
        if not path.exists() or self.scenario_key == "manual" or self.initial_state_key == "manual":
            return None
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        try:
            self.initial_state_meta = data["scenarios"][self.scenario_key]["states"][self.initial_state_key]
            target = self.initial_state_meta["ee_target"]
            self.initial_ee_target = (float(target[0]), float(target[1]), float(target[2]))
            return self.initial_ee_target
        except KeyError:
            self.get_logger().warn(
                f"Could not find initial state {self.scenario_key}/{self.initial_state_key} in {path}"
            )
            return None

    def _on_gas(self, msg: GasSensor) -> None:
        now = self.get_clock().now()
        if self.gas_msg_count == 0:
            self.first_gas_time = now
        self.gas_msg_count += 1
        self.last_gas_time = now
        self.raw = float(msg.raw)
        self.long_window.append(self.raw)
        self.baseline = _percentile(list(self.long_window), float(self.get_parameter("baseline_percentile").value))
        self.margin = self.raw - self.baseline
        self.max_margin_seen = max(self.max_margin_seen, self.margin)
        self.short_window.append((self._elapsed(), self.margin, self.raw))
        self._assess()

    def _assess(self) -> None:
        margins = [m for _, m, _ in self.short_window]
        raws = [r for _, _, r in self.short_window]
        if not margins:
            return
        if self.auto_thresholds and self.max_margin_seen > self.theta_high:
            self.theta_low = max(self.theta_low, 0.15 * self.max_margin_seen)
            self.theta_mid = max(self.theta_mid, 0.40 * self.max_margin_seen)
            self.theta_high = max(self.theta_high, 0.70 * self.max_margin_seen)

        self.strength = mean(margins)
        self.persistence = sum(1 for m in margins if m > self.contact_threshold) / len(margins)
        self.stability = pstdev(margins) if len(margins) > 1 else 0.0
        if len(margins) >= 6:
            n = max(3, len(margins) // 3)
            dt = max(1e-3, self.short_window[-1][0] - self.short_window[0][0])
            self.trend = (mean(margins[-n:]) - mean(margins[:n])) / dt
        else:
            self.trend = 0.0

        m = self.margin
        if m >= self.theta_high:
            self.zone = "core"
        elif m >= self.theta_mid:
            self.zone = "edge"
        elif m >= self.theta_low:
            self.zone = "near"
        else:
            self.zone = "far"

        confirm_p = float(self.get_parameter("phase_confirm_persistence").value)
        cand_p = float(self.get_parameter("phase_candidate_persistence").value)
        stable_limit = max(0.1, abs(self.strength) * 1.5)
        if self.strength >= self.theta_mid and self.persistence >= confirm_p and self.stability <= stable_limit:
            self.phase = "confirmed"
        elif self.strength >= self.theta_low or self.persistence >= cand_p:
            self.phase = "candidate"
        else:
            self.phase = "no_contact"
        if self.phase == "confirmed" and self.zone == "far":
            self.zone = "near"
        if self.phase == "no_contact" and self.zone == "core":
            self.zone = "edge"

        hit_rate = sum(1 for m in margins if m > self.theta_low) / len(margins)
        denom = max(1e-6, self.theta_high - self.theta_low)
        strength_score = _clamp((self.strength - self.theta_low) / denom, 0.0, 1.0)
        cv = (pstdev(raws) if len(raws) > 1 else 0.0) / (abs(mean(raws)) + 1e-6)
        inst = strength_score * hit_rate * math.exp(-float(self.get_parameter("confidence_lambda_cv").value) * cv)
        alpha = float(self.get_parameter("confidence_alpha").value)
        self.confidence = (1.0 - alpha) * self.confidence + alpha * inst

    def _tick(self) -> None:
        if self.finished:
            return
        pose = self._lookup_pose()
        if not self.search_started and self.initial_goal is not None:
            self._settle_initial_goal(pose)
            return
        if pose is not None:
            self._update_metrics(pose)
        elapsed = self._elapsed()
        if self.distance_confidence_satisfied:
            reason = "debug_distance_reached" if self.required_confidence <= 0.0 else "distance_confidence_confirmed"
            self._finish(True, reason)
            return
        if elapsed >= self.timeout_s:
            self._finish(False, "timeout")
            return
        now = self.get_clock().now()
        if (now - self.last_control_time).nanoseconds / 1e9 < self.control_period:
            return
        self.last_control_time = now
        if bool(self.get_parameter("require_gas_messages").value) and self.gas_msg_count == 0:
            gas_wait_timeout_s = float(self.get_parameter("gas_wait_timeout_s").value)
            if gas_wait_timeout_s > 0.0 and elapsed >= gas_wait_timeout_s:
                self._finish(False, "no_gas_messages")
            else:
                self.get_logger().warn(
                    f"Waiting for gas messages on {self.gas_topic}; "
                    "check that the GADEN/Franka launch is still running and "
                    "that /fake_gas_sensor has a publisher.",
                    throttle_duration_sec=5.0,
                )
            return
        if pose is None or len(self.short_window) < 3:
            return
        if self.anchor is None:
            self.anchor = pose
        self.state_counts[self.state] += 1
        if self.state == "CAST":
            self._step_cast(pose)
        elif self.state == "SURGE":
            self._step_surge(pose)
        elif self.state == "SPIRAL":
            self._step_spiral(pose)

    def _settle_initial_goal(self, pose: tuple[float, float, float] | None) -> None:
        now = self.get_clock().now()
        if self.initial_goal_sent_time is None:
            self.initial_goal_sent_time = now
            self.anchor = self.initial_goal
            self._publish_goal(self.initial_goal)
            self.get_logger().info(
                "Moving to requested initial state before starting the trial; "
                f"settle={float(self.get_parameter('initial_settle_s').value):.1f}s"
            )
            return
        settle_s = max(0.0, float(self.get_parameter("initial_settle_s").value))
        settled_for = (now - self.initial_goal_sent_time).nanoseconds / 1e9
        if (now - self.last_control_time).nanoseconds / 1e9 >= self.control_period:
            self.last_control_time = now
            self._publish_goal(self.initial_goal)
        if settled_for < settle_s or pose is None:
            return
        self._begin_search_from_initial_pose(pose)

    def _begin_search_from_initial_pose(self, pose: tuple[float, float, float]) -> None:
        now = self.get_clock().now()
        self.start_time = now
        self.last_control_time = now
        self.search_started = True
        self.anchor = pose
        self.initial_goal = None

        self.long_window.clear()
        self.short_window.clear()
        self.pose_history.clear()
        self.recent_pose_margins.clear()
        self.gas_msg_count = 0
        self.first_gas_time = None
        self.last_gas_time = None
        self.raw = 0.0
        self.margin = 0.0
        self.baseline = 0.0
        self.strength = 0.0
        self.persistence = 0.0
        self.stability = 0.0
        self.trend = 0.0
        self.zone = "far"
        self.phase = "no_contact"
        self.confidence = 0.0
        self.max_margin_seen = 0.0

        self.path_length = 0.0
        self.last_pose = None
        self.min_distance = float("inf")
        self.min_distance_confidence = 0.0
        self.min_distance_time = 0.0
        self.min_distance_pose = None
        self.distance_confidence_satisfied = False
        self.best_margin = -1e9
        self.best_pose = None
        self.state = "CAST"
        self.state_counts = {"CAST": 0, "SURGE": 0, "SPIRAL": 0}
        self.get_logger().info(
            "Initial state settled; starting trial clock from "
            f"pose=({pose[0]:.2f},{pose[1]:.2f},{pose[2]:.2f})"
        )

    def _lookup_pose(self) -> tuple[float, float, float] | None:
        try:
            tf = self.tf_buffer.lookup_transform(self.fixed_frame, self.sensor_frame, Time())
        except TransformException as exc:
            self.get_logger().warn(f"Waiting for TF {self.fixed_frame}->{self.sensor_frame}: {exc}", throttle_duration_sec=3.0)
            return None
        t = tf.transform.translation
        return (float(t.x), float(t.y), float(t.z))

    def _update_metrics(self, pose: tuple[float, float, float]) -> None:
        if self.last_pose is not None:
            d = _dist(pose, self.last_pose)
            if d < 0.25:
                self.path_length += d
        self.last_pose = pose
        self.pose_history.append((self._elapsed(), pose))
        self.recent_pose_margins.append((self._elapsed(), self.margin, pose))
        current_distance = _dist(pose, self.source)
        if current_distance < self.min_distance:
            self.min_distance = current_distance
            self.min_distance_confidence = self.confidence
            self.min_distance_time = self._elapsed()
            self.min_distance_pose = pose
        if current_distance <= self.success_radius and self.confidence >= self.required_confidence:
            self.distance_confidence_satisfied = True
        if self.margin > self.best_margin:
            self.best_margin = self.margin
            self.best_pose = pose

    def _step_cast(self, pose: tuple[float, float, float]) -> None:
        if self.active_probe is not None:
            for name, offset in self.active_probe:
                self.cast_samples[name].append((self.margin, offset))
            self.active_probe = None
        if self._should_switch_cast_to_surge():
            direction = self._estimate_cast_direction()
            if direction is not None:
                self.surge_dir = direction
                self.state = "SURGE"
                self.surge_start_elapsed = self._elapsed()
                self.surge_peak_margin = self.margin
                self.surge_lost_count = 0
                self.spiral_enter_count = 0
                self.get_logger().info(f"CAST -> SURGE dir={tuple(round(v, 3) for v in direction)}")
                return

        target, active_probe = self._next_cast_target()
        self.active_probe = active_probe
        self._publish_goal(target)

    def _next_cast_target(self) -> tuple[tuple[float, float, float], list[tuple[str, tuple[float, float, float]]]]:
        """Thesis-style CAST: adaptive saddle scan plus alternating yaw probe."""
        assert self.anchor is not None
        hx, hy = self.heading
        lx, ly = self.lateral

        yaw_amp_deg, pitch_amp_deg, reach_amp_deg, omega = self._cast_zone_amplitudes()
        phase_scale = {"confirmed": 0.55, "candidate": 0.75}.get(self.phase, 1.0)
        yaw_amp = float(self.get_parameter("cast_yaw_radius_m").value) * math.sin(math.radians(yaw_amp_deg)) * phase_scale
        pitch_amp = float(self.get_parameter("cast_pitch_radius_m").value) * math.sin(math.radians(pitch_amp_deg)) * phase_scale
        reach_amp = float(self.get_parameter("cast_reach_radius_m").value) * math.sin(math.radians(reach_amp_deg)) * phase_scale

        self.cast_theta += omega * max(0.1, self.control_period)
        # The thesis provides the CAST base trajectory graphically. This Cartesian
        # equivalent preserves the stated ingredients: yaw sweep, pitch sweep,
        # reach modulation, continuous saddle-like motion, and alternating probe.
        base_reach = reach_amp * math.sin(self.cast_theta)
        base_lateral = yaw_amp * math.sin(self.cast_theta) * math.cos(self.cast_theta)
        base_vertical = pitch_amp * math.sin(2.0 * self.cast_theta)

        probe_sign = 1.0 if self.cast_pattern_idx % 2 == 0 else -1.0
        self.cast_pattern_idx += 1
        probe_angle = math.radians(float(self.get_parameter("cast_probe_angle_deg").value))
        probe_lateral = probe_sign * float(self.get_parameter("cast_yaw_radius_m").value) * math.sin(probe_angle) * phase_scale

        offset = (
            base_reach * hx + (base_lateral + probe_lateral) * lx,
            base_reach * hy + (base_lateral + probe_lateral) * ly,
            base_vertical,
        )
        target = (
            self.anchor[0] + offset[0],
            self.anchor[1] + offset[1],
            self.anchor[2] + offset[2],
        )
        active_probe = [("right" if probe_sign > 0.0 else "left", offset)]
        dz = offset[2] - self.cast_last_offset[2]
        if dz > 1e-4:
            active_probe.append(("up", offset))
        elif dz < -1e-4:
            active_probe.append(("down", offset))
        reach_delta = (offset[0] - self.cast_last_offset[0]) * hx + (offset[1] - self.cast_last_offset[1]) * hy
        if reach_delta > 1e-4:
            active_probe.append(("forward", offset))
        elif reach_delta < -1e-4:
            active_probe.append(("backward", offset))
        self.cast_last_offset = offset
        return target, active_probe

    def _cast_zone_amplitudes(self) -> tuple[float, float, float, float]:
        table = {
            "far": (40.0, 35.0, 20.0, 0.8),
            "near": (25.0, 22.0, 15.0, 1.0),
            "edge": (35.0, 30.0, 20.0, 0.9),
            "core": (10.0, 10.0, 5.0, 1.2),
        }
        return table.get(self.zone, table["far"])

    def _zone_reference_threshold(self) -> float:
        return self.theta_mid if self.zone in ("edge", "core") else self.theta_low

    def _should_switch_cast_to_surge(self) -> bool:
        if self.phase not in ("candidate", "confirmed"):
            return False
        if self.trend <= 0.0:
            return False
        m_th = float(self.get_parameter("cast_switch_lambda").value) * self._zone_reference_threshold()
        if self.margin < m_th:
            return False
        return self._cast_has_enough_samples()

    @staticmethod
    def _sample_mean(samples: list[tuple[float, tuple[float, float, float]]]) -> float | None:
        if not samples:
            return None
        return mean(m for m, _ in samples)

    @staticmethod
    def _signed_diff(a: float | None, b: float | None, deadband: float) -> float:
        if a is None or b is None or abs(a - b) <= deadband:
            return 0.0
        return math.copysign(1.0, a - b)

    def _cast_has_enough_samples(self) -> bool:
        min_side = int(self.get_parameter("cast_min_side_samples").value)
        return (
            len(self.cast_samples["right"]) >= min_side
            and len(self.cast_samples["left"]) >= min_side
        )

    def _estimate_cast_direction(self) -> tuple[float, float, float] | None:
        r_mean = self._sample_mean(self.cast_samples["right"])
        l_mean = self._sample_mean(self.cast_samples["left"])
        u_mean = self._sample_mean(self.cast_samples["up"])
        d_mean = self._sample_mean(self.cast_samples["down"])
        f_mean = self._sample_mean(self.cast_samples["forward"])
        b_mean = self._sample_mean(self.cast_samples["backward"])
        deadband = max(0.02, 0.1 * self.contact_threshold)
        dyaw = self._signed_diff(r_mean, l_mean, deadband)
        dpitch = self._signed_diff(u_mean, d_mean, deadband)
        dreach = self._signed_diff(f_mean, b_mean, deadband)
        if dreach == 0.0 and abs(self.trend) > 1e-6:
            dreach = math.copysign(1.0, self.trend)
        hx, hy = self.heading
        lx, ly = self.lateral
        # Thesis Eq. (30): yaw has highest reliability, reach second, pitch lowest.
        vx = 2.0 * dyaw * lx + 1.2 * dreach * hx
        vy = 2.0 * dyaw * ly + 1.2 * dreach * hy
        vz = 0.5 * dpitch
        if abs(vx) + abs(vy) + abs(vz) < 1e-9 and self.best_pose is not None and self.anchor is not None:
            vx = self.best_pose[0] - self.anchor[0]
            vy = self.best_pose[1] - self.anchor[1]
            vz = self.best_pose[2] - self.anchor[2]
        n = math.sqrt(vx * vx + vy * vy + vz * vz)
        if n < 1e-9:
            return None
        return (vx / n, vy / n, vz / n)

    def _step_surge(self, pose: tuple[float, float, float]) -> None:
        self.surge_peak_margin = max(self.surge_peak_margin, self.margin)
        drop_abs = float(self.get_parameter("surge_peak_drop_abs").value)
        drop_ratio = float(self.get_parameter("surge_peak_drop_ratio").value) * max(0.0, self.surge_peak_margin)
        significant_drop = self.surge_peak_margin > self.theta_low and (self.surge_peak_margin - self.margin) > max(drop_abs, drop_ratio)
        if self.phase == "no_contact" or self.margin < 0.0 or self.trend < -0.03 or significant_drop:
            self.surge_lost_count += 1
        else:
            self.surge_lost_count = max(0, self.surge_lost_count - 1)
        if self.surge_lost_count >= int(self.get_parameter("surge_loss_steps").value):
            self._reset_cast(pose)
            self.get_logger().info("SURGE -> CAST (plume lost)")
            return
        if (
            self.phase == "confirmed"
            and self.zone == "core"
            and self.confidence >= float(self.get_parameter("spiral_enter_confidence").value)
        ):
            self.spiral_enter_count += 1
        else:
            self.spiral_enter_count = 0
        if self.spiral_enter_count >= int(self.get_parameter("spiral_enter_steps").value):
            self.state = "SPIRAL"
            self.anchor = pose
            self.spiral_radius = float(self.get_parameter("spiral_radius").value)
            self.spiral_probe_scale = float(self.get_parameter("spiral_probe_scale").value)
            self.spiral_drift_scale = float(self.get_parameter("spiral_drift_scale").value)
            self.spiral_mode = "PROBE"
            self.spiral_probe_idx = 0
            self.spiral_angle = 0.0
            self.spiral_loss_count = 0
            self.spiral_confirm_count = 0
            self.spiral_converged_count = 0
            self.spiral_cycle_best_margin = self.margin
            for samples in self.spiral_probe_samples.values():
                samples.clear()
            self.get_logger().info("SURGE -> SPIRAL")
            return

        step = {
            "far": float(self.get_parameter("surge_step_far").value),
            "near": float(self.get_parameter("surge_step_near").value),
            "edge": float(self.get_parameter("surge_step_edge").value),
            "core": float(self.get_parameter("surge_step_core").value),
        }.get(self.zone, 0.10)
        if self.phase == "confirmed":
            step *= 1.15
        direction = self._surge_direction(pose)
        target = (
            pose[0] + step * direction[0],
            pose[1] + step * direction[1],
            pose[2] + step * direction[2],
        )
        self._publish_goal(target)

    def _surge_direction(self, pose: tuple[float, float, float]) -> tuple[float, float, float]:
        local = self._local_gradient_direction(pose)
        elapsed = max(0.0, self._elapsed() - self.surge_start_elapsed)
        tau = max(1e-3, float(self.get_parameter("surge_weight_tau_s").value))
        w = math.exp(-elapsed / tau)
        vx = w * self.surge_dir[0] + (1.0 - w) * local[0]
        vy = w * self.surge_dir[1] + (1.0 - w) * local[1]
        vz = w * self.surge_dir[2] + (1.0 - w) * local[2]
        n = math.sqrt(vx * vx + vy * vy + vz * vz)
        if n < 1e-9:
            return self.surge_dir
        return (vx / n, vy / n, vz / n)

    def _local_gradient_direction(self, pose: tuple[float, float, float]) -> tuple[float, float, float]:
        if len(self.recent_pose_margins) < 3:
            return self.surge_dir
        best = max(self.recent_pose_margins, key=lambda item: item[1])
        if best[1] <= self.margin + 1e-6:
            if self.trend >= 0.0:
                return self.surge_dir
            return (-self.surge_dir[0], -self.surge_dir[1], -self.surge_dir[2])
        bx, by, bz = best[2]
        vx, vy, vz = bx - pose[0], by - pose[1], bz - pose[2]
        n = math.sqrt(vx * vx + vy * vy + vz * vz)
        if n < 1e-6:
            return self.surge_dir
        return (vx / n, vy / n, vz / n)

    def _step_spiral(self, pose: tuple[float, float, float]) -> None:
        if self.phase == "no_contact" or self.zone == "far" or self.confidence < 0.15:
            self.spiral_loss_count += 1
        else:
            self.spiral_loss_count = max(0, self.spiral_loss_count - 1)
        if self.spiral_loss_count >= int(self.get_parameter("spiral_loss_steps").value):
            if self.confidence >= 0.25 or self.margin >= self.theta_low:
                self.state = "SURGE"
                self.anchor = pose
                self.surge_start_elapsed = self._elapsed()
                self.surge_lost_count = 0
                self.get_logger().info("SPIRAL -> SURGE (cue degraded, still trackable)")
            else:
                self._reset_cast(pose)
                self.get_logger().info("SPIRAL -> CAST (cue degraded)")
            return

        if self.phase == "confirmed" and self.zone == "core" and self.confidence >= self.required_confidence:
            self.spiral_confirm_count += 1
        else:
            self.spiral_confirm_count = 0
        if self.spiral_confirm_count >= int(self.get_parameter("spiral_confirm_steps").value):
            self._finish(True, "stop_mode_confirmed")
            return

        if self.spiral_mode == "DRIFT":
            self._step_spiral_drift(pose)
            return
        self._step_spiral_probe(pose)

    def _step_spiral_probe(self, pose: tuple[float, float, float]) -> None:
        assert self.anchor is not None
        self.spiral_cycle_best_margin = max(self.spiral_cycle_best_margin, self.margin)
        steps = max(4, int(self.get_parameter("spiral_probe_steps").value))
        self.spiral_angle += 2.0 * math.pi / steps
        r = self.spiral_probe_scale
        hx, hy = self.heading
        lx, ly = self.lateral
        lateral = r * math.sin(self.spiral_angle)
        vertical = 0.75 * r * math.sin(2.0 * self.spiral_angle)
        reach = 0.35 * r * math.cos(self.spiral_angle)
        offset = (
            reach * hx + lateral * lx,
            reach * hy + lateral * ly,
            vertical,
        )
        target = (
            self.anchor[0] + offset[0],
            self.anchor[1] + offset[1],
            self.anchor[2] + offset[2],
        )
        if lateral >= 0.0:
            self.spiral_probe_samples["right"].append((self.margin, offset))
        else:
            self.spiral_probe_samples["left"].append((self.margin, offset))
        if vertical >= 0.0:
            self.spiral_probe_samples["up"].append((self.margin, offset))
        else:
            self.spiral_probe_samples["down"].append((self.margin, offset))
        self.spiral_probe_idx += 1
        if self.spiral_probe_idx >= steps:
            self.spiral_gradient = self._estimate_spiral_gradient()
            if self._spiral_is_converged():
                self.spiral_converged_count += 1
            else:
                self.spiral_converged_count = 0
            if self.spiral_converged_count >= int(self.get_parameter("spiral_converged_cycles").value):
                self.get_logger().info("SPIRAL holding for source confirmation")
                target = pose
            else:
                self.spiral_mode = "DRIFT"
        self._publish_goal(target)

    def _step_spiral_drift(self, pose: tuple[float, float, float]) -> None:
        assert self.anchor is not None
        gx, gy, gz = self.spiral_gradient
        n = math.sqrt(gx * gx + gy * gy + gz * gz)
        if n < 1e-9 and self.best_pose is not None:
            gx = self.best_pose[0] - self.anchor[0]
            gy = self.best_pose[1] - self.anchor[1]
            gz = self.best_pose[2] - self.anchor[2]
            n = math.sqrt(gx * gx + gy * gy + gz * gz)
        if n < 1e-9:
            gx, gy, gz, n = self.surge_dir[0], self.surge_dir[1], self.surge_dir[2], 1.0
        drift = self.spiral_drift_scale
        target = (
            self.anchor[0] + drift * gx / n,
            self.anchor[1] + drift * gy / n,
            self.anchor[2] + drift * gz / n,
        )
        self.anchor = target
        decay = float(self.get_parameter("spiral_radius_decay").value)
        self.spiral_probe_scale = max(
            float(self.get_parameter("spiral_min_probe_scale").value),
            self.spiral_probe_scale * decay,
        )
        self.spiral_drift_scale = max(
            float(self.get_parameter("spiral_min_drift_scale").value),
            self.spiral_drift_scale * decay,
        )
        self.spiral_mode = "PROBE"
        self.spiral_probe_idx = 0
        self.spiral_angle = 0.0
        self.spiral_cycle_best_margin = self.margin
        for samples in self.spiral_probe_samples.values():
            samples.clear()
        self._publish_goal(target)

    def _estimate_spiral_gradient(self) -> tuple[float, float, float]:
        r_mean = self._sample_mean(self.spiral_probe_samples["right"])
        l_mean = self._sample_mean(self.spiral_probe_samples["left"])
        u_mean = self._sample_mean(self.spiral_probe_samples["up"])
        d_mean = self._sample_mean(self.spiral_probe_samples["down"])
        deadband = max(float(self.get_parameter("spiral_gradient_epsilon").value), 0.1 * self.contact_threshold)
        lr = self._signed_diff(r_mean, l_mean, deadband)
        ud = self._signed_diff(u_mean, d_mean, deadband)
        hx, hy = self.heading
        lx, ly = self.lateral
        reach = math.copysign(1.0, self.trend) if abs(self.trend) > 1e-6 else 0.0
        return (lr * lx + 0.4 * reach * hx, lr * ly + 0.4 * reach * hy, ud)

    def _spiral_is_converged(self) -> bool:
        gx, gy, gz = self.spiral_gradient
        gmag = math.sqrt(gx * gx + gy * gy + gz * gz)
        small_gradient = gmag <= float(self.get_parameter("spiral_gradient_epsilon").value)
        small_probe = self.spiral_probe_scale <= float(self.get_parameter("spiral_min_probe_scale").value) + 1e-9
        small_drift = self.spiral_drift_scale <= float(self.get_parameter("spiral_min_drift_scale").value) + 1e-9
        negligible_improvement = (self.spiral_cycle_best_margin - self.best_margin) <= max(0.02, 0.02 * abs(self.best_margin))
        return (small_gradient or negligible_improvement) and small_probe and small_drift

    def _reset_cast(self, pose: tuple[float, float, float]) -> None:
        self.state = "CAST"
        self.anchor = pose
        self.cast_pattern_idx = 0
        self.cast_last_offset = (0.0, 0.0, 0.0)
        self.active_probe = None
        self.spiral_enter_count = 0
        for samples in self.cast_samples.values():
            samples.clear()

    def _publish_goal(self, target: tuple[float, float, float]) -> None:
        x = _clamp(target[0], float(self.get_parameter("workspace_min_x").value), float(self.get_parameter("workspace_max_x").value))
        y = _clamp(target[1], float(self.get_parameter("workspace_min_y").value), float(self.get_parameter("workspace_max_y").value))
        z = _clamp(target[2], float(self.get_parameter("workspace_min_z").value), float(self.get_parameter("workspace_max_z").value))
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.fixed_frame
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z
        if self.goal_preset == "identity":
            msg.pose.orientation.w = 1.0
        else:
            # Same as publish_ee_goal default: rotate TCP around X by +90 deg.
            msg.pose.orientation.x = math.sin(math.pi / 4.0)
            msg.pose.orientation.w = math.cos(math.pi / 4.0)
        self.goal_pub.publish(msg)
        self.get_logger().info(
            f"{self.state}: goal=({x:.2f},{y:.2f},{z:.2f}) raw={self.raw:.3f} "
            f"m={self.margin:.3f} phase={self.phase} zone={self.zone} "
            f"c={self.confidence:.2f} gas_n={self.gas_msg_count}",
            throttle_duration_sec=0.5,
        )

    def _elapsed(self) -> float:
        return (self.get_clock().now() - self.start_time).nanoseconds / 1e9

    def _finish(self, success: bool, reason: str) -> None:
        self.finished = True
        self.success = success
        self.stop_reason = reason
        self._write_csv()
        self.get_logger().info(
            f"Finished: success={success} reason={reason} time={self._elapsed():.1f}s "
            f"path={self.path_length:.2f}m min_dist={self.min_distance:.3f}m"
        )

    def _write_csv(self) -> None:
        initial_distance = (
            _dist(self.initial_ee_target, self.source)
            if self.initial_ee_target is not None
            else float("inf")
        )
        base_pose = self.initial_state_meta.get("base_pose", ["", "", ""])
        ee_target = self.initial_state_meta.get("ee_target", ["", "", ""])
        row = {
            "scenario": self.scenario_key,
            "initial_state": self.initial_state_key,
            "initial_label": str(self.initial_state_meta.get("label", "")),
            "source_relation": str(self.initial_state_meta.get("source_relation", "")),
            "plume_relation": str(self.initial_state_meta.get("plume_relation", "")),
            "wind_relation": str(self.initial_state_meta.get("wind_relation", "")),
            "expected_gas_cue": str(self.initial_state_meta.get("expected_gas_cue", "")),
            "base_x": str(base_pose[0]) if len(base_pose) > 0 else "",
            "base_y": str(base_pose[1]) if len(base_pose) > 1 else "",
            "base_yaw": str(base_pose[2]) if len(base_pose) > 2 else "",
            "initial_ee_x": str(ee_target[0]) if len(ee_target) > 0 else "",
            "initial_ee_y": str(ee_target[1]) if len(ee_target) > 1 else "",
            "initial_ee_z": str(ee_target[2]) if len(ee_target) > 2 else "",
            "param_set": self.param_set,
            "success": int(self.success),
            "stop_reason": self.stop_reason,
            "time_s": f"{self._elapsed():.3f}",
            "path_length_m": f"{self.path_length:.4f}",
            "initial_distance_m": f"{initial_distance:.4f}",
            "min_distance_m": f"{self.min_distance:.4f}",
            "min_distance_confidence": f"{self.min_distance_confidence:.6f}",
            "min_distance_time_s": f"{self.min_distance_time:.3f}",
            "final_distance_m": f"{_dist(self.last_pose, self.source):.4f}" if self.last_pose is not None else "inf",
            "final_raw": f"{self.raw:.6f}",
            "final_margin": f"{self.margin:.6f}",
            "final_confidence": f"{self.confidence:.6f}",
            "max_margin_seen": f"{self.max_margin_seen:.6f}",
            "gas_msg_count": self.gas_msg_count,
            "cast_steps": self.state_counts["CAST"],
            "surge_steps": self.state_counts["SURGE"],
            "spiral_steps": self.state_counts["SPIRAL"],
            "theta_low": f"{self.theta_low:.6f}",
            "theta_mid": f"{self.theta_mid:.6f}",
            "theta_high": f"{self.theta_high:.6f}",
        }
        fieldnames = list(row.keys())
        exists = self.output_csv.exists()
        if exists:
            with self.output_csv.open(newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                existing_header = next(reader, [])
            if existing_header and existing_header != fieldnames:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = self.output_csv.with_name(
                    f"{self.output_csv.stem}_legacy_schema_{stamp}{self.output_csv.suffix}"
                )
                self.output_csv.rename(backup)
                self.get_logger().warn(
                    "CSV header changed; moved previous results to "
                    f"{backup} and started a clean file."
                )
                exists = False
        with self.output_csv.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not exists:
                writer.writeheader()
            writer.writerow(row)

    def close(self) -> None:
        if not self.finished:
            self._finish(False, "interrupted")


def main() -> None:
    rclpy.init()
    node = SurgeCastSpiralGSL()
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
