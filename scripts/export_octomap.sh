#!/bin/bash
# 从现有地图生成高密度 Octomap

echo "========================================="
echo "从 RTAB-Map 地图生成高密度 Octomap"
echo "========================================="
echo ""

DB_PATH="$1"
RESOLUTION="${2:-0.02}"  # 默认 2cm 分辨率

if [ -z "$DB_PATH" ]; then
    echo "用法: $0 <数据库路径> [分辨率]"
    echo ""
    echo "示例:"
    echo "  $0 ~/rtabmap_maps/map_20260615_1424.db 0.02"
    echo "  $0 ~/rtabmap_maps/map_20260615_1424.db 0.05"
    echo ""
    echo "分辨率建议:"
    echo "  0.01m - 超高精度（工业应用）"
    echo "  0.02m - 高精度（推荐人形机器人）⭐"
    echo "  0.05m - 标准精度（通用导航）"
    echo "  0.10m - 低精度（快速规划）"
    exit 1
fi

if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在: $DB_PATH"
    exit 1
fi

echo "数据库: $DB_PATH"
echo "分辨率: ${RESOLUTION}m"
echo ""

# 创建输出目录
OUTPUT_DIR=$(dirname "$DB_PATH")
BASENAME=$(basename "$DB_PATH" .db)
OUTPUT_FILE="${OUTPUT_DIR}/${BASENAME}_octomap_${RESOLUTION}.bt"

echo "输出文件: $OUTPUT_FILE"
echo ""

# 方法 1: 使用 rtabmap-export (如果可用)
if command -v rtabmap-export &> /dev/null; then
    echo "方法 1: 使用 rtabmap-export"
    rtabmap-export \
        --db "$DB_PATH" \
        --output "$OUTPUT_FILE" \
        --resolution "$RESOLUTION"

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Octomap 生成成功!"
        echo ""
        echo "文件信息:"
        ls -lh "$OUTPUT_FILE"
        echo ""
        echo "查看 Octomap:"
        echo "  octomap-viewer $OUTPUT_FILE"
        echo ""
        echo "统计信息:"
        echo "  octomap-info $OUTPUT_FILE"
        exit 0
    fi
fi

# 方法 2: 使用 RTAB-Map 定位模式 + octomap_saver
echo "方法 2: 使用 RTAB-Map 定位模式"
echo ""
echo "步骤 1: 启动 RTAB-Map 定位模式（后台）"
echo "  ros2 launch factor_perception factor_perception_launch.py \\"
echo "    localization:=true \\"
echo "    database_path:=$DB_PATH \\"
echo "    key:=12D0C1E7D1AB466C09BD9AE6427D5240 &"

echo ""
echo "步骤 2: 等待地图加载 (约 20 秒)"
echo "  sleep 20"

echo ""
echo "步骤 3: 保存 Octomap"
echo "  ros2 run octomap_server octomap_saver \\"
echo "    -f ${OUTPUT_FILE%.bt} \\"
echo "    /factor_perception/octomap_binary"

echo ""
echo "步骤 4: 停止 RTAB-Map"
echo "  pkill -f 'ros2 launch'"

echo ""
echo "========================================="
echo "手动执行命令:"
echo "========================================="
echo ""
echo "# 终端 1: 启动定位模式"
echo "ros2 launch factor_perception factor_perception_launch.py \\"
echo "  localization:=true \\"
echo "  database_path:=$DB_PATH \\"
echo "  key:=12D0C1E7D1AB466C09BD9AE6427D5240"
echo ""
echo "# 等待 20 秒让地图加载"
echo "sleep 20"
echo ""
echo "# 终端 2: 保存 Octomap"
echo "ros2 run octomap_server octomap_saver \\"
echo "  -f ${OUTPUT_FILE%.bt} \\"
echo "  /factor_perception/octomap_binary"
echo ""
echo "========================================="