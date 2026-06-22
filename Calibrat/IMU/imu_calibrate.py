#!/usr/bin/env python3
"""
BNO086 IMU 校准脚本 - 支持多种相机姿态

相机姿态说明：
- upright: 相机直立，Z轴垂直向上（默认）
- flat_front: 相机躺平，镜头朝上，X轴垂直
- flat_back: 相机躺平，镜头朝下，X轴垂直
- flat_left: 相机侧躺，Y轴垂直
- flat_right: 相机侧躺，Y轴垂直
"""
import depthai as dai
import numpy as np
import time
import argparse

def collect_imu_data(duration_sec=5, sample_rate=100):
    """收集静止状态下的IMU数据"""
    print(f'收集 {duration_sec} 秒 IMU 数据，请保持相机静止...')

    with dai.Pipeline() as pipeline:
        imu = pipeline.create(dai.node.IMU)
        imu.enableIMUSensor(dai.IMUSensor.ACCELEROMETER_UNCALIBRATED, sample_rate)
        imu.enableIMUSensor(dai.IMUSensor.GYROSCOPE_UNCALIBRATED, sample_rate)
        imu.setBatchReportThreshold(1)
        imu.setMaxBatchReports(10)

        imu_q = imu.out.createOutputQueue(maxSize=50, blocking=False)

        pipeline.start()
        time.sleep(0.5)

        acc_data = []
        gyro_data = []

        start_time = time.time()
        while time.time() - start_time < duration_sec:
            try:
                imuData = imu_q.get()
                for pkt in imuData.packets:
                    acc = pkt.acceleroMeter
                    gyro = pkt.gyroscope
                    acc_data.append([acc.x, acc.y, acc.z])
                    gyro_data.append([gyro.x, gyro.y, gyro.z])
            except Exception:
                pass

        pipeline.stop()

    return np.array(acc_data), np.array(gyro_data)

def detect_orientation(acc_mean):
    """自动检测相机姿态"""
    abs_acc = np.abs(acc_mean)
    gravity_axis = np.argmax(abs_acc)

    if gravity_axis == 0:  # X轴垂直
        if acc_mean[0] > 0:
            return 'flat_front'  # 镜头朝上
        else:
            return 'flat_back'   # 镜头朝下
    elif gravity_axis == 1:  # Y轴垂直
        if acc_mean[1] > 0:
            return 'flat_left'
        else:
            return 'flat_right'
    else:  # Z轴垂直
        return 'upright'

def compute_calibration(acc_data, gyro_data, orientation='upright', gravity=9.81):
    """计算校准参数"""

    acc_mean = np.mean(acc_data, axis=0)
    acc_std = np.std(acc_data, axis=0)
    gyro_mean = np.mean(gyro_data, axis=0)
    gyro_std = np.std(gyro_data, axis=0)

    # 根据姿态确定重力作用轴
    gravity_config = {
        'upright':      {'axis': 2, 'sign': 1},  # Z轴向上
        'flat_front':   {'axis': 0, 'sign': 1},  # X轴向上（镜头朝上）
        'flat_back':    {'axis': 0, 'sign': -1}, # X轴向下（镜头朝下）
        'flat_left':    {'axis': 1, 'sign': 1},  # Y轴向上
        'flat_right':   {'axis': 1, 'sign': -1}, # Y轴向下
    }

    config = gravity_config.get(orientation, gravity_config['upright'])
    gravity_axis = config['axis']
    gravity_sign = config['sign']

    # 计算校准矩阵
    acc_calibration = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]

    for i in range(3):
        if i == gravity_axis:
            # 重力轴：偏置 = -mean + gravity * sign
            acc_calibration[i][3] = -acc_mean[i] + gravity * gravity_sign
        else:
            # 其他轴：偏置 = -mean（归零）
            acc_calibration[i][3] = -acc_mean[i]

    # 陀螺仪校准矩阵（所有轴归零）
    gyro_calibration = [
        [1.0, 0.0, 0.0, -gyro_mean[0]],
        [0.0, 1.0, 0.0, -gyro_mean[1]],
        [0.0, 0.0, 1.0, -gyro_mean[2]],
    ]

    return {
        'acc_mean': acc_mean,
        'acc_std': acc_std,
        'gyro_mean': gyro_mean,
        'gyro_std': gyro_std,
        'acc_calibration': acc_calibration,
        'gyro_calibration': gyro_calibration,
        'detected_orientation': orientation,
        'gravity_axis': gravity_axis,
    }

