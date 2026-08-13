# Booster T1 Python SDK 文档（从源码提取）

> 来源：`slambAK/boosterxjw/booster_robotics_sdk_release/` 头文件 + Python binding
> 提取时间：2026-08-12

---

## 1. SDK 架构

### 通信模型

```
┌──────────────┐     DDS (fastDDS)      ┌──────────────┐
│   工控机      │ ◄─────────────────────► │   T1 机器人    │
│  (本程序)     │   RPC over DDS          │  (onboard)    │
│              │                         │              │
│ B1LocoClient │ ──SendApiRequest()──►  │ RPC Server   │
│ ChannelFactory│ ──DDS Publisher/       │              │
│              │    Subscriber           │              │
└──────────────┘                         └──────────────┘
```

- **DDS domain**: `ChannelFactory.Init(domain_id, network_interface)`
- **RPC 请求**: `B1LocoClient.SendApiRequest(api_id, json_param)` → 返回 `int32_t` (0=成功)
- **RPC 响应**: `SendApiRequestWithResponse(api_id, param, response)` → 带返回数据
- **Fire-and-forget**: `SendApiRequestFireAndForget(api_id, param)` → 不等待响应

### 关键 Topic（低层 DDS 通信）

| Topic | 方向 | 说明 |
|-------|------|------|
| `rt/joint_ctrl` | PC→机器人 | 关节控制指令 |
| `rt/low_state` | 机器人→PC | 低层状态（IMU、电机） |
| `rt/fall_down` | 机器人→PC | 跌倒事件 |
| `rt/odometer_state` | 机器人→PC | 里程计状态 |
| `rt/booster_hand_data` | 机器人→PC | 手部数据 |
| `rt/booster_hand_touch_data` | 机器人→PC | 手部触觉 |
| `rt/tf` | 机器人→PC | TF 变换 |
| `rt/robot_states` | 机器人→PC | 机器人状态 |

---

## 2. Python API 总览

### 2.1 ChannelFactory

```python
from booster_robotics_sdk_python import ChannelFactory

ChannelFactory.Instance().Init(domain_id, network_interface="")
# domain_id: DDS 域 ID
# network_interface: 网络接口名，如 'eth0'
```

### 2.2 B1LocoClient

```python
from booster_robotics_sdk_python import B1LocoClient, RobotMode

client = B1LocoClient()
client.Init()                          # 初始化 RPC 客户端
client.WaitForService(timeout_ms=5000)  # 等待机器人 DDS 服务发现
```

#### 运动控制

| 方法 | 签名 | 返回值 | 说明 |
|------|------|--------|------|
| `Move` | `Move(vx, vy, vyaw)` | `int32_t` | vx/vy 单位 m/s, vyaw 单位 rad/s |
| `MoveCommand` | `MoveCommand(vx, vy, vyaw)` | `int32_t` | Fire-and-forget 版本 |

#### 模式控制

| 方法 | 签名 | 返回值 | 说明 |
|------|------|--------|------|
| `ChangeMode` | `ChangeMode(mode: RobotMode)` | `int32_t` | 切换机器人模式 |
| `GetMode` | `GetMode(response: GetModeResponse)` | `int32_t` | 查询当前模式 |
| `GetStatus` | `GetStatus(response: GetStatusResponse)` | `int32_t` | 查询完整状态 |

#### 头部控制

| 方法 | 签名 | 返回值 |
|------|------|--------|
| `RotateHead` | `RotateHead(pitch, yaw)` | `int32_t` |
| `RotateHeadWithDirection` | `RotateHeadWithDirection(pitch_dir, yaw_dir)` | `int32_t` |

#### 手部控制

| 方法 | 签名 | 返回值 |
|------|------|--------|
| `WaveHand` | `WaveHand(action: HandAction)` | `int32_t` |
| `Handshake` | `Handshake(action: HandAction)` | `int32_t` |
| `MoveHandEndEffector` | `MoveHandEndEffector(posture, time_ms, hand_index)` | `int32_t` (deprecated) |
| `MoveHandEndEffectorV2` | `MoveHandEndEffectorV2(posture, time_ms, hand_index)` | `int32_t` |
| `ControlGripper` | `ControlGripper(motion_param, mode, hand_index)` | `int32_t` |
| `ControlDexterousHand` | `ControlDexterousHand(finger_params, hand_index, hand_type)` | `int32_t` |

#### 其他

