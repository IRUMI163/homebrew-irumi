"""
IRUMI インポートシステム (読み込む) 堅牢化検証テスト
"""

import sys
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
import irumi


class TestIrumiImportSystem(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_script_relative_import(self):
        """1. スクリプト位置基準の相対パス解決テスト"""
        sub_dir = os.path.join(self.test_dir, "sub")
        os.makedirs(sub_dir)

        mod_b_path = os.path.join(sub_dir, "mod_b.ir")
        with open(mod_b_path, "w", encoding="utf-8") as f:
            f.write('（メッセージ "mod_b loaded" 覚える）\n')

        mod_a_path = os.path.join(sub_dir, "mod_a.ir")
        with open(mod_a_path, "w", encoding="utf-8") as f:
            f.write('（"mod_b.ir" 読み込む）\n')

        env = irumi.Environment()
        irumi.run_file(mod_a_path, env)
        self.assertEqual(env.get("メッセージ"), "mod_b loaded")

    def test_circular_import_detection(self):
        """2. 循環インポート検出テスト"""
        file_a = os.path.join(self.test_dir, "file_a.ir")
        file_b = os.path.join(self.test_dir, "file_b.ir")

        with open(file_a, "w", encoding="utf-8") as f:
            f.write(f'("{file_b}" 読み込む)\n')

        with open(file_b, "w", encoding="utf-8") as f:
            f.write(f'("{file_a}" 読み込む)\n')

        env = irumi.Environment()
        with self.assertRaises(RuntimeError) as cm:
            irumi.run_file(file_a, env)

        err_str = str(cm.exception)
        self.assertIn("循環インポート", err_str)

    def test_import_error_candidate_paths(self):
        """3. インポートエラー時の探索パス候補表示テスト"""
        env = irumi.Environment()
        with self.assertRaises(RuntimeError) as cm:
            irumi.run_code('（"non_existent_file_xyz" 読み込む）', env)

        err_str = str(cm.exception)
        self.assertIn("探索したパス:", err_str)
        self.assertIn("non_existent_file_xyz", err_str)

    def test_irumi_quest_all_12_files(self):
        """4. irumi_quest 全12ファイルのロードおよび実行テスト"""
        files = [
            "irumi_quest/ui.ir",
            "irumi_quest/player.ir",
            "irumi_quest/monster.ir",
            "irumi_quest/skills.ir",
            "irumi_quest/items.ir",
            "irumi_quest/inventory.ir",
            "irumi_quest/battle.ir",
            "irumi_quest/map_data.ir",
            "irumi_quest/dungeon.ir",
            "irumi_quest/shop.ir",
            "irumi_quest/save.ir",
        ]

        # 11個の個別モジュールのロード検証
        for filepath in files:
            env = irumi.Environment()
            irumi.run_file(filepath, env)

        # main.ir を含む全12ファイルの統合実行検証（入力応答を模倣して正常終了を確認）
        env_main = irumi.Environment()
        inputs = ["1", "テスト勇者", "0"]  # 最初から -> 名前入力 -> 終了
        with patch('builtins.input', side_effect=inputs):
            irumi.run_file("irumi_quest/main.ir", env_main)

        self.assertTrue(env_main.contains("勇者名"))
        self.assertEqual(env_main.get("勇者名"), "テスト勇者")


if __name__ == "__main__":
    unittest.main()
