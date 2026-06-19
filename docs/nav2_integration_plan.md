# Nav2 集成方案 - nav24r 项目

## 当前状态

### ✅ 已完成
- RTAB-Map SLAM 已集成（支持建图和定位）
- Factor Perception (OAK-D Pro) 已配置
- nav2_params.yaml 配置文件已创建
- nav2.launch.py 启动文件已创建

### ❌ 待解决问题

1. **TF 树冲突** - RTAB-Map 和 Nav2 的 TF 发布可能冲突
2. **地图话题不匹配** - RTAB-Map 发布 `/rtabmap/grid_map`，Nav2 期望 `/map`
3. **Costmap 配置不完整** - 缺少 global_costmap 配置
4. **里程计话题不明确** - 需要确认 RTAB-Map VIO 的话题
5. **Launch 文件未集成** - 缺少统一的启动文件

## 解决方案

### 方案 A: RTAB-Map 作为实时地图源（推荐）

**适用场景**: 在未知环境中实时建图和导航

**架构**:
```
Factor Perception (OAK-D Pro)
    ↓
    发布: RGB-D 图像, 点云, IMU
    ↓
RTAB-Map SLAM
    ↓
    发布: /rtabmap/grid_map → 重映射到 /map
    发布: odom → base_link TF
    发布: /tf (map → odom)
    ↓
Nav2 Stack
    ↓
    订阅: /map, odom, 点云
    提供: 导航服务
```

**优点**:
- 实时建图和定位
- 适合探索未知环境
- 充分利用 RTAB-Map 的 SLAM 能力

**实施步骤**:

1. 创建统一的 launch 文件
2. 配置话题重映射
3. 完善 costmap 配置
4. 验证 TF 树
5. 测试导航

### 方案 B: 独立地图服务器

**适用场景**: 在已知环境中导航

**架构**:
```
阶段 1: 建图
Factor Perception → RTAB-Map → 保存地图文件

阶段 2: 导航
地图文件 → map_server → /map
Factor Perception → RTAB-Map (定位模式) → /tf
Nav2 Stack → 订阅地图和定位
```

**优点**:
- 地图和导航解耦
- 更稳定的定位
- 可以离线编辑地图

**实施步骤**:

1. 使用 RTAB-Map 构建地图
2. 保存地图文件
3. 配置 map_server
4. 切换 RTAB-Map 到定位模式
5. 启动 Nav2

## 详细实施计划（方案 A）

### 步骤 1: 验证当前系统

```bash
# 启动 RTAB-Map
ros2 launch nav24r factor_perception_auto.launch.py

# 检查话题
ros2 topic list | grep -E "rtabmap|factor_perception"

# 检查 TF 树
ros2 run tf2_tools view_frames

# 检查地图话题
ros2 topic echo /rtabmap/grid_map --once
```

### 步骤 2: 创建统一 Launch 文件

创建 `nav24r_full.launch.py`，整合：
- Factor Perception
- RTAB-Map SLAM
- Nav2 Stack
- 话题重映射

### 步骤 3: 完善 Nav2 配置

更新 `nav2_params.yaml`:
- 添加 global_costmap 配置
- 使用 RTAB-Map 的地图话题
- 配置正确的传感器源
- 修正 TF frames

### 步骤 4: 测试集成

```bash
# 启动完整系统
ros2 launch nav24r nav24r_full.launch.py

# 发送导航目标
ros2 topic pub /goal_pose geometry_msgs/PoseStamped \
  "header: {frame_id: 'map'}
   pose: {position: {x: 1.0, y: 0.0, z: 0.0}}"

# 监控状态
ros2 topic echo /navigate_to_pose/_action/status
```

## 下一步行动

1. **立即**: 验证 RTAB-Map 输出话题
2. **然后**: 创建统一的 launch 文件
3. **接着**: 完善 costmap 配置
4. **最后**: 测试完整导航流程

## 预期挑战

1. **TF 树冲突** - 可能需要禁用某个节点的 TF 发布
2. **话题命名空间** - 需要仔细配置重映射
3. **QoS 兼容性** - RTAB-Map 和 Nav2 的 QoS 可能不匹配
4. **性能** - 实时 SLAM + Nav2 可能对 RK3588 有压力

## 参考资料

- [Nav2 官方文档](https://navigation.ros.org/)
- [RTAB-Map ROS2 集成](http://wiki.ros.org/rtabmap_ros)
- [已安装的 Nav2 调优技能](~/.claude/skills/ros2-copilot-reference/)
