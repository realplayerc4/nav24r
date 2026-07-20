#!/bin/bash
# Factor Perception 启动脚本（改进版）
# 支持建图/续建/定位模式，结构化日志
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
LOG_DIR="${LOG_DIR:-$HOME/.local/share/nav24r/logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/start_factor_$(date +%Y%m%d_%H%M%S).log"

DEFAULT_DB="$HOME/rtabmap.db"
MODE="mapping"
RTABMAP_VIZ="true"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1" | tee -a "$LOG_FILE"; }

cleanup() {
    local exit_code=$?
    log_info "收到终止信号，正在清理..."
    pkill -f "ros2 launch.*factor_perception" 2>/dev/null || true
    log_info "清理完成，日志: $LOG_FILE"
    exit $exit_code
}
trap cleanup SIGINT SIGTERM EXIT

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -m, --mode <mode>   运行模式: mapping (新建), continue (续建), localization (定位), reset (重置)"
    echo "  -v, --viz           启用 RTAB-Map 可视化 (默认启用)"
    echo "  --no-viz            禁用 RTAB-Map 可视化"
    echo "  -h, --help          显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -m mapping              # 新建地图 (默认数据库)"
    echo "  $0 -m continue             # 续建地图 (默认数据库)"
    echo "  $0 -m localization         # 定位模式 (默认数据库)"
    echo "  $0 -m reset                # 重置地图 (删除数据库)"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -v|--viz)
            RTABMAP_VIZ="true"
            shift
            ;;
        --no-viz)
            RTABMAP_VIZ="false"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

if [ -z "$ROS_DISTRO" ]; then
    log_info "正在加载 ROS2 环境..."
    source /opt/ros/jazzy/setup.bash
fi

log_info "检查相机连接..."
if lsusb | grep -qi "Movidius"; then
    log_info "OAK-D 相机已连接"
else
    log_error "未检测到 OAK-D 相机"
    echo "请检查相机 USB 连接"
    exit 1
fi

DATABASE="$DEFAULT_DB"
LOCALIZATION="false"
MODE_DESC="新建地图"

if [ "$MODE" = "localization" ]; then
    LOCALIZATION="true"
    MODE_DESC="定位模式"
elif [ "$MODE" = "continue" ]; then
    LOCALIZATION="false"
    MODE_DESC="续建地图"
elif [ "$MODE" = "reset" ]; then
    if [ -f "$DATABASE" ]; then
        echo -e "${YELLOW}重置地图: 删除数据库 ${DATABASE}${NC}"
        rm -f "$DATABASE"
        echo -e "${GREEN}✓ 数据库已删除${NC}"
    else
        echo -e "${YELLOW}数据库不存在，无需重置: ${DATABASE}${NC}"
    fi
    exit 0
elif [ "$MODE" != "mapping" ]; then
    log_error "未知模式: $MODE（支持: mapping, continue, localization, reset）"
    usage
    exit 1
fi

if [ ! -f "$DATABASE" ] && [ "$MODE" != "mapping" ]; then
    log_error "默认数据库不存在: ${DATABASE}"
    echo "请先使用建图模式创建地图"
    exit 1
fi

if [ -f "$DATABASE" ]; then
    SIZE=$(du -h "$DATABASE" | cut -f1)
    log_info "数据库: ${DATABASE} (${SIZE})"
fi

log_info "启动配置: mode=${MODE_DESC}, db=${DATABASE}, viz=${RTABMAP_VIZ}, localization=${LOCALIZATION}"

log_info "正在启动..."
ros2 launch "${PROJECT_DIR}/factor_perception_auto.launch.py" \
    localization:=${LOCALIZATION} \
    rtabmap_viz:=${RTABMAP_VIZ} \
    database_path:=${DATABASE} &
LAUNCH_PID=$!

wait $LAUNCH_PID
echo "完成"
