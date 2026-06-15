#!/bin/bash
# ROS2 Jazzy 依赖安装脚本
# 用于安装 Nav2 和其他缺失的依赖

set -e

echo "========================================="
echo "ROS2 Jazzy 依赖安装脚本"
echo "========================================="
echo ""

# 更新包列表
echo "[1/4] 更新软件包列表..."
sudo apt update

# 安装 Navigation2 完整栈
echo ""
echo "[2/4] 安装 Navigation2..."
sudo apt install -y ros-jazzy-navigation2

# 安装 robot_localization (EKF 融合)
echo ""
echo "[3/4] 安装 robot_localization..."
sudo apt install -y ros-jazzy-robot-localization

# 安装其他常用包
echo ""
echo "[4/4] 安装其他依赖..."
sudo apt install -y \
    ros-jazzy-nav2-bringup \
    ros-jazzy-slam-toolbox \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-xacro \
    ros-jazzy-tf2-tools \
    ros-jazzy-tf2-ros

# 安装 RViz 插件（用于可视化）
echo ""
echo "安装 RViz 插件..."
sudo apt install -y \
    ros-jazzy-rviz2 \
    ros-jazzy-rviz-common \
    ros-jazzy-rviz-default-plugins

echo ""
echo "========================================="
echo "✅ 安装完成！"
echo "========================================="
echo ""
echo "接下来请运行："
echo "  source /opt/ros/jazzy/setup.bash"
echo "  ./test_factor_perception.sh"
