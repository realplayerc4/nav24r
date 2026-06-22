#!/bin/bash
# Factor Perception 诊断脚本
set -euo pipefail

echo "=========================================="
echo "Factor Perception 诊断检查"
echo "=========================================="

echo ""
echo "1. 检查相机连接..."
lsusb | grep -i "Movidius" && echo "   ✅ OAK-D 相机已连接" || echo "   ❌ 未检测到 OAK-D 相机"

echo ""
echo "2. 检查 ROS2 环境..."
source /opt/ros/jazzy/setup.bash
ros2 topic list 2>/dev/null && echo "   ✅ ROS2 正常" || echo "   ❌ ROS2 有问题"

echo ""
echo "3. 检查 Factor Perception 包..."
ros2 pkg list | grep factor_perception && echo "   ✅ Factor Perception 包已安装" || echo "   ❌ Factor Perception 包未安装"

echo ""
echo "4. 检查组件..."
ros2 component types | grep factor_perception && echo "   ✅ 组件可用" || echo "   ❌ 组件不可用"

echo ""
echo "5. 检查地图数据库..."
echo "   地图目录内容:"
ls -lh ~/rtabmap_maps/ 2>/dev/null || echo "   目录不存在"
ls -lh ~/rtabmap.db 2>/dev/null || echo "   默认地图不存在"

echo ""
echo "=========================================="
echo "诊断完成"
echo "=========================================="

echo ""
echo "建议启动命令（在终端运行）："
echo "建图模式："
echo "  source /opt/ros/jazzy/setup.bash"
echo "  ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=false database_path:=~/rtabmap_maps/test.db"
echo ""
echo "定位模式："
echo "  source /opt/ros/jazzy/setup.bash"
echo "  ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=true database_path:=~/rtabmap.db"