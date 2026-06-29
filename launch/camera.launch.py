"""USB 双摄像头启动（独立于 color_detect 包）。

设备路径（你用 udev 绑定）:
  /dev/camera_left   → 左摄像头
  /dev/camera_right  → 右摄像头

用法:
  ros2 launch camera_stream camera.launch.py
  ros2 launch camera_stream camera.launch.py device_left:=/dev/video0 device_right:=/dev/video2
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    config_file = os.path.join(
        get_package_share_directory('camera_stream'),
        'config',
        'camera_stream.yaml'
    )

    return LaunchDescription([
        DeclareLaunchArgument('device_left',  default_value='/dev/camera_left'),
        DeclareLaunchArgument('device_right', default_value='/dev/camera_right'),

        Node(
            package='camera_stream',
            executable='camera_node',
            name='cam_left',
            output='screen',
            parameters=[config_file, {
                'device':       LaunchConfiguration('device_left'),
            }],
        ),

        Node(
            package='camera_stream',
            executable='camera_node',
            name='cam_right',
            output='screen',
            parameters=[config_file, {
                'device':       LaunchConfiguration('device_right'),
            }],
        ),
    ])
