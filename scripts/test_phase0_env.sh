#!/bin/bash
# nav24r 测试 - 阶段 0：环境预检
# 用法: bash ~/nav24r/scripts/test_phase0_env.sh

PASS=0; FAIL=0; WARN=0

check() {
    local desc="$1" cmd="$2" expected="$3"
    echo -n "  $desc ... "
    result=$(eval "$cmd" 2>&1)
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        echo "✅ $expected"
        ((PASS++))
    elif [ $? -eq 0 ]; then
        echo "⚠️  输出为空"
        ((WARN++))
    else
        echo "❌ 失败"
        ((FAIL++))
    fi
}

echo "=========================================="
echo "阶段 0：环境预检"
echo "=========================================="
echo ""

# 0.1 ROS2 环境
echo "[0.1] ROS2 Jazzy 环境"
if [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
    ROS_VER=$(ros2 --version 2>/dev/null)
    echo "  ✅ ROS2 已加载: $ROS_VER"
    ((PASS++))
else
    echo "  ❌ /opt/ros/jazzy/setup.bash 不存在"
    ((FAIL++))
fi

# 0.2 factor_perception 包
echo "[0.2] Factor Perception 包"
if ros2 pkg list 2>/dev/null | grep -q factor_perception; then
    echo "  ✅ factor_perception 已安装"
    ((PASS++))
else
    echo "  ❌ factor_perception 未安装"
    ((FAIL++))
fi

# 0.3 Nav2 包
echo "[0.3] Nav2 包"
NAV2_COUNT=$(ros2 pkg list 2>/dev/null | grep -c "nav2_" || echo 0)
if [ "$NAV2_COUNT" -gt 5 ]; then
    echo "  ✅ Nav2 包已安装 ($NAV2_COUNT 个)"
    ((PASS++))
else
    echo "  ❌ Nav2 包不足 ($NAV2_COUNT 个)"
    ((FAIL++))
fi

# 0.4 OAK-D 相机
echo "[0.4] OAK-D 相机"
if lsusb 2>/dev/null | grep -qiE "luxonis|oak|03e7"; then
    echo "  ✅ OAK-D 相机已连接"
    lsusb | grep -iE "luxonis|oak|03e7" | head -1
    ((PASS++))
else
    echo "  ⚠️  未检测到 OAK-D 相机（可能需要 sudo 或设备未连接）"
    ((WARN++))
fi

# 0.5 视频设备
echo "[0.5] 视频设备权限"
if ls /dev/video* 2>/dev/null; then
    echo "  ✅ 视频设备存在"
    ((PASS++))
else
    echo "  ⚠️  无视频设备"
    ((WARN++))
fi

# 0.6 FACTOR_PERCEPTION_KEY
echo "[0.6] 相机密钥环境变量"
if [ -n "$FACTOR_PERCEPTION_KEY" ]; then
    KEY_LEN=${#FACTOR_PERCEPTION_KEY}
    echo "  ✅ FACTOR_PERCEPTION_KEY 已设置 (长度: $KEY_LEN)"
    ((PASS++))
else
    echo "  ❌ FACTOR_PERCEPTION_KEY 未设置"
    echo "     请执行: export FACTOR_PERCEPTION_KEY='你的密钥'"
    ((FAIL++))
fi

# 0.7 Cyclone DDS
echo "[0.7] Cyclone DDS"
if [ "$RMW_IMPLEMENTATION" = "rmw_cyclonedds_cpp" ]; then
    echo "  ✅ Cyclone DDS 已配置"
    ((PASS++))
else
    echo "  ⚠️  RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION (建议设为 rmw_cyclonedds_cpp)"
    ((WARN++))
fi

# 0.8 nav24r 包
echo "[0.8] nav24r 包"
if ros2 pkg list 2>/dev/null | grep -q "^nav24r$"; then
    echo "  ✅ nav24r 包已安装"
    ((PASS++))
else
    echo "  ⚠️  nav24r 包未在 ROS2 中注册（可能需要 colcon build）"
    ((WARN++))
fi

# 0.9 rtabmap_slam 包
echo "[0.9] RTAB-Map SLAM 包"
if ros2 pkg list 2>/dev/null | grep -q rtabmap_slam; then
    echo "  ✅ rtabmap_slam 已安装"
    ((PASS++))
else
    echo "  ❌ rtabmap_slam 未安装"
    ((FAIL++))
fi

echo ""
echo "=========================================="
echo "结果: ✅ $PASS 通过 | ⚠️ $WARN 警告 | ❌ $FAIL 失败"
echo "=========================================="
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "⚠️  存在失败项，请先修复后再继续下一阶段测试。"
    exit 1
fi
