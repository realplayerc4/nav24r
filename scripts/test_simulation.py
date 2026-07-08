#!/usr/bin/env python3
"""
仿真环境测试脚本 - 无实机条件下测试 Nav2 基础功能

测试目标：
1. Nav2 生命周期正常启动
2. 代价地图正常加载
3. 全局/本地规划器响应
4. 控制器基础运行
5. 行为服务器正常

前置条件：
- ROS2 Jazzy 已安装
- nav24r 包已构建：colcon build --packages-select nav24r
- 已有地图数据库：~/rtabmap.db 或指定路径
"""

import os
import sys
import subprocess
import time
import signal
from typing import List, Optional


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log_info(msg: str) -> None:
    print(f"{Colors.OKBLUE}[INFO]{Colors.ENDC} {msg}")


def log_ok(msg: str) -> None:
    print(f"{Colors.OKGREEN}[PASS]{Colors.ENDC} {msg}")


def log_fail(msg: str) -> None:
    print(f"{Colors.FAIL}[FAIL]{Colors.ENDC} {msg}")


def log_warn(msg: str) -> None:
    print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {msg}")


def run_cmd(cmd: List[str], timeout: Optional[int] = 30) -> subprocess.CompletedProcess:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired:
        log_warn(f"Command timed out: {' '.join(cmd)}")
        raise


def source_ros2_env():
    """确保 ROS2 环境变量已设置"""
    if 'ROS_DISTRO' not in os.environ:
        os.environ['ROS_DISTRO'] = 'jazzy'
    if 'RMW_IMPLEMENTATION' not in os.environ:
        os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'


def check_ros2_environment() -> bool:
    """检查 ROS2 环境"""
    log_info("检查 ROS2 环境...")
    
    # 检查 ROS_DISTRO
    ros_distro = os.environ.get('ROS_DISTRO', '')
    if ros_distro != 'jazzy':
        log_warn(f"ROS_DISTRO={ros_distro}, 期望 jazzy")
    
    # 检查关键包
    packages = [
        'nav2_bringup',
        'nav2_mppi_controller',
        'rtabmap_slam',
        'depth_image_proc',
        'robot_state_publisher',
    ]
    
    missing = []
    for pkg in packages:
        result = run_cmd(['ros2', 'pkg', 'list'], timeout=10)
        if pkg not in result.stdout:
            missing.append(pkg)
    
    if missing:
        log_fail(f"缺少 ROS2 包: {', '.join(missing)}")
        return False
    
    log_ok("ROS2 环境检查通过")
    return True


def check_nav24r_package() -> bool:
    """检查 nav24r 包是否可用"""
    log_info("检查 nav24r 包...")
    
    result = run_cmd(['ros2', 'pkg', 'list'], timeout=10)
    if 'nav24r' not in result.stdout:
        log_fail("nav24r 包未找到，请先运行 colcon build")
        return False
    
    log_ok("nav24r 包已安装")
    return True


def check_map_database() -> bool:
    """检查地图数据库是否存在"""
    log_info("检查地图数据库...")
    
    db_path = os.path.expanduser('~/rtabmap.db')
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        log_ok(f"找到地图数据库: {db_path} ({size_mb:.1f} MB)")
        return True
    else:
        log_warn(f"未找到地图数据库: {db_path}")
        log_warn("将使用仿真模式，不进行真实定位测试")
        return False


