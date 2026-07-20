import depthai as dai
import numpy as np

with dai.Pipeline() as pipeline:
    imu = pipeline.create(dai.node.IMU)
    imu.enableIMUSensor(dai.IMUSensor.ACCELEROMETER_RAW, 100)
    imu_q = imu.out.createOutputQueue(maxSize=10, blocking=False)

    device = pipeline.getDefaultDevice()
    calib = device.readCalibration()
    imu_to_cam = np.array(calib.getImuToCameraExtrinsics(dai.CameraBoardSocket.CAM_A, False))
    R_imu_to_cam = imu_to_cam[:3, :3]

    pipeline.start()
    pkt = imu_q.get().packets[0]
    raw = np.array([pkt.acceleroMeter.x, pkt.acceleroMeter.y, pkt.acceleroMeter.z])
    uncalibrated = R_imu_to_cam @ raw
