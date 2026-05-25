# 技术知识库

> 本文件由 **智库专家 (Knowledge Expert)** 维护
>
> 状态: ✅ 已填充核心内容

---

## 1. Factor-VIO Front-end 深入解析

### 1.1 核心原理

Factor-VIO (Visual Inertial Odometry) 是 Factor Perception 的前端核心，提供：

- **视觉里程计**: 通过相机图像估计位姿变化
- **惯性里程计**: 通过 IMU 数据估计位姿变化
- **融合输出**: 两者结合提供高频、高精度里程计

**关键特性:**
- 输出频率: **200 Hz** (与 IMU 同步)
- 定位精度: **厘米级**
- 自动初始化: 支持静态和动态初始化
- 无需 GPU: 神经网络推理在相机内部运行

---

### 1.2 发布话题详解

#### 1.2.1 视觉话题

| 话题 | 类型 | 频率 | 深入说明 |
|------|------|------|----------|
| `rgb/image_rect/compressed` | CompressedImage | 20 Hz | JPEG 格式，相机内部编码，用 `image_transport` 解压 |
| `left/image_rect/compressed` | CompressedImage | 20 Hz | 左相机图像，OAK-D LR/SR 为彩色，其他为单色 |
| `depth/image_rect` | Image | 20 Hz | 深度图，对齐到左相机坐标系，单位为米 |
| `rgbd_image` | RGBDImage | - | RTAB-Map 专用，包含同步数据 + 特征 + 描述符 |

**使用建议:**
```bash
# 使用 image_transport 订阅压缩图像
ros2 run image_transport republish compressed raw --ros-args -r /factor_perception/rgb/image_rect/compressed:=/factor_perception/rgb/image_rect
```

#### 1.2.2 IMU 话题

| 话题 | 类型 | 频率 | 深入说明 |
|------|------|------|----------|
| `imu` | Imu | 200 Hz | 9轴数据，包含加速度、角速度、融合方向 |

**IMU 数据结构:**
```
linear_acceleration:  # 3轴加速度
  x, y, z            # 排除重力分量

angular_velocity:     # 3轴角速度 (rad/s)
  x, y, z

orientation:          # 9轴融合方向 (四元数)
  x, y, z, w         # BNO085/086 内部融合
```

#### 1.2.3 里程计话题

| 话题 | 类型 | 频率 | 深入说明 |
|------|------|------|----------|
| `odom` | Odometry | 200 Hz | VIO 输出，与 IMU 时间戳同步 |

**里程计数据结构:**
```
pose.pose:
  position: x, y, z           # 位置估计
  orientation: x, y, z, w     # 方向估计 (四元数)

twist.twist:
  linear: x, y, z             # 线速度
  angular: x, y, z            # 角速度
```

---

### 1.3 参数深入解析

#### 1.3.1 `publish_tf` (关键参数)

| 属性 | 值 |
|------|-----|
| 类型 | bool |
| 默认 | true |
| 推荐 | **false** (使用 EKF 融合时) |

**深入理解:**

```
publish_tf = true 时:
  Factor Perception 发布: odom → base_link
  TF 树: map → odom (RTAB-Map) → base_link (Factor-VIO)

publish_tf = false 时:
  Factor Perception 只发布 odom 话题，不发布 TF
  需要外部节点 (如 EKF) 发布: odom → base_link
  TF 树: map → odom (RTAB-Map) → base_link (EKF)
```

**决策指南:**
| 场景 | publish_tf | 说明 |
|------|------------|------|
| 单传感器导航 | true | 简单，直接使用 VIO |
| 多传感器融合 | false | 让 EKF 融合 VIO + IMU + 其他 |
| RK3588 嵌入式 | true | 减少计算负担 |
| 高精度定位 | false | EKF 可改善精度 |

#### 1.3.2 `depth_filter` (导航关键)

| 属性 | 值 |
|------|-----|
| 类型 | bool |
| 默认 | false |
| 推荐 | **true** (人形机器人导航) |

**深入理解:**

