#!/usr/bin/env python3
"""
生成 Nav2 Mock 导航测试用地图

生成 10x10m 室内环境（PGM + YAML），包含外墙和内部障碍物。
原点在地图中心，方便 RViz 中设置目标点。

用法:
  python3 scripts/generate_test_map.py [输出目录]
  # 默认: /home/yq/rtabmap_maps/
"""

import os
import sys
import yaml
import numpy as np
from PIL import Image


def generate(output_dir: str = "/home/yq/rtabmap_maps"):
    os.makedirs(output_dir, exist_ok=True)

    res = 0.05
    W_m, H_m = 10.0, 10.0
    W = int(W_m / res)   # 200
    H = int(H_m / res)   # 200
    grid = np.zeros((H, W), dtype=np.int8)

    def wall_h(y_m, thick_m=0.2):
        row = int(y_m / res)
        t = int(thick_m / res)
        grid[max(0, row):min(H, row + t), :] = 100

    def wall_v(x_m, thick_m=0.2):
        col = int(x_m / res)
        t = int(thick_m / res)
        grid[:, max(0, col):min(W, col + t)] = 100

    def box(cx, cy, sx, sy):
        x1 = int((cx - sx / 2) / res)
        x2 = int((cx + sx / 2) / res)
        y1 = int((cy - sy / 2) / res)
        y2 = int((cy + sy / 2) / res)
        grid[max(0, y1):min(H, y2), max(0, x1):min(W, x2)] = 100

    def circle(cx, cy, r):
        cx_px, cy_px = int(cx / res), int(cy / res)
        r_px = int(r / res)
        for i in range(max(0, cy_px - r_px), min(H, cy_px + r_px + 1)):
            for j in range(max(0, cx_px - r_px), min(W, cx_px + r_px + 1)):
                if (i - cy_px) ** 2 + (j - cx_px) ** 2 <= r_px ** 2:
                    grid[i, j] = 100

    # 外墙 (20cm 厚)
    wall_h(0.0); wall_h(10.0); wall_v(0.0); wall_v(10.0)

    # 内部障碍物
    circle(5.0, 5.0, 0.35)       # 中央柱子
    box(2.0, 2.0, 0.8, 0.25)     # 左上障碍
    box(7.5, 7.5, 0.8, 0.25)     # 右下障碍
    box(1.5, 7.0, 0.25, 1.0)     # 左侧竖墙
    box(8.0, 3.0, 0.25, 1.0)     # 右侧竖墙

    # 保存 PGM
    pgm = np.zeros_like(grid, dtype=np.uint8)
    pgm[grid == 0] = 254
    pgm[grid == 100] = 0

    pgm_path = os.path.join(output_dir, "test_map.pgm")
    Image.fromarray(pgm, mode='L').save(pgm_path)

    # 保存 YAML
    yaml_path = os.path.join(output_dir, "test_map.yaml")
    with open(yaml_path, 'w') as f:
        yaml.dump({
            'image': 'test_map.pgm',
            'resolution': res,
            'origin': [-5.0, -5.0, 0.0],
            'negate': 0,
            'occupied_thresh': 0.65,
            'free_thresh': 0.196,
        }, f, default_flow_style=False)

    print(f"测试地图已生成:")
    print(f"  Dir: {output_dir}")
    print(f"  PGM: test_map.pgm ({W}x{H} @ {res}m)")
    print(f"  YAML: test_map.yaml")
    print(f"  原点: (-5, -5), 中心 (0,0)")
    print(f"\n启动 mock 导航:")
    print(f"  python3 scripts/generate_test_map.py")
    print(f"  ros2 launch nav24r mock_nav.launch.py")


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else "/home/yq/rtabmap_maps"
    generate(out)
