# Factor Perception Nav2 集成指南

**目标硬件**: OAK-D Pro + RK3588 (或 x86 开发机)
**ROS 2 版本**: Jazzy
**Nav2 栈**: Navigation2

---

## 1. Factor Perception SDK 概述

Factor Perception 是 Luxonis OAK-D 系列相机的感知 SDK，提供以下功能：

| 功能 | 描述 |
|------|------|
| **视觉惯性里程计 (VIO)** | 用于 6-DOF 位姿估计的视觉惯性里程计 |
| **深度** | 带滤波和置信度的立体深度 |
| **SLAM** | 密集 3D 建图和重建 |
| **物体检测** | 设备端神经网络推理 |

### 硬件要求

- OAK-D Pro (推荐人形机器人使用)
- USB 3.0 连接
- 主机: x86 Ubuntu 24.04

---

## 2. 核心 ROS 2 参数

### 启动文件配置

```python
# factor_perception_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        # Factor Perception 节点
        Node(
            package='factor_perception',
            executable='factor_perception_node',
            name='factor_perception',
            output='screen',
            parameters=[{
                # 相机标识
                'mxid_or_name': '',  # 自动检测或指定 OAK-D 序列号

                # TF 发布 (重要: 与 EKF 融合时禁用)
                'publish_tf': False,  # 让 robot_localization 处理 odom->base_link

                # 深度配置
                'depth_filter': False,
                'confidence_threshold': 200,

                # 红外投射器 (室内/弱光环境)
                'ir_intensity': 0.4,  # 补光灯强度 (0.0-1.0)

                # Frame IDs
                'base_frame_id': 'base_link',
                'odom_frame_id': 'odom',

                # VIO 配置
                'enable_vio': True,
                'vio_frequency': 30.0,  # Hz
            }]
        ),
    ])
```

### 参数说明

| 参数 | 默认值 | 推荐值 | 说明 |
|------|--------|--------|------|
| `publish_tf` | `true` | `false` | 与 EKF 融合时禁用，避免 TF 冲突 |
| `depth_filter` | `false` | `false` | 默认关闭；仅在需要时开启 |
| `ir_intensity` | `0.0` | `0.4` | 改善室内/弱光环境 VIO 稳定性 |

---

## 3. 发布的话题

| 话题 | 类型 | 描述 |
|------|------|------|
| `/camera/depth/image_raw` | `sensor_msgs/Image` | 深度图像 |
| `/camera/depth/points` | `sensor_msgs/PointCloud2` | 3D 点云 |
| `/camera/rgb/image_raw` | `sensor_msgs/Image` | RGB 图像 |
| `/camera/imu` | `sensor_msgs/Imu` | IMU 数据 |
| `/camera/odom` | `nav_msgs/Odometry` | VIO 里程计 |
| `/camera/pose` | `geometry_msgs/PoseStamped` | 估计位姿 |

---

## 4. Nav2 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        RK3588 (上层板)                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   OAK-D Pro  │───▶│   Factor     │───▶│  robot_localization│ │
│  │   (USB 3.0)  │    │  Perception  │    │     (EKF)         │   │
│  └──────────────┘    └──────────────┘    └─────────┬────────┘   │
│                                                   │             │
│                              ┌────────────────────▼────────┐    │
│                              │           Nav2              │    │
│                              │  ┌─────────────────────┐    │    │
│                              │  │   Costmap 2D        │    │    │
│                              │  │   (体素/障碍物)      │    │    │
│                              │  └──────────┬──────────┘    │    │
│                              │             │               │    │
│                              │  ┌──────────▼──────────┐    │    │
│                              │  │   MPPI 控制器        │    │    │
│                              │  └──────────┬──────────┘    │    │
│                              │             │               │    │
│                              └─────────────┼───────────────┘    │
│                                            │                    │
│                              ┌─────────────▼──────────────┐     │
│                              │      /cmd_vel              │     │
│                              └─────────────┬──────────────┘     │
└────────────────────────────────────────────┼────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RL 控制板 (下层板)                           │
│                    (接收 /cmd_vel，执行步态)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Nav2 配置

