"""
开阔场地 GADEN + Franka（默认 = 论文 Exp.1 弱风）。

等价于：scenario=10x6_empty_room, configuration=config_exp1_open_weak
论文 Exp.2 时变风请用：gaden_franka_open_exp2.launch.py
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
