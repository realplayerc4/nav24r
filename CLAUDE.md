#!/usr/bin/env python3
"""
CLAUDE.md - nav24r 项目特定指南

基于 Karpathy 编码原则，为 nav24r ROS 2 项目定制的最佳实践。
全局准则（/home/yq/.claude/CLAUDE.md）也适用于本项目。
"""

# ============================================================
# nav24r 项目特定指南
# ============================================================

## 项目概述

**名称：** nav24r（人形机器人自主导航系统）
**版本：** 2.7.4
**技术栈：** ROS 2 Jazzy + Python 3.12 + Factor Perception SDK + RTAB-Map + Nav2
**构建系统：** ament_python
**许可证：** MIT

**项目状态：** 建图、修图、定位、导航全流程已测试通过，生产就绪。

---

## 编码风格

### Python 规则

- **版本：** Python 3.12+
- **格式化：** 遵循 PEP 8
- **导入顺序：** 标准库 → ROS 2 → 第三方 → 本地模块
- **字符串引号：** 单引号（除非包含单引号）
- **类型提示：** 鼓励但不强制
- **文档字符串：** Google 风格（简短而实用）

### Shell 脚本规则

- **Shebang：** `#!/bin/bash`
- **严格模式：** 始终使用 `set -euo pipefail`
- **缩进：** 2 空格（不使用 tab）
- **函数命名：** 小写+下划线（`snake_case`）
- **变量：** 大写常量，小写+下划线变量

### YAML 配置规则

- **缩进：** 2 空格
- **布尔值：** 使用 `true/false` 而非 `True/False`
- **字符串引号：** 必要时使用引号，避免歧义
- **注释：** 使用 `#`，说明"为什么"而非"是什么"

### JSON 配置规则

- **缩进：** 2 空格
- **引号：** 双引号（JSON 标准）
- **尾部逗号：** 不允许

---

## ROS 2 约定

### 命名规范

- **包名：** 小写+下划线（`nav24r`）
- **节点名：** 小写+下划线（`factor_perception_node`）
- **话题名：** 小写+下划线（`/factor_perception/odom`）
- **TF 坐标系：** `base_link`, `odom`, `map`, `camera_link`, `oak`

### 关键参数

- **相机高度：** `cam_pos_z:=0.85`（OAK-D Pro W 安装高度）
- **障碍物高度过滤：** 0.2m ~ 1.4m（RTAB-Map + Nav2 统一）
- **默认数据库：** `~/rtabmap.db`（所有模式共用）
- **IR 投影仪强度：** `ir_intensity:=0.8`
- **depth_filter：** `true`

---

## 项目结构

```
nav24r/
├── factor_perception_auto.launch.py  # 根目录 Launch（感知+SLAM，主入口）
├── package.xml                        # ROS 2 包描述（ament_python）
├── setup.py                           # 构建配置
├── README.md / CHANGELOG.md / CLAUDE.md
│
├── config/                            # 配置文件
│   ├── nav2_params.yaml              # 真机 Nav2 参数（RPP 控制器，高度过滤 0.2~1.4m）
│   ├── nav2_params_mock.yaml         # mock 环境参数（RPP，与真机分离）
│   ├── nav2_params_mppi_backup.yaml  # MPPI 配置备份（可切回）
│   ├── factor_perception_config.yaml # 感知 SDK 配置
│   ├── rtabmap.ini                   # RTAB-Map 参数（SDK 自带）
│   ├── cyclonedds.xml                # Cyclone DDS 优化
│   ├── maps_config.json              # 地图管理配置
│   ├── mapping.rviz / mapping_3d.rviz
│   ├── navigation.rviz / navigation_clean.rviz
│   ├── octomap.rviz / octomap_3d.rviz
│   ├── map_viewer_3d.rviz
│   └── rtabmap_light.rviz
│
├── launch/                            # Launch 文件
│   ├── nav24r_full.launch.py         # 完整系统（感知+SLAM+Nav2）
│   ├── factor_perception_isolated.launch.py  # 隔离架构
│   ├── nav2.launch.py                # 纯 Nav2
│   ├── mock_nav.launch.py            # 🧪 Mock 导航环境（地图+差分模拟器+Nav2）
│   └── simulation/                   # 仿真启动文件
│       └── simulation_nav2.launch.py #   模拟感知数据 + Nav2
│
├── scripts/                           # 工具脚本
│   ├── factor_control_panel.py       # ⭐ 主入口：GUI 控制面板
│   ├── start_factor.sh               # 智能启动脚本（建图/定位）
│   ├── start_rtabmap_light.sh        # 轻量化建图启动
│   ├── factor_control.sh             # Shell 快捷启动
│   ├── analyze_map_quality.py        # 地图质量分析
│   ├── export_octomap.py             # Octomap 导出
│   ├── export_cloud_and_view.py      # 点云导出+RViz查看
│   ├── clean_ground_false_positives.py  # 地面误判清理
│   ├── cleanup_rtabmap.py            # RTAB-Map 节点清理工具
│   ├── odom_covariance_fix.py        # 里程计协方差修复
│   ├── ply_to_pointcloud.py          # PLY点云转ROS2 PointCloud2
│   ├── mock_odom_publisher.py        # 仿真里程计
│   ├── mock_pointcloud_publisher.py  # 仿真点云
│   ├── mock_map_publisher.py         # 空白地图发布器（global_costmap 用）
│   ├── mock_robot.py                 # 差分驱动模拟器（cmd_vel → odom+TF）
│   ├── generate_test_map.py          # 生成测试地图 YAML
│   ├── t1_bridge.py                 # Nav2 → T1 速度桥接节点（纯 Python，subprocess 取 cmd_vel）
│   ├── cancel_nav2_goal.py          # 停止 Nav2 导航（抢占目标，停止按钮调用）
│   ├── mock_trajectory_publisher.py # Mock 轨迹测试 (t1_bridge → SDK)
│   ├── test_nav2_goal.py             # Nav2 输出观察器（验证 cmd_vel）
│   ├── test_t1_sdk.py               # T1 SDK 连通性测试
│   ├── test_runner.sh / test_simulation.py  # 测试框架
│   └── test_phase*.sh               # 分阶段测试脚本
│
├── factor_perception/                 # Factor Perception SDK（第三方）
├── Calibrat/                          # IMU/相机标定工具
│   └── IMU/
├── docs/                              # 技术文档
└── book/                              # SDK 参考手册
└── slambAK/                           # 旧版系统（曾稳定控制机器人）
    ├── boosterxjw/                    # C++ Nav2→T1 桥接节点（生产验证）
    ├── factor_perception/             # 旧版感知 SDK
    └── slam文档.txt                   # 旧系统启动流程记录
```

