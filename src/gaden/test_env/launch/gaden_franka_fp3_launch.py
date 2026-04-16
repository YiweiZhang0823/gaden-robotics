"""
GADEN Player + Franka Panda (fp3) 描述模型：在 map 坐标系下显示气体场与机械臂。

- GADEN 的 fixed_frame 为 map（见 gaden.rviz）。
- fp3 在非 Gazebo 模式下根 link 为 base，经 static TF 接到 map。
- 在 RViz 中将 Fixed Frame 设为 map，可同时看到环境与机械臂。

依赖: 需安装 xacro 可执行文件（例如 sudo apt install ros-humble-xacro）。
本文件用子进程调用 xacro，不在 import 阶段依赖 Python 模块 xacro。

底座默认可按 sim.yaml 的 source.position，放在「气源相对 room_center 的对面」一侧（固定基座、臂伸向气源）；
默认启动假气体传感器；读数话题 gas_sensor_topic（默认 /fake_gas_sensor/Sensor_reading）。
末端到点：joint_state_mode=interactive 且启动 franka_fp3_ik_goal 后，
向 /franka_ee_goal 发 PoseStamped（frame_id 可为 base 或 map）。

启动前务必: cd <ws> && colcon build --packages-select test_env --symlink-install && source install/setup.bash
（勿只 source /opt/ros，否则可能跑到旧版脚本，IK/平滑改动不生效。）
"""

import math
import os
import re
import shutil
import subprocess

from ament_index_python.packages import PackageNotFoundError, get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _find_xacro_executable() -> str:
    try:
        prefix = get_package_prefix("xacro")
        for rel in ("bin/xacro", "lib/xacro/xacro"):
            p = os.path.join(prefix, rel)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    except PackageNotFoundError:
        pass
    w = shutil.which("xacro")
    return w if w else ""


def _parse_gas_source_xyz(sim_yaml_path: str):
    """从 sim.yaml 解析 source.position: [x, y, z]；失败返回 None。"""
    if not os.path.isfile(sim_yaml_path):
        return None
    try:
        with open(sim_yaml_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    m = re.search(
        r"position:\s*\[\s*([\d.+-]+)\s*,\s*([\d.+-]+)\s*,\s*([\d.+-]+)\s*\]",
        text,
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2)), float(m.group(3))


# robot_state_publisher 默认订阅 joint_states；改到专用话题（脚本内已显式发布 /fp3_arm/joint_states）
_FRANKA_JOINT_STATES_REMAP = [
    ("joint_states", "/fp3_arm/joint_states"),
]


def _xacro_process_file(xacro_path: str, mappings: dict) -> str:
    xacro_bin = _find_xacro_executable()
    if not xacro_bin:
        raise RuntimeError(
            "未找到 xacro 可执行文件。请安装: sudo apt install ros-humble-xacro"
        )
    cmd = [xacro_bin, xacro_path]
    for key, val in mappings.items():
        cmd.append(f"{key}:={val}")
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(
            f"xacro 处理失败 (exit {completed.returncode}): {err}"
        )
    return completed.stdout


