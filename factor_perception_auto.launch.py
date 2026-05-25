from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.substitutions import FindPackageShare
import os

def generate_launch_description():
    # Launch arguments
    camera_model_arg = DeclareLaunchArgument('camera_model', default_value='OAK-D-PRO-W')
    mxid_or_name_arg = DeclareLaunchArgument('mxid_or_name', default_value='')  # Empty for auto-discovery
    key_arg = DeclareLaunchArgument('key', default_value='')
    oak_tf_prefix_arg = DeclareLaunchArgument('oak_tf_prefix', default_value='oak')
    base_frame_id_arg = DeclareLaunchArgument('base_frame_id', default_value='base_link')
    odom_frame_id_arg = DeclareLaunchArgument('odom_frame_id', default_value='odom')
    publish_tf_arg = DeclareLaunchArgument('publish_tf', default_value='false')
    depth_filter_arg = DeclareLaunchArgument('depth_filter', default_value='true')
    ir_intensity_arg = DeclareLaunchArgument('ir_intensity', default_value='0.4')
    
    # Robot description
    robot_description_content = f"xacro {PathJoinSubstitution([FindPackageShare('factor_perception'), 'urdf', 'OAK-D.urdf.xacro'])} camera_model:=OAK-D-PRO-W tf_prefix:=oak parent_frame:=base_link"
    
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_content}]
    )
    
    # Factor Perception node with auto-discovery
    factor_perception_node = ComposableNode(
        package='factor_perception',
        plugin='factor_perception::FactorPerceptionNode',
        namespace='factor_perception',
        parameters=[{
            'mxid_or_name': '',
            'key': '',
            'oak_tf_prefix': 'oak',
            'base_frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'publish_tf': False,
            'depth_filter': True,
            'ir_intensity': 0.4,
            'blob_path': PathJoinSubstitution([FindPackageShare('factor_perception'), 'blobs', 'HF-Net.blob']),
        }],
    )
    
    # Component container
    factor_perception_container = ComposableNodeContainer(
        name='factor_perception_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[factor_perception_node],
    )
    
    return LaunchDescription([
        camera_model_arg, mxid_or_name_arg, key_arg,
        oak_tf_prefix_arg, base_frame_id_arg, odom_frame_id_arg,
        publish_tf_arg, depth_filter_arg, ir_intensity_arg,
        robot_state_publisher_node, factor_perception_container,
    ])
