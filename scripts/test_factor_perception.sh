#!/bin/bash
# Factor Perception 测试脚本 - ROS2 Jazzy 版本

echo "========================================="
echo "Factor Perception 测试脚本"
echo "ROS2 Jazzy + Ubuntu 24.04"
echo "========================================="
echo ""

# Source ROS2 环境
echo "[1/6] 加载 ROS2 Jazzy 环境..."
source /opt/ros/jazzy/setup.bash

# 检查相机设备
echo ""
echo "[2/6] 检查 OAK-D 相机连接..."
if lsusb | grep -i "luxonis\|oak\|intel" | grep -v "Bluetooth"; then
    echo "✅ 检测到相机设备"
else
    echo "⚠️  未检测到 OAK-D 相机"
    echo "   请检查："
    echo "   1. 相机是否通过 USB 3.0 连接"
    echo "   2. USB 线缆是否正常"
    echo "   3. 尝试运行: lsusb -v | grep -A 5 Luxonis"
    echo ""
    read -p "是否继续测试？ (y/n): " continue_test
    if [[ $continue_test != "y" ]]; then
        exit 1
    fi
fi

# 检查视频设备权限
echo ""
echo "[3/6] 检查视频设备权限..."
if ls -la /dev/video* 2>/dev/null; then
    echo "✅ 找到视频设备"
else
    echo "⚠️  未找到视频设备"
fi

# 测试 Factor Perception 启动
echo ""
echo "[4/6] 启动 Factor Perception..."
echo "使用参数："
echo "  - publish_tf: true (默认)"
echo "  - depth_filter: true (推荐)"
echo "  - ir_intensity: 0.4 (室内环境)"
echo "  - key: 12D0C1E7D1AB466C09BD9AE6427D5240"
echo ""
echo "按 Ctrl+C 停止测试..."
echo ""

ros2 launch factor_perception factor_perception_launch.py \
    key:=12D0C1E7D1AB466C09BD9AE6427D5240 \
    depth_filter:=true \
    ir_intensity:=0.4 \
    cam_pos_z:=0.5

# 注意：上面的命令会阻塞，直到用户按 Ctrl+C
# Ctrl+C 后继续执行后续检查

echo ""
echo "[5/6] 检查话题发布情况..."
echo "活动话题列表："
ros2 topic list

echo ""
echo "检查关键话题频率："
echo "  /camera/odom:"
timeout 5 ros2 topic hz /camera/odom || echo "⚠️  话题未发布"

echo ""
echo "  /camera/imu:"
timeout 5 ros2 topic hz /camera/imu || echo "⚠️  话题未发布"

echo ""
echo "  /camera/depth/points:"
timeout 5 ros2 topic hz /camera/depth/points || echo "⚠️  话题未发布"

# 检查 TF 树
echo ""
echo "[6/6] 检查 TF 树..."
ros2 run tf2_tools view_frames
if [ -f frames.pdf ]; then
    echo "✅ TF 树已生成: frames.pdf"
    echo "   可以使用: evince frames.pdf 查看"
fi

echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
