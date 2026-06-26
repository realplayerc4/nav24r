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

### 2.1.1 源码架构

```
rtabmap/                              # 核心库（纯 C++，无 ROS 依赖）
├── corelib/
│   ├── include/rtabmap/core/
│   │   ├── Rtabmap.h             # ★ 主 SLAM 类 — 算法引擎
│   │   ├── Memory.h              # ★ 三层记忆管理
│   │   ├── BayesFilter.h         # ★ 贝叶斯回环检测
│   │   ├── VWDictionary.h        # 视觉词典（BoW）
│   │   ├── Signature.h           # 地图节点
│   │   ├── Registration.h        # 帧间配准
│   │   ├── EpipolarGeometry.h    # 本质矩阵验证
│   │   ├── Odometry.h            # 视觉里程计
│   │   ├── Optimizer.h           # 图优化（g2o/GTSAM）
│   │   └── Parameters.h          # 所有参数定义
│   └── src/                      # ~60 个 .cpp 实现文件

rtabmap_ros/                       # ROS 2 封装
├── rtabmap_slam/
│   ├── src/
│   │   ├── CoreWrapper.cpp       # ★ ROS2 Node 实现 (~2000+ 行)
│   │   └── CoreNode.cpp          # main() 入口
│   ├── include/rtabmap_slam/
│   │   └── CoreWrapper.h         # 类声明 (~700+ 行)
│   └── launch/
├── rtabmap_msgs/                  # 自定义消息/服务
├── rtabmap_sync/                  # CommonDataSubscriber — 数据同步
└── rtabmap_viz/                   # 3D 可视化
```

### 2.1.2 核心类关系

```
CoreWrapper (ROS2 Node, rclcpp::Node)
  ├── rtabmap::Rtabmap          ← 核心 SLAM 引擎
  │   ├── rtabmap::Memory       ← 三层记忆管理
  │   │   ├── Signature         ← 地图节点
  │   │   ├── VWDictionary      ← 视觉词典 (BoW)
  │   │   └── Registration      ← 帧间配准
  │   ├── rtabmap::BayesFilter  ← 回环概率模型
  │   ├── rtabmap::Optimizer    ← 图优化 (g2o/GTSAM)
  │   └── rtabmap_util::MapsManager ← 地图发布
  ├── rtabmap_sync::CommonDataSubscriber ← 数据同步
  └── tf2_ros::TransformBroadcaster ← TF 发布
```

### 2.1.3 异步处理架构

```cpp
// CoreWrapper 使用 callback_group 隔离不同执行流
processingCallbackGroup_ → syncTimer_ → processAsync() → process()
                                                      ↓
                                              rtabmap_.process(data, ...)
                                                      ↓
                                          Memory::update() → 创建节点
                                          computeLikelihood() → BoW 相似度
                                          BayesFilter → 后验概率
                                          EpipolarGeometry → 几何验证
                                          Optimizer → GTSAM 图优化
                                          MapsManager → 发布地图
```

**关键设计**: 传感器回调、TF 广播、处理逻辑使用不同 `callback_group`，确保**不互相阻塞**。

### 2.1.4 RtabmapThread — 处理线程

```cpp
// 生产者-消费者模式
// 数据流入:
SensorEvent/OdometryEvent → handleEvent() → addData() → _dataBuffer (deque)

// 数据流出:
_dataBuffer → getData() → process() → _rtabmap->process(data, odom, ...)
```

**状态机**: `kStateDetecting` (处理传感器数据) → `kStateProcessCommand` (处理控制命令)

**速率控制**: 检测率限制（`Rtabmap/DetectionRate`），跳过过快帧。

---

### 2.2 核心算法 — Rtabmap::process() 流水线

