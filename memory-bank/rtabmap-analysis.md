# RTAB-Map 深度技术分析

> **来源**: GitHub 源码分析 (introlab/rtabmap, introlab/rtabmap_ros)
> **版本**: v0.23.1 (2025-10-13)
> **分析日期**: 2026-06-26

---

## 1. 项目概览

| 属性 | 值 |
|------|-----|
| 仓库 | https://github.com/introlab/rtabmap |
| 最新版本 | v0.23.1 (2025-10-13) |
| Stars | 3.9k |
| 协议 | BSD |
| 核心语言 | C++ (57.5%), C (35.4%) |
| ROS 支持 | Humble, Jazzy, Kilted, Rolling |
| 论文 | Labbe, M. (2014) "Real-Time Appearance-Based Mapping", ICRA |

---

## 2. 源码架构

### 2.1 目录结构

```
rtabmap/                              # 核心库（纯 C++，无 ROS 依赖）
├── corelib/
│   ├── include/rtabmap/core/
│   │   ├── Rtabmap.h              # ★ 主 SLAM 类 — 算法引擎
│   │   ├── Memory.h               # ★ 三层记忆管理
│   │   ├── BayesFilter.h          # ★ 贝叶斯回环检测
│   │   ├── VWDictionary.h         # 视觉词典 (Bag of Words)
│   │   ├── Signature.h            # 地图节点
│   │   ├── Registration.h         # 帧间配准
│   │   ├── Odometry.h             # 视觉里程计
│   │   ├── Optimizer.h            # 图优化 (g2o/GTSAM)
│   │   ├── EpipolarGeometry.h     # 本质矩阵验证
│   │   └── Parameters.h           # 所有参数定义
│   └── src/                       # ~60 个 .cpp 实现文件
├── guilib/                        # GUI (Database Viewer, Map Viewer)
├── tools/                         # 命令行工具
└── examples/                      # 示例

rtabmap_ros/                       # ROS 2 封装
├── rtabmap_slam/
│   ├── src/
│   │   ├── CoreWrapper.cpp        # ★ ROS2 Node 实现 (~2000+ 行)
│   │   └── CoreNode.cpp           # main() 入口
│   ├── include/rtabmap_slam/
│   │   └── CoreWrapper.h          # 类声明 (~700+ 行)
│   └── launch/                    # launch 文件
├── rtabmap_msgs/                  # 自定义消息/服务
├── rtabmap_sync/                  # CommonDataSubscriber — 数据同步
├── rtabmap_costmap_plugins/       # Nav2 Costmap 插件
├── rtabmap_viz/                   # 3D 可视化
└── rtabmap_launch/                # 标准 launch 文件
```

### 2.2 关键类关系

```
CoreWrapper (ROS2 Node)
  ├── rtabmap::Rtabmap          ← 核心 SLAM 引擎
  │   ├── rtabmap::Memory       ← 三层记忆管理
  │   │   ├── Signature         ← 地图节点
  │   │   ├── VWDictionary      ← 视觉词典
  │   │   └── Registration      ← 帧间配准
  │   ├── rtabmap::BayesFilter  ← 回环概率模型
  │   ├── rtabmap::Optimizer    ← 图优化
  │   └── rtabmap_util::MapsManager ← 地图发布
  ├── rtabmap_sync::CommonDataSubscriber ← 数据同步
  └── tf2_ros::TransformBroadcaster ← TF 发布
```

---

## 3. 核心 SLAM 算法 — Rtabmap::process()

### 3.1 完整处理流水线

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

### 3.2 源码级关键逻辑

**节点创建 — Memory::update():**
```cpp
// Memory.h 中的核心数据结构
std::map<int, Signature*> _signatures;  // 所有节点（含 LTM）
std::set<int> _stMem;                   // 短期记忆（最近 N 个节点 ID）
std::map<int, double> _workingMem;      // 工作记忆（节点 ID → 年龄）
// 不在 STM 也不在 WM 的 = LTM（存储在 SQLite 数据库）
```

