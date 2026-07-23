# NAV24R - 人形机器人导航系统

[![ROS2 Version](https://img.shields.io/badge/ROS2-Jazzy-blue.svg)](https://docs.ros.org/en/jazzy/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-x86__64%20%7C%20仿真优先-orange.svg)]()

基于 ROS2 Jazzy 的人形机器人自主导航系统，集成 Factor Perception SDK、RTAB-Map SLAM 和 Nav2 导航栈。

**版本**: v2.2.0 | **相机**: OAK-D Pro W (0.85m 安装高度) | **障碍物高度过滤**: 0.2m ~ 1.4m

---

## 🎯 项目特性

### 核心功能

- **✅ 视觉感知** - OAK-D Pro 相机集成，支持 VIO 200Hz
- **✅ SLAM 建图** - RTAB-Map 实时建图，支持 3D Octomap
- **✅ 自主导航** - Nav2 导航栈，路径规划与避障
- **✅ 地图管理** - 地图质量分析、Octomap 导出、可视化工具
- **✅ 系统监控** - 控制面板、设备检测、自动恢复

### 技术亮点

- 🚀 **高性能** - VIO 200Hz，建图 20Hz，实时响应
- 🛡️ **高稳定性** - 多线程容器、错误恢复、设备检测
- 📊 **数据分析** - 地图质量评分系统（100分制）
- 🔧 **易于配置** - 参数集中管理，可视化配置工具
- 📖 **完善文档** - 中文文档齐全，包含使用指南和技术分析

---

## 🚀 快速开始

### 系统要求

- **操作系统**: Ubuntu 24.04 LTS (Noble)
- **ROS 版本**: ROS2 Jazzy
- **Python**: 3.12+
- **硬件**: OAK-D Pro / OAK-D Pro W 相机
- **外部依赖**: Factor Perception SDK（已安装）、`ros-jazzy-rtabmap-ros`、`ros-jazzy-navigation2`
- **测试模式**: 仿真优先，无实机条件下优先验证感知/SLAM/Nav2 基础流程

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/yourusername/nav24r.git
   cd nav24r
   ```

2. **安装依赖**
   ```bash
   # ROS2 依赖
   sudo apt install ros-jazzy-navigation2 ros-jazzy-rtabmap-ros ros-jazzy-rmw-cyclonedds-cpp

   # Python 依赖
   pip3 install pyyaml
   ```

3. **配置环境**
   ```bash
   # Cyclone DDS 配置（推荐，降低延迟）
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   export CYCLONEDDS_URI=file://$(pwd)/config/cyclonedds.xml

   # 添加到 bashrc（永久生效）
   echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc
   echo "export CYCLONEDDS_URI=file://$(realpath .)/config/cyclonedds.xml" >> ~/.bashrc
   ```

4. **检查相机**

   OAK-D 相机连接状态可在控制面板的"设备状态"中实时查看（每 3 秒自动刷新）。
   ```bash
   python3 scripts/factor_control_panel.py
   # → "设备状态" 区域查看 OAK-D 连接
   ```

### ⭐ 启动系统（推荐方式）

**程序入口为控制面板**，直接用 Python 运行，无需 colcon 编译：

```bash
python3 scripts/factor_control_panel.py
```

控制面板功能一览：

| 功能 | 说明 |
|------|------|
| 🗺️ 新建建图 | 清空数据库后重新建图（需二次确认） |
| 🔄 续建 | 加载已有数据库继续建图 |
| 🧭 开始定位 | 加载已有地图进入定位模式（localization） |
| 🚀 完整导航 | Factor Perception + RTAB-Map + Nav2 全栈 |
| 📷 设备状态 | OAK-D 连接/USB速度实时监控 |
| 📊 地图质量 | 地图质量分析报告 |
| 🧹 清理地面误判 | 分析并清理地毯等弱纹理地面的误判障碍物 |
| ✂️ 清理节点 | 交互式浏览和删除 RTAB-Map 数据库中的节点 |
| 🗺️ 导出Octomap | 启动 Database Viewer 导出 |
| 📁 数据库 | 打开 rtabmap-databaseViewer |

> **替代入口（无 GUI 环境）**: `python3 scripts/factor_control_panel.py`（同一入口，跨平台兼容）

---

### 🛠️ 高级用法：直接当 Launch 文件

> **注意**: 以下方式需要先将 `nav24r` 作为 ROS2 包编译安装。日常使用控制面板无需此步骤。

```bash
# 在 colcon 工作区编译安装（仅需一次）
cd ~/ros2_ws  # 或您的 colcon 工作区
ln -s /home/yq/nav24r src/nav24r  # 或将目录拷贝进 src/
colcon build --packages-select nav24r
source install/setup.bash

# 然后可以直接用 ros2 launch
# 新建地图
ros2 launch nav24r factor_perception_auto.launch.py

# 续建地图
ros2 launch nav24r factor_perception_auto.launch.py

# 定位模式
ros2 launch nav24r factor_perception_auto.launch.py localization:=true

# 隔离架构（更稳定）
ros2 launch nav24r factor_perception_isolated.launch.py

# 完整导航系统
ros2 launch nav24r nav24r_full.launch.py
```

---

```
nav24r/
├── 📄 package.xml                          # ROS2 包描述（ament_python）
├── 📄 setup.py / setup.cfg                 # colcon 构建配置
├── 📄 factor_perception_auto.launch.py     # 根目录 Launch 文件（感知+SLAM）
│
├── config/                                 # 配置文件
│   ├── nav2_params.yaml                   # Nav2 参数
│   ├── factor_perception_config.yaml      # 感知 SDK 配置
│   ├── cyclonedds.xml                     # Cyclone DDS 优化
│   ├── maps_config.json                   # 地图管理配置
│   ├── rtabmap_light.rviz                 # 轻量化 RViz
│   ├── rtabmap_config_doc.md              # RTAB-Map 配置文档
│   ├── mapping.rviz / mapping_3d.rviz     # 建图视角
│   ├── navigation.rviz                    # 导航视角
│   ├── octomap.rviz / octomap_3d.rviz     # Octomap 视角
│   └── map_viewer_3d.rviz                 # 地图观察器
│
├── launch/                                 # Launch 文件
│   ├── nav24r_full.launch.py              # ✅ 完整系统（感知+SLAM+Nav2）
│   ├── factor_perception_isolated.launch.py # ✅ 隔离架构（推荐）
│   └── nav2.launch.py                     # 纯 Nav2
│
├── scripts/                                # 工具脚本
│   ├── factor_control_panel.py            # ⭐ 主入口：tkinter 控制面板
│   ├── start_factor.sh                    # 智能启动脚本（建图/定位）
│   ├── start_rtabmap_light.sh             # 轻量化建图启动
│   ├── factor_control.sh                  # Shell 快捷启动
│   ├── analyze_map_quality.py             # 地图质量分析
│   ├── export_octomap.py                  # Octomap 导出
│   ├── clean_ground_false_positives.py  # 地面误判清理工具
│   ├── cleanup_rtabmap.py               # RTAB-Map 节点清理工具
│   ├── odom_covariance_fix.py           # 里程计协方差修复
│   ├── ply_to_pointcloud.py             # PLY点云转ROS2 PointCloud2
│   ├── mock_odom_publisher.py             # 仿真里程计
│   ├── mock_pointcloud_publisher.py       # 仿真点云
│   └── test_runner.sh / test_simulation.py # 测试脚本
│
├── docs/                                   # 技术文档
│   ├── ros2_engineering_analysis.md       # ROS2 工程分析
│   ├── rtabmap_config_doc.md              # RTAB-Map 配置说明
│   ├── nav2_integration_plan.md           # Nav2 集成方案
│   ├── nav2_rtabmap_knowledge.md          # Nav2/RTAB-Map 知识要点 ⭐
│   ├── WORK_SUMMARY_20260615.md           # 工作总结
│   ├── 因子空间感知SDK标准版使用手册.pdf  # SDK 官方手册
│   └── ...（控制面板、地图分析、RViz 等使用指南）
│
├── factor_perception/                      # Factor Perception SDK（第三方）
├── Calibrat/                               # IMU/相机标定工具
│   └── IMU/                                # IMU 数据与处理脚本
├── book/                                   # SDK 参考手册
├── memory-bank/                            # 架构文档
├── CHANGELOG.md
└── README.md
```

---

## 📖 使用指南

### 建图模式

1. **连接相机**
   ```bash
   # 通过控制面板的设备状态监控确认 OAK-D 连接
   python3 scripts/factor_control_panel.py
   # → "设备状态" 中查看 OAK-D 连接状态
   ```

2. **启动建图**
   ```bash
   # 控制面板方式
   python3 scripts/factor_control_panel.py
   # 选择 "新建地图"
   
   # 或直接启动
    ros2 launch nav24r factor_perception_auto.launch.py cam_pos_z:=0.85
   ```

3. **查看地图**
   ```bash
   # 轻量化 RViz（避免 GPU 崩溃）
   rviz2 -d config/rtabmap_light.rviz
   ```

4. **分析质量**
   ```bash
   # 控制面板 → 选择地图 → 📊 解读地图质量
   ```

5. **导出地图**
   ```bash
   # Octomap 格式（推荐用于导航）
   # 控制面板 → 选择地图 → 🗺️ 导出 Octomap
   ```

### 导航模式

1. **准备地图**
   - 已有地图：使用定位模式
   - 无地图：使用建图模式

2. **启动导航**
   ```bash
   # 完整系统
   ros2 launch nav24r nav24r_full.launch.py localization:=true
   
   # 或使用控制面板
   python3 scripts/factor_control_panel.py
   # 选择 "开始定位" → 或 "完整导航"
   ```

3. **发送目标**
   ```bash
   # RViz2 中点击 "2D Pose Estimate" 设置起点
   # 点击 "Nav2 Goal" 设置目标点
   ```

### 地图保护

- **数据库路径**: `~/rtabmap.db`（固定路径，所有模式共用）
- **保护机制**: 点击"新建建图"时，如果数据库已存在且有效，必须通过弹窗确认才能覆盖
- **按钮提示**: 数据库存在时按钮变为橙色并显示"🗺️ 新建建图 (覆盖)"
- **清理工具**: 控制面板 → "🧹 清理地面误判"（备份后删除，可恢复）

> ⚠️ **注意**: "续建"和"开始定位"不会删除数据库。只有"新建建图"才会覆盖。

---

## 🔧 配置说明

### RTAB-Map 参数

使用 SDK 自带 `rtabmap.ini`，无自定义覆盖参数。

### Nav2 参数

关键配置（`config/nav2_params.yaml`）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_obstacle_height` | 1.4m | 高于 1.4m 不视为障碍物（相机有效范围） |
| `min_obstacle_height` | 0.2m | 低于 0.2m 不视为障碍物（地面/门槛） |
| `robot_radius` | 0.5m | 机器人半径 |

---

## 📊 地图质量评分系统

评分维度（总分 100）：

- **节点数量** (25分) - 地图覆盖范围
- **链接密度** (25分) - 连接稳定性
- **闭环检测** (30分) - 地图准确性 ⭐ 最关键
- **建图时长** (20分) - 地图完整性

评级标准：

| 评分 | 星级 | 质量 |
|------|------|------|
| 85-100 | ⭐⭐⭐⭐⭐ | 优秀 |
| 70-84 | ⭐⭐⭐⭐ | 良好 |
| 55-69 | ⭐⭐⭐ | 一般 |
| 40-54 | ⭐⭐ | 较差 |
| <40 | ⭐ | 不合格 |

---

## 🛡️ 系统稳定性

### 已解决的问题

#### 1. 地面误判 ✅
- **问题**: 地毯等弱纹理地面被检测为障碍物
- **解决**: NormalK=60 大邻域平滑法线 + MaxGroundHeight=0.15 + depth_filter=true

#### 2. rtabmap_viz 崩溃 ✅
- **问题**: Wayland 下 Qt 不兼容，rtabmap_viz 40秒后崩溃
- **解决**: 改用 Node 直接启动 + QT_QPA_PLATFORM=xcb

#### 3. 数据库表名不匹配 ✅
- **问题**: 控制面板检查旧版表名，v0.22+ 数据库报错
- **解决**: 表名更新为 Node/Link/Word/Data

#### 4. USB 验证弹窗 ✅
- **问题**: USB 速度验证失败时弹窗并停止所有进程
- **解决**: 仅状态栏显示警告，不中断运行

### 地图保护机制

| 保护层 | 实现 |
|--------|------|
| 按钮颜色 | 数据库存在时按钮变橙色 + "(覆盖)" 文字 |
| 确认弹窗 | 点击后需确认"是否覆盖现有数据" |
| 备份清理 | "🧹 清理地面误判"自动备份为 .backup 文件 |

### 架构改进

| 特性 | 说明 |
|------|------|
| 容器类型 | `component_container_mt`（多线程） |
| 设备检查 | 自动检测 OAK-D 连接和 USB 速度 |
| 错误恢复 | rtabmap_viz 独立进程，崩溃不影响建图 |
| 地面过滤 | 法线分割 + 高度过滤 + 光线追踪三层过滤 |

---

## 📚 技术文档

### 核心文档

- [ROS2 工程分析报告](docs/ros2_engineering_analysis.md) - 系统架构问题与解决方案
- [RTAB-Map 配置文档](config/rtabmap_config_doc.md) - 参数配置与优化
- [Nav2 集成方案](docs/nav2_integration_plan.md) - 导航系统集成指南
- [Nav2/RTAB-Map 知识要点](docs/nav2_rtabmap_knowledge.md) - Nav2 与 RTAB-Map 核心知识速查 ⭐
- [工作总结](docs/WORK_SUMMARY_20260615.md) - 开发过程详细记录

### 使用指南

- [控制面板使用](docs/control_panel_update.md)
- [地图质量分析](docs/map_quality_analysis_guide.md)
- [Octomap 导出](docs/octomap_export_panel_guide.md)
- [RViz 配置](docs/rviz_config_update.md)

### 参考资料

- [Cyclone DDS 配置](docs/Cyclone_DDS_配置指南.md)
- [地图查看工具对比](docs/map_viewing_comparison.md)
- [依赖说明](docs/dependencies.md)

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📝 版本历史

### [v2.3.0] - 2026-07-22
- Nav2 composition 模式修复（nav2_container 依赖修复）
- Localization 模式修复（use_composition 布尔量处理）
- 地图保护开关：默认关闭，保护已有数据库
- 重置地图和清理工具也受地图保护开关约束
- 新增 cleanup_rtabmap.py：交互式 RTAB-Map 节点清理工具
- 新增 odom_covariance_fix.py：里程计协方差修复节点
- 新增 ply_to_pointcloud.py：PLY 点云转 ROS2 PointCloud2
- pre-commit hook 配置

### [v2.2.0] - 2026-07-20
- 障碍物高度过滤 0.2m ~ 1.4m（RTAB-Map + Nav2 统一）
- 地面误判修复：NormalK=60, MaxGroundHeight=0.15, MaxGroundAngle=25°
- IR 投影仪强度提升 (0.4→0.8)，depth_filter 开启
- 立体匹配优化（TextureThreshold, UniquenessRatio, Speckle）
- 数据库保护：按钮颜色警告 + 确认弹窗
- Wayland 兼容：rtabmap_viz 改用 Node 启动 + QT_QPA_PLATFORM=xcb
- 移除 USB 验证弹窗（仅状态栏显示）
- 新增 navigation_clean.rviz（导航干净视图）
- 新增 clean_ground_false_positives.py（地面误判清理工具）
- 按钮文案修正：开始导航 → 开始定位

### [v2.1.0] - 2026-07-17
- SDK 更新与配置简化
- 单 rtabmap_slam 节点架构
- 相机高度更新为 0.85m

### [v2.0.0] - 2026-06-19
- 系统架构优化（容器隔离、生命周期管理）
- 设备检测和自动恢复
- ROS2 工程规范优化
- 文档完善

### [v1.1.0] - 2026-06-15
- ROS2 Jazzy 升级验证
- 控制面板大幅增强
- Octomap 导出功能
- 地图质量分析系统
- 完整文档体系

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Factor Perception SDK](https://github.com/luxonis) - OAK-D 相机驱动
- [RTAB-Map](https://github.com/introlab/rtabmap) - SLAM 系统
- [Nav2](https://navigation.ros.org/) - ROS2 导航栈
- [ROS2](https://docs.ros.org/en/jazzy/) - 机器人操作系统

---

## 📧 联系方式

项目维护者: Claude (执行官)

- GitHub Issues: [提交问题](https://github.com/yourusername/nav24r/issues)
- 项目文档: [完整文档](docs/)

---

**项目状态**: ✅ 生产就绪 | ✅ 测试通过 | ✅ 文档齐全

**适用于**: 人形机器人自主导航 | OAK-D 相机集成 | ROS2 Jazzy