```
depth_filter = false:
  原始深度数据，可能包含噪点和鬼影
  导致 Costmap 出现虚假障碍物

depth_filter = true:
  高置信度滤波算法
  过滤低置信度深度点
  输出更干净的点云
  稍增加 CPU 使用 (~5-10%)
```

**鬼影障碍物成因:**
1.立体匹配错误
2. 边缘模糊
3. 反光表面
4. 低纹理区域

**启用 depth_filter 的效果:**
- Costmap 更干净
- 导航更稳定
- 避障更准确

#### 1.3.3 `ir_intensity` (暗光环境)

| 属性 | 值 |
|------|-----|
| 类型 | double |
| 范围 | 0.0 - 1.0 |
| 默认 | 0.0 |
| 推荐 | **0.4** (室内/暗光) |

**深入理解:**

OAK-D Pro 系列内置 IR 补光灯:
- 940nm 红外光 (不可见)
- 改善暗光环境下的深度测量
- 改善 VIO 特征提取

**推荐值:**
| 环境 | ir_intensity | 说明 |
|------|--------------|------|
| 室外白天 | 0.0 | 自然光充足 |
| 室内明亮 | 0.0-0.2 | 可选 |
| 室内暗光 | 0.3-0.5 | 推荐 |
| 夜间 | 0.5-0.8 | 必需 |

**注意:** 仅 OAK-D Pro / Pro W / Pro PoE 支持

#### 1.3.4 `min_feat_depth` (遮挡过滤)

| 属性 | 值 |
|------|-----|
| 类型 | double |
| 默认 | 0.0 |
| 推荐 | **0.3** (人形机器人) |

**深入理解:**

人形机器人行走时:
- 腿部、手臂可能遮挡相机
- 这些近距离特征会导致 VIO 误判
- 设置 min_feat_depth 过滤这些特征

**推荐值:**
| 载体类型 | min_feat_depth | 说明 |
|----------|----------------|------|
| 固定相机 | 0.0 | 无遮挡 |
| 移动手臂 | 0.2-0.3 | 过滤手臂 |
| 人形机器人 | 0.3-0.5 | 过滤腿部 |

#### 1.3.5 `blob_path` (AI 模型)

| 属性 | 值 |
|------|-----|
| 类型 | string |
| 默认 | "" (传统算法) |
| 推荐 | `HF-Net.blob` (深度学习) |

**深入理解:**

```
blob_path = "":
  使用传统特征检测 (ORB/SIFT)
  适合简单场景

blob_path = "HF-Net.blob":
  使用深度学习特征检测
  更鲁棒，更准确
  视觉位置识别 (Visual Place Recognition)
  相机内部推理，不占用主机 CPU/GPU
```

**HF-Net 优势:**
- 更好的特征提取
- 更好的闭环检测
- 更鲁棒的 SLAM

---

### 1.4 TF 坐系详解

#### 1.4.1 坐系定义

```
oak_base_frame:     相机基坐标系 (安装位置)
oak_left_camera_frame:    左相机坐标系
oak_left_camera_optical_frame:  左相机光心坐标系 (REP-103)
oak_right_camera_frame:   右相机坐标系
oak_rgb_camera_frame:     RGB相机坐标系 (OAK-D Pro W)
```

#### 1.4.2 坐系方向 (REP-103)

```
camera frame (相机坐标系):
  X轴: 前方
  Y轴: 左方
  Z轴: 上方

optical frame (光心坐标系):
  X轴: 右方
  Y轴: 下方
  Z轴: 前方 (光轴方向)
```

#### 1.4.3 TF 树结构

```
map└── odom (RTAB-Map 发布)└── base_link└── oak_base_frame (用户配置)
        ├── oak_left_camera_frame├── oak_left_camera_optical_frame
        ├── oak_right_camera_frame├── oak_rgb_camera_frame (可选)
```

---

### 1.5 初始化详解

#### 1.5.1 静态初始化

**条件:**
- 相机静止
- 环境有足够纹理

**步骤:**
1. 相机保持静止 2-3 秒
2. 避免面对白墙等无纹理区域
3. 系统自动完成初始化

**注意:**
- 仅能准确估计陀螺仪 bias
- 加速度计 bias 只能粗略估计

