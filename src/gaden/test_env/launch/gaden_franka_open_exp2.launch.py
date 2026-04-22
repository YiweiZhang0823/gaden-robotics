"""
开阔场地 + 论文 Exp.2 类时变风：scenario=10x6_empty_room, configuration=config_exp2_open_timevarying

同时包含 GADEN 场景与 Franka；要看「房间 + 气体 + 机械臂」用本文件，不要用仅 filament 的 gaden_sim_launch。
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
                    "configuration": "config_exp2_open_timevarying",
                }.items(),
            ),
        ]
    )
