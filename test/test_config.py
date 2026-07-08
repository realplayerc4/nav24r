"""nav24r 基本单元测试

测试地图配置加载和 Factor Perception 配置验证。
运行: python -m pytest test/ -v
"""

import json
import os
import sys
import unittest

import yaml


# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")


class TestMapsConfig(unittest.TestCase):
    """测试地图配置文件"""

    def setUp(self):
        self.config_path = os.path.join(CONFIG_DIR, "maps_config.json")

    def test_maps_config_exists(self):
        """maps_config.json 文件存在"""
        self.assertTrue(
            os.path.exists(self.config_path),
            f"地图配置文件不存在: {self.config_path}",
        )

    def test_maps_config_valid_json(self):
        """maps_config.json 是有效的 JSON"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_maps_config_has_required_keys(self):
        """maps_config.json 包含必要字段"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("maps", data, "缺少 'maps' 字段")
        self.assertIn("maps_dir", data, "缺少 'maps_dir' 字段")

    def test_maps_config_entries_have_path(self):
        """每个地图条目包含 path 字段"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for map_id, entry in data.get("maps", {}).items():
            self.assertIn(
                "path", entry, f"地图 '{map_id}' 缺少 'path' 字段"
            )


class TestFactorPerceptionConfig(unittest.TestCase):
    """测试 Factor Perception 配置文件"""

    def setUp(self):
        self.config_path = os.path.join(CONFIG_DIR, "factor_perception_config.yaml")

    def test_config_exists(self):
        """factor_perception_config.yaml 文件存在"""
        self.assertTrue(
            os.path.exists(self.config_path),
            f"配置文件不存在: {self.config_path}",
        )

    def test_config_valid_yaml(self):
        """factor_perception_config.yaml 是有效的 YAML"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIsInstance(data, dict)

    def test_config_has_required_sections(self):
        """配置文件包含必要区域"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        required_keys = ["camera", "ros", "maps", "launch", "paths"]
        for key in required_keys:
            self.assertIn(key, data, f"配置缺少 '{key}' 区域")

    def test_ros_distro_is_jazzy(self):
        """ROS distro 配置为 jazzy"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["ros"]["distro"], "jazzy")

    def test_ros_setup_path_matches_distro(self):
        """ROS setup 路径与 distro 一致"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        distro = data["ros"]["distro"]
        setup_path = data["ros"]["setup_path"]
        self.assertIn(
            distro, setup_path,
            f"setup_path '{setup_path}' 与 distro '{distro}' 不匹配",
        )


class TestNav2Params(unittest.TestCase):
    """测试 Nav2 参数配置"""

    def setUp(self):
        self.config_path = os.path.join(CONFIG_DIR, "nav2_params.yaml")

    def test_nav2_params_exists(self):
        """nav2_params.yaml 文件存在"""
        self.assertTrue(
            os.path.exists(self.config_path),
            f"Nav2 参数文件不存在: {self.config_path}",
        )

    def test_nav2_params_valid_yaml(self):
        """nav2_params.yaml 是有效的 YAML"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIsInstance(data, dict)


class TestDeprecatedFiles(unittest.TestCase):
    """测试已弃用文件已移除"""

    def test_rtabmap_3d_ini_removed(self):
        """rtabmap_3d.ini 已移除（已弃用）"""
        deprecated_path = os.path.join(CONFIG_DIR, "rtabmap_3d.ini")
        self.assertFalse(
            os.path.exists(deprecated_path),
            f"已弃用文件仍存在: {deprecated_path}",
        )


if __name__ == "__main__":
    unittest.main()
