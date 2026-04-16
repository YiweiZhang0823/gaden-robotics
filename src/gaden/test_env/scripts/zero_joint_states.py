#!/usr/bin/env python3
"""发布 fp3 合法就绪关节（非全零），使 robot_state_publisher 能发布 TF（不依赖 joint_state_publisher 包）。"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState

FP3_ARM_JOINT_STATES_TOPIC = "/fp3_arm/joint_states"

# fp3 的 joint4/joint6 不能为 0（见 franka_description/robots/fp3/joint_limits.yaml），全零会显示折断。
_FP3_READY_DEFAULT_RAD: dict[str, float] = {
    "fp3_joint1": 0.0,
    "fp3_joint2": -0.3,
    "fp3_joint3": 0.0,
    "fp3_joint4": -1.4,
    "fp3_joint5": 0.0,
    "fp3_joint6": 1.7,
    "fp3_joint7": 0.0,
}
# 与 gaden_franka_fp3_launch 中 franka_robot_state_publisher 的 qos_overrides 一致
_FP3_JS_QOS = QoSProfile(
    depth=20,
    reliability=ReliabilityPolicy.RELIABLE,
)


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


class ZeroJointStates(Node):
    def __init__(self):
        super().__init__("zero_joint_states")
        self.declare_parameter("robot_description", "")
        urdf = self.get_parameter("robot_description").get_parameter_value().string_value
        self._names = _joint_names_from_urdf(urdf)
        self.get_logger().info(
            f"Publishing fp3 ready joint_states for {len(self._names)} joints (fallback publisher)"
        )
        self._pub = self.create_publisher(
            JointState, FP3_ARM_JOINT_STATES_TOPIC, _FP3_JS_QOS
        )
        self._msg = JointState()
        self._msg.name = self._names
        self._msg.position = [_FP3_READY_DEFAULT_RAD.get(n, 0.0) for n in self._names]
        self.create_timer(0.1, self._tick)

    def _tick(self):
        self._msg.header.stamp = self.get_clock().now().to_msg()
        self._pub.publish(self._msg)


def main():
    rclpy.init()
    node = ZeroJointStates()
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
