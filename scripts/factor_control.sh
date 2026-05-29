#!/bin/bash
# Factor Perception 一键启动脚本
# 建图模式 vs 导航模式

MODE=${1:-"mapping"}

case $MODE in
    "mapping")
        echo "=== 启动建图模式 ==="
        ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py \
            localization:=false \
            rtabmap_viz:=true
        ;;

    "navigation")
        echo "=== 启动导航模式 ==="
        ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py \
            localization:=true \
            rtabmap_viz:=true
        ;;

    "nav2")
        echo "=== 启动完整导航系统 ==="
        ros2 launch /home/yq/nav24r/launch/nav24r_full.launch.py
        ;;

    "stop")
        echo "=== 停止所有进程 ==="
        pkill -f "ros2 launch"
        pkill -f rviz2
        ;;

    *)
        echo "用法: $0 [mode]"
        echo ""
        echo "模式选项:"
        echo "  mapping    - 建图模式 (SLAM)"
        echo "  navigation - 导航模式 (定位)"
        echo "  nav2       - 完整导航系统 (Factor Perception + Nav2)"
        echo "  stop       - 停止所有进程"
        ;;
esac