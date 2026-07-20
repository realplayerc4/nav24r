#!/usr/bin/env python3
"""
Factor Perception 控制面板（简化版）
只使用默认数据库 ~/rtabmap.db，支持建图/续建/导航
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import logging
import yaml
import threading
import time

LOG_DIR = os.path.expanduser("~/.local/share/nav24r/logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(LOG_DIR, 'factor_control_panel.log')
)
logger = logging.getLogger(__name__)

DEFAULT_DB = os.path.expanduser("~/rtabmap.db")


class FactorControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Factor Perception 控制面板")
        self.root.geometry("650x620")

        self.load_app_config()

        self.device_connected = False
        self.device_check_thread = None
        self.auto_check_enabled = True
        self.ros_running = False
        self.ros_mode = None
        self.ros_buttons = []
        self.independent_buttons = []

        self.create_ui()
        self.start_device_monitor()
        self.update_db_size()

    def load_app_config(self):
        _script_dir = os.path.dirname(os.path.abspath(__file__))
        _project_root = os.path.dirname(_script_dir)
        config_path = os.path.join(_project_root, "config", "factor_perception_config.yaml")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.app_config = yaml.safe_load(f)
                if 'paths' not in self.app_config:
                    self.app_config['paths'] = {}
                self.app_config['paths']['project_root'] = _project_root
                self.app_config['paths']['config_dir'] = os.path.join(_project_root, 'config')
                self.app_config['paths']['scripts_dir'] = _script_dir
                logger.info(f"配置文件加载成功: {config_path}")
            else:
                self.app_config = {
                    'camera': {'key': os.environ.get('FACTOR_PERCEPTION_KEY', '')},
                    'ros': {'distro': 'jazzy', 'setup_path': '/opt/ros/jazzy/setup.bash'},
                    'paths': {
                        'project_root': _project_root,
                        'config_dir': os.path.join(_project_root, 'config'),
                        'scripts_dir': _script_dir,
                    }
                }
                logger.warning("配置文件不存在，使用默认配置")
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

    def create_ui(self):
        tk.Label(self.root, text="Factor Perception 控制面板",
                font=('Arial', 16, 'bold'), fg='#00ff88', bg='#2b2b2b').pack(pady=10)
        self.root.configure(bg='#2b2b2b')

        device_frame = tk.LabelFrame(self.root, text="📷 OAK-D 设备状态", font=('Arial', 11), padx=10, pady=10)
        device_frame.pack(fill=tk.X, padx=20, pady=5)

        status_row = tk.Frame(device_frame)
        status_row.pack(fill=tk.X, pady=3)

        self.device_status_var = tk.StringVar(value="⏳ 正在检测设备...")
        self.device_status_label = tk.Label(status_row, textvariable=self.device_status_var,
                                            font=('Arial', 10, 'bold'), fg='#ffaa00')
        self.device_status_label.pack(side=tk.LEFT)

        self.device_info_var = tk.StringVar(value="")
        tk.Label(status_row, textvariable=self.device_info_var, font=('Arial', 9), fg='#888888').pack(side=tk.LEFT, padx=10)

        self.usb_speed_var = tk.StringVar(value="")
        self.usb_speed_label = tk.Label(status_row, textvariable=self.usb_speed_var,
                                        font=('Arial', 9, 'bold'), fg='#00ff88')
        self.usb_speed_label.pack(side=tk.RIGHT)

        device_btn_row = tk.Frame(device_frame)
        device_btn_row.pack(fill=tk.X, pady=5)

        tk.Button(device_btn_row, text="🔍 检测设备", width=12, height=1,
                 command=self.check_device_now, bg='#3d5a80', fg='white').pack(side=tk.LEFT, padx=3)
        tk.Button(device_btn_row, text="🔄 重启相机", width=12, height=1,
                 command=self.restart_camera, bg='#e07c24', fg='white').pack(side=tk.LEFT, padx=3)
        tk.Button(device_btn_row, text="⚡ 强制重连", width=12, height=1,
                 command=self.force_reconnect, bg='#e63946', fg='white').pack(side=tk.LEFT, padx=3)

        self.auto_check_var = tk.BooleanVar(value=True)
        tk.Checkbutton(device_btn_row, text="自动检测", variable=self.auto_check_var,
                      command=self.toggle_auto_check, bg='#2b2b2b', fg='white',
                      selectcolor='#2b2b2b', activebackground='#2b2b2b').pack(side=tk.RIGHT, padx=5)

        db_info_frame = tk.LabelFrame(self.root, text="📦 默认数据库", font=('Arial', 11), padx=10, pady=5)
        db_info_frame.pack(fill=tk.X, padx=20, pady=5)

        db_row = tk.Frame(db_info_frame)
        db_row.pack(fill=tk.X, pady=2)
        tk.Label(db_row, text="路径:", font=('Arial', 9), fg='#888888', bg='#2b2b2b').pack(side=tk.LEFT)
        tk.Label(db_row, text=DEFAULT_DB, font=('Arial', 9), fg='#00ff88', bg='#2b2b2b').pack(side=tk.LEFT, padx=5)
        self.db_size_var = tk.StringVar(value="计算中...")
        tk.Label(db_row, textvariable=self.db_size_var, font=('Arial', 9, 'bold'), fg='#ffaa00', bg='#2b2b2b').pack(side=tk.RIGHT)

        btn_frame = tk.LabelFrame(self.root, text="功能", font=('Arial', 11), padx=10, pady=10)
        btn_frame.pack(fill=tk.X, padx=20, pady=5)

        btn_row1 = tk.Frame(btn_frame)
        btn_row1.pack(pady=5)
        self.btn_new_mapping = tk.Button(btn_row1, text="🗺️ 新建建图", width=14, height=2,
            command=self.start_new_mapping, bg='#2980b9', fg='white')
        self.btn_new_mapping.pack(side=tk.LEFT, padx=5)
        self.ros_buttons.append(self.btn_new_mapping)

        self.btn_continue = tk.Button(btn_row1, text="🔄 续建", width=14, height=2,
            command=self.start_continue_mapping, bg='#3d5a80', fg='white')
        self.btn_continue.pack(side=tk.LEFT, padx=5)
        self.ros_buttons.append(self.btn_continue)

        self.btn_nav = tk.Button(btn_row1, text="🧭 开始导航", width=14, height=2,
            command=self.start_navigation, bg='#3d5a80', fg='white')
        self.btn_nav.pack(side=tk.LEFT, padx=5)
        self.ros_buttons.append(self.btn_nav)

        btn_row2 = tk.Frame(btn_frame)
        btn_row2.pack(pady=5)
        self.btn_full_nav = tk.Button(btn_row2, text="🚀 完整导航", width=14, height=2,
            command=self.start_full_nav, bg='#3d5a80', fg='white')
        self.btn_full_nav.pack(side=tk.LEFT, padx=5)
        self.ros_buttons.append(self.btn_full_nav)

        self.btn_reset = tk.Button(btn_row2, text="🗑️ 重置地图", width=14, height=2,
            command=self.reset_map, bg='#c0392b', fg='white')
        self.btn_reset.pack(side=tk.LEFT, padx=5)

        self.btn_stop = tk.Button(btn_row2, text="⏹️ 停止", width=14, height=2,
            command=self.stop_all, bg='#e63946', fg='white')
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        btn_row3 = tk.Frame(btn_frame)
        btn_row3.pack(pady=5)
        tk.Button(btn_row3, text="📊 RViz", width=14, height=2, command=self.launch_rviz, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row3, text="📊 RViz 3D", width=14, height=2, command=self.launch_rviz_3d, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row3, text="🗺️ 地图观察", width=14, height=2, command=self.launch_map_viewer, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)

        btn_row4 = tk.Frame(btn_frame)
        btn_row4.pack(pady=5)
        self.btn_database = tk.Button(btn_row4, text="📁 数据库", width=14, height=2,
            command=self.view_database, bg='#4a7c59', fg='white')
        self.btn_database.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_row4, text="📊 地图质量", width=14, height=2, command=self.analyze_map_quality, bg='#e67e22', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row4, text="🗺️ 导出Octomap", width=14, height=2, command=self.export_octomap, bg='#16a085', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row4, text="☁️ 导出点云+RViz", width=14, height=2, command=self.export_cloud_and_view, bg='#16a085', fg='white').pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="状态: 就绪")
        tk.Label(self.root, textvariable=self.status_var, fg='#00ff88', bg='#2b2b2b', font=('Arial', 10)).pack(pady=5)

        tk.Label(self.root, text=f"💡 新建建图: 覆盖已有数据库 | 续建: 加载已有数据继续建图 | 重置地图: 删除数据库", fg='#888888', bg='#2b2b2b', font=('Arial', 8)).pack()

    def launch_rviz(self):
        ros_setup = self.app_config['ros']['setup_path']
        config_dir = self.app_config['paths']['config_dir']
        subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/mapping.rviz'],
                         shell=False, start_new_session=True)
        self.status_var.set("状态: RViz 已启动（顶视角）")

    def launch_rviz_3d(self):
        ros_setup = self.app_config['ros']['setup_path']
        config_dir = self.app_config['paths']['config_dir']
        subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/mapping_3d.rviz'],
                         shell=False, start_new_session=True)
        self.status_var.set("状态: RViz 3D 已启动（多视角）")

    def launch_map_viewer(self):
        ros_setup = self.app_config['ros']['setup_path']
        config_dir = self.app_config['paths']['config_dir']
        subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/map_viewer_3d.rviz'],
                         shell=False, start_new_session=True)
        self.status_var.set("状态: 地图观察器已启动（3D 查看器）")

    def _get_default_db(self):
        return DEFAULT_DB

    def set_ros_running(self, running, mode=None):
        self.ros_running = running
        self.ros_mode = mode
        state = tk.DISABLED if running else tk.NORMAL
        for btn in self.ros_buttons:
            btn.config(state=state)
        if running:
            self.status_var.set(f"状态: {mode}运行中...")
        else:
            self.status_var.set("状态: 就绪")

    def is_ros_running(self):
        return self.ros_running

    def start_new_mapping(self):
        if self.is_ros_running():
            messagebox.showwarning("系统运行中", "ROS2 系统正在运行，请先停止再切换模式")
            return
        if not self.check_device_before_launch():
            return
        try:
            db_path = self._get_default_db()
            if os.path.exists(db_path):
                if not messagebox.askyesno("确认覆盖", f"数据库已存在:\n{db_path}\n\n新建建图将覆盖现有数据，是否继续？"):
                    return
                os.remove(db_path)
                logger.info(f"删除已有数据库: {db_path}")
            self._launch_mapping(db_path, "新建建图")
            self.set_ros_running(True, "新建建图")
        except Exception as e:
            self.set_ros_running(False)
            logger.error(f"启动新建建图失败: {e}")
            messagebox.showerror("错误", f"启动新建建图失败: {str(e)}")

    def start_continue_mapping(self):
        if self.is_ros_running():
            messagebox.showwarning("系统运行中", "ROS2 系统正在运行，请先停止再切换模式")
            return
        if not self.check_device_before_launch():
            return
        try:
            db_path = self._get_default_db()
            if not os.path.exists(db_path):
                messagebox.showerror("错误", f"默认数据库不存在: {db_path}\n请先使用'新建建图'创建地图")
                return
            self._launch_mapping(db_path, "续建地图")
            self.set_ros_running(True, "续建地图")
        except Exception as e:
            self.set_ros_running(False)
            logger.error(f"启动续建失败: {e}")
            messagebox.showerror("错误", f"启动续建失败: {str(e)}")

    def _launch_mapping(self, db_path, mode_desc):
        try:
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            project_root = self.app_config['paths']['project_root']
            config_dir = self.app_config['paths']['config_dir']
            config_path = os.path.join(config_dir, 'rtabmap.ini')
            launch_file = os.path.join(project_root, "factor_perception_auto.launch.py")

            cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
                   f'localization:=false rtabmap_viz:=true database_path:={db_path} '
                   f'key:={camera_key} config_path:={config_path}']
            subprocess.Popen(cmd, shell=False)
            logger.info(f"启动{mode_desc}: {db_path}")
        except Exception as e:
            logger.error(f"启动{mode_desc}失败: {e}")
            messagebox.showerror("错误", f"启动{mode_desc}失败: {str(e)}")
            raise

    def update_db_size(self):
        db_path = self._get_default_db()
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            if size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 * 1024 * 1024:
                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
            self.db_size_var.set(f"大小: {size_str}")
        else:
            self.db_size_var.set("大小: 不存在")
        self.root.after(2000, self.update_db_size)

    def start_navigation(self):
        if self.is_ros_running():
            messagebox.showwarning("系统运行中", "ROS2 系统正在运行，请先停止再切换模式")
            return
        if not self.check_device_before_launch():
            return
        try:
            db_path = self._get_default_db()
            if not os.path.exists(db_path):
                messagebox.showerror("错误", f"默认数据库不存在: {db_path}\n请先建图")
                return
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            project_root = self.app_config['paths']['project_root']
            config_dir = self.app_config['paths']['config_dir']
            config_path = os.path.join(config_dir, 'rtabmap.ini')
            launch_file = os.path.join(project_root, "factor_perception_auto.launch.py")
            cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
                   f'localization:=true rtabmap_viz:=true database_path:={db_path} '
                   f'key:={camera_key} config_path:={config_path}']
            subprocess.Popen(cmd, shell=False)
            self.set_ros_running(True, "导航模式")
            logger.info(f"启动导航模式: {db_path}")
        except Exception as e:
            self.set_ros_running(False)
            logger.error(f"启动导航失败: {e}")
            messagebox.showerror("错误", f"启动导航失败: {str(e)}")

    def start_full_nav(self):
        if self.is_ros_running():
            messagebox.showwarning("系统运行中", "ROS2 系统正在运行，请先停止再切换模式")
            return
        try:
            db_path = self._get_default_db()
            if not os.path.exists(db_path):
                messagebox.showerror("错误", f"默认数据库不存在: {db_path}\n请先建图")
                return
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            project_root = self.app_config['paths']['project_root']
            config_dir = self.app_config['paths']['config_dir']
            config_path = os.path.join(config_dir, 'rtabmap.ini')
            nav2_params = os.path.join(config_dir, 'nav2_params.yaml')
            launch_file = os.path.join(project_root, "launch", "nav24r_full.launch.py")
            cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} '
                   f'database_path:={db_path} key:={camera_key} '
                   f'config_path:={config_path} nav2_params_file:={nav2_params}']
            subprocess.Popen(cmd, shell=False)
            self.set_ros_running(True, "完整导航")
            logger.info(f"启动完整导航: {db_path}")
        except Exception as e:
            self.set_ros_running(False)
            logger.error(f"启动完整导航失败: {e}")
            messagebox.showerror("错误", f"启动完整导航失败: {str(e)}")

    def reset_map(self):
        if self.is_ros_running():
            messagebox.showwarning("系统运行中", "ROS2 系统正在运行，请先停止再重置地图")
            return
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showinfo("提示", f"数据库不存在:\n{db_path}\n\n无需重置")
            return
        if not messagebox.askyesno("确认重置", f"将删除数据库:\n{db_path}\n\n此操作不可恢复，是否继续？"):
            return
        try:
            os.remove(db_path)
            logger.info(f"重置地图: 删除数据库 {db_path}")
            messagebox.showinfo("成功", "✅ 地图已重置\n\n数据库已删除，请使用'新建建图'开始")
            self.status_var.set("状态: 地图已重置")
            self.update_db_size()
        except Exception as e:
            logger.error(f"重置地图失败: {e}")
            messagebox.showerror("错误", f"重置地图失败: {str(e)}")

    def view_map_only(self):
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"默认数据库不存在: {db_path}")
            return
        try:
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            launch_file = os.path.join(self.app_config['paths']['project_root'], "factor_perception_auto.launch.py")
            cmd = ['bash', '-c', f'source {ros_setup} && ros2 launch {launch_file} localization:=true database_path:={db_path} key:={camera_key}']
            subprocess.Popen(cmd, shell=False)
            time.sleep(2)
            config_dir = self.app_config['paths']['config_dir']
            subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/map_viewer_3d.rviz'], shell=False)
            self.status_var.set(f"状态: 正在查看地图")
        except Exception as e:
            logger.error(f"查看地图失败: {e}")
            messagebox.showerror("错误", f"查看地图失败: {str(e)}")

    def analyze_map_quality(self):
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"默认数据库不存在: {db_path}")
            return
        self.status_var.set(f"状态: 正在分析地图...")
        result = subprocess.run(
            ['python3', os.path.join(self.app_config['paths']['scripts_dir'], 'analyze_map_quality.py'), db_path],
            capture_output=True, text=True
        )
        report_window = tk.Toplevel(self.root)
        report_window.title("地图质量分析报告")
        report_window.geometry("700x600")
        text_frame = tk.Frame(report_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                             font=('Consolas', 10), bg='#2b2b2b', fg='#00ff88')
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert(tk.END, result.stdout)
        btn_frame = tk.Frame(report_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(btn_frame, text="📋 复制报告", command=lambda: self.copy_report(result.stdout),
                 bg='#3d5a80', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📁 打开数据库查看器", command=lambda: self.view_database(),
                 bg='#4a7c59', fg='white', width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="关闭", command=report_window.destroy,
                 bg='#e63946', fg='white', width=15).pack(side=tk.RIGHT, padx=5)
        self.status_var.set("状态: 地图质量分析完成")

    def copy_report(self, report_text):
        self.root.clipboard_clear()
        self.root.clipboard_append(report_text)
        messagebox.showinfo("成功", "报告已复制到剪贴板")

    def export_octomap(self):
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"默认数据库不存在: {db_path}")
            return
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
            self._do_export_octomap(db_path, resolution)
        tk.Button(resolution_window, text="开始导出", command=start_export, bg='#16a085', fg='white', width=15).pack(pady=20)

    def _do_export_octomap(self, db_path, resolution):
        guide_window = tk.Toplevel(self.root)
        guide_window.title("导出 Octomap 指导")
        guide_window.geometry("600x500")
        tk.Label(guide_window, text="导出 Octomap 最佳方法",
                font=('Arial', 14, 'bold'), fg='#2ecc71').pack(pady=15)
        info_frame = tk.Frame(guide_window)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(info_frame, text=f"数据库: {DEFAULT_DB}", font=('Arial', 10)).pack()
        tk.Label(info_frame, text=f"分辨率: {resolution}m", font=('Arial', 10)).pack()
        tk.Label(info_frame, text=f"文件大小: {os.path.getsize(db_path)/(1024*1024):.1f} MB", font=('Arial', 10)).pack()
        ttk.Separator(guide_window, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        steps_frame = tk.Frame(guide_window)
        steps_frame.pack(fill=tk.BOTH, padx=20, pady=10)
        tk.Label(steps_frame, text="导出步骤:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        steps_text = f"""
