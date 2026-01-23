"""
Tests for shared/config.py
"""

import unittest
import os
from pathlib import Path
from shared.config import Config, load_config

class TestConfig(unittest.TestCase):
    def test_config_init(self):
        config = Config(host="test", port=9000, workflows_dir="/tmp", temp_dir="/tmp")
        self.assertEqual(config.host, "test")
        self.assertEqual(config.port, 9000)
        self.assertEqual(config.base_url, "http://test:9000/gimp_bridge/")
        self.assertEqual(config.workflows_dir, Path("/tmp"))
        self.assertEqual(config.temp_dir, Path("/tmp"))

    def test_config_invalid_port(self):
        with self.assertRaises(ValueError):
            Config(port=70000)

    def test_load_config_defaults(self):
        # Test with no env vars
        config = load_config()
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 8188)

if __name__ == '__main__':
    unittest.main()