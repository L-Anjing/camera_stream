#!/bin/bash
# camera_watchdog.sh — USB 摄像头 ROS2 发布 watchdog
# 参照 camera_bridge/start_usbcam.sh 的 watchdog 模式
#
# 用法:
#   ./camera_watchdog.sh             启动
#   ./camera_watchdog.sh --stop      停止
#   ./camera_watchdog.sh --status    状态

set -uo pipefail

PIDFILE=/tmp/camera_watchdog.pid

##################################################
# 状态管理
##################################################

if [ "${1:-}" = "--stop" ]; then
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        echo "Stopping camera watchdog PID=$PID"
        kill -TERM "$PID" 2>/dev/null || true
        rm -f "$PIDFILE"
    else
        echo "Camera watchdog not running"
    fi
    exit 0
fi

if [ "${1:-}" = "--status" ]; then
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Camera watchdog running PID=$PID"
        else
            echo "PID file exists but process dead"
        fi
    else
        echo "Camera watchdog not running"
    fi
    exit 0
fi

echo $$ > "$PIDFILE"

##################################################
# 日志
##################################################

log() { echo "[CAM-WD][$(date '+%F %T')] $*"; }

##################################################
# ROS 环境
##################################################

load_env()
{
    set +u
    source /opt/ros/humble/setup.bash || return 1
    source ~/workspace/install/setup.bash 2>/dev/null || true
    set -u
    return 0
}

##################################################
# 全局
##################################################

LAUNCH_PID=""
TAIL_PID=""
STOP_REQUESTED=0

cleanup_launch()
{
    if [ -n "${TAIL_PID:-}" ]; then
        kill "$TAIL_PID" 2>/dev/null || true
        wait "$TAIL_PID" 2>/dev/null || true
        TAIL_PID=""
    fi
    if [ -z "${LAUNCH_PID:-}" ]; then return; fi
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then LAUNCH_PID=""; return; fi
    log "Stopping camera launch PID=$LAUNCH_PID"
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    for i in {1..10}; do
        if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then break; fi
        sleep 0.05
    done
    if kill -0 "$LAUNCH_PID" 2>/dev/null; then
        log "Force kill camera launch PID=$LAUNCH_PID"
        kill -KILL "$LAUNCH_PID" 2>/dev/null || true
    fi
    LAUNCH_PID=""
}

shutdown()
{
    log "User requested stop"
    STOP_REQUESTED=1
    cleanup_launch
    rm -f "$PIDFILE"
    exit 0
}

trap shutdown SIGINT SIGTERM

##################################################
# 主循环
##################################################

log "======================================"
log "Camera Watchdog Started PID=$$"
log "======================================"

if ! load_env; then
    log "ROS environment load failed"
    exit 1
fi
log "ROS environment ready"

while true; do
    [ "$STOP_REQUESTED" = "1" ] && break

    LAUNCH_LOG=$(mktemp /tmp/cam_launch_XXXX.log)

    log "Launching camera_stream (left + right)"
    ros2 launch camera_stream camera.launch.py \
        > "$LAUNCH_LOG" 2>&1 &

    LAUNCH_PID=$!
    log "Camera launch PID=$LAUNCH_PID"

    stdbuf -oL tail -n 0 --pid="$LAUNCH_PID" -f "$LAUNCH_LOG" &
    TAIL_PID=$!

    EXIT_CODE=0
    while true; do
        [ "$STOP_REQUESTED" = "1" ] && break
        if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
            wait "$LAUNCH_PID"
            EXIT_CODE=$?
            log "Camera launch exited code=$EXIT_CODE"
            break
        fi
        if tail -n 50 "$LAUNCH_LOG" | \
            grep -qiE "(\[error\]|failed to open|camera failed|device failed)"
        then
            log "Camera error detected, restarting..."
            EXIT_CODE=1
            break
        fi
        sleep 0.2
    done

    cleanup_launch
    rm -f "$LAUNCH_LOG"
    [ "$STOP_REQUESTED" = "1" ] && break

    log "Restart camera after 0.5s..."
    sleep 0.5
done

cleanup_launch
rm -f "$PIDFILE"
log "Camera watchdog exited"
