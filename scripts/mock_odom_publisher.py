#!/usr/bin/env python3
"""
模拟里程计发布器 - 用于仿真环境测试 Nav2
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
import math
import time


class MockOdomPublisher(Node):
    def __init__(self):
        super().__init__('mock_odom_publisher')
        
        # 参数
        self.declare_parameter('odom_topic', '/factor_perception/odom')
        self.declare_parameter('publish_rate', 30.0)
        self.declare_parameter('use_sim_time', False)
        
        odom_topic = str(self.get_parameter('odom_topic').value)
        publish_rate = float(self.get_parameter('publish_rate').value)
        
        # 发布者
        self.odom_pub = self.create_publisher(Odometry, odom_topic, 10)
        
        # 定时器
        timer_period = 1.0 / publish_rate
        self.timer = self.create_timer(timer_period, self.publish_odom)
        
        # 模拟状态
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.vx = 0.1  # 0.1 m/s
        self.vy = 0.0
        self.vz = 0.0
        self.wz = 0.05  # 0.05 rad/s
        
        self.last_time = self.get_clock().now()
        
        self.get_logger().info(f'模拟里程计发布器已启动，话题: {odom_topic}')
    
    def publish_odom(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        
        # 更新位置
        self.x += self.vx * math.cos(self.theta) * dt
        self.y += self.vx * math.sin(self.theta) * dt
        self.theta += self.wz * dt
        
        # 创建里程计消息
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        
        # 位姿
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        
        # 四元数
        odom.pose.pose.orientation.x = 0.0
        odom.pose.pose.orientation.y = 0.0
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)
        
        # 速度
        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.linear.y = self.vy
        odom.twist.twist.linear.z = self.vz
        odom.twist.twist.angular.z = self.wz
        
        # 协方差（简化）
        pose_cov = [0.01] * 36
        pose_cov[0] = 0.01  # x
        pose_cov[7] = 0.01  # y
        pose_cov[14] = 0.01  # z
        pose_cov[21] = 0.01  # roll
        pose_cov[28] = 0.01  # pitch
        pose_cov[35] = 0.01  # yaw
        odom.pose.covariance = pose_cov
        
        twist_cov = [0.01] * 36
        odom.twist.covariance = twist_cov
        
        self.odom_pub.publish(odom)


def main(args=None):
    rclpy.init(args=args)
    node = MockOdomPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
