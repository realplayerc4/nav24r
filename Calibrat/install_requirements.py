#!/usr/bin/env python3
"""nav24r 校准工具依赖安装脚本

安装 IMU 校准和相机数据读取所需的 Python 依赖。
原始版本来自 depthai-python 示例，已简化为仅安装本仓库所需依赖。
"""

import sys
import subprocess


def main():
    dependencies = [
        'depthai',
        'numpy',
        'opencv-python',
    ]

    pip_call = [sys.executable, "-m", "pip"]

    # Check pip is available
    try:
        subprocess.check_call(pip_call + ["--version"])
    except subprocess.CalledProcessError:
        raise RuntimeError(
            "pip 不可用，请先安装 pip: https://pip.pypa.io/en/stable/installation/"
        )

    # Check Python 3
    if sys.version_info[0] != 3:
        raise RuntimeError(
            f"需要 Python 3 (检测到: Python {sys.version_info[0]})"
        )

    # Install dependencies
    install_cmd = pip_call + ["install", "-U", "--prefer-binary"] + dependencies
    print(f"安装依赖: {' '.join(dependencies)}")
    subprocess.check_call(install_cmd)
    print("✅ 依赖安装完成")


if __name__ == "__main__":
    main()
