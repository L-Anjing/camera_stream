#!/bin/bash
# beacon_watchdog.sh — 灯带信标检测 watchdog
#
# 用法:
#   ./beacon_watchdog.sh             启动
#   ./beacon_watchdog.sh --stop      停止
#   ./beacon_watchdog.sh --status    状态

set -uo pipefail

PIDFILE=/tmp/beacon_watchdog.pid
WORKSPACE_DIR=${WORKSPACE_DIR:-$HOME/workspace}
COLOR_SERIAL_PORT=${COLOR_SERIAL_PORT:-/dev/ttyACM0}
SERIAL_BAUD=${SERIAL_BAUD:-115200}

# ── 状态管理 ──
if [ "${1:-}" = "--stop" ]; then
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE"); echo "Stopping beacon watchdog PID=$PID"
        kill -TERM "$PID" 2>/dev/null || true; rm -f "$PIDFILE"
    else echo "Beacon watchdog not running"; fi
    exit 0
fi
if [ "${1:-}" = "--status" ]; then
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then echo "Running PID=$PID"
        else echo "PID file exists but dead"; fi
    else echo "Not running"; fi
    exit 0
fi

echo $$ > "$PIDFILE"
log() { echo "[BEACON-WD][$(date '+%F %T')] $*"; }

load_env() {
    set +u; source /opt/ros/humble/setup.bash || return 1
    source "$WORKSPACE_DIR/install/setup.bash" 2>/dev/null || true
    set -u; return 0
}

wait_for_topic() {
    local topic="$1"
    local timeout="${2:-30}"
    local start_ts
    start_ts=$(date +%s)
    while true; do
        [ "$STOP_REQUESTED" = "1" ] && return 1
        if ros2 topic list 2>/dev/null | grep -qx "$topic"; then
            log "Topic ready: $topic"
            return 0
        fi
        if [ $(( $(date +%s) - start_ts )) -ge "$timeout" ]; then
            log "Timeout waiting topic: $topic"
            return 1
        fi
        sleep 0.5
    done
}

LAUNCH_PID=""; TAIL_PID=""; STOP_REQUESTED=0

cleanup_launch() {
    if [ -n "${TAIL_PID:-}" ]; then kill "$TAIL_PID" 2>/dev/null || true; wait "$TAIL_PID" 2>/dev/null || true; TAIL_PID=""; fi
    if [ -z "${LAUNCH_PID:-}" ]; then return; fi
    if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then LAUNCH_PID=""; return; fi
    log "Stopping beacon PID=$LAUNCH_PID"
    kill -TERM "$LAUNCH_PID" 2>/dev/null || true
    for i in {1..10}; do if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then break; fi; sleep 0.05; done
    if kill -0 "$LAUNCH_PID" 2>/dev/null; then kill -KILL "$LAUNCH_PID" 2>/dev/null || true; fi
    LAUNCH_PID=""
}

shutdown() { log "Stop requested"; STOP_REQUESTED=1; cleanup_launch; rm -f "$PIDFILE"; exit 0; }
trap shutdown SIGINT SIGTERM

log "======================================"
log "Beacon Watchdog Started PID=$$"
log "======================================"
if ! load_env; then log "ROS env fail"; exit 1; fi
log "ROS ready"

while true; do
    [ "$STOP_REQUESTED" = "1" ] && break

    log "Waiting camera topics before color_detect..."
    wait_for_topic "/cam_left/image_raw" 30 || { log "Left camera topic not ready"; sleep 1; continue; }
    wait_for_topic "/cam_right/image_raw" 30 || { log "Right camera topic not ready"; sleep 1; continue; }

    LOG=$(mktemp /tmp/beacon_launch_XXXX.log)
    log "Launching color_detect + serial"
    ros2 launch color_detect color_detect_all.launch.py \
        serial_port:="$COLOR_SERIAL_PORT" \
        serial_baud:="$SERIAL_BAUD" \
        > "$LOG" 2>&1 &
    LAUNCH_PID=$!; log "PID=$LAUNCH_PID"
    stdbuf -oL tail -n 0 --pid="$LAUNCH_PID" -f "$LOG" & TAIL_PID=$!
    EXIT_CODE=0
    while true; do
        [ "$STOP_REQUESTED" = "1" ] && break
        if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
            wait "$LAUNCH_PID"; EXIT_CODE=$?; log "Exited code=$EXIT_CODE"; break
        fi
        if tail -n 50 "$LOG" | grep -qiE "(\[error\]|failed|exception)"; then
            log "Error, restarting..."; EXIT_CODE=1; break
        fi
        sleep 0.2
    done
    cleanup_launch; rm -f "$LOG"
    [ "$STOP_REQUESTED" = "1" ] && break
    log "Restart after 0.5s..."; sleep 0.5
done
cleanup_launch; rm -f "$PIDFILE"
log "Beacon watchdog exited"
