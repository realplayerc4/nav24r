import depthai as dai
import numpy as np

imu_calibration = [
    [1.0, 0.0, 0.0, 0.125],
    [0.0, 1.0, 0.0, 0.000],
    [0.0, 0.0, 1.0, 0.000],
]

with dai.Pipeline() as pipeline:
    imu = pipeline.create(dai.node.IMU)
    imu.enableIMUSensor(dai.IMUSensor.ACCELEROMETER_UNCALIBRATED, 100)
    imu_q = imu.out.createOutputQueue(maxSize=10, blocking=False)

    pipeline.start()
    pkt = imu_q.get().packets[0]
    uncalibrated = np.array([pkt.acceleroMeter.x, pkt.acceleroMeter.y, pkt.acceleroMeter.z])

    calibration = np.array(imu_calibration)
    calibrated = calibration[:, :3] @ uncalibrated + calibration[:, 3]

    print(f"未校准加速度计数据: {uncalibrated}")
    print(f"校准后加速度计数据: {calibrated}")
    print(f"校准矩阵:\n{calibration}")
