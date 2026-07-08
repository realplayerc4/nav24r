#!/bin/bash
# nav24r 测试 - 阶段 2：SLAM 建图测试
# 用法: bash ~/nav24r/scripts/test_phase2_slam.sh
# 注意: 需要先通过阶段 1（相机数据流正常）

set -e

echo "=========================================="
echo "阶段 2：SLAM 建图测试"
echo "=========================================="
echo ""

if [ -z "$AMENT_PREFIX_PATH" ]; then
    source /opt/ros/jazzy/setup.bash
fi

if [ -z "$FACTOR_PERCEPTION_KEY" ]; then
    echo "❌ FACTOR_PERCEPTION_KEY 未设置"
    exit 1
fi

NAV24R_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH_FILE="$NAV24R_DIR/factor_perception_auto.launch.py"
MAPS_DIR=~/rtabmap_maps
mkdir -p "$MAPS_DIR"

MAP_ID="test_$(date +%Y%m%d_%H%M)"
DB_PATH="$MAPS_DIR/${MAP_ID}.db"

echo "[2.1] 启动建图模式..."
echo "  地图 ID: $MAP_ID"
echo "  数据库: $DB_PATH"
echo ""
echo "  命令: ros2 launch $LAUNCH_FILE localization:=false rtabmap_viz:=true database_path:=$DB_PATH"
echo ""

ros2 launch "$LAUNCH_FILE" \
    localization:=false \
    rtabmap_viz:=true \
    database_path:="$DB_PATH" \
    &

LAUNCH_PID=$!
echo "  启动进程 PID: $LAUNCH_PID"

echo ""
echo "[2.2] 等待 SLAM 启动 (15秒)..."
sleep 15

echo ""
echo "[2.3] 检查地图话题..."
if timeout 5 ros2 topic hz /factor_perception/map 2>&1 | grep -q "average rate"; then
    echo "  ✅ 地图话题正在发布"
else
    echo "  ⚠️  地图话题频率较低或未发布（SLAM 可能还在初始化）"
fi

echo ""
echo "=========================================="
echo "⏳ SLAM 已启动，请执行以下操作："
echo "=========================================="
echo ""
echo "  1. 在 RViz2 中确认地图可视化正常"
echo "  2. 缓慢移动相机 2-3 分钟（模拟机器人行走）"
echo "  3. 观察地图是否逐渐扩展且无断裂"
echo ""
echo "  完成后按 Enter 键继续测试..."
read -r

echo ""
echo "[2.4] 检查 SLAM 信息..."
SLAM_INFO=$(timeout 5 ros2 topic echo /factor_perception/info --once 2>/dev/null)
if [ -n "$SLAM_INFO" ]; then
    echo "  ✅ SLAM 信息有数据"
    echo "$SLAM_INFO" | grep -E "node_id|loop_closure_id" | head -5 | sed 's/^/    /'
else
    echo "  ⚠️  SLAM 信息话题无数据"
fi

echo ""
echo "[2.5] 停止 SLAM..."
kill $LAUNCH_PID 2>/dev/null || true
sleep 3
pkill -f "rtabmap" 2>/dev/null || true
pkill -f "factor_perception" 2>/dev/null || true

echo ""
echo "[2.6] 检查地图数据库..."
sleep 2
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo "  ✅ 数据库文件存在: $DB_PATH ($DB_SIZE)"
else
    echo "  ❌ 数据库文件不存在: $DB_PATH"
fi

echo ""
echo "[2.7] 地图质量分析..."
if [ -f "$DB_PATH" ]; then
    python3 "$NAV24R_DIR/scripts/analyze_map_quality.py" "$DB_PATH" 2>/dev/null || echo "  ⚠️  质量分析脚本执行失败"
else
    echo "  ⏭️  跳过（数据库不存在）"
fi

echo ""
echo "=========================================="
echo "阶段 2 测试完成"
echo "  地图数据库: $DB_PATH"
echo "  后续定位测试请使用此数据库"
echo "=========================================="
