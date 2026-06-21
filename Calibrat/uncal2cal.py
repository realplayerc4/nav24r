"""
IMU 未校准数据转校准数据脚本

使用校准矩阵将未校准的加速度计数据转换为校准数据。
需要 OAK-D 设备连接。

用法:
    python3 uncal2cal.py
"""

import sys

try:
    import depthai as dai
except ImportError:
    print("[ERROR] depthai 库未安装。请运行: pip install depthai")
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    print("[ERROR] numpy 库未安装。请运行: pip install numpy")
    sys.exit(1)


def check_device():
    """检查 OAK-D 设备是否已连接"""
    try:
        device_info = dai.DeviceInfo()
        device = dai.Device(device_info)
        device.close()
        return True
    except Exception as e:
        print(f"[ERROR] 未检测到 OAK-D 设备: {e}")
        print("  请确认:")
        print("  1. OAK-D 设备已通过 USB 连接")
        print("  2. USB 设备权限已正确配置")
        print("  3. 没有其他程序占用设备")
        return False


def main():
    # 检查设备连接
    if not check_device():
        sys.exit(1)

    # 校准矩阵（示例值，应根据实际校准结果替换）
    imu_calibration = [
        [1.0, 0.0, 0.0, 0.125],
        [0.0, 1.0, 0.0, 0.000],
        [0.0, 0.0, 1.0, 0.000],
    ]

    try:
        with dai.Pipeline() as pipeline:
            imu = pipeline.create(dai.node.IMU)
            imu.enableIMUSensor(dai.IMUSensor.ACCELEROMETER_UNCALIBRATED, 100)
            imu_q = imu.out.createOutputQueue(maxSize=10, blocking=False)

            pipeline.start()

            try:
                pkt = imu_q.get().packets[0]
            except Exception as e:
                print(f"[ERROR] 无法获取 IMU 数据: {e}")
                print("  请确认 IMU 传感器正常工作")
                sys.exit(1)

            uncalibrated = np.array([pkt.acceleroMeter.x, pkt.acceleroMeter.y, pkt.acceleroMeter.z])

            calibration = np.array(imu_calibration)
            calibrated = calibration[:, :3] @ uncalibrated + calibration[:, 3]

            print(f"未校准加速度计数据: {uncalibrated}")
            print(f"校准后加速度计数据: {calibrated}")
            print(f"校准矩阵:\n{calibration}")

    except RuntimeError as e:
        print(f"[ERROR] Pipeline 运行失败: {e}")
        print("  可能原因: 设备被其他程序占用或设备固件异常")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生未预期的错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
