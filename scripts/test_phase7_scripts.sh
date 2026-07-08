#!/bin/bash
# nav24r 测试 - 阶段 7：脚本与工具验证
# 用法: bash ~/nav24r/scripts/test_phase7_scripts.sh
# 不需要 ROS2 环境，纯静态验证

set -e

echo "=========================================="
echo "阶段 7：脚本与工具验证"
echo "=========================================="
echo ""

NAV24R_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0; FAIL=0

echo "[7.1] Shell 脚本语法检查..."

check_bash_syntax() {
    local file="$1" name="$2"
    echo -n "  $name: "
    if bash -n "$file" 2>/dev/null; then
        echo "✅ 语法正常"
        ((PASS++))
    else
        echo "❌ 语法错误"
        ((FAIL++))
    fi
}

check_bash_syntax "$NAV24R_DIR/scripts/diagnose.sh" "diagnose.sh"
check_bash_syntax "$NAV24R_DIR/scripts/start_rtabmap_light.sh" "start_rtabmap_light.sh"
check_bash_syntax "$NAV24R_DIR/scripts/export_octomap.sh" "export_octomap.sh"
check_bash_syntax "$NAV24R_DIR/scripts/check_camera.sh" "check_camera.sh"
check_bash_syntax "$NAV24R_DIR/scripts/setup_cyclonedds.sh" "setup_cyclonedds.sh"
check_bash_syntax "$NAV24R_DIR/scripts/factor_control.sh" "factor_control.sh"

echo ""
echo "[7.2] Python 配置文件加载..."

check_yaml() {
    local file="$1" name="$2"
    echo -n "  $name: "
    if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        echo "✅ YAML 有效"
        ((PASS++))
    else
        echo "❌ YAML 加载失败"
        ((FAIL++))
    fi
}

check_yaml "$NAV24R_DIR/config/factor_perception_config.yaml" "factor_perception_config.yaml"
check_yaml "$NAV24R_DIR/config/nav2_params.yaml" "nav2_params.yaml"

echo ""
echo "[7.3] JSON 配置文件加载..."
echo -n "  maps_config.json: "
if python3 -c "import json; json.load(open('$NAV24R_DIR/config/maps_config.json'))" 2>/dev/null; then
    echo "✅ JSON 有效"
    ((PASS++))
else
    echo "❌ JSON 加载失败"
    ((FAIL++))
fi

echo ""
echo "[7.4] 单元测试..."
echo -n "  pytest: "
if python3 -m pytest "$NAV24R_DIR/test/" -v --tb=short 2>&1 | tail -2 | grep -q "passed"; then
    TEST_RESULT=$(python3 -m pytest "$NAV24R_DIR/test/" -v --tb=short 2>&1 | tail -1)
    echo "✅ $TEST_RESULT"
    ((PASS++))
else
    echo "❌ 测试失败"
    ((FAIL++))
fi

echo ""
echo "[7.5] Calibrat/install_requirements.py..."
echo -n "  import 检查: "
if python3 -c "import sys; sys.path.insert(0, '$NAV24R_DIR'); from Calibrat.install_requirements import main; print('OK')" 2>/dev/null; then
    echo "✅ 可导入"
    ((PASS++))
else
    echo "❌ 导入失败"
    ((FAIL++))
fi

echo ""
echo "[7.6] 已弃用文件验证..."
echo -n "  rtabmap_3d.ini: "
if [ -f "$NAV24R_DIR/config/rtabmap_3d.ini" ]; then
    echo "❌ 已弃用文件仍存在"
    ((FAIL++))
else
    echo "✅ 已移除"
    ((PASS++))
fi

echo ""
echo "[7.7] diagnose.sh ROS 版本检查..."
echo -n "  humble 残留: "
HUMBLE_COUNT=$(grep -c "humble" "$NAV24R_DIR/scripts/diagnose.sh" 2>/dev/null || echo 0)
if [ "$HUMBLE_COUNT" -eq 0 ]; then
    echo "✅ 无 humble 残留"
    ((PASS++))
else
    echo "❌ 仍有 $HUMBLE_COUNT 处 humble 引用"
    ((FAIL++))
fi

echo ""
echo "=========================================="
echo "结果: ✅ $PASS 通过 | ❌ $FAIL 失败"
echo "=========================================="
