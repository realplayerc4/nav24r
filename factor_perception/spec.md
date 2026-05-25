# 集成规范

> 本文件由 **立法者 (Legislator)** 维护
>
> 状态: 📝 模板待填充

---

## 1. TF 树规范

> 定义 TF 树结构，明确各 TF 的发布者和频率。

### 1.1 坐标系定义

| 坐标系 | 描述 |
|--------|------|
| `map` | 世界固定坐标系 |
| `odom` | 里程计坐标系 |
| `base_link` | 机器人本体坐标系 |
| `camera_link` | 相机坐标系 |

### 1.2 TF 发布规范

```yaml
# TODO: 由立法者填充
TF 发布规范:
  odom → base_link:
    发布者: robot_localization
    频率: 30Hz
    # 添加更多细节

  camera_link → base_link:
    发布者: static_transform_publisher
    类型: 静态TF
    # 添加平移和旋转参数
```

### 1.3 TF 禁止项

```yaml
# Factor Perception 禁止发布 odom→base_link
禁止:
  - publish_tf: True  # 不允许，会与 EKF 冲突
```

---

## 2. 话题规范

> 定义话题名称、消息类型和 QoS 设置。

### 2.1 感知话题

| 话题 | 类型 | QoS | 描述 |
|------|------|-----|------|
| `/camera/depth/points` | `PointCloud2` | best_effort | 深度点云 |
| `/camera/odom` | `Odometry` | reliable | VIO里程计 |
| `/camera/imu` | `Imu` | best_effort | IMU数据 |
| `/camera/rgb/image_raw` | `Image` | best_effort | RGB图像 |

### 2.2 导航话题

| 话题 | 类型 | QoS | 描述 |
|------|------|-----|------|
| `/cmd_vel` | `Twist` | reliable | 速度命令 |
| `/plan` | `Path` | reliable | 路径规划 |

---

## 3. 参数边界

> 定义参数的可接受范围和推荐值。

### 3.1 Factor Perception 参数

| 参数 | 允许值 | 推荐值 | 原因 |
|------|--------|--------|------|
| `publish_tf` | `[False]` | `False` | 防止与EKF冲突 |
| `depth_filter` | `[True, False]` | `True` | 人形机器人需过滤噪点 |
| `ir_intensity` | `[0.0, 1.0]` | `0.4` | 室内VIO稳定性 |
| `confidence_threshold` | `[0, 255]` | `200` | 深度置信度 |
| `vio_frequency` | `[10.0, 60.0]` | `30.0` | VIO频率 |

### 3.2 Nav2 Costmap 参数

| 参数 | 允许值 | 推荐值 | 原因 |
|------|--------|--------|------|
| `obstacle_range` | `[1.0, 10.0]` | `3.0` | 障碍物检测范围 |
| `raytrace_range` | `[1.5, 12.0]` | `3.5` | 清除范围 |
| `max_obstacle_height` | `[0.5, 3.0]` | `2.0` | 最大障碍物高度 |

---

## 4. 性能指标

> 定义系统性能要求。

### 4.1 实时性要求

| 指标 | 要求 | 测试方法 |
|------|------|----------|
| VIO 频率 | ≥ 30Hz | `ros2 topic hz /camera/odom` |
| 深度延迟 | < 50ms | 时间戳对比 |
| TF 延迟 | < 10ms | `tf2_echo` |

### 4.2 精度要求

| 指标 | 要求 | 测试方法 |
|------|------|----------|
| 定位精度 | < 0.1m (室内) | 真值对比 |
| 路径跟踪误差 | < 0.05m | 轨迹对比 |

### 4.3 资源要求

| 指标 | 要求 |
|------|------|
| CPU 占用 | < 80% (单核) |
| 内存占用 | < 2GB |

---

## 5. 约束与限制

### 5.1 硬件约束

- USB 3.0 连接必需
- RK3588 需绑定大核运行关键进程

### 5.2 软件约束

- ROS2 Humble 版本
- Cyclone DDS (不使用 Fast DDS)

### 5.3 功能边界

参见 `memory-bank/project-overview.md` 中的 Non-Goals

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-05-25 | Claude (执行官) | 创建模板 |
| v0.2 | 2026-05-25 | Claude (执行官) | 添加相机 MXID |

---

## 附录: 硬件配置

### 相机信息

| 属性 | 值 |
|------|-----|
| 设备 | OAK-D Pro |
| MXID | `B4C22057DAC5A53595D92CD44D06F91E` |
| Key | `12D0C1E7D1AB466C09BD9AE6427D5240` |
| 连接状态 | ✅ 已连接 |
| 安装位置 | 前方水平，高度 0.5m |

### 启动命令

```bash
# 官方启动方式
ros2 launch factor_perception factor_perception_launch.py key:=12D0C1E7D1AB466C09BD9AE6427D5240

# 如需指定相机位置
ros2 launch factor_perception factor_perception_launch.py \
    key:=12D0C1E7D1AB466C09BD9AE6427D5240 \
    cam_pos_z:=0.5
```

### 可视化插件安装

```bash
sudo apt install ros-humble-rtabmap-rviz-plugins ros-humble-octomap-rviz-plugins
```

---

*维护者: 立法者 (Legislator)*
*最后更新: 待用户填充*