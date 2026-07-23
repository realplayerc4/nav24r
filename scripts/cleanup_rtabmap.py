#!/usr/bin/env python3
"""
cleanup_rtabmap.py — RTAB-Map 数据库节点清理工具

功能：
  1. 列出数据库所有节点（ID、权重、标签、数据大小、邻居/parents/children 数）
  2. 选中某行，下方实时显示：该节点图 + 父节点缩略图 + 子节点缩略图
  3. 支持多选删除，删除后光标自动移到下一行
  4. 删除后可通过「重新生成地图」清理缓存的 occupancy grid，让 RTAB-Map 重建地图

用法：
  python3 cleanup_rtabmap.py [数据库路径]
  # 默认路径：~/rtabmap.db
"""

import sys
import os
import sqlite3
import zlib
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
import numpy as np


DEFAULT_DB = os.path.expanduser("~/rtabmap.db")
THUMB_SIZE = 96
PREVIEW_MAX_W = 400


# ─── 数据库操作 ─────────────────────────────────────────────────────

def get_node_list(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT n.id, n.weight, n.label, length(d.image) AS data_size
        FROM Node n
        LEFT JOIN Data d ON d.id = n.id
        ORDER BY n.id ASC
    """)
    nodes = {row["id"]: dict(row) for row in cur.fetchall()}

    cur.execute("SELECT from_id, to_id FROM Link")
    parent_count = {nid: 0 for nid in nodes}
    child_count = {nid: 0 for nid in nodes}
    for from_id, to_id in cur.fetchall():
        if from_id in parent_count and to_id in parent_count:
            if from_id < to_id:
                child_count[from_id] += 1
                parent_count[to_id] += 1
            else:
                parent_count[from_id] += 1
                child_count[to_id] += 1

    conn.close()

    return [
        (
            nid,
            row["weight"],
            row["label"] or "",
            row["data_size"] or 0,
            parent_count[nid] + child_count[nid],
            parent_count[nid],
            child_count[nid],
        )
        for nid, row in sorted(nodes.items())
    ]


def load_image(db_path, node_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT image FROM Data WHERE id = ?", (node_id,))
    row = cur.fetchone()
    conn.close()
    if row is None or row[0] is None:
        return None
    raw = row[0]
    try:
        data = zlib.decompress(raw)
    except zlib.error:
        data = raw
    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def load_neighbors(db_path, node_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT from_id, to_id FROM Link WHERE from_id = ? OR to_id = ?",
        (node_id, node_id),
    )
    parents, children = [], []
    for from_id, to_id in cur.fetchall():
        other = to_id if from_id == node_id else from_id
        if other < node_id:
            parents.append(other)
        else:
            children.append(other)
    conn.close()
    return sorted(set(parents)), sorted(set(children))


def delete_node(db_path, node_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute("DELETE FROM Feature WHERE node_id = ?", (node_id,))
        cur.execute("DELETE FROM GlobalDescriptor WHERE node_id = ?", (node_id,))
        cur.execute("DELETE FROM Link WHERE from_id = ? OR to_id = ?", (node_id, node_id))
        cur.execute("DELETE FROM Statistics WHERE id = ?", (node_id,))
        cur.execute("DELETE FROM Data WHERE id = ?", (node_id,))
        cur.execute("DELETE FROM Node WHERE id = ?", (node_id,))
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    conn2 = sqlite3.connect(db_path)
    conn2.execute("VACUUM")
    conn2.close()


def regenerate_map(db_path):
    """清理缓存的 occupancy grid 地图数据，让 RTAB-Map 下次启动时重建地图

    删除节点后，缓存的 2D 地图和优化位姿存于 Admin 表：
      opt_ids, opt_poses, opt_last_localization, opt_map
    每个节点的 per-node occupancy grid 存于 Data 表：
      ground_cells, obstacle_cells, empty_cells
    这些缓存不会因节点删除而自动更新，需要手动清除后重建。
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("BEGIN")
        # 清除 Admin 表中的缓存地图/位姿
        cur.execute("""
            UPDATE Admin SET
                opt_ids = NULL,
                opt_poses = NULL,
                opt_last_localization = NULL,
                opt_map = NULL,
                opt_map_x_min = NULL,
                opt_map_y_min = NULL,
                opt_map_resolution = NULL
        """)
        # 清除所有 per-node occupancy grid（让 RTAB-Map 重建）
        cur.execute("""
            UPDATE Data SET
                ground_cells = NULL,
                obstacle_cells = NULL,
                empty_cells = NULL,
                cell_size = NULL,
                view_point_x = NULL,
                view_point_y = NULL,
                view_point_z = NULL
        """)
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    conn2 = sqlite3.connect(db_path)
    conn2.execute("VACUUM")
    conn2.close()


# ─── GUI 辅助 ────────────────────────────────────────────────────────

def _make_thumb(img, size=THUMB_SIZE):
    h, w = img.shape[:2]
    scale = min(size / w, size / h)
    if scale < 1.0:
        thumb = cv2.resize(img, (int(w * scale), int(h * scale)))
    else:
        thumb = img.copy()
    img_rgb = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
    from PIL import Image, ImageTk
    return ImageTk.PhotoImage(Image.fromarray(img_rgb))


def _place_img(parent, photo, label_text):
    frame = ttk.Frame(parent)
    lbl = ttk.Label(frame, image=photo)
    lbl.image = photo
    lbl.pack()
    ttk.Label(frame, text=label_text, font=("TkDefaultFont", 8), foreground="#888").pack()
    return frame


# ─── 主界面 ─────────────────────────────────────────────────────────

class CleanupApp:
    def __init__(self, root, db_path):
        self.root = root
        self.db_path = db_path
        self.root.title(f"RTAB-Map 清理工具 — {os.path.basename(db_path)}")
        self.root.geometry("750x900")

        self._thumb_cache = {}
        self._img_cache = {}

        self._build_ui()
        self._load_nodes()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)
        ttk.Label(
            top,
            text="点击选中一行（Ctrl+点击多选）→ 下方显示该图及父子邻居 → 确认后删除",
            foreground="#555",
        ).pack(side=tk.LEFT)

        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill=tk.BOTH, expand=False, padx=8, pady=4)

        columns = ("id", "weight", "label", "size", "neighbors", "parents", "children")
        self.tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=18,
            selectmode="extended",
        )
        self.tree.heading("id",        text="ID")
        self.tree.heading("weight",    text="权重")
        self.tree.heading("label",     text="标签")
        self.tree.heading("size",      text="大小")
        self.tree.heading("neighbors", text="邻居")
        self.tree.heading("parents",   text="← parents")
        self.tree.heading("children",  text="children →")

        self.tree.column("id",        width=50,  anchor=tk.CENTER)
        self.tree.column("weight",    width=55,  anchor=tk.CENTER)
        self.tree.column("label",     width=160, anchor=tk.W)
        self.tree.column("size",      width=80,  anchor=tk.CENTER)
        self.tree.column("neighbors", width=55,  anchor=tk.CENTER)
        self.tree.column("parents",   width=70,  anchor=tk.CENTER)
        self.tree.column("children",  width=70,  anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        preview_frame = ttk.LabelFrame(self.root, text="  预览  ", padding=8)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.preview_container = ttk.Frame(preview_frame)
        self.preview_container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            self.preview_container,
            text="← 点击表格中的行，这里显示图片",
            foreground="#aaa",
        ).pack(pady=40)

        btn_frame = ttk.Frame(self.root, padding=8)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="🔄 刷新列表", command=self._load_nodes).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btn_frame, text="🗑 删除选中节点", command=self._on_delete).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(
            btn_frame, text="🗺️ 重新生成地图", command=self._on_regenerate_map
        ).pack(side=tk.RIGHT, padx=4)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        ).pack(fill=tk.X, side=tk.BOTTOM)

    def _load_nodes(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            nodes = get_node_list(self.db_path)
        except Exception as e:
            messagebox.showerror("错误", f"无法读取数据库：{e}")
            return

        for nid, weight, label, size, n_nbr, n_par, n_ch in nodes:
            size_str = f"{size / 1024:.1f} KB" if size > 0 else "0 B"
            self.tree.insert(
                "", tk.END,
                values=(nid, weight, label, size_str, n_nbr, n_par, n_ch),
            )

        self.status_var.set(f"共 {len(nodes)} 个节点 | 选中行查看预览")
        self._clear_preview()

    def _clear_preview(self):
        for w in self.preview_container.winfo_children():
            w.destroy()

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        # 只预览第一个选中的
        item = self.tree.item(selection[0])
        nid = int(item["values"][0])

        if nid not in self._img_cache:
            self._img_cache[nid] = load_image(self.db_path, nid)
        img = self._img_cache[nid]

        parent_ids, child_ids = load_neighbors(self.db_path, nid)

        for nid2 in parent_ids + child_ids:
            if nid2 not in self._img_cache:
                self._img_cache[nid2] = load_image(self.db_path, nid2)

        self._render_preview(nid, img, parent_ids, child_ids)
        self.status_var.set(
            f"节点 #{nid} | 父节点 {len(parent_ids)} 个 | 子节点 {len(child_ids)} 个"
        )

    def _render_preview(self, nid, img, parent_ids, child_ids):
        self._clear_preview()

        has_parents = len(parent_ids) > 0
        has_children = len(child_ids) > 0

        if img is None:
            ttk.Label(
                self.preview_container,
                text=f"节点 #{nid} — 无图像数据",
                foreground="#888",
            ).pack(pady=20)
            return

        main_frame = ttk.Frame(self.preview_container)
        main_frame.grid(
            row=0, column=0,
            rowspan=2 if has_parents and has_children else 1,
            padx=8, pady=4, sticky="n",
        )

        h, w = img.shape[:2]
        scale = min(PREVIEW_MAX_W / w, PREVIEW_MAX_W / h, 1.0)
        if scale < 1.0:
            disp = cv2.resize(img, (int(w * scale), int(h * scale)))
        else:
            disp = img

        if nid not in self._thumb_cache:
            self._thumb_cache[nid] = _make_thumb(disp, PREVIEW_MAX_W)

        ttk.Label(main_frame, image=self._thumb_cache[nid]).pack()
        ttk.Label(main_frame, text=f"#{nid} ← 当前", font=("TkDefaultFont", 9, "bold")).pack(pady=2)

        if has_parents:
            pf = ttk.LabelFrame(
                self.preview_container,
                text=f"  ← Parents ({len(parent_ids)})  ",
                padding=6,
            )
            pf.grid(row=0, column=1, padx=4, pady=2, sticky="nw")
            for pid in parent_ids:
                pimg = self._img_cache.get(pid)
                if pimg is not None:
                    thumb = _make_thumb(pimg)
                    _place_img(pf, thumb, f"#{pid}").pack(side=tk.LEFT, padx=3)

        if has_children:
            cf = ttk.LabelFrame(
                self.preview_container,
                text=f"  Children ({len(child_ids)}) →  ",
                padding=6,
            )
            row_cf = 1 if has_parents else 0
            cf.grid(row=row_cf, column=1, padx=4, pady=2, sticky="nw")
            for cid in child_ids:
                cimg = self._img_cache.get(cid)
                if cimg is not None:
                    thumb = _make_thumb(cimg)
                    _place_img(cf, thumb, f"#{cid}").pack(side=tk.LEFT, padx=3)

        self.preview_container.grid_columnconfigure(0, weight=0)
        self.preview_container.grid_columnconfigure(1, weight=1)

    def _on_delete(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先在列表中选中要删除的节点\n（按住 Ctrl 可多选）")
            return

        selected_ids = sorted(
            [int(self.tree.item(s)["values"][0]) for s in selection], reverse=True
        )

        if len(selected_ids) == 1:
            info_text = f"节点 #{selected_ids[0]}"
        else:
            info_text = (
                f"{len(selected_ids)} 个节点:\n  #"
                + "  #".join(str(i) for i in reversed(selected_ids))
            )

        info = (
            f"即将删除 {info_text}\n\n"
            f"删除后将清理关联数据并执行 VACUUM。\n\n"
            f"⚠️  此操作不可恢复，是否确认？"
        )
        if not messagebox.askyesno("确认删除", info, icon="warning"):
            return

        if not messagebox.askyesno("最后确认", f"确定删除 {len(selected_ids)} 个节点？", icon="warning"):
            return

        last_deleted_id = min(selected_ids)

        try:
            for nid in selected_ids:
                delete_node(self.db_path, nid)
                self._img_cache.pop(nid, None)
                self._thumb_cache.pop(nid, None)
        except Exception as e:
            messagebox.showerror("删除失败", str(e))
            return

        messagebox.showinfo("完成", f"已删除 {len(selected_ids)} 个节点")
        self._load_nodes()
        self._select_next_after(last_deleted_id)

    def _select_next_after(self, deleted_id):
        children = self.tree.get_children()
        if not children:
            return

        row_ids = [int(self.tree.item(c)["values"][0]) for c in children]

        target = None
        for i, rid in enumerate(row_ids):
            if rid > deleted_id:
                target = children[i]
                break

        if target is None and len(children) > 1:
            target = children[-1]

        if target:
            self.tree.selection_set(target)
            self.tree.see(target)
            self._on_select(None)

    def _on_regenerate_map(self):
        """清理缓存的 occupancy grid，让 RTAB-Map 下次启动时重建地图"""
        db_path = self._get_default_db()
        if not os.path.exists(db_path):
            messagebox.showinfo("提示", f"数据库不存在:\n{db_path}")
            return

        if not messagebox.askyesno(
            "重新生成地图",
            "将清除数据库中缓存的 occupancy grid 地图数据。\n\n"
            "RTAB-Map 下次启动时会根据当前 SLAM 图自动重建地图。\n\n"
            "是否继续？",
        ):
            return

        try:
            self.status_var.set("状态: 正在清理缓存地图...")
            self.root.update()
            regenerate_map(db_path)
        except Exception as e:
            messagebox.showerror("失败", f"清理失败:\n{str(e)}")
            self.status_var.set("状态: 清理失败")
            return

        messagebox.showinfo(
            "完成",
            "缓存地图已清除！\n\n"
            "请重新启动 RTAB-Map（定位模式），\n"
            "它将自动重建 occupancy grid 地图。",
        )
        self.status_var.set("状态: 地图缓存已清除，请重启 RTAB-Map")

    def _get_default_db(self):
        return DEFAULT_DB


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB

    if not os.path.isfile(db_path):
        print(f"错误：数据库文件不存在 — {db_path}", file=sys.stderr)
        sys.exit(1)

    root = tk.Tk()
    app = CleanupApp(root, db_path)
    root.mainloop()


if __name__ == "__main__":
    main()
