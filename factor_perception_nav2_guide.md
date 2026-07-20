# Factor Perception SDK v1.5.1 Nav2 集成指南

**SDK 版本**: Factor Perception v1.5.1
**ROS 2 版本**: Jazzy
**目标硬件**: OAK-D 系列相机 + 人形机器人

---

## 1. SDK 架构概览

Factor Perception 是一个以 AI 视觉 SLAM 为核心的机器人空间感知 ROS 包，提供 Factor-VIO（视觉惯性里程计）前端和 RTAB-Map 后端。

### 1.1 数据流

```
OAK Camera ──▶ OAK Manager ──▶ HF-Net Engine ──▶ Factor-VIO ──▶ RTAB-Map
                                                                │
                          ┌──────────────────────────────────────┴──────────────────────┐
                          │                                                             │
                     Nav2 输出                                                      地图输出
                     /factor_perception/odom                                        /factor_perception/map → odom
                     /factor_perception/imu (200Hz)                                 2D/2.5D/3D Map
```

### 1.2 核心模块

| 模块 | 功能 |
|------|------|
| **OAK Manager** | 管理 OAK-D 系列相机硬件 |
| **HF-Net Engine** | 混合特征网络（深度学习特征 + 传统 SGBM 深度） |
| **Factor-VIO** | 因子图视觉惯性里程计前端，输出 odom → base_link |
| **RTAB-Map** | 后端建图与回环检测，输出 map → odom |

---

## 2. 支持硬件

### 2.1 OAK 相机型号

| 型号 | 说明 | 授权要求 |
|------|------|----------|
| OAK-D S2 | USB 3.0, 标准版 | 需要密钥 |
| OAK-D W | USB 3.0, 广角版 | 需要密钥 |
| OAK-D Pro | USB 3.0, 高精度版 | 需要密钥 |
| OAK-D Pro W | USB 3.0, 4K 广角 | 需要密钥 |
| OAK-D Pro PoE | 以太网供电 | 需要密钥 |
| OAK-D Pro W PoE | 以太网供电, 4K | 需要密钥 |
| OAK-D S2 PoE | 以太网供电 | 需要密钥 |
| OAK-D LR | 低功耗低分辨率 | 无需密钥 |
| OAK-D SR | 低功耗低分辨率 | 无需密钥 |

> **注意**: LR/SR 型号某些功能受限（如不发布 `CompressedImage` 和 `CameralInfo` 话题）。

### 2.2 密钥获取

- 官方渠道: https://www.luxonis.com/hardware/
- 国内渠道: https://www.oakchina.cn/download/

---

## 3. ROS 2 平台配置

### 3.1 ROS 包安装

```bash
# ROS 1
sudo dpkg -i ros-<distro>-factor-perception_<version>_<architecture>.deb

# ROS 2
ros2 launch factor_perception factor_perception.launch.py key:=<your_key>
```

### 3.2 udev 规则

```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' | sudo tee /etc/udev/rules.d/80-movidius.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 3.3 DDS 中间件（重要）

SDK v1.5.1 默认使用 Fast DDS，但**不适合传输大量数据**（如深度图像、点云）。

| DDS | 适用场景 |
|-----|----------|
| Fast DDS | ROS 2 默认，不适合 Factor Perception 大数据 |
| CycloneDDS | **推荐**，稳定传输大量数据 |
| Zenoh | 也可用，非DDS但网络性能好 |

**切换为 CycloneDDS**:
```bash
# 安装
sudo apt install ros-jazzy-rmw-cyclonedds-cpp

# 设置环境变量
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

---

## 4. 核心参数参考

### 4.1 Factor-VIO 前端参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-mxid_or_name` | string | `""` | OAK 相机 MXID/IP/USB 端口名，留空自动检测 |
| `-key` | string | `""` | **完整功能必须的授权密钥** |
| `-oak_tf_prefix` | string | `"oak"` | OAK 相机 TF 前缀 |
| `-base_frame_id` | string | `"base_link"` | 机器人基座坐标系 |
| `-odom_frame_id` | string | `"odom"` | 里程计坐标系 |
| `-publish_tf` | bool | `true` | 是否发布 TF（odom→base_link） |
| `-depth_filter` | bool | `false` | 深度置信度过滤（开启可减少虚假障碍物，增加 CPU） |
| `-ir_intensity` | double | `0.0` | 红外补光强度 (>0.0 且 <1.0)，仅 Pro 型号 |
| `-min_feat_depth` | double | `0.0` | 特征提取最小深度 (m) |
| `-blob_path` | string | `""` | SLAM 神经网络模型路径，留空使用 SDK 默认 |
| `-camera_cpu` | int | `-1` | 相机线程绑定的 CPU 核心 ID |
| `-imu_cpu` | int | `-1` | IMU 线程绑定的 CPU 核心 ID |
| `-rgb_fps` | float | `20.0` | RGB 帧率 |
| `-publish_tf` | bool | `true` | 发布 odom→base_link TF |

