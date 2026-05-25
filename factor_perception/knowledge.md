# 技术知识库

> 本文件由 **智库专家 (Knowledge Expert)** 维护
>
> 状态: 📝 模板待填充

---

## 1. 硬件知识

### 1.1 OAK-D Pro 相机

#### 技术规格

| 参数 | 规格 |
|------|------|
| 深度分辨率 | 1280×800 |
| RGB分辨率 | 4K (可选) |
| 深度范围 | 0.2m - 35m |
| 视场角 | 89° (水平) |
| IMU | BMI270 |
| 接口 | USB 3.0 |

#### 使用技巧

```markdown
# TODO: 添加使用技巧
- IR 投影器在暗光环境下的使用
- MXID 查询方法
- 常见问题处理
```

### 1.2 RK3588 开发板

#### 性能特性

| 参数 | 规格 |
|------|------|
| CPU | 4×A55 (小核) + 4×A76 (大核) |
| 内存 | 8GB LPDDR4 |
| 大核频率 | 2.4GHz |

#### 优化技巧

```markdown
# CPU 亲和性绑定
taskset -c 4-7 <command>  # 绑定到大核

# 性能监控
htop  # 查看 CPU 使用
```

---

## 2. 软件知识

### 2.1 Factor Perception SDK

#### 核心功能

| 功能 | 描述 | 关键参数 |
|------|------|----------|
| VIO | 视觉惯性里程计 | `enable_vio`, `vio_frequency` |
| Depth | 立体深度估计 | `depth_filter`, `confidence_threshold` |
| IMU | IMU 数据发布 | `ir_intensity` |

#### 参数调优

```markdown
# TODO: 添加参数调优经验
- VIO 稳定性优化
- 深度滤波配置
- 延迟优化
```

### 2.2 Nav2 导航栈

#### Costmap 配置

```markdown
# TODO: 添加 Costmap 调参经验
- obstacle_range 与 raytrace_range 的关系
- 膨胀半径设置
- 层顺序影响
```

#### MPPI 控制器

```markdown
# TODO: 添加 MPPI 调参经验
- batch_size 与性能平衡
- cost_weights 调优
- 运动模型选择
```

### 2.3 robot_localization EKF

#### 融合配置

```markdown
# TODO: 添加 EKF 配置经验
- odom0_config 和 imu0_config 的含义
- 协方差矩阵设置
- 融合权重调整
```

---

## 3. 运维知识

### 3.1 启动顺序

```bash
# 1. Factor Perception (相机数据)
ros2 launch factor_perception factor_perception_launch.py

# 2. Robot Localization (EKF融合)
ros2 launch robot_localization ekf.launch.py

# 3. Nav2 (导航栈)
ros2 launch nav2_bringup navigation_launch.py

# 4. SLAM (可选，建图)
ros2 launch slam_toolbox online_async_launch.py
```

### 3.2 性能监控

```bash
# 查看 TF 树
ros2 run tf2_tools view_frames

# 查看话题频率
ros2 topic hz /camera/odom

# 查看 CPU 使用
htop
```

### 3.3 Cyclone DDS 配置

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

## 4. 故障知识

### 4.1 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| TF 树断开 | `publish_tf=True` | 设置为 `False` |
| 鬼影障碍物 | 深度噪声 | 启用 `depth_filter=True` |
| VIO 漂移 | 室内暗光 | 增加 `ir_intensity` |
| 高延迟 | Fast DDS | 使用 Cyclone DDS |
| TF 时间戳错误 | 时钟漂移 | 安装 Chrony |

### 4.2 详细故障排除

#### TF 树断开

```markdown
症状:
- `tf2_echo` 报错: "Frame does not exist"
- Nav2 无法规划路径

原因:
- Factor Perception 发布了 odom→base_link TF
- 与 EKF 发布的 TF 冲突

解决方案:
1. 设置 publish_tf: False
2. 确保 robot_localization 正常运行
3. 检查 TF 树: ros2 run tf2_tools view_frames
```

#### VIO 漂移

```markdown
症状:
- 定位逐渐偏离真实位置
- 机器人位置在 RViz 中漂移

原因:
- 室内光照不足
- 缺乏视觉特征

解决方案:
1. 增加 ir_intensity: 0.4
2. 改善环境光照
3. 增加视觉特征 (如海报、家具)
```

---

## 5. 最佳实践

### 5.1 开发流程

```markdown
# TODO: 添加开发流程建议
- 参数调试顺序
- 测试方法
- 部署检查清单
```

### 5.2 性能优化

```markdown
# TODO: 添加性能优化建议
- CPU 亲和性
- 内存管理
- 网络配置
```

---

## 修订历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v0.1 | 2026-05-25 | Claude (执行官) | 创建模板 |

---

*维护者: 智库专家 (Knowledge Expert)*
*最后更新: 待用户填充*