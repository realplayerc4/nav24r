#!/usr/bin/env python3
"""
Nav2 输出观察器 — 监听 /cmd_vel_smoothed（velocity_smoother 平滑后）+ TF，不发送目标

使用方式:
    1. 确保 Nav2 已启动（定位模式）
    2. 在 RViz 中点击 "Nav2 Goal" 发送目标
    3. 运行本脚本观察输出

    python3 scripts/test_nav2_goal.py

    也可以指定目标点用于标记（仅显示，不发送）:
    python3 scripts/test_nav2_goal.py --x 2 --y 0

    按 Ctrl+C 停止并打印摘要
"""

import os
# 隔离 domain：电脑侧 ROS2 用 42（与 Nav2 同 domain，避免机器人 FastDDS domain 0 干扰）
os.environ['ROS_DOMAIN_ID'] = '42'

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped, Point, Quaternion
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener
import argparse
import time
import math
import sys


class VelocityRecorder:
    """记录 /cmd_vel_nav 的速度指令历史。"""

    def __init__(self):
        self.vx_history = []
        self.vyaw_history = []
        self.timestamps = []
        self._lock = __import__('threading').Lock()

    def record(self, vx: float, vyaw: float):
        with self._lock:
            self.vx_history.append(vx)
            self.vyaw_history.append(vyaw)
            self.timestamps.append(time.time())

    def summary(self) -> dict:
        with self._lock:
            if not self.vx_history:
                return {}
            return {
                'count': len(self.vx_history),
                'duration': self.timestamps[-1] - self.timestamps[0] if len(self.timestamps) > 1 else 0,
                'vx_max': max(self.vx_history, key=abs),
                'vx_min': min(self.vx_history),
                'vx_avg': sum(self.vx_history) / len(self.vx_history),
                'vyaw_max': max(self.vyaw_history, key=abs),
                'vyaw_min': min(self.vyaw_history),
                'vyaw_avg': sum(self.vyaw_history) / len(self.vyaw_history),
            }


