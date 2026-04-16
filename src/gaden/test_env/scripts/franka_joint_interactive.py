#!/usr/bin/env python3
"""
订阅 /franka_joint_target (sensor_msgs/JointState)，按关节名更新位置，并持续发布 /fp3_arm/joint_states。

用于在 GADEN + RViz 中控制 Franka（基座不动，只动臂）。与 robot_state_publisher 配套使用。

示例（只动第一个臂关节）:
  ros2 topic pub --once /franka_joint_target sensor_msgs/msg/JointState \\
    "{name: ['fp3_joint1'], position: [0.3]}"

一次设置多个关节时 name 与 position 长度需一致。

/franka_joint_target 写的是目标关节角；实际发出的是按 max_joint_velocity 从当前角平滑过去。
未发 IK 前为 fp3 合法就绪角（joint4/joint6 不能为 0），故 echo 非全零属正常。

若仅调高/调低 max_joint_velocity 而末端目标与上次完全相同，franka_fp3_ik_goal 可能因
skip_duplicate_cartesian 不再发布 /franka_joint_target；此时应微调目标位姿或暂时关闭该参数。
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import rclpy
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState

# 与 gaden_franka_fp3_launch 中 robot_state_publisher 的 remap 一致；勿用裸 joint_states，以免与其它节点混用
FP3_ARM_JOINT_STATES_TOPIC = "/fp3_arm/joint_states"
# 与 launch 里 franka_robot_state_publisher 的 qos_overrides 一致（RELIABLE + depth），避免与默认 SensorData 订阅端不匹配导致 RSP 收不到关节状态
_FP3_JS_QOS = QoSProfile(
    depth=20,
    reliability=ReliabilityPolicy.RELIABLE,
)

# 与 franka_fp3_ik_goal._FP3_READY_SEED_RAD 一致（见脚本内 FK 说明）。
_FP3_READY_DEFAULT_RAD: dict[str, float] = {
    "fp3_joint1": 0.0,
    "fp3_joint2": -0.3,
    "fp3_joint3": 0.0,
    "fp3_joint4": -1.4,
    "fp3_joint5": 0.0,
    "fp3_joint6": 1.7,
    "fp3_joint7": 0.0,
}
_FP3_LIMITS_RAD: dict[str, tuple[float, float]] = {
    "fp3_joint1": (-2.9007, 2.9007),
    "fp3_joint2": (-1.8361, 1.8361),
    "fp3_joint3": (-2.9007, 2.9007),
    "fp3_joint4": (-3.0770, -0.1169),
    "fp3_joint5": (-2.8763, 2.8763),
    "fp3_joint6": (0.4398, 4.6216),
    "fp3_joint7": (-3.0508, 3.0508),
}


def _clamp_fp3_named(name: str, v: float) -> float:
    lim = _FP3_LIMITS_RAD.get(name)
    if lim is None:
        return v
    lo, hi = lim
    return max(lo, min(hi, v))
# depth 太小易丢 IK 仅发的一条 JointState，表现为 /fp3_arm/joint_states 永远跟不上目标
_TARGET_IN_QOS = QoSProfile(
    depth=20,
    reliability=ReliabilityPolicy.RELIABLE,
)


def _clamp_max_vel(v: float) -> float:
    """限制角速度范围；必须拒绝 nan/inf，否则 step 变 nan 后机械臂会「冻住」。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.25
    if not math.isfinite(x):
        return 0.25
    return max(0.05, min(5.0, x))


def _parse_max_joint_velocity(p: Parameter) -> float | None:
    """从 Parameter 解析出 max_joint_velocity；无法解析时返回 None。"""
    if p.type_ == Parameter.Type.DOUBLE:
        return float(p.value)
    if p.type_ == Parameter.Type.INTEGER:
        return float(int(p.value))
    if p.type_ == Parameter.Type.STRING:
        try:
            return float(str(p.value).strip())
        except (TypeError, ValueError):
            return None
    return None


def _joint_names_from_urdf(urdf: str) -> list:
    if not urdf.strip():
        return []
    root = ET.fromstring(urdf)
    names = []
    for el in root.iter():
        if el.tag.split("}")[-1] != "joint":
            continue
        jtype = el.attrib.get("type", "")
        if jtype not in ("revolute", "continuous", "prismatic"):
            continue
        name = el.attrib.get("name")
        if name:
            names.append(name)
    return names


