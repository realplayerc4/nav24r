# RTAB-Map 配置文档

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v2.1 | 2026-06-18 | 基于Factor Perception SDK默认配置 + 3D避障 |
| v2.2 | 2026-06-18 | 添加ROS2工程分析、设备检测、控制面板更新 |
| v3.0 | 2026-07-17 | 移除3D避障自定义，采用SDK默认 rtabmap.ini；相机高度更新为 0.85m；关闭 depth_filter；单 rtabmap_slam 节点 |
| v3.1 | 2026-07-20 | 添加 RGBD/ProximityBySpace 和 RGBD/ProximityByTime 参数（修复续建地图关联问题）；更新文档匹配 SDK v1.5.1 |

---

## 最新更新 (2026-06-18)

### 新增文件

| 文件 | 说明 |
|------|------|
| `launch/factor_perception_isolated.launch.py` | 隔离架构 + 错误恢复 |
| `scripts/check_camera.sh` | 设备检测脚本 |
| `scripts/factor_control_panel.py` | 更新：设备检测 + 相机重启 |
| `config/rtabmap_light.rviz` | 轻量化RViz配置（含3D+Octomap） |
| `docs/ros2_engineering_analysis.md` | ROS2工程问题分析报告 |

### 主要改进

1. **设备检测功能** - 控制面板实时监控 OAK-D 连接状态
2. **相机重启功能** - 软重启和强制重连
3. **容器隔离架构** - 硬件驱动与SLAM分离
4. **错误恢复机制** - 崩溃后自动重启

---

## 配置来源

基于 Factor Perception SDK 默认配置修改：
- 源文件: `/opt/ros/jazzy/share/factor_perception/config/rtabmap.ini`

---

## 机器人参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 相机高度 | 0.85m | OAK-D Pro 安装高度 |
| 机器人最高点 | ≤1.4m | 机器人本体最高高度 |
| 机器人半径 | 0.5m | 用于 footprint 计算 |

---

## 障碍物检测范围

| 参数 | 值 | 说明 |
|------|-----|------|
| `min_obstacle_height` | 0.05m | 低于此高度不检测（避免地面误判） |
| `max_obstacle_height` | 1.5m | 高于此高度不检测（天花板/门框上方） |
| 有效检测范围 | 0.05m ~ 1.5m | 地面和天花板不计入障碍物 |

### 工作原理示意

```
高度 (m)     检测状态
─────────────────────────
  0.00       地面 ✓ 可通行
  0.05       ─── min_obstacle_height
  0.10       小障碍物 ✗ 需避障
  0.50       桌面障碍物 ✗ 需避障
  1.00       相机高度
  1.40       机器人最高点
  1.50       ─── max_obstacle_height
  2.00       门框下沿 ✓ 可通行
  2.50+      天花板 ✓ 可通行
```

---

## 关键配置修改

### 相比SDK默认值的修改

| 参数 | SDK默认 | 修改值 | 说明 |
|------|---------|--------|------|
| `cam_pos_z` | 0.0m | **0.85m** | 相机实际安装高度 |
| `depth_filter` | false | **false** | 保持默认关闭 |
| `ir_intensity` | 0.0 | **0.4** | 改善室内 VIO 稳定性 |
| `publish_tf` | true | **true** | 保持默认（单传感器导航） |
| `RGBD/ProximityBySpace` | false | **true** | 空间 proximity 检测（续建地图必需） |
| `RGBD/ProximityByTime` | false | **true** | 时间 proximity 检测（续建地图必需） |
| `Mem/IncrementalMemory` | true | **true** | 增量记忆（新建+续建） |
| `Mem/InitWMWithAllNodes` | false | **false**(建图) / **true**(定位) | 是否加载所有历史节点到工作内存 |
| `RGBD/ProximityBySpace` | false | **true** | 空间 proximity 检测（续建地图必需） |
| `RGBD/ProximityByTime` | false | **true** | 时间 proximity 检测（续建地图必需） |

---

## Nav2 配置同步

RTAB-Map 参数与 Nav2 配置 (`config/nav2_params.yaml`) 保持一致：

| 参数 | RTAB-Map | Nav2 | 说明 |
|------|----------|------|------|
| max_obstacle_height | 1.0m (SDK默认) | 1.5m | Nav2 costmap 限制 |
| min_obstacle_height | - | 0.05m | Nav2 obstacle_layer |
| min_z / max_z | - | 0.05m / 1.5m | Nav2 collision_monitor |

