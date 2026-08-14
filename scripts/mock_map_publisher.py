#!/usr/bin/env python3
"""
发布空白 OccupancyGrid 地图（用于 mock 环境）

在 /factor_perception/map 发布一个 20x20 米的空白地图，
供 Nav2 global_costmap static_layer 使用。
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import QoSProfile, QoSHistoryPolicy, QoSDurabilityPolicy, QoSReliabilityPolicy
import math


class MockMapPublisher(Node):
    def __init__(self):
        super().__init__('mock_map_publisher')

        self.declare_parameter('map_topic', '/factor_perception/map')
        self.declare_parameter('resolution', 0.05)
        self.declare_parameter('width', 400)     # 20m / 0.05
        self.declare_parameter('height', 400)    # 20m / 0.05
        self.declare_parameter('origin_x', -10.0)
        self.declare_parameter('origin_y', -10.0)

        map_topic = str(self.get_parameter('map_topic').value)
        # TRANSIENT_LOCAL 匹配 global_costmap static_layer 的订阅
        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            reliability=QoSReliabilityPolicy.RELIABLE,
        )
        self._pub = self.create_publisher(OccupancyGrid, map_topic, qos)

        # 延迟 0.5 秒发布，等 subscriber 就绪
        self._timer = self.create_timer(0.5, self._publish_map)

        self.get_logger().info(f'空白地图发布器启动: {map_topic}')

    def _publish_map(self):
        resolution = float(self.get_parameter('resolution').value)
        width = int(self.get_parameter('width').value)
        height = int(self.get_parameter('height').value)
        origin_x = float(self.get_parameter('origin_x').value)
        origin_y = float(self.get_parameter('origin_y').value)

        grid = OccupancyGrid()
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.header.frame_id = 'map'
        grid.info.resolution = resolution
        grid.info.width = width
        grid.info.height = height
        grid.info.origin.position.x = origin_x
        grid.info.origin.position.y = origin_y
        grid.info.origin.orientation.w = 1.0

        # -1 = 未知区域（static_layer 会保留为未知）
        # 0 = 空闲, 100 = 障碍物
        # 全部设为 -1（未知），这样 global_costmap 可以自由规划
        grid.data = [-1] * (width * height)

        self._pub.publish(grid)
        self.get_logger().info(f'已发布空白地图: {width}x{height}, {resolution}m/cell')
        # 取消定时器（只发一次）
        self._timer.cancel()


def main(args=None):
    rclpy.init(args=args)
    node = MockMapPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