---

## 关键配置

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `FACTOR_PERCEPTION_KEY` | Factor Perception SDK 密钥 | `export FACTOR_PERCEPTION_KEY=xxx` |
| `ROS_DOMAIN_ID` | ROS 2 域 ID（多机器人隔离） | `export ROS_DOMAIN_ID=42` |
| `RMW_IMPLEMENTATION` | RMW 实现 | `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` |

### 文件路径

- **项目根目录：** `/home/yq/nav24r`
- **配置目录：** `/home/yq/nav24r/config`
- **地图目录：** `~/rtabmap_maps/`
- **默认数据库：** `~/rtabmap.db`
- **日志目录：** `~/.local/share/nav24r/logs/`

### 网络拓扑

```
nav24r 电脑 (192.168.10.103) ──LAN 直连── Robot eth0 (192.168.10.102)
    │                                    │
    │ 电脑侧 ROS2: ROS_DOMAIN_ID=42       │
    │ Nav2/CycloneDDS (隔离，避免冲突)     │
    │                                    FastDDS (domain 0)
    │                                    T1 SDK DDS + ROS2 Humble
```

- 统一接口：`enx207bd2d33010`（USB LAN）
- **domain 隔离**：电脑侧 ROS2 用 `ROS_DOMAIN_ID=42`，机器人 FastDDS 用 domain 0，避免 DDS 冲突（type hash 刷屏、bt_navigator 失败、SDK 干扰 damping）
- 机器人 IP：`192.168.10.102`
- WiFi (`192.168.0.x`) 不使用

---

## 常见任务

### 启动方式

**唯一主入口 — 控制面板：**
```bash
python3 scripts/factor_control_panel.py
```

所有功能通过 GUI 按钮操作：

| 按钮 | 功能 | 说明 |
|------|------|------|
| 地图保护开关 | checkbox | 关闭时保护已有数据库，新建建图需二次确认 |
| 🗺️ 新建建图 | 建图 | 清空数据库后重新建图（受保护开关约束） |
| 🔄 续建 | 建图 | 加载已有数据库继续建图 |
| 🧭 开始定位 | 定位 | 加载已有地图进入 localization 模式 |
| 🚀 完整导航 | 导航 | Factor Perception + RTAB-Map + Nav2 全栈 |
| 🤖 T1 控制 | 机器人 | 模式切换（Prepare/Walking/Damping，Damping 有二次确认）+ 方向键手动操控 |
| 🗑️ 重置地图 | 清理 | 删除数据库（受保护开关约束） |
| ⏹️ 停止 | 停止 | 停止所有 ROS 节点 |
| 📊 RViz / RViz 3D | 可视化 | 2D 顶视角 / 3D 视角 |
| 📁 数据库 | 工具 | rtabmap-databaseViewer |
| 📊 地图质量 | 分析 | 地图质量评分报告 |
| 🗺️ 导出Octomap | 导出 | 启动 Database Viewer 导出 Octomap |
| ☁️ 导出点云+RViz | 导出 | PLY 点云转 ROS2 话题 + RViz 查看 |
| ⚠️ 重置重建地图 | 清理 | 分析并清理地面误判障碍物 |
| ✂️ 清理节点 | 工具 | 交互式删除 RTAB-Map 数据库节点 |
| 🧪 测试报告 | 测试 | 运行测试框架并生成报告 |
| 📋 查看日志 | 调试 | 查看控制面板日志 |