**回环检测 — BayesFilter:**
```cpp
// BayesFilter.h — 概率模型
std::vector<double> _predictionLC;  // 转移概率: {Vp, Lc, l1, l2, ...}
// Vp = Virtual Place 先验概率
// Lc = 回环权重
// l1, l2... = 各位置转移概率

// 后验计算 = 预测 × 似然，然后归一化
std::map<int, float> computePosterior(
    const Memory* memory, 
    const std::map<int, float>& likelihood);
```

**图优化:**
```cpp
// Optimizer::Optimizer 策略
// 0 = g2o (传统)
// 2 = GTSAM (iSAM2, 增量优化，默认)
Optimizer::Strategy = 2
GTSAM::Incremental = true
```

**回环验证流程（Rtabmap::process 源码）:**
```cpp
// 1. 计算似然
rawLikelihood = _memory->computeLikelihood(signature, signaturesToCompare);
likelihood = adjustLikelihood(rawLikelihood);

// 2. 贝叶斯后验
posterior = _bayesFilter->computePosterior(_memory, likelihood);

// 3. 取最高概率假设
_highestHypothesis = 1 - posterior.begin()->second; // 减去虚拟位置

// 4. 阈值判断
if (_highestHypothesis.second >= loopThr) {
    // 5. 几何验证
    if (_verifyLoopClosureHypothesis) {
        _epipolarGeometry->check(signature, candidateSignature);
    }
    // 6. 创建回环链接
    // 7. 图优化
}
```

---

## 4. 三层记忆系统（Memory Management）

### 4.1 架构图

```
┌──────────────────────────────────────────────────┐
│                 STM (短期记忆)                      │
│  _stMem: set<int>, 大小 = Mem\STMSize (默认 10)    │
│  - 最近访问的 N 个节点                              │
│  - 快速访问，全量数据在 RAM                         │
│  - 满了之后旧节点 → 通过 Rehearsal 巩固             │
└──────────────────────┬───────────────────────────┘
                       │ Rehearsal (相似度 ≥ 0.9)
                       ▼
┌──────────────────────────────────────────────────┐
│                 WM (工作记忆)                       │
│  _workingMem: map<int, double> (id → 年龄)         │
│  - 经过巩固的重要节点                               │
│  - 大小 = Mem\RecentWmRatio × STM 大小             │
│  - 满时最旧的 → 压缩 → LTM                         │
└──────────────────────┬───────────────────────────┘
                       │ reduceGraph / 压缩
                       ▼
┌──────────────────────────────────────────────────┐
│                 LTM (长期记忆)                      │
│  存储在 SQLite 数据库 (~/rtabmap.db)               │
│  - 容量无限（磁盘存储）                             │
│  - 按需加载（回环检测时加载候选节点）                 │
│  - 压缩存储（图像、深度、特征均可压缩）               │
└──────────────────────────────────────────────────┘
```

### 4.2 关键机制

**Rehearsal（记忆巩固）:**
```cpp
// 当新节点与 STM 中某节点相似度 ≥ _rehearsalSimilarity (0.9)
// → 合并两个节点（将新节点的观察转移到旧节点）
// → 类似人脑的记忆巩固过程
void rehearsal(Signature* signature, Statistics* stats)
```

**STM → WM 转移:**
```cpp
void moveSignatureToWMFromSTM(int id, int* reducedTo = 0);
```

**LTM → WM 转移（按需加载）:**
```cpp
void addSignatureToWmFromLTM(Signature* signature);
// 在回环检测时，将 LTM 中的候选节点加载到 WM
```

**图缩减:**
```cpp
// 保持 WM 大小恒定，将最旧节点移到 LTM
std::list<int> forget(const std::set<int>& ignoredIds = std::set<int>());
```

---

## 5. ROS 2 集成 — CoreWrapper 详解