步骤 1: 点击下方按钮启动 Database Viewer

步骤 2: 在 Database Viewer 中操作:
       File → Export 3D clouds...

步骤 3: 在弹出窗口中:
       ✓ 选择 "Export Octomap"
       ✓ 设置分辨率: {resolution}m
       ✓ 点击 "Export"

步骤 4: 保存文件:
        推荐位置: ~/rtabmap_maps/octomap_{resolution}m.bt
        """
        tk.Label(steps_frame, text=steps_text, font=('Arial', 10), justify=tk.LEFT).pack(anchor=tk.W, pady=10)
        advantages_frame = tk.Frame(guide_window)
        advantages_frame.pack(fill=tk.X, padx=20, pady=10)
        tk.Label(advantages_frame, text="为什么使用 Database Viewer?", font=('Arial', 11, 'bold')).pack(anchor=tk.W)
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
        btn_frame = tk.Frame(guide_window)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)
        def launch_db_viewer():
            try:
                ros_setup = self.app_config['ros']['setup_path']
                subprocess.Popen(['bash', '-c', f'source {ros_setup} && rtabmap-databaseViewer {db_path}'],
                                 shell=False, start_new_session=True)
                self.status_var.set(f"状态: Database Viewer 已启动")
                logger.info(f"启动 Database Viewer: {db_path}")
                messagebox.showinfo("成功",
                    f"Database Viewer 已启动!\n\n"
                    f"请在 Database Viewer 中:\n"
                    f"1. File → Export 3D clouds\n"
                    f"2. 选择 Octomap, 分辨率 {resolution}m\n"
                    f"3. 点击 Export 保存")
            except FileNotFoundError:
                error_msg = f"找不到 rtabmap-databaseViewer\n请确保 ROS2 环境已加载\nsource {self.app_config['ros']['setup_path']}"
                logger.error(error_msg)
                messagebox.showerror("错误", error_msg)
            except Exception as e:
                error_msg = f"启动失败: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("错误", error_msg)
        tk.Button(btn_frame, text="🚀 启动 Database Viewer",
                 command=launch_db_viewer,
                 bg='#3498db', fg='white',
                 font=('Arial', 11, 'bold'),
                 width=20, height=2).pack(side=tk.LEFT, padx=10)
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
        tk.Button(btn_frame, text="关闭",
                 command=guide_window.destroy,
                 bg='#e74c3c', fg='white',
                 font=('Arial', 10),
                 width=15, height=2).pack(side=tk.RIGHT, padx=10)
        tk.Label(guide_window,
                text="提示: 导出的 Octomap 可直接用于 Nav2 导航",
                font=('Arial', 9), fg='#7f8c8d').pack(pady=10)

    def export_cloud_and_view(self):
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"默认数据库不存在: {db_path}")
            return
        if not messagebox.askyesno("确认导出", f"将导出数据库完整点云:\n{db_path}\n\n导出时间取决于数据库大小，是否继续？"):
            return
        self.status_var.set("状态: 正在导出点云...")
        self.root.update()

        ros_setup = self.app_config['ros']['setup_path']
        project_root = self.app_config['paths']['project_root']
        config_dir = self.app_config['paths']['config_dir']
        ply_path = "/home/yq/rtabmap_cloud.ply"

        export_cmd = f"bash -c 'source {ros_setup} && rtabmap-export --cloud --filter_floor 0.2 --filter_ceiling 1.4 {db_path}'"
        try:
            result = subprocess.run(export_cmd, shell=True, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            messagebox.showerror("导出超时", "点云导出超时，数据库可能过大")
            self.status_var.set("状态: 导出超时")
            return

        if result.returncode != 0 or not os.path.exists(ply_path):
            err_msg = result.stderr.strip() or result.stdout.strip() or "未知错误"
            messagebox.showerror("导出失败", f"点云导出失败:\n{err_msg}")
            self.status_var.set("状态: 导出失败")
            return

        ply_size_mb = os.path.getsize(ply_path) / (1024 * 1024)
        self.status_var.set(f"状态: 点云已导出 ({ply_size_mb:.1f}MB)，正在启动查看器...")
        self.root.update()

        try:
            subprocess.Popen(['bash', '-c', f'source {ros_setup} && python3 {project_root}/scripts/ply_to_pointcloud.py'],
                             shell=False, start_new_session=True)
            subprocess.Popen(['bash', '-c', f'source {ros_setup} && rviz2 -d {config_dir}/map_viewer_3d.rviz'],
                             shell=False, start_new_session=True)
            messagebox.showinfo("导出完成",
                f"点云已导出 ({ply_size_mb:.1f}MB)\n\n"
                f"RViz 已启动\n\n"
                f"请将 RViz 中点云话题改为:\n/rtabmap/historical_cloud")
            self.status_var.set("状态: 点云查看器已启动")
        except Exception as e:
            logger.error(f"启动查看器失败: {e}")
            messagebox.showerror("错误", f"启动查看器失败: {str(e)}")
            self.status_var.set("状态: 启动查看器失败")

    def view_database(self):
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showerror("错误", f"默认数据库不存在: {db_path}")
            return
        try:
            ros_setup = self.app_config['ros']['setup_path']
            subprocess.Popen(['bash', '-c', f'source {ros_setup} && rtabmap-databaseViewer {db_path}'],
                             shell=False, start_new_session=True)
            self.status_var.set(f"状态: Database Viewer 已启动")
            logger.info(f"启动 Database Viewer: {db_path}")
        except FileNotFoundError:
            error_msg = f"找不到 rtabmap-databaseViewer\n请确保 ROS2 环境已加载\nsource {self.app_config['ros']['setup_path']}"
            logger.error(error_msg)
            messagebox.showerror("错误", error_msg)
        except Exception as e:
            error_msg = f"启动 Database Viewer 失败: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("错误", error_msg)

    def stop_all(self):
        subprocess.run(['pkill', '-f', 'ros2 launch'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'rviz2'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'rtabmap'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'rtabmap-databaseViewer'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'rtabmap_viz'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'component_container'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-f', 'robot_state_publisher'], stderr=subprocess.DEVNULL)
        subprocess.run(['pkill', '-9', '-f', 'factor_perception'], stderr=subprocess.DEVNULL)
        self.set_ros_running(False)
        self.status_var.set("状态: 已停止所有进程")

    # ==================== 设备检测功能 ====================

    def check_oak_device(self):
        try:
            result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
            usb_devices = result.stdout
            oak_ids = ['03e7', '1443', '2e1d', 'luxonis']
            found = False
            device_info = ""
            usb_speed = ""

            for oak_id in oak_ids:
                if oak_id.lower() in usb_devices.lower():
                    found = True
                    try:
                        detail_result = subprocess.run(['lsusb', '-d', f'{oak_id}:'],
                                                       capture_output=True, text=True, timeout=3)
                        lines = detail_result.stdout.strip().split('\n')
                        for line in lines:
                            if 'ID' in line:
                                parts = line.split('ID')
                                if len(parts) > 1:
                                    device_info = parts[1].strip()
                                    break
                        if not device_info:
                            device_info = "OAK-D 设备"
                    except:
                        device_info = "OAK-D 设备"
                    break

            if found:
                try:
                    import glob as g
                    for dev in g.glob('/sys/bus/usb/devices/*'):
                        if os.path.exists(f"{dev}/idVendor") and os.path.exists(f"{dev}/speed"):
                            with open(f"{dev}/idVendor", 'r') as f:
                                vendor = f.read().strip().lower()
                            if vendor in ['03e7', '1443', '2e1d']:
                                with open(f"{dev}/speed", 'r') as f:
                                    speed_mbps = int(f.read().strip())
                                    if speed_mbps >= 20000:
                                        usb_speed = f"USB {speed_mbps/1000:.1f}Gbps"
                                    elif speed_mbps >= 5000:
                                        usb_speed = f"USB {speed_mbps/1000:.1f}Gbps"
                                    elif speed_mbps >= 1000:
                                        usb_speed = f"USB {speed_mbps/1000:.1f}Gbps"
                                    else:
                                        usb_speed = f"USB {speed_mbps:.0f}Mbps"
                                break
                except Exception as e:
                    logger.debug(f"获取 USB 速度失败: {e}")
                    usb_speed = ""

            if found:
                info = device_info
                if usb_speed:
                    info = f"{device_info} | {usb_speed}"
                return True, info, usb_speed

            return False, "", ""
        except subprocess.TimeoutExpired:
            logger.error("设备检测超时")
            return False, "检测超时", ""
        except Exception as e:
            logger.error(f"设备检测失败: {e}")
            return False, f"检测失败: {str(e)}", ""

    def update_device_status(self):
        connected, info, usb_speed = self.check_oak_device()
        self.device_connected = connected
        if connected:
            self.device_status_var.set("✅ 设备已连接")
            self.device_status_label.config(fg='#00ff88')
            self.device_info_var.set(info)
            if usb_speed:
                self.usb_speed_var.set(usb_speed)
                if "USB 3" in usb_speed:
                    self.usb_speed_label.config(fg='#00ff88')
                elif "USB 2.0" in usb_speed or "480Mbps" in usb_speed:
                    self.usb_speed_label.config(fg='#ffaa00')
                else:
                    self.usb_speed_label.config(fg='#ff6600')
            else:
                self.usb_speed_var.set("")
        else:
            self.device_status_var.set("❌ 设备未连接")
            self.device_status_label.config(fg='#e63946')
            self.device_info_var.set("请连接 OAK-D 相机")
            self.usb_speed_var.set("")

    def start_device_monitor(self):
        def monitor():
            while self.auto_check_enabled:
                try:
                    self.root.after(0, self.update_device_status)
                    time.sleep(3)
                except Exception as e:
                    logger.error(f"设备监控异常: {e}")
                    break
        self.device_check_thread = threading.Thread(target=monitor, daemon=True)
        self.device_check_thread.start()
        logger.info("设备监控已启动")

    def check_device_now(self):
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
        self.auto_check_enabled = self.auto_check_var.get()
        if self.auto_check_enabled:
            logger.info("已启用自动设备检测")
            if not self.device_check_thread or not self.device_check_thread.is_alive():
                self.start_device_monitor()
        else:
            logger.info("已禁用自动设备检测")

    def restart_camera(self):
        if not self.device_connected:
            self.check_device_now()
            if not self.device_connected:
                messagebox.showwarning("重启失败", "设备未连接，无法重启\n\n请先连接 OAK-D 相机")
                return
        self.status_var.set("状态: 正在重启相机...")
        self.device_status_var.set("⏳ 正在重启相机...")
        self.root.update()
        try:
            result = subprocess.run(['bash', '-c', "lsusb | grep -iE '03e7|1443|luxonis' | head -1"], shell=False, capture_output=True, text=True, timeout=5)
            if result.stdout:
                logger.info("尝试软重启 OAK-D 设备")
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
                time.sleep(2)
                self.update_device_status()
                if self.device_connected:
                    self.status_var.set("状态: 相机重启成功")
                    messagebox.showinfo("成功", "✅ 相机重启成功！")
                    logger.info("相机重启成功")
                else:
                    self.status_var.set("状态: 相机重启失败")
                    messagebox.showwarning("重启失败", "软重启失败，请尝试:\n1. 点击 '强制重连'\n2. 或物理重新插拔 USB 线")
            else:
                messagebox.showwarning("重启失败", "无法找到 OAK-D 设备")
        except Exception as e:
            logger.error(f"重启相机失败: {e}")
            messagebox.showerror("错误", f"重启相机失败:\n{str(e)}")
            self.status_var.set("状态: 重启失败")

    def force_reconnect(self):
        if not messagebox.askyesno("强制重连", "这将停止所有运行中的 ROS2 进程，然后尝试重新连接相机。\n\n确定要继续吗？"):
            return
        self.status_var.set("状态: 正在强制重连相机...")
        self.device_status_var.set("⏳ 正在强制重连...")
        self.root.update()
        try:
            logger.info("停止所有 ROS2 进程...")
            self.stop_all()
            time.sleep(2)
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
            time.sleep(3)
            self.update_device_status()
            if self.device_connected:
                self.status_var.set("状态: 强制重连成功")
                messagebox.showinfo("成功", "✅ 相机强制重连成功！\n\n设备已重新识别，可以启动系统")
                logger.info("强制重连成功")
            else:
                self.status_var.set("状态: 设备仍未连接")
                messagebox.showwarning("重连失败", "❌ 相机仍未检测到\n\n请尝试:\n1. 物理重新插拔 USB 线\n2. 检查 USB 线是否损坏\n3. 尝试不同的 USB 端口")
        except Exception as e:
            logger.error(f"强制重连失败: {e}")
            messagebox.showerror("错误", f"强制重连失败:\n{str(e)}")
            self.status_var.set("状态: 重连失败")

    def check_device_before_launch(self):
        self.update_device_status()
        if not self.device_connected:
            result = messagebox.askyesno("设备未连接", "⚠️ 未检测到 OAK-D 设备！\n\n启动 Factor Perception 需要连接相机。\n如果相机已连接，可能被其他程序占用或驱动异常。\n\n是否尝试强制重连？\n(将停止所有 ROS2 进程并重置设备)")
            if result:
                self.force_reconnect()
                self.update_device_status()
                return self.device_connected
            return False
        return True


if __name__ == "__main__":
    root = tk.Tk()
    app = FactorControlPanel(root)
    root.mainloop()
