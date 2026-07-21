#!/usr/bin/env python3
"""
Odom Covariance Fix Node
订阅 /factor_perception/odom，添加协方差后重新发布到 /factor_perception/odom_fixed

RTAB-Map 要求里程计消息包含有效的协方差矩阵，
但 Factor Perception SDK 发布的 odom 可能没有填充 covariance。
此节点确保 odom 消息始终包含有效的协方差。
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import numpy as np
from rclpy.executors import ExternalShutdownException


class OdomCovarianceFix(Node):
    def __init__(self):
        super().__init__('odom_covariance_fix')
        
        # 声明参数
        self.declare_parameter('input_topic', '/factor_perception/odom')
        self.declare_parameter('output_topic', '/factor_perception/odom_fixed')
        self.declare_parameter('covariance_xx', 0.1)   # x 方向方差
        self.declare_parameter('covariance_yy', 0.1)   # y 方向方差
        self.declare_parameter('covariance_zz', 0.1)   # z 方向方差
        self.declare_parameter('covariance_rr', 0.5)   # roll 方差
        self.declare_parameter('covariance_pp', 0.5)   # pitch 方差
        self.declare_parameter('covariance_yyaw', 0.3) # yaw 方差
        
        # 获取参数
        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        self.cov_xx = self.get_parameter('covariance_xx').value
        self.cov_yy = self.get_parameter('covariance_yy').value
        self.cov_zz = self.get_parameter('covariance_zz').value
        self.cov_rr = self.get_parameter('covariance_rr').value
        self.cov_pp = self.get_parameter('covariance_pp').value
        self.cov_yyaw = self.get_parameter('covariance_yyaw').value
        
        # 订阅原 odom
        self.subscription = self.create_subscription(
            Odometry,
            input_topic,
            self.odom_callback,
            10
        )
        
        # 发布修复后的 odom
        self.publisher = self.create_publisher(
            Odometry,
            output_topic,
            10
        )
        
        self.get_logger().info(f'Odom Covariance Fix 节点已启动')
        self.get_logger().info(f'  输入: {input_topic}')
        self.get_logger().info(f'  输出: {output_topic}')
        self.get_logger().info(f'  协方差: xx={self.cov_xx}, yy={self.cov_yy}, zz={self.cov_zz}')
        self.get_logger().info(f'         rr={self.cov_rr}, pp={self.cov_pp}, yyaw={self.cov_yyaw}')
    
    def odom_callback(self, msg):
        # 复制原消息
        fixed_msg = msg
        
        # 检查 twist 的协方差是否有效
        # Odometry.twist 是 TwistWithCovariance，包含 covariance 字段
        try:
            covariance = list(fixed_msg.twist.covariance)
            covariance_valid = any(covariance)
        except (AttributeError, TypeError):
            covariance_valid = False
        
        if not covariance_valid:
            # 设置默认 twist 协方差（表示中等不确定性）
            # 6x6 协方差矩阵（行优先）
            cov = [
                self.cov_xx, 0.0, 0.0, 0.0, 0.0, 0.0,   # twist.x
                0.0, self.cov_yy, 0.0, 0.0, 0.0, 0.0,   # twist.y
                0.0, 0.0, self.cov_zz, 0.0, 0.0, 0.0,   # twist.z
                0.0, 0.0, 0.0, self.cov_rr, 0.0, 0.0,   # twist.rx
                0.0, 0.0, 0.0, 0.0, self.cov_pp, 0.0,   # twist.ry
                0.0, 0.0, 0.0, 0.0, 0.0, self.cov_yyaw  # twist.rz
            ]
            fixed_msg.twist.covariance = cov
            self.get_logger().debug('填充默认 twist 协方差')
        
        self.publisher.publish(fixed_msg)


def main(args=None):
    rclpy.init(args=args)
    node = OdomCovarianceFix()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except ExternalShutdownException:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