class Nav2GoalTester(Node):
    def __init__(self, goal_x: float, goal_y: float, goal_yaw: float,
                 cmd_vel_topic: str = '/cmd_vel_smoothed'):
        super().__init__('nav2_goal_tester')

        self._goal_x = goal_x
        self._goal_y = goal_y
        self._goal_yaw = goal_yaw
        self._cmd_vel_topic = cmd_vel_topic
        self._recorder = VelocityRecorder()

        # TF 监听
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        # /cmd_vel_smoothed 订阅（velocity_smoother 平滑后的输出，真正驱动机器人的指令）
        # 注: 默认观察平滑后话题；若未启用 smoother（如 mock_nav remap 到 /cmd_vel_nav）可用 --cmd-vel-topic 指定
        self._cmd_vel_sub = self.create_subscription(
            Twist, self._cmd_vel_topic, self._on_cmd_vel, 10
        )

        # /odom 订阅（用于对比 TF 和里程计）
        self._odom_sub = self.create_subscription(
            Odometry, '/factor_perception/odom', self._on_odom, 10
        )

        # 起始位姿
        self._start_pose = None
        self._latest_pose = None

        # 状态
        self._cmd_vel_received = False
        self._odom_received = False

        # 状态监控定时器（2Hz）
        self._status_timer = self.create_timer(0.5, self._status_report)

        self.get_logger().info('Nav2 输出观察器启动')
        self.get_logger().info('请在 RViz 中点击 "Nav2 Goal" 发送目标点')
        if goal_x != 0 or goal_y != 0:
            self.get_logger().info(f'参考目标: ({goal_x:.2f}, {goal_y:.2f})')

    # ------------------------------------------------------------------ #
    # 回调
    # ------------------------------------------------------------------ #
    def _on_cmd_vel(self, msg: Twist):
        """记录 Nav2 输出的速度指令。"""
        if not self._cmd_vel_received:
            self.get_logger().info(f'收到 /cmd_vel_nav! vx={msg.linear.x:.3f} vyaw={msg.angular.z:.3f}')
            self._cmd_vel_received = True
        self._recorder.record(msg.linear.x, msg.angular.z)

    def _on_odom(self, msg: Odometry):
        """记录里程计位姿。"""
        if not self._odom_received:
            self._odom_received = True
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )
        self._latest_pose = (p.x, p.y, yaw)

    # ------------------------------------------------------------------ #
    # 状态报告
    # ------------------------------------------------------------------ #
    def _status_report(self):
        """定期打印状态。"""
        # 尝试获取 TF 位姿
        try:
            trans = self._tf_buffer.lookup_transform(
                'map', 'base_link', rclpy.time.Time()
            )
            p = trans.transform.translation
            q = trans.transform.rotation
            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            )
            self._start_pose = (p.x, p.y, yaw)
        except Exception:
            pass

        # 打印状态
        s = self._recorder.summary()
        if s and s['count'] > 0:
            self.get_logger().info(
                f'[数据] vx={s["vx_avg"]:.3f} vyaw={s["vyaw_avg"]:.3f} '
                f'| vx_range=[{s["vx_min"]:.3f},{s["vx_max"]:.3f}] '
                f'| 共 {s["count"]} 条指令'
            )

    # ------------------------------------------------------------------ #
    # 摘要
    # ------------------------------------------------------------------ #
    def _print_summary(self):
        """打印最终摘要。"""
        s = self._recorder.summary()

        print("\n" + "=" * 60)
        print("  Nav2 输出观察摘要")
        print("=" * 60)

        # 位姿信息
        if self._start_pose:
            sx, sy, syaw = self._start_pose
            print(f"  起点 (TF): ({sx:.2f}, {sy:.2f}), yaw={math.degrees(syaw):.1f}°")
        else:
            print(f"  起点: (TF 未获取到)")

        if self._latest_pose:
            lx, ly, lyaw = self._latest_pose
            print(f"  当前位姿 (odom): ({lx:.2f}, {ly:.2f}), yaw={math.degrees(lyaw):.1f}°")

        # 目标
        print(f"  参考目标: ({self._goal_x:.2f}, {self._goal_y:.2f})")

        # 速度统计
        if s and s['count'] > 0:
            print(f"\n  --- /cmd_vel_nav 统计 ---")
            print(f"  指令数量: {s['count']}")
            print(f"  持续时间: {s['duration']:.1f}s")
            print(f"  vx: [{s['vx_min']:.3f}, {s['vx_max']:.3f}], avg={s['vx_avg']:.3f}")
            print(f"  vyaw: [{s['vyaw_min']:.3f}, {s['vyaw_max']:.3f}], avg={s['vyaw_avg']:.3f}")

            # 如果目标不是正前方，检查是否有转向
            if self._start_pose:
                sx, sy, _ = self._start_pose
                dx = self._goal_x - sx
                dy = self._goal_y - sy
                angle_to_goal = math.atan2(dy, dx)

                if abs(angle_to_goal) > 0.3:
                    if abs(s['vyaw_avg']) < 0.05:
                        print(f"\n  ⚠️  目标方向 {math.degrees(angle_to_goal):.0f}° 但平均 vyaw 接近 0")
                    else:
                        print(f"\n  ✅ 目标方向 {math.degrees(angle_to_goal):.0f}°，vyaw_avg={s['vyaw_avg']:.3f}（有转向）")
                else:
                    print(f"\n  ✅ 目标在正前方，vx_avg={s['vx_avg']:.3f}")

            # 速度范围检查
            issues = []
            if abs(s['vx_max']) > 0.35:
                issues.append(f"vx_max={s['vx_max']:.3f} 超限")
            if abs(s['vyaw_max']) > 0.6:
                issues.append(f"vyaw_max={s['vyaw_max']:.3f} 超限")
            zero_ratio = sum(1 for v in self._recorder.vx_history if abs(v) < 0.001) / len(self._recorder.vx_history)
            if zero_ratio > 0.5:
                issues.append(f"{zero_ratio:.0%} 时间速度为零")

            if issues:
                print(f"  ⚠️  问题: {', '.join(issues)}")
            else:
                print(f"  ✅ 速度输出正常")
        else:
            print(f"\n  ⚠️  未收到任何 /cmd_vel_nav 消息")
            print(f"  请确认:")
            print(f"    1. RViz 中是否发送了 Nav2 Goal")
            print(f"    2. Nav2 是否接受了目标（看 Nav2 日志）")
            print(f"    3. TF 是否正常（robot_state_publisher 在运行）")

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Nav2 输出观察器（监听模式）')
    parser.add_argument('--x', type=float, default=0.0, help='参考目标 X (m)，仅显示')
    parser.add_argument('--y', type=float, default=0.0, help='参考目标 Y (m)，仅显示')
    parser.add_argument('--yaw', type=float, default=0.0, help='参考目标 yaw (rad)')
    parser.add_argument('--cmd-vel-topic', default='/cmd_vel_smoothed',
                        help='观察的速度话题（默认 /cmd_vel_smoothed；mock_nav 用 /cmd_vel_nav）')
    args = parser.parse_args()

    rclpy.init(args=None)
    node = Nav2GoalTester(args.x, args.y, args.yaw, args.cmd_vel_topic)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("\n\n用户中断，打印摘要...")
        node._print_summary()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
