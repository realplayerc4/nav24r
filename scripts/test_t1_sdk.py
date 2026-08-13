#!/usr/bin/env python3
"""
T1 SDK 最小连通性测试 — 独立于 ROS2，只测 SDK 链路

步骤:
    1. ChannelFactory.Init(domain_id, enx0826ae3beeb8)
    2. B1LocoClient.Init()
    3. WaitForService(timeout_ms=15000)
    4. GetMode() → 打印当前机器人模式
    5. (可选) Move(0.1, 0, 0) → 慢走 0.1 m/s，2 秒后停止

用法:
    python3 scripts/test_t1_sdk.py                  # 只测连接 + GetMode
    python3 scripts/test_t1_sdk.py --move-test      # 额外测 Move
"""

import argparse
import sys
import time

try:
    from booster_robotics_sdk_python import (
        B1LocoClient,
        ChannelFactory,
        RobotMode,
    )
except ImportError:
    print("ERROR: booster_robotics_sdk_python not found.")
    print("Install: pip install booster_robotics_sdk_python")
    sys.exit(1)

ROBOT_IP = "192.168.10.102"
NET_IF = "enx0826ae3beeb8"
DOMAIN_ID = 0
SDK_TIMEOUT_MS = 15000

# SDK v1.5.6 API calling convention:
# GetMode/GetStatus/GetRobotInfo return response directly (no output param)
# ChangeMode/Move return int32_t (0 = success)


def step(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def fail(msg: str) -> None:
    print(f"  ❌ {msg}")


def test_connect(client: B1LocoClient) -> bool:
    """WaitForService — 等机器人 DDS 服务发现."""
    print(f"  等待机器人上线 (timeout={SDK_TIMEOUT_MS}ms) ...")
    if client.WaitForService(timeout_ms=SDK_TIMEOUT_MS):
        ok("WaitForService 成功 — 机器人 DDS 已发现")
        return True
    else:
        fail(f"WaitForService 超时 ({SDK_TIMEOUT_MS}ms)")
        print(f"  检查项:")
        print(f"    - 机器人是否已启动并进入 kPrepare/kWalking 模式?")
        print(f"    - {NET_IF} 是否能 ping 通 {ROBOT_IP}?")
        print(f"    - 机器人板载 DDS 配置的 domain_id 是否为 {DOMAIN_ID}?")
        return False


def test_get_mode(client: B1LocoClient) -> RobotMode | None:
    """GetMode — 查询当前机器人模式 (直接返回响应对象)."""
    try:
        resp = client.GetMode()
        mode_name = resp.mode.name if hasattr(resp.mode, "name") else str(resp.mode)
        ok(f"GetMode 成功 — 当前模式: {mode_name} ({resp.mode})")
        return resp.mode
    except Exception as e:
        fail(f"GetMode 异常: {e}")
        return None


def test_move(client: B1LocoClient, duration: float = 2.0) -> None:
    """Move — 慢走测试 (vx=0.1 m/s)."""
    print(f"  Move 测试: vx=0.1 m/s, 持续 {duration}s")
    print(f"  ⚠️  确保机器人周围无障碍物!")

    res = client.Move(0.1, 0.0, 0.0)
    if res == 0:
        ok("Move(0.1, 0, 0) 指令发送成功")
    else:
        fail(f"Move 失败 — 错误码: {res}")
        return

    print(f"  等待 {duration}s ...")
    time.sleep(duration)

    print(f"  发送停止指令 Move(0, 0, 0)")
    res = client.Move(0.0, 0.0, 0.0)
    if res == 0:
        ok("停止指令发送成功")
    else:
        fail(f"停止指令失败 — 错误码: {res}")


def main():
    parser = argparse.ArgumentParser(description="T1 SDK 连通性测试")
    parser.add_argument("--move-test", action="store_true",
                        help="额外测 Move（机器人会慢走，确保周围安全）")
    args = parser.parse_args()

    print(f"  机器人 IP:   {ROBOT_IP}")
    print(f"  网络接口:    {NET_IF}")
    print(f"  DDS domain:  {DOMAIN_ID}")
    print(f"  SDK timeout: {SDK_TIMEOUT_MS}ms")

    # ---- Step 1: ChannelFactory Init ----
    step("Step 1: ChannelFactory.Init()")
    try:
        ChannelFactory.Instance().Init(DOMAIN_ID, NET_IF)
        ok(f"ChannelFactory.Init({DOMAIN_ID}, '{NET_IF}') 成功")
    except Exception as e:
        fail(f"ChannelFactory.Init 异常: {e}")
        print(f"  可能原因: 网络接口 '{NET_IF}' 不存在或无权限")
        sys.exit(1)

    # ---- Step 2: B1LocoClient Init ----
    step("Step 2: B1LocoClient.Init()")
    try:
        client = B1LocoClient()
        client.Init()
        ok("B1LocoClient.Init() 成功")
    except Exception as e:
        fail(f"B1LocoClient.Init() 异常: {e}")
        sys.exit(1)

    # ---- Step 3: WaitForService ----
    step("Step 3: WaitForService()")
    if not test_connect(client):
        fail("SDK 连通性测试 FAILED")
        sys.exit(1)

    # ---- Step 4: GetMode ----
    step("Step 4: GetMode()")
    current_mode = test_get_mode(client)
    if current_mode is None:
        fail("GetMode 失败，后续 Move 测试跳过")
    else:
        ok("SDK 基础连通性测试 PASSED")
        print(f"\n  机器人当前模式: {current_mode}")
        if current_mode != RobotMode.kWalking:
            print(f"  (不在 kWalking 模式，Move 测试会依赖模式切换)")

    # ---- Step 5: Move test (optional) ----
    if args.move_test and current_mode is not None:
        step("Step 5: Move() — 慢走测试")
        if current_mode != RobotMode.kWalking:
            print(f"  机器人不在 kWalking 模式 ({current_mode})")
            print(f"  尝试切换到 kWalking ...")
            res = client.ChangeMode(RobotMode.kPrepare)
            if res == 0:
                ok("ChangeMode(kPrepare) 成功")
                time.sleep(1.0)
            else:
                fail(f"ChangeMode(kPrepare) 失败 — 错误码: {res}")

            res = client.ChangeMode(RobotMode.kWalking)
            if res == 0:
                ok("ChangeMode(kWalking) 成功")
                time.sleep(1.0)
            else:
                fail(f"ChangeMode(kWalking) 失败 — 错误码: {res}")
                print(f"  Move 测试终止 — 无法进入 Walking 模式")
                sys.exit(1)

        test_move(client, duration=2.0)
        ok("Move 测试完成 — 机器人应已停止")
    else:
        print(f"\n  (不加 --move-test 不测 Move，只测连通性)")

    # ---- Done ----
    print(f"\n{'='*60}")
    print(f"  测试完毕")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
