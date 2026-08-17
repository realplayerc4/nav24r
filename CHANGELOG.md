# 变更日志

## [v2.8.0] - 2026-08-15 - 真机完整导航验证 + RTAB-Map 定位漂移诊断

### 🎯 真机完整导航验证（成功）
- ✅ **完整导航链路走通**：Nav2 Goal → 路径(97点) → RPP 满速 0.2m/s → velocity_smoother → t1_bridge → MoveCommand → 机器人行走 **7.24m 到达目标**
- ✅ 无 damping、无原地踏步（干净环境 + 单 t1_bridge）
- ✅ 手动 MoveCommand 走 0.2m 正常（SDK 步态控制验证通过）

### 🔍 重要诊断：RTAB-Map 定位漂移（vx=0 根因）
- ⚠️ **`NaN found in local descriptor map`**（RTAB-Map 视觉定位产生 NaN）
- ⚠️ odom 静止时 ±0.1m 抖动，位移累计假数据（数十米但实际位置不变）
- ⚠️ Nav2 基于漂移 odom → RPP 输出 vx=0 → 机器人不走 → 进度检查失败循环
- ⚠️ 控制环速率仅 5-14Hz（应 20Hz）
- 📌 **结论**：vx=0 非 Nav2 配置问题，是 RTAB-Map 定位漂移所致。手动控制（不依赖 odom）正常

### 🔧 环境/运维
- ⚠️ 多次点"完整导航"会累积多个 t1_bridge 进程（多客户端连 SDK 导致 damping/异常）——**每次启动前先"⏹️ 停止"清理**
- ✅ 推送 GitHub 需走 Clash 代理（`-c http.proxy=http://127.0.0.1:7897`，DNS 被 fake-ip 污染）

---

## [v2.7.4] - 2026-08-14 - domain 隔离 + velocity_smoother 激活修复 + 真机走步验证

### 🔧 真机走步验证通过
- ✅ **机器人实际走步 0.2m 成功，全程无 damping**（MoveCommand 步态控制正常）

### 🌐 domain 隔离（根治 FastDDS/CycloneDDS 冲突）
- ✅ 电脑侧 ROS2（Nav2/CycloneDDS）统一 `ROS_DOMAIN_ID=42`，与机器人 FastDDS(domain 0) 隔离
- ✅ 影响文件：`launch/nav24r_full.launch.py`、`t1_bridge.py`、`factor_control_panel.py`、`cancel_nav2_goal.py`、`test_nav2_goal.py`
- ✅ 解决：type hash 警告刷屏、bt_navigator 启动失败(follow_path 超时)、SDK 连接被干扰导致 damping

### 🔧 velocity_smoother 激活修复
- ✅ **`velocity_smoother` 加入 lifecycle_manager node_names**（此前未激活 → /cmd_vel_smoothed 无输出 → 机器人不动）
- ✅ 数据流完整：controller → /cmd_vel → smoother(激活) → /cmd_vel_smoothed → t1_bridge → MoveCommand

### 📋 其他
- ✅ `t1_bridge.py` 纯 Python 化（不用 rclpy，subprocess ros2 topic echo 获取 cmd_vel）
- ✅ 控制面板 T1 停止按钮可切断 Nav2 规划（`cancel_nav2_goal.py` 抢占目标）

---

## [v2.7.3] - 2026-08-14 - t1_bridge 纯 Python 化（修复真机 Segfault / damping）

- ✅ **根因**：t1_bridge 之前同时 `import rclpy`（CycloneDDS）+ booster SDK（FastDDS），两套 DDS 在同一进程冲突导致 Segfault，机器人侧检测到控制客户端异常断开而切 damping
- ✅ **t1_bridge 纯 Python 化**：不再 `import rclpy`，改用 `subprocess ros2 topic echo` 获取 cmd_vel，解析 YAML 后通过 SDK `MoveCommand` 转发（与控制面板同为纯 Python + SDK，无 DDS 冲突）
- ✅ 去掉 leg_tau 模式推断（不可靠，控制面板负责模式）
- ✅ launch 里 t1_bridge 从 `Node` 改为 `ExecuteProcess`（纯 Python 脚本用命令行参数）
- ✅ 修复 YAML 解析（`ros2 topic echo` 的 `---` 分隔符导致解析失败）
- ✅ 端到端验证通过：发布 cmd_vel → t1_bridge 正确接收并转发

