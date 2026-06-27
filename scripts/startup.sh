#!/bin/bash
# ============================================================
# startup.sh — 机器人自启动入口
# 放到 ~/startup.sh，在 Raspberry Pi OS 的
# "Preferences → Raspberry Pi Configuration → Autostart" 中
# 设置为 "Startup Application"
# ============================================================
#
# 启动顺序（严格控制）:
#   1. 桌面稳定 + rustdesk（远程）
#   2. USB 摄像头 ROS2 发布（camera_stream）
#   3. 灯带信标检测（color_detect）+ 串口
#   4. YOLO 物块检测（start_usbcam.sh）
#
# ============================================================

set -e

# ── 日志 ──
LOG=~/startup.log
echo "[STARTUP][$(date '+%F %T')] ======================" >> "$LOG"
log() { echo "[STARTUP][$(date '+%F %T')] $*" | tee -a "$LOG"; }

# ── ROS 环境 ──
load_ros() {
    source /opt/ros/humble/setup.bash
    source ~/workspace/install/setup.bash 2>/dev/null || true
}

##################################################
# Step 0: 等桌面稳定
##################################################
log "Step 0: Waiting for desktop..."
sleep 3

# ── 远程桌面 ──
log "Starting rustdesk..."
rustdesk &
sleep 2

##################################################
# Step 1: 摄像头 ROS2 推流
##################################################
log "Step 1: Starting camera stream watchdog..."
load_ros
gnome-terminal --title="Camera Watchdog" --window -- \
    bash -c "~/workspace/camera_stream/scripts/camera_watchdog.sh; exec bash" &
sleep 2

##################################################
# Step 2: 灯带信标检测 + 串口
##################################################
log "Step 2: Starting beacon detection watchdog..."
gnome-terminal --title="Beacon Detection" --window -- \
    bash -c "~/workspace/camera_stream/scripts/beacon_watchdog.sh; exec bash" &
sleep 2

##################################################
# Step 3: YOLO 物块检测（原有）
##################################################
log "Step 3: Starting YOLO detection (start_usbcam.sh)..."
gnome-terminal --title="YOLO Detection" --window -- \
    bash -c "~/workspace/camera_bridge/start_usbcam.sh; exec bash" &

log "======================================"
log "All systems started"
log "======================================"

exit 0