| 方法 | 说明 |
|------|------|
| `GetUp()` | 站起 |
| `LieDown()` | 躺下 |
| `Shoot()` | 踢球 |
| `GetFrameTransform(src, dst, transform)` | 获取坐标系变换 |
| `SwitchHandEndEffectorControlMode(switch_on)` | 切换手部控制模式 |
| `ZeroTorqueDrag(active)` | 零力矩拖拽 |
| `RecordTrajectory(active)` | 记录轨迹 |
| `ReplayTrajectory(path)` | 回放轨迹 |
| `ResetOdometry()` | 重置里程计 |
| `PlaySound(path)` | 播放音频 |
| `Dance(dance_id)` | 跳舞 |

### 2.3 枚举类型

#### RobotMode（机器人模式）

```python
class RobotMode:
    kUnknown = -1    # 未知/错误
    kDamping = 0     # 阻尼模式（所有电机阻尼，机器人会摔倒）
    kPrepare = 1     # 准备模式（站立，可切换到 Walking）
    kWalking = 2     # 行走模式（唯一能 Move() 的模式）
    kCustom = 3      # 自定义模式
    kSoccer = 4      # 足球模式
```

#### HandAction

```python
class HandAction:
    kHandOpen = 0
    kHandClose = 1
```

#### HandIndex

```python
class HandIndex:
    kLeftHand = 0
    kRightHand = 1
```

#### GripperControlMode

```python
class GripperControlMode:
    kPosition = 0   # 位置模式（到达目标位置或力阈值时停止）
    kForce = 1      # 力模式（持续以指定力移动）
```

#### Frame（坐标系）

```python
class Frame:
    kUnknown = -1
    kBody = 0       # 躯干坐标系
    kHead = 1
    kLeftHand = 2
    kRightHand = 3
    kLeftFoot = 4
    kRightFoot = 5
```

#### DanceId / WholeBodyDanceId

```python
class DanceId:
    kNewYear = 0, kNezha = 1, kTowardsFuture = 2,
    kDabbingGesture = 3, kUltramanGesture = 4, kRespectGesture = 5,
    kCheeringGesture = 6, kLuckyCatGesture = 7, kStop = 1000

class WholeBodyDanceId:
    kArbicDance = 0, kMichaelDance1 = 1, kMichaelDance2 = 2,
    kMichaelDance3 = 3, kBoxingStyleKick = 5, kRoundhouseKick = 6,
    kShanHeGuRenDance = 7, kGaiGeChunFengDance = 8, kMichaelDance1And2 = 9
```

### 2.4 数据类型

#### Position / Orientation / Posture / Transform

```python
from booster_robotics_sdk_python import Position, Orientation, Posture, Transform, Quaternion

pos = Position(x, y, z)
ori = Orientation(roll, pitch, yaw)
posture = Posture(position, orientation)
quat = Quaternion(x, y, z, w)
transform = Transform(position, orientation)
```

#### GripperMotionParameter

```python
from booster_robotics_sdk_python import GripperMotionParameter

# 位置: 0~1000 (对应 0~77mm)
# 力: 0~1000 (对应 0~2kg)
# 速度: 0~1000
param = GripperMotionParameter(position=500, force=100, speed=100)
```

#### DexterousFingerParameter

```python
from booster_robotics_sdk_python import DexterousFingerParameter

# seq: 0~5 (手指序号)
# angle: 0~1000 (0=完全闭合, 1000=完全张开)
# force: 0~1500
# speed: 0~1000
finger = DexterousFingerParameter(seq=0, angle=1000, force=200, speed=800)
```

#### Odometer（里程计）

```python
from booster_robotics_sdk_python import Odometer

# 属性: x, y, theta (float)
```

#### LowState / MotorState / ImuState（低层状态）

```python
from booster_robotics_sdk_python import LowState, MotorState, ImuState

# LowState:
#   .imu_state → ImuState
#   .motor_state_parallel → List[MotorState]
#   .motor_state_serial → List[MotorState]

# ImuState:
#   .rpy → [roll, pitch, yaw]
#   .gyro → [gx, gy, gz]
#   .acc → [ax, ay, az]

# MotorState:
#   .mode, .q, .dq, .ddq, .tau_est, .temperature, .lost
```

#### HandReplyData / HandTouchData