---

## [v2.7.2] - 2026-08-14 - 停止按钮切断 Nav2 规划

- ✅ **T1 停止按钮现在会取消 Nav2 导航目标**：先抢占 Nav2 目标（发"原地目标"），再连发停止指令，防止 Nav2 继续下发 cmd_vel 导致机器人停不住
- ✅ 新增 `scripts/cancel_nav2_goal.py`：用 rclpy ActionClient 读取当前位姿并发"原地目标"抢占（`ros2 action cancel` 在 Jazzy 不存在；rclpy cancel API 有 bug，改用抢占）
- ✅ **mock 实测通过**：导航中执行抢占 → 旧目标 ABORTED → cmd_vel 归零 → 机器人停止

---

## [v2.7.1] - 2026-08-14 - Mock 导航链路实测通过

- ✅ **mock 环境改用 RPP 控制器**（`config/nav2_params_mock.yaml`），实测导航目标 SUCCEEDED
- ✅ **参数文件分工**：mock → RPP（轻量可靠）；实机 → MPPI DiffDrive（`nav2_params.yaml`，待实机调参）
- ✅ **t1_bridge dry-run 模式**：`-p dry_run:=true` 只记录 cmd_vel，不连接/驱动机器人
- ✅ 修复 `PathFollowCritic offset_from_furthest` 过大导致短路径无前进驱动力的问题（40→6）

> MPPI 在 mock 环境控制环仅 ~5.5Hz 且输出近零（非算力问题，疑 mock costmap/TF 同步限制），故 mock 验证用 RPP；MPPI 留待实机调优。

---

## [v2.7.0] - 2026-08-14 - Nav2 人形机器人导航适配

### 🤖 人形适配（基于公开最佳实践调研）
- ✅ **MPPI 运动模型 Omni → DiffDrive**：人形无横移，Omni 生成无法执行的轨迹（vy_std 归 0）
- ✅ **补全 MPPI critic**（5 个新增）：ConstraintCritic / PathFollowCritic / GoalAngleCritic / PathAngleCritic / PreferForwardCritic
- ✅ **全局规划器 NavFn → SmacPlannerHybrid**（Hybrid A*）：考虑非完整约束，生成人形可跟随的平滑弧线
- ✅ **启用 velocity_smoother**：controller → /cmd_vel → smoother → /cmd_vel_smoothed → t1_bridge，平滑加减速防前倾
- ✅ **调参**：wz_max 0.5→0.4（双足转向受限）、inflation 0.6→0.7（更大障碍余量）、prune_distance 1.0→1.5

### 🔧 相关文件
- ✅ `config/nav2_params.yaml`：MPPI/规划器/代价地图/velocity_smoother 人形调优
- ✅ `launch/nav24r_full.launch.py`：新增 velocity_smoother 节点，t1_bridge 订阅 /cmd_vel_smoothed
- ✅ `scripts/test_nav2_goal.py`：默认观察 /cmd_vel_smoothed（可 --cmd-vel-topic 指定）

### 📚 文档
- ✅ `README.md` / `docs/t1_bridge_status.md`：数据流更新（加入 velocity_smoother）
- ✅ 规划详见 `~/.claude/plans/steady-wobbling-mccarthy.md`

---

## [v2.6.0] - 2026-08-14 - 控制面板 T1 实测修复 + 纯 Python SDK 方案定型

### 🔧 面板实测修复（有实机验证）
- ✅ **模式改为"开关"模型**：模式完全由按钮决定，**移除 leg_tau 自动推断**
  - 实测 leg_tau 站立时波动极大（0.06~2.05Nm，26% 采样 <0.5），无法可靠区分 Prepare/Damping，导致模式不停跳变
