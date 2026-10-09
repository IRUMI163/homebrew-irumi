import os
import subprocess
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestIRUMILanguage(unittest.TestCase):
    def test_irumi_full_script(self):
        """test_irumi_full.ir の自動実行テスト"""
        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "irumi.py"),
            os.path.join(PROJECT_ROOT, "test_irumi_full.ir"),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        self.assertEqual(
            result.returncode,
            0,
            f"test_irumi_full.ir failed with exit code {result.returncode}.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        self.assertIn("ALL TESTS PASSED!", result.stdout)

    def test_quest_auto_script(self):
        """test_quest_auto.py の自動実行テスト"""
        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "test_quest_auto.py"),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=PROJECT_ROOT
        )
        self.assertEqual(
            result.returncode,
            0,
            f"test_quest_auto.py failed with exit code {result.returncode}.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )
        self.assertIn("全項目オールグリーン", result.stdout)


if __name__ == "__main__":
    unittest.main()
