# 变更日志

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