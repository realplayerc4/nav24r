#!/usr/bin/env python3
"""
仿真环境启动文件 - 无实机条件下测试 Nav2 基础功能

包含：
1. 静态 TF 树（map -> odom -> base_link）
2. 模拟里程计话题
3. 模拟点云话题（用于代价地图）
4. Nav2 导航栈

使用方法：
  ros2 launch nav24r simulation/simulation_nav2.launch.py
  ros2 launch nav24r simulation/simulation_nav2.launch.py map:=my_map.yaml
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # 参数
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='使用仿真时间'
    )
    
    map_arg = DeclareLaunchArgument(
        'map',
        default_value='',
        description='地图文件路径（可选）'
    )
    
    params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('nav24r'), 'config', 'nav2_params.yaml'
        ])
    )
    
    # 静态 TF：map -> odom -> base_link
    static_tf_map_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_map_odom',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']
    )
    
    static_tf_odom_base = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_odom_base',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_link']
    )
    
    # 模拟里程计发布器
    mock_odom_pub = Node(
        package='nav24r',
        executable='mock_odom_publisher.py',
        name='mock_odom_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'odom_topic': '/factor_perception/odom',
            'publish_rate': 30.0,
        }]
    )
    
    # 模拟点云发布器（用于代价地图）
    mock_pointcloud_pub = Node(
        package='nav24r',
        executable='mock_pointcloud_publisher.py',
        name='mock_pointcloud_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'pointcloud_topic': '/factor_perception/cloud_obstacles',
            'publish_rate': 10.0,
            'frame_id': 'base_link',
        }]
    )
    
    # Nav2 导航栈
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'), 'launch', 'navigation_launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'params_file': LaunchConfiguration('params_file'),
            'autostart': 'true',
            'map_subscribe_transient_local': 'true',
        }.items(),
    )
    
    return LaunchDescription([
        use_sim_time_arg,
        map_arg,
        params_file_arg,
        static_tf_map_odom,
        static_tf_odom_base,
        mock_odom_pub,
        mock_pointcloud_pub,
        nav2_navigation,
    ])
