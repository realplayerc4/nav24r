#!/usr/bin/env python3
"""
Factor Perception 控制面板
建图模式 + 导航模式 + 地图管理
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import threading
import os
import glob
import json
from datetime import datetime

class FactorControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Factor Perception 控制面板")
        self.root.geometry("700x500")
        self.root.configure(bg='#2b2b2b')

        # 进程引用
        self.current_process = None

        # 地图配置
        self.map_dir = "~/rtabmap_maps"
        self.current_map_id = None

        # 配置文件
        self.config_file = "/home/yq/nav24r/config/maps_config.json"
        self.load_config()

        self.setup_ui()

    def load_config(self):
        """加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "maps_dir": "~/rtabmap_maps",
                "last_map": None,
                "maps": {}
            }

    def save_config(self):
        """保存配置"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def setup_ui(self):
        # 标题
        title = tk.Label(
            self.root,
            text="Factor Perception 控制面板",
            font=('Arial', 18, 'bold'),
            fg='#00ff88',
            bg='#2b2b2b'
        )
        title.pack(pady=15)

        # ====== 地图管理区域 ======
        map_frame = tk.LabelFrame(
            self.root,
            text="🗺️ 地图管理",
            font=('Arial', 12),
            fg='#ffffff',
            bg='#2b2b2b',
            padx=15,
            pady=10
        )
        map_frame.pack(fill=tk.X, padx=20, pady=10)

        # 地图ID输入
        id_row = tk.Frame(map_frame, bg='#2b2b2b')
        id_row.pack(fill=tk.X, pady=5)

        tk.Label(id_row, text="地图ID:", font=('Arial', 11), fg='#ffffff', bg='#2b2b2b').pack(side=tk.LEFT)

        self.map_id_entry = tk.Entry(id_row, font=('Arial', 11), width=15)
        self.map_id_entry.pack(side=tk.LEFT, padx=10)
        # 自动生成默认ID
        default_id = f"map_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.map_id_entry.insert(0, default_id)

        # 新建地图按钮
        self.new_map_btn = tk.Button(
            id_row,
            text="新建地图",
            font=('Arial', 10),
            bg='#4a7c59',
            fg='white',
            command=self.new_map
        )
        self.new_map_btn.pack(side=tk.LEFT, padx=10)

        # 地图选择下拉框
        select_row = tk.Frame(map_frame, bg='#2b2b2b')
        select_row.pack(fill=tk.X, pady=5)

        tk.Label(select_row, text="选择地图:", font=('Arial', 11), fg='#ffffff', bg='#2b2b2b').pack(side=tk.LEFT)

        self.map_combo = ttk.Combobox(select_row, font=('Arial', 11), width=30)
        self.map_combo.pack(side=tk.LEFT, padx=10)
        self.refresh_map_list()

        tk.Button(
            select_row,
            text="刷新列表",
            font=('Arial', 10),
            bg='#3d5a80',
            fg='white',
            command=self.refresh_map_list
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            select_row,
            text="删除地图",
            font=('Arial', 10),
            bg='#e63946',
            fg='white',
            command=self.delete_map
        ).pack(side=tk.LEFT, padx=5)

        # ====== 功能模块区域 ======
        mode_frame = tk.LabelFrame(
            self.root,
            text="功能模块",
            font=('Arial', 12),
            fg='#ffffff',
            bg='#2b2b2b',
            padx=15,
            pady=10
        )
        mode_frame.pack(fill=tk.X, padx=20, pady=10)

        # 按钮网格
        buttons_frame = tk.Frame(mode_frame, bg='#2b2b2b')
        buttons_frame.pack()

        # 建图模式按钮
        self.mapping_btn = tk.Button(
            buttons_frame,
            text="🗺️ 开始建图\nSLAM Mapping",
            font=('Arial', 12),
            width=18,
            height=2,
            bg='#3d5a80',
            fg='white',
            activebackground='#4a7c59',
            command=self.start_mapping
        )
        self.mapping_btn.grid(row=0, column=0, padx=8, pady=8)

        # 导航模式按钮
        self.nav_btn = tk.Button(
            buttons_frame,
            text="🧭 开始导航\nNavigation",
            font=('Arial', 12),
            width=18,
            height=2,
            bg='#3d5a80',
            fg='white',
            activebackground='#ee6c4d',
            command=self.start_navigation
        )
        self.nav_btn.grid(row=0, column=1, padx=8, pady=8)

        # 完整导航系统按钮
        self.full_btn = tk.Button(
            buttons_frame,
            text="🚀 完整导航\nFactor + Nav2",
            font=('Arial', 12),
            width=18,
            height=2,
            bg='#3d5a80',
            fg='white',
            activebackground='#98c1d9',
            command=self.start_full_nav
        )
        self.full_btn.grid(row=0, column=2, padx=8, pady=8)

        # RViz 可视化按钮
        self.rviz_btn = tk.Button(
            buttons_frame,
            text="📊 RViz 可视化\nVisualization",
            font=('Arial', 12),
            width=18,
            height=2,
            bg='#3d5a80',
            fg='white',
            activebackground='#c09553',
            command=self.launch_rviz
        )
        self.rviz_btn.grid(row=1, column=0, padx=8, pady=8)

        # 查看数据库按钮
        self.db_btn = tk.Button(
            buttons_frame,
            text="📁 查看数据库\nDatabase Viewer",
            font=('Arial', 12),
            width=18,
            height=2,
            bg='#3d5a80',
            fg='white',
            activebackground='#6b5b95',
            command=self.view_database
        )
        self.db_btn.grid(row=1, column=1, padx=8, pady=8)

        # 地图信息按钮
        self.info_btn = tk.Button(
            buttons_frame,
            text="ℹ️ 地图信息\nMap Info",
            font=('Arial', 12),
            width=18,
            height=2,
            bg='#3d5a80',
            fg='white',
            activebackground='#88b04b',
            command=self.show_map_info
        )
        self.info_btn.grid(row=1, column=2, padx=8, pady=8)

        # ====== 控制区域 ======
        control_frame = tk.LabelFrame(
            self.root,
            text="控制",
            font=('Arial', 12),
            fg='#ffffff',
            bg='#2b2b2b',
            padx=15,
            pady=5
        )
        control_frame.pack(fill=tk.X, padx=20, pady=10)

        # 停止按钮
        self.stop_btn = tk.Button(
            control_frame,
            text="⏹️ 停止所有进程",
            font=('Arial', 11),
            width=20,
            height=1,
            bg='#e63946',
            fg='white',
            activebackground='#ff0000',
            command=self.stop_all
        )
        self.stop_btn.pack(pady=5)

        # ====== 状态显示 ======
        self.status_var = tk.StringVar(value="状态: 就绪 | 当前地图: 无")
        status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=('Arial', 11),
            fg='#00ff88',
            bg='#2b2b2b'
        )
        status_label.pack(pady=10)

        # ====== 信息区域 ======
        info_text = """