### 5.1 类结构

```cpp
class CoreWrapper : public rclcpp::Node, 
                    public rtabmap_sync::CommonDataSubscriber
{
    // 核心 SLAM 引擎
    rtabmap::Rtabmap rtabmap_;
    
    // 传感器数据同步
    CommonDataSubscriber — 处理多相机同步
    
    // 异步处理架构
    rclcpp::TimerBase::SharedPtr syncTimer_;  // 定时触发处理
    struct SyncData { ... };                  // 同步数据缓冲
    rclcpp::CallbackGroup::SharedPtr processingCallbackGroup_;
};
```

### 5.2 数据处理流程

```
订阅端                          异步回调                        处理定时器
─────────────────────────────────────────────────────────────────────────
/camera/rgbd/image    ──▶  commonMultiCameraCallback()   ──▶ syncTimer_
/camera/depth/image   ──▶     ↓                              │    │
/camera/color/image   ──▶  数据存入 syncData_              │    ▼
/camera/info1         ──▶  (mutex 保护)                    │  processAsync()
/camera/info2         ──▶                                   │    │
/imu                  ──▶  imuAsyncCallback()              │    ▼
                                                                  process()
                                                                   │
                                                                   ▼
                                                            rtabmap_.process(data, ...)
```

**关键设计**: 使用 `callback_group` 隔离，确保传感器回调、TF 广播、处理逻辑**不互相阻塞**。

### 5.3 发布的话题和服务

**关键话题:**

| 话题 | 消息类型 | 用途 |
|------|---------|------|
| `/factor_perception/rtabmap/grid_map` | `nav_msgs/OccupancyGrid` | **2D 占据网格（Nav2 用）** |
| `/factor_perception/rtabmap/cloud_obstacles` | `sensor_msgs/PointCloud2` | 障碍物点云 |
| `/factor_perception/rtabmap/cloud_map` | `sensor_msgs/PointCloud2` | 3D 地图点云 |
| `/factor_perception/rtabmap/odom` | `nav_msgs/Odometry` | 里程计 |
| `/factor_perception/rtabmap/octomap` | `octomap_msgs/OctomapWithPose` | 3D Octomap |
| `/factor_perception/localization_pose` | `geometry_msgs/PoseWithCovarianceStamped` | 定位位姿 |
| `/factor_perception/rtabmap/mapData` | `rtabmap_msgs/MapData` | 完整地图数据 |
| `/factor_perception/rtabmap/info` | `rtabmap_msgs/Info` | 统计信息 |

**关键服务:**

| 服务 | 功能 |
|------|------|
| `/rtabmap/reset` | 重置内存 |
| `/rtabmap/pause` / `resume` | 暂停/恢复处理 |
| `/rtabmap/load_database` | 加载数据库 |
| `/rtabmap/set_mode_localization` | 切换定位模式 |
| `/rtabmap/set_mode_mapping` | 切换建图模式 |
| `/rtabmap/get_map_data` | 获取地图数据 |
| `/rtabmap/detect_more_loop_closures` | 强制检测回环 |
| `/rtabmap/global_bundle_adjustment` | 全局束调整 |

### 5.4 TF 发布行为

```cpp
// CoreWrapper 内部发布 map → odom TF
// TF 广播频率: 与处理频率同步
// tfDelay = 0.05s, tfTolerance = 0.1s

// 注意：当 graph optimization 启用时
// 才有 map → odom TF 的修正
// 纯里程计模式下只有 odom → base_link
```

---

## 6. 关键参数详解（与项目配置对照）

### 6.1 回环检测参数

