# Nav2 / RTAB-Map 知识要点

> 本文件整理 `nav24r` 中 Nav2 与 RTAB-Map 的核心知识，便于快速理解和记忆。

---

## 1. RTAB-Map（SLAM 层）

### 1.1 三种运行模式

| 模式 | `Mem/IncrementalMemory` | `Mem/InitWMWithAllNodes` | 说明 |
|------|------------------------|--------------------------|------|
| 新建地图 | `true` | `false` | 从空地图开始建图 |
| 续建地图 | `true` | `true` | 加载已有地图数据继续建图 |
| 定位模式 | `false` | `true` | 只读已有地图，用于导航 |

### 1.2 关键配置参数

- `Grid/3D = true`：启用 3D 点云地图，用于 3D 避障
- `RGBD/ProximityBySpace = true`：基于空间邻近度进行闭环检测
- `RGBD/ProximityByTime = true`：基于时间邻近度进行闭环检测
- `config_path`：指向 `config/rtabmap_custom.ini`
- `database_path`：SQLite `.db` 文件路径，默认 `~/rtabmap_maps/<map_id>.db`

### 1.3 核心话题

| 话题 | 类型 | 说明 |
|------|------|------|
| `/factor_perception/map` | `nav_msgs/OccupancyGrid` | 2D 栅格地图 |
| `/factor_perception/odom` | `nav_msgs/Odometry` | 里程计 |
| `/factor_perception/cloud_obstacles` | `sensor_msgs/PointCloud2` | 3D 障碍物点云 |
| `/tf` | `tf2_msgs/TFMessage` | TF 树（map → odom → base_link → ...）|

### 1.5 回环检测（Loop Closure Detection）

RTAB-Map 的回环检测分两步：**视觉匹配**（词袋模型）→ **几何验证**（RANSAC + 变换估计）。

#### 日志含义

| 日志 | 含义 |
|------|------|
| `Loop hypothesis <id> accepted` | 视觉匹配通过，几何验证也通过，回环成立 |
| `Loop hypothesis <id> rejected` | 视觉匹配通过，但几何验证失败，回环被拒绝 |

- **hypothesis**：当前帧与历史帧的潜在回环匹配
- **id**：候选匹配的节点 ID（如 3054 = 数据库中第 3054 帧）
- **rejected**：RANSAC 内点不足或变换估计不合理

#### 被拒绝的常见原因

| 原因 | 说明 |
|------|------|
| 几何验证失败 | RANSAC 内点数不足，变换估计不可靠 |
| 变换不合理 | 估计位姿与里程计差距超出阈值 |
| 重复纹理/场景 | 走廊、窗户等导致视觉误匹配 |
| 运动模糊 | 图像质量差，特征点匹配不准确 |

#### 判断与调优

- **偶尔 rejected**：正常，验证机制在过滤错误回环
- **大量 rejected**：可能场景特征重复、相机标定/里程计偏差、图像质量差
- **地图漂移严重**：回环被误拒绝，可降低验证严格度

```yaml
# 调优参数（rtabmap.launch.py 或 rtabmap_custom.ini）
rtabmap:
  ros__parameters:
    Rtabmap/LoopThr: 0.11       # 回环检测阈值（默认 0.11，越低越严格）
    Vis/MinInliers: 15          # 最小内点数（默认 15，可降至 10 放宽验证）
    Vis/InlierDistance: 0.1     # 内点距离阈值（默认 0.1m）
```

> ⚠️ 降低 `Vis/MinInliers` 可让更多回环通过，但会增加误匹配风险。

### 1.4 离线分析工具

- **rtabmap-databaseViewer**：官方工具，可直接打开 `.db` 文件
  - 查看节点分布、链接关系、闭环检测
  - 查看每个节点的 RGB 图像、深度图像、3D 点云
  - 导出地图为图像或 3D 点云

---

## 2. Nav2（导航层）

### 2.1 控制器