```python
from booster_robotics_sdk_python import HandReplyData, HandTouchData, HandReplyParam, HandTouchParam

# HandReplyData:
#   .hand_index, .hand_type, .hand_data → List[HandReplyParam]
# HandReplyParam: .angle, .force, .current, .error, .status, .temp, .seq
# HandTouchData:
#   .hand_index, .hand_type, .touch_data → HandTouchParam
# HandTouchParam: .finger_one, .finger_two, .finger_three, .finger_four, .finger_five, .finger_palm
```

---

## 3. 官方 Python 示例

### 3.1 基本初始化 + 移动

```python
from booster_robotics_sdk_python import B1LocoClient, ChannelFactory, RobotMode

ChannelFactory.Instance().Init(0, 'eth0')

client = B1LocoClient()
client.Init()

# 模式切换
client.ChangeMode(RobotMode.kPrepare)   # 准备模式（站立）
client.ChangeMode(RobotMode.kWalking)    # 行走模式

# 移动
client.Move(0.2, 0.0, 0.0)    # 前进 0.2 m/s
client.Move(0.0, 0.0, 0.5)    # 左转 0.5 rad/s
client.Move(0.0, 0.0, 0.0)    # 停止
```

### 3.2 完整交互示例（b1_loco_example_client.py）

```python
while True:
    cmd = input().strip()
    if cmd == "mp":
        client.ChangeMode(RobotMode.kPrepare)
    elif cmd == "mw":
        client.ChangeMode(RobotMode.kWalking)
    elif cmd == "stop":
        client.Move(0, 0, 0)
    elif cmd == "w":
        client.Move(0.8, 0.0, 0.0)    # 前进
    elif cmd == "s":
        client.Move(-0.2, 0.0, 0.0)   # 后退
    elif cmd == "a":
        client.Move(0.0, 0.2, 0.0)    # 左移
    elif cmd == "d":
        client.Move(0.0, -0.2, 0.0)   # 右移
    elif cmd == "q":
        client.Move(0.0, 0.0, 0.2)    # 左转
    elif cmd == "e":
        client.Move(0.0, 0.0, -0.2)   # 右转
```

### 3.3 里程计订阅

```python
from booster_robotics_sdk_python import B1OdometerStateSubscriber

def handler(odometer_msg):
    print(f"Odometer: {odometer_msg.x}, {odometer_msg.y}, {odometer_msg.theta}")

ChannelFactory.Instance().Init(0)
sub = B1OdometerStateSubscriber(handler)
sub.InitChannel()
while True:
    time.sleep(1)
```

### 3.4 灵巧手控制

```python
from booster_robotics_sdk_python import DexterousFingerParameter, B1HandIndex

finger_params = []
for seq in range(6):
    fp = DexterousFingerParameter()
    fp.seq = seq
    fp.angle = 1000    # 张开
    fp.force = 200
    fp.speed = 800
    finger_params.append(fp)

client.ControlDexterousHand(finger_params, B1HandIndex.kRightHand)
```

---

## 4. C++ API 参考（关键接口）

### B1LocoClient 方法签名

```cpp
class B1LocoClient {
public:
    void Init();
    void Init(const std::string &robot_name);  // 指定机器人名称
    bool WaitForService(int64_t timeout_ms = 5000, bool require_response_path = true);

    int32_t SendApiRequest(LocoApiId api_id, const std::string &param);
    int32_t SendApiRequest(LocoApiId api_id, const std::string &param, int64_t timeout_ms);
    int32_t SendApiRequestFireAndForget(LocoApiId api_id, const std::string &param);

    int32_t ChangeMode(RobotMode mode);           // 返回 0=成功
    int32_t GetMode(GetModeResponse &resp);       // 查询当前模式
    int32_t GetStatus(GetStatusResponse &resp);   // 查询完整状态
    int32_t GetRobotInfo(GetRobotInfoResponse &resp);

    int32_t Move(float vx, float vy, float vyaw);           // 同步请求
    int32_t MoveCommand(float vx, float vy, float vyaw);    // 异步发送

    int32_t RotateHead(float pitch, float yaw);
    int32_t WaveHand(HandAction action);
    int32_t Handshake(HandAction action);
    int32_t MoveHandEndEffectorV2(const Posture &posture, int time_ms, HandIndex hand);
    int32_t ControlGripper(const GripperMotionParameter &param, GripperControlMode mode, HandIndex hand);
    int32_t ControlDexterousHand(const vector<DexterousFingerParameter> &params, HandIndex hand, BoosterHandType type);
    int32_t GetFrameTransform(Frame src, Frame dst, Transform &transform);
    int32_t SwitchHandEndEffectorControlMode(bool switch_on);
    int32_t GetUp();
    int32_t LieDown();
    int32_t Shoot();
    int32_t ZeroTorqueDrag(bool active);
    int32_t RecordTrajectory(bool active);
    int32_t ReplayTrajectory(std::string path);
    int32_t ResetOdometry();
    int32_t PlaySound(std::string path);
    int32_t Dance(DanceId id);
    int32_t WholeBodyDance(WholeBodyDanceId id);
    int32_t UpperBodyCustomControl(bool start);
    int32_t SwitchGait(GaitType gait_type);
    // ... 更多 API
};
```

