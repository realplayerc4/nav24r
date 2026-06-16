#!/usr/bin/env python3
"""
Factor Perception 控制面板
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import json
import logging
import yaml
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='/tmp/factor_control_panel.log'
)
logger = logging.getLogger(__name__)
import glob
from datetime import datetime

class FactorControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Factor Perception 控制面板")
        self.root.geometry("600x500")

        # 加载配置
        self.load_app_config()

        self.config_file = "/home/yq/nav24r/config/maps_config.json"
        self.maps_dir = os.path.expanduser("~/rtabmap_maps")

        self.load_config()
        self.create_ui()

    def load_app_config(self):
        """加载应用配置文件"""
        config_path = "/home/yq/nav24r/config/factor_perception_config.yaml"
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.app_config = yaml.safe_load(f)
                logger.info(f"配置文件加载成功: {config_path}")
            else:
                # 默认配置
                self.app_config = {
                    'camera': {'key': '12D0C1E7D1AB466C09BD9AE6427D5240'},
                    'ros': {'distro': 'jazzy', 'setup_path': '/opt/ros/jazzy/setup.bash'}
                }
                logger.warning("配置文件不存在，使用默认配置")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.app_config = {
                'camera': {'key': '12D0C1E7D1AB466C09BD9AE6427D5240'},
                'ros': {'distro': 'jazzy', 'setup_path': '/opt/ros/jazzy/setup.bash'}
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

        # 地图管理
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
        self.map_id_entry.delete(0, tk.END)
        self.map_id_entry.insert(0, name)
        self.status_var.set(f"状态: 续建 '{name}'")

    def delete_map(self):
        name = self.get_map_name()
        if not name:
            return
        if name == "default":
            messagebox.showerror("错误", "不能删除默认地图")
            return
        if not messagebox.askyesno("确认", f"删除地图 '{name}'?"):
            return
        db_path = self.get_db_path(name)
        if os.path.exists(db_path):
            os.remove(db_path)
        self.refresh_maps()
        self.status_var.set(f"状态: 已删除 '{name}'")

    def start_mapping(self):
        """开始建图"""
        try:
            map_id = self.map_id_entry.get().strip()
            if not map_id:
                messagebox.showerror("错误", "请输入地图ID")
                return
            db_path = self.get_db_path(map_id)
            ros_setup = self.app_config['ros']['setup_path']
            camera_key = self.app_config['camera']['key']
            cmd = f"bash -c 'source {ros_setup} && ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=false rtabmap_viz:=true database_path:={db_path} key:={camera_key}'"
            subprocess.Popen(cmd, shell=True)
            self.status_var.set(f"状态: 建图模式 | {map_id}")
            logger.info(f"启动建图模式: {map_id}, 数据库: {db_path}")
        except Exception as e:
            logger.error(f"启动建图失败: {e}")
            messagebox.showerror("错误", f"启动建图失败: {str(e)}")

    def start_navigation(self):
        """开始导航"""
        try:
            name = self.get_map_name()
            if not name:
                messagebox.showerror("错误", "请选择地图")
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
            cmd = f"bash -c 'source {ros_setup} && ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=true rtabmap_viz:=true database_path:={db_path} key:={camera_key}'"
            subprocess.Popen(cmd, shell=True)
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
        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", "地图不存在")
            return
        cmd = f"bash -c 'source /opt/ros/jazzy/setup.bash && ros2 launch /home/yq/nav24r/launch/nav24r_full.launch.py database_path:={db_path}'"
        subprocess.Popen(cmd, shell=True)
        self.status_var.set(f"状态: 完整导航 | {name}")

    def launch_rviz(self):
        """启动 RViz（顶视角配置）"""
        subprocess.Popen("bash -c 'source /opt/ros/jazzy/setup.bash && rviz2 -d /home/yq/nav24r/config/mapping.rviz'", shell=True)
        self.status_var.set("状态: RViz 已启动（顶视角）")

    def launch_rviz_3d(self):
        """启动 RViz（3D 视角配置）"""
        subprocess.Popen("bash -c 'source /opt/ros/jazzy/setup.bash && rviz2 -d /home/yq/nav24r/config/mapping_3d.rviz'", shell=True)
        self.status_var.set("状态: RViz 3D 已启动（多视角）")

    def launch_map_viewer(self):
        """启动地图观察器（专门用于查看已建好的地图）"""
        subprocess.Popen("bash -c 'source /opt/ros/jazzy/setup.bash && rviz2 -d /home/yq/nav24r/config/map_viewer_3d.rviz'", shell=True)
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
            cmd = f"bash -c 'source {ros_setup} && ros2 launch factor_perception factor_perception_launch.py localization:=true database_path:={db_path} key:={camera_key}'"
            subprocess.Popen(cmd, shell=True)

            # 等待 2 秒后启动 RViz 观察器
            import time
            time.sleep(2)

            # 启动地图观察器
            subprocess.Popen(f"bash -c 'source {ros_setup} && rviz2 -d /home/yq/nav24r/config/map_viewer_3d.rviz'", shell=True)

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
            ['python3', '/home/yq/nav24r/scripts/analyze_map_quality.py', db_path],
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
        """执行 Octomap 导出 - 直接从数据库导出（快速方法）"""

        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title(f"导出 Octomap - {name}")
        progress_window.geometry("500x300")

        # 进度信息
        info_frame = tk.Frame(progress_window)
        info_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(info_frame, text=f"数据库: {name}", font=('Arial', 10)).pack()
        tk.Label(info_frame, text=f"分辨率: {resolution}m", font=('Arial', 10)).pack()
        tk.Label(info_frame, text=f"文件大小: {os.path.getsize(db_path)/(1024*1024):.1f} MB", font=('Arial', 10)).pack()

        # 进度条
        progress_bar = ttk.Progressbar(progress_window, mode='determinate', length=400)
        progress_bar.pack(pady=20)

        # 进度文本
        progress_text = tk.StringVar(value="准备导出...")
        tk.Label(progress_window, textvariable=progress_text, font=('Arial', 10)).pack()

        # 时间预估
        time_text = tk.StringVar(value="预估时间: 5-10秒")
        tk.Label(progress_window, textvariable=time_text, font=('Arial', 9), fg='#666666').pack()

        # 详细日志
        log_frame = tk.Frame(progress_window)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        log_text = tk.Text(log_frame, height=8, width=50, font=('Consolas', 9))
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.config(yscrollcommand=scrollbar.set)

        # 关闭按钮（初始禁用）
        close_btn = tk.Button(progress_window, text="关闭", state=tk.DISABLED, command=progress_window.destroy, width=15)
        close_btn.pack(pady=10)

        # 输出文件
        output_dir = os.path.dirname(db_path)
        basename = os.path.basename(db_path).replace('.db', '')
        output_file = os.path.join(output_dir, f"{basename}_octomap_{resolution}m.bt")

        def log_message(msg):
            log_text.insert(tk.END, msg + "\n")
            log_text.see(tk.END)
            logger.info(msg)

        def update_progress(value, text):
            progress_bar['value'] = value
            progress_text.set(text)
            progress_window.update()

        def export_thread():
            try:
                log_message("=" * 50)
                log_message("直接从数据库导出 Octomap（快速方法）")
                log_message("=" * 50)
                log_message(f"数据库: {db_path}")
                log_message(f"分辨率: {resolution}m")
                log_message(f"输出: {output_file}")
                log_message("")
                log_message("✅ 使用 rtabmap-export 工具")
                log_message("   无需启动 Factor Perception")
                log_message("   无需等待地图加载")
                log_message("")

                update_progress(10, "检查导出工具...")
                log_message("步骤 1: 检查 rtabmap-export 可用性")

                # 检查工具
                check_cmd = "which rtabmap-export"
                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)

                if check_result.returncode == 0:
                    log_message(f"✓ 工具路径: {check_result.stdout.strip()}")
                    update_progress(20, "准备导出参数...")

                    log_message("")
                    log_message("步骤 2: 构建导出命令")

                    # 使用 rtabmap-export 导出 Octomap
                    # 注意：rtabmap-export 不直接支持 octomap 格式
                    # 我们需要导出点云，然后转换为 Octomap
                    # 或者使用 Database Viewer GUI 方法

                    log_message("⚠️  rtabmap-export 不直接支持 Octomap 格式")
                    log_message("")
                    log_message("推荐方法:")
                    log_message("  方法 1: Database Viewer GUI (最可靠)")
                    log_message(f"    rtabmap-databaseViewer {db_path}")
                    log_message("    File → Export 3D clouds → Octomap")
                    log_message("")
                    log_message("  方法 2: 启动定位模式获取 Octomap")
                    log_message("    (当需要实时 Octomap 时使用)")

                    update_progress(30, "导出点云数据...")

                    # 尝试导出点云作为备选
                    cloud_file = output_file.replace('.bt', '.ply')
                    export_cmd = f"rtabmap-export --db {db_path} --output {cloud_file} --cloud"

                    log_message("")
                    log_message("步骤 3: 导出点云数据（备选方案）")
                    log_message(f"  命令: {export_cmd}")

                    update_progress(50, "正在导出点云...")
                    log_message("  执行导出...")

                    export_result = subprocess.run(
                        export_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if export_result.returncode == 0:
                        update_progress(80, "处理导出结果...")
                        log_message("  ✓ 点云导出成功")

                        if os.path.exists(cloud_file):
                            size = os.path.getsize(cloud_file) / (1024*1024)
                            log_message(f"  ✓ 点云文件: {cloud_file}")
                            log_message(f"  ✓ 文件大小: {size:.2f} MB")
                            log_message("")
                            log_message("后续操作:")
                            log_message(f"  1. 在 Database Viewer 中导出 Octomap:")
                            log_message(f"     rtabmap-databaseViewer {db_path}")
                            log_message(f"     File → Export 3D clouds → Octomap")
                            log_message("")
                            log_message(f"  2. 或使用点云转换工具")
                    else:
                        log_message(f"  ✗ 导出失败: {export_result.stderr}")
                        log_message("")
                        log_message("解决方案:")
                        log_message(f"  使用 Database Viewer: rtabmap-databaseViewer {db_path}")

                    update_progress(100, "完成")
                    log_message("")
                    log_message("=" * 50)
                    log_message("总结:")
                    log_message("  • rtabmap-export 不直接支持 Octomap")
                    log_message("  • Database Viewer 是导出 Octomap 的最佳方法")
                    log_message("  • 点云数据已导出作为备选")
                    log_message("=" * 50)

                else:
                    log_message("✗ rtabmap-export 不可用")
                    log_message("")
                    log_message("解决方案:")
                    log_message(f"  安装工具: sudo apt install ros-jazzy-rtabmap-tools")
                    log_message(f"  或使用 Database Viewer: rtabmap-databaseViewer {db_path}")
                    update_progress(100, "需要安装工具")

                # 启用关闭按钮
                close_btn.config(state=tk.NORMAL)
                self.status_var.set(f"状态: 导出完成 - 建议使用 Database Viewer")

            except subprocess.TimeoutExpired:
                log_message("✗ 导出超时")
                update_progress(0, "导出超时")
                close_btn.config(state=tk.NORMAL)
            except Exception as e:
                log_message(f"✗ 导出失败: {str(e)}")
                update_progress(0, f"导出失败: {str(e)}")
                close_btn.config(state=tk.NORMAL)
                logger.error(f"Octomap 导出失败: {e}")

        # 启动导出线程
        import threading
        thread = threading.Thread(target=export_thread, daemon=True)
        thread.start()

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
            cmd = f"rtabmap-databaseViewer {db_path}"
            subprocess.Popen(cmd, shell=True, start_new_session=True)
            self.status_var.set(f"状态: Database Viewer 已启动 | {name}")
            logger.info(f"启动 Database Viewer: {db_path}")
        except Exception as e:
            error_msg = f"启动 Database Viewer 失败: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("错误", error_msg)

    def stop_all(self):
        """停止所有 ROS2 进程和 RTAB-Map 相关窗口"""
        # 停止 ROS2 launch 进程
        subprocess.run("pkill -f 'ros2 launch'", shell=True)

        # 停止 RViz
        subprocess.run("pkill -f rviz2", shell=True)

        # 停止 RTAB-Map 相关进程和窗口
        subprocess.run("pkill -f rtabmap", shell=True)  # RTAB-Map 核心进程
        subprocess.run("pkill -f 'rtabmap-databaseViewer'", shell=True)  # 数据库查看器
        subprocess.run("pkill -f 'rtabmap_viz'", shell=True)  # 可视化节点

        # 停止 Factor Perception 容器
        subprocess.run("pkill -f 'component_container'", shell=True)

        # 停止 robot_state_publisher
        subprocess.run("pkill -f 'robot_state_publisher'", shell=True)

        # 清理可能的僵尸进程
        subprocess.run("pkill -9 -f 'factor_perception'", shell=True)

        self.status_var.set("状态: 已停止所有进程")

if __name__ == "__main__":
    root = tk.Tk()
    app = FactorControlPanel(root)
    root.mainloop()
