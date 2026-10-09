#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import unittest
import irumi

class TestIrumiSecurity(unittest.TestCase):
    def test_dunder_attribute_blocking(self):
        env = irumi.Environment()

        # 1. 呼ぶ での dunder 属性アクセスブロック
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('("test" "__class__" 呼ぶ)', env)
        self.assertIn("特殊属性", str(ctx.exception))
        self.assertIn("__class__", str(ctx.exception))

        # 2. 取る での dunder 属性アクセスブロック
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('("test" "__globals__" 取る)', env)
        self.assertIn("特殊属性", str(ctx.exception))
        self.assertIn("__globals__", str(ctx.exception))

        # 3. インスタンスに対する dunder 属性アクセスブロック
        irumi.run_code('（テストクラス （名前） （（名前 名前 覚える）） 設計図）', env)
        irumi.run_code('（obj （"sample" テストクラス 生み出す） 覚える）', env)
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（obj "__subclasses__" 呼ぶ）', env)
        self.assertIn("特殊属性", str(ctx.exception))
        self.assertIn("__subclasses__", str(ctx.exception))

        # 4. インスタンス・辞書属性更新での dunder ブロック
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（obj "__class__" "hacked" 設定）', env)
        self.assertIn("特殊属性", str(ctx.exception))

    def test_safe_mode_restrictions(self):
        # 1. safe_mode=True の環境を作成
        env = irumi.Environment(safe_mode=True)

        # 外部呼出 の禁止
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（"math" "sqrt" 16 外部呼出）', env)
        self.assertIn("安全モード", str(ctx.exception))
        self.assertIn("外部呼出", str(ctx.exception))

        # 危険なPythonモジュール読み込みの禁止
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（"os" 読み込む）', env)
        self.assertIn("安全モード", str(ctx.exception))
        self.assertIn("読み込みは禁止", str(ctx.exception))

        # ファイル操作の禁止
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（"malicious.txt" "hello" 保存）', env)
        self.assertIn("安全モード", str(ctx.exception))

        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（"malicious.txt" 読む）', env)
        self.assertIn("安全モード", str(ctx.exception))

        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（"malicious.txt" "hello" 追記）', env)
        self.assertIn("安全モード", str(ctx.exception))

        # 2. 環境変数 IRUMI_SAFE=1 による安全モード有効化
        os.environ["IRUMI_SAFE"] = "1"
        env_envvar = irumi.Environment()
        self.assertTrue(env_envvar.safe_mode)
        with self.assertRaises(Exception) as ctx:
            irumi.run_code('（"sys" 読み込む）', env_envvar)
        self.assertIn("安全モード", str(ctx.exception))
        del os.environ["IRUMI_SAFE"]

    def test_recursion_limit_trapping(self):
        env = irumi.Environment()
        # 無限再帰関数の定義と実行
        code = """
        （無限再帰 （） （
            （無限再帰）
        ） 関数）
        （無限再帰）
        """
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code(code, env)
        self.assertIn("再帰の深さが上限に達しました。", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
