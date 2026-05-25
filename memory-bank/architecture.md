# 系统架构

## 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        RK3588 (上位机)                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   OAK-D Pro  │───▶│   Factor     │───▶│  robot_localization│ │
│  │   (USB 3.0)  │    │  Perception  │    │     (EKF)         │  │
│  └──────────────┘    └──────────────┘    └─────────┬────────┘  │
│                                                   │            │
│                              ┌────────────────────▼────────┐   │
│                              │           Nav2             │   │
│                              │  ┌─────────────────────┐   │   │
│                              │  │   Costmap 2D        │   │   │
│                              │  │   (Voxel/Obstacle)  │   │   │
│                              │  └──────────┬──────────┘   │   │
│                              │             │              │   │
│                              │  ┌──────────▼──────────┐   │   │
│                              │  │   MPPI Controller   │   │   │
│                              │  └──────────┬──────────┘   │   │
│                              │             │              │   │
│                              └─────────────┼──────────────┘   │
│                                            │                  │
│                              ┌─────────────▼──────────────┐   │
│                              │      /cmd_vel              │   │
│                              └─────────────┬──────────────┘   │
└────────────────────────────────────────────┼──────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RL 控制板 (下位机)                            │
│                    (接收 /cmd_vel，执行步态)                      │
└─────────────────────────────────────────────────────────────────┘
```

## 模块职责

| 模块 | 职责 | 输入 | 输出 |
|------|------|------|------|
| Factor Perception | 相机数据处理 | USB相机数据 | 深度/RGB/IMU/VIO话题 |
| robot_localization | 里程计融合 | VIO + IMU | odom→base_link TF |
| Nav2 Costmap | 障碍物感知 | 点云数据 | 代价地图 |
| Nav2 MPPI | 路径规划 | 目标点 + Costmap | /cmd_vel |
| RL控制板 | 步态执行 | /cmd_vel | 关节运动 |

## TF 树结构

```
map
 └── odom (robot_localization 发布)
      └── base_link
           ├── camera_link (静态TF)
           │    ├── camera_depth_frame
           │    └── camera_rgb_frame
           └── [其他机器人部件]
```

**关键约束**:
- Factor Perception **不发布** odom→base_link TF
- 所有里程计信息通过 EKF 融合后由 robot_localization 统一发布

## 数据流

```
OAK-D Pro ──USB3.0──▶ Factor Perception
                        │
                        ├──▶ /camera/depth/points ──▶ Costmap
                        ├──▶ /camera/odom ──────────▶ EKF
                        ├──▶ /camera/imu ───────────▶ EKF
                        └──▶ /camera/rgb/image_raw
                        │
                        ▼
                   robot_localization (EKF)
                        │
                        ▼
                   odom→base_link TF
                        │
                        ▼
                   Nav2 (Costmap + MPPI)
                        │
                        ▼
                   /cmd_vel ──▶ RL控制板
```

---

*Created: 2026-05-25*