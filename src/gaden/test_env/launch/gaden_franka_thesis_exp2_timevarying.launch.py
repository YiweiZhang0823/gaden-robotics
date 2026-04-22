"""
学位论文 Exp.2：无障碍开阔场中的时变风场。

对应导师要求：
- 参考 APPIS 2020 Exp.2 的「homogeneous time-dependent airflow」
- 使用无障碍开阔房间（10x6_empty_room）
- 对应前一个学生未覆盖的时变风场设定
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
