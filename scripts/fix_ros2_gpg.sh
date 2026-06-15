#!/bin/bash
# 修复 ROS2 GPG 密钥问题

echo "========================================="
echo "修复 ROS2 仓库 GPG 密钥"
echo "========================================="
echo ""

# 方法 1: 使用新的密钥管理方式（推荐）
echo "[方法 1] 使用新的 GPG 密钥管理方式..."
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# 更新仓库源文件，使用新的密钥格式
echo ""
echo "[方法 2] 更新 sources.list..."
if [ -f /etc/apt/sources.list.d/ros2.list ]; then
    echo "备份旧的 ros2.list..."
    sudo cp /etc/apt/sources.list.d/ros2.list /etc/apt/sources.list.d/ros2.list.bak

    echo "创建新的 ros2.list..."
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
fi

# 同时修复 USTC 镜像的密钥问题
if [ -f /etc/apt/sources.list.d/ros2-ustc.list ]; then
    echo ""
    echo "修复 USTC 镜像的密钥..."
    sudo cp /etc/apt/sources.list.d/ros2-ustc.list /etc/apt/sources.list.d/ros2-ustc.list.bak
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.ustc.edu.cn/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2-ustc.list > /dev/null
fi

# 方法 3: 旧方式（备用）
echo ""
echo "[方法 3] 旧方式添加密钥（备用）..."
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F42ED6FBAB17C654

# 更新软件包列表
echo ""
echo "更新软件包列表..."
sudo apt update

echo ""
echo "========================================="
echo "✅ GPG 密钥修复完成！"
echo "========================================="
echo ""
echo "现在可以继续运行："
echo "  ./scripts/install_dependencies.sh"