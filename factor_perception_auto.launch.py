from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression, EnvironmentVariable
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera_model_arg = DeclareLaunchArgument('camera_model', default_value='OAK-D-PRO-W')
    mxid_or_name_arg = DeclareLaunchArgument('mxid_or_name', default_value='')  # 自动检测
    key_arg = DeclareLaunchArgument('key', default_value=EnvironmentVariable('FACTOR_PERCEPTION_KEY', default_value=''))  # 相机 Key（通过环境变量 FACTOR_PERCEPTION_KEY 传入）
    oak_tf_prefix_arg = DeclareLaunchArgument('oak_tf_prefix', default_value='oak')
    base_frame_id_arg = DeclareLaunchArgument('base_frame_id', default_value='base_link')
    odom_frame_id_arg = DeclareLaunchArgument('odom_frame_id', default_value='odom')
    cam_pos_x_arg = DeclareLaunchArgument('cam_pos_x', default_value='0.0')  # 相机位置: 前方
    cam_pos_y_arg = DeclareLaunchArgument('cam_pos_y', default_value='0.0')  # 相机位置: 正中
    cam_pos_z_arg = DeclareLaunchArgument('cam_pos_z', default_value='1.0')  # 相机高度: 1.0m（统一默认值）
    cam_roll_arg = DeclareLaunchArgument('cam_roll', default_value='0.0')
    cam_pitch_arg = DeclareLaunchArgument('cam_pitch', default_value='0.0')  # 相机俯仰: 水平
    cam_yaw_arg = DeclareLaunchArgument('cam_yaw', default_value='0.0')
    publish_tf_arg = DeclareLaunchArgument('publish_tf', default_value='true')  # SDK 默认值
    depth_filter_arg = DeclareLaunchArgument('depth_filter', default_value='true')  # 启用深度滤波
    ir_intensity_arg = DeclareLaunchArgument('ir_intensity', default_value='0.4')  # IR 补光
    min_feat_depth_arg = DeclareLaunchArgument('min_feat_depth', default_value='0.0')
    config_path_arg = DeclareLaunchArgument('config_path',
        default_value=PathJoinSubstitution([
            FindPackageShare('nav24r'), 'config', 'rtabmap_custom.ini'
        ]))
    database_path_arg = DeclareLaunchArgument('database_path', default_value=EnvironmentVariable('HOME', default_value='/home/yq') + '/rtabmap.db')
    localization_arg = DeclareLaunchArgument('localization', default_value='false')
    rtabmap_viz_arg = DeclareLaunchArgument('rtabmap_viz', default_value='true')
    # 续建模式: 传入字符串 'true' 来加载已有地图数据
    # 注意: ROS2 launch 命令行会自动把 :=true 解析为 bool，
    # 而 RTAB-Map 的 Mem/InitWMWithAllNodes 要求 string 类型，
    # 所以这里用两个 SLAM 节点 + 条件选择来规避类型问题
    continue_mapping_arg = DeclareLaunchArgument('continue_mapping', default_value='false')

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
        package = 'robot_state_publisher',
        executable = 'robot_state_publisher',
        ros_arguments = ['--log-level', 'warn'],
        parameters = [{'robot_description': robot_description_content}]
    )

    factor_perception_node = ComposableNode(
        package = 'factor_perception',
        plugin = 'factor_perception::FactorPerceptionNode',
        namespace = 'factor_perception',
        parameters = [{
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
        package = 'depth_image_proc',
        plugin = 'depth_image_proc::RegisterNode',
        name = 'register_node',
        namespace = 'factor_perception',
        condition = IfCondition(PythonExpression([
            "'", LaunchConfiguration('camera_model'), "' != 'OAK-D-LR' and '", LaunchConfiguration('camera_model'), "' != 'OAK-D-SR'"
        ])),
        parameters = [{'fill_upsampling_holes': True}],
    )

    # SLAM 建图 - 新建地图（从空地图开始）
    rtabmap_slam_new = ComposableNode(
        package = 'rtabmap_slam',
        plugin = 'rtabmap_slam::CoreWrapper',
        name = 'rtabmap',
        namespace = 'factor_perception',
        condition = IfCondition(PythonExpression([
            "'", LaunchConfiguration('localization'), "' == 'false' and '",
            LaunchConfiguration('continue_mapping'), "' == 'false'"
        ])),
        parameters = [{
            'subscribe_rgb': False,
            'subscribe_depth': False,
            'subscribe_rgbd': True,
            'frame_id': LaunchConfiguration('base_frame_id'),
            'odom_frame_id_init': LaunchConfiguration('odom_frame_id'),
            'sync_queue_size': 50,
            'config_path': LaunchConfiguration('config_path'),
            'database_path': LaunchConfiguration('database_path'),
            'Mem/IncrementalMemory': 'true',
            'Mem/InitWMWithAllNodes': 'false',   # 新建: 不加载旧节点
            'Grid/3D': 'true',
            # 关键参数覆盖（优先级高于 ini）
            'RGBD/ProximityBySpace': 'true',
            'RGBD/ProximityByTime': 'true',
        }],
    )

    # SLAM 建图 - 续建地图（加载已有地图数据）
    rtabmap_slam_continue = ComposableNode(
        package = 'rtabmap_slam',
        plugin = 'rtabmap_slam::CoreWrapper',
        name = 'rtabmap',
        namespace = 'factor_perception',
        condition = IfCondition(PythonExpression([
            "'", LaunchConfiguration('localization'), "' == 'false' and '",
            LaunchConfiguration('continue_mapping'), "' != 'false'"
        ])),
        parameters = [{
            'subscribe_rgb': False,
            'subscribe_depth': False,
            'subscribe_rgbd': True,
            'frame_id': LaunchConfiguration('base_frame_id'),
            'odom_frame_id_init': LaunchConfiguration('odom_frame_id'),
            'sync_queue_size': 50,
            'config_path': LaunchConfiguration('config_path'),
            'database_path': LaunchConfiguration('database_path'),
            'Mem/IncrementalMemory': 'true',
            'Mem/InitWMWithAllNodes': 'true',    # 续建: 加载所有已有节点
            'Grid/3D': 'true',
            'RGBD/ProximityBySpace': 'true',
            'RGBD/ProximityByTime': 'true',
        }],
    )

    rtabmap_localization = ComposableNode(
        package = 'rtabmap_slam',
        plugin = 'rtabmap_slam::CoreWrapper',
        name = 'rtabmap',  # 与新建/续建节点保持一致，确保话题名匹配
        namespace = 'factor_perception',
        condition = IfCondition(LaunchConfiguration('localization')),
        parameters = [{
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
            'Grid/3D': 'true',
            'RGBD/ProximityBySpace': 'true',
            'RGBD/ProximityByTime': 'true',
        }],
    )

    factor_perception_container = ComposableNodeContainer(
        name = 'factor_perception_container',
        namespace = '',
        package = 'rclcpp_components',
        executable = 'component_container_mt',
        ros_arguments = ['--log-level', 'info'],  # 改为 info 以查看组件加载信息
        composable_node_descriptions = [factor_perception_node, register_node, rtabmap_slam_new, rtabmap_slam_continue, rtabmap_localization],
    )

    rtabmap_viz = IncludeLaunchDescription(
        PathJoinSubstitution([
            FindPackageShare('factor_perception'),
            'launch',
            'rtabmap_viz_launch.py'
        ]),
        launch_arguments = {'base_frame_id': LaunchConfiguration('base_frame_id')}.items(),
        condition = IfCondition(LaunchConfiguration('rtabmap_viz')),
    )

    return LaunchDescription([
        camera_model_arg, mxid_or_name_arg, key_arg,
        oak_tf_prefix_arg, base_frame_id_arg, odom_frame_id_arg,
        cam_pos_x_arg, cam_pos_y_arg, cam_pos_z_arg,
        cam_roll_arg, cam_pitch_arg, cam_yaw_arg,
        publish_tf_arg, depth_filter_arg,
        ir_intensity_arg, min_feat_depth_arg,
        config_path_arg, database_path_arg,
        localization_arg, rtabmap_viz_arg, continue_mapping_arg,
        robot_state_publisher_node, factor_perception_container, rtabmap_viz,
    ])