#### 1.5.2 动态初始化

**条件:**
- 相机移动
- 6自由度充分激励

**步骤:**
1. 相机连续移动
2. 包含前后左右上下移动
3. 包含旋转运动
4. 系统自动完成初始化

**优势:**
- 可准确估计加速度计和陀螺仪 bias

---

### 1.6 IMU 自校准

**何时需要:**
- VIO 精度和鲁棒性低于预期
- 加速度输出有较大 bias
- 部分 OAK-D 出厂未校准

**六位置法:**
```
1. 启动系统
2. 放置相机在6个方向 (X+, X-, Y+, Y-, Z+, Z-)
3. 每个方向静止至少1秒
4. Ctrl+C 终止，不要拔相机
5.重新启动，校准数据写入 flash
```

---

## 2. RTAB-Map Back-end 深入解析

### 2.1 核心原理

RTAB-Map (Real-Time Appearance-Based Mapping) 是 Factor Perception 的后端核心，提供：

- **SLAM**: 同时定位与建图
- **闭环检测**: 识别已访问区域，消除累积误差
- **地图管理**: 内存管理和多 session 支持
- **地图输出**: 2D/2.5D/3D 地图格式

**关键特性:**
- 深度集成 Factor-VIO 前端
- 使用神经网络处理后的数据 (非原始图像)
- 支持 hybrid SLAM、lifelong SLAM
- 支持 iSAM (增量平滑与建图)
- 支持多机器人 SLAM 和自动地图合并

---

### 2.2 运行模式

#### 2.2.1 SLAM 模式 (建图)

**参数:** `localization:=false`

```
功能:
- 创建新地图
- 增量建图
- 闭环检测
- 地图优化

适用场景:
- 首次探索新环境
- 环境发生变化后重新建图
```

#### 2.2.2 Localization 模式 (定位)

**参数:** `localization:=true`

```
功能:
- 在已有地图中定位
- 不创建新节点
- 重定位到已有地图适用场景:
- 已建图环境的导航
- 多次运行同一环境
```

---

### 2.3 配置文件详解

**默认配置:** `/opt/ros/humble/share/factor_perception/config/rtabmap.ini`

#### 2.3.1 关键参数分类

| 类别 | 参数前缀 | 说明 |
|------|----------|------|
| 地图生成 | `Grid/`, `GridGlobal/` | 2D 占据地图配置 |
| 闭环检测 | `Kp/`, `Vh/` | 特征匹配和视觉词袋 |
| 内存管理 | `Mem/` | 节点存储和管理 |
| 优化 | `Optimizer/` | 图优化和位姿优化 |

#### 2.3.2 Grid 参数详解

**推荐修改的参数:**

| 参数 | 默认值 | 说明 | 调整建议 |
|------|--------|------|----------|
| `Grid/CellSize` | 0.05m | 地图分辨率 | 人形机器人建议 0.02-0.05m |
| `Grid/RangeMin` | 0.0m | 最小深度范围 | 过滤近距离噪声 |
| `Grid/RangeMax` | 5.0m | 最大深度范围 | 根据传感器有效范围调整 |
| `Grid/MaxObstacleHeight` | 2.0m | 最大障碍物高度 | 根据机器人高度调整 |
| `Grid/MinGroundHeight` | 0.0m | 最小地面高度 | 根据地面实际情况调整 |
| `Grid/NormalsK` | 20 | 法向量计算邻居数 | 影响地面检测精度 |

**示例配置:**
```ini
# 人形机器人推荐配置
Grid/CellSize=0.03       # 更高分辨率
Grid/RangeMin=0.3        # 过滤近距离
Grid/RangeMax=3.0        # 深度传感器有效范围
Grid/MaxObstacleHeight=1.5  # 障碍物高度上限
```

#### 2.3.3 GridGlobal 参数详解

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `GridGlobal/MinClusterSize` | 20 | 最小聚类尺寸 (节点数) |
| `GridGlobal/Eroded` | false | 是否腐蚀地图边缘 |
| `GridGlobal/FillEmptyCells` | false | 填充空白区域 |

---

### 2.4 数据库管理

#### 2.4.1 数据库结构

