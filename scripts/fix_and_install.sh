#!/bin/bash
# 一键修复 GPG 密钥并安装所有依赖

set -euo pipefail

echo "========================================="
echo "ROS2 Jazzy 一键修复和安装脚本"
echo "========================================="
echo ""

# Step 1: 修复 GPG 密钥
echo "[1/5] 修复 ROS2 GPG 密钥..."
echo ""

# 下载并安装新的密钥
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# 更新官方源
if [ -f /etc/apt/sources.list.d/ros2.list ]; then
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    echo "✅ 官方源已更新"
fi

# 更新 USTC 镜像源
if [ -f /etc/apt/sources.list.d/ros2-ustc.list ]; then
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.ustc.edu.cn/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2-ustc.list > /dev/null
    echo "✅ USTC 镜像源已更新"
fi

# Step 2: 更新软件包列表
echo ""
echo "[2/5] 更新软件包列表..."
sudo apt update

# Step 3: 安装 Navigation2
echo ""
echo "[3/5] 安装 Navigation2..."
sudo apt install -y ros-jazzy-navigation2

# Step 4: 安装 robot_localization
echo ""
echo "[4/5] 安装 robot_localization..."
sudo apt install -y ros-jazzy-robot-localization

# Step 5: 安装其他依赖
echo ""
echo "[5/5] 安装其他依赖..."
sudo apt install -y \
    ros-jazzy-nav2-bringup \
    ros-jazzy-slam-toolbox \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-xacro \
    ros-jazzy-tf2-tools \
    ros-jazzy-rviz2 \
    ros-jazzy-rviz-default-plugins

echo ""
echo "========================================="
echo "✅ 安装完成！"
echo "========================================="
echo ""
echo "接下来请运行："
echo "  source /opt/ros/jazzy/setup.bash"
echo "  ./scripts/test_factor_perception.sh"