- ✅ **模式切换改用真 fire-and-forget**：`SendApiRequestFireAndForget(kChangeMode, '{"mode":N}')`
  - 修复：`ChangeMode()`/`SendApiRequest()` 同步请求无 rpc_service_node 时抛 502（机器人忙碌/行走时更易触发）
- ✅ **切换模式前先停止**：先连发 MoveCommand(0) ~0.6s 再发模式指令
  - 修复：Walking→Prepare 需机器人先停止步态，否则 Prepare 指令被忽略（Damping 断电随时有效）
- ✅ **停止连发**：`_t1_stop` 20Hz 连发 10 次停止指令（fire-and-forget 可能丢包）
  - 修复：松手后机器人继续行走 / 停止按钮无效
- ✅ **A/D 左右修正**：实测 vy 正=左、vy 负=右（与 SDK 文档相反），A=左(+vy)、D=右(-vy)
- ✅ **Damping 二次确认弹窗**：警告"电机将直接失去电力，站立中的机器人会瘫倒"
- ✅ **订阅器导入修复**：补上 `B1LowStateSubscriber`/`B1OdometerStateSubscriber` 导入（此前缺失导致状态订阅从未启动）
- ✅ `_t1_status_var` 笔误修复（`self._t1_status_var` → `self.t1_status_var`）

### 📋 实测结论（2026-08-14，机器人 LAN 直连）
- 面板可正常：Prepare/Walking/Damping 切换、WASD/QE 移动、松手停止
- 机器人空闲（Prepare）时 ChangeMode/MoveCommand 稳定返回 None；行走中同步请求会 502
- 网络：LAN `192.168.10.103/24` ↔ 机器人 `192.168.10.102`（eth0），以太网 0 错误

### 📚 文档
- ✅ `docs/t1_bridge_status.md`：模式控制改为开关模型、fire-and-forget 用法
- ✅ `docs/booster_t1_sdk.md`：ChangeMode/Move 502 说明 + MoveCommand 推荐
- ✅ `README.md` / `CLAUDE.md`：T1 控制按钮、Damping 确认、面板描述

---

## [v2.5.0] - 2026-08-13 - Python SDK 验证 + LAN 直连

### 🆕 新功能
- ✅ `scripts/test_t1_sdk.py`：T1 SDK 最小连通性测试脚本
- ✅ Python SDK 核心功能全部验证通过：
  - 模式切换 (Damping → Prepare → Walking)
  - 运动控制 (Move / SendApiRequest)
  - 状态读取 (B1LowStateSubscriber 23电机 + IMU ~500Hz)
  - 里程计订阅 (B1OdometerStateSubscriber ~600Hz)
- ✅ 控制面板 T1 方向键映射修正（W/S=前后, A/D=左右, Q/E=转向）

### 🔧 改动
- ✅ 网络接口统一为 LAN 直连 `enx207bd2d33010`（废弃 WiFi 跳板）
- ✅ `t1_bridge.py` 默认 network_interface → `enx207bd2d33010`
- ✅ `nav24r_full.launch.py` 默认 t1_network_interface → `enx207bd2d33010`
- ✅ `factor_control_panel.py` T1 初始化接口 → `enx207bd2d33010`
- ✅ A/D 键 vy 符号修正：A=左(vy负), D=右(vy正)，与机器人实际移动方向一致
- ✅ 模式检测改用 subscriber 推断（B1LowStateSubscriber 电机扭矩），不再依赖 GetMode RPC
- ✅ `t1_bridge.py` 添加 B1LowStateSubscriber 用于 Walking 模式检测

### 📚 文档
- ✅ `docs/t1_bridge_status.md`：更新网络拓扑、SDK 验证结果、坐标系说明
- ✅ `CLAUDE.md`：更新网络拓扑、启动命令
- ✅ `README.md`：T1 网络接口参数更新
- ✅ 删除废弃的 FastDDS XML 配置文件（t1_sdk_fastdds.xml, t1_sdk_fastdds_unicast.xml）

### 📋 机器人信息
- 固件: v1.1.0.0-release (branch: release/v1.1.0-20250421)
- SDK: booster_robotics_sdk_python==1.5.6
- SSH: booster@192.168.10.102 (LAN)

