from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'nav24r'

setup(
    name=package_name,
    version='2.3.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # ament index 注册
        ('share/ament_index/resource_index/packages',
            ['resource/nav24r']),
        # package.xml
        ('share/' + package_name, ['package.xml']),
        # launch 文件（根目录 + launch/ 子目录 + simulation 子目录）
        ('share/' + package_name + '/launch',
            glob('launch/*.py') + glob('factor_perception_auto.launch.py') + glob('launch/simulation/*.py')),
        # config 文件
        ('share/' + package_name + '/config',
            glob('config/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='nav24r',
    maintainer_email='todo@example.com',
    description='人形机器人自主导航系统 - ROS2 Jazzy + Factor Perception SDK + RTAB-Map + Nav2',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mock_odom_publisher = scripts.mock_odom_publisher:main',
            'mock_pointcloud_publisher = scripts.mock_pointcloud_publisher:main',
            'mock_robot = scripts.mock_robot:main',
            'generate_test_map = scripts.generate_test_map:main',
            'test_simulation = scripts.test_simulation:main',
            'odom_covariance_fix = scripts.odom_covariance_fix:main',
            't1_bridge = scripts.t1_bridge:main',
            'mock_trajectory_publisher = scripts.mock_trajectory_publisher:main',
            'mock_map_publisher = scripts.mock_map_publisher:main',
            'test_nav2_goal = scripts.test_nav2_goal:main',
        ],
    },
)