### 4.2 机器人模型配置

Factor-VIO 在 odom 帧中发布位姿。SDK 直接提供从 odom 到 base_link 的 TF，以及从 base_link 到 map 的 TF。用户无需额外配置机器人模型即可获取位姿。

---

## 5. 发布的话题

### 5.1 已发布话题列表

| 话题 | 消息类型 | 频率 | 说明 |
|------|---------|------|------|
| `/factor_perception/rgb/image/compressed` | `sensor_msgs/CompressedImage` | 20Hz | 矫正后彩色图（LR/SR 不支持此话题） |
| `/factor_perception/camera/camera_info` | `sensor_msgs/CameraInfo` | - | 中间相机内参（LR/SR 不支持） |
| `/factor_perception/left/image_rect/compressed` | `sensor_msgs/CompressedImage` | 20Hz | 矫正后左图彩色图（LR/SR 为黑白图） |
| `/factor_perception/camera/camera_info` | `sensor_msgs/CameraInfo` | - | 左相机内参 |
| `/factor_perception/depth/image_rect` | `sensor_msgs/Image` | 20Hz | 矫正后深度图（与左相机对齐） |
| `/factor_perception/depth/camera_info` | `sensor_msgs/CameraInfo` | - | 深度相机内参 |
| `/factor_perception/rgbd/image` | `rtabmap_msgs/RGBDImage` | - | 同步图像+深度+特征+描述子 |
| `/factor_perception/imu` | `sensor_msgs/Imu` | 200Hz | 9轴 IMU（3轴加速度 + 3轴角速度 + 9轴融合方向） |
| `/factor_perception/odom` | `nav_msgs/Odometry` | 200Hz | 视觉惯性里程计（与 IMU 同步） |

> **注意**: 话题名使用 namespace `factor_perception/`，而非旧版的 `/camera/*` 前缀。

### 5.2 旧版话题对比

| 旧版话题（过时） | SDK v1.5.1 话题 | 说明 |
|------------------|-----------------|------|
| `/camera/depth/image_raw` | `/factor_perception/depth/image_rect` | 深度图 |
| `/camera/depth/points` | `/factor_perception/rgbd/image` | RGBD 数据 |
| `/camera/rgb/image_raw` | `/factor_perception/rgb/image/compressed` | 彩色图 |
| `/camera/imu` | `/factor_perception/imu` | IMU 数据 |
| `/camera/odom` | `/factor_perception/odom` | 里程计 |

---

## 6. TF 树结构

```
map                          (RTAB-Map 发布)
 └── odom                    (Factor-VIO 发布)
      └── base_link          (Factor-VIO 发布，里程计估算)
           └── oak_base_frame
                ├── oak_model_origin
                ├── oak_rgb_frame
                ├── oak_left_frame / oak_right_frame
                ├── oak_rgb_optical_frame
                ├── oak_left_optical_frame / oak_right_optical_frame
                └── oak_imu_frame
```

- `map → odom`：RTAB-Map 后端发布，修正前端漂移
- `odom → base_link`：Factor-VIO 前端发布，高频里程计
- Factor Perception 直接提供从 odom 到 base_link 的 TF，以及从 base_link 到 map 的 TF

---

## 7. 传感器校准

### 7.1 IMU 自校准

- **动态初始化**：Factor-VIO 估计陀螺仪零偏
- **静态初始化**：Factor-VIO 估计加速度计零偏和重力方向

### 7.2 动态外参标定

OAK 相机出厂时对相机和 IMU 进行了初步标定。在动态运动时，可通过传感器标定节点动态优化外参：

```bash
# ROS 1
roslaunch factor_perception sensor_calibration.launch

# ROS 2
ros2 launch factor_perception sensor_calibration_launch.py
```

**标定步骤**：
1. 启动标定 launch 文件
2. 在水平面沿六个方向放置设备：X±、Y±、Z+、Z-
3. 每个方位保持静止 ≥ 1 秒
4. 观察 RViz 中相机和 IMU 坐标系从抖动到收敛
5. 当 sigma 值 < 0.001 时标定完成
6. 按 `Ctrl+C` 停止，数据自动写入 EEPROM

**注意事项**：
- 环境光照充足且无重复纹理
- 设备不接近高精度陀螺仪或强磁场
- 摇摄不超过 45 度，避免长距离平移
- 不包含过快/过慢动作，包含平移和旋转

### 7.3 重置为出厂标定

```bash
# ROS 2
ros2 launch factor_perception sensor_calibration_launch.py calibration_mode:=reset rviz:=false
```

---

## 8. 启动与配置

### 8.1 启动 Launch 文件

```bash
# ROS 1
roslaunch factor_perception factor_perception.launch.py key:=<your_key>

# ROS 2
ros2 launch factor_perception factor_perception.launch.py key:=<your_key>
```

