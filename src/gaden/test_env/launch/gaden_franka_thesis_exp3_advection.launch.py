"""
学位论文 Exp.3：平流主导（advection-dominated）开阔稳态风场。

对应导师要求：
- 参考 APPIS 2020 Exp.3 的风型，但去掉中央障碍
- 使用无障碍开阔房间（10x6_empty_room）
- 采用稳态均匀强风，作为学位论文中的 advection 主导设定
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
                    "configuration": "config_exp3_open_steady",
                }.items(),
            ),
        ]
    )
