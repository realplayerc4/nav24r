# Nav2 → T1 桥接 — 当前状态记录

**日期**: 2026-07-24（设计）, 2026-08-13（Python SDK 验证完成）, 2026-08-14（面板实测通过）
**状态**: ✅ 控制面板 T1 功能已实测通过（模式切换/移动/停止），纯 Python SDK 方案定型

---

## 网络拓扑（2026-08-14 确认）

```
nav24r 电脑 (192.168.10.103) ──LAN 直连── Robot eth0 (192.168.10.102)
                                       │
                                    FastDDS (domain 0)
                                    T1 SDK DDS + ROS2 Humble
```

- 统一走 LAN `192.168.10.x`：nav24r 用 `enx207bd2d33010`（192.168.10.103/24，nmcli 静态配置）
- 机器人 `eth0` = 192.168.10.102/24
- WiFi (`192.168.0.x`) 不使用
- Python SDK v1.5.6 通过 LAN 直连完整验证；以太网链路 0 错误

## ✅ 面板实测结果（2026-08-14）

| 功能 | 状态 | 说明 |
|------|------|------|
| 模式切换 Prepare/Walking/Damping | ✅ | 用 `SendApiRequestFireAndForget`，无 502 |
| Damping 二次确认 | ✅ | 警告电机断电、机器人瘫倒 |
| WASD/QE 方向键移动 | ✅ | A/D 已修正（vy 正=左，与 SDK 文档相反） |
| 松手停止 / 停止按钮 | ✅ | 停止指令连发 10 次（fire-and-forget 防丢包） |
| Walking→Prepare | ✅ | 需先停止步态再切（面板已内置先停止逻辑） |

### 机器人信息

| 项目 | 值 |
|------|------|
| 固件 | v1.1.0.0-release (branch: release/v1.1.0-20250421) |
| SDK 包 | `booster_rpc_service` (已安装，未启动) |
| ROS2 | Humble + CycloneDDS |
| 服务端可执行文件 | `/opt/booster/BoosterRos2/install/booster_rpc_service/lib/booster_rpc_service/rpc_service_node` |
| SSH | `booster@192.168.10.102` (LAN) |

---

## 已完成的代码

### 1. `scripts/t1_bridge.py` — 桥接节点

**职责**: 订阅 Nav2 输出的 `/cmd_vel`，调用 T1 SDK `B1LocoClient.Move()` 驱动机器人。

**核心逻辑**:
```
/cmd_vel (Twist) ──▶ _on_cmd_vel() ──▶ SDK.Move(vx, vy, vyaw)
```

**关键设计**:
- vy 透传（Nav2 `vy_max=0.0`，实际恒为 0；T1 双足不宜横移）
- 模式保护：通过 `B1LowStateSubscriber` 电机扭矩推断 kWalking 模式（不依赖 GetMode RPC），非 Walking 模式忽略 cmd_vel
- 看门狗：`watchdog_timeout=2.0s` 无指令自动停车（`Move(0,0,0)`）
- 指令直接转发，不做额外节流（Nav2 controller 已限速 ~20Hz）
- SDK 连接超时抛 `RuntimeError`，由 `main()` 的 `finally` 块优雅关闭
- 退出时发送停止指令 `Move(0,0,0)`（不切换 Damping，模式切换由控制面板管理）

**ROS 参数**:
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `network_interface` | `enx207bd2d33010` | T1 SDK 网络接口 (USB LAN) |
| `watchdog_timeout` | 2.0 | 无指令超时停车时间 (s) |
| `cmd_vel_topic` | `/cmd_vel` | 订阅的话题 |

**外部依赖**: `booster_robotics_sdk_python` (pip install)

**与旧 C++ 代码对比** (`slambAK/boosterxjw/booster_nav2_controller/src/booster_nav2_example.cpp`):
| 维度 | 旧 (C++) | 新 (Python) |
|------|----------|-------------|
| 订阅 topic | `/cmd_vel` | `/cmd_vel`（与 nav24r_full.launch.py 参数一致） |
| vy 处理 | 透传（允许横移） | 透传（Nav2 vy_max=0.0，实际恒为 0） |
| 看门狗超时 | 2.0 秒 | 2.0 秒（`watchdog_timeout` 参数可调） |
| 模式检测 | 依赖 GetMode RPC | B1LowStateSubscriber 电机扭矩推断（不依赖 RPC） |
| SDK 连接失败 | 无处理 | `raise RuntimeError` → `finally` 优雅关闭 |
| 退出处理 | 无（C++ spin 自然结束） | `Move(0,0,0)`（不切 Damping） |
| ChannelFactory | 直接调用 | try/except 优雅降级 |
| 指令频率 | 不限频 | 直接转发（Nav2 controller 限速 ~20Hz） |

