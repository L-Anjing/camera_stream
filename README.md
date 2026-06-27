# camera_stream — USB Camera ROS2 MJPEG Publisher

## 概述

独立的 USB 摄像头 ROS2 发布节点，走 V4L2 + MJPEG 推流。

与 `color_detect`（灯带信标检测）完全分离，可独立启动、独立 watchdog 管理。

## 依赖

```bash
sudo apt install ros-humble-cv-bridge ros-humble-sensor-msgs libopencv-dev
```

## 编译

```bash
cd ~/workspace
colcon build --packages-select camera_stream
source install/setup.bash
```

## 用法

```bash
# 启动左右双摄像头（默认 /dev/camera_left, /dev/camera_right）
ros2 launch camera_stream camera.launch.py

# 指定设备路径（udev 绑定前的临时测试）
ros2 launch camera_stream camera.launch.py \
  device_left:=/dev/video0 \
  device_right:=/dev/video2

# 单独启动左摄像头
ros2 run camera_stream camera_node --ros-args \
  -p device:=/dev/camera_left \
  -p camera_name:=cam_left \
  -p image_width:=1280 \
  -p image_height:=720 \
  -p framerate:=30
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `device` | `/dev/video0` | 摄像头设备路径 |
| `camera_name` | `cam` | 相机名称（决定话题名 `/cam_name/image_raw`） |
| `image_width` | `1280` | 目标宽度 |
| `image_height` | `720` | 目标高度 |
| `framerate` | `30` | 目标帧率 |

相机自动设置为 MJPEG 格式。实际生效参数取决于硬件和 V4L2 驱动。

## 设备绑定（udev）

创建 `/etc/udev/rules.d/99-cameras.rules`，根据 USB 序列号固定设备名：

```
SUBSYSTEM=="video4linux", KERNEL=="video[0-9]*", \
  ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="XXXX", \
  ATTRS{serial}=="LEFT_CAM_SERIAL", SYMLINK+="camera_left"
```

## 发布话题

| 话题 | 类型 | 说明 |
|------|------|------|
| `/cam_left/image_raw` | `sensor_msgs/Image` | 左摄像头 bgr8 |
| `/cam_right/image_raw` | `sensor_msgs/Image` | 右摄像头 bgr8 |

## Watchdog

```bash
# 启动摄像头 watchdog（自动重启）
./scripts/camera_watchdog.sh

# 停止
./scripts/camera_watchdog.sh --stop

# 状态
./scripts/camera_watchdog.sh --status
```