### 代价地图层配置

```yaml
# nav2_params.yaml
local_costmap:
  local_costmap:
    ros__parameters:
      # 坐标系设置
      global_frame: odom
      robot_base_frame: base_link

      # 层插件
      plugins: ["obstacle_layer", "inflation_layer"]

      # 障碍物层 - 使用 Factor Perception 点云
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: "pointcloud"
        pointcloud:
          topic: /camera/depth/points
          data_type: "PointCloud2"
          clearing: True
          marking: True
          max_obstacle_height: 2.0
          min_obstacle_height: 0.05
          obstacle_range: 3.0
          raytrace_range: 3.5

global_costmap:
  global_costmap:
    ros__parameters:
      global_frame: map
      robot_base_frame: base_link
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]

      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: "pointcloud"
        pointcloud:
          topic: /camera/depth/points
          data_type: "PointCloud2"
          clearing: True
          marking: True
```

### EKF 配置 (robot_localization)

```yaml
# ekf_params.yaml
ekf_filter_node:
  ros__parameters:
    frequency: 30.0

    # 坐标系 IDs
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom

    # 输入源
    odom0: /camera/odom
    odom0_config: [False, False, False,  # x, y, z
                   True,  True,  True,   # roll, pitch, yaw
                   False, False, False,  # vx, vy, vz
                   True,  True,  True,   # vroll, vpitch, vyaw
                   False, False, False]  # ax, ay, az

    # IMU 输入 (来自 OAK-D)
    imu0: /camera/imu
    imu0_config: [False, False, False,  # x, y, z
                  True,  True,  True,   # roll, pitch, yaw
                  False, False, False,  # vx, vy, vz
                  True,  True,  True,   # vroll, vpitch, vyaw
                  True,  True,  True]   # ax, ay, az
```

---

## 6. MPPI 控制器配置

人形机器人推荐使用 MPPI (模型预测路径积分) 控制器：

```yaml
controller_server:
  ros__parameters:
    controller_plugins: ["FollowPath"]
    FollowPath:
      plugin: "nav2_mppi_controller::MPPIController"

      # 人形机器人运动模型
      motion_model: "Omni"

      # 时间和采样
      time_steps: 56
      model_dt: 0.05
      batch_size: 2000

      # 速度约束 (根据你的人形机器人调整)
      max_velocity: 0.5
      min_velocity: -0.1
      max_angular_velocity: 1.0

      # 成本权重
      cost_weights:
        goal_dist_cost: 1.0
        path_dist_cost: 2.0
        obstacles_cost: 5.0
```

---

## 7. 启动顺序

```bash
# 终端 1: Factor Perception (使用 composable node)
ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py

# 终端 2: Robot Localization (EKF)
ros2 launch robot_localization ekf.launch.py

# 终端 3: Nav2
ros2 launch nav2_bringup navigation_launch.py \
    params_file:=/path/to/nav2_params.yaml

# 终端 4: SLAM (可选，用于建图)
ros2 launch rtabmap_launch rtabmap.launch.py \
    args:="-d /home/yq/rtabmap.db"
```

---

## 9. 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| TF 树断开 | `publish_tf=True` | 设置为 `false`，使用 EKF |
| VIO 室内漂移 | 光线不足 | 增加 `ir_intensity` |
| 高延迟 | Fast DDS 开销 | 使用 Cyclone DDS |
| TF 时间戳错误 | 时钟漂移 | 安装 Chrony |

---

## 10. 后续步骤

1. [x] 安装 Factor Perception SDK（已通过系统包安装至 `/opt/ros/jazzy/share/factor_perception/`）
2. [x] 使用 `factor_perception_auto.launch.py` 启动
3. [x] 配置 Nav2 代价地图层
4. [x] 设置 robot_localization EKF
5. [ ] 在目标硬件上部署并验证 CPU 亲和性（如需要）
6. [ ] 长期运行稳定性测试

---

*版本: v2.0-Jazzy*
*更新日期: 2026-07-17*
*基于: Factor Perception SDK (Jul 17 update)*