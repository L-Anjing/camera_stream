"""USB 双摄像头启动（独立于 color_detect 包）。

设备路径（你用 udev 绑定）:
  /dev/camera_left   → 左摄像头
  /dev/camera_right  → 右摄像头

用法:
  ros2 launch camera_stream camera.launch.py
  ros2 launch camera_stream camera.launch.py device_left:=/dev/video0 device_right:=/dev/video2
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.actions import DeclareLaunchArgument


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('device_left',  default_value='/dev/camera_left'),
        DeclareLaunchArgument('device_right', default_value='/dev/camera_right'),
        DeclareLaunchArgument('image_width',  default_value='1280'),
        DeclareLaunchArgument('image_height', default_value='720'),
        DeclareLaunchArgument('framerate',    default_value='30'),

        Node(
            package='camera_stream',
            executable='camera_node',
            name='cam_left',
            output='screen',
            parameters=[{
                'device':       LaunchConfiguration('device_left'),
                'camera_name':  'cam_left',
                'image_width':  LaunchConfiguration('image_width'),
                'image_height': LaunchConfiguration('image_height'),
                'framerate':    LaunchConfiguration('framerate'),
            }],
        ),

        Node(
            package='camera_stream',
            executable='camera_node',
            name='cam_right',
            output='screen',
            parameters=[{
                'device':       LaunchConfiguration('device_right'),
                'camera_name':  'cam_right',
                'image_width':  LaunchConfiguration('image_width'),
                'image_height': LaunchConfiguration('image_height'),
                'framerate':    LaunchConfiguration('framerate'),
            }],
        ),
    ])