| 参数 | 项目值 | 含义 | 源码位置 |
|------|--------|------|---------|
| `Rtabmap/LoopThr` | 0.11 | 回环相似度阈值 | Rtabmap::process() |
| `Kp/NndrRatio` | 0.8 | 特征匹配 Lowe's 比率 | Memory::computeLikelihood() |
| `Vis/CorNNDR` | 0.8 | 视觉相关 NNDR | RegistrationVis |
| `Vis/MinInliers` | 20 | RANSAC 最小内点数 | EpipolarGeometry |
| `Bayes/PredictionLC` | 0.1 0.36 ... | 贝叶斯转移概率矩阵 | BayesFilter |

### 6.2 记忆管理参数

| 参数 | 项目值 | 含义 | 源码位置 |
|------|--------|------|---------|
| `Mem/STMSize` | 10 | 短期记忆大小 | Memory::addSignatureToStm() |
| `Mem/IncrementalMemory` | true/false | 增量记忆（SLAM）/ 只读（定位） | Memory::update() |
| `Mem/InitWMWithAllNodes` | true/false | 初始化时加载所有节点 | Memory::init() |
| `Mem/RehearsalSimilarity` | 0.9 | 记忆巩固相似度阈值 | Memory::rehearsal() |
| `Mem/ReduceGraph` | true | 图缩减（保持 STM 大小） | Memory::cleanup() |

### 6.3 3D 建图参数

| 参数 | 项目值 | 含义 | 源码位置 |
|------|--------|------|---------|
| `Grid/3D` | true | 启用 3D 网格 | LocalGridMaker |
| `Grid/CellSize` | 0.05 | 体素大小 | OccupancyGrid |
| `Grid/MaxObstacleHeight` | 1.5 | 障碍物最大高度 | Grid::filterByHeight() |
| `Grid/FootprintHeight` | 1.4 | 机器人高度 | Grid::setFootprint() |
| `Grid/FootprintRadius` | 0.5 | 机器人半径 | Grid::setFootprint() |

### 6.4 优化器参数

| 参数 | 项目值 | 含义 | 源码位置 |
|------|--------|------|---------|
| `Optimizer/Strategy` | 2 | 优化器选择 (0=g2o, 2=GTSAM) | Optimizer::optimizeGraph() |
| `GTSAM/Incremental` | true | 增量优化（iSAM2） | GTSAM Optimizer |
| `RGBD/LocalBundleOnLoopClosure` | true | 回环时局部束调整 | Memory::update() |

---

## 7. RtabmapThread — 处理线程架构

### 7.1 生产者-消费者模式

```cpp
// RtabmapThread 实现了事件驱动的 SLAM 处理线程

// 数据流入:
SensorEvent → handleEvent() → addData() → _dataBuffer (deque)
OdometryEvent → handleEvent() → addData() → _dataBuffer

// 数据流出:
_dataBuffer → getData() → process() → _rtabmap->process()
```

### 7.2 状态机

```
kStateDetecting → process() → 处理传感器数据
kStateProcessCommand → 处理控制命令 (init, reset, pause, goal...)
```

### 7.3 速率控制

```cpp
// 检测率限制
if (_rate > 0.0f && timeSinceLastFrame < 1.0f/_rate) {
    ignoreFrame = true;  // 跳过帧
}
```

---

## 8. 数据流与 Nav2 集成

### 8.1 完整数据流

```
Factor Perception SDK
  │
  ├── /camera/rgbd_image (rtabmap_msgs/RGBDImage)
  │       │
  │       ▼ rtabmap_slam::CoreWrapper
  │       ├── commonMultiCameraCallback()
  │       │   └── syncTimer_ → processAsync()
  │       │
  │       └── rtabmap_.process(data, odom, ...)
  │           ├── Memory::update() — 创建节点
  │           ├── computeLikelihood() — BoW 相似度
  │           ├── BayesFilter — 后验概率
  │           ├── EpipolarGeometry — 几何验证
  │           ├── Optimizer — GTSAM 图优化
  │           └── MapsManager — 发布地图
  │
  ├── /factor_perception/map (OccupancyGrid) ──→ Nav2 Global Costmap (static_layer)
  ├── /factor_perception/cloud_obstacles (PointCloud2) ──→ Nav2 ObstacleLayer
  ├── /factor_perception/odom (Odometry) ──→ velocity_smoother
  └── TF: map → odom → base_link
```