可以在相机静止或移动时启动。VIO 会自动适应动态或静态初始化。

### 8.2 RTAB-Map 后端配置

RTAB-Map 配置文件路径：`/opt/ros/<distro>/share/factor_perception/config/rtabmap.ini`

可通过 `config_path` 参数指定其他配置文件。

**RTAB-Map 数据库路径**：通过 `database_path` 参数设置，默认 `~/.ros/rtabmap.db`

### 8.3 建图/定位模式切换

| 参数 | 建图模式 | 定位模式 |
|------|---------|---------|
| `localization` | `false` | `true` |
| `Mem/IncrementalMemory` | `true` | `false` |
| `Mem/InitWMWithAllNodes` | `false` | `true` |

---

## 9. Nav2 集成

### 9.1 话题映射

| Nav2 组件 | 使用的话题 | 说明 |
|-----------|-----------|------|
| Costmap (obstacle) | `/factor_perception/rgbd/image` | RGBD 数据用于障碍物检测 |
| robot_localization (EKF) | `/factor_perception/odom`, `/factor_perception/imu` | 融合里程计和 IMU |
| Map Server | RTAB-Map 生成的 2D 栅格地图 | 通过 map_server 加载 |

### 9.2 EKF 配置

Factor-VIO 输出的 `odom→base_link` TF 已经包含了视觉和 IMU 的融合结果。如果需要额外的滤波，可在 `robot_localization` 中配置 EKF：

```yaml
# EKF 输入
odom0: /factor_perception/odom
imu0: /factor_perception/imu
```

### 9.3 Costmap 配置

使用 RTAB-Map 生成的 2D 栅格地图作为静态层：

```yaml
local_costmap:
  local_costmap:
    ros__parameters:
      global_frame: odom
      robot_base_frame: base_link
      plugins: ["obstacle_layer", "inflation_layer"]

      obstacle_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        observation_sources: pointcloud
        pointcloud:
          topic: /factor_perception/rgbd/image
          data_type: "RGBD"
          clearing: True
          marking: True
          max_obstacle_height: 1.5
          min_obstacle_height: 0.05
```

---

## 10. 续建地图说明

### 10.1 原理

RTAB-Map 支持增量记忆模式（Incremental Memory），当 `localization=false` 且数据库文件已存在时：
1. RTAB-Map 自动加载已有数据库中的所有历史节点
2. 新的传感器数据被添加到数据库
3. 回环检测将新数据与历史数据进行匹配

### 10.2 注意事项

- **VIO 重启**：每次启动 Factor Perception 时，Factor-VIO 都会重新初始化，`map→odom` TF 可能会有短暂跳变。这是正常的，RTAB-Map 会在接收到足够数据后自动修正。
- **TF 连续性**：续建时不应关闭 `publish_tf`，否则 Nav2 会丢失 TF 树。
- **Proximity 检测**：确保 `RGBD/ProximityBySpace` 和 `RGBD/ProximityByTime` 已启用，这对续建时的数据关联至关重要。

### 10.3 操作流程

```bash
# 1. 新建地图
ros2 launch factor_perception_auto.launch.py localization:=false database_path:=~/rtabmap.db

# 2. 采集数据后停止（Ctrl+C）

# 3. 续建地图（使用同一数据库路径）
ros2 launch factor_perception_auto.launch.py localization:=false database_path:=~/rtabmap.db
```

---

## 11. 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| TF 树断裂 | publish_tf 设置错误 | 确保 `publish_tf:=true` |
| 虚假障碍物 | 深度噪声 | 启用 `depth_filter:=true` |
| 续建地图数据不连续 | VIO 重启后位姿跳变 | 正常现象，移动几秒后 RTAB-Map 会自动修正 |
| 室内 VIO 漂移 | 光照不足 | 增加 `ir_intensity` (0.0-1.0) |
| 高延迟 | Fast DDS 开销 | 切换为 CycloneDDS |
| 相机无法检测 | USB 连接问题 | 检查 udev 规则，确保 USB 3.0 |
| 数据话题收不到 | DDS 兼容性 | 使用 CycloneDDS 而非 Fast DDS |

### 11.1 调试命令

```bash
# 查看所有话题
ros2 topic list | grep factor_perception

# 查看 IMU 数据
ros2 topic echo /factor_perception/imu

# 查看里程计
ros2 topic echo /factor_perception/odom

# 查看 TF 树
ros2 run tf2_tools view_frames

# 查看节点
ros2 node list | grep factor_perception
```

---

## 12. 参考资料

- [Factor Perception User Guide (PDF)](./Factor%20Perception%20User%20Guide.pdf)
- [因子空间感知SDK标准版使用手册 (PDF)](./因子空间感知SDK标准版使用手册.pdf)
- SDK 官方 RTAB-Map 配置: `/opt/ros/jazzy/share/factor_perception/config/rtabmap.ini`
- RTAB-Map Wiki: https://github.com/introlab/rtabmap/wiki
