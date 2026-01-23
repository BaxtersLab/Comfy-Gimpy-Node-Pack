"""
Tests for shared/history.py
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from shared.history import HistoryManager

class TestHistoryManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.history = HistoryManager(temp_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_start_session(self):
        self.history.start_session("test_session")
        self.assertIsNotNone(self.history.session_id)
        self.assertTrue(self.history.session_dir.exists())

    def test_next_step_dir(self):
        self.history.start_session()
        step_dir = self.history.next_step_dir()
        self.assertTrue(step_dir.exists())
        self.assertEqual(self.history.current_step, 1)

    def test_save_step(self):
        self.history.start_session()
        step_dir = self.history.next_step_dir()
        # Create dummy files outside step_dir
        input_file = self.temp_dir / "input.png"
        input_file.write_bytes(b"dummy")
        output_file = self.temp_dir / "output.png"
        output_file.write_bytes(b"dummy")
        
        self.history.save_step(str(input_file), None, str(output_file), {"mode": "test"})
        
        meta_file = step_dir / "meta.json"
        self.assertTrue(meta_file.exists())

    def test_undo_redo(self):
        self.history.start_session()
        step1_dir = self.history.next_step_dir()
        output1 = self.temp_dir / "output1.png"
        output1.write_bytes(b"dummy")
        self.history.save_step(None, None, str(output1), {"mode": "test"})
        
        step2_dir = self.history.next_step_dir()
        output2 = self.temp_dir / "output2.png"
        output2.write_bytes(b"dummy")
        self.history.save_step(None, None, str(output2), {"mode": "test"})
        
        self.assertTrue(self.history.can_undo())
        
        path = self.history.undo()
        self.assertIsNotNone(path)
        self.assertTrue(self.history.can_redo())

if __name__ == '__main__':
    unittest.main()