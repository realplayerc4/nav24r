#!/usr/bin/env python3
"""
Factor Perception 控制面板
带设备检测和相机重启功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import json
import logging
import re
import shutil
import yaml
from datetime import datetime
import glob
import threading
import time

# 配置日志
LOG_DIR = os.path.expanduser("~/.local/share/nav24r/logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(LOG_DIR, 'factor_control_panel.log')
)
logger = logging.getLogger(__name__)

# 地图 ID 白名单校验：只允许字母、数字、下划线、连字符
MAP_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

# 地图回收站目录
TRASH_DIR = os.path.expanduser("~/.local/share/nav24r/trash/maps")


def validate_map_id(map_id):
    """校验地图 ID，防止命令注入"""
    if not map_id:
        return False, "地图ID不能为空"
    if not MAP_ID_PATTERN.match(map_id):
        return False, "地图ID只能包含字母、数字、下划线和连字符"
    if len(map_id) > 128:
        return False, "地图ID过长（最多128字符）"
    return True, ""

class FactorControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Factor Perception 控制面板")
        self.root.geometry("650x600")

        # 加载配置
        self.load_app_config()

        # 续建模式标记
        self.is_continue = False

        # 设备状态
        self.device_connected = False
        self.device_check_thread = None
        self.auto_check_enabled = True

        # 动态解析项目根目录（脚本在 scripts/ 下，向上一级即为项目根）
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_script_dir)
        self.config_file = os.path.join(_project_root, "config", "maps_config.json")
        self.maps_dir = os.path.expanduser("~/rtabmap_maps")

        self.load_config()
        self.create_ui()

        # 启动设备检测
        self.start_device_monitor()

    def load_app_config(self):
        """加载应用配置文件"""
        # 动态定位配置文件：scripts/ -> project_root -> config/
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_script_dir)
        config_path = os.path.join(_project_root, "config", "factor_perception_config.yaml")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.app_config = yaml.safe_load(f)
                # 用动态计算的路径覆盖配置文件中可能存在的硬编码路径
                if 'paths' not in self.app_config:
                    self.app_config['paths'] = {}
                self.app_config['paths']['project_root'] = _project_root
                self.app_config['paths']['config_dir'] = os.path.join(_project_root, 'config')
                self.app_config['paths']['scripts_dir'] = _script_dir
                logger.info(f"配置文件加载成功: {config_path}, project_root={_project_root}")
            else:
                # 默认配置
                self.app_config = {
                    'camera': {'key': os.environ.get('FACTOR_PERCEPTION_KEY', '')},
                    'ros': {'distro': 'jazzy', 'setup_path': '/opt/ros/jazzy/setup.bash'},
                    'paths': {
                        'project_root': _project_root,
                        'config_dir': os.path.join(_project_root, 'config'),
                        'scripts_dir': _script_dir,
                    }
                }
                logger.warning("配置文件不存在，使用动态默认配置（camera.key 从 FACTOR_PERCEPTION_KEY 环境变量读取）")
                if not self.app_config['camera']['key']:
                    logger.error("FACTOR_PERCEPTION_KEY 环境变量未设置，相机密钥为空！请设置环境变量后重试")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.app_config = {
                'camera': {'key': os.environ.get('FACTOR_PERCEPTION_KEY', '')},
                'ros': {'distro': 'jazzy', 'setup_path': '/opt/ros/jazzy/setup.bash'},
                'paths': {
                    'project_root': _project_root,
                    'config_dir': os.path.join(_project_root, 'config'),
                    'scripts_dir': _script_dir,
                }
            }

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {"maps_dir": "~/rtabmap_maps", "last_map": None, "maps": {}}

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def create_ui(self):
        # 标题
        tk.Label(self.root, text="Factor Perception 控制面板",
                font=('Arial', 16, 'bold'), fg='#00ff88', bg='#2b2b2b').pack(pady=10)
        self.root.configure(bg='#2b2b2b')

        # === 设备状态区域（新增） ===
        device_frame = tk.LabelFrame(self.root, text="📷 OAK-D 设备状态", font=('Arial', 11), padx=10, pady=10)
        device_frame.pack(fill=tk.X, padx=20, pady=5)

        # 设备状态显示
        status_row = tk.Frame(device_frame)
        status_row.pack(fill=tk.X, pady=3)

        self.device_status_var = tk.StringVar(value="⏳ 正在检测设备...")
        self.device_status_label = tk.Label(status_row, textvariable=self.device_status_var,
                                            font=('Arial', 10, 'bold'), fg='#ffaa00')
        self.device_status_label.pack(side=tk.LEFT)

        # 设备详情
        self.device_info_var = tk.StringVar(value="")
        tk.Label(status_row, textvariable=self.device_info_var, font=('Arial', 9), fg='#888888').pack(side=tk.LEFT, padx=10)

        # 设备操作按钮
        device_btn_row = tk.Frame(device_frame)
        device_btn_row.pack(fill=tk.X, pady=5)

        tk.Button(device_btn_row, text="🔍 检测设备", width=12, height=1,
                 command=self.check_device_now, bg='#3d5a80', fg='white').pack(side=tk.LEFT, padx=3)
        tk.Button(device_btn_row, text="🔄 重启相机", width=12, height=1,
                 command=self.restart_camera, bg='#e07c24', fg='white').pack(side=tk.LEFT, padx=3)
        tk.Button(device_btn_row, text="⚡ 强制重连", width=12, height=1,
                 command=self.force_reconnect, bg='#e63946', fg='white').pack(side=tk.LEFT, padx=3)

        # 自动检测开关
        self.auto_check_var = tk.BooleanVar(value=True)
        tk.Checkbutton(device_btn_row, text="自动检测", variable=self.auto_check_var,
                      command=self.toggle_auto_check, bg='#2b2b2b', fg='white',
                      selectcolor='#2b2b2b', activebackground='#2b2b2b').pack(side=tk.RIGHT, padx=5)

        # === 地图管理 ===
        map_frame = tk.LabelFrame(self.root, text="地图管理", font=('Arial', 11), padx=10, pady=10)
        map_frame.pack(fill=tk.X, padx=20, pady=5)

        # 地图ID
        row1 = tk.Frame(map_frame)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="地图ID:").pack(side=tk.LEFT)
        self.map_id_entry = tk.Entry(row1, width=20)
        self.map_id_entry.pack(side=tk.LEFT, padx=10)
        self.map_id_entry.insert(0, f"map_{datetime.now().strftime('%Y%m%d_%H%M')}")
        tk.Button(row1, text="新建地图", command=self.new_map, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)

        # 地图选择
        row2 = tk.Frame(map_frame)
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="已有地图:").pack(side=tk.LEFT)
        self.map_combo = ttk.Combobox(row2, width=25)
        self.map_combo.pack(side=tk.LEFT, padx=10)
        tk.Button(row2, text="刷新", command=self.refresh_maps, bg='#3d5a80', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="续建", command=self.continue_map, bg='#e07c24', fg='white').pack(side=tk.LEFT, padx=2)
        tk.Button(row2, text="删除", command=self.delete_map, bg='#e63946', fg='white').pack(side=tk.LEFT, padx=2)

        # 新增：查看地图按钮和导出功能
        row_map = tk.Frame(map_frame)
        row_map.pack(fill=tk.X, pady=3)
        tk.Button(row_map, text="👁️ 查看地图", width=14, height=1, command=self.view_map_only, bg='#9b59b6', fg='white').pack(side=tk.LEFT, padx=3)
        tk.Button(row_map, text="📊 解读地图质量", width=14, height=1, command=self.analyze_map_quality, bg='#e67e22', fg='white').pack(side=tk.LEFT, padx=3)
        tk.Button(row_map, text="🗺️ 导出Octomap", width=14, height=1, command=self.export_octomap, bg='#16a085', fg='white').pack(side=tk.LEFT, padx=3)

        self.refresh_maps()

        # 功能按钮
        btn_frame = tk.LabelFrame(self.root, text="功能", font=('Arial', 11), padx=10, pady=10)
        btn_frame.pack(fill=tk.X, padx=20, pady=5)

        btn_row1 = tk.Frame(btn_frame)
        btn_row1.pack(pady=5)
        tk.Button(btn_row1, text="🗺️ 开始建图", width=14, height=2, command=self.start_mapping, bg='#3d5a80', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row1, text="🧭 开始导航", width=14, height=2, command=self.start_navigation, bg='#3d5a80', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row1, text="🚀 完整导航", width=14, height=2, command=self.start_full_nav, bg='#3d5a80', fg='white').pack(side=tk.LEFT, padx=5)

        btn_row2 = tk.Frame(btn_frame)
        btn_row2.pack(pady=5)
        tk.Button(btn_row2, text="📊 RViz", width=14, height=2, command=self.launch_rviz, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row2, text="📊 RViz 3D", width=14, height=2, command=self.launch_rviz_3d, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row2, text="🗺️ 地图观察", width=14, height=2, command=self.launch_map_viewer, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)

        btn_row3 = tk.Frame(btn_frame)
        btn_row3.pack(pady=5)
        tk.Button(btn_row3, text="📁 数据库", width=14, height=2, command=self.view_database, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row3, text="⏹️ 停止", width=14, height=2, command=self.stop_all, bg='#e63946', fg='white').pack(side=tk.LEFT, padx=5)

        # 状态
        self.status_var = tk.StringVar(value="状态: 就绪")
        tk.Label(self.root, textvariable=self.status_var, fg='#00ff88', bg='#2b2b2b', font=('Arial', 10)).pack(pady=10)

        # 续建模式指示
        self.continue_var = tk.StringVar(value="")
        tk.Label(self.root, textvariable=self.continue_var, fg='#e07c24', bg='#2b2b2b', font=('Arial', 9)).pack()

        # 信息
        tk.Label(self.root, text="地图存储: ~/rtabmap_maps/<map_id>.db", fg='#888888', bg='#2b2b2b').pack()

    def refresh_maps(self):
        if not os.path.exists(self.maps_dir):
            os.makedirs(self.maps_dir)
        maps = []
        for f in glob.glob(os.path.join(self.maps_dir, "*.db")):
            name = os.path.basename(f).replace(".db", "")
            size = os.path.getsize(f) / (1024 * 1024)
            maps.append(f"{name} ({size:.1f}MB)")
        default = os.path.expanduser("~/rtabmap.db")
        if os.path.exists(default):
            size = os.path.getsize(default) / (1024 * 1024)
            maps.append(f"default ({size:.1f}MB)")
        self.map_combo['values'] = sorted(maps, reverse=True)
        if maps:
            self.map_combo.set(maps[0])

    def get_map_name(self):
        s = self.map_combo.get()
        return s.split(" (")[0] if s else None

    def get_db_path(self, name=None):
        if name is None:
            name = self.get_map_name()
        if not name:
            return None
        if name == "default":
            return os.path.expanduser("~/rtabmap.db")
        return os.path.join(self.maps_dir, f"{name}.db")

    def new_map(self):
        map_id = self.map_id_entry.get().strip()
        if not map_id:
            messagebox.showerror("错误", "请输入地图ID")
            return
        db_path = self.get_db_path(map_id)
        if os.path.exists(db_path):
            if not messagebox.askyesno("地图已存在", f"地图 '{map_id}' 已存在，是否续建?"):
                return
        self.status_var.set(f"状态: 地图 '{map_id}' 已准备")

    def continue_map(self):
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return
        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return
        self.map_id_entry.delete(0, tk.END)
        self.map_id_entry.insert(0, name)
        self.is_continue = True
        self.continue_var.set("🔄 续建模式: 将加载已有地图数据继续建图")
        self.status_var.set(f"状态: 续建 '{name}'")
        logger.info(f"设置续建模式: {name}, 数据库: {db_path}")

    def delete_map(self):
        name = self.get_map_name()
        if not name:
            return
        if name == "default":
            messagebox.showerror("错误", "不能删除默认地图")
            return
        # 校验地图名称
        valid, msg = validate_map_id(name)
        if not valid:
            messagebox.showerror("错误", msg)
            return
        if not messagebox.askyesno("确认", f"删除地图 '{name}'?"):
            return
        db_path = self.get_db_path(name)
        if os.path.exists(db_path):
            # C5 安全修复：移动到回收站而非直接删除
            os.makedirs(TRASH_DIR, exist_ok=True)
            trash_path = os.path.join(TRASH_DIR, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            try:
                shutil.move(db_path, trash_path)
                logger.info(f"地图已移至回收站: {name} -> {trash_path}")
            except Exception as e:
                logger.error(f"移动地图到回收站失败: {e}")
                messagebox.showerror("错误", f"删除失败: {str(e)}")
                return
        self.refresh_maps()
        self.status_var.set(f"状态: 已移至回收站 '{name}'")

    def start_mapping(self):
        """开始建图"""
        # 先检查设备
        if not self.check_device_before_launch():
            return

        try:
            map_id = self.map_id_entry.get().strip()
            if not map_id:
                messagebox.showerror("错误", "请输入地图ID")
                return
            # C2 安全修复：校验地图ID，防止命令注入
            valid, msg = validate_map_id(map_id)
            if not valid:
                messagebox.showerror("错误", msg)
                return
            db_path = self.get_db_path(map_id)
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            project_root = self.app_config['paths']['project_root']
            config_dir = self.app_config['paths']['config_dir']
            config_path = os.path.join(config_dir, 'rtabmap_custom.ini')

            launch_file = f"{project_root}/factor_perception_auto.launch.py"

            # 判断是否为续建模式
            if self.is_continue and os.path.exists(db_path):
                # 续建：加载已有地图数据继续建图
                cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
                       f'localization:=false rtabmap_viz:=true database_path:={db_path} '
                       f'key:={camera_key} config_path:={config_path} continue_mapping:=true']
                self.status_var.set(f"状态: 续建模式 | {map_id} (加载已有地图)")
                logger.info(f"启动续建模式: {map_id}, 数据库: {db_path}")
            else:
                # 新建图
                cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
                       f'localization:=false rtabmap_viz:=true database_path:={db_path} '
                       f'key:={camera_key} config_path:={config_path}']
                self.status_var.set(f"状态: 建图模式 | {map_id}")
                logger.info(f"启动建图模式: {map_id}, 数据库: {db_path}")

            subprocess.Popen(cmd, shell=False)
            # 重置续建标记
            self.is_continue = False
            self.continue_var.set("")
        except Exception as e:
            logger.error(f"启动建图失败: {e}")
            messagebox.showerror("错误", f"启动建图失败: {str(e)}")

    def start_navigation(self):
        """开始导航"""
        # 先检查设备
        if not self.check_device_before_launch():
            return

        try:
            name = self.get_map_name()
            if not name:
                messagebox.showerror("错误", "请选择地图")
                return
            # C2 安全修复：校验地图名称
            valid, msg = validate_map_id(name)
            if not valid:
                messagebox.showerror("错误", msg)
                return
            db_path = self.get_db_path(name)
            if not db_path:
                messagebox.showerror("错误", "无法获取地图路径")
                return
            if not os.path.exists(db_path):
                messagebox.showerror("错误", f"地图文件不存在: {db_path}")
                return
            self.status_var.set(f"状态: 启动导航 {name}...")
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            project_root = self.app_config['paths']['project_root']
            config_path = os.path.join(self.app_config['paths']['config_dir'], 'rtabmap_custom.ini')
            launch_file = f"{project_root}/factor_perception_auto.launch.py"
            cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
                   f'localization:=true rtabmap_viz:=true database_path:={db_path} '
                   f'key:={camera_key} config_path:={config_path}']
            subprocess.Popen(cmd, shell=False)
            self.status_var.set(f"状态: 导航模式 | {name}")
            logger.info(f"启动导航模式: {name}, 数据库: {db_path}")
        except Exception as e:
            logger.error(f"启动导航失败: {e}")
            messagebox.showerror("错误", f"启动导航失败: {str(e)}")

    def start_full_nav(self):
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return
        # C2 安全修复：校验地图名称
        valid, msg = validate_map_id(name)
        if not valid:
            messagebox.showerror("错误", msg)
            return
        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", "地图不存在")
            return
        ros_setup = self.app_config['ros']['setup_path']
        camera_key = self.app_config['camera']['key']
        project_root = self.app_config['paths']['project_root']
        config_dir = self.app_config['paths']['config_dir']
        config_path = os.path.join(config_dir, 'rtabmap_custom.ini')
        nav2_params = os.path.join(config_dir, 'nav2_params.yaml')
        launch_file = f"{project_root}/launch/nav24r_full.launch.py"
        cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
               f'database_path:={db_path} key:={camera_key} '
               f'config_path:={config_path} nav2_params_file:={nav2_params}']
        subprocess.Popen(cmd, shell=False)
        self.status_var.set(f"状态: 完整导航 | {name}")

    def launch_rviz(self):
        """启动 RViz（顶视角配置）"""
        ros_setup = self.app_config['ros']['setup_path']
        config_dir = self.app_config['paths']['config_dir']
        subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/mapping.rviz'],
                         shell=False, start_new_session=True)
        self.status_var.set("状态: RViz 已启动（顶视角）")

    def launch_rviz_3d(self):
        """启动 RViz（3D 视角配置）"""
        ros_setup = self.app_config['ros']['setup_path']
        config_dir = self.app_config['paths']['config_dir']
        subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/mapping_3d.rviz'],
                         shell=False, start_new_session=True)
        self.status_var.set("状态: RViz 3D 已启动（多视角）")

    def launch_map_viewer(self):
        """启动地图观察器（专门用于查看已建好的地图）"""
        ros_setup = self.app_config['ros']['setup_path']
        config_dir = self.app_config['paths']['config_dir']
        subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/map_viewer_3d.rviz'],
                         shell=False, start_new_session=True)
        self.status_var.set("状态: 地图观察器已启动（3D 查看器）")

    def view_map_only(self):
        """查看已保存的地图（仅加载地图数据，不启动建图）"""
        try:
            name = self.get_map_name()
            if not name:
                messagebox.showerror("错误", "请选择地图")
                return

            db_path = self.get_db_path(name)
            if not os.path.exists(db_path):
                messagebox.showerror("错误", f"地图文件不存在: {db_path}")
                return

            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']

            # 启动 RTAB-Map 定位模式（只读地图）
            cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch factor_perception factor_perception_launch.py localization:=true database_path:={db_path} key:={camera_key}']
            subprocess.Popen(cmd, shell=False)

            # 等待 2 秒后启动 RViz 观察器
            time.sleep(2)

            # 启动地图观察器
            config_dir = self.app_config['paths']['config_dir']
            subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/map_viewer_3d.rviz'], shell=False)

            self.status_var.set(f"状态: 正在查看地图 '{name}'")
            logger.info(f"查看地图: {name}")
        except Exception as e:
            logger.error(f"查看地图失败: {e}")
            messagebox.showerror("错误", f"查看地图失败: {str(e)}")

    def analyze_map_quality(self):
        """解读地图质量，显示详细分析报告"""
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return

        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return

        self.status_var.set(f"状态: 正在分析地图 '{name}'...")

        # 运行分析脚本
        result = subprocess.run(
            ['python3', os.path.join(self.app_config['paths']['scripts_dir'], 'analyze_map_quality.py'), db_path],
            capture_output=True,
            text=True
        )

        # 创建新窗口显示分析结果
        report_window = tk.Toplevel(self.root)
        report_window.title(f"地图质量分析报告 - {name}")
        report_window.geometry("700x600")

        # 创建文本框
        text_frame = tk.Frame(report_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                             font=('Consolas', 10), bg='#2b2b2b', fg='#00ff88')
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # 插入分析结果
        text_widget.insert(tk.END, result.stdout)

        # 添加按钮
        btn_frame = tk.Frame(report_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(btn_frame, text="📋 复制报告", command=lambda: self.copy_report(result.stdout),
                 bg='#3d5a80', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📁 打开数据库查看器", command=lambda: self.view_database(),
                 bg='#4a7c59', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="关闭", command=report_window.destroy,
                 bg='#e63946', fg='white', width=15).pack(side=tk.RIGHT, padx=5)

        self.status_var.set(f"状态: 地图质量分析完成 - '{name}'")

    def copy_report(self, report_text):
        """复制报告到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(report_text)
        messagebox.showinfo("成功", "报告已复制到剪贴板")

    def export_octomap(self):
        """导出 Octomap 地图，带进度显示"""
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return

        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return

        # 选择分辨率
        resolution_window = tk.Toplevel(self.root)
        resolution_window.title("选择 Octomap 分辨率")
        resolution_window.geometry("300x200")

        tk.Label(resolution_window, text="选择导出分辨率:", font=('Arial', 12, 'bold')).pack(pady=10)

        resolution_var = tk.StringVar(value="0.02")
        resolutions = [
            ("0.01m - 超高精度（工业应用）", "0.01"),
            ("0.02m - 高精度（推荐人形机器人）⭐", "0.02"),
            ("0.05m - 标准精度（通用导航）", "0.05"),
            ("0.10m - 低精度（快速规划）", "0.10"),
        ]

        for text, value in resolutions:
            rb = tk.Radiobutton(resolution_window, text=text, variable=resolution_var, value=value)
            rb.pack(anchor=tk.W, padx=20)

        def start_export():
            resolution = float(resolution_var.get())
            resolution_window.destroy()
            self._do_export_octomap(db_path, name, resolution)

        tk.Button(resolution_window, text="开始导出", command=start_export, bg='#16a085', fg='white', width=15).pack(pady=20)

    def _do_export_octomap(self, db_path, name, resolution):
        """导出 Octomap - 使用 Database Viewer（最可靠方法）"""

        # 创建导出指导窗口
        guide_window = tk.Toplevel(self.root)
        guide_window.title(f"导出 Octomap 指导 - {name}")
        guide_window.geometry("600x500")

        # 标题
        tk.Label(guide_window, text="导出 Octomap 最佳方法",
                font=('Arial', 14, 'bold'), fg='#2ecc71').pack(pady=15)

        # 信息显示
        info_frame = tk.Frame(guide_window)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(info_frame, text=f"数据库: {name}", font=('Arial', 10)).pack()
        tk.Label(info_frame, text=f"分辨率: {resolution}m", font=('Arial', 10)).pack()
        tk.Label(info_frame, text=f"文件大小: {os.path.getsize(db_path)/(1024*1024):.1f} MB", font=('Arial', 10)).pack()

        # 分隔线
        ttk.Separator(guide_window, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)

        # 步骤说明
        steps_frame = tk.Frame(guide_window)
        steps_frame.pack(fill=tk.BOTH, padx=20, pady=10)

        tk.Label(steps_frame, text="导出步骤:",
                font=('Arial', 12, 'bold')).pack(anchor=tk.W)

        steps_text = """
步骤 1: 点击下方按钮启动 Database Viewer

步骤 2: 在 Database Viewer 中操作:
       File → Export 3D clouds...

步骤 3: 在弹出窗口中:
       ✓ 选择 "Export Octomap"
       ✓ 设置分辨率: {resolution}m
       ✓ 点击 "Export"

步骤 4: 保存文件:
       推荐位置: ~/rtabmap_maps/{name}_octomap_{resolution}m.bt
        """.format(resolution=resolution, name=name)

        tk.Label(steps_frame, text=steps_text, font=('Arial', 10),
                justify=tk.LEFT).pack(anchor=tk.W, pady=10)

        # 优势说明
        advantages_frame = tk.Frame(guide_window)
        advantages_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(advantages_frame, text="为什么使用 Database Viewer?",
                font=('Arial', 11, 'bold')).pack(anchor=tk.W)

        advantages = """
✅ 最可靠的导出方法（官方工具）
✅ 不需要启动 Factor Perception（节省时间）
✅ 不需要相机连接
✅ 可视化地图质量
✅ 支持多种导出格式
✅ 导出时间: 5-15秒（比之前快 3-6倍）
        """

        tk.Label(advantages_frame, text=advantages, font=('Arial', 10),
                fg='#27ae60', justify=tk.LEFT).pack(anchor=tk.W)

        # 按钮区
        btn_frame = tk.Frame(guide_window)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)

        # 启动 Database Viewer 按钮
        def launch_db_viewer():
            try:
                subprocess.Popen(['rtabmap-databaseViewer', db_path], shell=False, start_new_session=True)
                self.status_var.set(f"状态: Database Viewer 已启动 | {name}")
                logger.info(f"启动 Database Viewer: {db_path}")
                messagebox.showinfo("成功",
                    f"Database Viewer 已启动!\n\n"
                    f"请在 Database Viewer 中:\n"
                    f"1. File → Export 3D clouds\n"
                    f"2. 选择 Octomap, 分辨率 {resolution}m\n"
                    f"3. 点击 Export 保存")
            except Exception as e:
                error_msg = f"启动失败: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("错误", error_msg)

        tk.Button(btn_frame, text="🚀 启动 Database Viewer",
                 command=launch_db_viewer,
                 bg='#3498db', fg='white',
                 font=('Arial', 11, 'bold'),
                 width=20, height=2).pack(side=tk.LEFT, padx=10)

        # 复制命令按钮
        def copy_command():
            cmd = f"rtabmap-databaseViewer {db_path}"
            self.root.clipboard_clear()
            self.root.clipboard_append(cmd)
            messagebox.showinfo("已复制", f"命令已复制到剪贴板:\n{cmd}")

        tk.Button(btn_frame, text="📋 复制命令",
                 command=copy_command,
                 bg='#95a5a6', fg='white',
                 font=('Arial', 10),
                 width=15, height=2).pack(side=tk.LEFT, padx=10)

        # 关闭按钮
        tk.Button(btn_frame, text="关闭",
                 command=guide_window.destroy,
                 bg='#e74c3c', fg='white',
                 font=('Arial', 10),
                 width=15, height=2).pack(side=tk.RIGHT, padx=10)

        # 底部提示
        tk.Label(guide_window,
                text="提示: 导出的 Octomap 可直接用于 Nav2 导航",
                font=('Arial', 9), fg='#7f8c8d').pack(pady=10)

    def view_database(self):
        """打开 RTAB-Map Database Viewer 查看地图数据库"""
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return

        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return

        try:
            # 使用 subprocess.Popen 启动，不等待完成
            subprocess.Popen(['rtabmap-databaseViewer', db_path], shell=False, start_new_session=True)
            self.status_var.set(f"状态: Database Viewer 已启动 | {name}")
            logger.info(f"启动 Database Viewer: {db_path}")
        except Exception as e:
            error_msg = f"启动 Database Viewer 失败: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("错误", error_msg)

    def stop_all(self):
        """停止所有 ROS2 进程和 RTAB-Map 相关窗口"""
        # 停止 ROS2 launch 进程
        subprocess.run(['pkill', '-f', 'ros2 launch'], stderr=subprocess.DEVNULL)

        # 停止 RViz
        subprocess.run(['pkill', '-f', 'rviz2'], stderr=subprocess.DEVNULL)

        # 停止 RTAB-Map 相关进程和窗口
        subprocess.run(['pkill', '-f', 'rtabmap'], stderr=subprocess.DEVNULL)  # RTAB-Map 核心进程
        subprocess.run(['pkill', '-f', 'rtabmap-databaseViewer'], stderr=subprocess.DEVNULL)  # 数据库查看器
        subprocess.run(['pkill', '-f', 'rtabmap_viz'], stderr=subprocess.DEVNULL)  # 可视化节点

        # 停止 Factor Perception 容器
        subprocess.run(['pkill', '-f', 'component_container'], stderr=subprocess.DEVNULL)

        # 停止 robot_state_publisher
        subprocess.run(['pkill', '-f', 'robot_state_publisher'], stderr=subprocess.DEVNULL)

        # 清理可能的僵尸进程
        subprocess.run(['pkill', '-9', '-f', 'factor_perception'], stderr=subprocess.DEVNULL)

        self.status_var.set("状态: 已停止所有进程")

    # ==================== 设备检测功能 ====================

    def check_oak_device(self):
        """检测 OAK-D 设备是否连接"""
        try:
            # 方法1: 通过 lsusb 检测
            result = subprocess.run(
                ['lsusb'],
                capture_output=True, text=True, timeout=5
            )
            usb_devices = result.stdout

            # OAK-D 设备可能的 vendor ID
            oak_ids = ['03e7', '1443', '2e1d', 'luxonis']

            for oak_id in oak_ids:
                if oak_id.lower() in usb_devices.lower():
                    # 尝试获取设备详细信息
                    try:
                        detail_result = subprocess.run(
                            ['lsusb', '-d', f'{oak_id}:'],
                            capture_output=True, text=True, timeout=3
                        )
                        lines = detail_result.stdout.strip().split('\n')
                        device_info = ""
                        for line in lines:
                            if 'ID' in line:
                                parts = line.split('ID')
                                if len(parts) > 1:
                                    device_info = parts[1].strip()
                                    break
                        return True, device_info if device_info else "OAK-D 设备"
                    except:
                        return True, "OAK-D 设备"

            # 方法2: 检查 /dev 目录
            import glob as g
            video_devices = g.glob('/dev/video*')
            if video_devices:
                # 有视频设备，但需要进一步确认是否是 OAK-D
                # 这只是备用检测方法
                pass

            return False, ""

        except subprocess.TimeoutExpired:
            logger.error("设备检测超时")
            return False, "检测超时"
        except Exception as e:
            logger.error(f"设备检测失败: {e}")
            return False, f"检测失败: {str(e)}"

    def update_device_status(self):
        """更新设备状态显示"""
        connected, info = self.check_oak_device()
        self.device_connected = connected

        if connected:
            self.device_status_var.set("✅ 设备已连接")
            self.device_status_label.config(fg='#00ff88')
            self.device_info_var.set(info)
        else:
            self.device_status_var.set("❌ 设备未连接")
            self.device_status_label.config(fg='#e63946')
            self.device_info_var.set("请连接 OAK-D 相机")

    def start_device_monitor(self):
        """启动设备监控线程"""
        def monitor():
            while self.auto_check_enabled:
                try:
                    self.root.after(0, self.update_device_status)
                    time.sleep(3)  # 每3秒检测一次
                except Exception as e:
                    logger.error(f"设备监控异常: {e}")
                    break

        self.device_check_thread = threading.Thread(target=monitor, daemon=True)
        self.device_check_thread.start()
        logger.info("设备监控已启动")

    def check_device_now(self):
        """立即检测设备"""
        self.device_status_var.set("⏳ 正在检测设备...")
        self.root.update()
        self.update_device_status()

        if self.device_connected:
            messagebox.showinfo("设备检测", "✅ OAK-D 设备已连接\n可以正常启动系统")
        else:
            messagebox.showwarning("设备检测",
                "❌ 未检测到 OAK-D 设备\n\n"
                "请检查:\n"
                "1. 相机 USB 线是否连接\n"
                "2. USB 线是否插紧（建议 USB 3.0）\n"
                "3. 相机电源是否正常\n\n"
                "连接后点击 '重启相机' 或 '强制重连'")

    def toggle_auto_check(self):
        """切换自动检测"""
        self.auto_check_enabled = self.auto_check_var.get()
        if self.auto_check_enabled:
            logger.info("已启用自动设备检测")
            if not self.device_check_thread or not self.device_check_thread.is_alive():
                self.start_device_monitor()
        else:
            logger.info("已禁用自动设备检测")

    def restart_camera(self):
        """重启相机（软重启）"""
        if not self.device_connected:
            # 尝试重新检测
            self.check_device_now()
            if not self.device_connected:
                messagebox.showwarning("重启失败",
                    "设备未连接，无法重启\n\n"
                    "请先连接 OAK-D 相机")
                return

        self.status_var.set("状态: 正在重启相机...")
        self.device_status_var.set("⏳ 正在重启相机...")
        self.root.update()

        try:
            # 重置 USB 设备（软重启）
            # 查找 OAK-D 设备的 USB 路径
            result = subprocess.run(
                ['bash', '-c', "lsusb | grep -iE '03e7|1443|luxonis' | head -1"],
                shell=False, capture_output=True, text=True, timeout=5
            )

            if result.stdout:
                # 找到设备，尝试重置
                logger.info("尝试软重启 OAK-D 设备")

                # 重置 USB 端口
                reset_cmd = """
for dev in /sys/bus/usb/devices/*; do
    if [ -f "$dev/idVendor" ] && [ -f "$dev/idProduct" ]; then
        vendor=$(cat "$dev/idVendor" 2>/dev/null)
        if echo "$vendor" | grep -qiE "03e7|1443"; then
            echo "$dev" | xargs -I{} sh -c 'echo {} > /sys/bus/usb/drivers/usb/unbind 2>/dev/null; echo {} > /sys/bus/usb/drivers/usb/bind 2>/dev/null' &
        fi
    fi
done
"""
                subprocess.run(['bash', '-c', reset_cmd], shell=False, timeout=10)

                # 等待设备重新枚举
                time.sleep(2)

                # 重新检测
                self.update_device_status()

                if self.device_connected:
                    self.status_var.set("状态: 相机重启成功")
                    messagebox.showinfo("成功", "✅ 相机重启成功！")
                    logger.info("相机重启成功")
                else:
                    self.status_var.set("状态: 相机重启失败")
                    messagebox.showwarning("重启失败",
                        "软重启失败，请尝试:\n"
                        "1. 点击 '强制重连'\n"
                        "2. 或物理重新插拔 USB 线")
            else:
                messagebox.showwarning("重启失败", "无法找到 OAK-D 设备")

        except Exception as e:
            logger.error(f"重启相机失败: {e}")
            messagebox.showerror("错误", f"重启相机失败:\n{str(e)}")
            self.status_var.set("状态: 重启失败")

    def force_reconnect(self):
        """强制重连相机（停止所有进程后重新连接）"""
        # 确认操作
        if not messagebox.askyesno("强制重连",
            "这将停止所有运行中的 ROS2 进程，然后尝试重新连接相机。\n\n"
            "确定要继续吗？"):
            return

        self.status_var.set("状态: 正在强制重连相机...")
        self.device_status_var.set("⏳ 正在强制重连...")
        self.root.update()

        try:
            # 步骤1: 停止所有相关进程
            logger.info("停止所有 ROS2 进程...")
            self.stop_all()
            time.sleep(2)

            # 步骤2: 重置 USB
            logger.info("重置 USB 设备...")
            reset_cmd = """
for dev in /sys/bus/usb/devices/*; do
    if [ -f "$dev/idVendor" ]; then
        vendor=$(cat "$dev/idVendor" 2>/dev/null)
        if echo "$vendor" | grep -qiE "03e7|1443|2e1d"; then
            echo "Resetting: $dev"
            echo "$dev" | xargs -I{} sh -c 'echo {} > /sys/bus/usb/drivers/usb/unbind 2>/dev/null'
            sleep 1
            echo "$dev" | xargs -I{} sh -c 'echo {} > /sys/bus/usb/drivers/usb/bind 2>/dev/null'
        fi
    fi
done
"""
            subprocess.run(['bash', '-c', reset_cmd], shell=False, timeout=15)

            # 步骤3: 等待设备重新枚举
            time.sleep(3)

            # 步骤4: 重新检测设备
            self.update_device_status()

            if self.device_connected:
                self.status_var.set("状态: 强制重连成功")
                messagebox.showinfo("成功",
                    "✅ 相机强制重连成功！\n\n"
                    "设备已重新识别，可以启动系统")
                logger.info("强制重连成功")
            else:
                self.status_var.set("状态: 设备仍未连接")
                messagebox.showwarning("重连失败",
                    "❌ 相机仍未检测到\n\n"
                    "请尝试:\n"
                    "1. 物理重新插拔 USB 线\n"
                    "2. 检查 USB 线是否损坏\n"
                    "3. 尝试不同的 USB 端口")

        except Exception as e:
            logger.error(f"强制重连失败: {e}")
            messagebox.showerror("错误", f"强制重连失败:\n{str(e)}")
            self.status_var.set("状态: 重连失败")

    def check_device_before_launch(self):
        """启动前检查设备状态"""
        self.update_device_status()

        if not self.device_connected:
            result = messagebox.askyesno(
                "设备未连接",
                "⚠️ 未检测到 OAK-D 设备！\n\n"
                "启动 Factor Perception 需要连接相机。\n"
                "如果相机已连接，可能被其他程序占用或驱动异常。\n\n"
                "是否尝试强制重连？\n"
                "(将停止所有 ROS2 进程并重置设备)"
            )
            if result:
                self.force_reconnect()
                # 再次检测
                self.update_device_status()
                return self.device_connected
            return False

        return True

if __name__ == "__main__":
    root = tk.Tk()
    app = FactorControlPanel(root)
    root.mainloop()