def print_calibration(calib):
    """打印校准结果"""
    print('\n' + '='*50)
    print('IMU 校准结果')
    print('='*50)

    axis_names = ['X', 'Y', 'Z']
    print(f'\n【检测到的相机姿态】: {calib["detected_orientation"]}')
    print(f'【重力作用轴】: {axis_names[calib["gravity_axis"]]} 轴')

    print('\n【加速度计原始读数】')
    print(f"  平均值: X={calib['acc_mean'][0]:+.4f}, Y={calib['acc_mean'][1]:+.4f}, Z={calib['acc_mean'][2]:+.4f} m/s²")
    print(f"  标准差: X={calib['acc_std'][0]:.4f}, Y={calib['acc_std'][1]:.4f}, Z={calib['acc_std'][2]:.4f} m/s²")

    print('\n【陀螺仪原始读数】')
    print(f"  平均值: X={calib['gyro_mean'][0]:+.4f}, Y={calib['gyro_mean'][1]:+.4f}, Z={calib['gyro_mean'][2]:+.4f} rad/s")
    print(f"  标准差: X={calib['gyro_std'][0]:.4f}, Y={calib['gyro_std'][1]:.4f}, Z={calib['gyro_std'][2]:.4f} rad/s")

    print('\n【加速度计校准矩阵】')
    for row in calib['acc_calibration']:
        print(f"  [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}, {row[3]:+.6f}]")

    print('\n【陀螺仪校准矩阵】')
    for row in calib['gyro_calibration']:
        print(f"  [{row[0]:.6f}, {row[1]:.6f}, {row[2]:.6f}, {row[3]:+.6f}]")
    print()

def apply_calibration(calib, flash=False):
    """应用校准到设备"""
    device = dai.Device()
    calibration_handler = device.readCalibration()

    calibration_handler.setAccelerometerCalibration(calib['acc_calibration'])
    calibration_handler.setGyroscopeCalibration(calib['gyro_calibration'])

    if flash:
        print('\n写入校准数据到设备 EEPROM...')
        device.flashCalibration(calibration_handler)
        print('✓ 校准数据已保存到 EEPROM')
    else:
        print('\n校准数据已更新 (未写入EEPROM，使用 --flash 参数保存)')

    device.close()

def main():
    parser = argparse.ArgumentParser(description='BNO086 IMU 校准工具')
    parser.add_argument('--duration', type=int, default=5, help='数据采集时长(秒)')
    parser.add_argument('--flash', action='store_true', help='将校准数据写入EEPROM')
    parser.add_argument('--gravity', type=float, default=9.81, help='当地重力加速度')
    parser.add_argument('--orientation', type=str, default='auto',
                       choices=['auto', 'upright', 'flat_front', 'flat_back', 'flat_left', 'flat_right'],
                       help='相机姿态 (auto=自动检测)')
    args = parser.parse_args()

    # 收集数据
    acc_data, gyro_data = collect_imu_data(args.duration)

    if len(acc_data) < 100:
        print('错误: 采集数据不足，请延长采集时间')
        return

    # 计算平均值用于姿态检测
    acc_mean = np.mean(acc_data, axis=0)

    # 确定姿态
    if args.orientation == 'auto':
        orientation = detect_orientation(acc_mean)
        print(f'\n自动检测到相机姿态: {orientation}')
    else:
        orientation = args.orientation

    # 计算校准
    calib = compute_calibration(acc_data, gyro_data, orientation, args.gravity)

    # 打印结果
    print_calibration(calib)

    # 应用校准
    apply_calibration(calib, args.flash)

if __name__ == '__main__':
    main()
