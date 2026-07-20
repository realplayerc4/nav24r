#!/usr/bin/env python3
"""
CLAUDE.md - nav24r 项目特定指南

基于 Karpathy 编码原则，为 nav24r ROS 2 项目定制的最佳实践。
全局准则（/home/yq/.claude/CLAUDE.md）也适用于本项目。
"""

# ============================================================
# nav24r 项目特定指南
# ============================================================

## 项目概述

**名称：** nav24r（人形机器人自主导航系统）
**版本：** 2.0.0
**技术栈：** ROS 2 Jazzy + Python 3.10+ + Factor Perception SDK + RTAB-Map + Nav2
**构建系统：** ament_python
**许可证：** MIT

---

## 编码风格

### Python 规则

- **版本：** Python 3.10+
- **格式化：** 遵循 PEP 8
- **导入顺序：** 标准库 → ROS 2 → 第三方 → 本地模块
- **字符串引号：** 单引号（除非包含单引号）
- **类型提示：** 鼓励但不强制
- **文档字符串：** Google 风格（简短而实用）

```python
#!/usr/bin/env python3
"""
模块简短描述（一句话）

详细描述（可选）
"""

from typing import Optional  # 标准库
import os
import logging

import rclpy  # ROS 2
from rclpy.node import Node

import yaml  # 第三方库

from .local_module import MyClass  # 本地模块


def example_function(param: str) -> bool:
    """简短描述（Google 风格文档字符串）

    Args:
        param: 参数描述

    Returns:
        返回值描述
    """
    # 实现逻辑
    pass
```

### Shell 脚本规则

- **Shebang：** `#!/bin/bash`
- **严格模式：** 始终使用 `set -euo pipefail`
- **缩进：** 2 空格（不使用 tab）
- **函数命名：** 小写+下划线（`snake_case`）
- **变量：** 大写常量，小写+下划线变量

```bash
#!/bin/bash
set -euo pipefail

# 常量（大写+下划线）
CONFIG_DIR="/home/yq/nav24r/config"
DEFAULT_MODE="mapping"

# 函数（小写+下划线）
log_info() {
    echo -e "\033[0;32m[INFO]\033[0m $1"
}

# 主逻辑
main() {
    log_info "Starting nav24r..."
}
main "$@"
```

### YAML 配置规则

- **缩进：** 2 空格
- **布尔值：** 使用 `true/false` 而非 `True/False`
- **字符串引号：** 必要时使用引号，避免歧义
- **注释：** 使用 `#`，说明"为什么"而非"是什么"

```yaml
# Nav2 参数 - 人形机器人（为什么：身高 1.6m，重心高）
bt_navigator:
  ros__parameters:
    use_sim_time: false
    global_frame: map
    robot_base_frame: base_link  # 统一使用 base_link（而非 base_footprint）
```

### JSON 配置规则

- **缩进：** 2 空格
- **引号：** 双引号（JSON 标准）
- **尾部逗号：** 不允许

```json
{
  "camera": {
    "model": "OAK-D-PRO-W",
    "resolution": "4K"
  }
}
```

---

## ROS 2 约定

### 包和命名

- **包名：** 小写+下划线（`nav24r`）
- **节点名：** 小写+下划线（`factor_perception_node`）
- **话题名：** 小写+下划线（`/factor_perception/odom`）
- **服务名：** 小写+下划线
- **TF 坐标系：** 标准 ROS 2 约定（`base_link`, `odom`, `map`, `camera_link`）

### Launch 文件（Python 格式）

- **格式：** 使用 Python launch 文件（而非 XML）
- **参数化：** 使用 `DeclareLaunchArgument` + `LaunchConfiguration`
- **条件执行：** 使用 `IfCondition` / `UnlessCondition`
- **文件包含：** 使用 `IncludeLaunchDescription`
- **包引用：** 使用 `FindPackageShare`

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # 参数声明
    use_sim_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='使用仿真时间'
    )

    # 节点配置
    node = Node(
        package='nav24r',
        executable='my_node',
        name='my_node',
        parameters=[
            {'use_sim_time': LaunchConfiguration('use_sim_time')}
        ]
    )

    return LaunchDescription([
        use_sim_arg,
        node
    ])