快捷命令:
• 新建地图: 输入ID → 点击新建 → 开始建图
• 加载地图: 选择地图 → 开始导航
• 地图存储: ~/rtabmap_maps/<map_id>.db
        """
        info_label = tk.Label(
            self.root,
            text=info_text,
            font=('Arial', 9),
            fg='#888888',
            bg='#2b2b2b',
            justify=tk.LEFT
        )
        info_label.pack()

    def refresh_map_list(self):
        """刷新地图列表"""
        maps_dir = os.path.expanduser("~/rtabmap_maps")
        if not os.path.exists(maps_dir):
            os.makedirs(maps_dir)

        # 查找所有 .db 文件
        db_files = glob.glob(os.path.join(maps_dir, "*.db"))
        map_names = [os.path.basename(f).replace(".db", "") for f in db_files]

        # 也检查默认位置的地图
        default_db = os.path.expanduser("~/rtabmap.db")
        if os.path.exists(default_db):
            map_names.append("default (rtabmap.db)")

        self.map_combo['values'] = sorted(map_names, reverse=True)

        if map_names:
            self.map_combo.set(map_names[0])

    def new_map(self):
        """新建地图"""
        map_id = self.map_id_entry.get().strip()

        if not map_id:
            messagebox.showerror("错误", "请输入地图ID")
            return

        # 验证ID格式 (只允许字母、数字、下划线、横线)
        if not map_id.replace('_', '').replace('-', '').isalnum():
            messagebox.showerror("错误", "地图ID只能包含字母、数字、下划线和横线")
            return

        # 创建地图目录
        maps_dir = os.path.expanduser("~/rtabmap_maps")
        if not os.path.exists(maps_dir):
            os.makedirs(maps_dir)

        # 检查是否已存在
        db_path = os.path.join(maps_dir, f"{map_id}.db")
        if os.path.exists(db_path):
            messagebox.showwarning("警告", f"地图 '{map_id}' 已存在，建图将追加到现有地图")

        self.current_map_id = map_id
        self.config["last_map"] = map_id
        self.config["maps"][map_id] = {
            "created": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "path": db_path,
            "description": ""
        }
        self.save_config()

        self.status_var.set(f"状态: 新地图已创建 | 当前地图: {map_id}")
        self.refresh_map_list()

        messagebox.showinfo("成功", f"地图 '{map_id}' 已准备\n数据库路径: {db_path}\n\n点击 '开始建图' 启动SLAM")

    def get_database_path(self):
        """获取当前选中的数据库路径"""
        selected = self.map_combo.get()

        if selected == "default (rtabmap.db)" or not selected:
            return "~/rtabmap.db"

        maps_dir = os.path.expanduser("~/rtabmap_maps")
        return os.path.join(maps_dir, f"{selected}.db")

    def start_mapping(self):
        """启动建图模式"""
        map_id = self.map_id_entry.get().strip()

        if not map_id:
            messagebox.showerror("错误", "请先输入地图ID并点击 '新建地图'")
            return

        self.stop_all()

        db_path = os.path.expanduser("~/rtabmap_maps") + f"/{map_id}.db"

        self.status_var.set(f"状态: 建图模式运行中 | 地图: {map_id}")
        self.update_button_state('mapping')

        # 启动 Factor Perception 建图
        cmd = f"ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=false rtabmap_viz:=true database_path:={db_path}"
        threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()

        # 启动 RViz 建图配置
        threading.Thread(
            target=lambda: subprocess.Popen(
                "rviz2 -d /home/yq/nav24r/config/mapping.rviz",
                shell=True
            ),
            daemon=True
        ).start()

    def start_navigation(self):
        """启动导航模式（定位）"""
        selected_map = self.map_combo.get()

        if not selected_map:
            messagebox.showerror("错误", "请选择要加载的地图")
            return

        self.stop_all()

        db_path = self.get_database_path()
        db_path_expanded = os.path.expanduser(db_path)

        if not os.path.exists(db_path_expanded):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return

        self.status_var.set(f"状态: 导航模式运行中 | 地图: {selected_map}")
        self.update_button_state('navigation')

        # 启动 Factor Perception 定位模式
        cmd = f"ros2 launch /home/yq/nav24r/factor_perception_auto.launch.py localization:=true rtabmap_viz:=true database_path:={db_path}"
        threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()

        # 启动 RViz 导航配置
        threading.Thread(
            target=lambda: subprocess.Popen(
                "rviz2 -d /home/yq/nav24r/config/navigation.rviz",
                shell=True
            ),
            daemon=True
        ).start()

    def start_full_nav(self):
        """启动完整导航系统"""
        selected_map = self.map_combo.get()

        if not selected_map:
            messagebox.showerror("错误", "请选择要加载的地图")
            return

        db_path = self.get_database_path()
        db_path_expanded = os.path.expanduser(db_path)

        if not os.path.exists(db_path_expanded):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return

        self.stop_all()
        self.status_var.set(f"状态: 完整导航运行中 | 地图: {selected_map}")
        self.update_button_state('full')

        cmd = f"ros2 launch /home/yq/nav24r/launch/nav24r_full.launch.py database_path:={db_path}"
        threading.Thread(target=self.run_command, args=(cmd,), daemon=True).start()

        # 启动 RViz
        threading.Thread(
            target=lambda: subprocess.Popen(
                "rviz2 -d /home/yq/nav24r/config/navigation.rviz",
                shell=True
            ),
            daemon=True
        ).start()

    def view_database(self):
        """打开数据库查看器"""
        selected_map = self.map_combo.get()

        if not selected_map:
            messagebox.showerror("错误", "请选择要查看的地图")
            return

        db_path = self.get_database_path()
        db_path_expanded = os.path.expanduser(db_path)

        if not os.path.exists(db_path_expanded):
            messagebox.showerror("错误", f"地图文件不存在: {db_path}")
            return

        subprocess.Popen(f"rtabmap-databaseViewer {db_path_expanded}", shell=True)
        self.status_var.set(f"状态: 打开数据库查看器 | 地图: {selected_map}")

    def show_map_info(self):
        """显示地图信息"""
        selected_map = self.map_combo.get()

        if not selected_map:
            messagebox.showinfo("信息", "请先选择一个地图")
            return

        db_path = self.get_database_path()
        db_path_expanded = os.path.expanduser(db_path)

        if not os.path.exists(db_path_expanded):
            messagebox.showinfo("信息", f"地图文件不存在: {db_path}")
            return

        # 获取文件信息
        file_size = os.path.getsize(db_path_expanded) / (1024 * 1024)  # MB
        mod_time = datetime.fromtimestamp(os.path.getmtime(db_path_expanded))

        # 从配置获取创建时间
        map_info = self.config.get("maps", {}).get(selected_map, {})
        created = map_info.get("created", "未知")

        info = f"""
