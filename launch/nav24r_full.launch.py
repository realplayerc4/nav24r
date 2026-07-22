# 综合启动文件 - Factor Perception + Nav2
# 人形机器人导航系统

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression, EnvironmentVariable, TextSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os


def generate_launch_description():
    # ============ 参数定义 ============

    # Factor Perception 参数
    camera_model_arg = DeclareLaunchArgument('camera_model', default_value='OAK-D-PRO-W',
        description='Factor Perception camera model (OAK-D-PRO-W, OAK-D-LR, OAK-D-SR)')
    mxid_or_name_arg = DeclareLaunchArgument('mxid_or_name', default_value='',
        description='Camera MX ID or device name (empty = first available)')
    key_arg = DeclareLaunchArgument('key', default_value=EnvironmentVariable('FACTOR_PERCEPTION_KEY', default_value=''),
        description='Factor Perception SDK license key')
    oak_tf_prefix_arg = DeclareLaunchArgument('oak_tf_prefix', default_value='oak',
        description='TF prefix for camera frames')
    base_frame_id_arg = DeclareLaunchArgument('base_frame_id', default_value='base_link',
        description='Robot base frame ID')
    odom_frame_id_arg = DeclareLaunchArgument('odom_frame_id', default_value='odom',
        description='Odometry frame ID')
    cam_pos_x_arg = DeclareLaunchArgument('cam_pos_x', default_value='0.0',
        description='Camera position X offset from base_frame (meters)')
    cam_pos_y_arg = DeclareLaunchArgument('cam_pos_y', default_value='0.0',
        description='Camera position Y offset from base_frame (meters)')
    cam_pos_z_arg = DeclareLaunchArgument('cam_pos_z', default_value='0.85',
        description='Camera height above base_frame (meters)')
    cam_roll_arg = DeclareLaunchArgument('cam_roll', default_value='0.0',
        description='Camera roll rotation (radians)')
    cam_pitch_arg = DeclareLaunchArgument('cam_pitch', default_value='0.0',
        description='Camera pitch rotation (radians)')
    cam_yaw_arg = DeclareLaunchArgument('cam_yaw', default_value='0.0',
        description='Camera yaw rotation (radians)')
    publish_tf_arg = DeclareLaunchArgument('publish_tf', default_value='true',
        description='Publish camera TF transforms')
    depth_filter_arg = DeclareLaunchArgument('depth_filter', default_value='true',
        description='Enable depth image filtering')
    ir_intensity_arg = DeclareLaunchArgument('ir_intensity', default_value='0.8',
        description='IR illumination intensity (0.0-1.0)')
    min_feat_depth_arg = DeclareLaunchArgument('min_feat_depth', default_value='0.0',
        description='Minimum depth for feature extraction (meters)')
    config_path_arg = DeclareLaunchArgument('config_path',
        default_value=PathJoinSubstitution([
            FindPackageShare('factor_perception'), 'config', 'rtabmap.ini'
        ]), description='Path to RTAB-Map configuration INI file')
    database_path_arg = DeclareLaunchArgument('database_path',
        default_value=[EnvironmentVariable('HOME', default_value='/home/yq'), TextSubstitution(text='/rtabmap.db')],
        description='Path to RTAB-Map database file')
    localization_arg = DeclareLaunchArgument('localization', default_value='false',
        description='Enable localization-only mode (uses existing map)')
    rtabmap_viz_arg = DeclareLaunchArgument('rtabmap_viz', default_value='true',
        description='Show RTAB-Map visualization window')

    # Nav2 参数
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='false',
        description='Use simulation (Gazebo) clock if true')
    autostart_arg = DeclareLaunchArgument('autostart', default_value='true',
        description='Automatically start Nav2 lifecycle nodes')
    nav2_params_file_arg = DeclareLaunchArgument('nav2_params_file',
        default_value=PathJoinSubstitution([
            FindPackageShare('nav24r'), 'config', 'nav2_params.yaml'
        ]), description='Path to Nav2 parameter YAML file')
    map_subscribe_transient_local_arg = DeclareLaunchArgument('map_subscribe_transient_local',
        default_value='true', description='Subscribe to map with TRANSIENT_LOCAL durability')
    use_composition_arg = DeclareLaunchArgument('use_composition', default_value='True',
        description='Use composed bringup via lifecycle manager')
    use_respawn_arg = DeclareLaunchArgument('use_respawn', default_value='false',
        description='Respawn crashed Nav2 nodes')
    log_level_arg = DeclareLaunchArgument('log_level', default_value='warn',
        description='Nav2 node log level (debug, info, warn, error, fatal)')

    # ============ Factor Perception ============

    robot_description_content = Command([
        'xacro ',
        PathJoinSubstitution([FindPackageShare('factor_perception'), 'urdf', 'OAK-D.urdf.xacro']),
        ' camera_model:=', LaunchConfiguration('camera_model'),
        ' tf_prefix:=', LaunchConfiguration('oak_tf_prefix'),
        ' parent_frame:=', LaunchConfiguration('base_frame_id'),
        ' cam_pos_x:=', LaunchConfiguration('cam_pos_x'),
        ' cam_pos_y:=', LaunchConfiguration('cam_pos_y'),
        ' cam_pos_z:=', LaunchConfiguration('cam_pos_z'),
        ' cam_roll:=', LaunchConfiguration('cam_roll'),
        ' cam_pitch:=', LaunchConfiguration('cam_pitch'),
        ' cam_yaw:=', LaunchConfiguration('cam_yaw'),
    ])

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        ros_arguments=['--log-level', 'warn'],
        parameters=[{'robot_description': robot_description_content}]
    )

    factor_perception_node = ComposableNode(
        package='factor_perception',
        plugin='factor_perception::FactorPerceptionNode',
        namespace='factor_perception',
        parameters=[{
            'mxid_or_name': LaunchConfiguration('mxid_or_name'),
            'key': LaunchConfiguration('key'),
            'oak_tf_prefix': LaunchConfiguration('oak_tf_prefix'),
            'base_frame_id': LaunchConfiguration('base_frame_id'),
            'odom_frame_id': LaunchConfiguration('odom_frame_id'),
            'publish_tf': LaunchConfiguration('publish_tf'),
            'depth_filter': LaunchConfiguration('depth_filter'),
            'ir_intensity': LaunchConfiguration('ir_intensity'),
            'min_feat_depth': LaunchConfiguration('min_feat_depth'),
            'blob_path': PathJoinSubstitution([FindPackageShare('factor_perception'), 'blobs', 'HF-Net.blob']),
        }],
    )

    register_node = ComposableNode(
        package='depth_image_proc',
        plugin='depth_image_proc::RegisterNode',
        name='register_node',
        namespace='factor_perception',
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('camera_model'), "' != 'OAK-D-LR' and '",
            LaunchConfiguration('camera_model'), "' != 'OAK-D-SR'"
        ])),
        parameters=[{'fill_upsampling_holes': True}],
    )

    # SLAM 建图 - 新建地图
    rtabmap_slam = ComposableNode(
        package='rtabmap_slam',
        plugin='rtabmap_slam::CoreWrapper',
        name='rtabmap',
        namespace='factor_perception',
        condition=UnlessCondition(LaunchConfiguration('localization')),
        parameters=[{
            'subscribe_rgb': False,
            'subscribe_depth': False,
            'subscribe_rgbd': True,
            'frame_id': LaunchConfiguration('base_frame_id'),
            'odom_frame_id_init': LaunchConfiguration('odom_frame_id'),
            'sync_queue_size': 50,
            'config_path': LaunchConfiguration('config_path'),
            'database_path': LaunchConfiguration('database_path'),
            'Mem/IncrementalMemory': 'true',
            'Mem/InitWMWithAllNodes': 'false',
        }],
    )

    rtabmap_localization = ComposableNode(
        package='rtabmap_slam',
        plugin='rtabmap_slam::CoreWrapper',
        name='rtabmap',
        namespace='factor_perception',
        condition=IfCondition(LaunchConfiguration('localization')),
        parameters=[{
            'subscribe_rgb': False,
            'subscribe_depth': False,
            'subscribe_rgbd': True,
            'frame_id': LaunchConfiguration('base_frame_id'),
            'odom_frame_id_init': LaunchConfiguration('odom_frame_id'),
            'sync_queue_size': 50,
            'config_path': LaunchConfiguration('config_path'),
            'database_path': LaunchConfiguration('database_path'),
            'Mem/IncrementalMemory': 'false',
            'Mem/InitWMWithAllNodes': 'true',
        }],
    )

    factor_perception_container = ComposableNodeContainer(
        name='factor_perception_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        ros_arguments=['--log-level', 'warn'],
        composable_node_descriptions=[factor_perception_node, register_node, rtabmap_slam, rtabmap_localization],
    )

    rtabmap_viz = IncludeLaunchDescription(
        PathJoinSubstitution([
            FindPackageShare('factor_perception'),
            'launch',
            'rtabmap_viz_launch.py'
        ]),
        launch_arguments={'base_frame_id': LaunchConfiguration('base_frame_id')}.items(),
        condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
    )

    # ============ Nav2 ============

    # 使用 navigation_launch.py (不含 SLAM，使用 RTAB-Map 定位)
    nav2_navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('nav2_bringup'), 'launch', 'navigation_launch.py'])
        ]),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
            'params_file': LaunchConfiguration('nav2_params_file'),
            'use_composition': LaunchConfiguration('use_composition'),
            'use_respawn': LaunchConfiguration('use_respawn'),
            'log_level': LaunchConfiguration('log_level'),
        }.items(),
    )

    # ============ 返回 LaunchDescription ============

    return LaunchDescription([
        SetEnvironmentVariable('QT_QPA_PLATFORM', 'xcb'),  # Wayland 兼容 Qt
        # Factor Perception 参数
        camera_model_arg,
        mxid_or_name_arg,
        key_arg,
        oak_tf_prefix_arg,
        base_frame_id_arg,
        odom_frame_id_arg,
        cam_pos_x_arg,
        cam_pos_y_arg,
        cam_pos_z_arg,
        cam_roll_arg,
        cam_pitch_arg,
        cam_yaw_arg,
        publish_tf_arg,
        depth_filter_arg,
        ir_intensity_arg,
        min_feat_depth_arg,
        config_path_arg,
        database_path_arg,
        localization_arg,
        rtabmap_viz_arg,
        # Nav2 参数
        use_sim_time_arg,
        autostart_arg,
        nav2_params_file_arg,
        map_subscribe_transient_local_arg,
        use_composition_arg,
        use_respawn_arg,
        log_level_arg,
        # 节点
        robot_state_publisher_node,
        factor_perception_container,
        rtabmap_viz,
        nav2_navigation,
    ])