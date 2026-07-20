#!/usr/bin/env python3
"""
模拟点云发布器 - 用于仿真环境测试 Nav2 Costmap
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
import struct
import math
import time


class MockPointCloudPublisher(Node):
    def __init__(self):
        super().__init__('mock_pointcloud_publisher')
        
        # 参数
        self.declare_parameter('pointcloud_topic', '/factor_perception/cloud_obstacles')
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('frame_id', 'base_link')
        self.declare_parameter('use_sim_time', False)
        
        pointcloud_topic = str(self.get_parameter('pointcloud_topic').value)
        publish_rate = float(self.get_parameter('publish_rate').value)
        
        # 发布者
        self.pc_pub = self.create_publisher(PointCloud2, pointcloud_topic, 10)
        
        # 定时器
        timer_period = 1.0 / publish_rate
        self.timer = self.create_timer(timer_period, self.publish_pointcloud)
        
        # 模拟参数
        self.points_count = 100
        self.angle_offset = 0.0
        
        self.get_logger().info(f'模拟点云发布器已启动，话题: {pointcloud_topic}')
    
    def publish_pointcloud(self):
        now = self.get_clock().now()
        
        # 创建 PointCloud2 消息
        header = Header()
        header.stamp = now.to_msg()
        header.frame_id = str(self.get_parameter('frame_id').value)
        
        # 生成模拟点云数据（前方扇形区域）
        points = []
        angle_offset = self.angle_offset
        self.angle_offset += 0.1
        
        for i in range(self.points_count):
            angle = (i / self.points_count) * 1.5 - 0.75 + angle_offset  # 前方 0.75 弧度
            distance = 1.0 + (i % 5) * 0.3  # 1.0m ~ 2.2m
            
            x = distance * math.cos(angle)
            y = distance * math.sin(angle)
            z = 0.1  # 地面以上 0.1m
            
            points.append((x, y, z))
        
        # 序列化点云
        pointcloud = self.create_pointcloud2(header, points)
        self.pc_pub.publish(pointcloud)
    
    def create_pointcloud2(self, header, points):
        """创建 PointCloud2 消息"""
        fields = [
            PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
        ]
        
        point_step = 12
        row_step = point_step * len(points)
        data = bytearray()
        
        for x, y, z in points:
            data.extend(struct.pack('fff', x, y, z))
        
        pc2 = PointCloud2()
        pc2.header = header
        pc2.height = 1
        pc2.width = len(points)
        pc2.fields = fields
        pc2.is_bigendian = False
        pc2.point_step = point_step
        pc2.row_step = row_step
        pc2.data = bytes(data)
        pc2.is_dense = True
        
        return pc2


def main(args=None):
    import math
    rclpy.init(args=args)
    node = MockPointCloudPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
