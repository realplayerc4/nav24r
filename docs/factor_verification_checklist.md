# Factor Perception 功能验证清单

## 验证前提
- 环境：ROS2 Jazzy，仿真优先，无实机 OAK-D
- 重点：配置正确性、Launch 可解析、话题接口一致、Nav2 集成点可运行

---

## 1. 配置验证
- [ ] `config/factor_perception_config.yaml` 可被 YAML 解析
- [ ] `camera.keys` / `camera.mxids` / `camera.model` 字段存在
- [ ] `ros.distro` 为 `jazzy`
- [ ] `maps.directory` 和 `maps.default_db` 路径可展开
- [ ] `launch.*` 参数类型正确
- [ ] `paths.*` 指向 `/home/yq/nav24r/...`

## 2. Launch 文件验证
- [ ] `factor_perception_auto.launch.py` 可被 `ros2 launch --show-args` 解析
- [ ] `factor_perception_isolated.launch.py` 同上
- [ ] `nav24r_full.launch.py` 包含 Factor + RTAB-Map + Nav2 组合
- [ ] 所有 `database_path_arg` 使用 `PathJoinSubstitution`
- [ ] `Node` / `ComposableNode` 的 `package`、`plugin`、`executable` 可解析

## 3. 话题接口一致性
- [ ] Nav2 `odom_topic` == `/factor_perception/odom`
- [ ] Nav2 `obstacle_topic` == `/factor_perception/cloud_obstacles`
- [ ] `factor_perception_auto.launch.py` 实际发布的 odom topic 与 Nav2 一致
- [ ] `factor_perception_auto.launch.py` 实际发布的点云 topic 与 Nav2 costmap 一致
- [ ] TF 广播帧：`map` -> `odom` -> `base_link` 无冲突

## 4. 仿真兼容性
- [ ] `mock_odom_publisher` 可发布到 `/factor_perception/odom`
- [ ] `mock_pointcloud_publisher` 可发布到 `/factor_perception/cloud_obstacles`
- [ ] Nav2 在仿真 launch 中能接收 mock 数据并启动
- [ ] `test_simulation` 脚本能完成端到端检查

## 5. RTAB-Map 集成
- [ ] `rtabmap_custom.ini` 存在且可读
- [ ] RTAB-Map 节点能从 `database_path_arg` 读取数据库
- [ ] `rtabmap/*` 话题与 Nav2 localization 配置一致
- [ ] 地图保存路径与 `factor_perception_config.yaml` 一致

## 6. 安全与路径
- [ ] 无硬编码密钥泄露风险
- [ ] 相机密钥优先从 `FACTOR_PERCEPTION_KEY` 环境变量读取
- [ ] 所有 `~` 路径使用 `os.path.expanduser`
- [ ] `map_id` 输入有白名单校验

---

## 快速验证命令

```bash
cd /home/yq/nav24r
source install/setup.bash

# 1. Build
colcon build --packages-select nav24r

# 2. Launch 语法
ros2 launch --show-args nav24r factor_perception_auto.launch.py
ros2 launch --show-args nav24r factor_perception_isolated.launch.py
ros2 launch --show-args nav24r simulation_nav2.launch.py

# 3. 仿真测试
ros2 run nav24r test_simulation

# 4. Mock 发布器
ros2 run nav24r mock_odom_publisher
ros2 run nav24r mock_pointcloud_publisher
```

---

## 已知限制
- 无 OAK-D 硬件时，无法验证实际深度/点云质量
- 仿真只能验证数据流和接口，不能验证感知算法精度
- RTAB-Map 建图质量需要真实环境或 Gazebo 场景验证
