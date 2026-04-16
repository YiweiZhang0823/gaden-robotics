#!/usr/bin/env python3
"""
向 /franka_ee_goal 发布一条 PoseStamped（geometry_msgs），避免 ros2 topic pub 的 YAML 解析问题。

须先启动含 franka_fp3_ik_goal 的 launch，否则没有订阅者，消息会丢失。

用法:
  ros2 run test_env publish_ee_goal 0.55 0.0 0.45
  ros2 run test_env publish_ee_goal 0.6 0.1 0.4 --frame base
  ros2 run test_env publish_ee_goal 0.45 0.0 0.50 --preset identity
  # 重要：只改位置、姿态用 identity(0,0,0,1) 时，冗余 IK 常回到「指天」观感，与 z 高低无关。
  # 默认 preset 为 tilt_x_90（绕 base X +90°）；可改 --preset tilt_x_m90 / tilt_x_180 等对比。
  # 乱填四元数易「扭曲」；优先用 preset，再微调。
"""
from __future__ import annotations

import argparse
import math
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.qos import QoSProfile, ReliabilityPolicy

# 绕 base 系 X 轴转角(rad)的四元数 (x,y,z,w)，与 geometry_msgs 一致；少「指天」可试 tilt_x_90 等
def _quat_rotate_x(angle_rad: float) -> tuple[float, float, float, float]:
    h = angle_rad * 0.5
    s, c = math.sin(h), math.cos(h)
    return (s, 0.0, 0.0, c)


PRESET_QUAT: dict[str, tuple[float, float, float, float]] = {
    "identity": (0.0, 0.0, 0.0, 1.0),
    # 常见试探：绕 X ±90°（是否改善「朝天」视模型而定，需试）
    "tilt_x_90": _quat_rotate_x(math.pi / 2),
    "tilt_x_m90": _quat_rotate_x(-math.pi / 2),
    "tilt_x_180": _quat_rotate_x(math.pi),
}


def main() -> None:
    ap = argparse.ArgumentParser(description="发布一次末端目标（base 系，单位 m）")
    ap.add_argument("x", type=float, help="pose.position.x")
    ap.add_argument("y", type=float, help="pose.position.y")
    ap.add_argument("z", type=float, help="pose.position.z")
    ap.add_argument("--frame", default="base", help="header.frame_id")
    ap.add_argument("--qx", type=float, default=0.0)
    ap.add_argument("--qy", type=float, default=0.0)
    ap.add_argument("--qz", type=float, default=0.0)
    ap.add_argument("--qw", type=float, default=1.0)
    ap.add_argument(
        "--preset",
        choices=tuple(PRESET_QUAT.keys()),
        default="tilt_x_90",
        help="预设末端姿态四元数；非 identity 时覆盖 --qx..--qw。默认 tilt_x_90（绕 base X +90°）以减轻「指天」冗余解",
    )
    ap.add_argument(
        "--wait-sec",
        type=float,
        default=15.0,
        help="最多等待多少秒直到有节点订阅 /franka_ee_goal（默认 15）",
    )
    args = ap.parse_args()

    rclpy.init()
    node = rclpy.create_node("publish_ee_goal_once")
    # 与 franka_fp3_ik_goal 订阅端一致（depth=5, RELIABLE）
    qos = QoSProfile(depth=5, reliability=ReliabilityPolicy.RELIABLE)
    pub = node.create_publisher(PoseStamped, "/franka_ee_goal", qos)

    # 给 DDS 一点时间完成 discovery
    t_disc = time.monotonic()
    while time.monotonic() - t_disc < 0.3 and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)

    t0 = time.monotonic()
    while pub.get_subscription_count() == 0 and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)
        if time.monotonic() - t0 > args.wait_sec:
            print(
                "错误: 超时仍无订阅者连接 /franka_ee_goal。\n"
                "  请先在一个终端启动:\n"
                "    source install/setup.bash\n"
                "    ros2 launch test_env gaden_franka_fp3_launch.py\n"
                "  再在本终端 source 后重试。",
                file=sys.stderr,
            )
            node.destroy_node()
            rclpy.shutdown()
            sys.exit(1)

    if args.preset != "identity":
        qx, qy, qz, qw = PRESET_QUAT[args.preset]
    else:
        qx, qy, qz, qw = args.qx, args.qy, args.qz, args.qw

    msg = PoseStamped()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = args.frame
    msg.pose.position.x = args.x
    msg.pose.position.y = args.y
    msg.pose.position.z = args.z
    msg.pose.orientation.x = qx
    msg.pose.orientation.y = qy
    msg.pose.orientation.z = qz
    msg.pose.orientation.w = qw

    pub.publish(msg)
    print(
        f"已发布 /franka_ee_goal: frame={args.frame!r} "
        f"pos=({args.x}, {args.y}, {args.z}) m "
        f"preset={args.preset!r} quat=({qx:.4f},{qy:.4f},{qz:.4f},{qw:.4f}) "
        f"订阅者数={pub.get_subscription_count()}"
    )

    # 节点过早 shutdown 时 DDS 可能来不及把消息送出去，多 spin 一会儿
    t_end = time.monotonic() + 0.8
    while time.monotonic() < t_end and rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.05)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
