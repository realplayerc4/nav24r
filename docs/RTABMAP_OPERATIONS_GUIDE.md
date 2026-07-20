# RTAB-Map 操作手册

**项目**: nav24r 人形机器人导航系统  
**版本**: v2.1.0  
**更新日期**: 2026-07-16  

---

## 📋 目录

1. [快速开始](#快速开始)
2. [数据库管理](#数据库管理)
3. [建图模式](#建图模式)
4. [续建模式](#续建模式)
5. [定位/导航模式](#定位导航模式)
6. [可视化工具](#可视化工具)
7. [地图分析](#地图分析)
8. [导出地图](#导出地图)
9. [设备管理](#设备管理)
10. [故障排查](#故障排查)

---

## 🚀 快速开始

### 系统要求

- **操作系统**: Ubuntu 24.04 LTS (Noble)
- **ROS 版本**: ROS2 Jazzy
- **Python**: 3.12+
- **硬件**: OAK-D Pro / OAK-D Pro W 相机
- **数据库**: `~/rtabmap.db` (默认)

### 环境配置

```bash
# 1. 加载 ROS2 环境
source /opt/ros/jazzy/setup.bash

# 2. 加载项目环境（如果已编译）
source /home/yq/nav24r/install/local_setup.bash

# 3. 设置相机密钥（可选，如果环境变量未设置）
export FACTOR_PERCEPTION_KEY=your_camera_key_here
```

### 启动方式

**方式1：控制面板（推荐）**
```bash
python3 /home/yq/nav24r/scripts/factor_control_panel.py
```

**方式2：启动脚本**
```bash
# 新建地图
/home/yq/nav24r/scripts/start_factor.sh -m mapping

# 续建地图
/home/yq/nav24r/scripts/start_factor.sh -m continue

# 定位模式
/home/yq/nav24r/scripts/start_factor.sh -m localization
```

**方式3：Launch 文件**
```bash
# 新建地图
ros2 launch nav24r factor_perception_auto.launch.py

# 续建地图
ros2 launch nav24r factor_perception_auto.launch.py continue_mapping:=true

# 定位模式
ros2 launch nav24r factor_perception_auto.launch.py localization:=true
```

---

## 💾 数据库管理

### 数据库位置

**默认数据库**: `~/rtabmap.db`
- 大小: 动态增长（通常 100-300 MB）
- 用途: 存储所有建图数据

**历史地图目录**: `~/rtabmap_maps/`
- 存放多个历史地图数据库
- 每个数据库包含一次完整的建图会话

### 数据库操作

#### 查看数据库信息

```bash
# 查看数据库大小
ls -lh ~/rtabmap.db

# 查看数据库内容（节点数、链接数）
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/yq/rtabmap.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM Node')
print(f'节点数: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM Link')
print(f'链接数: {cursor.fetchone()[0]}')
conn.close()
"
```

#### 重置地图

**控制面板**: 点击 "🗑️ 重置地图" 按钮  
**启动脚本**: `/home/yq/nav24r/scripts/start_factor.sh -m reset`  
**手动删除**:
```bash
rm ~/rtabmap.db
```

#### 备份数据库

```bash
# 手动备份
cp ~/rtabmap.db ~/rtabmap_backup_$(date +%Y%m%d_%H%M).db

# 或使用控制面板的 Database Viewer 导出
```

---

## 🗺️ 建图模式

### 新建地图

**用途**: 创建全新地图，覆盖已有数据

**启动方式**:
```bash
# 控制面板
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🗺️ 新建建图"

# 启动脚本
/home/yq/nav24r/scripts/start_factor.sh -m mapping

# Launch 文件
ros2 launch nav24r factor_perception_auto.launch.py
```

**行为**:
- 如果 `~/rtabmap.db` 已存在，会提示确认覆盖
- 删除旧数据库，创建新数据库
- 从头开始建图

### 续建地图

**用途**: 在已有地图基础上继续建图

**启动方式**:
```bash
# 控制面板
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🔄 续建"

# 启动脚本
/home/yq/nav24r/scripts/start_factor.sh -m continue

# Launch 文件
ros2 launch nav24r factor_perception_auto.launch.py continue_mapping:=true
```

**要求**:
- `~/rtabmap.db` 必须已存在
- 数据库不能损坏

**行为**:
- 加载数据库中所有历史节点（`Mem/InitWMWithAllNodes = true`）
- 从数据库深度图重建点云（`cloud_source = 1`）
- 继续建图，新数据追加到数据库

### 建图过程

1. **启动建图**
   ```bash
   python3 /home/yq/nav24r/scripts/factor_control_panel.py
   # 点击 "🗺️ 新建建图"
   ```

2. **打开 RViz 查看**
   ```bash
   # 顶视角（2D 地图）
   rviz2 -d /home/yq/nav24r/config/mapping.rviz

   # 或 3D 视角
   rviz2 -d /home/yq/nav24r/config/mapping_3d.rviz
   ```

3. **移动机器人建图**
   - 使用键盘/手柄控制机器人移动
   - 或使用 Web 控制面板：`python3 /home/yq/nav24r/scripts/web_control_panel.py`
   - 访问 `http://localhost:8080`

4. **监控建图状态**
   - 控制面板显示数据库大小变化
   - RViz 中查看 2D 地图（`/factor_perception/map`）
   - 查看 3D 点云（`/factor_perception/cloud_map`）

5. **停止建图**
   ```bash
   # 控制面板点击 "⏹️ 停止"
   # 或 Ctrl+C 终止终端
   ```

---

## 🧭 定位/导航模式

### 定位模式

**用途**: 在已有地图上进行定位，不建图

**启动方式**:
```bash
# 控制面板
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🧭 开始导航"

# 启动脚本
/home/yq/nav24r/scripts/start_factor.sh -m localization

# Launch 文件
ros2 launch nav24r factor_perception_auto.launch.py localization:=true
```

**要求**:
- `~/rtabmap.db` 必须已存在
- 地图质量良好（建议评分 > 70）

**行为**:
- 加载数据库进行定位（`Mem/IncrementalMemory = false`）
- 不创建新节点
- 实时发布位姿和地图

### 完整导航模式

**用途**: 启动完整的导航系统（Factor Perception + RTAB-Map + Nav2）

**启动方式**:
```bash
# 控制面板
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🚀 完整导航"

# Launch 文件
ros2 launch nav24r nav24r_full.launch.py localization:=true
```

**包含组件**:
- Factor Perception（相机驱动）
- RTAB-Map（定位）
- Nav2（导航栈）
- 代价地图、全局/局部规划器、控制器

### 发送导航目标

1. **启动 RViz**
   ```bash
   rviz2 -d /home/yq/nav24r/config/navigation.rviz
   ```

2. **设置起点**
   - 点击 RViz 工具栏 "2D Pose Estimate"
   - 在地图上点击并拖动设置机器人起点和方向

3. **发送目标**
   - 点击 RViz 工具栏 "Nav2 Goal"
   - 在地图上点击目标位置
   - 机器人自动规划路径并导航

---

## 🖥️ 可视化工具

### RViz 配置

| 配置文件 | 用途 | 说明 |
|----------|------|------|
| `mapping.rviz` | 2D 建图视角 | 顶视角，查看 2D 地图 |
| `mapping_3d.rviz` | 3D 建图视角 | 多视角，查看点云和 Octomap |
| `navigation.rviz` | 导航视角 | 查看路径规划和导航 |
| `map_viewer_3d.rviz` | 地图观察器 | 3D 查看历史地图 |
| `rtabmap_light.rviz` | 轻量化 RViz | 避免 GPU 崩溃 |
| `octomap.rviz` | Octomap 2D | 2D Octomap 视图 |
| `octomap_3d.rviz` | Octomap 3D | 3D Octomap 视图 |

### 启动 RViz

**控制面板方式**:
```bash
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击对应按钮:
# - 📊 RViz (2D 顶视角)
# - 📊 RViz 3D (3D 多视角)
# - 🗺️ 地图观察 (3D 地图查看器)
```

**命令行方式**:
```bash
source /opt/ros/jazzy/setup.bash

# 2D 建图视角
rviz2 -d /home/yq/nav24r/config/mapping.rviz

# 3D 建图视角
rviz2 -d /home/yq/nav24r/config/mapping_3d.rviz

# 导航视角
rviz2 -d /home/yq/nav24r/config/navigation.rviz
```

### RViz 显示项

**mapping_3d.rviz 包含**:
- **障碍物点云** (`/factor_perception/cloud_obstacles`) - 红色
- **地面点云** (`/factor_perception/cloud_ground`) - 绿色
- **全局点云地图** (`/factor_perception/cloud_map`) - 灰色
- **2D 地图** (`/factor_perception/map`) - 灰度图
- **Octomap 3D** (`/factor_perception/octomap_occupied_space`) - 3D 栅格
- **TF** - 坐标系树
- **机器人模型** - 机器人 URDF 模型
- **当前位姿** - 机器人当前位置

---

## 📊 地图分析

### 地图质量评分

**启动方式**:
```bash
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "📊 地图质量"
```

**评分维度**（总分 100）:

| 维度 | 分值 | 说明 |
|------|------|------|
| 节点数量 | 25分 | 地图覆盖范围 |
| 链接密度 | 25分 | 连接稳定性 |
| 闭环检测 | 30分 | 地图准确性 ⭐ 最关键 |
| 建图时长 | 20分 | 地图完整性 |

**评级标准**:

| 评分 | 星级 | 质量 |
|------|------|------|
| 85-100 | ⭐⭐⭐⭐⭐ | 优秀 |
| 70-84 | ⭐⭐⭐⭐ | 良好 |
| 55-69 | ⭐⭐⭐ | 一般 |
| 40-54 | ⭐⭐ | 较差 |
| <40 | ⭐ | 不合格 |

### 查看地图质量报告

**控制面板**:
1. 点击 "📊 地图质量"
2. 自动分析当前数据库
3. 显示详细评分报告
4. 可复制报告或打开 Database Viewer

**命令行**:
```bash
python3 /home/yq/nav24r/scripts/analyze_map_quality.py ~/rtabmap.db
```

---

## 🗺️ 导出地图

### 导出 Octomap（推荐）

**用途**: 导出 3D 栅格地图，用于 Nav2 导航

**启动方式**:
```bash
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🗺️ 导出Octomap"
```

**导出步骤**:
1. 选择分辨率：
   - 0.01m - 超高精度（工业应用）
   - 0.02m - 高精度（推荐人形机器人）⭐
   - 0.05m - 标准精度（通用导航）
   - 0.10m - 低精度（快速规划）

2. 启动 Database Viewer
3. File → Export 3D clouds...
4. 选择 "Export Octomap"
5. 设置分辨率
6. 点击 "Export" 保存

**输出文件**:
- 推荐位置: `~/rtabmap_maps/octomap_<resolution>m.bt`
- 格式: Octomap binary (`.bt`)

### 导出点云（PLY）

**用途**: 导出完整 3D 点云，用于可视化或进一步处理

**命令行**:
```bash
# 导出完整点云
rtabmap-export --cloud /home/yq/rtabmap.db --output /home/yq/rtabmap_cloud.ply

# 查看导出的点云
ls -lh /home/yq/rtabmap_cloud.ply
```

**点云信息**:
- 格式: PLY (binary little endian)
- 点数: 通常 30,000-60,000 点
- 大小: 约 1-2 MB
- 包含颜色信息 (RGB)

### 在 RViz 中查看历史点云

如果需要在 RViz 中查看从数据库导出的完整点云：

```bash
# 1. 导出点云
rtabmap-export --cloud /home/yq/rtabmap.db --output /home/yq/rtabmap_cloud.ply

# 2. 启动点云发布节点
python3 /home/yq/nav24r/scripts/ply_to_pointcloud.py

# 3. 在 RViz 中添加话题
#    Topic: /rtabmap/historical_cloud
#    Color Transformer: RGB8
```

---

## 📷 设备管理

### OAK-D 相机状态监控

**控制面板自动监控**:
- 每 3 秒自动检测设备状态
- 显示连接状态和 USB 速率

**手动检测**:
```bash
# 查看 USB 设备
lsusb | grep -iE "03e7|1443|luxonis"

# 查看 USB 速率
lsusb -d 03e7:

# 或使用控制面板
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🔍 检测设备"
```

### 相机重启

**软重启**（不拔 USB）:
```bash
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🔄 重启相机"
```

**强制重连**（停止所有 ROS2 进程）:
```bash
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "⚡ 强制重连"
```

**手动重启**:
```bash
# 停止所有 ROS2 进程
pkill -f "ros2 launch"
pkill -f "rtabmap"
pkill -f "factor_perception"

# 重置 USB 设备
for dev in /sys/bus/usb/devices/*; do
    if [ -f "$dev/idVendor" ]; then
        vendor=$(cat "$dev/idVendor" 2>/dev/null)
        if echo "$vendor" | grep -qiE "03e7|1443|2e1d"; then
            echo "Resetting: $dev"
            echo "$dev" | xargs -I{} sh -c 'echo {} > /sys/bus/usb/drivers/usb/unbind 2>/dev/null'
            sleep 1
            echo "$dev" | xargs -I{} sh -c 'echo {} > /sys/bus/usb/drivers/usb/bind 2>/dev/null'
        fi
    fi
done

sleep 3

# 验证连接
lsusb | grep -iE "03e7|1443|luxonis"
```

### USB 速率要求

| USB 版本 | 速率 | 建议用途 |
|----------|------|----------|
| USB 3.0 | 5 Gbps | ✅ 推荐（4K 分辨率） |
| USB 3.1/3.2 | 5-20 Gbps | ✅ 优秀 |
| USB 2.0 | 480 Mbps | ⚠️ 可用（降低分辨率） |

**检查 USB 速率**:
```bash
# 查看 USB 设备速度
cat /sys/bus/usb/devices/*/speed 2>/dev/null | sort -u

# 或使用控制面板查看
```

---

## 🔧 故障排查

### 常见问题

#### 1. 相机未检测到

**症状**: 控制面板显示 "❌ 设备未连接"

**解决方案**:
```bash
# 1. 检查 USB 连接
lsusb | grep -iE "03e7|1443|luxonis"

# 2. 重启相机（控制面板点击 "🔄 重启相机"）
# 或强制重连（控制面板点击 "⚡ 强制重连"）

# 3. 检查 USB 速率
lsusb -d 03e7:

# 4. 物理重新插拔 USB 线
```

#### 2. 建图时 GPU 崩溃

**症状**: RViz 导致系统崩溃

**解决方案**:
```bash
# 使用轻量化 RViz
rviz2 -d /home/yq/nav24r/config/rtabmap_light.rviz

# 或禁用图像显示
# 在 RViz 中移除 Image 显示项
```

#### 3. 数据库损坏

**症状**: RTAB-Map 启动失败，提示数据库错误

**解决方案**:
```bash
# 1. 备份当前数据库
cp ~/rtabmap.db ~/rtabmap_corrupt_backup.db

# 2. 重置地图
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🗑️ 重置地图"

# 3. 或使用 Database Viewer 修复
rtabmap-databaseViewer ~/rtabmap.db
# File → Repair database
```

#### 4. 续建时看不到历史点云

**症状**: RViz 中只能看到新点云，看不到历史点云

**原因**: RTAB-Map 的 `cloud_map` 话题只发布当前局部点云

**解决方案**:
```bash
# 方案1: 使用 Database Viewer 查看历史点云
rtabmap-databaseViewer ~/rtabmap.db

# 方案2: 导出完整点云
rtabmap-export --cloud /home/yq/rtabmap.db --output /home/yq/rtabmap_cloud.ply
python3 /home/yq/nav24r/scripts/ply_to_pointcloud.py

# 方案3: 导出 Octomap
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "🗺️ 导出Octomap"
```

#### 5. 定位漂移

**症状**: 定位模式下机器人位姿不稳定

**解决方案**:
```bash
# 1. 检查地图质量
python3 /home/yq/nav24r/scripts/factor_control_panel.py
# 点击 "📊 地图质量"

# 2. 如果评分 < 70，重新建图
# 3. 确保闭环检测正常工作（查看 RTAB-Map 日志）
# 4. 调整 IMU 参数（如果使用 IMU）
```

### ROS2 诊断命令

```bash
# 查看所有节点
ros2 node list

# 查看所有话题
ros2 topic list

# 查看点云话题
ros2 topic list | grep cloud

# 查看点云数据
ros2 topic echo /factor_perception/cloud_map --once

# 查看 RTAB-Map 状态
ros2 service list | grep rtabmap

# 查看 TF 树
ros2 run tf2_tools view_frames

# 查看日志
tail -f ~/ros2_ws/log/factor_perception/rtabmap.log
```

---

## 📚 高级用法

### 命令行直接启动

```bash
# 加载环境
source /opt/ros/jazzy/setup.bash

# 新建地图（指定数据库路径）
ros2 launch nav24r factor_perception_auto.launch.py \
    database_path:=/path/to/custom.db \
    key:=your_camera_key \
    config_path:=/home/yq/nav24r/config/rtabmap_custom.ini

# 续建地图
ros2 launch nav24r factor_perception_auto.launch.py \
    continue_mapping:=true \
    database_path:=/path/to/existing.db

# 定位模式
ros2 launch nav24r factor_perception_auto.launch.py \
    localization:=true \
    database_path:=/path/to/map.db

# 完整导航
ros2 launch nav24r nav24r_full.launch.py \
    localization:=true \
    database_path:=/path/to/map.db \
    nav2_params_file:=/home/yq/nav24r/config/nav2_params.yaml
```

### 自定义参数

```bash
# 修改相机高度
ros2 launch nav24r factor_perception_auto.launch.py cam_pos_z:=1.5

# 修改相机位置
ros2 launch nav24r factor_perception_auto.launch.py \
    cam_pos_x:=0.2 \
    cam_pos_y:=0.0 \
    cam_pos_z:=1.0

# 禁用 RTAB-Map 可视化
ros2 launch nav24r factor_perception_auto.launch.py rtabmap_viz:=false
```

### 多地图管理

**注意**: 当前系统简化版只使用默认数据库 `~/rtabmap.db`

**如果需要多地图管理**:
```bash
# 手动切换数据库
ros2 launch nav24r factor_perception_auto.launch.py \
    database_path:=/path/to/other_map.db \
    continue_mapping:=true

# 或修改控制面板配置
# 编辑 /home/yq/nav24r/config/maps_config.json
```

---

## 📖 相关文档

- [RTAB-Map 配置说明](config/rtabmap_config_doc.md)
- [Nav2/RTAB-Map 知识要点](docs/nav2_rtabmap_knowledge.md)
- [ROS2 工程分析](docs/ros2_engineering_analysis.md)
- [控制面板使用指南](docs/control_panel_update.md)
- [Octomap 导出指南](docs/octomap_export_panel_guide.md)

---

## 📞 技术支持

- **项目文档**: `/home/yq/nav24r/docs/`
- **日志目录**: `~/.local/share/nav24r/logs/`
- **数据库目录**: `~/rtabmap.db` (默认)
- **地图目录**: `~/rtabmap_maps/` (历史地图)

---

**最后更新**: 2026-07-16  
**版本**: v2.1.0