class InteractiveJointStates(Node):
    def __init__(self):
        super().__init__("franka_joint_interactive")
        self.declare_parameter("robot_description", "")
        # 默认略保守，便于肉眼看到「逐步」运动；需要快可在运行时 param set 提高（过大时会像瞬间到位）
        self.declare_parameter("max_joint_velocity", 0.25)
        # 与常见显示器刷新率对齐，减轻与 RViz 不同步时的视觉抖动
        self.declare_parameter("publish_rate", 30.0)
        urdf = self.get_parameter("robot_description").get_parameter_value().string_value
        self._names = _joint_names_from_urdf(urdf)
        self._name_to_idx = {n: i for i, n in enumerate(self._names)}
        n = len(self._names)
        init_pos = [_FP3_READY_DEFAULT_RAD.get(name, 0.0) for name in self._names]
        self._positions = list(init_pos)
        self._goal_positions = list(init_pos)
        self._max_vel = _clamp_max_vel(
            float(self.get_parameter("max_joint_velocity").value)
        )
        rate = float(self.get_parameter("publish_rate").value)
        rate = max(rate, 5.0)
        self._dt = 1.0 / rate

        self.add_on_set_parameters_callback(self._on_param_change)

        self.pub = self.create_publisher(
            JointState, FP3_ARM_JOINT_STATES_TOPIC, _FP3_JS_QOS
        )
        self.create_subscription(
            JointState,
            "/franka_joint_target",
            self._on_target,
            _TARGET_IN_QOS,
        )
        self._timer = self.create_timer(self._dt, self._tick)
        # 首帧立即发一条 joint_states，避免等第一个 timer 周期前 RSP/IK 读到旧状态或全零
        self._tick()

        self.get_logger().info(
            f"Publishing joint_states for {len(self._names)} joints; "
            f"smooth max_vel={self._max_vel} rad/s; subscribe to /franka_joint_target"
        )

    def _on_param_change(self, params: list[Parameter]) -> SetParametersResult:
        for p in params:
            if p.name != "max_joint_velocity":
                continue
            raw = _parse_max_joint_velocity(p)
            if raw is None:
                return SetParametersResult(
                    successful=False,
                    reason="max_joint_velocity 须为有限数值（double/int 或可解析的字符串）",
                )
            self._max_vel = _clamp_max_vel(raw)
            self.get_logger().info(f"max_joint_velocity => {self._max_vel}")
        return SetParametersResult(successful=True)

    def _on_target(self, msg: JointState):
        if not msg.name or len(msg.name) != len(msg.position):
            self.get_logger().warn(
                "忽略 joint_target: name 与 position 长度须一致且非空"
            )
            return
        for name, pos in zip(msg.name, msg.position):
            idx = self._name_to_idx.get(name)
            if idx is None:
                self.get_logger().warn(f"未知关节名: {name}")
                continue
            self._goal_positions[idx] = _clamp_fp3_named(name, float(pos))

    def _tick(self):
        if not math.isfinite(self._max_vel) or not math.isfinite(self._dt):
            self._max_vel = _clamp_max_vel(0.25)
            rate = float(self.get_parameter("publish_rate").value)
            rate = max(rate, 5.0)
            if math.isfinite(rate):
                self._dt = 1.0 / rate
        step = self._max_vel * self._dt
        if not math.isfinite(step) or step <= 0.0:
            step = _clamp_max_vel(0.25) * self._dt
            if not math.isfinite(step):
                step = 0.25 / 30.0

        for i in range(len(self._positions)):
            g = self._goal_positions[i]
            p = self._positions[i]
            if not math.isfinite(g):
                g = 0.0
                self._goal_positions[i] = g
            if not math.isfinite(p):
                p = g
                self._positions[i] = p
            err = g - p
            if abs(err) <= step:
                self._positions[i] = g
            else:
                self._positions[i] = p + math.copysign(step, err)

        out = JointState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.name = list(self._names)
        # 舍入减轻浮点尾数在 RViz 中的微跳变观感
        out.position = [round(float(x), 5) for x in self._positions]
        self.pub.publish(out)


def main():
    rclpy.init()
    node = InteractiveJointStates()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    try:
        node.destroy_node()
    except Exception:
        pass
    try:
        rclpy.shutdown()
    except Exception:
        pass  # launch 可能已关掉 context，避免重复 rcl_shutdown 报错


if __name__ == "__main__":
    main()
