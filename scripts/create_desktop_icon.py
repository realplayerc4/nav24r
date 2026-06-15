#!/usr/bin/env python3
"""
创建 Factor Perception 控制面板的桌面图标
"""

import os
import subprocess

# 创建一个简单的图标
icon_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <!-- 背景圆形 -->
  <circle cx="32" cy="32" r="30" fill="#2b2b2b" stroke="#00ff88" stroke-width="2"/>

  <!-- 机器人图标 -->
  <g fill="#00ff88">
    <!-- 机器人头部 -->
    <rect x="22" y="15" width="20" height="16" rx="2" ry="2"/>
    <!-- 眼睛 -->
    <circle cx="27" cy="23" r="2" fill="#2b2b2b"/>
    <circle cx="37" cy="23" r="2" fill="#2b2b2b"/>
    <!-- 天线 -->
    <line x1="32" y1="15" x2="32" y2="8" stroke="#00ff88" stroke-width="2"/>
    <circle cx="32" cy="7" r="2"/>

    <!-- 机器人身体 -->
    <rect x="18" y="32" width="28" height="20" rx="2" ry="2"/>
    <!-- 控制面板按钮 -->
    <circle cx="25" cy="40" r="3" fill="#e63946"/>
    <circle cx="32" cy="40" r="3" fill="#4a7c59"/>
    <circle cx="39" cy="40" r="3" fill="#3d5a80"/>
  </g>
</svg>
"""

# 保存图标
icon_dir = os.path.expanduser("~/.local/share/icons")
os.makedirs(icon_dir, exist_ok=True)
icon_path = os.path.join(icon_dir, "factor_perception.svg")

with open(icon_path, 'w') as f:
    f.write(icon_content)

print(f"✅ 图标已创建: {icon_path}")

# 更新桌面快捷方式使用新图标
desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Factor Perception 控制面板
Comment=Factor Perception Control Panel for ROS2 Jazzy
Exec=/usr/bin/python3 /home/yq/nav24r/scripts/factor_control_panel.py
Icon={icon_path}
Terminal=false
Categories=Development;Robotics;
StartupNotify=true
Keywords=ROS2;Factor Perception;Navigation;SLAM;Robot;
Name[zh_CN]=Factor Perception 控制面板
Comment[zh_CN]=ROS2 Jazzy 导航与建图控制面板
"""

# 保存到桌面
desktop_path = os.path.expanduser("~/Desktop/Factor_Perception_Control_Panel.desktop")
with open(desktop_path, 'w') as f:
    f.write(desktop_content)

# 保存到应用菜单
app_path = os.path.expanduser("~/.local/share/applications/factor_perception_control_panel.desktop")
with open(app_path, 'w') as f:
    f.write(desktop_content)

# 设置权限
os.chmod(desktop_path, 0o755)
os.chmod(app_path, 0o755)

print(f"✅ 桌面快捷方式已更新: {desktop_path}")
print(f"✅ 应用菜单快捷方式已更新: {app_path}")
print("\n🎉 完成！你现在可以：")
print("  1. 在桌面双击图标启动控制面板")
print("  2. 在应用菜单中搜索 'Factor Perception' 启动")
