# RTAB-Map 配置文档

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v2.1 | 2026-06-18 | 基于Factor Perception SDK默认配置 + 3D避障 |
| v2.2 | 2026-06-18 | 添加ROS2工程分析、设备检测、控制面板更新 |
| v2.3 | 2026-06-21 | 修复W3-W10配置Warning问题 |

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
| 相机高度 | 1.0m | OAK-D Pro 安装高度 |
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
| `Grid\3D` | false | **true** | 启用3D点云地图（3D避障需要） |
| `Grid\MaxObstacleHeight` | 1.0m | **1.5m** | 适配机器人最高点1.4m |
| `GridGlobal\FootprintRadius` | 0.0 | **0.5m** | 设置机器人轮廓半径 |
| `Grid\FootprintHeight` | 0.0 | **1.4m** | 机器人3D轮廓高度（RayTracing剔除机器人点云） |
| `Grid\FootprintLength` | 0.0 | **0.5m** | 机器人3D轮廓长度 |
| `Grid\FootprintWidth` | 0.0 | **0.5m** | 机器人3D轮廓宽度 |
| `Grid\MaxGroundHeight` | 0.0 | **0.05m** | 地面检测上限（避免低矮障碍物误判为地面） |
| `Grid\MinGroundHeight` | 0.0 | **-0.05m** | 地面检测下限（容差范围） |
| `Mem\InitWMWithAllNodes` | true | **false** | 新建地图不加载旧节点，续建/定位模式在launch中显式覆盖 |
| `Optimizer\Robust` | false | **true** | 启用鲁棒核函数，防止错误回环闭合影响全图 |
| `RGBD\OptimizeMaxError` | 3.0 | **1.0** | 室内场景更严格的优化误差阈值 |
| `RGBD\ForceOdom3DoF` | false | **true** | 2D平面运动机器人强制3DoF里程计 |
| `Reg\Force3DoF` | false | **true** | 与ForceOdom3DoF保持一致，避免约束类型不匹配 |
| `DbSqlite3\Synchronous` | 0 | **1** | NORMAL模式写入，防止断电数据丢失 |
| `Rtabmap\WorkingDirectory` | (硬编码) | **~/.ros** | 避免硬编码用户路径 |

---

## Nav2 配置同步

RTAB-Map 参数与 Nav2 配置 (`config/nav2_params.yaml`) 保持一致：

| 参数 | RTAB-Map | Nav2 | 说明 |
|------|----------|------|------|
| max_obstacle_height | 1.5m | 1.5m | ✅ 一致 |
| min_obstacle_height | - | 0.05m | Nav2 obstacle_layer |
| min_z / max_z | - | 0.05m / 1.5m | Nav2 collision_monitor |

---

## 配置文件位置

- RTAB-Map: `/home/yq/nav24r/config/rtabmap_custom.ini`
- Nav2: `/home/yq/nav24r/config/nav2_params.yaml`

---

## 相关话题

| 话题 | 说明 |
|------|------|
| `/factor_perception/cloud_obstacles` | 3D障碍物点云 |
| `/factor_perception/map` | 2D栅格地图 |

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
    cam_pos_z:=1.0 \
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