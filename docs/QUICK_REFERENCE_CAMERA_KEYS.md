# 📷 相机密钥快速参考

## 🎯 密钥对照表

| 相机型号 | 密钥（Key）| 机器码（MXID）|
|---------|-----------|--------------|
| **OAK-D Pro W** | `12D0C1E7D1AB466C09BD9AE6427D5240` ⭐ 默认 | 自动检测 |
| **OAK-D S2** | `B4C22057DAC5A53595D92CD44D06F91E` | 自动检测 |
| **OAK-D Pro** | 使用 Pro W 密钥 | `14442C105168D9D600` |

## 🚀 快速使用

```bash
# 默认（OAK-D Pro W）
ros2 launch nav24r factor_perception_auto.launch.py

# OAK-D Pro（指定机器码）
ros2 launch nav24r factor_perception_auto.launch.py \
    camera_model:=OAK-D-PRO \
    mxid_or_name:=14442C105168D9D600

# OAK-D S2
ros2 launch nav24r factor_perception_auto.launch.py \
    camera_model:=OAK-D-S2 \
    key:=B4C22057DAC5A53595D92CD44D06F91E
```

详细说明: [camera_keys_guide.md](camera_keys_guide.md)