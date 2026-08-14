#!/usr/bin/env python3
"""
Mock 轨迹发布器 — 测试 t1_bridge → T1 SDK 链路

发布预定义的轨迹序列到 /cmd_vel_nav，验证 t1_bridge 是否正确转发
到 SDK，以及 SDK 是否能稳定执行。

使用方法:
    # 终端 1: 启动 t1_bridge
    ros2 run nav24r t1_bridge

    # 终端 2: 发布 mock 轨迹
    python3 scripts/mock_trajectory_publisher.py

    # 观察 t1_bridge 日志确认转发
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time


class TrajectoryPoint:
    """一条轨迹点：线速度 + 角速度 + 持续时间。"""

    def __init__(self, vx: float, vyaw: float, duration: float):
        self.vx = vx          # 前进速度 (m/s)
        self.vyaw = vyaw      # 转向速度 (rad/s)
        self.duration = duration  # 持续时间 (s)


# 预定义测试轨迹：模拟人形机器人典型行走模式
TEST_TRAJECTORY = [
    # 阶段1: 静止站立 → 确认看门狗不误触发
    TrajectoryPoint(0.0, 0.0, 1.0),

    # 阶段2: 慢速直线行走 (vx=0.15, 5秒 ≈ 0.75m)
    TrajectoryPoint(0.15, 0.0, 5.0),

    # 阶段3: 左转 (vx=0.05, vyaw=0.3, 3秒)
    TrajectoryPoint(0.05, 0.3, 3.0),

    # 阶段4: 右转
    TrajectoryPoint(0.05, -0.3, 3.0),

    # 阶段5: 加速前进 (vx=0.3, 4秒)
    TrajectoryPoint(0.3, 0.0, 4.0),

    # 阶段6: 减速停止 (vx=0.1, 2秒)
    TrajectoryPoint(0.1, 0.0, 2.0),

    # 阶段7: 急停 → 验证看门狗 + 停止指令
    TrajectoryPoint(0.0, 0.0, 2.0),

    # 阶段8: 后退
    TrajectoryPoint(-0.1, 0.0, 3.0),

    # 阶段9: 原地旋转
    TrajectoryPoint(0.0, 0.5, 2.0),

    # 阶段10: 最终停止
    TrajectoryPoint(0.0, 0.0, 2.0),
]


class MockTrajectoryPublisher(Node):
    def __init__(self):
        super().__init__('mock_trajectory_publisher')

        # 参数
        self.declare_parameter('cmd_vel_topic', '/cmd_vel_nav')
        self.declare_parameter('publish_rate', 50.0)      # 50Hz，高于 t1_bridge 节流阈值
        self.declare_parameter('trajectory', 'default')   # 预置轨迹名

        self._topic = str(self.get_parameter('cmd_vel_topic').value)
        self._rate = float(self.get_parameter('publish_rate').value)
        self._trajectory_name = str(self.get_parameter('trajectory').value)

        # 发布者
        self._pub = self.create_publisher(Twist, self._topic, 10)

        # 轨迹
        self._trajectory = TEST_TRAJECTORY
        self._current_idx = 0
        self._segment_start = None

        # 计时
        self._timer = self.create_timer(1.0 / self._rate, self._on_timer)
        self._start_time = None

        self.get_logger().info(
            f'Mock 轨迹发布器启动: topic={self._topic}, rate={self._rate}Hz'
        )
        self.get_logger().info(
            f'轨迹 "{self._trajectory_name}" 共 {len(self._trajectory)} 个阶段'
        )

    def _on_timer(self):
        now = self.get_clock().now()

        if self._start_time is None:
            self._start_time = now
            self._segment_start = now
            self._publish_current()
            return

        # 当前轨迹点
        point = self._trajectory[self._current_idx]
        elapsed = (now - self._segment_start).nanoseconds / 1e9

        if elapsed >= point.duration:
            # 进入下一段
            self._current_idx += 1
            if self._current_idx >= len(self._trajectory):
                self.get_logger().info('轨迹执行完毕，停止机器人。')
                self._publish_stop()
                self._timer.cancel()
                # 等一会让 stop 消息发出后退出
                self.create_timer(1.0, self._shutdown_self, oneshot=True)
                return

            self._segment_start = now
            new_point = self._trajectory[self._current_idx]
            self.get_logger().info(
                f'阶段 {self._current_idx + 1}/{len(self._trajectory)}: '
                f'vx={new_point.vx:.2f} vyaw={new_point.vyaw:.2f} '
                f'持续 {new_point.duration:.1f}s'
            )
            self._publish_current()

    def _publish_current(self):
        point = self._trajectory[self._current_idx]
        msg = Twist()
        msg.linear.x = point.vx
        msg.linear.y = 0.0   # T1 双足不横移
        msg.angular.z = point.vyaw
        self._pub.publish(msg)

    def _publish_stop(self):
        msg = Twist()
        msg.linear.x = 0.0
        msg.linear.y = 0.0
        msg.angular.z = 0.0
        self._pub.publish(msg)

    def _shutdown_self(self):
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = MockTrajectoryPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('用户中断，发送停止指令...')
        stop_msg = Twist()
        node._pub.publish(stop_msg)
    finally:
        node.destroy_node()


if __name__ == '__main__':
    main()
