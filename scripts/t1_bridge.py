#!/usr/bin/env python3
"""
T1 Bridge — Nav2 cmd_vel → T1 SDK（纯 Python 版，不用 rclpy）

关键设计（2026-08-14 修正）:
    rclpy（CycloneDDS）与 booster SDK（FastDDS）在同一进程会 Segfault 冲突。
    因此本节点不 import rclpy，改用 subprocess 运行 `ros2 topic echo` 获取
    Nav2 的 cmd_vel，解析后通过 Python SDK 的 MoveCommand 转发给机器人。

    - 不改变机器人模式（无 ChangeMode），模式切换由 factor_control_panel.py 管理
    - 不检查 Walking 模式（leg_tau 推断不可靠，控制面板负责确保模式正确）
    - 看门狗：watchdog_timeout 秒无指令自动停车
    - dry_run：只打印 cmd_vel，不连接 SDK

用法:
    python3 scripts/t1_bridge.py --cmd-vel-topic /cmd_vel_smoothed
    python3 scripts/t1_bridge.py --dry-run --cmd-vel-topic /cmd_vel_nav
"""

import argparse
import subprocess
import threading
import time

try:
    import yaml
except ImportError:
    yaml = None

try:
    from booster_robotics_sdk_python import ChannelFactory, B1LocoClient
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

ROS_SETUP = '/opt/ros/jazzy/setup.bash'


class T1Bridge:
    """纯 Python 的 Nav2 → T1 SDK 桥接（不用 rclpy）。"""

    def __init__(self, network_interface='enx207bd2d33010',
                 cmd_vel_topic='/cmd_vel_smoothed',
                 watchdog_timeout=2.0, dry_run=False):
        self._dry_run = dry_run
        self._watchdog_timeout = watchdog_timeout
        self._cmd_vel_topic = cmd_vel_topic

        # ---- Thread safety ----
        self._lock = threading.Lock()
        self._last_cmd_time = time.time()
        self._is_moving = False

        if not dry_run:
            if not _SDK_AVAILABLE:
                raise RuntimeError('booster_robotics_sdk_python 未安装')
            # ---- SDK 连接（只连接，不切模式）----
            ChannelFactory.Instance().Init(0, network_interface)
            self._client = B1LocoClient()
            self._client.Init()
            print(f'T1 SDK connected (interface: {network_interface}).', flush=True)

        # ---- 启动 cmd_vel 读取线程 ----
        self._reader_thread = threading.Thread(target=self._read_cmd_vel, daemon=True)
        self._reader_thread.start()

        # ---- 看门狗线程 ----
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()

        mode_str = 'DRY-RUN' if dry_run else '转发中'
        print(f'T1 Bridge ready ({mode_str}). 订阅 {cmd_vel_topic}', flush=True)

    # ------------------------------------------------------------------ #
    # cmd_vel 读取（subprocess ros2 topic echo）                          #
    # ------------------------------------------------------------------ #
    def _read_cmd_vel(self):
        """用 ros2 topic echo 订阅 cmd_vel，解析 YAML 并转发。"""
        # ROS_DOMAIN_ID=42：与 Nav2 同 domain（隔离机器人 FastDDS domain 0）
        cmd = (f'source {ROS_SETUP} && '
               f'export ROS_DOMAIN_ID=42 && '
               f'ros2 topic echo {self._cmd_vel_topic} --once')
        # --once 每次只读一条，循环读取；单条读完即退出，避免长连接崩溃后无法恢复
        while True:
            try:
                proc = subprocess.Popen(
                    ['bash', '-c', cmd],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                out, _ = proc.communicate(timeout=30)
                if out.strip():
                    self._parse_and_send(out)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception as e:
                print(f'[WARN] cmd_vel 读取异常: {e}', flush=True)
                time.sleep(0.5)

    def _parse_and_send(self, text: str):
        """解析 ros2 topic echo 的 YAML 输出，提取 vx/vy/vyaw 并转发。"""
        vx = vy = vyaw = 0.0
        if yaml is not None:
            try:
                # 去掉 --- 分隔符（ros2 topic echo 用 --- 分隔多条消息）
                data = yaml.safe_load(text.replace('---', ''))
                vx = float(data['linear']['x'])
                vy = float(data['linear']['y'])
                vyaw = float(data['angular']['z'])
            except Exception:
                return
        else:
            import re
            m = re.search(r'x:\s*([-\d.eE+]+)', text)
            vx = float(m.group(1)) if m else 0.0
            m = re.search(r'y:\s*([-\d.eE+]+)', text)
            vy = float(m.group(1)) if m else 0.0
            m = re.search(r'angular:\s*\n\s*x:[^\n]*\n\s*y:[^\n]*\n\s*z:\s*([-\d.eE+]+)', text)
            vyaw = float(m.group(1)) if m else 0.0

        self._send(vx, vy, vyaw)

    # ------------------------------------------------------------------ #
    # 转发                                                                #
    # ------------------------------------------------------------------ #
    def _send(self, vx, vy, vyaw):
        if self._dry_run:
            print(f'[DRY-RUN] cmd_vel: vx={vx:+.3f} vy={vy:+.3f} vyaw={vyaw:+.3f}', flush=True)
        else:
            with self._lock:
                self._last_cmd_time = time.time()
                self._is_moving = True
            try:
                self._client.MoveCommand(vx, vy, vyaw)
            except Exception as e:
                print(f'[ERROR] MoveCommand 失败: {e}', flush=True)

    def _watchdog_loop(self):
        """看门狗：超时无指令自动停车。"""
        while True:
            time.sleep(0.5)
            with self._lock:
                if not self._is_moving:
                    continue
                elapsed = time.time() - self._last_cmd_time
            if elapsed > self._watchdog_timeout:
                if self._dry_run:
                    print(f'[DRY-RUN] watchdog: {elapsed:.1f}s 无指令，将停止', flush=True)
                else:
                    print(f'{elapsed:.1f}s 无指令，停止机器人', flush=True)
                    try:
                        self._client.MoveCommand(0.0, 0.0, 0.0)
                    except Exception as e:
                        print(f'[ERROR] 停止失败: {e}', flush=True)
                with self._lock:
                    self._is_moving = False


def main():
    parser = argparse.ArgumentParser(description='T1 Bridge (纯 Python)')
    parser.add_argument('--network-interface', default='enx207bd2d33010')
    parser.add_argument('--cmd-vel-topic', default='/cmd_vel_smoothed')
    parser.add_argument('--watchdog-timeout', type=float, default=2.0)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    T1Bridge(
        network_interface=args.network_interface,
        cmd_vel_topic=args.cmd_vel_topic,
        watchdog_timeout=args.watchdog_timeout,
        dry_run=args.dry_run,
    )
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nT1 Bridge 退出', flush=True)


if __name__ == '__main__':
    main()
