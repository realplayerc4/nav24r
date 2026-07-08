#!/bin/bash
# nav24r 测试 - 阶段 1：Factor Perception 相机数据流验证
# 用法: bash ~/nav24r/scripts/test_phase1_camera.sh
# 注意: 需要先 source /opt/ros/jazzy/setup.bash

set -e

echo "=========================================="
echo "阶段 1：Factor Perception 相机测试"
echo "=========================================="
echo ""

# 确保环境已加载
if [ -z "$AMENT_PREFIX_PATH" ]; then
    source /opt/ros/jazzy/setup.bash
fi

NAV24R_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH_FILE="$NAV24R_DIR/factor_perception_auto.launch.py"

if [ ! -f "$LAUNCH_FILE" ]; then
    echo "❌ 启动文件不存在: $LAUNCH_FILE"
    exit 1
fi

# 检查密钥
if [ -z "$FACTOR_PERCEPTION_KEY" ]; then
    echo "❌ FACTOR_PERCEPTION_KEY 未设置，请先执行:"
    echo "   export FACTOR_PERCEPTION_KEY='你的密钥'"
    exit 1
fi

echo "[1.1] 启动 Factor Perception（无可视化）..."
echo "  命令: ros2 launch $LAUNCH_FILE rtabmap_viz:=false"
echo ""

ros2 launch "$LAUNCH_FILE" rtabmap_viz:=false &
LAUNCH_PID=$!
echo "  启动进程 PID: $LAUNCH_PID"

# 等待节点启动
echo ""
echo "[1.2] 等待节点启动 (10秒)..."
sleep 10

echo ""
echo "[1.3] 检查话题列表..."
TOPICS=$(ros2 topic list 2>/dev/null)

check_topic() {
    local topic="$1" name="$2"
    if echo "$TOPICS" | grep -q "$topic"; then
        echo "  ✅ $name ($topic)"
    else
        echo "  ❌ $name ($topic) 未找到"
    fi
}

check_topic "/factor_perception/odom" "VIO 里程计"
check_topic "/factor_perception/imu" "IMU 数据"
check_topic "/factor_perception/depth/points" "深度点云"

echo ""
echo "[1.4] 检查话题频率 (每个测 5 秒)..."

measure_hz() {
    local topic="$1" name="$2" min_hz="$3"
    echo -n "  $name: "
    HZ=$(timeout 6 ros2 topic hz "$topic" 2>&1 | tail -1 | grep -oP '[\d.]+' | tail -1)
    if [ -n "$HZ" ]; then
        # 使用 awk 进行浮点比较
        if awk "BEGIN{exit !($HZ >= $min_hz)}"; then
            echo "✅ ${HZ}Hz (≥ ${min_hz}Hz)"
        else
            echo "⚠️  ${HZ}Hz (< ${min_hz}Hz 期望)"
        fi
    else
        echo "❌ 无数据"
    fi
}

measure_hz "/factor_perception/odom" "VIO 里程计" 20
measure_hz "/factor_perception/imu" "IMU" 200
measure_hz "/factor_perception/depth/points" "深度点云" 15

echo ""
echo "[1.5] 检查 VIO 里程计数据有效性..."
ODOM_DATA=$(timeout 3 ros2 topic echo /factor_perception/odom --once 2>/dev/null | head -20)
if [ -n "$ODOM_DATA" ]; then
    echo "  ✅ 里程计有数据输出"
    echo "$ODOM_DATA" | grep -E "x:|y:|z:" | head -3 | sed 's/^/    /'
else
    echo "  ❌ 里程计无数据"
fi

echo ""
echo "[1.6] 检查 TF 树..."
TF_CHECK=$(timeout 3 ros2 run tf2_ros tf2_echo map base_link 2>&1 | head -5)
if echo "$TF_CHECK" | grep -qi "transform"; then
    echo "  ✅ map → base_link TF 正常"
else
    echo "  ⚠️  map → base_link TF 可能缺失（尝试 odom → base_link）"
    TF_CHECK2=$(timeout 3 ros2 run tf2_ros tf2_echo odom base_link 2>&1 | head -5)
    if echo "$TF_CHECK2" | grep -qi "transform"; then
        echo "  ✅ odom → base_link TF 正常"
    else
        echo "  ❌ TF 树异常"
    fi
fi

echo ""
echo "[1.7] 停止 Factor Perception..."
kill $LAUNCH_PID 2>/dev/null || true
sleep 2
# 确保清理
pkill -f "factor_perception" 2>/dev/null || true

echo ""
echo "=========================================="
echo "阶段 1 测试完成"
echo "=========================================="
