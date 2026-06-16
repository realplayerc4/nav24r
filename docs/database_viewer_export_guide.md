# Octomap 导出 - Database Viewer 方法使用指南

## 🎯 最佳导出方法：Database Viewer GUI

**为什么选择 Database Viewer？**

| 特点 | 优势 |
|------|------|
| **可靠性** | ✅ 官方工具，最稳定 |
| **速度** | ✅ 5-15秒（无需启动 Factor Perception） |
| **可视化** | ✅ 可以查看地图质量 |
| **独立性** | ✅ 不需要相机连接 |
| **灵活性** | ✅ 支持多种格式和分辨率 |

---

## 📋 使用步骤

### 步骤 1: 在控制面板选择地图

```
已有地图: [map_20260615_1424 ▼]
点击: 🗺️ 导出Octomap
选择分辨率: 0.02m ⭐ 推荐
点击: 开始导出
```

### 步骤 2: 点击启动 Database Viewer

控制面板会显示一个指导窗口：

```
┌──────────────────────────────────────────────┐
│  导出 Octomap 指导 - map_20260615_1424        │
├──────────────────────────────────────────────┤
│  导出 Octomap 最佳方法                       │
│                                              │
│  数据库: map_20260615_1424                   │
│  分辨率: 0.02m                               │
│  文件大小: 190.0 MB                          │
│                                              │
│  ────────────────────────────────────────    │
│                                              │
│  导出步骤:                                   │
│                                              │
│  步骤 1: 点击下方按钮启动 Database Viewer    │
│                                              │
│  步骤 2: 在 Database Viewer 中操作:          │
│         File → Export 3D clouds...          │
│                                              │
│  步骤 3: 在弹出窗口中:                        │
│         ✓ 选择 "Export Octomap"             │
│         ✓ 设置分辨率: 0.02m                  │
│         ✓ 点击 "Export"                     │
│                                              │
│  步骤 4: 保存文件:                            │
│         推荐: ~/rtabmap_maps/...octomap.bt   │
│                                              │
│  ────────────────────────────────────────    │
│                                              │
│  为什么使用 Database Viewer?                 │
│  ✅ 最可靠的导出方法（官方工具）              │
│  ✅ 不需要启动 Factor Perception              │
│  ✅ 不需要相机连接                            │
│  ✅ 可视化地图质量                            │
│  ✅ 导出时间: 5-15秒                          │
│                                              │
│  [🚀 启动 Database Viewer] [📋 复制命令] [关闭] │
└──────────────────────────────────────────────┘
```

### 步骤 3: 在 Database Viewer 中导出

Database Viewer 启动后：

```
菜单操作:
  File → Export 3D clouds...

弹出窗口:
  ☑ Export Octomap
  ☑ Resolution: 0.02m
  [Export]

保存位置:
  ~/rtabmap_maps/map_20260615_1424_octomap_0.02m.bt
```

### 步骤 4: 验证导出结果

```bash
# 查看文件
ls -lh ~/rtabmap_maps/*.bt

# 可视化
octomap-viewer ~/rtabmap_maps/map_octomap_0.02m.bt

# 查看统计
octomap-info ~/rtabmap_maps/map_octomap_0.02m.bt
```

---

## ⏱️ 时间对比

| 方法 | 总时间 | 说明 |
|------|--------|------|
| **启动 Factor Perception** | 30-60秒 | ❌ 复杂、易出错 |
| **Database Viewer GUI** | 5-15秒 | ✅ 快速、可靠 |
| **rtabmap-export** | 不支持 Octomap | ❌ 只能导出点云 |

---

## 🎯 分辨率建议

| 分辨率 | 适用场景 | 推荐度 |
|-------|---------|--------|
| **0.01m** | 工业应用、精细操作 | ⭐⭐ |
| **0.02m** | 人形机器人导航 | ⭐⭐⭐⭐⭐ |
| **0.05m** | 通用导航 | ⭐⭐⭐⭐ |
| **0.10m** | 快速规划 | ⭐⭐⭐ |

**推荐**: **0.02m** - 最适合人形机器人导航

---

## 💡 优势总结

### Database Viewer vs 其他方法

```
Database Viewer:
  ✅ 官方工具
  ✅ 直接从数据库读取
  ✅ 不需要任何外部程序
  ✅ 可视化地图质量
  ✅ 支持多种格式
  ✅ 速度最快

启动 Factor Perception:
  ❌ 需要相机连接
  ❌ 需要等待加载
  ❌ 占用大量资源
  ❌ 容易出错
  ❌ 时间最长

rtabmap-export:
  ❌ 不支持 Octomap 格式
  ⚠️ 只能导出点云
  ⚠️ 需要额外转换步骤
```

---

## 📁 导出文件管理

### 推荐的文件命名规范

```
命名格式:
  <地图名>_octomap_<分辨率>m.bt

示例:
  map_20260615_1424_octomap_0.02m.bt
  map_20260615_1424_octomap_0.05m.bt

存储位置:
  ~/rtabmap_maps/
```

### 文件大小参考

| 分辨率 | 190MB 数据库导出大小 |
|-------|---------------------|
| 0.01m | ~100-200MB |
| 0.02m | ~50-80MB ⭐ |
| 0.05m | ~10-20MB |
| 0.10m | ~5-10MB |

---

## 🔧 高级技巧

### 1. 批量导出不同分辨率

可以在 Database Viewer 中多次导出：

```
第一次: 分辨率 0.02m → 保存为 map_octomap_0.02m.bt
第二次: 分辨率 0.05m → 保存为 map_octomap_0.05m.bt
第三次: 分辨率 0.10m → 保存为 map_octomap_0.10m.bt
```

### 2. 同时导出多种格式

Database Viewer 支持同时导出：
- Octomap (.bt)
- PLY (点云)
- OBJ (网格)

### 3. 检查地图质量

导出前可以在 Database Viewer 中检查：
- 闭环检测（绿色线条）
- 节点分布
- 拓扑结构

---

## ❓ 常见问题

### Q1: Database Viewer 启动失败？

**解决方案**:
```bash
# 检查工具是否安装
which rtabmap-databaseViewer

# 如果缺失，安装
sudo apt install ros-jazzy-rtabmap-tools
```

### Q2: 导出的 Octomap 文件太大？

**解决方案**:
- 降低分辨率（使用 0.05m 或 0.10m）
- Database Viewer 有压缩选项

### Q3: 导出的 Octomap 为空？

**原因**: 地图中没有足够的 3D 数据

**解决方案**:
- 检查 Database Viewer 中的 3D 视图
- 确认地图包含障碍物数据

---

## 🎊 总结

**Database Viewer 是导出 Octomap 的最佳方法！**

**特点**:
- ✅ 快速（5-15秒）
- ✅ 可靠（官方工具）
- ✅ 简单（GUI 操作）
- ✅ 灵活（多格式支持）
- ✅ 独立（无需相机）

**控制面板已集成一键启动功能，现在导出 Octomap 非常简单！** 🚀