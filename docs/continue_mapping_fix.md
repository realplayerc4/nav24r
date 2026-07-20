# 续建地图修复记录

**日期**: 2026-07-16
**问题**: 续建地图时 RTAB-Map 无法正确显示旧地图
**状态**: ✅ 已修复

---

## 问题现象

点击控制面板"续建"按钮后，RTAB-Map 启动但 2D 栅格地图不显示：

```
rtabmap: Working Memory = 465, Local map = 2
map 话题 Publisher count: 0
```

旧两阶段方案（`localization:=true` → `switch_to_mapping.py` 切换）存在三个问题：

| 问题 | 说明 |
|------|------|
| 时序脆弱 | 依赖 `info` 话题 `loop_closure_id>0` 才切换，位姿不佳时超时 |
| 数据库锁风险 | 先以定位模式（只读）打开数据库，再切换为写模式 |
| 错误被吞没 | `switch_to_mapping.py` 运行在 daemon 线程，stderr 只写日志 |

---

## 根因分析

### 根因1：`Grid/3D=true` 抑制了 2D 栅格发布

RTAB-Map 的 `Grid/3D=true` 参数只启用 3D 点云地图，不自动启用 2D 占位栅格地图。`continue_mapping` 模式下旧节点加载到工作内存，但 2D 栅格为空，导致 `/factor_perception/map` 话题无发布者。

### 根因2：`publish_map` 服务不存在

RTAB-Map 0.22.1 的 composable node 不暴露 `publish_map` 服务，`switch_to_mapping.py` 调用的服务根本不存在，导致续建失败。

### 根因3：旧进程占用数据库锁

旧进程（PID 90354）以 `localization:=true` 打开数据库后未退出，新进程以 `continue_mapping`（写模式）打开时 SQLite 报 `database is locked`。

---

## 修复方案

### 1. 添加 `Grid/2D=true` 参数

在三个 launch 文件的 RTAB-Map 节点中添加 `Grid/2D: 'true'`，让 RTAB-Map 同时发布 2D 和 3D 地图：

**修改文件：**
- `factor_perception_auto.launch.py` — 三个 RTAB-Map 节点
- `launch/nav24r_full.launch.py` — 三个 RTAB-Map 节点
- `launch/factor_perception_isolated.launch.py` — 共享 `slam_params` dict

**关键参数：**
```python
'Grid/3D': 'true',
'Grid/2D': 'true',  # 新增：启用 2D 占位栅格地图发布
```

### 2. 简化续建流程

删除旧的两阶段方案（`localization:=true` → `switch_to_mapping.py`），替换为直接 `continue_mapping:=true`：

**修改文件：**
- `scripts/factor_control_panel.py` — 删除两阶段方案
- `scripts/start_factor.sh` — 删除 `SWITCH_SCRIPT` 逻辑
- `scripts/start_rtabmap_light.sh` — 删除 `SWITCH_SCRIPT` 逻辑

**删除文件：**
- `scripts/switch_to_mapping.py` — 旧方案废弃
- `scripts/publish_map_helper.py` — 服务不存在，无用的中间脚本

---

## 修复后的续建流程

```
点击"续建" / start_factor.sh -m continue
    ↓
ros2 launch ... localization:=false continue_mapping:=true
    ↓
RTAB-Map 以 SLAM 模式启动，从数据库加载所有旧节点
    ↓
Grid/2D=true → 2D 栅格地图自动发布到 /factor_perception/map
    ↓
新传感器数据实时写入同一数据库，继续建图
```

---

## 测试结果

### 测试环境

- **数据库**: `map_20260715_1509.db` (241 MB)
- **RTAB-Map 版本**: 0.22.1
- **ROS 2 版本**: Jazzy
- **测试时间**: 2026-07-16

### 测试命令

```bash
ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py \
    localization:=false continue_mapping:=true \
    database_path:=/home/yq/rtabmap_maps/map_20260715_1509.db \
    config_path:=/home/yq/nav24r/config/rtabmap_custom.ini
```

### 测试结果

| 指标 | 预期 | 实际 | 状态 |
|------|------|------|------|
| 2D 地图加载 | 正确加载旧地图 | 156×202 栅格 | ✅ |
| map 话题发布者 | >0 | 1 | ✅ |
| odom 话题发布者 | >0 | 1 | ✅ |
| Working Memory | 加载旧节点 | 476 | ✅ |
| Local map | >0 | 12 | ✅ |
| 处理帧数 | 持续处理 | 2811+ | ✅ |
| 崩溃/锁错误 | 无 | 无 | ✅ |

### 关键日志

```
rtabmap: 2D occupancy grid map loaded (156x202).
rtabmap: Working Memory = 476, Local map = 12.
rtabmap: Database version = "0.22.1".
rtabmap: SLAM mode (Mem/IncrementalMemory=true)
rtabmap (2811): Rate=1.00s, Limit=0.700s, pub=0.1176s delay=0.4754s (local map=14, WM=477)
```

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `factor_perception_auto.launch.py` | 修改 | 添加 `Grid/2D: 'true'` |
| `launch/nav24r_full.launch.py` | 修改 | 添加 `Grid/2D: 'true'` |
| `launch/factor_perception_isolated.launch.py` | 修改 | 添加 `Grid/2D: 'true'` |
| `scripts/factor_control_panel.py` | 重写 | 删除两阶段方案 |
| `scripts/start_factor.sh` | 重写 | 删除 `SWITCH_SCRIPT` |
| `scripts/start_rtabmap_light.sh` | 重写 | 删除 `SWITCH_SCRIPT` |
| `scripts/switch_to_mapping.py` | 删除 | 旧方案废弃 |
| `scripts/publish_map_helper.py` | 删除 | 服务不存在，无用 |
| `README.md` | 更新 | 文件列表 |
| `CLAUDE.md` | 更新 | 文件列表 |

---

## 经验总结

1. **`Grid/3D=true` 不包含 `Grid/2D`** — RTAB-Map 中 3D 和 2D 栅格是独立参数，需要同时启用
2. **composable node 不暴露所有服务** — `publish_map`、`set_mode_mapping` 等服务在 composable 模式下可能不可用
3. **数据库锁是常见问题** — 确保只有一个 RTAB-Map 进程访问同一数据库
4. **简单方案更可靠** — 直接 `continue_mapping:=true` 比两阶段切换更稳定

---

## 下一步

- [ ] 在有 OAK-D 相机的环境下测试续建功能
- [ ] 验证新数据能正确写入已有地图
- [ ] 测试多次续建的累积效果
