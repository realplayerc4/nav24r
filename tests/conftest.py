"""Shared pytest fixtures for nav24r tests."""
import os
import subprocess
import sys
import pytest

NAV24R_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
)
SCRIPTS_DIR = os.path.join(NAV24R_ROOT, 'scripts')
LAUNCH_DIR = os.path.join(NAV24R_ROOT, 'launch')


@pytest.fixture(scope='session')
def nav24r_root():
    return NAV24R_ROOT


@pytest.fixture(scope='session')
def scripts_dir():
    return SCRIPTS_DIR


@pytest.fixture(scope='session')
def launch_dir():
    return LAUNCH_DIR


@pytest.fixture
def run_bash():
    """Run a bash command and return (returncode, stdout, stderr)."""
    def _run(script_path, args=''):
        cmd = f"bash -c 'source /opt/ros/jazzy/setup.bash 2>/dev/null; {script_path} {args}'"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=10,
            cwd=NAV24R_ROOT
        )
        return result.returncode, result.stdout, result.stderr
    return _run