def franka_nodes(context, *args, **kwargs):
    load_gripper = LaunchConfiguration("load_gripper").perform(context)
    ee_id = LaunchConfiguration("ee_id").perform(context)
    use_sim_time = LaunchConfiguration("use_sim_time").perform(context).lower() in (
        "true",
        "1",
        "yes",
    )
    joint_state_mode = (
        LaunchConfiguration("joint_state_mode").perform(context).strip().lower()
    )
    franka_max_vel = float(
        LaunchConfiguration("franka_joint_max_velocity").perform(context).strip()
    )

    scenario = LaunchConfiguration("scenario").perform(context)
    configuration = LaunchConfiguration("configuration").perform(context)
    simulation = LaunchConfiguration("simulation").perform(context)
    share = get_package_share_directory("test_env")
    sim_yaml = os.path.join(
        share,
        "scenarios",
        scenario,
        "environment_configurations",
        configuration,
        "simulations",
        simulation,
        "sim.yaml",
    )

    align = LaunchConfiguration("align_base_from_gas_yaml").perform(context).lower() in (
        "true",
        "1",
        "yes",
    )
    approach = float(LaunchConfiguration("approach_distance").perform(context))
    face_source = LaunchConfiguration("face_yaw_towards_source").perform(context).lower() in (
        "true",
        "1",
        "yes",
    )

    map_x = float(LaunchConfiguration("map_x").perform(context))
    map_y = float(LaunchConfiguration("map_y").perform(context))
    map_z = float(LaunchConfiguration("map_z").perform(context))
    map_yaw = float(LaunchConfiguration("map_yaw").perform(context))

    placement = LaunchConfiguration("base_placement").perform(context).strip().lower()

    src = _parse_gas_source_xyz(sim_yaml)
    if align and src is not None:
        sx, sy, sz = src
        cx = float(LaunchConfiguration("room_center_x").perform(context))
        cy = float(LaunchConfiguration("room_center_y").perform(context))
        # 从中心指向气源的单位向量
        dx_cs = sx - cx
        dy_cs = sy - cy
        dist_cs = math.hypot(dx_cs, dy_cs)

        if placement in ("opposite_source", "opposite", "across"):
            # 气源对面：底座在「中心背向气源」一侧，距中心 approach 米（臂伸向气源，基座不动）
            if dist_cs > 1e-6:
                ux, uy = dx_cs / dist_cs, dy_cs / dist_cs
                map_x = cx - approach * ux
                map_y = cy - approach * uy
            else:
                map_x = cx - approach
                map_y = cy
        else:
            # toward_center_from_source：从气源沿「气源→中心」方向偏移 approach 米（旧行为）
            if dist_cs > 1e-6:
                nx, ny = (cx - sx) / dist_cs, (cy - sy) / dist_cs
                map_x = sx + approach * nx
                map_y = sy + approach * ny
            else:
                map_x = sx - approach
                map_y = sy
        map_z = 0.0
        if face_source:
            dx = sx - map_x
            dy = sy - map_y
            if abs(dx) > 1e-6 or abs(dy) > 1e-6:
                map_yaw = math.atan2(dy, dx)
    elif align and src is None:
        print(
            f"[gaden_franka_fp3] 警告: 无法从 {sim_yaml} 解析 source.position，"
            "使用手动 map_x/map_y/map_yaw。"
        )

    franka_xacro = os.path.join(
        get_package_share_directory("franka_description"),
        "robots",
        "fp3",
        "fp3.urdf.xacro",
    )
    robot_description = _xacro_process_file(
        franka_xacro,
        {"hand": load_gripper, "ee_id": ee_id},
    )

    sim_time_param = {"use_sim_time": use_sim_time}

    joint_nodes = []
    if joint_state_mode == "gui":
        joint_nodes.append(
            Node(
                package="joint_state_publisher_gui",
                executable="joint_state_publisher_gui",
                name="joint_state_publisher_gui",
                parameters=[
                    {"robot_description": robot_description},
                    sim_time_param,
                ],
                remappings=_FRANKA_JOINT_STATES_REMAP,
            )
        )
    elif joint_state_mode == "interactive":
        joint_nodes.append(
            Node(
                package="test_env",
                executable="franka_joint_interactive",
                name="franka_joint_interactive",
                output="screen",
                parameters=[
                    {"robot_description": robot_description},
                    sim_time_param,
                    # 显式传入，避免未 source install 时仍用脚本内旧默认值；越小越「一步一步」
                    {"max_joint_velocity": franka_max_vel, "publish_rate": 30.0},
                ],
            )
        )
    else:
        joint_nodes.append(
            Node(
                package="test_env",
                executable="zero_joint_states",
                name="zero_joint_states",
                parameters=[
                    {"robot_description": robot_description},
                    sim_time_param,
                ],
            )
        )

    return [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="franka_robot_state_publisher",
            output="screen",
            parameters=[
                {"robot_description": robot_description},
                sim_time_param,
                # 避免因 joint_states 时间戳与 RSP 内部节流逻辑不一致导致几乎不发布关节 TF（RViz 机械臂「完全不动」）
                {"ignore_timestamp": True},
                {"publish_frequency": 50.0},
                # 与 franka_joint_interactive 发布端 QoS 显式配对（否则默认 SensorData 订阅可能与 RELIABLE 发布不建链）
                {
                    "qos_overrides": {
                        "/fp3_arm/joint_states": {
                            "subscription": {
                                "reliability": "reliable",
                                "history": "keep_last",
                                "depth": 20,
                            }
                        }
                    }
                },
            ],
            remappings=_FRANKA_JOINT_STATES_REMAP,
        ),
        Node(
            package="tf2_ros",
            executable="static_transform_publisher",
            name="map_to_franka_base",
            output="screen",
            arguments=[
                "--x",
                str(map_x),
                "--y",
                str(map_y),
                "--z",
                str(map_z),
                "--yaw",
                str(map_yaw),
                "--frame-id",
                "map",
                "--child-frame-id",
                "base",
            ],
            parameters=[sim_time_param],
        ),
        *joint_nodes,
    ]


