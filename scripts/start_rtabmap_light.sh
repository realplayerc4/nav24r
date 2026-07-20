#!/bin/bash
# RTAB-Map 轻量化启动脚本（简化版）
# 禁用内置可视化，使用独立RViz2，只使用默认数据库

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

DEFAULT_DB="$HOME/rtabmap.db"
MODE_CHOICE=""
INTERACTIVE=false
RVIZ_ENABLED=false

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -m, --mode <mode>   启动模式: slam (新建), continue (续建), localization (定位)"
    echo "  --rviz              启动 RViz2 可视化"
    echo "  -i, --interactive   交互式模式"
    echo "  -h, --help          显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -m slam --rviz                    # 新建地图 + RViz2"
    echo "  $0 -m continue                       # 续建默认地图"
    echo "  $0 -m localization                   # 定位模式"
    echo "  $0 -i                                 # 交互式模式"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE_CHOICE="$2"
            shift 2
            ;;
        --rviz)
            RVIZ_ENABLED=true
            shift
            ;;
        -i|--interactive)
            INTERACTIVE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            usage
            exit 1
            ;;
    esac
done

if [ "$INTERACTIVE" = true ]; then
    echo "=========================================="
    echo "RTAB-Map 轻量化启动"
    echo "=========================================="
    echo ""
    echo "请选择模式:"
    echo "  1. 新建地图 (SLAM)"
    echo "  2. 续建地图 (继续上次建图)"
    echo "  3. 定位模式 (使用已有地图)"
    echo ""
    read -rp "请输入选项 (1/2/3): " MODE_INPUT
    case $MODE_INPUT in
        1) MODE_CHOICE="slam" ;;
        2) MODE_CHOICE="continue" ;;
        3) MODE_CHOICE="localization" ;;
        *) echo "无效选项，使用默认: 新建地图"; MODE_CHOICE="slam" ;;
    esac
    echo ""
    read -rp "是否启动轻量化 RViz2? (y/n): " RVIZ_INPUT
    if [[ "$RVIZ_INPUT" == "y" || "$RVIZ_INPUT" == "Y" ]]; then
        RVIZ_ENABLED=true
    fi
fi

MODE=""
MODE_DESC=""

case $MODE_CHOICE in
    slam|"")
        MODE=""
        MODE_DESC="新建地图"
        ;;
    continue)
        MODE=""
        MODE_DESC="续建地图（同新建，RTAB-Map 自动加载已有地图）"
        ;;
    localization)
        MODE="localization:=true"
        MODE_DESC="定位模式"
        ;;
    *)
        echo "无效模式: $MODE_CHOICE (可选: slam, continue, localization)"
        exit 1
        ;;
esac

echo ""
echo "启动参数:"
echo "  模式: $MODE_DESC"
echo "  数据库: $DEFAULT_DB"
echo "  RViz2: $RVIZ_ENABLED"
echo ""

if [ "$MODE_CHOICE" != "slam" ] && [ ! -f "$DEFAULT_DB" ]; then
    echo -e "${RED}✗ 默认数据库不存在: ${DEFAULT_DB}${NC}"
    echo "请先使用建图模式创建地图"
    exit 1
fi

echo "启动 Factor Perception + RTAB-Map (无可视化)..."

ros2 launch ${PROJECT_DIR}/factor_perception_auto.launch.py \
    camera_model:=OAK-D-PRO-W \
    cam_pos_z:=0.85 \
    config_path:=${PROJECT_DIR}/config/rtabmap.ini \
    database_path:=${DEFAULT_DB} \
    rtabmap_viz:=false \
    $MODE &

SLAM_PID=$!
echo "SLAM 进程 PID: $SLAM_PID"

sleep 5

if [ "$RVIZ_ENABLED" = true ]; then
    echo ""
    echo "启动轻量化 RViz2..."
    RVIZ_CONFIG="${PROJECT_DIR}/config/rtabmap_light.rviz"
    if [ ! -f "$RVIZ_CONFIG" ]; then
        echo "警告: 轻量化配置文件不存在，使用默认配置"
        RVIZ_CONFIG="/opt/ros/jazzy/share/factor_perception/config/factor_perception.rviz"
    fi
    rviz2 -d "$RVIZ_CONFIG" &
    RVIZ_PID=$!
    echo "RViz2 进程 PID: $RVIZ_PID"
fi

echo ""
echo "=========================================="
echo "系统已启动"
echo "=========================================="
echo ""
echo "监控命令:"
echo "  查看节点: ros2 node list"
echo "  查看话题: ros2 topic list"
echo "  查看地图: ros2 topic echo /factor_perception/map"
echo "  查看信息: ros2 topic echo /factor_perception/info"
echo ""
echo "停止系统:"
echo "  kill $SLAM_PID"
if [ "$RVIZ_ENABLED" = true ]; then
    echo "  kill $RVIZ_PID (RViz2)"
fi
echo ""

wait $SLAM_PID

if [ "$RVIZ_ENABLED" = true ]; then
    kill $RVIZ_PID 2>/dev/null || true
fi

echo "完成"
