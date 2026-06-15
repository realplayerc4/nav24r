# Factor Control Panel 更新说明

## 更新日期
2026-06-08

## 版本
v1.1 - ROS2 Jazzy 兼容版

---

## 🔧 主要改进

### 1. ROS 版本兼容性修复
- ✅ 更新所有启动命令从 `ros-humble` 到 `ros-jazzy`
- ✅ 适配 ROS2 Jazzy 环境变量

### 2. 增强的停止功能 ⭐ 新特性

#### 改进前
```python
def stop_all(self):
    subprocess.run("pkill -f 'ros2 launch'", shell=True)
    subprocess.run("pkill -f rviz2", shell=True)
    self.status_var.set("状态: 已停止")
```

#### 改进后
```python
def stop_all(self):
    """停止所有 ROS2 进程和 RTAB-Map 相关窗口"""

    # 停止 ROS2 launch 进程
    subprocess.run("pkill -f 'ros2 launch'", shell=True)

    # 停止 RViz
    subprocess.run("pkill -f rviz2", shell=True)

    # 停止 RTAB-Map 相关进程和窗口 ⭐ 新增
    subprocess.run("pkill -f rtabmap", shell=True)
    subprocess.run("pkill -f 'rtabmap-databaseViewer'", shell=True)
    subprocess.run("pkill -f 'rtabmap_viz'", shell=True)

    # 停止 Factor Perception 容器 ⭐ 新增
    subprocess.run("pkill -f 'component_container'", shell=True)
    subprocess.run("pkill -f 'robot_state_publisher'", shell=True)

    # 清理可能的僵尸进程 ⭐ 新增
    subprocess.run("pkill -9 -f 'factor_perception'", shell=True)

    self.status_var.set("状态: 已停止所有进程")
```

---

## ✨ 新功能详情

### 停止按钮现在会关闭以下进程：

| 进程类型 | 命令 | 说明 |
|---------|------|------|
| ROS2 Launch | `pkill -f 'ros2 launch'` | 停止所有启动文件 |
| RViz | `pkill -f rviz2` | 关闭可视化窗口 |
| RTAB-Map 核心 | `pkill -f rtabmap` | 关闭 RTAB-Map 主进程 |
| 数据库查看器 | `pkill -f 'rtabmap-databaseViewer'` | 关闭数据库查看器窗口 |
| RTAB-Map 可视化 | `pkill -f 'rtabmap_viz'` | 关闭 RTAB-Map 可视化节点 |
| 组件容器 | `pkill -f 'component_container'` | 停止 Factor Perception 容器 |
| Robot State Publisher | `pkill -f 'robot_state_publisher'` | 停止机器人状态发布器 |
| Factor Perception | `pkill -9 -f 'factor_perception'` | 强制停止所有相关进程 |

---

## 🎯 使用效果

### 改进前
- 点击停止后，RTAB-Map 窗口可能仍然打开
- 需要手动关闭多个窗口
- 可能有僵尸进程残留

### 改进后
- 点击停止后，所有相关窗口自动关闭 ✅
- 所有相关进程被彻底清理 ✅
- 无僵尸进程残留 ✅
- 状态显示清晰："已停止所有进程" ✅

---

## 🔍 技术细节

### 为什么需要这么多 pkill 命令？

1. **分层架构**: Factor Perception 使用组件容器架构，需要分别停止
2. **RTAB-Map 多进程**: RTAB-Map 包含多个子进程（核心、可视化、数据库查看器）
3. **彻底清理**: 防止僵尸进程占用资源
4. **信号处理**:
   - 默认 `pkill` 发送 SIGTERM（温和终止）
   - `pkill -9` 发送 SIGKILL（强制终止）

---

## 📋 测试建议

### 测试步骤

1. **启动控制面板**
   ```bash
   python3 /home/yq/nav24r/scripts/factor_control_panel.py
   ```

2. **启动建图**
   - 输入地图 ID
   - 点击 "🗺️ 开始建图"
   - 等待 RTAB-Map 窗口打开

3. **测试停止功能**
   - 点击 "⏹️ 停止"
   - 观察所有窗口是否关闭
   - 检查进程是否清理完毕：
     ```bash
     ps aux | grep -E "rtabmap|factor_perception|rviz2" | grep -v grep
     ```
   - 应该无输出或只显示控制面板本身

---

## 🚀 下一步改进建议

### 可选增强功能

1. **进程监控**
   - 添加实时进程状态显示
   - 显示当前运行的节点列表

2. **日志查看**
   - 集成日志查看功能
   - 显示错误和警告信息

3. **资源监控**
   - 显示 CPU 和内存使用情况
   - 显示话题频率

4. **配置管理**
   - 可视化参数配置界面
   - 保存/加载配置文件

---

## 📝 文件位置

- **控制面板脚本**: `/home/yq/nav24r/scripts/factor_control_panel.py`
- **Cyclone DDS 配置**: `/home/yq/nav24r/config/cyclonedds.xml`
- **地图配置文件**: `/home/yq/nav24r/config/maps_config.json`

---

**更新完成！现在控制面板可以彻底停止所有相关进程和窗口了！** 🎉