---

## [v2.4.0] - 2026-08-10 - T1 双足机器人桥接

### 🆕 新功能
- ✅ `scripts/t1_bridge.py`：Nav2 → T1 SDK 速度桥接节点
  - 订阅 `/cmd_vel`，调用 `B1LocoClient.MoveCommand(vx, vy, vyaw)`
  - 看门狗 `watchdog_timeout=2.0s` 无指令自动停车
  - 指令直接转发（Nav2 controller 已限速 ~20Hz），不做额外节流
  - 模式保护：仅 kWalking 模式转发（B1LowStateSubscriber 扭矩推断）
  - SDK 连接超时优雅关闭（`raise RuntimeError` → `finally`）
  - 退出时发送停止指令 `MoveCommand(0,0,0)`
- ✅ `launch/nav24r_full.launch.py`：新增 `use_t1_bridge` / `t1_network_interface` 参数
- ✅ `setup.py`：注册 `t1_bridge` console_scripts 入口
- ✅ `docs/t1_bridge_status.md`：T1 Bridge 设计文档与旧代码对比
- ✅ `scripts/mock_trajectory_publisher.py`：Mock 轨迹测试 t1_bridge → SDK 链路
- ✅ `scripts/test_nav2_goal.py`：Nav2 目标导航测试（发目标 → 验证 cmd_vel 输出合理性）

### 📚 文档
- ✅ README.md 新增 T1 双足机器人导航章节
- ✅ CHANGELOG.md 新增 v2.4.0

---

## [v2.3.0] - 2026-07-22 - Nav2 修复 + 地图保护 + 清理工具

### 🐛 Bug 修复
- ✅ Nav2 composition 模式：nav2_container 依赖修复（nav2_bringup 自带 lifecycle manager）
- ✅ Localization 模式：use_composition 布尔量处理修复（False 时走非 composition 路径）

### 🛡️ 地图保护增强
- ✅ 新增地图保护开关（默认关闭）：关闭时禁止覆盖已有数据库
- ✅ 重置地图按钮受保护开关约束
- ✅ 清理地面误判工具受保护开关约束

### 🛠️ 新增工具
- ✅ `cleanup_rtabmap.py`：交互式 RTAB-Map 节点清理工具（列表/缩略图/多选删除）
- ✅ `odom_covariance_fix.py`：里程计协方差修复节点（RTAB-Map 需要有效 covariance）
- ✅ `ply_to_pointcloud.py`：PLY 点云转 ROS2 PointCloud2 话题

### 📝 其他
- ✅ pre-commit hook 配置

---

## [v2.2.0] - 2026-07-20 - 障碍物高度过滤 + 地毯优化 + 数据库保护

### 🐛 Bug 修复
- ✅ 数据库表名不匹配：`_check_db_integrity()` 检查旧版表名 `vertex`/`rgbd_image`，RTAB-Map v0.22+ 使用 `Node`/`Data`

### 📝 按钮文案修正
- ✅ "开始导航" → "开始定位"（实际启动 localization 模式）
- ✅ 状态栏/日志同步修正

### 🛡️ 数据库保护
- ✅ 按钮视觉保护：数据库存在时按钮变橙色 + "(覆盖)" 文字提示
- ✅ 确认弹窗：已有确认框，本次确认代码路径正确（依赖完整性检查通过）

### 📏 障碍物高度过滤 (0.2m ~ 1.4m)
- ✅ `rtabmap.ini`：`MaxObstacleHeight=1.4`, `MinGroundHeight=0.2`, `MaxGroundAngle=30`
- ✅ `nav2_params.yaml`：local/global costmap `max_obstacle_height=1.4`, `min_obstacle_height=0.2`

### 🏠 地毯/弱纹理地面优化
- ✅ `ir_intensity` 从 0.4 提升到 0.8（IR 投影仪电流增强）
- ✅ 立体匹配：`TextureThreshold=5`, `UniquenessRatio=10/12`, `SpeckleRange=3`
- ✅ 噪声过滤：`NoiseFilteringMinNeighbors=7`

