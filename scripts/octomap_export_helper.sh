#!/bin/bash
# 使用 RTAB-Map Database Viewer 导出 Octomap 的自动化脚本

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       RTAB-Map → Octomap 导出助手                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

DB_PATH="$1"
RESOLUTION="${2:-0.02}"

if [ -z "$DB_PATH" ]; then
    echo "用法: $0 <数据库路径> [分辨率]"
    echo ""
    echo "示例:"
    echo "  $0 ~/rtabmap_maps/map_20260615_1424.db 0.02"
    echo ""
    echo "分辨率推荐:"
    echo "  0.02m - 高精度（人形机器人）⭐"
    echo "  0.05m - 标准精度"
    exit 1
fi

DB_PATH=$(eval echo "$DB_PATH")

if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在: $DB_PATH"
    exit 1
fi

echo "数据库: $DB_PATH"
echo "分辨率: ${RESOLUTION}m"
echo "文件大小: $(du -h "$DB_PATH" | cut -f1)"
echo ""
echo "─────────────────────────────────────────────────"
echo "推荐方法: 使用 RTAB-Map Database Viewer GUI"
echo "─────────────────────────────────────────────────"
echo ""
echo "请执行以下操作:"
echo ""
echo "步骤 1: 启动 Database Viewer"
echo "  rtabmap-databaseViewer \"$DB_PATH\""
echo ""
echo "步骤 2: 在 GUI 中导出 Octomap"
echo "  File → Export 3D clouds..."
echo "  ✓ 选择 Export Octomap"
echo "  ✓ 设置 Resolution: ${RESOLUTION}m"
echo "  ✓ 点击 Export"
echo ""
echo "步骤 3: 保存 Octomap 文件"
echo "  文件名建议: $(dirname "$DB_PATH")/$(basename "$DB_PATH" .db)_octomap_${RESOLUTION}m.bt"
echo ""
echo "─────────────────────────────────────────────────"
echo "导出完成后，可以:"
echo "─────────────────────────────────────────────────"
echo ""
echo "查看 Octomap:"
echo "  octomap-viewer <octomap_file>.bt"
echo ""
echo "查看统计信息:"
echo "  octomap-info <octomap_file>.bt"
echo ""
echo "在 ROS2 中加载:"
echo "  ros2 run octomap_server octomap_server_node <octomap_file>.bt"
echo ""
echo "─────────────────────────────────────────────────"
echo ""
echo "💡 提示:"
echo "  • Database Viewer 是最可靠的导出方法"
echo "  • GUI 操作直观，可视化效果好"
echo "  • 支持多种分辨率选择"
echo "  • 导出的 Octomap 可直接用于导航"
echo ""