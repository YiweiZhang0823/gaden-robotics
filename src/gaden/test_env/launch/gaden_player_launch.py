"""
    Launch file to run GADEN_player, a node in charge of playing back 
    the gas dispersal generated with GADEN, offering visualization, and
    simulated sensors to access the gas concentration and wind vector.

    Parameters:
        @param scenario - The scenario where dispersal takes place
        @param simulation - The wind flow actuating in the scenario
"""

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, SetLaunchConfiguration, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile
from ament_index_python.packages import get_package_share_directory


# ===========================
def launch_arguments():
    return [
        DeclareLaunchArgument(
            "scenario",
            default_value=["Exp_C"],
            description="scenario to simulate",
        ),
        DeclareLaunchArgument(
            "configuration",
            default_value=["config1"],
            description="name of the configuration yaml file",
        ),
        DeclareLaunchArgument(
            "playback",
            default_value=["scene1"],
            description="name of the simulation yaml file",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value=["True"],
            description="",
        ),
        DeclareLaunchArgument(
            "simulation",
            default_value=["none"],
            description="Wind/simulation ID for gaden_params $(var simulation)",
        ),
        DeclareLaunchArgument(
            "rviz_config",
            default_value=["gaden.rviz"],
            description="RViz 配置文件名（位于 test_env/launch/）或绝对路径",
        ),
    ]
# ==========================


def launch_setup(context, *args, **kwargs):
    scenario = LaunchConfiguration("scenario").perform(context)
    pkg_dir = LaunchConfiguration("pkg_dir").perform(context)
    rviz_config = LaunchConfiguration("rviz_config").perform(context)
    if os.path.isabs(rviz_config):
        rviz_path = rviz_config
    else:
        rviz_path = os.path.join(pkg_dir, "launch", rviz_config)

    params_yaml_file = os.path.join(
        pkg_dir, "ros_params", "gaden_params.yaml"
    )

    return [
        Node(
            condition=IfCondition(LaunchConfiguration("use_rviz")),
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            arguments=[
                "-d" + rviz_path
            ],
            remappings=[
                ("/initialpose", "/PioneerP3DX/initialpose"),
                ("/goal_pose", "/PioneerP3DX/goal_pose"),
            ],
        ),

        # gaden_environment (for RVIZ visualization)
        Node(
            package='gaden_environment',
            executable='environment',
            name='gaden_environment',
            output='screen',
            parameters=[ParameterFile(params_yaml_file, allow_substs=True)]
        ),

        # gaden_player
        Node(
            package="gaden_player",
            executable="player",
            name="gaden_player",
            output="screen",
            parameters=[ParameterFile(params_yaml_file, allow_substs=True),
                        {"player_freq": 2.0}
                        ],
        ),
    ]


def generate_launch_description():

    launch_description = [
        # Set env var to print messages to stdout immediately
        SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"),
        SetEnvironmentVariable("RCUTILS_COLORIZED_OUTPUT", "1"),

        SetLaunchConfiguration(
            name="pkg_dir",
            value=[get_package_share_directory("test_env")],
        ),
    ]

    launch_description.extend(launch_arguments())
    launch_description.append(OpaqueFunction(function=launch_setup))

    return LaunchDescription(launch_description)
