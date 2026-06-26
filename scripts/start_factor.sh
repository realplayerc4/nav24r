#!/bin/bash
# Factor Perception 启动脚本
# 支持建图和定位模式

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# 默认参数
MODE="mapping"  # mapping 或 localization
DATABASE=""
RTABMAP_VIZ="true"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -m, --mode <mode>       运行模式: mapping (建图) 或 localization (定位)"
    echo "  -d, --database <path>   地图数据库路径"
    echo "  -v, --viz               启用 RTAB-Map 可视化 (默认启用)"
    echo "  --no-viz                禁用 RTAB-Map 可视化"
    echo "  -h, --help              显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 -m mapping -d ~/rtabmap_maps/new_map.db"
    echo "  $0 -m localization -d ~/rtabmap.db"
    echo "  $0  # 默认建图模式，自动生成地图ID"
}

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -d|--database)
            DATABASE="$2"
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

# 检查 ROS2 环境
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}正在加载 ROS2 环境...${NC}"
    source /opt/ros/jazzy/setup.bash
fi

# 检查相机连接
echo -e "${YELLOW}检查相机连接...${NC}"
if lsusb | grep -qi "Movidius"; then
    echo -e "${GREEN}✓ OAK-D 相机已连接${NC}"
else
    echo -e "${RED}✗ 未检测到 OAK-D 相机${NC}"
    echo "请检查相机 USB 连接"
    exit 1
fi

# 设置数据库路径
if [ -z "$DATABASE" ]; then
    if [ "$MODE" = "mapping" ]; then
        MAP_ID="map_$(date +%Y%m%d_%H%M)"
        DATABASE="$HOME/rtabmap_maps/${MAP_ID}.db"
        mkdir -p ~/rtabmap_maps
        echo -e "${GREEN}自动生成地图ID: ${MAP_ID}${NC}"
    else
        DATABASE="$HOME/rtabmap.db"
        echo -e "${YELLOW}使用默认地图: ${DATABASE}${NC}"
    fi
fi

# 检查定位模式的地图是否存在
if [ "$MODE" = "localization" ]; then
    if [ ! -f "$DATABASE" ]; then
        echo -e "${RED}✗ 地图文件不存在: ${DATABASE}${NC}"
        exit 1
    fi
    SIZE=$(du -h "$DATABASE" | cut -f1)
    echo -e "${GREEN}✓ 找到地图: ${DATABASE} (${SIZE})${NC}"
fi

# 设置参数
LOCALIZATION="false"
if [ "$MODE" = "localization" ]; then
    LOCALIZATION="true"
fi

echo ""
echo "=========================================="
echo "Factor Perception 启动配置"
echo "=========================================="
echo "模式:         $MODE"
echo "数据库:       $DATABASE"
echo "可视化:       $RTABMAP_VIZ"
echo "定位模式:     $LOCALIZATION"
echo "=========================================="
echo ""

# 启动
echo -e "${GREEN}正在启动...${NC}"
ros2 launch "${PROJECT_DIR}/factor_perception_auto.launch.py" \
    localization:=${LOCALIZATION} \
    rtabmap_viz:=${RTABMAP_VIZ} \
    database_path:=${DATABASE}