**存储位置:** `database_path` 参数控制
- 默认: `~/rtabmap.db`
- Factor Perceptionlaunch 文件改为: `~/rtabmap.db`

**数据库内容:**
```
- 节点
  - 关键帧图像
  - 特征点和描述符
  - 位姿估计
  
- 链接
  - 相邻节点链接
  - 闭环链接
  
- 地图数据
  - 2D 占据地图
  - 3D 点云
```

#### 2.4.2 多 Session 管理

**Session 概念:**
```
每次启动系统 = 一个 Session
- 使用同一数据库会创建新 Session
- RTAB-Map 自动尝试匹配和合并 Sessions
- 实现 incremental mapping 和 lifelong SLAM
```

**管理建议:**
```
不要在同一数据库中存储不同区域的地图
- 除非它们后续可以合并
- 使用不同数据库文件管理不同区域
```

#### 2.4.3 数据库工具

**rtabmap-databaseViewer:**
```bash
# 打开数据库查看器
rtabmap-databaseViewer ~/rtabmap.db

功能:
- 浏览地图节点
- 查看 3D 点云
- 查看关键帧图像
- 离线优化地图
- 导出地图
- 3D重建
```

---

### 2.5 地图输出格式

#### 2.5.1 2D 占据地图 (OccupancyGrid)

**话题:** `/factor_perception/grid_map`

**特点:**
- 二值地图 (占用/空闲)
- 用于 Nav2 导航
- 与 AMCL 兼容

#### 2.5.2 2.5D 地图 (GridMap)

**话题:** `/factor_perception/grid_map`

**特点:**
- 多层地图 (海拔、障碍物等)
- 支持多层信息叠加
- 用于复杂导航场景

#### 2.5.3 3D 地图 (OctoMap)

**话题:** `/factor_perception/octomap`

**特点:**
- 八叉树 3D 表示
- 高效存储
- 用于 3D 导航和避障

---

### 2.6 闭环检测机制

#### 2.6.1 原理

```
闭环检测流程:
1. 提取当前帧全局描述符 (HF-Net)
2. 与数据库中的帧进行匹配
3. 验证几何一致性
4. 创建闭环链接
5. 执行图优化
```

#### 2.6.2 HF-Net 优势

```
HF-Net = Hybrid Feature Network
- 局部特征提取 (关键点)
- 全局描述符 (位置识别)
- 相机内推理，不占用主机资源
- 更鲁棒的闭环检测
```

---

### 2.7 与 Nav2 集成

#### 2.7.1 TF 树

```
SLAM 模式:
map└── odom (RTAB-Map 发布)
    └── base_link (Factor-VIO 发布)└── oak_base_frame

Localization 模式:
map└── odom (RTAB-Map 发布)
    └── base_link (Factor-VIO 发布)
```

#### 2.7.2 地图话题对应

| RTAB-Map 话题 | Nav2 使用 |
|--------------|-----------|
| `/factor_perception/grid_map` | `global_costmap` 输入 |
| `/factor_perception/octomap` | 3D 避障 (可选) |

#### 2.7.3 Nav2 参数配置

```yaml
global_costmap:
  global_costmap:
    ros__parameters:
      global_frame: map
      robot_base_frame: base_link
      
      # 使用 RTAB-Map 地图
      plugins: ["static_layer"]
      
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_topic: /factor_perception/grid_map
```

---

### 2.8 调试与优化

#### 2.8.1查看所有参数

```bash
ros2 run rtabmap_slam rtabmap --params
```

#### 2.8.2 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 闭环检测失败 | 特征不足 | 增加 HF-Net.blob |
| 地图漂移 | VIO 精度低 | 检查 IMU 校准 |
| 地图不更新 | 内存管理限制 | 调整 Mem/参数 |
| 高 CPU 占用 | Grid 分辨率高 | 降低 Grid/CellSize |

---

## 4. Nav2 Costmap 配置详解

### 4.1 核心参数说明

#### 4.1.1 机器人 Footprint

**配置方式:**
```yaml
# 圆形机器人 (推荐使用 radius)
footprint: "[[0.5, 0.5], [0.5, -0.5], [-0.5, -0.5], [-0.5, 0.5]]"

# 或使用半径
robot_radius: 0.5
```