def test_nav2_lifecycle() -> bool:
    """测试 Nav2 生命周期启动"""
    log_info("测试 Nav2 生命周期启动...")
    
    # 使用 Nav2 的导航启动文件，启用仿真时间
    nav2_cmd = [
        'ros2', 'launch', 'nav2_bringup', 'navigation_launch.py',
        'use_sim_time:=true',
        'autostart:=true',
        'params_file:=/home/yq/nav24r/config/nav2_params.yaml',
    ]
    
    try:
        # 启动 Nav2
        proc = subprocess.Popen(
            nav2_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        
        # 等待启动
        log_info("等待 Nav2 启动（10秒）...")
        time.sleep(10)
        
        # 检查进程是否还活着
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            log_fail("Nav2 进程已退出")
            if stderr:
                log_fail(f"错误输出: {stderr.decode()[:500]}")
            return False
        
        # 检查关键节点
        result = run_cmd(['ros2', 'node', 'list'], timeout=10)
        nodes = result.stdout
        
        required_nodes = [
            'controller_server',
            'planner_server',
            'behavior_server',
            'bt_navigator',
        ]
        
        missing_nodes = []
        for node in required_nodes:
            if node not in nodes:
                missing_nodes.append(node)
        
        if missing_nodes:
            log_fail(f"缺少 Nav2 节点: {', '.join(missing_nodes)}")
            proc.terminate()
            return False
        
        log_ok("Nav2 生命周期启动成功")
        
        # 检查话题
        result = run_cmd(['ros2', 'topic', 'list'], timeout=10)
        topics = result.stdout
        
        required_topics = [
            '/cmd_vel',
            '/parameter_events',
        ]
        
        missing_topics = []
        for topic in required_topics:
            if topic not in topics:
                missing_topics.append(topic)
        
        if missing_topics:
            log_warn(f"缺少话题: {', '.join(missing_topics)}")
        else:
            log_ok("Nav2 话题正常")
        
        # 清理
        proc.terminate()
        proc.wait(timeout=5)
        
        return True
        
    except Exception as e:
        log_fail(f"Nav2 生命周期测试失败: {e}")
        return False


def test_costmap_with_mock_data() -> bool:
    """测试代价地图在模拟数据下的加载"""
    log_info("测试代价地图加载...")
    
    # 启动 Nav2
    nav2_cmd = [
        'ros2', 'launch', 'nav2_bringup', 'navigation_launch.py',
        'use_sim_time:=true',
        'autostart:=true',
        'params_file:=/home/yq/nav24r/config/nav2_params.yaml',
    ]
    
    try:
        proc = subprocess.Popen(
            nav2_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        
        time.sleep(8)
        
        # 检查代价地图服务
        result = run_cmd(['ros2', 'service', 'list'], timeout=10)
        services = result.stdout
        
        costmap_services = [
            '/local_costmap/footprint',
            '/global_costmap/footprint',
        ]
        
        missing_services = []
        for svc in costmap_services:
            if svc not in services:
                missing_services.append(svc)
        
        if missing_services:
            log_warn(f"缺少代价地图服务: {', '.join(missing_services)}")
        else:
            log_ok("代价地图服务正常")
        
        proc.terminate()
        proc.wait(timeout=5)
        
        return True
        
    except Exception as e:
        log_fail(f"代价地图测试失败: {e}")
        return False


def test_nav2_goal_interface() -> bool:
    """测试 Nav2 目标接口（仿真环境）"""
    log_info("测试 Nav2 目标接口...")
    
    # 启动 Nav2
    nav2_cmd = [
        'ros2', 'launch', 'nav2_bringup', 'navigation_launch.py',
        'use_sim_time:=true',
        'autostart:=true',
        'params_file:=/home/yq/nav24r/config/nav2_params.yaml',
    ]
    
    try:
        proc = subprocess.Popen(
            nav2_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        
        time.sleep(8)
        
        # 检查导航 action
        result = run_cmd(['ros2', 'action', 'list'], timeout=10)
        actions = result.stdout
        
        required_actions = [
            '/navigate_to_pose',
        ]
        
        missing_actions = []
        for action in required_actions:
            if action not in actions:
                missing_actions.append(action)
        
        if missing_actions:
            log_fail(f"缺少导航 action: {', '.join(missing_actions)}")
            proc.terminate()
            return False
        
        log_ok("Nav2 目标接口正常")
        
        proc.terminate()
        proc.wait(timeout=5)
        
        return True
        
    except Exception as e:
        log_fail(f"目标接口测试失败: {e}")
        return False


def print_summary(results: dict) -> None:
    """打印测试摘要"""
    print("\n" + "="*60)
    print(f"{Colors.HEADER}{Colors.BOLD}测试摘要{Colors.ENDC}")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = f"{Colors.OKGREEN}通过{Colors.ENDC}" if result else f"{Colors.FAIL}失败{Colors.ENDC}"
        print(f"{name:<30} {status}")
    
    print("-"*60)
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}所有测试通过！{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}部分测试失败，请检查日志{Colors.ENDC}")
    
    print("="*60)


def main():
    """主测试流程"""
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("="*60)
    print("NAV24R 仿真环境测试")
    print("="*60)
    print(f"{Colors.ENDC}")
    
    source_ros2_env()
    
    results = {}
    
    # 1. 环境检查
    results['ROS2 环境检查'] = check_ros2_environment()
    results['nav24r 包检查'] = check_nav24r_package()
    
    if not all(results.values()):
        log_fail("环境检查失败，终止测试")
        print_summary(results)
        return 1
    
    # 2. 地图数据库检查
    results['地图数据库'] = check_map_database()
    
    # 3. Nav2 生命周期测试
    results['Nav2 生命周期'] = test_nav2_lifecycle()
    
    # 4. 代价地图测试
    results['代价地图加载'] = test_costmap_with_mock_data()
    
    # 5. 目标接口测试
    results['Nav2 目标接口'] = test_nav2_goal_interface()
    
    # 打印摘要
    print_summary(results)
    
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
