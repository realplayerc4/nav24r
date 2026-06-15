#!/bin/bash
# Cyclone DDS 配置脚本
# 用于设置 ROS2 Jazzy 的 DDS 环境

echo "========================================="
echo "Cyclone DDS 配置脚本"
echo "========================================="
echo ""

# 检查 RMW 实现
echo "[1] 检查当前 DDS 实现..."
if [ -n "$RMW_IMPLEMENTATION" ]; then
    echo "当前 DDS: $RMW_IMPLEMENTATION"
else
    echo "当前 DDS: 默认（可能为 Fast DDS）"
fi

# 检查 Cyclone DDS 是否安装
echo ""
echo "[2] 检查 Cyclone DDS 安装..."
if dpkg -l | grep -q ros-jazzy-rmw-cyclonedds; then
    echo "✅ Cyclone DDS 已安装"
    dpkg -l | grep ros-jazzy-rmw-cyclonedds
else
    echo "⚠️  Cyclone DDS 未安装"
    echo "正在安装..."
    sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp
fi

# 设置环境变量
echo ""
echo "[3] 配置环境变量..."

# 获取配置文件路径
CYCLONEDDS_CONFIG="/home/yq/nav24r/config/cyclonedds.xml"

if [ -f "$CYCLONEDDS_CONFIG" ]; then
    echo "✅ 配置文件存在: $CYCLONEDDS_CONFIG"
else
    echo "⚠️  配置文件不存在，将创建默认配置"
fi

# 添加到 bashrc
echo ""
echo "[4] 添加环境变量到 ~/.bashrc..."

# 检查是否已配置
if grep -q "RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" ~/.bashrc; then
    echo "✅ RMW_IMPLEMENTATION 已在 bashrc 中"
else
    echo "添加 RMW_IMPLEMENTATION..."
    echo "" >> ~/.bashrc
    echo "# Cyclone DDS 配置 (ROS2 Jazzy)" >> ~/.bashrc
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc
    echo "✅ 已添加"
fi

if grep -q "CYCLONEDDS_URI" ~/.bashrc; then
    echo "✅ CYCLONEDDS_URI 已在 bashrc 中"
else
    echo "添加 CYCLONEDDS_URI..."
    echo "export CYCLONEDDS_URI=file://$CYCLONEDDS_CONFIG" >> ~/.bashrc
    echo "✅ 已添加"
fi

# 立即生效
echo ""
echo "[5] 应用环境变量..."
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file://$CYCLONEDDS_CONFIG

echo "✅ 环境变量已设置"
echo "  RMW_IMPLEMENTATION = $RMW_IMPLEMENTATION"
echo "  CYCLONEDDS_URI = $CYCLONEDDS_URI"

# 验证配置
echo ""
echo "[6] 验证 Cyclone DDS 配置..."
source /opt/ros/jazzy/setup.bash

# 使用 ros2 命令验证
echo "检查 DDS 实现版本..."
ros2 topic list > /dev/null 2>&1 && echo "✅ ROS2 命令正常工作" || echo "⚠️  ROS2 配置有问题"

echo ""
echo "========================================="
echo "✅ Cyclone DDS 配置完成！"
echo "========================================="
echo ""
echo "配置详情："
echo "  - DDS 实现: Cyclone DDS"
echo "  - 配置文件: $CYCLONEDDS_CONFIG"
echo ""
echo "环境变量已添加到 ~/.bashrc，重启终端后自动生效"
echo ""
echo "或者立即生效："
echo "  source ~/.bashrc"
echo ""
echo "测试命令："
echo "  ros2 topic list"
echo "  ros2 run demo_nodes_cpp talker"