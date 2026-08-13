# Nav2 → T1 桥接 — 当前状态记录

**日期**: 2026-07-24（设计）, 2026-08-13（Python SDK 验证完成）
**状态**: Python SDK 核心功能已全部验证通过，可正常操控机器人

---

## 网络拓扑（2026-08-13 确认）

```
nav24r 电脑 (192.168.10.103) ──LAN 直连── Robot eth0 (192.168.10.102)
                                       │
                                    FastDDS (domain 0)
                                    T1 SDK DDS + ROS2 Humble
```

- 统一走 LAN `192.168.10.x`，FastDDS whitelist 允许此网段
- WiFi (`192.168.0.x`) 不使用
- Python SDK v1.5.6 通过 LAN 直连完整验证

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

**职责**: 订阅 Nav2 的 `/cmd_vel_nav`，调用 T1 SDK `B1LocoClient.Move()` 驱动机器人。

**核心逻辑**:
```
/cmd_vel_nav (Twist) ──▶ _on_cmd_vel() ──▶ SDK.Move(vx, 0.0, vyaw)
```

**关键设计**:
- vy 强制为 0（T1 双足不宜横移，与 Nav2 vy_max=0.0 一致）
- ChannelFactory 导入做优雅降级（不同 SDK 版本可能需要）
- 零速看门狗 500ms，`_is_stopping` 标志位防止重复发停止指令
- 指令节流：≤20Hz (50ms)，速度变化 >0.05 时立即转发
- SDK 连接超时抛 `RuntimeError`，由 `main()` 的 `finally` 块优雅关闭
- 退出时切 Damping 模式

**ROS 参数**:
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `network_interface` | `enx0826ae3beeb8` | T1 SDK 网络接口 (USB LAN) |
| `watchdog_timeout` | 2.0 | 无指令超时停车时间 (s) |
| `cmd_vel_topic` | `/cmd_vel` | 订阅的话题 |

**外部依赖**: `booster_robotics_sdk_python` (pip install)

**与旧 C++ 代码对比** (`slambAK/boosterxjw/booster_nav2_controller/src/booster_nav2_example.cpp`):
| 维度 | 旧 (C++) | 新 (Python) |
|------|----------|-------------|
| 订阅 topic | `/cmd_vel` | `/cmd_vel_nav`（与 launch remap 一致） |
| vy 处理 | 透传（允许横移） | 强制为 0（Nav2 vy_max=0.0 不会输出非零 vy） |
| 看门狗超时 | 2.0 秒 | 0.5 秒 |
| 模式切换 | 同步，1s sleep | 同步，无 sleep（SDK 阻塞调用） |
| SDK 连接失败 | 无处理 | `raise RuntimeError` → `finally` 优雅关闭 |
| 退出处理 | 无（C++ spin 自然结束） | Move(0) + sleep(0.1s) + Damping |
| ChannelFactory | 直接调用 | try/except 优雅降级 |
| 指令频率 | 不限频 | ≤20Hz + 变化阈值 0.05 |

### 2. `launch/nav24r_full.launch.py` — 集成

新增两个 launch argument:
- `use_t1_bridge` (默认 `false`)
- `t1_network_interface` (默认 `eth0`)

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
| DDS 初始化 | `ChannelFactory.Instance().Init(0, 'enx0826ae3beeb8')` | ✅ |
| 客户端连接 | `B1LocoClient().Init()` | ✅ |
| 模式切换 | `client.ChangeMode(RobotMode.kPrepare/kWalking/kDamping)` | ✅ |
| 运动控制 | `client.SendApiRequest(LocoApiId.kMove, '{"vx":0.5,"vy":0,"vyaw":0}')` | ✅ |
| 运动控制 | `client.Move(vx, vy, vyaw)` | ✅ |
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
| `WaitForService` | 返回 True 但 API 502 | 只确认 DDS 发现，不保证 RPC 响应 | ✅ 保留作连接检查 |

### 推荐使用方式

```python
from booster_robotics_sdk_python import (
    B1LocoClient, ChannelFactory, RobotMode, LocoApiId,
    B1LowStateSubscriber, B1OdometerStateSubscriber
)

# 初始化
ChannelFactory.Instance().Init(0, 'enx0826ae3beeb8')
client = B1LocoClient()
client.Init()

# 模式切换
client.ChangeMode(RobotMode.kPrepare)   # 准备站立
client.ChangeMode(RobotMode.kWalking)    # 行走模式
client.ChangeMode(RobotMode.kDamping)    # 阻尼制动

# 运动 (SendApiRequest fire-and-forget, 返回 0=成功)
client.SendApiRequest(2001, '{"vx": 0.5, "vy": 0.0, "vyaw": 0.0}')   # 前进
client.SendApiRequest(2001, '{"vx": 0.0, "vy": 0.0, "vyaw": 0.0}')   # 停止

# 或直接用 Move()
client.Move(0.5, 0.0, 0.0)   # 前进
client.Move(0.0, 0.0, 0.0)   # 停止

# 状态读取 (subscriber, 不需要 RPC)
def on_low_state(msg):
    for i, m in enumerate(msg.motor_state_parallel):
        print(f'Motor {i}: q={m.q:.4f} tau={m.tau_est:.4f}')

sub = B1LowStateSubscriber(on_low_state)
sub.InitChannel()
```

### 模式推断（控制面板 / t1_bridge）

不依赖 `GetMode` RPC，通过 `B1LowStateSubscriber` 的电机数据推断：

| 模式 | 腿部扭矩 (leg_tau) | 里程计 | 电机数 |
|------|-------------------|--------|--------|
| Damping | < 1.0 Nm | 不变 | 23 |
| Prepare | 0.5~2.0 Nm | 不变 | 23 |
| Walking | 0.8~1.5 Nm + 持续变化 | 变化中 | 23 |

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
                      Nav2 栈
                           │
                      /cmd_vel_nav
                      /cmd_vel     (velocity_smoother remap)
```

### 双机模式（Nav2 电脑 + T1 电脑）
```
┌──────────────────── Nav2 电脑 ────────────────────┐
│                                                    │
│  Nav2 栈 → /cmd_vel_nav (Twist)                    │
│                   │                                 │
│                   │  ROS2 DDS 跨机器自动发现          │
└───────────────────│────────────────────────────────┘
                    │ 以太网/WiFi 同子网, ROS_DOMAIN_ID 相同
                    ▼
┌──────────────────── T1 电脑 ──────────────────────┐
│                                                    │
│  t1_bridge.py                                       │
│    └─▶ B1LocoClient.Move(vx, 0.0, vyaw)            │
│                    │                                 │
│                    ▼                                 │
│              T1 机器人 (以太网)                       │
└────────────────────────────────────────────────────┘
```

---

## 已知待确认事项

1. ~~Python SDK import 路径~~ ✅ 已确认 `booster_robotics_sdk_python==1.5.6`
2. ~~ChannelFactory 是否需要~~ ✅ 需要，`ChannelFactory.Instance().Init(0, 'enx0826ae3beeb8')`
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