### 关键 API ID

```cpp
enum class LocoApiId {
    kChangeMode = 2000,
    kMove = 2001,
    kRotateHead = 2004,
    kWaveHand = 2005,
    kRotateHeadWithDirection = 2006,
    kLieDown = 2007,
    kGetUp = 2008,
    kMoveHandEndEffector = 2009,
    kControlGripper = 2010,
    kGetFrameTransform = 2011,
    kSwitchHandEndEffectorControlMode = 2012,
    kControlDexterousHand = 2013,
    kHandshake = 2015,
    kDance = 2016,
    kGetMode = 2017,
    kGetStatus = 2018,
    kGetRobotInfo = 2022,
    kShoot = 2024,
    kGetUpWithMode = 2025,
    kZeroTorqueDrag = 2026,
    kRecordTrajectory = 2027,
    kReplayTrajectory = 2028,
    kWholeBodyDance = 2029,
    kUpperBodyCustomControl = 2030,
    kResetOdometry = 2031,
    kEnterWBCGait = 2035,
    kExitWBCGait = 2036,
    kMoveDualHandEndEffector = 2037,
    kVisualKick = 2038,
    kLionDancePrepare = 2039,
    kLionDanceStart = 2040,
    kLionDanceMove = 2041,
    kSwitchGait = 2042,
};
```

---

## 5. 最佳实践（从源码和示例中总结）

### 初始化流程

```python
# 1. 初始化 DDS
ChannelFactory.Instance().Init(0, 'eth0')

# 2. 创建客户端
client = B1LocoClient()
client.Init()

# 3. 等待机器人上线
client.WaitForService(timeout_ms=30000)
```

### 模式切换流程

```python
# 切换前先停止移动
client.Move(0, 0, 0)

# 等待 0.1s 确保停止指令生效
time.sleep(0.1)

# 切换模式
client.ChangeMode(RobotMode.kPrepare)
time.sleep(1.0)  # 等待模式切换完成

client.ChangeMode(RobotMode.kWalking)
time.sleep(1.0)  # 等待模式切换完成
```

### 移动指令

```python
# Move(vx, vy, vyaw)
# vx: 前后速度，正=前进，负=后退，单位 m/s
# vy: 左右速度，正=左移，负=右移，单位 m/s
# vyaw: 角速度，正=左转，负=右转，单位 rad/s

# 推荐速度范围
client.Move(0.2, 0.0, 0.0)    # 慢速前进
client.Move(0.5, 0.0, 0.0)    # 中速前进（官方示例最大值）
client.Move(0.8, 0.0, 0.0)    # 快速前进（官方示例）
```

### 错误处理

```python
res = client.ChangeMode(RobotMode.kWalking)
if res != 0:
    print(f"ChangeMode failed: error code {res}")

res = client.Move(0.2, 0.0, 0.0)
if res != 0:
    print(f"Move failed: error code {res}")
```

### 线程安全

- DDS 通信层内部有线程安全机制
- 多个 `B1LocoClient` 实例可以同时连接到同一机器人
- 每个 client 独立发送 RPC 请求，机器人按到达顺序处理
- Python binding 中 `py::gil_scoped_release` 用于在持有 GIL 的情况下进行 DDS 通信

### 已知限制

- `kDamping` 模式下机器人所有电机进入阻尼模式，机器人会摔倒——**仅用于紧急停止或维护**
- `Move()` 仅在 `kWalking` 模式下有效
- `kPrepare` 模式机器人保持站立，可以安全切换到 `kWalking`
- `MoveCommand()` 是 fire-and-forget，不保证送达；`Move()` 是同步请求，有响应确认