### 🖼️ RViz 配置
- ✅ 新建 `navigation_clean.rviz`：导航专用干净视图（无点云噪点）
- ✅ `mapping_3d.rviz`：移除地面/全局点云，仅保留 Octomap 3D (0.2~1.4m)
- ✅ 所有 RViz 面板标题标注高度范围

### 📂 影响文件
```
scripts/factor_control_panel.py
config/rtabmap.ini
config/nav2_params.yaml
config/factor_perception_config.yaml
factor_perception_auto.launch.py
launch/nav24r_full.launch.py
launch/factor_perception_isolated.launch.py
config/mapping.rviz
config/mapping_3d.rviz
config/navigation.rviz
config/navigation_clean.rviz       # 新增
config/map_viewer_3d.rviz
config/octomap.rviz
config/octomap_3d.rviz
```

## [v2.1.0] - 2026-07-17 - SDK 更新与配置简化

### 🔧 配置更新
- ✅ 删除 `config/rtabmap_custom.ini`，采用 SDK 自带 `rtabmap.ini`
- ✅ `cam_pos_z` 更新为 0.85m（相机实际安装高度）
- ✅ `depth_filter` 关闭（默认 false）
- ✅ `ir_intensity` 保持 0.4（室内 VIO 稳定性）
- ✅ 移除 3D 避障自定义参数（Grid/3D, MaxObstacleHeight 等）

### 🚀 Launch 文件简化
- ✅ `factor_perception_auto.launch.py` 简化为单 `rtabmap_slam` 节点
- ✅ `nav24r_full.launch.py` 简化为单 `rtabmap_slam` 节点
- ✅ `factor_perception_isolated.launch.py` 简化为单 `rtabmap_slam` 节点
- ✅ 移除 `continue_mapping` 参数（RTAB-Map 自动加载已有地图）
- ✅ 新增暴露 `camera_cpu`、`imu_cpu`、`rgb_fps` 参数
- ✅ 容器保持 `component_container_mt`

### 📚 文档更新
- ✅ 更新 `README.md`、`factor_perception/README.md`、`knowledge.md`、`spec.md`
- ✅ 更新 `config/rtabmap_config_doc.md` 反映 SDK 默认配置
- ✅ 更新 `scripts/factor_control_panel.py` 和 `start_rtabmap_light.sh`
- ✅ 更新 `CLAUDE.md` 项目结构

### 🔧 其他
- ✅ `config/factor_perception_config.yaml` 同步更新参数

---

## [v2.0.0] - 2026-06-19 - 系统架构优化

### 🔧 架构改进

#### ROS2 工程规范优化
- ✅ **容器隔离架构** - 硬件驱动与SLAM分离，避免单点故障
- ✅ **生命周期管理** - 添加LifecycleNode支持，实现优雅启停
- ✅ **设备检测机制** - 启动前自动检查OAK-D设备，防止崩溃
- ✅ **错误恢复机制** - 组件崩溃后自动重启，提高稳定性
- ✅ **路径规范化** - 使用PathJoinSubstitution替代硬编码路径

#### 新增文件
- 📄 `launch/factor_perception_isolated.launch.py` - 隔离架构启动文件
- 📄 `config/rtabmap_light.rviz` - 轻量化 RViz 配置
- 📄 `docs/ros2_engineering_analysis.md` - ROS2 工程分析报告

#### 控制面板增强
- ✅ 实时设备状态显示
- ✅ 自动设备检测（每3秒）
- ✅ 相机重启功能（软重启）
- ✅ 强制重连功能（停止进程+重置USB）
- ✅ 启动前设备检查

### 📚 文档优化

#### 技术文档
- 📖 完整的ROS2工程问题分析（严重问题5个，中等问题4个）
- 📖 RTAB-Map配置详细说明（参数来源、修改对比、Nav2同步）
- 📖 Nav2集成方案（实时建图vs独立地图服务器）
- 📖 系统架构对比表（当前vs改进后）

