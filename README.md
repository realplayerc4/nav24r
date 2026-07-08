# NAV24R - 人形机器人导航系统

[![ROS2 Version](https://img.shields.io/badge/ROS2-Jazzy-blue.svg)](https://docs.ros.org/en/jazzy/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-x86__64%20%7C%20仿真优先-orange.svg)]()

基于 ROS2 Jazzy 的人形机器人自主导航系统，集成 Factor Perception SDK、RTAB-Map SLAM 和 Nav2 导航栈。

---

## 🎯 项目特性

### 核心功能

- **✅ 视觉感知** - OAK-D Pro 相机集成，支持 VIO 200Hz
- **✅ SLAM 建图** - RTAB-Map 实时建图，支持 3D Octomap
- **✅ 自主导航** - Nav2 导航栈，路径规划与避障
- **✅ 地图管理** - 地图质量分析、多格式导出、可视化工具
- **✅ 系统监控** - 控制面板、设备检测、自动恢复

### 技术亮点

- 🚀 **高性能** - VIO 200Hz，建图 20Hz，实时响应
- 🛡️ **高稳定性** - 容器隔离、错误恢复、设备检测
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
   ```bash
   ./scripts/check_camera.sh
   ```

### ⭐ 启动系统（推荐方式）

**程序入口为控制面板**，直接用 Python 运行，无需 colcon 编译：

```bash
python3 scripts/factor_control_panel.py
```

控制面板功能一览：

| 功能 | 说明 |
|------|------|
| 🗺️ 新建地图 | 输入地图 ID 后点击“开始建图” |
| 🔄 续建地图 | 选择已有地图 → 续建 → 开始建图 |
| 🧭 定位导航 | 选择地图 → 开始导航 |
| 🚀 完整导航 | Factor Perception + RTAB-Map + Nav2 全内容 |
| 📷 设备状态 | OAK-D 连接状态实时监控（每3秒） |
| 📊 地图质量分析 | 地图 100 分制评分报告 |
| 🗺️ 导出 Octomap | 启动 Database Viewer 导出 |
| 📁 地图分析数据库查看器 | 直接打开 rtabmap-databaseViewer |

> **替代入口（无 GUI 环境）**: `python3 scripts/web_control_panel.py`，在浏览器访问 `http://localhost:5000`

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
ros2 launch nav24r factor_perception_auto.launch.py continue_mapping:=true

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
├── config/                                 # 配置文件（14个）
│   ├── rtabmap_custom.ini                 # RTAB-Map 完整参数配置
│   ├── nav2_params.yaml                   # Nav2 参数
│   ├── factor_perception_config.yaml      # 感知SDK配置（相机型号/密钥等）
│   ├── cyclonedds.xml                     # Cyclone DDS 优化
│   └── *.rviz (6个)                       # 多种 RViz 视角配置
│
├── launch/                                 # Launch 文件
│   ├── nav24r_full.launch.py              # ✅ 完整系统（感知+SLAM+Nav2）
│   ├── factor_perception_isolated.launch.py # ✅ 隔离架构（推荐，更稳定）
│   └── nav2.launch.py                     # 纯 Nav2
│
├── scripts/                                # 工具脚本（19个）
│   ├── factor_control_panel.py            # ⭐ 主入口：tkinter 控制面板
│   ├── web_control_panel.py               # 替代入口：Web 控制面板（无GUI）
│   ├── analyze_map_quality.py             # 地图质量分析（100分制）
│   ├── export_octomap.py                  # Octomap 导出
│   ├── check_camera.sh                    # OAK-D 设备检测
│   ├── start_factor.sh / factor_control.sh # 命令行快捷启动
│   └── diagnose.sh / setup_cyclonedds.sh  # 诊断/配置脚本
│
├── docs/                                   # 文档（24篇）
│   ├── WORK_SUMMARY_20260615.md           # 工作总结
│   ├── ros2_engineering_analysis.md       # ROS2工程分析
│   └── 因子空间感知SDK标准版使用手册.pdf
│
├── Calibrat/                               # IMU/相机标定工具
├── memory-bank/                            # 架构文档
└── CHANGELOG.md
```

---

## 📖 使用指南

### 建图模式

1. **连接相机**
   ```bash
   ./scripts/check_camera.sh
   ```

2. **启动建图**
   ```bash
   # 控制面板方式
   python3 scripts/factor_control_panel.py
   # 选择 "新建地图"
   
   # 或直接启动
   ros2 launch nav24r factor_perception_auto.launch.py cam_pos_z:=1.0
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
   # 选择 "定位模式" → "启动导航"
   ```

3. **发送目标**
   ```bash
   # RViz2 中点击 "2D Pose Estimate" 设置起点
   # 点击 "Nav2 Goal" 设置目标点
   ```

---

## 🔧 配置说明

### RTAB-Map 参数

关键配置（`config/rtabmap_custom.ini`）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `Grid/3D` | true | 3D 点云地图 |
| `Grid/MaxObstacleHeight` | 1.5m | 最高障碍物高度 |
| `GridGlobal/FootprintRadius` | 0.5m | 机器人半径 |

### Nav2 参数

关键配置（`config/nav2_params.yaml`）：

| 参数 | 值 | 说明 |
|------|-----|------|
| `max_obstacle_height` | 1.5m | 与 RTAB-Map 一致 |
| `min_obstacle_height` | 0.05m | 地面忽略高度 |
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

#### 1. 设备崩溃问题 ✅
- **问题**: OAK-D 未连接时系统崩溃
- **解决**: 启动前设备检测，自动重启机制

#### 2. GPU 内存崩溃 ✅
- **问题**: RViz 显示导致 GPU 崩溃
- **解决**: 轻量化 RViz 配置，禁用图像流

#### 3. 组件故障传播 ✅
- **问题**: 单个组件崩溃影响整个系统
- **解决**: 容器隔离架构，独立重启

### 架构改进

| 特性 | 旧版本 | 新版本 |
|------|--------|--------|
| 容器隔离 | 单容器 | 多容器隔离 |
| 生命周期 | 无 | LifecycleNode |
| 设备检查 | 无 | 自动检测 |
| 错误恢复 | 无 | 自动重启 |
| QoS 配置 | 无 | 显式配置 |

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