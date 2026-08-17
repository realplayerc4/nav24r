# Nav24r 人形机器人自主导航系统 — 使用手册

**版本**: v2.8.0 | **更新日期**: 2026-08-15
**适用平台**: Ubuntu 24.04 + ROS 2 Jazzy + Python 3.12

---

## 目录

1. [项目概览](#1-项目概览)
2. [硬件组成](#2-硬件组成)
3. [软件架构](#3-软件架构)
4. [名词解释](#4-名词解释)
5. [核心概念与原理](#5-核心概念与原理)
6. [网络拓扑与配置](#6-网络拓扑与配置)
7. [快速开始](#7-快速开始)
8. [控制面板使用指南](#8-控制面板使用指南)
9. [命令行操作](#9-命令行操作)
10. [配置详解](#10-配置详解)
11. [故障排查](#11-故障排查)
12. [参考链接（Wiki）](#12-参考链接wiki)

---

## 1. 项目概览

**Nav24r** 是一个**人形机器人自主导航系统**，让 T1 双足人形机器人能够像轮式机器人一样自主导航：构建环境地图 → 定位 → 规划路径 → 行走到达目标点。

```
┌─────────────────────────────────────────────────────────────┐
│                        Nav24r 系统                          │
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐  │
│  │ OAK-D    │──▶│ RTAB-Map │──▶│  Nav2    │──▶│ t1_bridge│ │
│  │ 相机     │   │ SLAM定位  │   │ 导航规划  │   │ →T1 SDK  │ │
│  └──────────┘   └──────────┘   └──────────┘   └─────────┘  │
│                                                             │
│  建图 → 修图 → 定位 → 导航 全流程                            │
└─────────────────────────────────────────────────────────────┘
```

**核心能力**:
- 🗺️ **建图**：使用 OAK-D 深度相机 + RTAB-Map 构建 3D 环境地图
- 📍 **定位**：在已有地图中定位机器人当前位置
- 🧭 **导航**：Nav2 规划路径，RPP 控制器驱动机器人行走
- 🤖 **T1 桥接**：将 Nav2 速度指令转换为 T1 双足机器人行走指令

---

## 2. 硬件组成

| 组件 | 型号/说明 | 作用 |
|------|-----------|------|
| **机器人** | 加速进化 T1 双足人形 | 执行行走运动 |
| **相机** | Luxonis OAK-D Pro W | 深度相机，提供 RGB + 深度 |
| **导航电脑** | 运行 Nav24r 的电脑 | 建图/定位/导航计算 |
| **机器人板载** | Jetson (tegra-ubuntu) | 运行 T1 SDK + 实时控制 |
| **网络** | USB LAN 直连 | 电脑 ↔ 机器人通信 |

**关键参数**:
- 相机安装高度：`0.85m`
- 障碍物高度过滤：`0.2m ~ 1.4m`（低于地面、高于相机有效范围不视为障碍）
- 机器人半径：`0.5m`（footprint）
- 导航最高速度：`0.2 m/s`

---

## 3. 软件架构

### 3.1 系统分层

```
┌────────────────────────────────────────────────────┐
│              应用层：控制面板 (GUI)                 │
│  factor_control_panel.py                           │
├────────────────────────────────────────────────────┤
│              导航层：Nav2 导航栈                    │
│  全局规划(SmacPlanner2D) → 局部控制(RPP) → 速度平滑 │
├────────────────────────────────────────────────────┤
│              感知层：Factor Perception + RTAB-Map   │
│  视觉里程计 / SLAM建图 / 定位 / 点云障碍物          │
├────────────────────────────────────────────────────┤
│              桥接层：t1_bridge (纯Python)           │
│  /cmd_vel_smoothed → MoveCommand → T1 SDK          │
├────────────────────────────────────────────────────┤
│              机器人层：T1 双足机器人 (FastDDS)      │
└────────────────────────────────────────────────────┘
```

### 3.2 数据流（导航模式）

```
Nav2 Goal
   │
   ▼
Nav2 全局规划器 (SmacPlanner2D)
   │  /plan 全局路径
   ▼
Nav2 局部控制器 (RPP - Regulated Pure Pursuit)
   │  /cmd_vel (Twist: vx, vyaw)
   ▼
velocity_smoother (平滑加减速)
   │  /cmd_vel_smoothed
   ▼
t1_bridge (纯Python，订阅 cmd_vel_smoothed)
   │  B1LocoClient.MoveCommand(vx, vy, vyaw)
   ▼
T1 双足机器人 (行走)
```

### 3.3 关键软件组件

| 组件 | 版本/说明 | 作用 |
|------|-----------|------|
| ROS 2 | Jazzy | 机器人操作系统 |
| Factor Perception SDK | 第三方 | OAK-D 相机驱动 + 视觉里程计 |
| RTAB-Map | rtabmap_slam | SLAM 建图 / 定位 |
| Nav2 | 1.3.12 | 导航栈（规划 + 控制） |
| RPP 控制器 | RegulatedPurePursuitController | 局部路径跟踪 |
| SmacPlanner2D | SmacPlanner | 全局路径规划 |
| Booster T1 SDK | booster_robotics_sdk_python 1.5.6 | T1 机器人运动控制 |

---

## 4. 名词解释

### 4.1 基础概念

| 术语 | 全称/说明 |
|------|-----------|
| **ROS 2** | Robot Operating System 2，机器人软件框架，提供话题/服务/动作通信 |
| **Node** | ROS2 节点，独立运行的程序单元，可发布/订阅话题 |
| **Topic** | 话题，节点间异步通信通道（如 `/cmd_vel` 速度指令） |
| **Service** | 服务，请求-响应式同步通信（如 `/get_state`） |
| **Action** | 动作，长任务异步通信（如 `/navigate_to_pose` 导航目标） |
| **TF** | Transform，坐标系变换树（如 `map → odom → base_link`） |

### 4.2 DDS 相关

| 术语 | 说明 |
|------|------|
| **DDS** | Data Distribution Service，数据分发服务，ROS2 底层通信中间件 |
| **CycloneDDS** | Eclipse CycloneDDS，本系统电脑侧 ROS2 的 RMW 实现 |
| **FastDDS** | eProsima FastDDS，T1 机器人 SDK 使用的 DDS 实现 |
| **Domain** | DDS 域，用 `ROS_DOMAIN_ID` 隔离，不同域互不可见 |
| **RMW** | ROS Middleware Interface，ROS2 中间件抽象层 |
| **Type hash** | DDS 类型哈希，不同 DDS 实现间类型不匹配会报 warning |

### 4.3 SLAM / 定位

| 术语 | 说明 |
|------|------|
| **SLAM** | Simultaneous Localization And Mapping，同时定位与建图 |
| **RTAB-Map** | Real-Time Appearance-Based Mapping，基于外观的实时 SLAM |
| **Loop Closure** | 回环检测，识别回到已访问位置，纠正累积漂移 |
| **Odometry** | 里程计，估计机器人相对运动（`/factor_perception/odom`） |
| **VIO** | Visual-Inertial Odometry，视觉-惯性里程计 |
| **Localization** | 定位，在已知地图中确定机器人位置 |
| **AMCL** | Adaptive Monte Carlo Localization，自适应蒙特卡洛定位（Nav2 常用） |

### 4.4 Nav2 导航

| 术语 | 说明 |
|------|------|
| **Nav2** | Navigation 2，ROS2 导航框架 |
| **Global Planner** | 全局规划器，规划从起点到目标的可通行路径 |
| **SmacPlanner2D** | Smac 2D 全局规划器（A* 算法 + 路径平滑） |
| **Local Controller** | 局部控制器，跟踪全局路径并输出速度指令 |
| **RPP** | Regulated Pure Pursuit，纯追踪控制器（简单可靠） |
| **MPPI** | Model Predictive Path Integral，模型预测路径积分控制器（高级，需调参） |
| **Costmap** | 代价地图，栅格化表示障碍物/可通行区域 |
| **Inflation Layer** | 膨胀层，在障碍物周围膨胀，避免机器人碰撞 |
| **Footprint** | 足迹，机器人在地图上的占地区域（本系统 0.5m 圆形） |
| **Lifecycle Node** | 生命周期节点，有 unconfigured/inactive/active 等状态 |

### 4.5 T1 机器人

| 术语 | 说明 |
|------|------|
| **B1LocoClient** | T1 SDK 的运动控制客户端 |
| **MoveCommand** | 发送速度指令（fire-and-forget，无需响应） |
| **ChangeMode** | 切换机器人模式 |
| **RobotMode** | 机器人模式：kDamping=0, kPrepare=1, kWalking=2 |
| **kDamping** | 阻尼模式，电机断电（机器人瘫倒） |
| **kPrepare** | 准备模式，站立 |
| **kWalking** | 行走模式，唯一可移动的模式 |
| **Fire-and-forget** | 发送后不等待响应的调用方式 |

---

## 5. 核心概念与原理

### 5.1 人形机器人导航难点

与轮式机器人相比，人形双足机器人导航有特殊约束：

| 约束 | 影响 |
|------|------|
| **无横移 (vy=0)** | 不能侧移，只能前进/后退/转向 → 用 DiffDrive/RPP 模型 |
| **转向受限** | 原地转向慢，偏好转弯弧线 |
| **不能急停** | 需平滑加减速（velocity_smoother） |
| **步态低速** | 行走速度低（0.2 m/s），需足够速度才推进 |
| **稳定性** | 定位漂移会导致导航异常 |

### 5.2 为什么用 RPP 而不是 MPPI

- **RPP（Regulated Pure Pursuit）**：简单可靠，3 个参数（lookahead、最大速度），适合人形
- **MPPI**：高级但难调参，实测在 mock/真机环境控制环只有 5-14Hz（需 20Hz），输出近零卡住
- 本项目**实机用 RPP**，MPPI 配置备份在 `nav2_params_mppi_backup.yaml`

### 5.3 domain 隔离（为什么必须）

- 电脑侧 Nav2 用 **CycloneDDS**
- 机器人 T1 SDK 用 **FastDDS (domain 0)**
- 两者同在 domain 0 会互相发现但类型不匹配 → type hash 警告刷屏 → Nav2 启动失败 / SDK 连接被干扰 → **机器人 damping**

**解决**：电脑侧 ROS2 统一 `ROS_DOMAIN_ID=42`，与机器人 FastDDS 隔离。

### 5.4 t1_bridge 为什么纯 Python

- t1_bridge 之前 `import rclpy`（CycloneDDS）+ T1 SDK（FastDDS）**同一进程** → 两套 DDS 冲突 → **Segfault**
- 改为纯 Python：不 import rclpy，用 `subprocess ros2 topic echo` 获取 cmd_vel → 解析 → MoveCommand
- 只连 SDK（FastDDS），不与 Nav2 的 CycloneDDS 同进程

### 5.5 SDK 调用约定（关键）

| 调用 | 类型 | 说明 |
|------|------|------|
| `MoveCommand()` | fire-and-forget | 移动指令，推荐 |
| `SendApiRequestFireAndForget(kChangeMode, '{"mode":N}')` | fire-and-forget | 模式切换，推荐 |
| `Move()` | 同步 | ❌ 无 rpc_service_node 时 502 |
| `ChangeMode()` | 同步 | ❌ 无 rpc_service_node 时 502 |
| `SendApiRequest()` | 同步 | ❌ 502 |

> **规则**：一律用 fire-and-forget 接口。停止指令可能丢包，需连发多次。

---

## 6. 网络拓扑与配置

### 6.1 拓扑

```
nav24r 电脑 (192.168.10.103) ──LAN 直连── Robot eth0 (192.168.10.102)
    │                                    │
    │ 电脑侧 ROS2: ROS_DOMAIN_ID=42       │
    │ Nav2/CycloneDDS (隔离，避免冲突)     │
    │                                    FastDDS (domain 0)
    │                                    T1 SDK DDS + ROS2 Humble
```

### 6.2 网络配置

| 项目 | 值 |
|------|-----|
| 电脑 LAN 接口 | `enx207bd2d33010` = `192.168.10.103/24` |
| 机器人 eth0 | `192.168.10.102/24` |
| ROS_DOMAIN_ID | `42`（电脑侧） |
| WiFi | `192.168.0.x` 不使用 |

> ⚠️ 电脑 LAN 接口需配置静态 IP `192.168.10.103/24`（可用 nmcli 持久化）。

### 6.3 GitHub 推送（代理）

- 系统 DNS 被 Clash fake-ip 污染（`198.18.0.x`），直连 GitHub 不通
- 需走 Clash 代理推送：
```bash
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push origin main
```

---

## 7. 快速开始

### 7.1 环境要求

- Ubuntu 24.04 + ROS 2 Jazzy
- Python 3.12
- 安装依赖：
```bash
pip install booster_robotics_sdk_python pyyaml numpy
```

### 7.2 完整流程（建议）

1. **启动控制面板**（唯一主入口）：
```bash
python3 scripts/factor_control_panel.py
```

2. **新建建图**（首次）：点 🗺️ 新建建图，手持/操控机器人在环境中走一遍

3. **续建 / 修图**（可选）：点 🔄 续建 继续建图

4. **开始定位**：点 🧭 开始定位（加载地图）

5. **完整导航**：点 🚀 完整导航（自动带 t1_bridge + domain 42）

6. **发送目标**：RViz 中点击 "Nav2 Goal" 设置目标点

---

## 8. 控制面板使用指南

### 8.1 功能按钮一览

| 区域 | 按钮 | 功能 |
|------|------|------|
| 📷 设备状态 | ⏹️ 停止 | 停止所有 ROS 节点 |
| 📷 设备状态 | 🔄 重启相机 | 软重启相机进程 |
| 📷 设备状态 | ⚡ 强制重连 | 停止进程 + 重置 USB |
| 📦 数据库 | 允许覆盖 | 地图保护开关（关闭时禁止覆盖） |
| 📦 数据库 | 🗑️ 重置地图 | 删除数据库 |
| 📦 数据库 | 🗺️ 导出Octomap | 启动 Database Viewer 导出 |
| 📦 数据库 | ☁️ 导出点云+RViz | PLY 转 ROS2 话题 |
| 📦 数据库 | 🧹 清理地面误判 | 清理弱纹理地面误判障碍 |
| 📦 数据库 | ✂️ 清理节点 | 交互式删除数据库节点 |
| 🤖 T1 控制 | Prepare | 机器人站立准备 |
| 🤖 T1 控制 | Walking | 机器人行走模式（可移动） |
| 🤖 T1 控制 | Damping | 电机断电（⚠️ 二次确认） |
| 🤖 T1 控制 | W/A/S/D/Q/E | 方向键手动操控 |
| 功能 | 🗺️ 新建建图 | 清空数据库建图 |
| 功能 | 🔄 续建 | 继续建图 |
| 功能 | 🧭 开始定位 | 定位模式 |
| 功能 | 🚀 完整导航 | 全栈导航（+T1桥接） |
| 功能 | 📊 RViz / RViz 3D | 可视化 |
| 功能 | 📊 地图质量 | 地图质量分析 |
| 功能 | 🧪 测试报告 | 运行测试框架 |

### 8.2 T1 控制区（重要）

- **模式是"开关"**：由按钮决定，不自动推断（leg_tau 推断不可靠已移除）
- **Damping 有二次确认**：警告"电机将直接失去电力，站立中的机器人会瘫倒"
- **方向键**：W/S 前后 (0.2 m/s)、A/D 左右、Q/E 转向（按住移动，松手停止）
- **停止按钮**：切断 Nav2 规划 + 连发停止指令

---

## 9. 命令行操作

### 9.1 常用命令

```bash
# 建图
ros2 launch nav24r factor_perception_auto.launch.py cam_pos_z:=0.85

# 定位
ros2 launch nav24r factor_perception_auto.launch.py localization:=true

# 完整导航（T1 桥接）
ros2 launch nav24r nav24r_full.launch.py localization:=true use_t1_bridge:=true

# T1 SDK 连通性测试
python3 scripts/test_t1_sdk.py

# Nav2 输出观察（domain 42）
export ROS_DOMAIN_ID=42
ros2 topic echo /cmd_vel_smoothed
```

### 9.2 发送 Nav2 目标

```bash
export ROS_DOMAIN_ID=42
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 2.0}, orientation: {w: 1.0}}}}"
```

### 9.3 Mock 仿真（无实机测试）

```bash
# 方案一：模拟感知数据
ros2 launch nav24r simulation/simulation_nav2.launch.py

# 方案二：真实测试地图 + 差分模拟器
python3 scripts/generate_test_map.py
ros2 launch nav24r mock_nav.launch.py
```

---

## 10. 配置详解

### 10.1 配置文件

| 文件 | 用途 |
|------|------|
| `config/nav2_params.yaml` | **真机** Nav2 参数（RPP 控制器） |
| `config/nav2_params_mock.yaml` | mock 环境参数（RPP） |
| `config/nav2_params_mppi_backup.yaml` | MPPI 配置备份 |
| `config/rtabmap.ini` | RTAB-Map 参数（SDK 自带） |
| `config/maps_config.json` | 地图管理配置 |

### 10.2 Nav2 关键参数（nav2_params.yaml）

| 参数 | 值 | 说明 |
|------|-----|------|
| 全局规划器 | SmacPlanner2D | A* + 路径平滑，人形可原地转 |
| 局部控制器 | RPP | 简单可靠 |
| `desired_linear_vel` | 0.2 | 最大前进速度 (m/s) |
| `max_velocity` | [0.2, 0, 0.4] | velocity_smoother 速度上限 |
| `max_accel` | [0.25, 0, 0.6] | 缓加速（防前倾） |
| footprint | 0.5m 圆 | 机器人足迹 |
| inflation_radius | 0.7 | 障碍物膨胀半径 |
| 障碍物高度 | 0.2~1.4m | 高度过滤 |

---

## 11. 故障排查

### 11.1 机器人 damping（电机断电）

| 可能原因 | 排查 | 解决 |
|----------|------|------|
| 多 t1_bridge 进程 | `ps aux \| grep t1_bridge` | 杀掉多余 t1_bridge，只留 1 个 |
| Nav2 CycloneDDS 干扰 SDK | 检查 type hash 警告 | 确保 ROS_DOMAIN_ID=42 |
| 重复启动未清理 | `ps aux \| grep nav2_` | 每次启动前先"⏹️ 停止" |

### 11.2 vx=0 机器人不走（Nav2 有路径但不动）

| 可能原因 | 排查 | 解决 |
|----------|------|------|
| **目标已到** | 查机器人到目标距离 <0.15m | 发远距离目标 |
| **RTAB-Map 定位漂移** | 日志 `NaN found in local descriptor map` | 重新定位 |
| odom 静止漂移 | 静止时位置 ±0.1m 抖动 | 检查相机/RTAB-Map |
| 控制环慢 | 日志 `Control loop missed` | 降低 batch_size（若用 MPPI） |

### 11.3 推送 GitHub 失败

- DNS 被 Clash fake-ip 污染（`198.18.0.x`）→ 需走代理
```bash
git -c http.proxy=http://127.0.0.1:7897 push origin main
```

### 11.4 bt_navigator 启动失败（follow_path not available）

- 通常因 DDS 干扰导致 controller 激活慢
- 解决：确保 domain 隔离 + 重启 Nav2

---

## 12. 参考链接（Wiki）

### 官方文档
- [ROS 2 文档](https://docs.ros.org/en/jazzy/)
- [Nav2 文档](https://docs.nav2.org/)
- [Nav2 MPPI 配置指南](https://docs.nav2.org/configuration/packages/configuring-mppic.html)
- [RTAB-Map Wiki](https://github.com/introlab/rtabmap/wiki)
- [CycloneDDS](https://github.com/eclipse-cyclonedds/cyclonedds)
- [FastDDS](https://fast-dds.docs.eprosima.com/)

### 概念科普
- [SLAM 是什么](https://en.wikipedia.org/wiki/Simultaneous_localization_and_mapping)
- [DDS 数据分发服务](https://en.wikipedia.org/wiki/Data_Distribution_Service)
- [A* 路径规划](https://en.wikipedia.org/wiki/A*_search_algorithm)
- [Pure Pursuit 纯追踪](https://en.wikipedia.org/wiki/Pure_pursuit)
- [MPC 模型预测控制](https://en.wikipedia.org/wiki/Model_predictive_control)

### 本项目文档
- [README](../README.md) - 项目快速总览
- [T1 桥接状态](t1_bridge_status.md) - T1 桥接设计
- [Booster T1 SDK](booster_t1_sdk.md) - SDK API 参考
- [变更日志](../CHANGELOG.md) - 版本历史

---

*本手册由 Nav24r 项目维护，如有疑问请参考上述链接或联系项目维护者。*