**人形机器人推荐:**
- 中型人形机器人: footprint 边长 1.0m (半径约0.5m)
- 膨胀半径 `inflation_radius`: 0.6m (略大于机器人半径)

#### 4.1.2 Costmap 分辨率

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `resolution` | 0.03m | 人形机器人高分辨率 |
| `width/height` | 3.0m | local_costmap 尺寸 |

**分辨率选择:**
- 太低 (>0.1m): 导航粗糙，可能撞障碍物
- 太高 (<0.02m): CPU占用高，更新慢
- 推荐: 0.03-0.05m

#### 4.1.3 Obstacle Layer 参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `obstacle_range` | 2.5-3.0m | 深度传感器有效范围 |
| `raytrace_range` | 3.0-3.5m | 清除范围，略大于检测范围 |
| `max_obstacle_height` | 1.5m | 人形机器人视线高度 |
| `min_obstacle_height` | 0.05m | 过滤地面噪声 |

**关键点:**
- `raytrace_range` > `obstacle_range`: 清除远处障碍物
- `max_obstacle_height`: 根据相机安装高度调整

#### 4.1.4 Inflation Layer 参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `inflation_radius` | 0.6m | 略大于机器人半径 |
| `cost_scaling_factor` | 3.0 | 代价衰减速度 |

**inflation_radius 计算:**
```
inflation_radius = robot_radius + safety_margin
示例: 0.5m + 0.1m = 0.6m
```

**cost_scaling_factor:**
- 低值 (1-2): 膨胀区域代价高，机器人远离障碍物
- 高值 (5-10): 膨胀区域代价低，机器人可靠近障碍物

---

### 4.2 Local vs Global Costmap

| 参数 | Local Costmap | Global Costmap |
|------|---------------|----------------|
| `global_frame` | odom | map |
| `rolling_window` | true | false |
| `width/height` | 3m | 自动 (跟随地图) |
| `plugins` | obstacle + inflation | static + obstacle + inflation |

**Static Layer 配置:**
```yaml
static_layer:
  map_topic: /factor_perception/grid_map  # RTAB-Map 地图
  track_unknown_space: true
```

---

### 4.3 MPPI 控制器参数

#### 4.3.1 速度约束

```yaml
vx_max: 0.3    # 最大前进速度 (保守配置)
vx_min: -0.1   # 最大后退速度
wz_max: 0.5    # 最大旋转速度
```

#### 4.3.2 规划参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `time_steps` | 56 | 规划步数 |
| `model_dt` | 0.05s | 每步时间 |
| `batch_size` | 2000 | 采样轨迹数 |

**规划时长计算:**
```
time_steps × model_dt = 56 × 0.05 = 2.8秒
```

#### 4.3.3 Cost Critics 权重

| Critic | 权重 | 说明 |
|--------|------|------|
| `PathAlignCritic` | 2.0 | 路径跟随 |
| `GoalAlignCritic` | 1.0 | 目标接近 |
| `ObstaclesCritic` | 5.0 | 避障 |

**调参建议:**
- `ObstaclesCritic` 太低 → 撞障碍物
- `ObstaclesCritic` 太高 → 绕远路，路径不优化

---

### 4.4 话题映射

**Factor Perception → Nav2:**

| Factor Perception 话题 | Nav2 使用 |
|------------------------|-----------|
| `/factor_perception/odom` | `odom_topic` |
| `/factor_perception/depth/points` | `pointcloud` 障碍物层 |
| `/factor_perception/grid_map` | `map_topic` 静态层 |

---

### 4.5 调试命令

```bash
# 检查 Costmap 参数
ros2 param get /local_costmap/local_costmap resolution
ros2 param get /local_costmap/local_costmap inflation_radius

# 查看 Costmap 更新频率
ros2 topic hz /local_costmap/costmap_raw

# 手动清除 Costmap
ros2 service call /global_costmap/clear_entirely_global_costmap/nav2_msgs/srv/ClearEntireCostmap
```

---

## 5. 硬件知识

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