from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression, EnvironmentVariable, TextSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera_model_arg = DeclareLaunchArgument('camera_model', default_value='OAK-D-PRO-W')
    mxid_or_name_arg = DeclareLaunchArgument('mxid_or_name', default_value='')
    key_arg = DeclareLaunchArgument('key', default_value=EnvironmentVariable('FACTOR_PERCEPTION_KEY', default_value=''))
    oak_tf_prefix_arg = DeclareLaunchArgument('oak_tf_prefix', default_value='oak')
    base_frame_id_arg = DeclareLaunchArgument('base_frame_id', default_value='base_link')
    odom_frame_id_arg = DeclareLaunchArgument('odom_frame_id', default_value='odom')
    cam_pos_x_arg = DeclareLaunchArgument('cam_pos_x', default_value='0.0')
    cam_pos_y_arg = DeclareLaunchArgument('cam_pos_y', default_value='0.0')
    cam_pos_z_arg = DeclareLaunchArgument('cam_pos_z', default_value='0.85')
    cam_roll_arg = DeclareLaunchArgument('cam_roll', default_value='0.0')
    cam_pitch_arg = DeclareLaunchArgument('cam_pitch', default_value='0.0')
    cam_yaw_arg = DeclareLaunchArgument('cam_yaw', default_value='0.0')
    publish_tf_arg = DeclareLaunchArgument('publish_tf', default_value='true')
    depth_filter_arg = DeclareLaunchArgument('depth_filter', default_value='true')
    ir_intensity_arg = DeclareLaunchArgument('ir_intensity', default_value='0.8')
    min_feat_depth_arg = DeclareLaunchArgument('min_feat_depth', default_value='0.0')
    camera_cpu_arg = DeclareLaunchArgument('camera_cpu', default_value='-1')
    imu_cpu_arg = DeclareLaunchArgument('imu_cpu', default_value='-1')
    rgb_fps_arg = DeclareLaunchArgument('rgb_fps', default_value='20.0')
    config_path_arg = DeclareLaunchArgument('config_path',
        default_value=PathJoinSubstitution([
            FindPackageShare('factor_perception'), 'config', 'rtabmap.ini'
        ]))
    database_path_arg = DeclareLaunchArgument('database_path', default_value=[EnvironmentVariable('HOME', default_value='/home/yq'), TextSubstitution(text='/rtabmap.db')])
    localization_arg = DeclareLaunchArgument('localization', default_value='false')
    rtabmap_viz_arg = DeclareLaunchArgument('rtabmap_viz', default_value='true')

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
        parameters=[{'robot_description': robot_description_content}],
    )

    factor_perception_node = ComposableNode(
        package='factor_perception',
        plugin='factor_perception::FactorPerceptionNode',
        name='factor_perception_node',
        namespace='factor_perception',
        parameters=[{
            'mxid_or_name': LaunchConfiguration('mxid_or_name'),
            'key': LaunchConfiguration('key'),
            'camera_tf_prefix': LaunchConfiguration('oak_tf_prefix'),
            'base_frame_id': LaunchConfiguration('base_frame_id'),
            'odom_frame_id': LaunchConfiguration('odom_frame_id'),
            'publish_tf': LaunchConfiguration('publish_tf'),
            'depth_filter': LaunchConfiguration('depth_filter'),
            'ir_intensity': LaunchConfiguration('ir_intensity'),
            'min_feat_depth': LaunchConfiguration('min_feat_depth'),
            'camera_cpu': LaunchConfiguration('camera_cpu'),
            'imu_cpu': LaunchConfiguration('imu_cpu'),
            'rgb_fps': LaunchConfiguration('rgb_fps'),
            'blob_path': PathJoinSubstitution([FindPackageShare('factor_perception'), 'blobs', 'HF-Net.blob']),
        }],
    )

    register_node = ComposableNode(
        package='depth_image_proc',
        plugin='depth_image_proc::RegisterNode',
        name='register_node',
        namespace='factor_perception',
        parameters=[{'fill_upsampling_holes': True}],
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('camera_model'), "' != 'OAK-D-LR' and '", LaunchConfiguration('camera_model'), "' != 'OAK-D-SR'"
        ])),
    )

    slam_params = {
        'subscribe_rgb': False,
        'subscribe_depth': False,
        'subscribe_rgbd': True,
        'frame_id': LaunchConfiguration('base_frame_id'),
        'odom_frame_id_init': LaunchConfiguration('odom_frame_id'),
        'sync_queue_size': 50,
        'config_path': LaunchConfiguration('config_path'),
        'database_path': LaunchConfiguration('database_path'),
        'RGBD/ProximityBySpace': 'true',
        'RGBD/ProximityByTime': 'true',
    }

    rtabmap_slam = ComposableNode(
        package='rtabmap_slam',
        plugin='rtabmap_slam::CoreWrapper',
        name='rtabmap',
        namespace='factor_perception',
        condition=UnlessCondition(LaunchConfiguration('localization')),
        parameters=[slam_params, {
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
        parameters=[slam_params, {
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
        composable_node_descriptions=[
            factor_perception_node,
            register_node,
            rtabmap_slam,
            rtabmap_localization,
        ],
    )

    rtabmap_viz = Node(
        executable='rtabmap_viz',
        package='rtabmap_viz',
        namespace='factor_perception',
        parameters=[{
            'subscribe_rgbd': True,
            'frame_id': LaunchConfiguration('base_frame_id'),
            'max_odom_update_rate': 200.0,
            'sync_queue_size': 50,
        }],
        ros_arguments=['--log-level', 'warn'],
        condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
    )

    return LaunchDescription([
        SetEnvironmentVariable('QT_QPA_PLATFORM', 'xcb'),  # Wayland 兼容 Qt
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
        camera_cpu_arg,
        imu_cpu_arg,
        rgb_fps_arg,
        config_path_arg,
        database_path_arg,
        localization_arg,
        rtabmap_viz_arg,
        robot_state_publisher_node,
        factor_perception_container,
        rtabmap_viz,
    ])
