"""Test launch file syntax and structure."""
import ast
import os
import sys
import pytest

LAUNCH_DIR = os.path.join(os.path.dirname(__file__), '..', 'launch')


def _load_launch_module(filename):
    """Load a launch file as an AST module and extract the function body."""
    path = os.path.join(LAUNCH_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f'{filename} not found')
    with open(path, 'r') as f:
        source = f.read()
    tree = ast.parse(source, filename=path)
    return path, source, tree


class TestLaunchFileSyntax:
    """All launch files must have valid Python syntax and generate_launch_description."""

    @pytest.mark.parametrize('filename', [
        'nav2.launch.py',
        'nav24r_full.launch.py',
        'factor_perception_isolated.launch.py',
    ])
    def test_valid_syntax(self, filename):
        path, source, tree = _load_launch_module(filename)
        # Check for syntax errors (ast.parse raises SyntaxError)
        assert True  # Reached here means no SyntaxError

    @pytest.mark.parametrize('filename', [
        'nav2.launch.py',
        'nav24r_full.launch.py',
        'factor_perception_isolated.launch.py',
    ])
    def test_has_generate_launch_description(self, filename):
        _, source, tree = _load_launch_module(filename)
        funcs = [node.name for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef)]
        assert 'generate_launch_description' in funcs, (
            f'{filename} missing generate_launch_description()'
        )

    @pytest.mark.parametrize('filename', [
        'nav2.launch.py',
        'nav24r_full.launch.py',
        'factor_perception_isolated.launch.py',
    ])
    def test_all_args_have_descriptions(self, filename):
        """Every DeclareLaunchArgument should have a description."""
        _, source, tree = _load_launch_module(filename)
        # Find all DeclareLaunchArgument keyword arguments
        missing = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if (hasattr(node.func, 'id') and
                        node.func.id == 'DeclareLaunchArgument'):
                    has_desc = any(
                        kw.arg == 'description'
                        for kw in node.keywords
                    )
                    if not has_desc:
                        # Try to get the argument name from positional args
                        name = '<unknown>'
                        if node.args:
                            name = ast.unparse(node.args[0])
                        missing.append(name)
        assert not missing, (
            f'{filename}: DeclareLaunchArgument missing description: {missing}'
        )

    @pytest.mark.parametrize('filename', [
        'nav2.launch.py',
        'nav24r_full.launch.py',
        'factor_perception_isolated.launch.py',
    ])
    def test_no_hardcoded_ros_distro_paths(self, filename):
        """Avoid hardcoded /opt/ros/<distro> paths; use FindPackageShare."""
        _, source, tree = _load_launch_module(filename)
        import re
        hardcoded = re.findall(r'/opt/ros/\w+/setup\.bash', source)
        assert not hardcoded, (
            f'{filename}: hardcoded ROS paths found: {hardcoded}'
        )
