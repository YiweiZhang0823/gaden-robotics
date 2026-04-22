"""
    Launch file to run GADEN gas dispersion simulator.
    IMPORTANT: GADEN_preprocessing should be called before!

    Parameters:
        @param scenario - The scenario where dispersal takes place
        @param simulation - The wind flow actuating in the scenario
        @param source_(xyz) - The 3D position of the release point
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
            default_value=["10x6_central_obstacle"],
            description="scenario to simulate",
        ),
        DeclareLaunchArgument(
            "configuration",
            default_value=["config1"],
            description="name of the configuration",
        ),
        DeclareLaunchArgument(
            "simulation",
            default_value=["sim1"],
            description="name of the simulation",
        ),
        DeclareLaunchArgument(
            "sim_time",
            default_value="320.0",
            description="仿真时长（秒），应 ≥ sim.yaml 里隐含的总时长需求",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="True",
            description="是否启动 RViz；批量生成结果时可设为 False",
        ),
    ]
# ==========================


def launch_setup(context, *args, **kwargs):
    pkg_dir = LaunchConfiguration("pkg_dir").perform(context)
    sim_time = float(LaunchConfiguration("sim_time").perform(context).strip())

    params_yaml_file = os.path.join(
        pkg_dir, "ros_params", "gaden_params.yaml"
    )

    return [
        Node(
            condition=IfCondition(LaunchConfiguration("use_rviz")),
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d' + os.path.join(pkg_dir, 'launch', 'gaden.rviz')]
        ),

        # gaden_environment (for RVIZ visualization)
        Node(
            package='gaden_environment',
            executable='environment',
            name='gaden_environment',
            output='screen',
            parameters=[ParameterFile(params_yaml_file, allow_substs=True)]
        ),

        # gaden_filament_simulator (The core)
        Node(
            package='gaden_filament_simulator',
            executable='filament_simulator',
            name='gaden_filament_simulator',
            output='screen',
            parameters=[ParameterFile(params_yaml_file, allow_substs=True),
                        {"sim_time": sim_time},
                        {"runRate": 0.0}
                        ]
        )
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
        SetLaunchConfiguration(name="playback", value="none"),
    ]

    launch_description.extend(launch_arguments())
    launch_description.append(OpaqueFunction(function=launch_setup))

    return LaunchDescription(launch_description)
