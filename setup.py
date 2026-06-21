import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'nav24r'

setup(
    name=package_name,
    version='2.0.0',
    packages=find_packages(exclude=['tests', 'Calibrat']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*')),
    ],
    install_requires=[
        'pyyaml',
        'setuptools',
    ],
    zip_safe=True,
    maintainer='NAV24R Team',
    maintainer_email='nav24r-maintainer@users.noreply.github.com',
    description='NAV24R - 人形机器人导航系统，集成 Factor Perception SDK、RTAB-Map SLAM 和 Nav2 导航栈',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'factor_control_panel = scripts.factor_control_panel:main',
        ],
    },
)
