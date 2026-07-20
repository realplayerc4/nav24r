# Cyclone DDS 配置指南

## 为什么使用 Cyclone DDS？

相比默认的 Fast DDS，Cyclone DDS 在以下方面有显著优势：

| 特性 | Fast DDS | Cyclone DDS | 优势 |
|------|----------|-------------|------|
| **延迟** | 中等 | 低 | ✅ 更适合实时控制 |
| **CPU 占用** | 较高 | 较低 | ✅ 适合嵌入式/RK3588 |
| **内存效率** | 一般 | 优秀 | ✅ 减少内存压力 |
| **多播性能** | 一般 | 优秀 | ✅ 更高效的数据分发 |
| **配置复杂度** | 复杂 | 简单 | ✅ 易于调优 |

**对于机器人导航系统，Cyclone DDS 可以显著提升性能！**

---

## 快速配置步骤

### Step 1: 安装 Cyclone DDS

```bash
sudo apt update
sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp
```

### Step 2: 配置环境变量

#### 方法 1: 手动设置（临时生效）

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/yq/nav24r/config/cyclonedds.xml
```

#### 方法 2: 添加到 bashrc（永久生效）

```bash
# 编辑 bashrc
nano ~/.bashrc

# 在文件末尾添加以下内容：
# Cyclone DDS 配置
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/yq/nav24r/config/cyclonedds.xml

# 保存后重新加载
source ~/.bashrc
```

#### 方法 3: 使用自动化脚本

```bash
cd /home/yq/nav24r
./scripts/setup_cyclonedds.sh
```

---

## 配置文件说明

配置文件位置: `/home/yq/nav24r/config/cyclonedds.xml`

### 关键配置项解释

#### 1. 网络配置
```xml
<NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
<AllowMulticast>true</AllowMulticast>
```
- `auto`: 自动选择最佳网络接口
- `AllowMulticast`: 启用多播提高效率

#### 2. 内存管理
```xml
<Watermarks>
  <WhcHigh>500kB</WhcHigh>
  <WhcLow>200kB</WhcLow>
</Watermarks>
```
- 控制数据缓冲区大小，防止内存溢出
- 适合点云等大数据传输

#### 3. 实时性能
```xml
<Scheduling>
  <InternalThreadPriority>high</InternalThreadPriority>
  <ReceiverThreadPriority>high</ReceiverThreadPriority>
</Scheduling>
```
- 提高线程优先级，改善实时性能

#### 4. 心跳检测
```xml
<HeartbeatInterval>
  <Minimum>1s</Minimum>
  <Maximum>10s</Maximum>
</HeartbeatInterval>
```
- 快速检测节点故障，提高系统可靠性

---

## 验证配置

### 1. 检查当前 DDS 实现

```bash
# 检查环境变量
echo $RMW_IMPLEMENTATION

# 应该输出: rmw_cyclonedds_cpp
```

### 2. 测试 DDS 性能

```bash
# 终端 1: 启动发布者
ros2 run demo_nodes_cpp talker

# 终端 2: 启动订阅者
ros2 run demo_nodes_cpp listener

# 终端 3: 检查话题频率
ros2 topic hz /chatter
```

### 3. 对比 Fast DDS vs Cyclone DDS

```bash
# 使用 Fast DDS
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ros2 topic hz /factor_perception/odom

# 使用 Cyclone DDS
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 topic hz /factor_perception/odom
```

---

## 针对不同场景的配置

### 场景 1: 单机开发（推荐配置）

```xml
<NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
<AllowMulticast>true</AllowMulticast>
<EnableMulticastLoopback>true</EnableMulticastLoopback>
```

### 场景 2: 多机协同（机器人集群）

```xml
<NetworkInterfaceAddress>192.168.1.100</NetworkInterfaceAddress>  <!-- 指定网卡IP -->
<AllowMulticast>true</AllowMulticast>
<EnableMulticastLoopback>false</EnableMulticastLoopback>
```

### 场景 3: RK3588 嵌入式平台

```xml
<Watermarks>
  <WhcHigh>300kB</WhcHigh>  <!-- 降低内存使用 -->
  <WhcLow>100kB</WhcLow>
</Watermarks>
<MaxMessageSize>32768B</MaxMessageSize>  <!-- 减小消息大小 -->
```

---

## 性能调优建议

### 1. 网络优化

```bash
# 检查网络接口
ip addr show

# 优化网络缓冲区
sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.rmem_default=26214400
```

### 2. CPU 亲和性（RK3588）

```bash
# 将 Factor Perception 绑定到大核 (core 4-7)
taskset -c 4-7 ros2 launch factor_perception factor_perception_launch.py

# 将 Nav2 绑定到剩余核心
taskset -c 0-3 ros2 launch nav2_bringup navigation_launch.py
```

### 3. 共享内存传输

Cyclone DDS 支持零拷贝共享内存传输，减少数据复制开销：

```xml
<SharedMemory>
  <Enable>true</Enable>
  <Size>10485760</Size>  <!-- 10MB -->
</SharedMemory>
```

---

## 故障排除

### 问题 1: 节点无法发现

**症状**: `ros2 topic list` 显示话题，但没有数据

**解决方案**:
```bash
# 检查 DDS 发现配置
export ROS_DISCOVERY_SERVER=;  # 清空发现服务器

# 重启节点
```

### 问题 2: 数据延迟高

**解决方案**:
```xml
<!-- 增加缓冲区 -->
<Watermarks>
  <WhcHigh>1MB</WhcHigh>
  <WhcLow>500kB</WhcLow>
</Watermarks>

<!-- 减少心跳间隔 -->
<HeartbeatInterval>
  <Minimum>0.5s</Minimum>
  <Maximum>5s</Maximum>
</HeartbeatInterval>
```

### 问题 3: 内存占用过高

**解决方案**:
```xml
<!-- 减小缓冲区 -->
<Watermarks>
  <WhcHigh>200kB</WhcHigh>
  <WhcLow>100kB</WhcLow>
</Watermarks>

<!-- 减小消息大小 -->
<MaxMessageSize>32768B</MaxMessageSize>
```

---

## 环境变量参考

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `RMW_IMPLEMENTATION` | 指定 DDS 实现 | `rmw_cyclonedds_cpp` |
| `CYCLONEDDS_URI` | 配置文件路径 | `file:///path/to/cyclonedds.xml` |
| `ROS_DOMAIN_ID` | ROS 域 ID（多机器人） | `0` (默认) |

---

## 一键配置命令

```bash
# 完整配置（安装 + 配置）
cd /home/yq/nav24r
./scripts/setup_cyclonedds.sh

# 验证配置
source ~/.bashrc
echo $RMW_IMPLEMENTATION  # 应该输出: rmw_cyclonedds_cpp
```

---

## 推荐配置流程

1. ✅ **安装 Cyclone DDS**
   ```bash
   sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp
   ```

2. ✅ **配置环境变量**
   ```bash
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   export CYCLONEDDS_URI=file:///home/yq/nav24r/config/cyclonedds.xml
   ```

3. ✅ **重启 Factor Perception 和 Nav2**
   ```bash
   # 停止当前运行的节点
   pkill -f factor_perception
   pkill -f nav2

   # 重新启动
   source ~/.bashrc
   ros2 launch factor_perception factor_perception_launch.py ...
   ```

4. ✅ **验证性能提升**
   ```bash
   ros2 topic hz /factor_perception/odom
   ```

---

**配置完成后，你将获得更低的通信延迟和更高的系统性能！** 🚀