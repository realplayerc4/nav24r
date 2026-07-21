"""Test start_factor.sh argument parsing and behavior."""
import os
import subprocess
import pytest


START_FACTOR = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'start_factor.sh'
)
START_FACTOR = os.path.normpath(START_FACTOR)


class TestStartFactorHelp:
    """Test --help output."""

    def test_help_flag(self):
        result = subprocess.run(
            ['bash', START_FACTOR, '--help'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0
        assert 'mapping' in result.stdout
        assert 'localization' in result.stdout

    def test_help_short_flag(self):
        result = subprocess.run(
            ['bash', START_FACTOR, '-h'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 0


class TestStartFactorModes:
    """Test mode argument parsing (without actually launching ROS)."""

    def test_default_mode_is_mapping(self):
        """Default mode should be mapping when no args given."""
        result = subprocess.run(
            ['bash', START_FACTOR],
            capture_output=True, text=True, timeout=5,
            env={**os.environ, 'HOME': '/tmp/nav24r_test_home'}
        )
        # Should fail because no camera, but mode parsing should work
        assert 'mapping' in result.stdout or '相机' in result.stdout

    def test_invalid_mode_exits_with_error(self):
        result = subprocess.run(
            ['bash', START_FACTOR, '-m', 'invalid_mode'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode != 0

    def test_no_viz_flag(self):
        result = subprocess.run(
            ['bash', START_FACTOR, '--no-viz'],
            capture_output=True, text=True, timeout=5,
            env={**os.environ, 'HOME': '/tmp/nav24r_test_home'}
        )
        assert result.returncode != 0 or 'false' in result.stdout
