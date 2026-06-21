#!/usr/bin/env python3
"""
nav24r 依赖安装脚本

安装 nav24r 项目所需的 Python 依赖包。
适用于 ROS2 Jazzy + Ubuntu 24.04 环境。

用法:
    python3 install_requirements.py              # 安装所有依赖
    python3 install_requirements.py --dry_run    # 仅打印命令，不执行
    python3 install_requirements.py --skip_opencv  # 跳过 OpenCV 安装
"""

import platform
import sys
import subprocess
import argparse


def run_command(cmd, dry_run=False):
    """执行或打印命令"""
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return True
    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] 命令执行失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="nav24r 依赖安装脚本")
    parser.add_argument("--dry_run", action="store_true", help="仅打印命令，不执行")
    parser.add_argument("--skip_opencv", action="store_true", help="跳过 OpenCV 安装")
    parser.add_argument("--user", action="store_true", help="使用 --user 模式安装")
    args = parser.parse_args()

    # 检查 Python 版本
    if sys.version_info[0] != 3:
        print(f"[ERROR] 需要 Python 3，当前检测到: Python {sys.version_info[0]}")
        sys.exit(1)

    if sys.version_info[1] < 10:
        print(f"[WARNING] 推荐使用 Python 3.10+，当前: Python {sys.version_info[0]}.{sys.version_info[1]}")

    # 检查 pip
    pip_call = [sys.executable, "-m", "pip"]
    try:
        subprocess.check_call(pip_call + ["--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("[ERROR] pip 未安装或不可用，请先安装 pip")
        sys.exit(1)

    # 构建依赖列表
    dependencies = [
        'pyyaml',
        'requests',
        'numpy',
    ]

    if not args.skip_opencv:
        # aarch64 平台可能需要特殊处理
        if platform.machine() == "aarch64":
            try:
                subprocess.check_call(
                    [sys.executable, "-c", "import numpy, cv2;"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                print("[INFO] OpenCV 已安装，跳过")
            except subprocess.CalledProcessError:
                dependencies.append('opencv-python')
        else:
            dependencies.append('opencv-python')

    # 构建安装命令
    pip_install = pip_call + ["install", "-U"]
    if args.user:
        pip_install.append("--user")
    pip_install.append("--prefer-binary")

    print("=" * 60)
    print("nav24r 依赖安装")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"依赖列表: {', '.join(dependencies)}")
    print("=" * 60)

    # 更新 pip
    print("\n[1/2] 更新 pip...")
    run_command(pip_install + ["pip"], dry_run=args.dry_run)

    # 安装依赖
    print("\n[2/2] 安装 Python 依赖...")
    success = run_command(pip_install + dependencies, dry_run=args.dry_run)

    if success or args.dry_run:
        print("\n[DONE] 依赖安装完成")
    else:
        print("\n[WARNING] 部分依赖安装失败，请检查错误信息")

    # aarch64 提示
    if platform.machine() == "aarch64":
        import os
        openblas = os.environ.get('OPENBLAS_CORE_TYPE')
        if openblas != 'ARMV8':
            print("\n[WARNING] 建议设置 OPENBLAS_CORE_TYPE=ARMV8 以避免 OpenCV 非法指令错误")
            print("  运行: echo 'export OPENBLAS_CORETYPE=ARMV8' >> ~/.bashrc && source ~/.bashrc")


if __name__ == "__main__":
    main()
