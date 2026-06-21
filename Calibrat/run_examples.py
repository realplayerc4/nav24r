#!/usr/bin/env python3
"""
运行 Calibrat 目录下所有示例脚本

此脚本会遍历 Calibrat 目录下的所有 .py 文件并依次运行，
每个脚本有超时限制。

注意: 进程组管理功能 (preexec_fn=os.setsid) 仅在 Linux/macOS 上可用，
      Windows 平台不支持此功能。

用法:
    python3 run_examples.py
    python3 run_examples.py --folder IMU
    python3 run_examples.py --timeout 30
"""

import os
import sys
import signal
import glob
import argparse
import time
import subprocess
import platform


parser = argparse.ArgumentParser()
parser.add_argument(
    "--folder",
    type=str,
    default="",
    help="Run all tests in a specific folder. All folders if not specified.",
)
parser.add_argument(
    "--timeout", type=int, default=20, help="Timeout for each example in seconds"
)
parser.add_argument(
    "--time-between-examples", type=int, default=3, help="Time between examples in seconds"
)
args = parser.parse_args()

dirs = [dir for dir in os.listdir() if os.path.isdir(dir)]
examples = []
for dir in dirs:
    if "v2_examples" in dir:
        continue
    print(args.folder, dir.lower())

    ex = glob.glob(f"{dir}/**/*.py", recursive=True)

    for example in ex:
        if args.folder and not example.lower().startswith(args.folder.lower()):
            continue
        examples.append(example)

print("Running examples:")
for example in examples:
    print(f"   + {example}")


# 平台判断: preexec_fn=os.setsid 仅在 Linux/macOS 可用
IS_POSIX = platform.system() != "Windows"

executable = sys.executable
print("=" * 100)
for example in examples:
    p = None
    try:
        start_time = time.time()
        command = executable + " " + f"{os.path.abspath(example)}"

        popen_kwargs = {
            "shell": True,
            "cwd": os.path.dirname(example),
            "text": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
        }
        # 仅在 POSIX 系统上使用 os.setsid 创建进程组
        if IS_POSIX:
            popen_kwargs["preexec_fn"] = os.setsid

        p = subprocess.Popen(command, **popen_kwargs)

        p.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        pass

    success = (p.returncode == 0 or p.returncode is None)

    # 终止进程组（仅 POSIX）
    if IS_POSIX:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
    else:
        # Windows: 直接终止进程
        try:
            p.terminate()
        except ProcessLookupError:
            pass

    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    if success:
        print(f"{GREEN}Success running {example}{RESET}")
    else:
        print(f"{RED}Error while in {example}{RESET}")
        print(p.stdout.read() if p.stdout else "")
        print(p.stderr.read() if p.stderr else "")

    time.sleep(args.time_between_examples)

    print("=" * 100)
