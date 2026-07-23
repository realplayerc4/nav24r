#!/usr/bin/env python3
"""
Mock 机器人节点 — 替代 Gazebo 的 DifferentialDrive 插件

订阅 cmd_vel，用差分驱动模型积分位姿，发布 odom + TF。
配合 static map + mock 点云即可完整跑通 Nav2 导航闭环。

用法:
  ros2 run nav24r mock_robot
  ros2 launch nav24r mock_nav.launch.py
"""

import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist, TransformStamped
from tf2_ros import TransformBroadcaster


class MockRobot(Node):
    """差分驱动 mock 机器人：订阅 cmd_vel → 积分 → 发布 odom + TF"""

    def __init__(self):
        super().__init__('mock_robot')

        # ---- 参数 ----
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_nav')
        self.declare_parameter('odom_topic', '/factor_perception/odom')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('publish_rate', 30.0)
        self.declare_parameter('wheel_base', 0.4)       # 轮距 0.4m
        self.declare_parameter('start_x', 0.0)
        self.declare_parameter('start_y', 0.0)
        self.declare_parameter('start_yaw', 0.0)

        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        odom_topic = self.get_parameter('odom_topic').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value
        rate = self.get_parameter('publish_rate').value

        # ---- 位姿状态 ----
        self.x = self.get_parameter('start_x').value
        self.y = self.get_parameter('start_y').value
        self.theta = self.get_parameter('start_yaw').value

        self.last_cmd = Twist()
        self.cmd_vel_received = False

        # ---- IO ----
        self.odom_pub = self.create_publisher(Odometry, odom_topic, 10)
        self.cmd_vel_sub = self.create_subscription(
            Twist, cmd_vel_topic, self.cmd_vel_cb, 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.timer = self.create_timer(1.0 / rate, self.timer_cb)
        self.last_time = self.get_clock().now()

        self.get_logger().info(
            f'MockRobot 已启动\n'
            f'  订阅: {cmd_vel_topic}\n'
            f'  发布: {odom_topic}\n'
            f'  TF: {self.odom_frame} -> {self.base_frame}\n'
            f'  频率: {rate} Hz')

    def cmd_vel_cb(self, msg):
        self.last_cmd = msg
        self.cmd_vel_received = True

    def timer_cb(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # 差分驱动运动学
        v = self.last_cmd.linear.x
        w = self.last_cmd.angular.z

        self.x += v * math.cos(self.theta) * dt
        self.y += v * math.sin(self.theta) * dt
        self.theta += w * dt

        # 归一化 yaw 到 [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # ---- Odometry ----
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame

        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)

        # 合理的小协方差（避免 EKF/Nav2 警告）
        pc = [0.0] * 36
        pc[0] = 0.01; pc[7] = 0.01; pc[14] = 0.01
        pc[21] = 0.01; pc[28] = 0.01; pc[35] = 0.02
        odom.pose.covariance = pc

        tc = [0.0] * 36
        tc[0] = 0.01; tc[7] = 0.01; tc[35] = 0.02
        odom.twist.covariance = tc

        odom.twist.twist = self.last_cmd
        self.odom_pub.publish(odom)

        # ---- TF: odom -> base_link ----
        tf = TransformStamped()
        tf.header.stamp = now.to_msg()
        tf.header.frame_id = self.odom_frame
        tf.child_frame_id = self.base_frame
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.translation.z = 0.0
        tf.transform.rotation = odom.pose.pose.orientation
        self.tf_broadcaster.sendTransform(tf)


def main(args=None):
    rclpy.init(args=args)
    node = MockRobot()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