```

### ROS 2 节点最佳实践

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node


class MyNode(Node):
    def __init__(self):
        super().__init__('my_node')

        # 声明参数
        self.declare_parameter('param_name', 'default_value')

        # 订阅者/发布者
        self.subscription = self.create_subscription(
            msg_type,
            'topic_name',
            self.callback,
            qos_profile
        )

        # 定时器
        self.timer = self.create_timer(
            timer_period_sec,
            self.timer_callback
        )

        self.get_logger().info('节点已启动')  # ✅ 使用 self.get_logger()
        # print('节点已启动')  # ❌ 不要使用 print

    def callback(self, msg):
        # 处理消息
        pass

    def timer_callback(self):
        # 定时逻辑
        pass


def main(args=None):
    rclpy.init(args=args)
    node = MyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

## 项目结构

```
nav24r/
├── launch/                    # ROS 2 launch 文件（Python 格式）
│   ├── nav24r_full.launch.py
│   ├── factor_perception_isolated.launch.py
│   └── nav2.launch.py
├── config/                    # 配置文件
│   ├── nav2_params.yaml
│   ├── factor_perception_config.yaml
│   ├── maps_config.json
│   ├── cyclonedds.xml
│   ├── rtabmap_light.rviz
│   ├── mapping.rviz / mapping_3d.rviz
│   ├── navigation.rviz
│   ├── octomap.rviz / octomap_3d.rviz
│   ├── map_viewer_3d.rviz
│   └── rtabmap_config_doc.md
├── scripts/                   # 控制脚本
│   ├── factor_control_panel.py
│   ├── start_factor.sh
│   ├── start_rtabmap_light.sh
│   ├── factor_control.sh
│   ├── analyze_map_quality.py
│   ├── export_octomap.py
│   ├── mock_odom_publisher.py
│   ├── mock_pointcloud_publisher.py
│   ├── test_runner.sh
│   └── test_phase*.sh / test_simulation.py
├── docs/                      # 技术文档（多篇）
├── factor_perception/         # Factor Perception SDK（第三方，不修改）
├── Calibrat/                  # IMU 校准工具
│   ├── IMU/
│   ├── raw2unCal.py
│   ├── uncal2cal.py
│   └── run_examples.py
├── package.xml
├── setup.py
├── README.md
└── CHANGELOG.md
```

---

## 关键配置

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `FACTOR_PERCEPTION_KEY` | Factor Perception SDK 密钥 | `export FACTOR_PERCEPTION_KEY=xxx` |
| `ROS_DOMAIN_ID` | ROS 2 域 ID（多机器人隔离） | `export ROS_DOMAIN_ID=42` |
| `RMW_IMPLEMENTATION` | RMW 实现 | `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` |

### 文件路径

- **项目根目录：** `/home/yq/nav24r`
- **配置目录：** `/home/yq/nav24r/config`
- **地图目录：** `~/rtabmap_maps/`
- **默认数据库：** `~/rtabmap.db`

---

## 依赖管理

### ROS 2 依赖（package.xml）

- rclpy
- robot_state_publisher
- robot_localization
- rtabmap_slam
- depth_image_proc
- nav2_bringup
- nav2_mppi_controller

### Python 依赖（pip）

- pyyaml
- tkinter（系统包）

**安装依赖：**
```bash
# ROS 2 依赖（通过 apt）
sudo apt install ros-jazzy-rtabmap-slam ros-jazzy-nav2-bringup

# Python 依赖
pip3 install -r requirements.txt  # （如果存在）
```

---

## 常见任务

### 启动模式

**建图模式：**
```bash
~/nav24r/scripts/start_factor.sh -m mapping -d ~/rtabmap_maps/new_map.db
```

**定位/导航模式：**
```bash
~/nav24r/scripts/start_factor.sh -m localization -d ~/rtabmap.db
```

**启动所有节点（完整系统）：**
```bash
ros2 launch nav24r nav24r_full.launch.py
```

### 控制面板

---

## 注意事项

### ✅ 允许的修改

- **launch 文件**：添加/修改参数、节点、包含文件
- **config 文件**：调整参数（Nav2、RTAB-Map、RViz）
- **scripts/**：修改控制脚本（启动、建图、导航、分析）
- **README.md**：更新文档和快速启动指南

### ⚠️ 谨慎修改

- **factor_perception/**：第三方 SDK，仅在确认必要时修改
- **Calibrat/**：IMU 校准工具，确保不影响机器人坐标系

### ❌ 不要修改

- **install/**：自动生成，由 ament 维护
- **build/**：构建产物
- **__pycache__/**：Python 缓存

---

## 调试技巧

### ROS 2 命令

```bash
# 查看所有话题
ros2 topic list

# 查看节点
ros2 node list

# 回放话题
ros2 topic echo /factor_perception/odom

# 查看服务
ros2 service list

# 运行时间分析
ros2 run rqt_console rqt_console
```

### 日志位置

- **ROS 2 日志：** `~/ros2_ws/log/`
- **控制台输出：** 使用 `self.get_logger().info()` 而非 `print()`

---

## 测试建议

### 手动测试清单

- [ ] Launch 文件语法正确：`ros2 launch --show-args <file>`
- [ ] 所有节点启动成功（无错误）
- [ ] 话题数据流正常（`ros2 topic echo`）
- [ ] TF 树完整（`ros2 run tf2_tools view_frames`）
- [ ] Nav2 能接收目标点（`ros2 action send_goal`）
- [ ] RTAB-Map 能生成地图

---

## 贡献者须知

### 提交前检查

- [ ] 只修改与任务相关的文件
- [ ] 遵循现有代码风格（PEP 8、2 空格缩进等）
- [ ] 添加/更新必要的注释（说明"为什么"）
- [ ] 更新相关文档（README、CHANGELOG）
- [ ] 测试 launch 文件语法
- [ ] 验证关键参数更改

### PR 描述模板

```markdown
## 变更说明
简要描述做了什么

## 变更类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 配置优化
- [ ] 文档更新

## 测试验证
- [ ] Launch 文件语法检查通过
- [ ] 所有节点正常启动
- [ ] 话题数据流验证
- [ ] 手动功能测试

## 相关 Issue
Closes #（issue 编号）

## 注意事项
- 需要重新校准吗？
- 影响现有地图吗？
- 环境变量是否更新？
```

---

## 资源链接

- **ROS 2 文档：** https://docs.ros.org/en/humble/
- **Nav2 文档：** https://navigation.ros.org/
- **RTAB-Map Wiki：** https://github.com/introlab/rtabmap/wiki
- **项目 README：** `/home/yq/nav24r/README.md`
- **集成指南：** `/home/yq/nav24r/factor_perception_nav2_guide.md`

---

*最后更新：2026-06-29*
*全局准则：~/.claude/CLAUDE.md（Karpathy 编码原则）*