### 8.2 Nav2 集成配置

```yaml
# Nav2 Global Costmap 使用 RTAB-Map 地图
global_costmap:
  static_layer:
    plugin: "nav2_costmap_2d::StaticLayer"
    map_topic: /factor_perception/map
    subscribe_to_updates: true

# Obstacle Layer 使用 RTAB-Map 3D 障碍物点云
obstacle_layer:
  pointcloud:
    topic: /factor_perception/cloud_obstacles
    data_type: "PointCloud2"
    max_obstacle_height: 1.5
    min_obstacle_height: 0.05
```

---

## 9. 工程评估与调参建议

### 9.1 当前配置评估

| 方面 | 评价 | 说明 |
|------|------|------|
| subscribe_rgbd | ✅ 正确 | Factor Perception 预同步数据，单订阅零拷贝 |
| Grid/3D = true | ✅ 正确 | 启用 3D 建图，障碍物点云正确生成 |
| GTSAM 增量优化 | ✅ 正确 | 实时性好，适合嵌入式 |
| RehearsalSimilarity = 0.9 | ✅ 正确 | 较严格的巩固阈值，避免错误合并 |
| ProximityBySpace + ProximityByTime | ✅ 正确 | 双重回环检测 |

### 9.2 潜在调参建议

| 参数 | 当前值 | 建议 | 原因 |
|------|--------|------|------|
| `Rtabmap/LoopThr` | 0.11 | 考虑 0.15-0.20 | 低纹理环境容易误回环 |
| `Kp/NndrRatio` | 0.8 | 考虑 0.7 | 与 LoopThr 配合，减少误匹配 |
| `RGBD/LinearUpdate` | 0.1m | 保持 | 适合人形机器人尺度 |
| `RGBD/AngularUpdate` | 0.1rad | 保持 | 适合人形机器人尺度 |
| `Grid/FootprintHeight` | 1.4 | 根据实际相机高度调整 | 影响障碍物过滤 |
| `Grid/FootprintRadius` | 0.5 | 根据实际机器人尺寸调整 | 影响 footprint 计算 |

### 9.3 subscribe_rgbd 与 Factor Perception 集成

```python
# 项目 launch 文件配置
'subscribe_rgb': False,
'subscribe_depth': False,
'subscribe_rgbd': True,  # ← 关键选择

# Factor Perception 发布 /factor_perception/rgbd_image
# 消息类型: rtabmap_msgs/RGBDImage
# 包含: RGB + Depth + CameraInfo + 预计算特征 (HF-Net)
```

**优势**:
- RTAB-Map 接收**已同步的 RGBD 图像 + 预计算特征**
- 无需自己做特征提取，大幅降低 CPU 负载
- 单订阅保证时间同步

---

## 10. RTAB-Map vs 其他 SLAM 方案

| 特性 | RTAB-Map | ORB-SLAM3 | Cartographer |
|------|----------|-----------|--------------|
| 回环检测 | BoW + Bayes Filter | BoW + 姿态图 | 子地图匹配 |
| 记忆管理 | STM/WM/LTM 三层 | 固定窗口 | 子地图 |
| 终身 SLAM | ✅ 原生支持 | ❌ | ❌ |
| 多地图 | ✅ 自动管理 | 手动 | 手动 |
| 3D Octomap | ✅ 原生 | 需转换 | ✅ |
| ROS 集成 | ✅ 成熟 | ✅ | ✅ |
| 计算量 | 中等 | 高 | 高 |
| 适用场景 | 长期运行、多环境 | 短时高精度 | 大场景建图 |

---

## 11. RTAB-Map 在 nav24r 中的角色

