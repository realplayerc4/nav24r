#!/bin/bash
# nav24r 测试 - 阶段 5：全栈集成测试
# 用法: bash ~/nav24r/scripts/test_phase5_fullstack.sh [数据库路径]
# 前置: 需要通过阶段 0-1，阶段 2 建图测试产出的数据库

set -e

echo "=========================================="
echo "阶段 5：全栈集成测试"
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
FULL_LAUNCH="$NAV24R_DIR/launch/nav24r_full.launch.py"

# 确定数据库路径
DB_PATH="${1:-}"
if [ -z "$DB_PATH" ]; then
    # 自动找最新的测试数据库
    LATEST_DB=$(ls -t ~/rtabmap_maps/test_*.db 2>/dev/null | head -1)
    if [ -n "$LATEST_DB" ]; then
        DB_PATH="$LATEST_DB"
        echo "  自动选择最新测试地图: $DB_PATH"
    else
        DB_PATH=~/rtabmap.db
        echo "  ⚠️  未找到测试地图，使用默认: $DB_PATH"
    fi
fi

if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库不存在: $DB_PATH"
    echo "  请先运行阶段 2 建图测试，或指定数据库路径："
    echo "  bash $0 ~/rtabmap_maps/你的地图.db"
    exit 1
fi

echo "[5.1] 启动全栈系统 (Factor Perception + RTAB-Map + Nav2)..."
echo "  数据库: $DB_PATH"
echo ""

ros2 launch "$FULL_LAUNCH" \
    localization:=true \
    database_path:="$DB_PATH" \
    &

LAUNCH_PID=$!
echo "  启动进程 PID: $LAUNCH_PID"

echo ""
echo "[5.2] 等待全栈启动 (20秒)..."
sleep 20

echo ""
echo "[5.3] 检查节点列表..."
NODES=$(ros2 node list 2>/dev/null)

check_node() {
    local node="$1" name="$2"
    if echo "$NODES" | grep -q "$node"; then
        echo "  ✅ $name"
    else
        echo "  ❌ $name 未找到"
    fi
}

check_node "controller_server" "Controller Server"
check_node "planner_server" "Planner Server"
check_node "bt_navigator" "BT Navigator"
check_node "rtabmap" "RTAB-Map SLAM"
check_node "robot_state_publisher" "Robot State Publisher"

echo ""
echo "[5.4] 检查 Nav2 关键话题..."
TOPICS=$(ros2 topic list 2>/dev/null)

check_topic() {
    local topic="$1" name="$2"
    if echo "$TOPICS" | grep -q "$topic"; then
        echo "  ✅ $name"
    else
        echo "  ❌ $name 未找到"
    fi
}

check_topic "/cmd_vel" "速度命令"
check_topic "/plan" "路径规划"
check_topic "/local_costmap/costmap" "局部代价地图"
check_topic "/global_costmap/costmap" "全局代价地图"

echo ""
echo "[5.5] 检查 Nav2 Lifecycle 节点状态..."

check_lifecycle() {
    local node="$1" name="$2"
    STATE=$(timeout 3 ros2 lifecycle get "$node" 2>/dev/null | head -1)
    if echo "$STATE" | grep -qi "active"; then
        echo "  ✅ $name: active"
    elif echo "$STATE" | grep -qi "inactive"; then
        echo "  ⚠️  $name: inactive (未激活!)"
    else
        echo "  ❌ $name: 未知状态 ($STATE)"
    fi
}

check_lifecycle "/controller_server" "Controller Server"
check_lifecycle "/bt_navigator" "BT Navigator"
check_lifecycle "/planner_server" "Planner Server"

echo ""
echo "[5.6] 检查代价地图数据..."

check_costmap() {
    local topic="$1" name="$2"
    DATA=$(timeout 5 ros2 topic echo "$topic" --once 2>/dev/null | head -3)
    if [ -n "$DATA" ]; then
        echo "  ✅ $name 有数据"
    else
        echo "  ⚠️  $name 无数据（可能需要移动相机产生障碍物数据）"
    fi
}

check_costmap "/local_costmap/costmap" "局部代价地图"
check_costmap "/global_costmap/costmap" "全局代价地图"

echo ""
echo "=========================================="
echo "⏳ 全栈系统已启动，请执行以下操作："
echo "=========================================="
echo ""
echo "  1. 在 RViz2 中确认地图和代价地图显示正常"
echo "  2. 使用 'Nav2 Goal' 工具点击地图设置导航目标"
echo "  3. 观察路径规划和速度命令输出"
echo ""
echo "  在另一个终端检查速度命令："
echo "    ros2 topic echo /cmd_vel"
echo ""
echo "  完成后按 Enter 键停止测试..."
read -r

echo ""
echo "[5.7] 停止全栈系统..."
kill $LAUNCH_PID 2>/dev/null || true
sleep 3
pkill -f "nav2" 2>/dev/null || true
pkill -f "rtabmap" 2>/dev/null || true
pkill -f "factor_perception" 2>/dev/null || true

echo ""
echo "=========================================="
echo "阶段 5 测试完成"
echo "=========================================="
