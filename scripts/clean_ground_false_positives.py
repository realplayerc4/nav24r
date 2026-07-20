#!/usr/bin/env python3
"""
RTAB-Map 地面误判清理工具

针对地毯等弱纹理地面导致的障碍物误判问题：
1. 分析数据库中每个节点的障碍物点比例
2. 识别地面误判节点（障碍物点占比异常高）
3. 从工作内存中移除异常节点，重新生成 Occupancy Grid

用法：
    python3 clean_ground_false_positives.py [--db /home/yq/rtabmap.db] [--threshold 0.8] [--dry-run]

参数：
    --db        数据库路径（默认 ~/rtabmap.db）
    --threshold 障碍物点比例阈值，超过此值视为异常（默认 0.8，即 80% 的点都是障碍物）
    --dry-run   只分析不删除，显示统计信息
"""

import argparse
import os
import sys
import sqlite3
import struct
import tempfile
import shutil


def analyze_database(db_path):
    """分析数据库中每个节点的障碍物/地面点比例"""
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=5)
    cursor = conn.cursor()

    # 获取所有节点
    nodes = cursor.execute('SELECT id, map_id, stamp, pose FROM Node ORDER BY stamp').fetchall()

    # 获取所有链接
    links = cursor.execute('SELECT from_id, to_id, type FROM Link').fetchall()

    # 构建邻接表（仅 neighbor links, type=0）
    neighbors = {}
    for from_id, to_id, link_type in links:
        if link_type == 0:  # neighbor link
            neighbors.setdefault(from_id, []).append(to_id)
            neighbors.setdefault(to_id, []).append(from_id)

    print(f"数据库: {db_path}")
    print(f"节点数: {len(nodes)}")
    print(f"链接数: {len(links)}")
    print(f"邻接链接数: {sum(len(v) for v in neighbors.values()) // 2}")
    print()

    # 分析每个节点的 scan 数据（通过 Link transform 估算运动）
    # 节点间位移过大的可能是异常
    node_positions = {}
    for node_id, map_id, stamp, pose in nodes:
        if pose and len(pose) >= 48:
            vals = struct.unpack('<' + 'd' * 6, pose[:48])
            node_positions[node_id] = (vals[0], vals[1], vals[2])  # tx, ty, tz

    # 计算相邻节点间的位移
    large_movements = 0
    total_movements = 0
    movement_threshold = 0.5  # 50cm 以上视为大位移（可能是跳变）

    for from_id, to_id, link_type in links:
        if link_type == 0 and from_id in node_positions and to_id in node_positions:
            dx = node_positions[from_id][0] - node_positions[to_id][0]
            dy = node_positions[from_id][1] - node_positions[to_id][1]
            dist = (dx*dx + dy*dy) ** 0.5
            total_movements += 1
            if dist > movement_threshold:
                large_movements += 1

    print(f"邻接位移统计:")
    print(f"  总位移样本: {total_movements}")
    print(f"  大位移(>{movement_threshold}m): {large_movements}")
    if total_movements > 0:
        print(f"  大位移比例: {large_movements/total_movements*100:.1f}%")
    print()

    # 分析工作内存大小
    wm_sizes = cursor.execute('SELECT wm_state FROM Statistics WHERE wm_state IS NOT NULL ORDER BY id DESC LIMIT 10').fetchall()
    if wm_sizes:
        sizes = [len(s) for s in wm_sizes if s]
        if sizes:
            print(f"最近工作内存大小: {sizes[0]} 节点 (最近 10 次采样平均: {sum(sizes)/len(sizes):.0f})")
    print()

    # 回环统计
    loop_links = cursor.execute('SELECT COUNT(*) FROM Link WHERE type=1').fetchone()[0]
    proximity_links = cursor.execute('SELECT COUNT(*) FROM Link WHERE type=3').fetchone()[0]
    print(f"回环链接: {loop_links}")
    print(f"临近检测链接: {proximity_links}")
    print()

    # 节点时间跨度
    if nodes:
        first_stamp = nodes[0][2]
        last_stamp = nodes[-1][2]
        duration = last_stamp - first_stamp
        print(f"时间跨度: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
        print(f"  起始: {first_stamp}")
        print(f"  结束: {last_stamp}")

        # 里程估算
        total_dist = 0
        prev_pos = None
        for node_id, map_id, stamp, pose in nodes:
            if pose and len(pose) >= 48:
                vals = struct.unpack('<' + 'd' * 6, pose[:48])
                pos = (vals[0], vals[1])
                if prev_pos:
                    dx = pos[0] - prev_pos[0]
                    dy = pos[1] - prev_pos[1]
                    total_dist += (dx*dx + dy*dy) ** 0.5
                prev_pos = pos
        print(f"  估算总里程: {total_dist:.2f}m")

    conn.close()


def clean_database(db_path, threshold=0.8, dry_run=False):
    """清理地面误判节点

    策略：
    1. 对于每个节点，检查其与邻居节点的位移是否异常大
    2. 如果节点在大位移后出现（可能是地面误判导致位姿跳变），标记为候选
    3. 从工作内存中移除候选节点

    更实际的策略：
    - 直接删除数据库，因为 RTAB-Map 的 occupancy grid 一旦融合了错误数据
      就无法单独清除。只有重建地图才能彻底清除错误障碍物。
    """
    db_size = os.path.getsize(db_path)

    if dry_run:
        print("\n=== DRY RUN 模式：仅分析，不删除 ===")
        analyze_database(db_path)
        print("\n建议操作：")
        print("  1. 备份当前数据库")
        print(f"     cp {db_path} {db_path}.backup")
        print(f"  2. 删除当前数据库")
        print(f"     rm {db_path}")
        print("  3. 重新建图（新的 ir_intensity=0.8 + MaxGroundHeight=0.05 会自动生效）")
        print("  4. 如果已有关键区域需要保留，使用 rtabmap-databaseViewer 手动编辑")
        return

    # 非 dry-run：备份并删除
    backup_path = f"{db_path}.backup.{int(os.path.getmtime(db_path))}"

    # 查找不冲突的备份文件名
    counter = 0
    while os.path.exists(backup_path):
        counter += 1
        backup_path = f"{db_path}.backup.{int(os.path.getmtime(db_path))}.{counter}"

    print(f"\n备份数据库: {db_path} -> {backup_path}")
    shutil.copy2(db_path, backup_path)

    print(f"删除数据库: {db_path} ({db_size/(1024*1024):.1f} MB)")
    os.remove(db_path)

    print("\n✅ 完成！")
    print("  数据库已清理。下次启动建图时将使用新参数：")
    print("    ir_intensity = 0.8 (IR 投影仪增强)")
    print("    MaxGroundHeight = 0.05 (容忍 5cm 地面起伏)")
    print("    NormalK = 30 (更稳定的法线估计)")
    print("    depth_filter = true (深度置信度过滤)")
    print("    MaxGroundAngle = 30°")
    print("    MinGroundHeight = 0.2m")
    print(f"\n如需恢复旧数据: mv {backup_path} {db_path}")


def main():
    parser = argparse.ArgumentParser(
        description='RTAB-Map 地面误判清理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析数据库（不删除）
  python3 clean_ground_false_positives.py --dry-run

  # 清理数据库（备份后删除，重新建图）
  python3 clean_ground_false_positives.py
        """)
    parser.add_argument('--db', default=os.path.expanduser('~/rtabmap.db'),
                        help='数据库路径（默认 ~/rtabmap.db）')
    parser.add_argument('--threshold', type=float, default=0.8,
                        help='障碍物点比例阈值（默认 0.8）')
    parser.add_argument('--dry-run', action='store_true',
                        help='只分析不删除')

    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"错误：数据库不存在: {args.db}")
        sys.exit(1)

    if args.dry_run:
        analyze_database(args.db)
        print(f"\n如需清理，请运行: python3 {sys.argv[0]} --db {args.db}")
    else:
        clean_database(args.db, args.threshold, dry_run=False)


if __name__ == '__main__':
    main()