- **MPPI（Model Predictive Path Integral）**：基于采样的优化控制器
  - 运动模型：`Omni`（全向）
  - 时间步长：`model_dt = 0.05s`，预测步数：`time_steps = 56`
  - 最大速度：`vx_max = 0.3 m/s`, `wz_max = 0.5 rad/s`

### 2.2 代价地图

| 参数 | 局部代价地图 | 全局代价地图 |
|------|-------------|-------------|
| 大小 | 3×3m 滑动窗口 | 静态全局地图 |
| 分辨率 | 0.05m | 0.05m |
| 更新频率 | 5.0 Hz | 1.0 Hz |
| 障碍物高度范围 | 0.05m ~ 1.5m | 0.05m ~ 1.5m |
| 订阅话题 | `/factor_perception/cloud_obstacles` | `/factor_perception/map`（静态层）+ `/factor_perception/cloud_obstacles`（障碍层）|
| 机器人半径 | 0.5m | 0.5m |

### 2.3 关键参数对齐

Nav2 与 RTAB-Map 的参数必须保持一致：

| 参数 | RTAB-Map | Nav2 | 说明 |
|------|----------|------|------|
| `max_obstacle_height` | 1.5m | 1.5m | 最高障碍物检测高度 |
| `min_obstacle_height` | - | 0.05m | 最低障碍物检测高度 |
| `footprint` | 0.5m | 0.5m | 机器人轮廓半径 |

---

## 3. 集成架构

### 3.1 数据流

```
Factor Perception（OAK-D Pro，VIO 200Hz）
    ↓ 发布 RGB-D 图像、点云、IMU
RTAB-Map SLAM（建图/定位 20Hz）
    ↓ 发布 /factor_perception/map、/factor_perception/odom、TF
Nav2 导航栈
    ↓ 路径规划 + 动态避障
cmd_vel → 机器人底盘
```

### 3.2 启动方式

1. **控制面板（GUI）**：`python3 scripts/factor_control_panel.py`
2. **Web 面板**：`python3 scripts/web_control_panel.py`
3. **Launch 文件**：
   - 新建地图：`ros2 launch nav24r factor_perception_auto.launch.py`
   - 完整导航：`ros2 launch nav24r nav24r_full.launch.py`
   - 隔离架构：`ros2 launch nav24r factor_perception_isolated.launch.py`

### 3.3 隔离架构（推荐）

- **硬件驱动容器**（单线程）：Factor Perception 节点，确定性硬件访问
- **SLAM 容器**（isolated）：RTAB-Map 节点，独立执行器
- **可视化**（可选）：rtabmap_viz 或 RViz2
- **错误恢复**：崩溃后自动重启，最多 3 次，指数退避（3s → 6s → 12s）

---

## 4. 常用命令速查

```bash
# 查看当前话题
ros2 topic list | grep factor_perception

# 查看 TF 树
ros2 run tf2_tools view_frames

# 打开地图数据库
rtabmap-databaseViewer ~/rtabmap_maps/<map_id>.db

# 启动 RViz（轻量化配置）
rviz2 -d config/rtabmap_light.rviz

# 查看节点列表
ros2 node list

# 查看地图话题
ros2 topic echo /factor_perception/map --once
```

---

## 5. 故障排查要点

- **OAK-D 未检测到**：检查 USB 连接（建议 USB 3.0），运行 `lsusb | grep -iE "03e7|1443|luxonis|oak"`
- **GPU 崩溃**：禁用 `rtabmap_viz`，使用轻量化 RViz2 配置
- **导航漂移**：检查闭环检测数量，确保地图质量评分 ≥ 70；大量 "Loop hypothesis rejected" 说明回环被误拒绝，参考 1.5 节调优
- **回环检测失败**：偶尔 rejected 正常；大量 rejected 检查场景重复性、相机标定、图像质量
- **话题不匹配**：确认 Nav2 `nav2_params.yaml` 中话题名与 RTAB-Map 输出一致
