#!/usr/bin/env python3
"""
RTAB-Map 地图质量分析工具 (增强版)
"""

import sqlite3
import os
import sys
from datetime import datetime

def analyze_map(db_path):
    """分析 RTAB-Map 数据库质量"""

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return

    print(f"\n{'='*60}")
    print(f"RTAB-Map 地图质量分析")
    print(f"{'='*60}")
    print(f"数据库: {db_path}")
    print(f"文件大小: {os.path.getsize(db_path) / (1024*1024):.2f} MB")
    print(f"{'='*60}\n")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 节点统计
        cursor.execute("SELECT COUNT(*) FROM Node")
        total_nodes = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(stamp), MAX(stamp) FROM Node")
        min_stamp, max_stamp = cursor.fetchone()

        print("📊 节点统计")
        print(f"  总节点数: {total_nodes}")
        if min_stamp and max_stamp:
            duration = (max_stamp - min_stamp)
            print(f"  建图时长: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
            print(f"  平均建图频率: {total_nodes/duration:.2f} Hz" if duration > 0 else "")

        # 2. 链接统计
        cursor.execute("SELECT COUNT(*) FROM Link")
        total_links = cursor.fetchone()[0]

        print(f"\n🔗 链接统计")
        print(f"  总链接数: {total_links}")
        print(f"  平均每个节点链接数: {total_links/total_nodes:.2f}" if total_nodes > 0 else "")

        # 链接类型分布
        cursor.execute("SELECT type, COUNT(*) FROM Link GROUP BY type ORDER BY COUNT(*) DESC")
        link_stats = cursor.fetchall()

        type_names = {
            0: "邻居链接",
            1: "全局闭环",
            2: "局部闭环",
            3: "虚拟链接",
            9: "其他链接"
        }

        for link_type, count in link_stats:
            type_name = type_names.get(link_type, f"类型{link_type}")
            print(f"    {type_name}: {count} ({count/total_links*100:.1f}%)" if total_links > 0 else "")

        # 3. 闭环检测质量
        cursor.execute("SELECT COUNT(*) FROM Link WHERE type = 1 OR type = 2")
        loop_closures = cursor.fetchone()[0]

        print(f"\n🔄 闭环检测")
        print(f"  闭环总数: {loop_closures}")
        print(f"  闭环密度: {loop_closures/total_nodes*100:.2f}%" if total_nodes > 0 else "")

        # 4. 空间分布分析
        print(f"\n📐 空间分布")
        cursor.execute("SELECT id FROM Node")
        nodes = cursor.fetchall()

        if len(nodes) > 10:
            # 抽样检查节点间距
            sample_size = min(50, len(nodes))
            cursor.execute(f"SELECT id FROM Node ORDER BY stamp LIMIT {sample_size}")
            sample_nodes = [n[0] for n in cursor.fetchall()]

            print(f"  分析样本数: {sample_size}")

        # 5. 地图质量评估
        print(f"\n{'='*60}")
        print("📈 地图质量评估")
        print(f"{'='*60}")

        score = 0
        max_score = 100
        issues = []
        recommendations = []

        # 节点数量评分 (25分)
        if total_nodes > 200:
            score += 25
            print(f"  ✅ 节点数量充足 ({total_nodes} > 200)")
        elif total_nodes > 100:
            score += 20
            print(f"  ✅ 节点数量良好 ({total_nodes} > 100)")
        elif total_nodes > 50:
            score += 15
            print(f"  ⚠️  节点数量中等 ({total_nodes})")
            recommendations.append("建议增加建图路径覆盖")
        else:
            score += 5
            print(f"  ❌ 节点数量较少 ({total_nodes})")
            issues.append("节点数量不足，地图覆盖范围有限")

        # 链接密度评分 (25分)
        link_density = total_links / total_nodes if total_nodes > 0 else 0
        if link_density > 2.5:
            score += 25
            print(f"  ✅ 链接密度优秀 ({link_density:.2f})")
        elif link_density > 2.0:
            score += 20
            print(f"  ✅ 链接密度良好 ({link_density:.2f})")
        elif link_density > 1.5:
            score += 15
            print(f"  ⚠️  链接密度中等 ({link_density:.2f})")
        else:
            score += 10
            print(f"  ❌ 链接密度较低 ({link_density:.2f})")
            issues.append("链接密度低，拓扑结构可能不稳定")

        # 闭环检测评分 (30分) - 最关键指标
        loop_ratio = loop_closures / total_nodes if total_nodes > 0 else 0
        if loop_ratio > 0.15:
            score += 30
            print(f"  ✅ 闭环检测优秀 ({loop_ratio*100:.1f}%)")
        elif loop_ratio > 0.08:
            score += 25
            print(f"  ✅ 闭环检测良好 ({loop_ratio*100:.1f}%)")
        elif loop_ratio > 0.03:
            score += 20
            print(f"  ⚠️  闭环检测一般 ({loop_ratio*100:.1f}%)")
            recommendations.append("建议重走路径增加闭环检测")
        elif loop_ratio > 0.01:
            score += 10
            print(f"  ⚠️  闭环检测较少 ({loop_ratio*100:.1f}%)")
            issues.append("闭环检测不足，可能存在累积误差")
            recommendations.append("建议在同一位置多次往返以增加闭环")
        else:
            print(f"  ❌ 闭环检测极少 ({loop_ratio*100:.1f}%)")
            issues.append("几乎没有闭环检测，定位误差会累积")
            recommendations.append("强烈建议返回起点形成闭环")

        # 建图时长评分 (20分)
        if min_stamp and max_stamp:
            duration = max_stamp - min_stamp
            if duration > 600:  # 10分钟以上
                score += 20
                print(f"  ✅ 建图时长充足 ({duration/60:.1f} 分钟)")
            elif duration > 300:  # 5分钟以上
                score += 15
                print(f"  ✅ 建图时长适中 ({duration/60:.1f} 分钟)")
            elif duration > 120:  # 2分钟以上
                score += 10
                print(f"  ⚠️  建图时长较短 ({duration/60:.1f} 分钟)")
            else:
                print(f"  ❌ 建图时长太短 ({duration/60:.1f} 分钟)")
                issues.append("建图时间不足")

        print(f"\n  总评分: {score}/{max_score}")

        # 评级
        if score >= 85:
            rating = "⭐⭐⭐⭐⭐ 优秀"
            print(f"  评级: {rating}")
            print("  🎉 地图质量非常好，可以直接用于导航！")
        elif score >= 70:
            rating = "⭐⭐⭐⭐ 良好"
            print(f"  评级: {rating}")
            print("  ✅ 地图质量良好，可以用于导航")
        elif score >= 55:
            rating = "⭐⭐⭐ 一般"
            print(f"  评级: {rating}")
            print("  ⚠️  地图质量一般，建议优化后再导航")
        elif score >= 40:
            rating = "⭐⭐ 较差"
            print(f"  评级: {rating}")
            print("  ⚠️  地图质量较差，导航可能不稳定")
        else:
            rating = "⭐ 不合格"
            print(f"  评级: {rating}")
            print("  ❌ 地图质量不合格，建议重新建图")

        # 显示问题和建议
        if issues:
            print(f"\n⚠️  发现的问题:")
            for i, issue in enumerate(issues, 1):
                print(f"  {i}. {issue}")

        if recommendations:
            print(f"\n💡 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

        print(f"\n{'='*60}")

        conn.close()

        return score, rating

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return 0, "分析失败"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        # 默认使用最新的地图
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

    print(f"\n分析地图: {db_path}")
    analyze_map(db_path)