### 2. `launch/nav24r_full.launch.py` — 集成

新增两个 launch argument:
- `use_t1_bridge` (默认 `false`)
- `t1_network_interface` (默认 `enx207bd2d33010`，USB LAN)

T1 bridge 节点在 launch 里但默认不启动，不影响现有 Nav2 工作流。

### 3. `setup.py` — 注册入口

添加 `t1_bridge = scripts.t1_bridge:main` 到 console_scripts。

### 4. `slambAK/boosterxjw/` — 旧代码存档

- `booster_nav2_controller/` — 旧 C++ 桥接节点（已验证可行）
- `booster_robotics_sdk-main/` — T1 Python SDK 示例（含手势控制、locomotion 示例）
- `booster_ros2_example/` — ROS2 低层级示例
- `slam文档.txt` — 旧系统启动流程记录

---

## Python SDK 验证结果（2026-08-13）

### 已验证可用

| 功能 | API | 状态 |
|------|-----|------|
| DDS 初始化 | `ChannelFactory.Instance().Init(0, 'enx207bd2d33010')` | ✅ |
| 客户端连接 | `B1LocoClient().Init()` | ✅ |
| 模式切换 | `SendApiRequestFireAndForget(LocoApiId.kChangeMode, '{"mode":N}')` | ✅ 返回 0，不会 502 |
| 运动控制 | `client.MoveCommand(vx, vy, vyaw)` | ✅ fire-and-forget，无需 rpc_service_node |
| 站起/躺下 | `client.GetUp()` / `client.LieDown()` | ✅ |
| 状态订阅 | `B1LowStateSubscriber` — 23电机 + IMU (~500Hz) | ✅ |
| 里程计订阅 | `B1OdometerStateSubscriber` (~600Hz) | ✅ |
| 手部控制 | `client.ControlDexterousHand(...)` | ✅ (SDK 有 API) |

### 已知限制

| 功能 | 现象 | 原因 | 解决方案 |
|------|------|------|----------|
| `GetMode()` | 502 错误 | RPC 响应通道需 `rpc_service_node` | ✅ 已绕过，改用 subscriber 推断 |
| `GetStatus()` | 502 错误 | 同上 | ✅ 已绕过，LowState subscriber |
| `SendApiRequestWithResponse` | 502 错误 | 同上 | ✅ 不需要，fire-and-forget 够用 |
| `Move()` | 502 错误 | 同步请求，需响应通道 | ✅ 改用 `MoveCommand()`（fire-and-forget） |
| `ChangeMode()` / `SendApiRequest()` | 502 错误 | 同步请求，需响应通道（机器人行走/忙碌时更易触发） | ✅ 改用 `SendApiRequestFireAndForget(kChangeMode, '{"mode":N}')` |
| `WaitForService` | 返回 True 但 API 502 | 只确认 DDS 发现，不保证 RPC 响应 | ✅ 保留作连接检查 |

### 推荐使用方式

```python
from booster_robotics_sdk_python import (
    B1LocoClient, ChannelFactory, RobotMode, LocoApiId,
    B1LowStateSubscriber, B1OdometerStateSubscriber
)

# 初始化
ChannelFactory.Instance().Init(0, 'enx207bd2d33010')
client = B1LocoClient()
client.Init()

# 模式切换 — 用 SendApiRequestFireAndForget（真 fire-and-forget，返回 0，不会 502）
# ⚠️ 不要用 ChangeMode()/SendApiRequest()：同步请求，无 rpc_service_node 时会抛 502
#    （机器人忙碌/行走时更易触发；实测 SendApiRequest(kChangeMode) 稳定返回 502）
# 模式枚举: kDamping=0, kPrepare=1, kWalking=2
client.SendApiRequestFireAndForget(LocoApiId.kChangeMode, '{"mode": 1}')   # Prepare
client.SendApiRequestFireAndForget(LocoApiId.kChangeMode, '{"mode": 2}')   # Walking
client.SendApiRequestFireAndForget(LocoApiId.kChangeMode, '{"mode": 0}')   # Damping

# 运动 — 用 MoveCommand（fire-and-forget，返回 None，无需 rpc_service_node）
# ⚠️ 不要用 Move()：同步请求，无 rpc_service_node 时会抛 RuntimeError 502
client.MoveCommand(0.5, 0.0, 0.0)   # 前进
client.MoveCommand(0.0, 0.0, 0.0)   # 停止（fire-and-forget 可能丢包，建议连发多次）

# 状态读取 (subscriber, 不需要 RPC)
def on_low_state(msg):
    for i, m in enumerate(msg.motor_state_parallel):
        print(f'Motor {i}: q={m.q:.4f} tau={m.tau_est:.4f}')

sub = B1LowStateSubscriber(on_low_state)
sub.InitChannel()
```

