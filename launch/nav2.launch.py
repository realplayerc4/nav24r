# Nav2 Launch 文件 - 人形机器人
# 配合 Factor Perception 使用

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # 参数
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='false')
    autostart_arg = DeclareLaunchArgument('autostart', default_value='true')
    params_file_arg = DeclareLaunchArgument('params_file',
        default_value=PathJoinSubstitution([FindPackageShare('nav24r'), 'config', 'nav2_params.yaml']))
    map_subscribe_transient_local_arg = DeclareLaunchArgument('map_subscribe_transient_local',
        default_value='true')
    use_composition_arg = DeclareLaunchArgument('use_composition', default_value='true')
    use_respawn_arg = DeclareLaunchArgument('use_respawn', default_value='false')
    log_level_arg = DeclareLaunchArgument('log_level', default_value='info')

    # Nav2 Bringup
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('nav2_bringup'), 'launch', 'bringup_launch.py'])
        ]),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'autostart': LaunchConfiguration('autostart'),
            'params_file': LaunchConfiguration('params_file'),
            'map_subscribe_transient_local': LaunchConfiguration('map_subscribe_transient_local'),
            'use_composition': LaunchConfiguration('use_composition'),
            'use_respawn': LaunchConfiguration('use_respawn'),
            'log_level': LaunchConfiguration('log_level'),
        }.items(),
    )

    return LaunchDescription([
        use_sim_time_arg,
        autostart_arg,
        params_file_arg,
        map_subscribe_transient_local_arg,
        use_composition_arg,
        use_respawn_arg,
        log_level_arg,
        nav2_bringup,
    ])