**设备操作：**
- ☑️ 自动检测 — 每 3 秒自动刷新 OAK-D 连接状态
- 🔄 重启相机 — 软重启相机进程
- ⚡ 强制重连 — 停止进程 + 重置 USB

**无 GUI 环境替代方案：**
```bash
# 建图
ros2 launch nav24r factor_perception_auto.launch.py cam_pos_z:=0.85

# 定位
ros2 launch nav24r factor_perception_auto.launch.py localization:=true db_path:=~/rtabmap.db

# 完整导航
ros2 launch nav24r nav24r_full.launch.py localization:=true

# T1 双足机器人导航（LAN 直连）
ros2 launch nav24r nav24r_full.launch.py localization:=true use_t1_bridge:=true

# T1 SDK 连通性测试
python3 scripts/test_t1_sdk.py

# 🧪 Mock 仿真环境（无实机测试 Nav2）
ros2 launch nav24r simulation/simulation_nav2.launch.py
# 或使用真实测试地图 + 差分模拟器
python3 scripts/generate_test_map.py
ros2 launch nav24r mock_nav.launch.py

# 🧪 T1 桥接转发测试
ros2 run nav24r t1_bridge
python3 scripts/mock_trajectory_publisher.py
```

---

## 依赖管理

### ROS 2 依赖（package.xml）

- rclpy, robot_state_publisher, robot_localization
- rtabmap_slam, depth_image_proc
- nav2_bringup, nav2_mppi_controller
- sensor_msgs, nav_msgs, tf2_ros

### Python 依赖（pip）

- pyyaml, numpy, opencv-python (headless)

---

## 注意事项

### ✅ 允许的修改

- **launch 文件**：添加/修改参数、节点、包含文件
- **config 文件**：调整参数（Nav2、RTAB-Map、RViz）
- **scripts/**：修改控制脚本（启动、建图、导航、分析）
- **README.md**：更新文档和快速启动指南

### ⚠️ 谨慎修改

- **factor_perception/**：第三方 SDK，仅在确认必要时修改
- **Calibrat/**：IMU 校准工具，确保不影响机器人坐标系

### ❌ 不要修改

- **install/**：自动生成，由 ament 维护
- **build/**：构建产物
- **__pycache__/**：Python 缓存

---

## 调试技巧

```bash
# 查看所有话题 / 节点 / 服务
ros2 topic list && ros2 node list && ros2 service list

# 回放话题
ros2 topic echo /factor_perception/odom

# TF 树可视化
ros2 run tf2_tools view_frames

# 日志
ros2 run rqt_console rqt_console
# 控制面板日志：~/.local/share/nav24r/logs/factor_control_panel.log
```

---

## 测试建议

### 手动测试清单

- [ ] Launch 文件语法正确：`ros2 launch --show-args <file>`
- [ ] 所有节点启动成功（无错误）
- [ ] 话题数据流正常（`ros2 topic echo`）
- [ ] TF 树完整（`ros2 run tf2_tools view_frames`）
- [ ] Nav2 能接收目标点（`ros2 action send_goal`）
- [ ] RTAB-Map 能生成地图
- [ ] 控制面板各按钮功能正常

---

## 贡献者须知

### 提交前检查

- [ ] 只修改与任务相关的文件
- [ ] 遵循现有代码风格（PEP 8、2 空格缩进等）
- [ ] 添加/更新必要的注释（说明"为什么"）
- [ ] 更新相关文档（README、CHANGELOG）
- [ ] 测试 launch 文件语法
- [ ] 验证关键参数更改

---

## 资源链接

- **ROS 2 文档：** https://docs.ros.org/en/jazzy/
- **Nav2 文档：** https://navigation.ros.org/
- **RTAB-Map Wiki：** https://github.com/introlab/rtabmap/wiki
- **项目 README：** `/home/yq/nav24r/README.md`

---

*最后更新：2026-07-22*
*全局准则：~/.claude/CLAUDE.md（Karpathy 编码原则）*