### 模式控制（控制面板 / t1_bridge）

**控制面板（2026-08-14 起）— 模式是"开关"**：由用户点击 Prepare/Walking/Damping 按钮决定，**不做自动推断**。
> 放弃扭矩推断的原因：实测 leg_tau 在机器人站立（Prepare）时波动极大（min=0.06 ~ max=2.05 Nm，avg≈0.69，
> 约 26% 采样 < 0.5 阈值），瞬时值会在 Prepare/Damping 之间来回穿越，导致面板模式不停跳变。
> 结论：电机扭矩无法可靠区分 Prepare/Damping，模式以用户按键为准。

**t1_bridge**：仍用 `B1LowStateSubscriber` 的 leg_tau 粗略判断机器人是否在 kWalking（仅作 cmd_vel 转发开关）。
> ⚠️ 因 leg_tau 不可靠，该判断在 Nav2→T1 集成时需重新评估（可能误判"非 Walking"而拒绝转发）。

### 坐标系

- **vx 正**: 机器人前方
- **vx 负**: 机器人后方
- **vy 正**: 机器人右侧
- **vy 负**: 机器人左侧
- **vyaw 正**: 左转
- **vyaw 负**: 右转

---

## 架构图

### 单机模式（当前 nav24r，不受影响）
```
Factor Perception ──▶ RTAB-Map ──▶ /factor_perception/odom
                           │
                      Nav2 栈 (MPPI DiffDrive)
                           │
                      /cmd_vel
                           │
                      velocity_smoother   (人形缓加速/减速)
                           │
                      /cmd_vel_smoothed
                           │
                      t1_bridge → MoveCommand
```

### 双机模式（Nav2 电脑 + T1 电脑）
```
┌──────────────────── Nav2 电脑 ────────────────────┐
│                                                    │
│  Nav2 栈 → /cmd_vel → velocity_smoother             │
│         → /cmd_vel_smoothed (Twist)                 │
│                   │                                 │
│                   │  ROS2 DDS 跨机器自动发现          │
└───────────────────│────────────────────────────────┘
                    │ 以太网/WiFi 同子网, ROS_DOMAIN_ID 相同
                    ▼
┌──────────────────── T1 电脑 ──────────────────────┐
│                                                    │
│  t1_bridge.py                                       │
│    └─▶ B1LocoClient.Move(vx, vy, vyaw)            │
│                    │                                 │
│                    ▼                                 │
│              T1 机器人 (以太网)                       │
└────────────────────────────────────────────────────┘
```

---

## 已知待确认事项

1. ~~Python SDK import 路径~~ ✅ 已确认 `booster_robotics_sdk_python==1.5.6`
2. ~~ChannelFactory 是否需要~~ ✅ 需要，`ChannelFactory.Instance().Init(0, 'enx207bd2d33010')`
3. ~~两台电脑的网络互通方式~~ ✅ LAN 直连 `192.168.10.103/24` ↔ `192.168.10.102/24`
4. ~~T1 电脑上的 ROS2 安装方式~~ ✅ Humble + `booster_ros2_interface` 已安装

---

## 下一步

### 1. 启动 rpc_service_node（可选，补全 RPC 查询）

在机器人上执行以启用 `GetMode` / `GetStatus` 等查询 API：

```bash
ssh booster@192.168.10.102
source /opt/ros/humble/setup.bash
source /opt/booster/BoosterRos2/install/setup.bash
ros2 run booster_rpc_service rpc_service_node --ros-args --log-level info
```

### 2. 完整导航集成（t1_bridge.py + Nav2）

```bash
ros2 launch nav24r nav24r_full.launch.py localization:=true use_t1_bridge:=true
```

### 3. 控制面板 T1 功能

已集成方向键控制（WASD）和模式切换按钮，可直接通过 GUI 操控机器人。
