# 项目概述

## 目标

将 Factor Perception SDK 与 Nav2 导航框架集成，实现人形机器人的自主导航功能。

## 目标范围 (Goals)

1. **感知集成**: OAK-D Pro 相机的深度、VIO、IMU 数据接入 ROS2
2. **导航功能**: Nav2 栈的配置与部署，实现自主路径规划与避障
3. **定位融合**: robot_localization EKF 融合 VIO 与 IMU 数据
4. **RK3588 优化**: 针对嵌入式平台的性能调优

## 非目标范围 (Non-Goals)

1. **SLAM建图**: 不包含建图功能（使用预先建立的地图）
2. **步态控制**: 下层 RL 控制板负责步态执行，本项目仅发送 `/cmd_vel`
3. **多相机支持**: 仅支持单 OAK-D Pro 相机
4. **仿真环境**: 目标为真实硬件部署，不包含仿真配置

## 目标硬件

| 组件 | 规格 |
|------|------|
| 相机 | Luxonis OAK-D Pro |
| 主控板 | RK3588 (上位机) |
| 控制板 | RL 控制板 (下位机，执行步态) |
| ROS2 版本 | Humble |
| 操作系统 | Ubuntu 22.04 |

## 项目边界

- 输入: OAK-D Pro 相机数据 (深度、RGB、IMU、VIO)
- 输出: `/cmd_vel` 命令到下位机
- 接口: ROS2 话题、TF 树、参数服务器

---

*Created: 2026-05-25*
*Status: Active*