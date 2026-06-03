#!/usr/bin/env python3
"""
Factor Perception 控制面板
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import json
import glob
from datetime import datetime

class FactorControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Factor Perception 控制面板")
        self.root.geometry("600x420")

        self.config_file = "/home/yq/nav24r/config/maps_config.json"
        self.maps_dir = os.path.expanduser("~/rtabmap_maps")

        self.load_config()
        self.create_ui()

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
        tk.Button(btn_row2, text="📁 数据库", width=14, height=2, command=self.view_database, bg='#4a7c59', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row2, text="⏹️ 停止", width=14, height=2, command=self.stop_all, bg='#e63946', fg='white').pack(side=tk.LEFT, padx=5)

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
        map_id = self.map_id_entry.get().strip()
        if not map_id:
            messagebox.showerror("错误", "请输入地图ID")
            return
        db_path = self.get_db_path(map_id)
        cmd = f"bash -c 'source /opt/ros/humble/setup.bash && ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=false rtabmap_viz:=true database_path:={db_path}'"
        subprocess.Popen(cmd, shell=True)
        self.status_var.set(f"状态: 建图模式 | {map_id}")

    def start_navigation(self):
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
        cmd = f"bash -c 'source /opt/ros/humble/setup.bash && ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=true rtabmap_viz:=true database_path:={db_path}'"
        subprocess.Popen(cmd, shell=True)
        self.status_var.set(f"状态: 导航模式 | {name}")

    def start_full_nav(self):
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return
        db_path = self.get_db_path(name)
        if not os.path.exists(db_path):
            messagebox.showerror("错误", "地图不存在")
            return
        cmd = f"bash -c 'source /opt/ros/humble/setup.bash && ros2 launch /home/yq/nav24r/launch/nav24r_full.launch.py database_path:={db_path}'"
        subprocess.Popen(cmd, shell=True)
        self.status_var.set(f"状态: 完整导航 | {name}")

    def launch_rviz(self):
        subprocess.Popen("bash -c 'source /opt/ros/humble/setup.bash && rviz2 -d /home/yq/nav24r/config/mapping.rviz'", shell=True)
        self.status_var.set("状态: RViz 已启动")

    def view_database(self):
        name = self.get_map_name()
        if not name:
            messagebox.showerror("错误", "请选择地图")
            return
        db_path = self.get_db_path(name)
        if os.path.exists(db_path):
            subprocess.Popen(f"rtabmap-databaseViewer {db_path}", shell=True)
            self.status_var.set(f"状态: 数据库查看器 | {name}")

    def stop_all(self):
        subprocess.run("pkill -f 'ros2 launch'", shell=True)
        subprocess.run("pkill -f rviz2", shell=True)
        self.status_var.set("状态: 已停止")

if __name__ == "__main__":
    root = tk.Tk()
    app = FactorControlPanel(root)
    root.mainloop()
