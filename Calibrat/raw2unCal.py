"""
IMU 原始数据转未校准数据脚本

从 IMU 原始传感器数据，使用设备校准信息中的 IMU-to-Camera 外参矩阵
将数据转换到相机坐标系。
需要 OAK-D 设备连接。

用法:
    python3 raw2unCal.py
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

    try:
        with dai.Pipeline() as pipeline:
            imu = pipeline.create(dai.node.IMU)
            imu.enableIMUSensor(dai.IMUSensor.ACCELEROMETER_RAW, 100)
            imu_q = imu.out.createOutputQueue(maxSize=10, blocking=False)

            try:
                device = pipeline.getDefaultDevice()
                calib = device.readCalibration()
                imu_to_cam = np.array(calib.getImuToCameraExtrinsics(dai.CameraBoardSocket.CAM_A, False))
                R_imu_to_cam = imu_to_cam[:3, :3]
            except Exception as e:
                print(f"[ERROR] 无法读取设备校准信息: {e}")
                print("  请确认设备已完成校准")
                sys.exit(1)

            pipeline.start()

            try:
                pkt = imu_q.get().packets[0]
            except Exception as e:
                print(f"[ERROR] 无法获取 IMU 数据: {e}")
                print("  请确认 IMU 传感器正常工作")
                sys.exit(1)

            raw = np.array([pkt.acceleroMeter.x, pkt.acceleroMeter.y, pkt.acceleroMeter.z])
            uncalibrated = R_imu_to_cam @ raw

            print(f"原始加速度计数据: {raw}")
            print(f"转换后数据 (相机坐标系): {uncalibrated}")
            print(f"IMU-to-Camera 旋转矩阵:\n{R_imu_to_cam}")

    except RuntimeError as e:
        print(f"[ERROR] Pipeline 运行失败: {e}")
        print("  可能原因: 设备被其他程序占用或设备固件异常")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生未预期的错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