```
输入: RGBD Image + Odometry
  │
  ├─[1] Memory::update() — 创建新节点 (Signature)
  │    ├── 特征提取 (ORB/SIFT/SUPERPOINT)
  │    ├── 创建 Signature（含特征、深度、位姿）
  │    ├── 添加到 STM（短期记忆）
  │    └── Rehearsal（记忆巩固：相似节点合并）
  │
  ├─[2] 局部回环检测 — 时间维度 (ProximityByTime)
  │    └── 检查 STM 中时间相近的节点
  │
  ├─[3] 计算似然 (computeLikelihood)
  │    ├── BoW 相似度（TF-IDF 加权）
  │    └── 返回每个候选节点的似然值
  │
  ├─[4] BayesFilter::computePosterior()
  │    ├── 贝叶斯预测（运动模型）
  │    └── 似然更新 → 后验概率分布
  │
  ├─[5] 回环假设选择
  │    ├── 取最高后验概率的节点
  │    ├── 阈值判断: posterior >= LoopThr (0.11)
  │    └── 几何验证: EpipolarGeometry / RANSAC
  │
  ├─[6] 图优化 (Optimizer)
  │    ├── 验证通过 → 添加 Loop Closure Link
  │    └── g2o / GTSAM (iSAM2) 增量优化
  │
  └─[7] 发布结果
       ├── mapData / mapGraph（地图数据）
       ├── cloud_map / cloud_obstacles（点云）
       ├── odom → base_link TF
       └── 2D OccupancyGrid (用于 Nav2)
```

**源码级回环验证流程:**
```cpp
// 1. 计算似然
rawLikelihood = _memory->computeLikelihood(signature, signaturesToCompare);
likelihood = adjustLikelihood(rawLikelihood);

// 2. 贝叶斯后验
posterior = _bayesFilter->computePosterior(_memory, likelihood);

// 3. 取最高概率假设（减去虚拟位置）
_highestHypothesis = 1 - posterior.begin()->second;

// 4. 阈值判断
if (_highestHypothesis.second >= loopThr) {
    // 5. 几何验证
    if (_verifyLoopClosureHypothesis) {
        _epipolarGeometry->check(signature, candidateSignature);
    }
    // 6. 创建回环链接 → 7. 图优化
}
```

### 2.3 三层记忆系统（Memory Management）

```
┌──────────────────────────────────────────────────┐
│                 STM (短期记忆)                      │
│  _stMem: set<int>, 大小 = Mem\STMSize (默认 10)    │
│  - 最近访问的 N 个节点                              │
│  - 快速访问，全量数据在 RAM                         │
└──────────────────────┬───────────────────────────┘
                       │ Rehearsal (相似度 ≥ 0.9)
                       ▼
┌──────────────────────────────────────────────────┐
│                 WM (工作记忆)                       │
│  _workingMem: map<int, double> (id → 年龄)         │
│  - 经过巩固的重要节点                               │
│  - 大小 = Mem\RecentWmRatio × STM 大小             │
└──────────────────────┬───────────────────────────┘
                       │ reduceGraph / 压缩
                       ▼
┌──────────────────────────────────────────────────┐
│                 LTM (长期记忆)                      │
│  存储在 SQLite 数据库 (~/rtabmap.db)               │
│  - 容量无限（磁盘存储）                             │
│  - 按需加载（回环检测时加载候选节点）                 │
└──────────────────────────────────────────────────┘
```

**Rehearsal（记忆巩固）:**
```cpp
// 当新节点与 STM 中某节点相似度 ≥ _rehearsalSimilarity (0.9)
// → 合并两个节点（将新节点的观察转移到旧节点）
void rehearsal(Signature* signature, Statistics* stats)
```

### 2.4 ROS 2 集成 — CoreWrapper

**关键话题:**

| 话题 | 消息类型 | 用途 |
|------|---------|------|
| `/factor_perception/rtabmap/grid_map` | `nav_msgs/OccupancyGrid` | **2D 占据网格（Nav2 用）** |
| `/factor_perception/rtabmap/cloud_obstacles` | `sensor_msgs/PointCloud2` | 障碍物点云 |
| `/factor_perception/rtabmap/cloud_map` | `sensor_msgs/PointCloud2` | 3D 地图点云 |
| `/factor_perception/rtabmap/odom` | `nav_msgs/Odometry` | 里程计 |
| `/factor_perception/rtabmap/octomap` | `octomap_msgs/OctomapWithPose` | 3D Octomap |

