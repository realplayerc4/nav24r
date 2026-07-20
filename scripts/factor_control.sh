#!/bin/bash
# Factor Perception 一键启动脚本（改进版）
# 建图 / 导航 / 完整导航，结构化日志
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
LOG_DIR="${LOG_DIR:-$HOME/.local/share/nav24r/logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/factor_control_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"; }

cleanup() {
    local exit_code=$?
    log_info "收到终止信号，正在停止所有 ROS2 进程..."
    pkill -f "ros2 launch" 2>/dev/null || true
    pkill -f rviz2 2>/dev/null || true
    log_info "清理完成，日志: $LOG_FILE"
    exit $exit_code
}
trap cleanup SIGINT SIGTERM EXIT

usage() {
    echo "用法: $0 [模式]"
    echo ""
    echo "Factor Perception 一键启动脚本"
    echo ""
    echo "模式选项:"
    echo "  mapping    - 建图模式 (SLAM)"
    echo "  navigation - 导航模式 (定位)"
    echo "  nav2       - 完整导航系统 (Factor Perception + Nav2)"
    echo "  stop       - 停止所有进程"
    echo "  -h, --help - 显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 mapping"
    echo "  $0 navigation"
    echo "  $0"
}

MODE=${1:-"mapping"}

case $MODE in
    -h|--help)
        usage
        exit 0
        ;;
    "mapping")
        echo "=== 启动建图模式 ==="
        ros2 launch "${PROJECT_DIR}/factor_perception_auto.launch.py" \
            localization:=false \
            rtabmap_viz:=true
        ;;

    "navigation")
        echo "=== 启动导航模式 ==="
        ros2 launch "${PROJECT_DIR}/factor_perception_auto.launch.py" \
            localization:=true \
            rtabmap_viz:=true
        ;;

    "nav2")
        echo "=== 启动完整导航系统 ==="
        ros2 launch "${PROJECT_DIR}/launch/nav24r_full.launch.py"
        ;;

    "stop")
        echo "=== 停止所有进程 ==="
        pkill -f "ros2 launch"
        pkill -f rviz2
        ;;

    *)
        usage
        exit 1
        ;;
esac
