# 技术栈

## 硬件平台

### OAK-D Pro 相机

| 参数 | 规格 |
|------|------|
| 深度分辨率 | 1280×800 |
| RGB分辨率 | 4K (可选) |
| IMU | BMI270 |
| 接口 | USB 3.0 |
| MXID | 自动检测或手动指定 |

### RK3588 开发板

| 参数 | 规格 |
|------|------|
| CPU | 4×A55 (小核) + 4×A76 (大核) |
| 内存 | 8GB LPDDR4 |
| USB | USB 3.0 |
| 性能建议 | 绑定关键进程到大核 (core 4-7) |

---

## 软件栈

### ROS2 Humble

| 包 | 版本 | 用途 |
|------|------|------|
| navigation2 | Humble默认 | 导航栈 |
| robot_localization | 3.x | EKF融合 |
| slam_toolbox | Humble默认 | 可选SLAM |
| nav2_mppi_controller | Humble默认 | MPPI控制器 |

### Factor Perception SDK

| 功能 | 描述 |
|------|------|
| VIO | 视觉惯性里程计，6自由度姿态估计 |
| Depth | 立体深度估计，带滤波与置信度 |
| IMU | BMI270 IMU数据发布 |
| Object Detection | 板载神经网络推理 (可选) |

### DDS 配置

推荐使用 **Cyclone DDS** (替代默认 Fast DDS)，减少延迟：

```xml
<!-- ~/.cyclonedds.xml -->
<CycloneDDS>
  <Domain id="any">
    <General>
      <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
      <AllowMulticast>true</AllowMulticast>
    </General>
  </Domain>
</CycloneDDS>
```

---

## 关键技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 里程计融合 | EKF (robot_localization) | 需融合多源数据，避免TF冲突 |
| 控制器 | MPPI | 适合人形机器人全向运动 |
| DDS | Cyclone | Fast DDS在RK3588上有延迟问题 |
| 深度滤波 | 启用 | 人形机器人易产生假障碍物 |
| IR补光 | 启用 | 室内/暗光环境VIO稳定性 |

---

## 参数配置要点

### Factor Perception 关键参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `publish_tf` | False | 防止与EKF冲突 |
| `depth_filter` | True | 过滤噪点 |
| `ir_intensity` | 0.4 | 室内补光 |
| `confidence_threshold` | 200 | 深度置信度 |
| `vio_frequency` | 30.0 | VIO频率 |

### Nav2 Costmap 参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `obstacle_range` | 3.0m | 障碍物检测范围 |
| `raytrace_range` | 3.5m | 清除范围 |
| `max_obstacle_height` | 2.0m | 最大障碍物高度 |

---

*Created: 2026-05-25*