地图信息:
━━━━━━━━━━━━━━━━━━━━━
ID: {selected_map}
路径: {db_path}
大小: {file_size:.2f} MB
创建时间: {created}
最后修改: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━
        """

        messagebox.showinfo("地图信息", info)

    def delete_map(self):
        """删除地图"""
        selected_map = self.map_combo.get()

        if not selected_map:
            messagebox.showerror("错误", "请选择要删除的地图")
            return

        if selected_map == "default (rtabmap.db)":
            messagebox.showerror("错误", "不能删除默认地图文件")
            return

        # 确认删除
        confirm = messagebox.askyesno("确认删除", f"确定要删除地图 '{selected_map}'?\n此操作不可恢复!")

        if not confirm:
            return

        db_path = self.get_database_path()
        db_path_expanded = os.path.expanduser(db_path)

        if os.path.exists(db_path_expanded):
            os.remove(db_path_expanded)

        # 从配置中移除
        if selected_map in self.config.get("maps", {}):
            del self.config["maps"][selected_map]
        self.save_config()

        self.refresh_map_list()
        self.status_var.set(f"状态: 地图 '{selected_map}' 已删除")
        messagebox.showinfo("成功", f"地图 '{selected_map}' 已删除")

    def launch_rviz(self):
        """单独启动 RViz"""
        self.status_var.set("状态: RViz 已启动")
        subprocess.Popen("rviz2 -d /home/yq/nav24r/config/mapping.rviz", shell=True)

    def run_command(self, cmd):
        """后台运行命令"""
        self.current_process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def stop_all(self):
        """停止所有进程"""
        subprocess.run("pkill -f 'ros2 launch'", shell=True)
        subprocess.run("pkill -f rviz2", shell=True)
        subprocess.run("pkill -f rtabmap-databaseViewer", shell=True)
        self.status_var.set("状态: 已停止")
        self.update_button_state('ready')

    def update_button_state(self, mode):
        """更新按钮状态显示"""
        colors = {
            'ready': '#3d5a80',
            'mapping': '#4a7c59',
            'navigation': '#ee6c4d',
            'full': '#98c1d9'
        }

        self.mapping_btn.configure(bg=colors['mapping'] if mode == 'mapping' else colors['ready'])
        self.nav_btn.configure(bg=colors['navigation'] if mode == 'navigation' else colors['ready'])
        self.full_btn.configure(bg=colors['full'] if mode == 'full' else colors['ready'])


def main():
    root = tk.Tk()
    app = FactorControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()