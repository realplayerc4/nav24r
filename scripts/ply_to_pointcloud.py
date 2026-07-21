#!/usr/bin/env python3
"""
将 RTAB-Map 导出的 PLY 点云文件发布为 ROS2 PointCloud2 话题
用于在 RViz 中查看历史点云
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
import struct
import sys
import random


class PlyToPointCloud(Node):
    def __init__(self):
        super().__init__('ply_to_pointcloud')
        
        # 声明参数
        self.declare_parameter('ply_file', '/home/yq/rtabmap_cloud.ply')
        self.declare_parameter('topic_name', '/rtabmap/historical_cloud')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('publish_rate', 0.2)
        self.declare_parameter('max_points', 100000)
        
        # 获取参数
        ply_file = self.get_parameter('ply_file').value
        topic_name = self.get_parameter('topic_name').value
        self.frame_id = self.get_parameter('frame_id').value
        publish_rate = self.get_parameter('publish_rate').value
        self.max_points = self.get_parameter('max_points').value
        
        # 读取 PLY 文件
        self.get_logger().info(f'读取 PLY 文件: {ply_file}')
        self.pointcloud_msg = self.read_ply_file(ply_file)
        
        if self.pointcloud_msg is None:
            self.get_logger().error('无法读取 PLY 文件，退出')
            sys.exit(1)
        
        # 创建发布者
        self.publisher = self.create_publisher(PointCloud2, topic_name, 10)
        
        # 创建定时器
        self.timer = self.create_timer(1.0 / publish_rate, self.timer_callback)
        
        self.get_logger().info(f'发布点云到话题: {topic_name}')
        self.get_logger().info(f'帧ID: {self.frame_id}')
        self.get_logger().info(f'点数量: {self.pointcloud_msg.width}')
        self.get_logger().info(f'发布频率: {publish_rate} Hz')
    
    def read_ply_file(self, filepath):
        """读取 PLY 文件并转换为 PointCloud2 消息"""
        try:
            with open(filepath, 'rb') as f:
                # 读取头部
                header_lines = []
                while True:
                    line = f.readline().decode('ascii').strip()
                    header_lines.append(line)
                    if line == 'end_header':
                        break
                
                # 解析头部
                num_vertices = 0
                properties = []
                in_vertex = False
                for line in header_lines:
                    if line.startswith('element vertex'):
                        in_vertex = True
                        num_vertices = int(line.split()[-1])
                    elif line.startswith('element'):
                        in_vertex = False
                    elif in_vertex and line.startswith('property'):
                        parts = line.split()
                        properties.append((parts[2], parts[1]))
                
                self.get_logger().info(f'顶点数: {num_vertices}')
                self.get_logger().info(f'属性: {[p[0] for p in properties]}')
                
                # 读取所有顶点数据
                vertex_data = f.read()
                
                # 创建 PointCloud2 消息
                msg = PointCloud2()
                msg.header = Header()
                msg.header.frame_id = self.frame_id
                msg.header.stamp = self.get_clock().now().to_msg()
                
                msg.height = 1
                msg.width = num_vertices
                msg.fields = []
                msg.point_step = 0
                msg.row_step = 0
                msg.data = b''
                msg.is_bigendian = False
                msg.is_dense = True
                
                # 构建 PointCloud2 的 fields
                # 我们需要: x, y, z, rgb
                field_offset = 0
                
                # x (float32)
                msg.fields.append(PointField(
                    name='x', offset=field_offset, datatype=PointField.FLOAT32, count=1
                ))
                field_offset += 4
                
                # y (float32)
                msg.fields.append(PointField(
                    name='y', offset=field_offset, datatype=PointField.FLOAT32, count=1
                ))
                field_offset += 4
                
                # z (float32)
                msg.fields.append(PointField(
                    name='z', offset=field_offset, datatype=PointField.FLOAT32, count=1
                ))
                field_offset += 4
                
                # rgb (uint32)
                msg.fields.append(PointField(
                    name='rgb', offset=field_offset, datatype=PointField.UINT32, count=1
                ))
                field_offset += 4
                
                msg.point_step = field_offset  # 16 bytes per point
                msg.row_step = msg.point_step * msg.width
                
                # 打包点云数据
                point_data = bytearray()
                
                offset = 0
                for i in range(num_vertices):
                    # 解析 PLY 顶点数据
                    # 格式: x(float), y(float), z(float), nx(float), ny(float), nz(float), red(uchar), green(uchar), blue(uchar), curvature(float)
                    values = struct.unpack_from('<ffffffBBBf', vertex_data, offset)
                    
                    x, y, z = values[0], values[1], values[2]
                    red, green, blue = values[6], values[7], values[8]
                    
                    # 打包为 PointCloud2 格式 (x, y, z, rgb)
                    point_data.extend(struct.pack('<fffI', x, y, z, (red << 16) | (green << 8) | blue))
                    
                    offset += 31  # PLY 顶点大小
                
                msg.data = bytes(point_data)
                
                original_count = num_vertices
                if self.max_points > 0 and num_vertices > self.max_points:
                    indices = sorted(random.sample(range(num_vertices), self.max_points))
                    sampled_data = bytearray()
                    for idx in indices:
                        start = idx * msg.point_step
                        sampled_data.extend(point_data[start:start + msg.point_step])
                    msg.data = bytes(sampled_data)
                    msg.width = self.max_points
                    self.get_logger().info(f'随机采样: {num_vertices} -> {self.max_points}')
                
                self.get_logger().info(f'成功读取 {original_count} 个点')
                return msg
                
        except Exception as e:
            self.get_logger().error(f'读取 PLY 文件失败: {e}')
            return None
    
    def timer_callback(self):
        """定时发布点云"""
        if self.pointcloud_msg is not None:
            self.pointcloud_msg.header.stamp = self.get_clock().now().to_msg()
            self.publisher.publish(self.pointcloud_msg)


def main(args=None):
    rclpy.init(args=args)
    node = PlyToPointCloud()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
