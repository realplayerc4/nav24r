#!/usr/bin/env python3
"""
RTAB-Map 点云存储格式分析脚本
"""

import sqlite3
import os
import struct
import sys

def analyze_rtabmap_db(db_path):
    """分析 RTAB-Map 数据库中的点云存储格式"""

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return

    print(f"\n{'='*60}")
    print(f"RTAB-Map 点云存储格式分析")
    print(f"{'='*60}")
    print(f"数据库: {db_path}")
    print(f"文件大小: {os.path.getsize(db_path) / (1024*1024):.2f} MB")
    print(f"{'='*60}\n")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 数据库表结构
        print("📊 数据库表结构:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")

        # 2. Node 表结构（存储关键帧）
        print("\n📋 Node 表结构:")
        cursor.execute("PRAGMA table_info(Node)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        # 3. 检查点云数据存储方式
        print("\n🔍 点云数据存储方式:")

        # RTAB-Map 存储点云的几种方式：
        # 1. 在 Node 表中存储压缩的点云数据
        # 2. 使用单独的表存储深度数据
        # 3. 存储在外部文件中

        # 检查是否有压缩数据列
        cursor.execute("SELECT COUNT(*) FROM Node WHERE depth > 0")
        depth_count = cursor.fetchone()[0]
        print(f"  有深度数据的节点数: {depth_count}")

        # 检查数据大小
        cursor.execute("SELECT id, depth, depth2 FROM Node LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"\n  样本节点 (ID={sample[0]}):")
            if sample[1]:
                print(f"    depth 数据: 存在 (类型: BLOB)")
                print(f"    depth 大小: 可能是压缩的深度图像")
            if sample[2]:
                print(f"    depth2 数据: 存在 (类型: BLOB)")
                print(f"    depth2 大小: 可能是右目深度图像")

        # 4. 点云格式说明
        print("\n💡 RTAB-Map 点云存储格式详解:")

        print("""
RTAB-Map 存储点云的方式：

1. **数据库内存储 (默认)**:
   - 深度图像：存储为压缩的 PNG 或 JPEG 格式
   - 位置：Node 表的 depth 和 depth2 列（BLOB 类型）
   - 压缩方式：zlib 或 libpng/libjpeg
   - 优势：节省空间，便于传输

2. **原始点云数据**:
   - 格式：未压缩的二进制点云
   - 每个 点包含：X, Y, Z 坐标（float32）
   - 可能包含：RGB 颜色、强度、置信度等
   - 存储：作为 BLOB 直接存储

3. **ROS 消息格式**:
   - 类型：sensor_msgs/PointCloud2
   - 结构：
     * header (时间戳 + 坐标系)
     * height, width (点云维度)
     * fields (字段描述：x, y, z, rgb 等)
     * is_bigendian, point_step, row_step
     * data (实际点云数据，二进制)
   - 编码：通常为 XYZ 或 XYZRGB

4. **生成方式**:
   - Factor Perception → 深度图像 → 深度图转点云
   - RTAB-Map → 从深度图像重建 3D 点云
   - Octomap → 从点云生成 3D 占用网格
""")

        # 5. ROS 话题中的点云格式
        print("\n📡 ROS 话题中的点云格式:")

        print("""
发布到 ROS 话题时：

/factor_perception/cloud_obstacles:
  - 类型: sensor_msgs/msg/PointCloud2
  - 内容: 障碍物点云（VIO 检测到的障碍物）
  - 格式: XYZ 或 XYZRGB
  - 压缩: 不压缩，直接传输

/factor_perception/cloud_ground:
  - 类型: sensor_msgs/msg/PointCloud2
  - 内容: 地面点云（可行走区域）
  - 格式: XYZ 或 XYZRGB

/factor_perception/cloud_map:
  - 类型: sensor_msgs/msg/PointCloud2
  - 内容: 全局点云地图（所有节点合并）
  - 格式: XYZRGB（包含颜色信息）
  - 来源: 从数据库重建

/factor_perception/octomap_binary:
  - 类型: octomap_msgs/msg/Octomap
  - 内容: 3D 占用网格地图
  - 格式: 八叉树结构（Octree）
  - 存储: 紧凑的二进制格式
""")

        # 6. 点云数据重建过程
        print("\n🔄 点云数据重建过程:")

        print("""
从数据库到可视化的过程：

1. 数据库存储:
   深度图像 → 压缩 (PNG/JPEG) → 存入数据库

2. 数据加载:
   数据库 → 解压深度图像 → 计算相机内参

3. 点云重建:
   深度图像 + 相机内参 → 反投影 → 3D 点云

4. 坐标转换:
   相机坐标系 → base_link → map 坐标系

5. 发布到 ROS:
   3D 点云 → sensor_msgs/PointCloud2 → ROS 话题

6. 可视化:
   ROS 话题 → RViz → 渲染显示
""")

        # 7. 文件导出选项
        print("\n💾 点云导出格式:")

        print("""
可以从 RTAB-Map 导出的格式：

1. **PCD (Point Cloud Data)**:
   - 格式: PCL 标准格式
   - 扩展名: .pcd
   - 支持二进制和 ASCII
   - 工具: pcl_viewer, meshlab

2. **PLY (Polygon File Format)**:
   - 格式: 通用 3D 格式
   - 扩展名: .ply
   - 可包含颜色和纹理
   - 工具: meshlab, blender

3. **OBJ (Wavefront OBJ)**:
   - 格式: 3D 模型格式
   - 扩展名: .obj
   - 可用于 3D 建模软件

4. **CSV (文本格式)**:
   - 格式: X, Y, Z, RGB
   - 扩展名: .csv
   - 易于分析和处理

导出方法:
- RTAB-Map Database Viewer → File → Export
- 或使用 rtabmap-export 命令行工具
""")

        conn.close()

        print(f"\n{'='*60}")

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # 自动查找最新地图
        maps_dir = os.path.expanduser("~/rtabmap_maps")
        if os.path.exists(maps_dir):
            maps = [f for f in os.listdir(maps_dir) if f.endswith('.db')]
            if maps:
                latest = max([os.path.join(maps_dir, f) for f in maps],
                           key=os.path.getmtime)
                db_path = latest
            else:
                db_path = os.path.expanduser("~/rtabmap.db")
        else:
            db_path = os.path.expanduser("~/rtabmap.db")

    analyze_rtabmap_db(db_path)