def generate_launch_description():
    share_test_env = get_package_share_directory("test_env")

    gaden_player = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(share_test_env, "launch", "gaden_player_launch.py")
        ),
        launch_arguments={
            "scenario": LaunchConfiguration("scenario"),
            "configuration": LaunchConfiguration("configuration"),
            "playback": LaunchConfiguration("playback"),
            "simulation": LaunchConfiguration("simulation"),
            "use_rviz": LaunchConfiguration("use_rviz"),
            "rviz_config": LaunchConfiguration("rviz_config"),
        }.items(),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "scenario",
                default_value="10x6_central_obstacle",
                description="GADEN 场景目录名（test_env/scenarios/...）",
            ),
            DeclareLaunchArgument(
                "configuration",
                default_value="config1",
                description="环境配置名",
            ),
            DeclareLaunchArgument(
                "playback",
                default_value="scene1",
                description="与 scene yaml 对应的 playback ID（见 gaden_params.yaml）",
            ),
            DeclareLaunchArgument(
                "simulation",
                default_value="sim1",
                description="供 gaden_params 中 $(var simulation) 替换（与预处理/仿真 ID 一致）",
            ),
            DeclareLaunchArgument(
                "use_rviz",
                default_value="True",
                description="是否启动 gaden_player_launch 中的 RViz",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value="gaden_franka.rviz",
                description="RViz 配置（Franka 用 gaden_franka.rviz，机械臂订阅 /robot_description）",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="False",
                description="若存在 /clock（例如回放 bag），设为 True",
            ),
            DeclareLaunchArgument(
                "load_gripper",
                default_value="true",
                description="是否加载 Franka 手爪（与 franka_description visualize 一致）",
            ),
            DeclareLaunchArgument(
                "ee_id",
                default_value="franka_hand",
                description="末端执行器 ID",
            ),
            DeclareLaunchArgument(
                "joint_state_mode",
                default_value="interactive",
                description="zero=全零关节；interactive=订阅 /franka_joint_target 控制；"
                "gui=joint_state_publisher_gui 拖动滑条（需 apt）",
            ),
            DeclareLaunchArgument(
                "franka_joint_max_velocity",
                default_value="0.2",
                description="franka_joint_interactive 角速度上限(rad/s)；越小越稳、越不易像栽倒",
            ),
            DeclareLaunchArgument(
                "align_base_from_gas_yaml",
                default_value="true",
                description="从 simulations/<simulation>/sim.yaml 读 source.position，自动放置底座（否则用手动 map_*）",
            ),
            DeclareLaunchArgument(
                "base_placement",
                default_value="opposite_source",
                description="opposite_source=底座在气源相对 room_center 的对面（默认）；"
                "toward_center_from_source=从气源朝中心方向偏移（旧策略）",
            ),
            DeclareLaunchArgument(
                "approach_distance",
                default_value="2.5",
                description="opposite_source：沿「中心→气源」反方向、离 room_center 的距离（米）；"
                "toward_center_from_source：从气源沿向心方向偏移的距离（米）",
            ),
            DeclareLaunchArgument(
                "room_center_x",
                default_value="5.0",
                description="10x6 类房间参考中心 x（米），用于计算从气源向室内偏移方向",
            ),
            DeclareLaunchArgument(
                "room_center_y",
                default_value="3.0",
                description="房间参考中心 y（米）",
            ),
            DeclareLaunchArgument(
                "face_yaw_towards_source",
                default_value="true",
                description="自动放置：base 在 map 平面内是否朝向气源",
            ),
            DeclareLaunchArgument(
                "launch_fake_gas_sensor",
                default_value="true",
                description="启动 simulated_gas_sensor（需 gaden_player 已提供 /odor_value）；设为 false 可关",
            ),
            DeclareLaunchArgument(
                "gas_sensor_frame",
                default_value="fp3_hand_tcp",
                description="假传感器 TF，一般为手爪 TCP：fp3_hand_tcp",
            ),
            DeclareLaunchArgument(
                "gas_sensor_topic",
                default_value="/fake_gas_sensor/Sensor_reading",
                description="GasSensor 读数话题（与节点名 fake_gas_sensor 一致）",
            ),
            DeclareLaunchArgument(
                "map_x",
                default_value="4.5",
                description="手动模式（align_base_from_gas_yaml:=false）或解析失败时的 base x（米）",
            ),
            DeclareLaunchArgument(
                "map_y",
                default_value="2.0",
                description="手动模式或解析失败时的 base y（米）",
            ),
            DeclareLaunchArgument(
                "map_z",
                default_value="0.0",
                description="机械臂 base 在 map 中的 z（米）",
            ),
            DeclareLaunchArgument(
                "map_yaw",
                default_value="0.0",
                description="base 相对 map 绕 Z 轴转角（弧度）",
            ),
            gaden_player,
            OpaqueFunction(function=franka_nodes),
            # PyKDL 数值 IK：/franka_ee_goal -> /franka_joint_target（需 joint_state_mode=interactive）
            Node(
                package="test_env",
                executable="franka_fp3_ik_goal",
                name="franka_fp3_ik_goal",
                output="screen",
            ),
            # 延迟启动，避免 TF 尚未收到 map→base / arm→tcp 时 lookupTransform 报竞态（配合假传感器内暖机）
            TimerAction(
                period=2.5,
                actions=[
                    Node(
                        condition=IfCondition(
                            LaunchConfiguration("launch_fake_gas_sensor")
                        ),
                        package="simulated_gas_sensor",
                        executable="simulated_gas_sensor",
                        name="fake_gas_sensor",
                        output="screen",
                        parameters=[
                            {
                                "sensor_frame": LaunchConfiguration(
                                    "gas_sensor_frame"
                                ),
                            },
                            {"fixed_frame": "map"},
                            {"sensor_model": 30},
                            {"rate": 10.0},
                            {
                                "topic": LaunchConfiguration(
                                    "gas_sensor_topic"
                                ),
                            },
                        ],
                    ),
                ],
            ),
        ]
    )