```
┌─────────────────────────────────────────────────────────┐
│  RTAB-Map 在 nav24r 系统中                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  角色：                                                │
│  ┌─────────────────────────────────────────────┐       │
│  │  感知层 → 建图层 → 定位层                     │       │
│  │                                             │       │
│  │  Factor Perception → RTAB-Map → Nav2       │       │
│  │  (VIO + Depth)      (SLAM)     (Navigation) │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  核心贡献：                                            │
│  1. 3D 占据栅格地图 → Nav2 Costmap 静态层              │
│  2. 障碍物点云 → Nav2 Costmap 障碍层                   │
│  3. 地图→里程计 TF 修正（回环校正漂移）                 │
│  4. 定位模式下的实时重定位                              │
│  5. Octomap 导出（用于外部工具分析）                    │
│                                                         │
│  关键理解：                                            │
│  • RTAB-Map 自己不做 VIO（它用外部里程计）             │
│  • Factor-VIO 提供 odom，RTAB-Map 用它做图优化         │
│  • 回环检测时，RTAB-Map 修正 map→odom 的 transform     │
│  • 3D Grid 产生障碍物点云，直接喂给 Nav2              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 12. 核心算法创新点

### 12.1 贝叶斯回环预测（区别于传统方法）

传统方法：基于几何验证（scan matching, PnP）→ 计算量大
RTAB-Map：先用 Bayes Filter **预测**最可能的位置，再验证 → 大幅减少计算量

```cpp
// 1. 预测: 基于运动模型
_bayesFilter->computePosterior(memory, likelihood);
// 2. 只验证最高概率的假设（而非所有候选）
// 3. 通过 → 创建回环链接 → 图优化
```

### 12.2 终身 SLAM（STM/WM/LTM）

```
其他 SLAM 系统：固定大小内存 → 必须删除旧数据
RTAB-Map:     STM/WM/LTM → 旧数据自动移到磁盘，需要时再加载
             → 支持数小时/数天的连续运行
```

### 12.3 Rehearsal（记忆巩固）

```
新节点进入 STM → 如果与已有节点高度相似 → 合并
类似人脑：相似记忆不重复存储，而是巩固到已有记忆
→ 节省内存，提高搜索效率
```

---

## 13. 调试命令速查

```bash
# 查看所有 RTAB-Map 参数
ros2 run rtabmap_slam rtabmap --params

# 查看 RTAB-Map 节点信息
ros2 node info /rtabmap/rtabmap

# 查看发布的 TF
ros2 topic echo /tf | grep -E "map|odom"

# 查看地图话题
ros2 topic echo /factor_perception/map --once

# 查看障碍物点云
ros2 topic echo /factor_perception/cloud_obstacles --once

# 查看回环统计
ros2 topic echo /factor_perception/rtabmap/info

# 打开数据库查看器
rtabmap-databaseViewer ~/rtabmap.db

# 导出 Octomap
rtabmap-export --db ~/rtabmap.db --output ~/map.bt --resolution 0.02
```

---

## 14. 常见问题与解决

| 问题 | 源码级原因 | 解决方案 |
|------|-----------|---------|
| 回环检测失败 | LoopThr 太低 / NNDR 太松 | 提高 LoopThr 到 0.15-0.20 |
| 误回环（低纹理） | Bayes Filter 预测不准确 | 提高 MinInliers, 降低 NNDR |
| 地图漂移 | 回环检测频率不够 | 降低 LinearUpdate/AngularUpdate |
| 高 CPU | Grid/3D 分辨率太高 | 提高 CellSize 到 0.05 |
| 内存溢出 | STM 太大 | 降低 Mem/STMSize |
| 图优化慢 | GTSAM 增量未启用 | 确保 GTSAM/Incremental = true |

---

*Created: 2026-06-26 | Maintainer: 智库专家 (Knowledge Expert)*
*References: introlab/rtabmap, introlab/rtabmap_ros, Labbe (2014) ICRA*
