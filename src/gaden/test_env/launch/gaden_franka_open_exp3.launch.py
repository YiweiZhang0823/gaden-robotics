"""
开阔场地 + 学位论文「平流主导」：定常均匀强风（APPIS §4.3 风型在开阔场的对应，无中央障碍）。

configuration=config_exp3_open_steady（uniformWind + wind_simulations/exp3_open_steady/wind_0.csv）
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
