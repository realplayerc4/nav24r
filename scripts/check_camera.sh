#!/bin/bash
# 启动前检查脚本 - 检查OAK-D相机连接状态

echo "=========================================="
echo "OAK-D 相机连接检查"
echo "=========================================="
echo ""

# 检查USB设备
echo "1. 检查USB设备..."
OAK_DEVICE=$(lsusb | grep -iE "03e7|luxonis|oak|2e1d")

if [ -z "$OAK_DEVICE" ]; then
    echo "❌ 未检测到 OAK-D 相机设备"
    echo ""
    echo "请检查:"
    echo "  - OAK-D 相机是否已通过 USB 线连接"
    echo "  - USB 线是否插紧（建议 USB 3.0 端口）"
    echo "  - 相机电源是否正常"
    echo ""
    echo "当前连接的USB设备:"
    lsusb
    echo ""
    exit 1
else
    echo "✅ 检测到 OAK-D 相机:"
    echo "   $OAK_DEVICE"
fi

echo ""

# 检查depthai包
echo "2. 检查 depthai 安装..."
DEPTHAI_PKG=$(dpkg -l | grep "ros-jazzy-depthai" | head -1)
if [ -n "$DEPTHAI_PKG" ]; then
    echo "✅ depthai 已安装:"
    echo "   $DEPTHAI_PKG"
else
    echo "❌ depthai 未安装"
    exit 1
fi

echo ""

# 检查factor_perception
echo "3. 检查 factor_perception 安装..."
FACTOR_PKG=$(dpkg -l | grep "ros-jazzy-factor-perception" | head -1)
if [ -n "$FACTOR_PKG" ]; then
    echo "✅ factor_perception 已安装:"
    echo "   $FACTOR_PKG"
else
    echo "❌ factor_perception 未安装"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 所有检查通过，可以启动系统"
echo "=========================================="
echo ""
echo "启动命令:"
echo "  cd /home/yq/nav24r"
echo "  ./scripts/start_rtabmap_light.sh"
echo ""

exit 0