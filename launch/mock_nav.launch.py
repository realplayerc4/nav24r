#!/usr/bin/env python3
"""
Mock 导航环境 Launch — 无实机 / 无 Gazebo 条件下测试 Nav2

启动内容:
  1. Map Server — 发布静态测试地图 (代替 RTAB-Map)
  2. MockRobot  — 差分驱动模拟，订阅 cmd_vel_nav，发布 odom + TF
  3. MockPointCloud — 模拟前方障碍物点云 (可选)
  4. Nav2       — 完整导航栈

使用:
  ros2 launch nav24r mock_nav.launch.py
  ros2 launch nav24r mock_nav.launch.py start_x:=1.0 start_y:=2.0 start_yaw:=0.0

前置:
  # 先生成测试地图
  python3 scripts/generate_test_map.py
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # ---- 参数 ----
    declare_map = DeclareLaunchArgument(
        'map_file',
        default_value='/home/yq/rtabmap_maps/test_map.yaml',
        description='测试地图 YAML 路径 (需先运行 generate_test_map.py 生成)')

    declare_start_x = DeclareLaunchArgument('start_x', default_value='0.0')
    declare_start_y = DeclareLaunchArgument('start_y', default_value='0.0')
    declare_start_yaw = DeclareLaunchArgument('start_yaw', default_value='0.0')

    # ---- Map Server (代替 RTAB-Map 的 /factor_perception/map) ----
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[{
            'use_sim_time': False,
            'yaml_filename': LaunchConfiguration('map_file'),
        }],
        remappings=[('/map', '/factor_perception/map')],
    )

    # map_server 的 static transform (map -> odom)
    # nav2_map_server 在某些版本不自动发布此 TF
    map_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_odom_tf',
        ros_arguments=['--log-level', 'warn'],
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
    )

    # ---- Mock 机器人 (差分驱动) ----
    mock_robot = Node(
        package='nav24r',
        executable='mock_robot',
        name='mock_robot',
        ros_arguments=['--log-level', 'warn'],
        parameters=[{
            'cmd_vel_topic': '/cmd_vel_nav',
            'odom_topic': '/factor_perception/odom',
            'odom_frame': 'odom',
            'base_frame': 'base_link',
            'publish_rate': 30.0,
            'start_x': LaunchConfiguration('start_x'),
            'start_y': LaunchConfiguration('start_y'),
            'start_yaw': LaunchConfiguration('start_yaw'),
        }],
    )

    # ---- Mock 点云 (可选) ----
    # 注: mock_pointcloud_publisher 有 use_sim_time 参数冲突，暂时禁用
    # Nav2 costmap 可通过 static_layer (map_server) 正常工作
    # mock_pc = Node(
    #     package='nav24r',
    #     executable='mock_pointcloud_publisher',
    #     name='mock_pointcloud',
    #     ros_arguments=['--log-level', 'warn'],
    #     parameters=[{
    #         'pointcloud_topic': '/factor_perception/cloud_obstacles',
    #         'publish_rate': 10.0,
    #         'frame_id': 'base_link',
    #     }],
    # )

    # ---- Nav2 ----
    nav2_params = PathJoinSubstitution(
        [FindPackageShare('nav24r'), 'config', 'nav2_params.yaml'])

    nav2_controller = Node(
        package='nav2_controller', executable='controller_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[nav2_params],
        remappings=[('cmd_vel', 'cmd_vel_nav')])

    nav2_smoother = Node(
        package='nav2_smoother', executable='smoother_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[nav2_params])

    nav2_planner = Node(
        package='nav2_planner', executable='planner_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[nav2_params])

    nav2_behaviors = Node(
        package='nav2_behaviors', executable='behavior_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[nav2_params],
        remappings=[('cmd_vel', 'cmd_vel_nav')])

    nav2_bt = Node(
        package='nav2_bt_navigator', executable='bt_navigator',
        ros_arguments=['--log-level', 'warn'],
        parameters=[nav2_params],
        remappings=[('tf', 'tf'), ('tf_static', 'tf_static')])

    nav2_lifecycle = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        ros_arguments=['--log-level', 'warn'],
        parameters=[
            {'autostart': True},
            {'node_names': [
                'map_server',
                'controller_server', 'planner_server',
                'behavior_server', 'bt_navigator',
            ]},
        ],
    )

    return LaunchDescription([
        declare_map,
        declare_start_x, declare_start_y, declare_start_yaw,
        map_server, map_tf,
        mock_robot,
        nav2_controller, nav2_smoother, nav2_planner,
        nav2_behaviors, nav2_bt, nav2_lifecycle,
    ])
