# 改进版 Launch 文件 - Factor Perception + RTAB-Map
# 解决架构问题：隔离容器、生命周期管理、错误恢复
# 版本: v2.0 - 2026-06-18

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler, EmitEvent, LogInfo, TimerAction, ExecuteProcess, GroupAction, OpaqueFunction
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression, TextSubstitution, EnvironmentVariable
from launch_ros.actions import ComposableNodeContainer, Node, LifecycleNode
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.events.lifecycle import ChangeState
from launch.event_handlers import OnProcessExit, OnProcessStart
from lifecycle_msgs.msg import Transition
import os


def generate_launch_description():
    # ============ 参数定义 ============

    # Factor Perception 参数
    camera_model_arg = DeclareLaunchArgument('camera_model', default_value='OAK-D-PRO-W')
    mxid_or_name_arg = DeclareLaunchArgument('mxid_or_name', default_value='')
    key_arg = DeclareLaunchArgument('key', default_value=EnvironmentVariable('FACTOR_PERCEPTION_KEY', default_value=''))
    oak_tf_prefix_arg = DeclareLaunchArgument('oak_tf_prefix', default_value='oak')
    base_frame_id_arg = DeclareLaunchArgument('base_frame_id', default_value='base_link')
    odom_frame_id_arg = DeclareLaunchArgument('odom_frame_id', default_value='odom')
    cam_pos_x_arg = DeclareLaunchArgument('cam_pos_x', default_value='0.0')
    cam_pos_y_arg = DeclareLaunchArgument('cam_pos_y', default_value='0.0')
    cam_pos_z_arg = DeclareLaunchArgument('cam_pos_z', default_value='1.0')  # 相机高度1m（v2.0隔离版安装位置更高）
    cam_roll_arg = DeclareLaunchArgument('cam_roll', default_value='0.0')
    cam_pitch_arg = DeclareLaunchArgument('cam_pitch', default_value='0.0')
    cam_yaw_arg = DeclareLaunchArgument('cam_yaw', default_value='0.0')
    publish_tf_arg = DeclareLaunchArgument('publish_tf', default_value='true')
    depth_filter_arg = DeclareLaunchArgument('depth_filter', default_value='true')
    ir_intensity_arg = DeclareLaunchArgument('ir_intensity', default_value='0.4')
    min_feat_depth_arg = DeclareLaunchArgument('min_feat_depth', default_value='0.0')

    # 使用 PathJoinSubstitution 替代硬编码路径
    config_path_arg = DeclareLaunchArgument('config_path',
        default_value=PathJoinSubstitution([
            FindPackageShare('nav24r'),
            'config', 'rtabmap_custom.ini'
        ]))
    database_path_arg = DeclareLaunchArgument('database_path', default_value=EnvironmentVariable('HOME', default_value='/home/yq') + '/rtabmap.db')
    localization_arg = DeclareLaunchArgument('localization', default_value='false')
    rtabmap_viz_arg = DeclareLaunchArgument('rtabmap_viz', default_value='true')  # 统一默认值
    continue_mapping_arg = DeclareLaunchArgument('continue_mapping', default_value='false')

    # 设备检查参数
    skip_device_check_arg = DeclareLaunchArgument('skip_device_check', default_value='false')

    # ============ 设备检查（启动前 - 信息性检查，不参与条件判断） ============
    # 注意：此检查仅用于调试和确认设备连接状态，不影响节点的启动。
    # 如需基于设备检查结果的条件启动，请使用 skip_device_check 参数。

    # 设备检查脚本（输出到屏幕，不参与控制逻辑）
    device_check_cmd = ExecuteProcess(
        cmd=['bash', '-c',
             'lsusb | grep -qiE "03e7|1443|luxonis|oak" && echo "✓ OAK-D device found" || echo "⚠ No OAK-D device found"'],
        name='device_check',
        output='screen',
    )

    # ============ Robot Description ============

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

    # ============ 硬件驱动容器（隔离） ============

    # Factor Perception 硬件驱动单独容器
    # 使用单线程容器确保确定性硬件访问
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
        extra_arguments=[{'use_intra_process_comms': True}],  # 零拷贝优化
    )

    # 硬件容器（单线程，隔离）
    hardware_container = ComposableNodeContainer(
        name='hardware_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',  # 单线程，确定性访问
        ros_arguments=['--log-level', 'info'],
        composable_node_descriptions=[factor_perception_node],
    )

    # Register 节点（单独容器）
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
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    register_container = ComposableNodeContainer(
        name='register_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[register_node],
    )

    # ============ SLAM 处理容器（隔离） ============

    # SLAM 参数
    slam_params = {
        'subscribe_rgb': False,
        'subscribe_depth': False,
        'subscribe_rgbd': True,
        'frame_id': LaunchConfiguration('base_frame_id'),
        'odom_frame_id_init': LaunchConfiguration('odom_frame_id'),
        'sync_queue_size': 50,
        'config_path': LaunchConfiguration('config_path'),
        'database_path': LaunchConfiguration('database_path'),
        'Grid/3D': 'true',
        'RGBD/ProximityBySpace': 'true',
        'RGBD/ProximityByTime': 'true',
    }

    # SLAM 建图 - 新建地图
    rtabmap_slam_new = ComposableNode(
        package='rtabmap_slam',
        plugin='rtabmap_slam::CoreWrapper',
        name='rtabmap',
        namespace='factor_perception',
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('localization'), "' == 'false' and '",
            LaunchConfiguration('continue_mapping'), "' == 'false'"
        ])),
        parameters=[slam_params, {
            'Mem/IncrementalMemory': 'true',
            'Mem/InitWMWithAllNodes': 'false',
        }],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    # SLAM 建图 - 续建地图
    rtabmap_slam_continue = ComposableNode(
        package='rtabmap_slam',
        plugin='rtabmap_slam::CoreWrapper',
        name='rtabmap',
        namespace='factor_perception',
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('localization'), "' == 'false' and '",
            LaunchConfiguration('continue_mapping'), "' != 'false'"
        ])),
        parameters=[slam_params, {
            'Mem/IncrementalMemory': 'true',
            'Mem/InitWMWithAllNodes': 'true',
        }],
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    # 定位模式
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
        extra_arguments=[{'use_intra_process_comms': True}],
    )

    # SLAM 容器（隔离，每个组件独立执行器）
    slam_container = ComposableNodeContainer(
        name='slam_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_isolated',  # 隔离模式
        ros_arguments=['--log-level', 'info'],
        composable_node_descriptions=[
            rtabmap_slam_new, rtabmap_slam_continue, rtabmap_localization
        ],
    )

    # ============ 可视化（可选） ============

    rtabmap_viz = IncludeLaunchDescription(
        PathJoinSubstitution([
            FindPackageShare('factor_perception'),
            'launch',
            'rtabmap_viz_launch.py'
        ]),
        launch_arguments={'base_frame_id': LaunchConfiguration('base_frame_id')}.items(),
        condition=IfCondition(LaunchConfiguration('rtabmap_viz')),
    )

    # ============ 错误恢复机制（带重启限制和退避策略） ============

    MAX_RESTART_ATTEMPTS = 3       # 最大重启次数
    BASE_RESTART_DELAY = 3.0      # 初始重启延迟（秒）
    BACKOFF_FACTOR = 2.0          # 退避倍数（3s → 6s → 12s）

    # 重启计数器（使用列表以支持闭包内修改）
    hardware_restart_count = [0]
    slam_restart_count = [0]

    def make_restart_handler(container, restart_count, container_name):
        """创建带重启限制和指数退避的事件处理器"""
        def on_exit_event(context):
            restart_count[0] += 1
            attempt = restart_count[0]
            if attempt > MAX_RESTART_ATTEMPTS:
                return [LogInfo(msg=(
                    f'[CRITICAL] {container_name} 已达到最大重启次数 ({MAX_RESTART_ATTEMPTS})，'
                    f'停止重启。请检查设备连接或日志排查崩溃原因。'
                ))]
            delay = BASE_RESTART_DELAY * (BACKOFF_FACTOR ** (attempt - 1))
            return [
                LogInfo(msg=(
                    f'[WARN] {container_name} 崩溃，第 {attempt}/{MAX_RESTART_ATTEMPTS} 次重启，'
                    f'等待 {delay:.1f} 秒后重启...'
                )),
                TimerAction(
                    period=delay,
                    actions=[container]
                )
            ]
        return RegisterEventHandler(
            OnProcessExit(
                target_action=container,
                on_exit=OpaqueFunction(function=on_exit_event)
            )
        )

    # 硬件容器崩溃时的自动重启（带限制和退避）
    hardware_restart_handler = make_restart_handler(
        hardware_container, hardware_restart_count, 'Hardware container'
    )

    # SLAM 容器崩溃时的自动重启（带限制和退避）
    slam_restart_handler = make_restart_handler(
        slam_container, slam_restart_count, 'SLAM container'
    )

    # ============ 返回 LaunchDescription ============

    return LaunchDescription([
        # 参数
        camera_model_arg, mxid_or_name_arg, key_arg,
        oak_tf_prefix_arg, base_frame_id_arg, odom_frame_id_arg,
        cam_pos_x_arg, cam_pos_y_arg, cam_pos_z_arg,
        cam_roll_arg, cam_pitch_arg, cam_yaw_arg,
        publish_tf_arg, depth_filter_arg,
        ir_intensity_arg, min_feat_depth_arg,
        config_path_arg, database_path_arg,
        localization_arg, rtabmap_viz_arg, continue_mapping_arg,
        skip_device_check_arg,

        # 设备检查（可选）
        device_check_cmd,

        # 节点
        robot_state_publisher_node,
        hardware_container,
        register_container,
        slam_container,
        rtabmap_viz,

        # 错误恢复
        hardware_restart_handler,
        slam_restart_handler,
    ])