**关键服务:**

| 服务 | 功能 |
|------|------|
| `/rtabmap/reset` | 重置内存 |
| `/rtabmap/set_mode_localization` | 切换定位模式 |
| `/rtabmap/set_mode_mapping` | 切换建图模式 |
| `/rtabmap/detect_more_loop_closures` | 强制检测回环 |

**TF 发布行为:**
```cpp
// CoreWrapper 内部发布 map → odom TF
// 注意：当 graph optimization 启用时才有 map → odom TF 的修正
```

### 2.5 关键参数详解

#### 2.5.1 回环检测参数

| 参数 | 含义 | 源码位置 |
|------|------|---------|
| `Rtabmap/LoopThr` | 回环相似度阈值（越低越严格） | Rtabmap::process() |
| `Kp/NndrRatio` | 特征匹配 Lowe's 比率 | Memory::computeLikelihood() |
| `Vis/CorNNDR` | 视觉相关 NNDR | RegistrationVis |
| `Vis/MinInliers` | RANSAC 最小内点数 | EpipolarGeometry |
| `Bayes/PredictionLC` | 贝叶斯转移概率矩阵 | BayesFilter |

#### 2.5.2 记忆管理参数

| 参数 | 含义 | 源码位置 |
|------|------|---------|
| `Mem/STMSize` | 短期记忆大小 | Memory::addSignatureToStm() |
| `Mem/IncrementalMemory` | 增量记忆（SLAM）/ 只读（定位） | Memory::update() |
| `Mem/InitWMWithAllNodes` | 初始化时加载所有节点 | Memory::init() |
| `Mem/RehearsalSimilarity` | 记忆巩固相似度阈值 | Memory::rehearsal() |
| `Mem/ReduceGraph` | 图缩减（保持 STM 大小） | Memory::cleanup() |

#### 2.5.3 3D 建图参数

| 参数 | 含义 | 源码位置 |
|------|------|---------|
| `Grid/3D` | 启用 3D 网格 | LocalGridMaker |
| `Grid/CellSize` | 体素大小 | OccupancyGrid |
| `Grid/MaxObstacleHeight` | 障碍物最大高度 | Grid::filterByHeight() |
| `Grid/FootprintHeight` | 机器人高度 | Grid::setFootprint() |
| `Grid/FootprintRadius` | 机器人半径 | Grid::setFootprint() |

### 2.6 工程评估与调参建议

| 方面 | 评价 | 说明 |
|------|------|------|
| subscribe_rgbd | ✅ 正确 | Factor Perception 预同步数据，单订阅零拷贝 |
| Grid/3D = true | ✅ 正确 | 启用 3D 建图，障碍物点云正确生成 |
| GTSAM 增量优化 | ✅ 正确 | 实时性好，适合嵌入式 |
| RehearsalSimilarity = 0.9 | ✅ 正确 | 较严格的巩固阈值，避免错误合并 |

| 参数 | 当前值 | 建议 | 原因 |
|------|--------|------|------|
| `Rtabmap/LoopThr` | 0.11 | 考虑 0.15-0.20 | 低纹理环境容易误回环 |
| `Kp/NndrRatio` | 0.8 | 考虑 0.7 | 与 LoopThr 配合，减少误匹配 |
| `Grid/FootprintHeight` | 1.4 | 根据实际相机高度调整 | 影响障碍物过滤 |
| `Grid/FootprintRadius` | 0.5 | 根据实际机器人尺寸调整 | 影响 footprint 计算 |

---

## 3. Nav2 Costmap 配置详解

### 3.1 核心参数说明

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

## 4. 硬件知识

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

## 5. 软件知识

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

## 6. 运维知识

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

## 7. 故障知识

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

## 8. 最佳实践

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