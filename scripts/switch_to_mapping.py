#!/usr/bin/env python3
"""切换 RTAB-Map 模式：从定位模式切换到建图模式（续建）。

用于续建地图场景：先以定位模式启动（正确显示旧地图），
然后延迟切换到建图模式（续建新数据）。

用法: python3 switch_to_mapping.py [--delay SECONDS]
"""

import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
import std_srvs.srv


def main():
    delay = 10
    if '--delay' in sys.argv:
        idx = sys.argv.index('--delay')
        if idx + 1 < len(sys.argv):
            delay = int(sys.argv[idx + 1])

    print(f"Waiting {delay} seconds before switching to mapping mode...")
    time.sleep(delay)

    rclpy.init()
    node = Node('switch_to_mapping')
    cb_group = MutuallyExclusiveCallbackGroup()
    cli = node.create_client(
        std_srvs.srv.Empty,
        '/factor_perception/rtabmap/set_mode_mapping',
        callback_group=cb_group
    )

    if not cli.wait_for_service(timeout_sec=10.0):
        print("ERROR: set_mode_mapping service not available after 10s")
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(1)

    req = std_srvs.srv.Empty.Request()
    future = cli.call_async(req)

    executor = MultiThreadedExecutor()
    executor.add_node(node)

    start = time.time()
    while not future.done() and (time.time() - start) < 30:
        executor.spin_once(timeout_sec=1.0)

    if future.done():
        print("OK: Switched to mapping mode (continue mapping)")
    else:
        print("ERROR: Switch timed out after 30s")

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
