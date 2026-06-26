#!/usr/bin/env python3
"""
Octomap 生成和导出脚本
支持多种分辨率配置
"""

import subprocess
import os
import sys
from datetime import datetime

def export_octomap(db_path, resolution=0.02):
    """从 RTAB-Map 数据库导出 Octomap"""

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print(f"\n{'='*60}")
    print(f"从 RTAB-Map 地图导出 Octomap")
    print(f"{'='*60}")
    print(f"数据库: {db_path}")
    print(f"分辨率: {resolution}m")
    print(f"{'='*60}\n")

    # 创建输出文件名
    output_dir = os.path.dirname(db_path)
    basename = os.path.basename(db_path).replace('.db', '')
    output_file = os.path.join(output_dir, f"{basename}_octomap_{resolution}m.bt")

    print(f"输出文件: {output_file}")
    print(f"数据库大小: {os.path.getsize(db_path) / (1024*1024):.2f} MB\n")

    # 方法 1: 使用 rtabmap-export
    print("正在使用 rtabmap-export 导出...")
    print(f"命令: rtabmap-export --db {db_path} --output {output_file} --resolution {resolution}\n")

    try:
        result = subprocess.run(
            ['rtabmap-export', '--db', db_path, '--output', output_file, '--resolution', str(resolution)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"✅ 导出成功!\n")
            print(f"输出文件信息:")
            if os.path.exists(output_file):
                size = os.path.getsize(output_file) / (1024*1024)
                print(f"  文件大小: {size:.2f} MB")
                print(f"  文件路径: {output_file}\n")

                print("后续操作:")
                print(f"  查看: octomap-viewer {output_file}")
                print(f"  信息: octomap-info {output_file}")
                print(f"  ROS: ros2 run octomap_server octomap_server_node {output_file}\n")
            return True
        else:
            print(f"⚠️  rtabmap-export 返回错误:")
            print(result.stderr)
            print("\n使用备用方法...\n")
            return export_octomap_ros_method(db_path, output_file, resolution)

    except subprocess.TimeoutExpired:
        print("⚠️  rtabmap-export 超时")
        print("使用备用方法...\n")
        return export_octomap_ros_method(db_path, output_file, resolution)
    except FileNotFoundError:
        print("⚠️  rtabmap-export 不可用")
        print("使用备用方法...\n")
        return export_octomap_ros_method(db_path, output_file, resolution)

def export_octomap_ros_method(db_path, output_file, resolution):
    """使用 ROS2 定位模式导出 Octomap"""

    print("备用方法: 使用 RTAB-Map 定位模式 + octomap_saver\n")
    print("需要手动执行以下步骤:\n")

    print("步骤 1: 启动 RTAB-Map 定位模式")
    print("─────────────────────────────────────")
    camera_key = os.environ.get('FACTOR_PERCEPTION_KEY', '')
    if not camera_key:
        print("⚠️  FACTOR_PERCEPTION_KEY 环境变量未设置，请在环境变量中配置相机密钥")
    cmd1 = f"ros2 launch factor_perception factor_perception_launch.py localization:=true database_path:={db_path} key:={camera_key}"
    print(f"  {cmd1}\n")

    print("步骤 2: 等待地图加载")
    print("─────────────────────────────────────")
    print(f"  等待约 20-30 秒让地图完全加载\n")

    print("步骤 3: 保存 Octomap")
    print("─────────────────────────────────────")
    output_base = output_file.replace('.bt', '')
    cmd2 = f"ros2 run octomap_server octomap_saver -f {output_base} /factor_perception/octomap_binary"
    print(f"  {cmd2}\n")

    print("步骤 4: 停止 RTAB-Map")
    print("─────────────────────────────────────")
    print(f"  pkill -f 'ros2 launch'\n")

    print(f"{'='*60}")
    print("完成后，Octomap 文件将保存为:")
    print(f"  {output_file}")
    print(f"{'='*60}\n")

    return False

def batch_export(db_path, resolutions=[0.01, 0.02, 0.05, 0.10]):
    """批量导出多个分辨率的 Octomap"""

    print(f"\n批量导出多个分辨率的 Octomap")
    print(f"数据库: {db_path}")
    print(f"分辨率列表: {resolutions}\n")

    for res in resolutions:
        print(f"\n{'─'*40}")
        print(f"导出分辨率: {res}m")
        print(f"{'─'*40}\n")

        export_octomap(db_path, res)

        if res == 0.01:
            print("说明: 超高精度，适合工业应用")
        elif res == 0.02:
            print("说明: 高精度，推荐人形机器人 ⭐")
        elif res == 0.05:
            print("说明: 标准精度，通用导航")
        elif res == 0.10:
            print("说明: 低精度，快速规划")

def main():
    """主函数"""

    print("""
╔═══════════════════════════════════════════════════════════╗
║          RTAB-Map Octomap 导出工具                        ║
╚═══════════════════════════════════════════════════════════╝
""")

    if len(sys.argv) < 2:
        print("用法:")
        print("  单个分辨率:")
        print("    python3 export_octomap.py <数据库路径> [分辨率]")
        print("")
        print("  批量导出:")
        print("    python3 export_octomap.py <数据库路径> --batch")
        print("")
        print("示例:")
        print("  python3 export_octomap.py ~/rtabmap_maps/map.db 0.02")
        print("  python3 export_octomap.py ~/rtabmap_maps/map.db --batch")
        print("")
        print("分辨率建议:")
        print("  0.01m - 超高精度")
        print("  0.02m - 高精度（推荐）⭐")
        print("  0.05m - 标准精度")
        print("  0.10m - 低精度")
        sys.exit(1)

    db_path = os.path.expanduser(sys.argv[1])

    if sys.argv[-1] == '--batch':
        # 批量导出
        batch_export(db_path)
    else:
        # 单个分辨率导出
        resolution = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02
        export_octomap(db_path, resolution)

if __name__ == "__main__":
    main()