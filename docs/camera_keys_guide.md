# Factor Perception 相机密钥配置

## 密钥与机器码说明

Factor Perception SDK 需要两个标识符：

1. **密钥（Key）** - 用于激活 SDK 的授权码
2. **机器码（MXID）** - 相机设备的序列号（可选，用于自动识别）

这些标识符是**硬件绑定**的，每个相机型号对应唯一的密钥。这些密钥不需要保密，因为它们只能用于对应的硬件设备。

---

## 相机密钥对照表

| 相机型号 | 密钥（Key）| 机器码（MXID）| 说明 |
|---------|-----------|--------------|------|
| **OAK-D Pro W** | `12D0C1E7D1AB466C09BD9AE6427D5240` | 自动检测 | OAK-D Pro W（宽版）⭐ 当前默认 |
| **OAK-D S2** | `B4C22057DAC5A53595D92CD44D06F91E` | 自动检测 | OAK-D S2 |
| **OAK-D Pro** | 使用 Pro W 密钥 | `14442C105168D9D600` | OAK-D Pro 标准版 |

> **注意**: OAK-D Pro 使用与 Pro W 相同的密钥，但有不同的机器码。

---

## 使用方法

### 方式 1: 自动选择（推荐）

在配置文件中设置默认相机型号：

```yaml
# config/factor_perception_config.yaml
camera:
  model: "OAK-D-PRO-W"  # 设置当前使用的相机型号
```

控制面板会自动读取对应的密钥。

### 方式 2: Launch 参数覆盖

```bash
# 使用 OAK-D Pro
ros2 launch nav24r factor_perception_auto.launch.py \
    camera_model:=OAK-D-PRO \
    key:=14442C105168D9D600

# 使用 OAK-D Pro W（默认）
ros2 launch nav24r factor_perception_auto.launch.py \
    camera_model:=OAK-D-PRO-W

# 使用 OAK-D S2
ros2 launch nav24r factor_perception_auto.launch.py \
    camera_model:=OAK-D-S2 \
    key:=B4C22057DAC5A53595D92CD44D06F91E
```

### 方式 3: 控制面板切换

在控制面板启动时，系统会提示选择相机型号，自动使用对应的密钥。

---

## 配置文件位置

密钥配置存储在：
- `config/factor_perception_config.yaml` - 主配置文件
- `factor_perception_auto.launch.py` - Launch 默认值
- `launch/nav24r_full.launch.py` - 完整系统 Launch
- `launch/factor_perception_isolated.launch.py` - 隔离架构 Launch

---

## 快速参考

### 当前默认配置

```yaml
相机型号: OAK-D-PRO-W
密钥: 12D0C1E7D1AB466C09BD9AE6427D5240
```

### 切换到其他相机

只需更改 `camera_model` 参数，密钥会自动匹配：

```bash
# OAK-D Pro
camera_model:=OAK-D-PRO

# OAK-D S2  
camera_model:=OAK-D-S2
```

---

## 硬件绑定原理

Factor Perception 的密钥机制：

1. **硬件绑定** - 密钥与相机硬件序列号绑定
2. **型号特定** - 每个相机型号有唯一的密钥
3. **无需保密** - 密钥只能在对应硬件上使用
4. **自动验证** - SDK 启动时自动验证密钥与硬件匹配

---

## 相关文档

- [Factor Perception User Guide (PDF)](../docs/Factor%20Perception%20User%20Guide.pdf)
- [因子空间感知SDK标准版使用手册 (PDF)](../docs/因子空间感知SDK标准版使用手册.pdf)
- [项目 README](../README.md)