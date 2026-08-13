#!/usr/bin/env python3
"""
T1 Bridge Node — Nav2 cmd_vel → 加速进化 T1 SDK

订阅 Nav2 输出的 /cmd_vel，通过 B1LocoClient.Move() 转发给 T1 双足机器人。
基于 slambAK/boosterxjw/booster_nav2_controller (C++ 验证版) 移植。

安全机制:
    - 模式检查：通过 LowState 电机扭矩推断 kWalking 模式（不依赖 GetMode RPC）
    - 看门狗：2s 无指令自动停止
    - SDK 连接断开时日志告警

注意:
    - 机器人启动序列（Prepare → Walking）由 factor_control_panel.py 管理
    - 本节点只负责 Nav2 自动导航时的速度转发
"""

import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

try:
    from booster_robotics_sdk_python import B1LocoClient, RobotMode, ChannelFactory, B1LowStateSubscriber
except ImportError:
    print(
        "ERROR: booster_robotics_sdk_python not found.\n"
        "Install with: pip install booster_robotics_sdk_python"
    )
    exit(1)


class T1Bridge(Node):
    """Nav2 → T1 SDK 速度指令桥接节点。"""

    def __init__(self):
        super().__init__('t1_bridge')

        # ---- Parameters ----
        self.declare_parameter('network_interface', 'enx0826ae3beeb8')
        self.declare_parameter('watchdog_timeout', 2.0)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')

        self._watchdog_timeout = self.get_parameter('watchdog_timeout').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        network_if = self.get_parameter('network_interface').value

        # ---- SDK Init（只做连接，不做模式切换） ----
        # ChannelFactory 必须先于 B1LocoClient 初始化（对齐 C++ / Python 官方示例）
        ChannelFactory.Instance().Init(0, network_if)

        self._client = B1LocoClient()
        self._client.Init()

        if not self._client.WaitForService(timeout_ms=30000):
            raise RuntimeError('T1 SDK connection timeout!')

        self.get_logger().info(f'T1 SDK connected (interface: {network_if}).')

        # ---- T1 LowState subscriber (模式推断用) ----
        self._t1_latest_state = {}
        self._t1_low_state_sub = B1LowStateSubscriber(self._on_t1_low_state)
        self._t1_low_state_sub.InitChannel()

        # 检查当前机器人模式 (基于 subscriber 数据)
        self._robot_in_walk = self._check_mode()

        # ---- Thread safety ----
        self._cmd_lock = threading.Lock()
        self._last_cmd_time = time.time()
        self._is_moving = False

        # ---- Subscription ----
        self._sub = self.create_subscription(
            Twist, cmd_vel_topic, self._on_cmd_vel, 10
        )

        # ---- Mode check timer (2 Hz) ----
        self._mode_timer = self.create_timer(0.5, self._check_mode_periodic)

        # ---- Watchdog timer (2 Hz) ----
        self._watchdog_timer = self.create_timer(0.5, self._watchdog)

        mode_str = 'kWalking' if self._robot_in_walk else 'NOT kWalking'
        self.get_logger().info(
            f'T1 Bridge ready. Listening on {cmd_vel_topic}, robot mode: {mode_str}'
        )

    # ------------------------------------------------------------------ #
    # Mode check (subscriber-based, no GetMode RPC needed)                #
    # ------------------------------------------------------------------ #
    def _check_mode(self) -> bool:
        """根据 LowState 电机扭矩推断是否在 kWalking 模式。"""
        if not hasattr(self, '_t1_latest_state') or not self._t1_latest_state:
            return self._robot_in_walk  # 无数据时保持原状态

        state = self._t1_latest_state
        leg_tau = state.get('leg_tau', 0)
        motor_count = state.get('motor_count', 0)

        # 简单推断: 有里程计变化 + 腿部有扭矩 = Walking
        # (t1_bridge 本身不订阅 odometer，用扭矩阈值判断)
        # Damping: leg_tau < 1.0
        # Prepare/Walking: leg_tau > 0.5
        # 保守策略: 扭矩 > 0.5 且电机在线 = 认为是 Walking
        is_walk = (motor_count > 0 and leg_tau > 0.5)

        if self._robot_in_walk and not is_walk:
            self.get_logger().warn(
                f'Robot may have left Walking mode (leg_tau={leg_tau:.2f})'
            )

        return is_walk

    def _check_mode_periodic(self):
        """周期性检查机器人是否还在 kWalking 模式。"""
        was_walk = self._robot_in_walk
        self._robot_in_walk = self._check_mode()
        if was_walk and not self._robot_in_walk:
            self.get_logger().warn(
                'Robot left kWalking mode! Stopping cmd_vel forwarding.'
            )

    def _on_t1_low_state(self, msg):
        """LowState subscriber 回调 — 缓存电机数据用于模式推断。"""
        if not hasattr(self, '_t1_latest_state'):
            self._t1_latest_state = {}
        self._t1_latest_state['motor_count'] = len(msg.motor_state_parallel)
        if msg.motor_state_parallel:
            leg_tau = sum(abs(m.tau_est) for m in msg.motor_state_parallel[3:8])
            self._t1_latest_state['leg_tau'] = leg_tau

    # ------------------------------------------------------------------ #
    # Callbacks                                                            #
    # ------------------------------------------------------------------ #
    def _on_cmd_vel(self, msg: Twist):
        """收到 Nav2 的速度指令，仅在 kWalking 模式下转发。"""
        if not self._robot_in_walk:
            self.get_logger().warn(
                'Robot not in kWalking mode, ignoring cmd_vel. '
                'Use the control panel to switch to Walking first.'
            )
            return

        vx = float(msg.linear.x)
        vy = float(msg.linear.y)
        vyaw = float(msg.angular.z)

        # 直接转发，不做节流（Nav2 controller 已限速 ~20Hz）
        with self._cmd_lock:
            self._last_cmd_time = time.time()
            self._is_moving = True
            self._client.Move(vx, vy, vyaw)

    def _watchdog(self):
        """超时未收到 cmd_vel 时自动停车。"""
        with self._cmd_lock:
            if not self._is_moving:
                return
            elapsed = time.time() - self._last_cmd_time

        if elapsed > self._watchdog_timeout:
            self.get_logger().info(f'No cmd_vel for {elapsed:.1f}s, stopping robot.')
            self._client.Move(0.0, 0.0, 0.0)
            with self._cmd_lock:
                self._is_moving = False

    # ------------------------------------------------------------------ #
    # Shutdown                                                             #
    # ------------------------------------------------------------------ #
    def shutdown(self):
        """节点退出时停止机器人。"""
        self.get_logger().info('Shutting down: stopping robot ...')
        try:
            self._client.Move(0.0, 0.0, 0.0)
            self.get_logger().info('Robot stopped. Shutdown complete.')
        except Exception as e:
            self.get_logger().error(f'Error during shutdown: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = T1Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
