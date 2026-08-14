# 综合启动文件 - Factor Perception + Nav2
# 人形机器人导航系统

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction, SetEnvironmentVariable, ExecuteProcess
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
    log_level_arg = DeclareLaunchArgument('log_level', default_value='warn',
        description='Nav2 node log level (debug, info, warn, error, fatal)')

    # T1 Bridge 参数
    use_t1_bridge_arg = DeclareLaunchArgument('use_t1_bridge', default_value='false',
        description='Enable T1 robot bridge (Nav2 cmd_vel → T1 SDK)')
    t1_network_if_arg = DeclareLaunchArgument('t1_network_interface', default_value='enx207bd2d33010',
        description='T1 SDK network interface (e.g. eth0)')

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
    # 手动创建 Nav2 节点（不通过 navigation_launch.py）
    # 原因：navigation_launch.py 硬编码包含 collision_monitor，
    # 但 opennav 版本的 collision_monitor 参数不兼容（observation_sources 要求非空）
    # costmap 已处理避障，collision_monitor 非必需

    nav2_controller = Node(
        package='nav2_controller',
        executable='controller_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
    )

    # 速度平滑器：controller 输出 /cmd_vel → smoother → /cmd_vel_smoothed → t1_bridge
    # 人形机器人不能急启急停，平滑加减速（防前倾）
    nav2_velocity_smoother = Node(
        package='nav2_velocity_smoother',
        executable='velocity_smoother',
        name='velocity_smoother',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
    )

    nav2_smoother = Node(
        package='nav2_smoother',
        executable='smoother_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
    )

    nav2_planner = Node(
        package='nav2_planner',
        executable='planner_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
    )

    nav2_route = Node(
        package='nav2_route',
        executable='route_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
    )

    nav2_behaviors = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
    )

    nav2_bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
        remappings=[('tf', 'tf'), ('tf_static', 'tf_static')],
    )

    nav2_waypoint = Node(
        package='nav2_waypoint_follower',
        executable='waypoint_follower',
        ros_arguments=['--log-level', 'warn'],
        parameters=[LaunchConfiguration('nav2_params_file')],
        remappings=[('tf', 'tf'), ('tf_static', 'tf_static')],
    )

    nav2_lifecycle = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        ros_arguments=['--log-level', 'warn'],
        parameters=[
            {'autostart': LaunchConfiguration('autostart')},
            {'node_names': [
                'controller_server',
                'smoother_server',
                'planner_server',
                'route_server',
                'behavior_server',
                'bt_navigator',
                'waypoint_follower',
                'velocity_smoother',
            ]},
        ],
    )

    # ============ T1 Bridge ============
    # Nav2 cmd_vel → 加速进化 T1 SDK（纯 Python，不用 rclpy，避免 CycloneDDS 与 FastDDS 冲突）
    t1_bridge = ExecuteProcess(
        cmd=['python3',
             '/home/yq/nav24r/scripts/t1_bridge.py',
             '--network-interface', LaunchConfiguration('t1_network_interface'),
             '--cmd-vel-topic', '/cmd_vel_smoothed',
             '--watchdog-timeout', '2.0'],
        output='screen',
        condition=IfCondition(LaunchConfiguration('use_t1_bridge')),
    )

    # ============ 返回 LaunchDescription ============

    return LaunchDescription([
        SetEnvironmentVariable('QT_QPA_PLATFORM', 'xcb'),  # Wayland 兼容 Qt
        # 隔离 domain：Nav2(CycloneDDS) 用 42，避免与机器人 FastDDS(domain 0) 冲突
        SetEnvironmentVariable('ROS_DOMAIN_ID', '42'),
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
        log_level_arg,
        use_t1_bridge_arg,
        t1_network_if_arg,
        # 节点
        robot_state_publisher_node,
        factor_perception_container,
        rtabmap_viz,
        nav2_controller,
        nav2_velocity_smoother,
        nav2_smoother,
        nav2_planner,
        nav2_route,
        nav2_behaviors,
        nav2_bt_navigator,
        nav2_waypoint,
        nav2_lifecycle,
        t1_bridge,
    ])