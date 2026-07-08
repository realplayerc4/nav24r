#!/bin/bash
# RTAB-Map 轻量化启动脚本
# 禁用内置可视化，使用独立RViz2

set -euo pipefail

# ==================== 参数配置 ====================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

CAMERA_MODEL="OAK-D-PRO-W"
CAM_POS_X="0.0"
CAM_POS_Y="0.0"
CAM_POS_Z="1.0"  # 相机高度1m
CONFIG_PATH="${PROJECT_DIR}/config/rtabmap_custom.ini"
DATABASE_PATH="~/rtabmap.db"
MODE_CHOICE=""
INTERACTIVE=false
RVIZ_ENABLED=false

# ==================== 帮助信息 ====================

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "RTAB-Map 轻量化启动脚本"
    echo ""
    echo "选项:"
    echo "  -m, --mode <mode>       启动模式: slam (新建地图), continue (续建地图), localization (定位模式)"
    echo "  -c, --camera <model>    相机型号 (默认: OAK-D-PRO-W)"
    echo "  -z, --height <m>        相机高度，单位米 (默认: 1.0)"
    echo "  -d, --database <path>   地图数据库路径 (默认: ~/rtabmap.db)"
    echo "  --config <path>         RTAB-Map 配置文件路径"
    echo "  --rviz                  启动 RViz2 可视化"
    echo "  -i, --interactive       交互式模式（使用提示选择参数）"
    echo "  -h, --help              显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -m slam --rviz                    # 新建地图 + RViz2"
    echo "  $0 -m continue -d ~/rtabmap_maps/map.db  # 续建指定地图"
    echo "  $0 -m localization -d ~/rtabmap.db   # 定位模式"
    echo "  $0 -i                                 # 交互式模式"
}

# ==================== 解析参数 ====================

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE_CHOICE="$2"
            shift 2
            ;;
        -c|--camera)
            CAMERA_MODEL="$2"
            shift 2
            ;;
        -z|--height)
            CAM_POS_Z="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE_PATH="$2"
            shift 2
            ;;
        --config)
            CONFIG_PATH="$2"
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

# ==================== 交互模式 ====================

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

# ==================== 设置模式参数 ====================

MODE=""
MODE_DESC=""

case $MODE_CHOICE in
    slam|"")
        MODE=""
        MODE_DESC="新建地图"
        ;;
    continue)
        MODE="continue_mapping:=true"
        MODE_DESC="续建地图"
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
echo "  相机: $CAMERA_MODEL"
echo "  相机高度: $CAM_POS_Z m"
echo "  配置文件: $CONFIG_PATH"
echo "  数据库: $DATABASE_PATH"
echo "  RViz2: $RVIZ_ENABLED"
echo ""

# ==================== 启动 SLAM ====================

echo "启动 Factor Perception + RTAB-Map (无可视化)..."

ros2 launch ${PROJECT_DIR}/factor_perception_auto.launch.py \
    camera_model:=$CAMERA_MODEL \
    cam_pos_z:=$CAM_POS_Z \
    config_path:=$CONFIG_PATH \
    database_path:=$DATABASE_PATH \
    rtabmap_viz:=false \
    $MODE &

SLAM_PID=$!
echo "SLAM 进程 PID: $SLAM_PID"

# 等待SLAM启动
sleep 5

# ==================== 启动 RViz2 ====================

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

# ==================== 状态监控 ====================

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

# 等待 SLAM 进程退出
wait $SLAM_PID

# 清理 RViz2 进程
if [ "$RVIZ_ENABLED" = true ]; then
    kill $RVIZ_PID 2>/dev/null || true
fi

echo "完成"
