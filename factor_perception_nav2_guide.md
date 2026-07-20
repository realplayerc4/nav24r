# Factor Perception SDK Integration Guide for Nav2

**Target Hardware**: OAK-D Pro + RK3588 (or x86 dev machine)
**ROS 2 Version**: Humble
**Nav2 Stack**: Navigation2

---

## 1. Factor Perception SDK Overview

Factor Perception is a perception SDK for Luxonis OAK-D series cameras, providing:

| Feature | Description |
|---------|-------------|
| **VIO** | Visual-Inertial Odometry for 6-DOF pose estimation |
| **Depth** | Stereo depth with filtering and confidence |
| **SLAM** | Dense 3D mapping and reconstruction |
| **Object Detection** | On-device neural network inference |

### Hardware Requirements
- OAK-D Pro (recommended for humanoid robots)
- USB 3.0 connection
- Host: RK3588 or x86 Ubuntu 22.04

---

## 2. Core ROS 2 Parameters

### Launch File Configuration

```python
# factor_perception_launch.py
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        # Factor Perception Node
        Node(
            package='factor_perception',
            executable='factor_perception_node',
            name='factor_perception',
            output='screen',
            parameters=[{
                # Camera identification
                'mxid_or_name': '',  # Auto-detect or specify OAK-D serial

                # TF publishing (IMPORTANT: disable for EKF fusion)
                'publish_tf': False,  # Let robot_localization handle odom->base_link

                # Depth configuration
                'depth_filter': True,  # Enable to remove ghost/noise points
                'confidence_threshold': 200,  # Depth confidence (0-255)

                # IR projector for indoor/low-light
                'ir_intensity': 0.4,  # Flood light intensity (0.0-1.0)

                # Frame IDs
                'base_frame_id': 'base_link',
                'odom_frame_id': 'odom',

                # VIO configuration
                'enable_vio': True,
                'vio_frequency': 30.0,  # Hz
            }]
        ),
    ])
```

### Parameter Explanations

| Parameter | Default | Recommended | Notes |
|-----------|---------|-------------|-------|
| `publish_tf` | `True` | `False` | Disable to prevent TF conflicts with EKF |
| `depth_filter` | `False` | `True` | Critical for humanoid robots - prevents false obstacles |
| `ir_intensity` | `0.0` | `0.4` | Improves VIO stability in indoor/dark environments |
| `confidence_threshold` | `200` | `200` | Higher = stricter depth filtering |

---

## 3. Published Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/camera/depth/image_raw` | `sensor_msgs/Image` | Depth image |
| `/camera/depth/points` | `sensor_msgs/PointCloud2` | 3D point cloud |
| `/camera/rgb/image_raw` | `sensor_msgs/Image` | RGB image |
| `/camera/imu` | `sensor_msgs/Imu` | IMU data |
| `/camera/odom` | `nav_msgs/Odometry` | VIO odometry |
| `/camera/pose` | `geometry_msgs/PoseStamped` | Estimated pose |

---

## 4. Nav2 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RK3588 (Upper Board)                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   OAK-D Pro  │───▶│   Factor     │───▶│  robot_localization│  │
│  │   (USB 3.0)  │    │  Perception  │    │     (EKF)         │  │
│  └──────────────┘    └──────────────┘    └─────────┬────────┘   │
│                                                   │             │
│                              ┌────────────────────▼────────┐    │
│                              │           Nav2              │    │
│                              │  ┌─────────────────────┐    │    │
│                              │  │   Costmap 2D        │    │    │
│                              │  │   (Voxel/Obstacle)  │    │    │
│                              │  └──────────┬──────────┘    │    │
│                              │             │               │    │
│                              │  ┌──────────▼──────────┐    │    │
│                              │  │   MPPI Controller   │    │    │
│                              │  └──────────┬──────────┘    │    │
│                              │             │               │    │
│                              └─────────────┼───────────────┘    │
│                                            │                    │
│                              ┌─────────────▼──────────────┐     │
│                              │      /cmd_vel              │     │
│                              └─────────────┬──────────────┘     │
└────────────────────────────────────────────┼────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RL Control Board (Lower Board)               │
│                    (Receives /cmd_vel, executes gait)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Nav2 Configuration for Factor Perception

### Costmap Layer Configuration

