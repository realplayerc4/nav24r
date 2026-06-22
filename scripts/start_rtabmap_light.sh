#!/bin/bash
# RTAB-Map 轻量化启动脚本
# 禁用内置可视化，使用独立RViz2

# ==================== 参数配置 ====================

CAMERA_MODEL="OAK-D-PRO-W"
CAM_POS_X="0.0"
CAM_POS_Y="0.0"
CAM_POS_Z="1.0"  # 相机高度1m
CONFIG_PATH="$HOME/nav24r/config/rtabmap_custom.ini"
DATABASE_PATH="~/rtabmap.db"

# ==================== 功能选择 ====================

echo "=========================================="
echo "RTAB-Map 轻量化启动"
echo "=========================================="
echo ""
echo "请选择模式:"
echo "  1. 新建地图 (SLAM)"
echo "  2. 续建地图 (继续上次建图)"
echo "  3. 定位模式 (使用已有地图)"
echo ""
read -p "请输入选项 (1/2/3): " MODE_CHOICE

case $MODE_CHOICE in
    1)
        MODE=""
        MODE_DESC="新建地图"
        ;;
    2)
        MODE="continue_mapping:=true"
        MODE_DESC="续建地图"
        ;;
    3)
        MODE="localization:=true"
        MODE_DESC="定位模式"
        ;;
    *)
        echo "无效选项，使用默认: 新建地图"
        MODE=""
        MODE_DESC="新建地图"
        ;;
esac

echo ""
echo "启动参数:"
echo "  模式: $MODE_DESC"
echo "  相机: $CAMERA_MODEL"
echo "  相机高度: $CAM_POS_Z m"
echo "  配置文件: $CONFIG_PATH"
echo ""

# ==================== 启动 SLAM ====================

echo "启动 Factor Perception + RTAB-Map (无可视化)..."

ros2 launch factor_perception factor_perception_auto.launch.py \
    camera_model:=$CAMERA_MODEL \
    cam_pos_z:=$CAM_POS_Z \
    config_path:=$CONFIG_PATH \
    database_path:=$DATABASE_PATH \
    rtabmap_viz:=false \
    $MODE &

SLAM_PID=$!
echo "SLAM 进程 PID: $SLAM_PID"

# 等待SLAM启动
sleep 5

# ==================== 启动 RViz2 ====================

echo ""
read -p "是否启动轻量化 RViz2? (y/n): " RVIZ_CHOICE

if [[ "$RVIZ_CHOICE" == "y" || "$RVIZ_CHOICE" == "Y" ]]; then
    echo "启动轻量化 RViz2..."

    RVIZ_CONFIG="$HOME/nav24r/config/rtabmap_light.rviz"

    if [ ! -f "$RVIZ_CONFIG" ]; then
        echo "警告: 轻量化配置文件不存在，使用默认配置"
        RVIZ_CONFIG="/opt/ros/jazzy/share/factor_perception/config/factor_perception.rviz"
    fi

    rviz2 -d "$RVIZ_CONFIG" &
    RVIZ_PID=$!
    echo "RViz2 进程 PID: $RVIZ_PID"
fi

# ==================== 状态监控 ====================

echo ""
echo "=========================================="
echo "系统已启动"
echo "=========================================="
echo ""
echo "监控命令:"
echo "  查看节点: ros2 node list"
echo "  查看话题: ros2 topic list"
echo "  查看地图: ros2 topic echo /factor_perception/map"
echo "  查看信息: ros2 topic echo /factor_perception/info"
echo ""
echo "停止系统:"
echo "  kill $SLAM_PID"
echo "  kill $RVIZ_PID (如果启动了)"
echo ""

# 等待用户输入退出
read -p "按 Enter 键停止所有进程..."

# 停止进程
echo "停止进程..."
kill $SLAM_PID 2>/dev/null
kill $RVIZ_PID 2>/dev/null

echo "完成"