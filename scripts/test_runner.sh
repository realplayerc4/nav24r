#!/bin/bash
# nav24r 测试总入口
# 用法: bash ~/nav24r/scripts/test_runner.sh [阶段号]
# 示例:
#   bash ~/nav24r/scripts/test_runner.sh 0      # 仅运行阶段 0
#   bash ~/nav24r/scripts/test_runner.sh 1      # 仅运行阶段 1
#   bash ~/nav24r/scripts/test_runner.sh all     # 依次运行全部

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PHASE="${1:-}"

echo "╔══════════════════════════════════════════╗"
echo "║     nav24r 测试套件                      ║"
echo "║     ROS2 Jazzy + Factor Perception       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if [ -z "$PHASE" ]; then
    echo "用法: bash $0 [阶段号]"
    echo ""
    echo "可用阶段:"
    echo "  0  - 环境预检（5分钟，必做）"
    echo "  1  - Factor Perception 相机测试（10分钟，必做）"
    echo "  2  - SLAM 建图测试（15分钟，推荐）"
    echo "  5  - 全栈集成测试（20分钟，核心）"
    echo "  7  - 脚本与工具验证（5分钟，可选）"
    echo "  all - 依次运行全部"
    echo ""
    echo "前置条件:"
    echo "  1. OAK-D Pro 相机已连接 USB 3.0"
    echo "  2. FACTOR_PERCEPTION_KEY 环境变量已设置"
    echo "  3. ROS2 Jazzy 环境已安装"
    exit 0
fi

# 确保环境变量
if [ -z "$AMENT_PREFIX_PATH" ] && [ -f /opt/ros/jazzy/setup.bash ]; then
    source /opt/ros/jazzy/setup.bash
fi

run_phase() {
    local phase="$1"
    local script=""
    case $phase in
        0) script="$SCRIPT_DIR/test_phase0_env.sh" ;;
        1) script="$SCRIPT_DIR/test_phase1_camera.sh" ;;
        2) script="$SCRIPT_DIR/test_phase2_slam.sh" ;;
        5) script="$SCRIPT_DIR/test_phase5_fullstack.sh" ;;
        7) script="$SCRIPT_DIR/test_phase7_scripts.sh" ;;
        *)
            echo "❌ 未知阶段: $phase"
            return 1
            ;;
    esac

    if [ ! -f "$script" ]; then
        echo "❌ 测试脚本不存在: $script"
        return 1
    fi

    echo "▶▶▶ 阶段 $phase ▶▶▶"
    bash "$script"
    local result=$?
    echo ""
    if [ $result -eq 0 ]; then
        echo "✅ 阶段 $phase 通过"
    else
        echo "❌ 阶段 $phase 失败 (exit code: $result)"
    fi
    echo ""
    return $result
}

if [ "$PHASE" = "all" ]; then
    FAILED=()
    for p in 0 1 2 5 7; do
        if ! run_phase $p; then
            FAILED+=($p)
            echo "⚠️  阶段 $p 失败，是否继续下一阶段？(y/n)"
            read -r CONTINUE
            if [ "$CONTINUE" != "y" ]; then
                break
            fi
        fi
    done

    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║     测试总结                             ║"
    echo "╚══════════════════════════════════════════╝"
    if [ ${#FAILED[@]} -eq 0 ]; then
        echo "  🎉 全部阶段通过！"
    else
        echo "  ❌ 失败阶段: ${FAILED[*]}"
    fi
else
    run_phase "$PHASE"
fi