#### 使用指南
- 📖 设备检测使用说明
- 📖 轻量化启动方案
- 📖 崩溃问题排查指南

---

## [v1.1.0] - 2026-06-15 - ROS2 Jazzy 升级和功能增强

### 新增功能

#### 控制面板增强
- ✅ 添加地图质量分析功能（一键解读地图质量）
- ✅ 添加多视角 RViz 配置（3D 建图、Octomap、地图观察器）
- ✅ 改进停止功能，彻底清理 RTAB-Map 和相关进程
- ✅ 添加配置文件支持，移除硬编码密钥
- ✅ 添加错误处理和日志记录

#### 配置文件
- ✅ `factor_perception_config.yaml` - 集中管理配置
- ✅ `mapping_3d.rviz` - 3D 多视角建图配置
- ✅ `octomap_3d.rviz` - Octomap 专用配置
- ✅ `map_viewer_3d.rviz` - 地图观察器配置
- ✅ `cyclonedds.xml` - Cyclone DDS 优化配置

#### 文档
- ✅ ROS2 Jazzy 升级完整测试报告
- ✅ Cyclone DDS 配置指南
- ✅ RViz 配置更新说明
- ✅ 地图质量分析使用指南
- ✅ RTAB-Map Database Viewer 使用指南
- ✅ 地图查看工具对比

#### 工具脚本
- ✅ `analyze_map_quality.py` - 地图质量分析工具

### 改进

#### 安全性
- 🔒 移除硬编码的相机密钥，使用配置文件管理
- 🔒 添加配置文件权限控制

#### 可维护性
- 📝 添加完整的日志记录系统
- 📝 添加异常处理和错误提示
- 📝 代码注释和文档完善

#### 性能
- ⚡ 优化 RViz 配置，减少资源占用
- ⚡ 改进 Cyclone DDS 配置，降低延迟

### 测试

#### ROS2 Jazzy 升级测试
- ✅ Factor Perception 完全兼容（VIO 200Hz）
- ✅ RTAB-Map SLAM 正常运行
- ✅ Nav2 导航栈成功启动
- ✅ Cyclone DDS 配置正确

#### 地图质量分析
- ✅ 地图质量评分系统验证
- ✅ 问题诊断功能测试
- ✅ 改进建议生成测试

### 兼容性

#### 系统要求
- Ubuntu 24.04 LTS (Noble)
- ROS2 Jazzy
- Python 3.12+
- PyYAML (新增依赖)

#### 硬件支持
- ✅ OAK-D Pro 相机
- ✅ x86_64 平台

### 已知问题

1. **地图质量分析**
   - 大地图（>200MB）加载时间较长
   - 建议：添加加载进度提示

2. **RViz 配置**
   - 3D 显示可能消耗较多资源
   - 建议：根据硬件调整显示密度

### 升级指南

#### 从旧版本升级

1. **更新代码**
   ```bash
   cd /home/yq/nav24r
   git pull
   ```

2. **安装新依赖**
   ```bash
   pip3 install pyyaml
   ```

3. **更新配置**
   ```bash
   # 编辑配置文件
   nano /home/yq/nav24r/config/factor_perception_config.yaml

   # 更新相机密钥（如果需要）
   ```

4. **重启控制面板**
   ```bash
   python3 /home/yq/nav24r/scripts/factor_control_panel.py
   ```

#### Cyclone DDS 配置

```bash
# 设置环境变量
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/yq/nav24r/config/cyclonedds.xml

# 添加到 bashrc
echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc
echo "export CYCLONEDDS_URI=file:///home/yq/nav24r/config/cyclonedds.xml" >> ~/.bashrc
```

### 下一步计划

- [ ] 添加单元测试
- [ ] 性能基准测试
- [ ] 多机器人支持

---

## 2026-06-08 - 初始版本

### 新增功能
- ✅ Factor Perception 控制面板
- ✅ Nav2 导航配置
- ✅ RTAB-Map 3D Octomap
- ✅ 地图管理功能
- ✅ 桌面快捷方式

---

**维护者**: Claude (执行官)
**版本**: v2.0.0
**最后更新**: 2026-06-19