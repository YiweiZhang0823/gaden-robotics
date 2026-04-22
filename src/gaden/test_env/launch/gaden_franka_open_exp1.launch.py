"""
开阔场地 + 论文 Exp.1 类弱风：scenario=10x6_empty_room, configuration=config_exp1_open_weak

同时包含：GADEN 房间/气体回放（gaden_environment + gaden_player）+ Franka（/robot_description）。
要看「场景 + 机械臂」请用本文件；不要用 gaden_sim_launch / open_field_build_gaden_data 里的 filament 单独 RViz（那是纯仿真、无机械臂）。
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    share = get_package_share_directory("test_env")
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(share, "launch", "gaden_franka_fp3_launch.py")
                ),
                launch_arguments={
                    "scenario": "10x6_empty_room",
                    "configuration": "config_exp1_open_weak",
                }.items(),
            ),
        ]
    )
