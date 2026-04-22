"""
学位论文 Exp.1：扩散主导（diffusion-dominated）开阔弱风场。

对应导师要求：
- 参考 APPIS 2020 Exp.1 的「weak airflow in an open environment」
- 使用无障碍开阔房间（10x6_empty_room）
- 与 `gaden_franka_open_exp1.launch.py` 等价，只是提供论文语义化入口
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
