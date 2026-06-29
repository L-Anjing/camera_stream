#!/bin/bash
# startup.sh — 机器人自启动入口
#
# 启动顺序（严格控制）:
#   1. 桌面稳定 + rustdesk（远程）
#   2. USB 摄像头 ROS2 发布（camera_stream）
#   3. 等待 /cam_left/image_raw 和 /cam_right/image_raw 出现
#   4. YOLO 物块检测（usb_detect）+ 串口
#   5. 灯带信标检测（color_detect）+ 串口
#

set -e

WORKSPACE_DIR=${WORKSPACE_DIR:-$HOME/workspace}
SRC_DIR=${SRC_DIR:-$WORKSPACE_DIR/src}
USB_YOLO_SERIAL_PORT=${USB_YOLO_SERIAL_PORT:-/dev/ttyUSB0}
COLOR_SERIAL_PORT=${COLOR_SERIAL_PORT:-/dev/ttyACM0}
SERIAL_BAUD=${SERIAL_BAUD:-115200}

# ── 日志 ──
LOG=~/startup.log
echo "[STARTUP][$(date '+%F %T')] ======================" >> "$LOG"
log() { echo "[STARTUP][$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ── ROS 环境 ──
load_ros() {
    source /opt/ros/humble/setup.bash
    source "$WORKSPACE_DIR/install/setup.bash" 2>/dev/null || true
}

wait_for_topic() {
    local topic="$1"
    local timeout="${2:-20}"
    local start_ts
    start_ts=$(date +%s)

    while true; do
        if ros2 topic list 2>/dev/null | grep -qx "$topic"; then
            log "Topic ready: $topic"
            return 0
        fi

        if [ "$timeout" -gt 0 ] && [ $(( $(date +%s) - start_ts )) -ge "$timeout" ]; then
            log "Timeout waiting topic: $topic"
            return 1
        fi

        sleep 0.5
    done
}

##################################################
# Step 1: 摄像头 ROS2 推流
##################################################
log "Step 1: Starting camera stream watchdog..."
load_ros
gnome-terminal --title="Camera Watchdog" --window -- \
    bash -c "$SRC_DIR/camera_stream/scripts/camera_watchdog.sh; exec bash" &

##################################################
# Step 2: 等待摄像头话题
##################################################
log "Step 2: Waiting camera topics..."
wait_for_topic "/cam_left/image_raw" 0
wait_for_topic "/cam_right/image_raw" 0

##################################################
# Step 3: YOLO 物块检测 + 串口
##################################################
log "Step 3: Starting USB YOLO watchdog..."
gnome-terminal --title="USB YOLO Detection" --window -- \
    bash -c "USB_YOLO_SERIAL_PORT=$USB_YOLO_SERIAL_PORT SERIAL_BAUD=$SERIAL_BAUD $SRC_DIR/camera_bridge/start_usbcam.sh; exec bash" &
sleep 2

##################################################
# Step 4: 灯带信标检测 + 串口
##################################################
log "Step 4: Starting beacon detection watchdog..."
gnome-terminal --title="Beacon Detection" --window -- \
    bash -c "COLOR_SERIAL_PORT=$COLOR_SERIAL_PORT SERIAL_BAUD=$SERIAL_BAUD $SRC_DIR/camera_stream/scripts/beacon_watchdog.sh; exec bash" &

log "======================================"
log "All systems started"
log "======================================"

exit 0