```yaml
# nav2_params.yaml
local_costmap:
  local_costmap:
    ros__parameters:
      # Frame settings
      global_frame: odom
      robot_base_frame: base_link

      # Layer plugins
      plugins: ["obstacle_layer", "inflation_layer"]

      # Obstacle layer - uses Factor Perception point cloud
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: "pointcloud"
        pointcloud:
          topic: /camera/depth/points
          data_type: "PointCloud2"
          clearing: True
          marking: True
          max_obstacle_height: 2.0
          min_obstacle_height: 0.05
          obstacle_range: 3.0
          raytrace_range: 3.5

global_costmap:
  global_costmap:
    ros__parameters:
      global_frame: map
      robot_base_frame: base_link
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]

      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        observation_sources: "pointcloud"
        pointcloud:
          topic: /camera/depth/points
          data_type: "PointCloud2"
          clearing: True
          marking: True
```

### EKF Configuration (robot_localization)

```yaml
# ekf_params.yaml
ekf_filter_node:
  ros__parameters:
    frequency: 30.0

    # Frame IDs
    map_frame: map
    odom_frame: odom
    base_link_frame: base_link
    world_frame: odom

    # Input sources
    odom0: /camera/odom
    odom0_config: [False, False, False,  # x, y, z
                   True,  True,  True,   # roll, pitch, yaw
                   False, False, False,  # vx, vy, vz
                   True,  True,  True,   # vroll, vpitch, vyaw
                   False, False, False]  # ax, ay, az

    # IMU input (from OAK-D)
    imu0: /camera/imu
    imu0_config: [False, False, False,  # x, y, z
                  True,  True,  True,   # roll, pitch, yaw
                  False, False, False,  # vx, vy, vz
                  True,  True,  True,   # vroll, vpitch, vyaw
                  True,  True,  True]   # ax, ay, az
```

---

## 6. MPPI Controller Configuration

For humanoid robots, MPPI (Model Predictive Path Integral) controller is recommended:

```yaml
controller_server:
  ros__parameters:
    controller_plugins: ["FollowPath"]
    FollowPath:
      plugin: "nav2_mppi_controller::MPPIController"

      # Motion model for humanoid
      motion_model: "Omni"

      # Time and sampling
      time_steps: 56
      model_dt: 0.05
      batch_size: 2000

      # Velocity constraints (adjust for your humanoid)
      max_velocity: 0.5
      min_velocity: -0.1
      max_angular_velocity: 1.0

      # Cost weights
      cost_weights:
        goal_dist_cost: 1.0
        path_dist_cost: 2.0
        obstacles_cost: 5.0
```

---

## 7. System Optimization for RK3588

### CPU Affinity (taskset)

```bash
# Bind Factor Perception to A76 big cores (cores 4-7 on RK3588)
taskset -c 4-7 ros2 run factor_perception factor_perception_node

# Bind Nav2 MPPI to remaining big cores
taskset -c 4-7 ros2 run nav2_controller controller_server
```

### Cyclone DDS Configuration

Already configured. For RK3588, create a Cyclone DDS XML config:

```xml
<!-- ~/.cyclonedds.xml -->
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://cdds.io/config" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="https://cdds.io/config https://raw.githubusercontent.com/eclipse-cyclonedds/cyclonedds/master/etc/cyclonedds.xsd">
  <Domain id="any">
    <General>
      <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
      <AllowMulticast>true</AllowMulticast>
    </General>
    <Internal>
      <Watermarks>
        <WhcHigh>500kB</WhcHigh>
      </Watermarks>
    </Internal>
  </Domain>
</CycloneDDS>
```

---

## 8. Launch Sequence

```bash
# Terminal 1: Factor Perception
ros2 launch factor_perception factor_perception_launch.py

# Terminal 2: Robot Localization (EKF)
ros2 launch robot_localization ekf.launch.py

# Terminal 3: Nav2
ros2 launch nav2_bringup navigation_launch.py \
    params_file:=/path/to/nav2_params.yaml

# Terminal 4: SLAM (optional, for mapping)
ros2 launch slam_toolbox online_async_launch.py
```

---

## 9. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| TF tree disconnect | `publish_tf=True` | Set to `False`, use EKF |
| Ghost obstacles | Depth noise | Enable `depth_filter=True` |
| VIO drift indoors | Low light | Increase `ir_intensity` |
| High latency | Fast DDS overhead | Use Cyclone DDS |
| TF timestamp errors | Clock drift | Install Chrony on all boards |

---

## 10. Next Steps

1. [ ] Install Factor Perception SDK: `sudo apt install ros-humble-factor-perception` (or build from source)
2. [ ] Create launch file with parameters above
3. [ ] Configure Nav2 costmap layers
4. [ ] Set up robot_localization EKF
5. [ ] Test on x86, then cross-compile for RK3588
6. [ ] Deploy with CPU affinity and Chrony on target hardware
