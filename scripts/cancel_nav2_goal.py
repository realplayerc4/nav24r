#!/usr/bin/env python3
"""
停止 Nav2 导航 — 通过发送"原地目标"抢占当前导航目标。

原理: 向 /navigate_to_pose 发送一个到机器人当前位置的目标，
Nav2 会抢占（取消）当前目标，并立即判定到达（已在原地），从而停止规划/下发 cmd_vel。

注: 不用 rclpy 的 cancel API（Jazzy 版本不完整/有 bug），改用抢占目标实现。

用法:
    python3 scripts/cancel_nav2_goal.py
  （需 source 过 ROS2 环境）

返回: 0 = 成功抢占（导航停止），1 = 失败
"""

import math
import os

# 隔离 domain：电脑侧 ROS2 用 42（与 Nav2 同 domain，避免机器人 FastDDS domain 0 干扰）
os.environ['ROS_DOMAIN_ID'] = '42'

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry

ODOM_TOPIC = '/factor_perception/odom'


def read_odom(node: Node, timeout: float = 3.0) -> dict:
    """一次性读取当前里程计位姿 (x, y, yaw)。"""
    result = {}

    def cb(msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        result['x'] = p.x
        result['y'] = p.y
        result['yaw'] = yaw

    sub = node.create_subscription(Odometry, ODOM_TOPIC, cb, 10)
    deadline = node.get_clock().now().nanoseconds + int(timeout * 1e9)
    while node.get_clock().now().nanoseconds < deadline and 'x' not in result:
        rclpy.spin_once(node, timeout_sec=0.2)
    node.destroy_subscription(sub)
    return result


def main():
    rclpy.init()
    node = rclpy.create_node('stop_nav2')
    try:
        pose = read_odom(node)
        if 'x' not in pose:
            print(f'未读取到里程计位置（{ODOM_TOPIC} 无数据）')
            return 1

        client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
        if not client.wait_for_server(timeout_sec=3.0):
            print('/navigate_to_pose action server 不可用')
            return 1

        # 发送"到当前位置"的目标，抢占当前导航目标
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.pose.position.x = pose['x']
        goal.pose.pose.position.y = pose['y']
        goal.pose.pose.orientation.z = math.sin(pose['yaw'] / 2.0)
        goal.pose.pose.orientation.w = math.cos(pose['yaw'] / 2.0)

        future = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, future, timeout_sec=3.0)
        if future.done() and future.result() and future.result().accepted:
            print(f'已抢占 Nav2 目标（原地 {pose["x"]:.2f},{pose["y"]:.2f}），导航已停止')
            return 0
        print('目标抢占失败')
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