---

## 配置文件位置

- RTAB-Map: SDK 自带 `/opt/ros/jazzy/share/factor_perception/config/rtabmap.ini`
- Nav2: `/home/yq/nav24r/config/nav2_params.yaml`

---

## 相关话题

| 话题 | 说明 |
|------|------|
| `/factor_perception/rtabmap/cloud_map` | 3D 地图点云 |
| `/factor_perception/rtabmap/octomap` | 3D Octomap |

---

## 轻量化启动方案

为避免GPU内存不足导致死机，采用轻量化启动方式：

### 启动方式对比

| 方案 | 内存占用 | 说明 |
|------|----------|------|
| 内置可视化 (rtabmap_viz) | 高 | 可能导致GPU崩溃 ❌ |
| 禁用可视化 | 低 | 纯SLAM功能 ✓ |
| 轻量RViz2 | 中 | 仅显示必要信息 ✓ |

### 使用方法

#### 方式1: 载启动脚本（推荐）

```bash
cd /home/yq/nav24r
./scripts/start_rtabmap_light.sh
```

脚本会提示选择模式：
- 1: 新建地图
- 2: 续建地图
- 3: 定位模式

#### 方式2: 手动启动

```bash
# 1. 启动 SLAM (无可视化)
ros2 launch factor_perception factor_perception_auto.launch.py \
    cam_pos_z:=0.85 \
    rtabmap_viz:=false

# 2. 启动轻量化 RViz2
rviz2 -d /home/yq/nav24r/config/rtabmap_light.rviz
```

### 轻量化RViz配置

位置: `/home/yq/nav24r/config/rtabmap_light.rviz`

**包含内容（导航避障必需）**:
- ✅ 2D占据栅格地图
- ✅ 3D点云地图 (MapCloud3D)
- ✅ Octomap彩色占据栅格
- ✅ 实时障碍物点云
- ✅ TF坐标系
- ✅ RTAB-Map信息面板
- ✅ 地图拓扑图

**不包含（节省GPU内存）**:
- ❌ 相机图像流
- ❌ DepthCloud深度云
- ❌ DepthRegisteredCloud

**预设视图**:
- TopDownMap: 俯视2D地图视图
- 3DView: 第三人称跟随视图

---

## 崩溃问题排查

### 崩溃根本原因

**不是 GPU 内存问题**，而是 **OAK-D 相机驱动崩溃**：

```
[FATAL] Cannot find any device with given deviceInfo
segfault in libdepthai-core.so
```

### 崩溃流程

```
1. 启动 factor_perception_node
2. 查找 OAK-D 设备 → 失败（设备未连接）
3. depthai-core 库访问空指针
4. segfault → component_container 崩溃
5. 系统不稳定 → 死机
```

### 解决方案

控制面板已添加设备检测和相机重启功能：

| 功能 | 说明 |
|------|------|
| **设备状态显示** | 实时显示 OAK-D 连接状态 |
| **自动检测** | 每3秒自动检测设备 |
| **检测设备** | 手动检测当前设备状态 |
| **重启相机** | 软重启相机（重置USB） |
| **强制重连** | 停止所有进程+重置USB+重新连接 |
| **启动前检查** | 启动建图/导航前自动检测设备 |

### 设备检测实现

检测 OAK-D 设备的方法：
- Vendor ID: `03e7`, `1443`, `2e1d`, `luxonis`
- 通过 `lsusb` 命令检测 USB 设备列表

### 历史崩溃记录

| 组件 | 时间 | 崩溃文件大小 | 原因 |
|------|------|-------------|------|
| component_container_mt | Jun 16 | 300MB | GPU内存不足 |
| rtabmap_viz | Jun 17 | 430KB | 可视化崩溃 |
| rviz2 | Jun 15 | 1.4MB | 显示问题 |

### 解决方案

已采用方案2（轻量化RViz）:
- 禁用内置 `rtabmap_viz`
- 使用独立的轻量化RViz2配置
- 减少3D渲染负载

---

## 参考资料

- Factor Perception User Guide (PDF)
- 因子空间感知SDK标准版使用手册 (PDF)
- `/opt/ros/jazzy/share/factor_perception/config/rtabmap.ini`