"""
Tests for comfy_extension/io_handlers.py
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from comfy_extension.io_handlers import save_uploaded_image, save_uploaded_mask, load_result_image

class TestIoHandlers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_save_uploaded_image(self):
        data = b"test image data"
        path = save_uploaded_image(data, self.temp_dir)
        self.assertTrue(Path(path).exists())
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), data)

    def test_save_uploaded_mask(self):
        data = b"test mask data"
        path = save_uploaded_mask(data, self.temp_dir)
        self.assertTrue(Path(path).exists())

    def test_load_result_image(self):
        test_file = self.temp_dir / "result.png"
        data = b"result data"
        test_file.write_bytes(data)
        
        result = load_result_image(str(test_file))
        self.assertEqual(result, data)

if __name__ == '__main__':
    unittest.main()