import unittest
import irumi

class TestIrumiErrorHandling(unittest.TestCase):
    def setUp(self):
        self.env = irumi.Environment()

    def test_zero_division_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code('（10 0 割る）', self.env)
        self.assertIn("0で割ることはできません。", str(ctx.exception))

    def test_index_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code('（l （1 2） 覚える） （l 5 番目）', self.env)
        self.assertIn("指定された番号はリストの範囲外です。", str(ctx.exception))

    def test_type_error(self):
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code('（"10" 2 引く）', self.env)
        self.assertIn("型が正しくありません", str(ctx.exception))

    def test_unclosed_string_syntax_error(self):
        with self.assertRaises(SyntaxError) as ctx:
            irumi.run_code('（"閉じられていない文字列 を書く）', self.env)
        self.assertIn("閉じられていない文字列リテラルがあります", str(ctx.exception))
        self.assertIn("1行目", str(ctx.exception))

    def test_unclosed_paren_syntax_error(self):
        with self.assertRaises(SyntaxError) as ctx:
            irumi.run_code('（1 2 足す', self.env)
        self.assertIn("対応する閉じカッコ", str(ctx.exception))
        self.assertIn("1行目", str(ctx.exception))

    def test_extra_paren_syntax_error(self):
        with self.assertRaises(SyntaxError) as ctx:
            irumi.run_code('（1 2 足す） ）', self.env)
        self.assertIn("対応する開きカッコ", str(ctx.exception))
        self.assertIn("1行目", str(ctx.exception))

    def test_missing_argument_user_function(self):
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code('（足し算 （a b） （（a b 足す） 返す） 関数） （10 足し算）', self.env)
        self.assertIn("命令『足し算』には引数が2個必要ですが、1個しか渡されていません。", str(ctx.exception))

    def test_missing_argument_builtin(self):
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code('（割る）', self.env)
        self.assertIn("命令『割る』には引数が2個必要ですが、0個しか渡されていません。", str(ctx.exception))

    def test_missing_argument_blueprint(self):
        with self.assertRaises(RuntimeError) as ctx:
            irumi.run_code('（ロボ （名前 型） （） 設計図） （ロボ 生み出す）', self.env)
        self.assertIn("命令『ロボ』には引数が2個必要ですが、0個しか渡されていません。", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
