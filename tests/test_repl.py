import unittest
import irumi

class TestIrumiRepl(unittest.TestCase):
    def test_has_unclosed_brackets_simple(self):
        self.assertFalse(irumi.has_unclosed_brackets("（10に 20を 足す）"))
        self.assertTrue(irumi.has_unclosed_brackets("（10に 20を 足す"))
        self.assertTrue(irumi.has_unclosed_brackets("(+ 1 2"))
        self.assertFalse(irumi.has_unclosed_brackets("(+ 1 2)"))

    def test_has_unclosed_brackets_string_literals(self):
        # カッコを含む文字列リテラル
        self.assertFalse(irumi.has_unclosed_brackets('(")" 書く)'))
        self.assertFalse(irumi.has_unclosed_brackets('（"（" 書く）'))
        self.assertTrue(irumi.has_unclosed_brackets('(")" '))
        # エスケープクォートを含む文字列
        self.assertFalse(irumi.has_unclosed_brackets(r'("\"(" 書く)'))

    def test_has_unclosed_brackets_comments(self):
        # コメント内のカッコ
        self.assertFalse(irumi.has_unclosed_brackets("（10 足す） # (あいうえお"))
        self.assertTrue(irumi.has_unclosed_brackets("（10 足す # （あいうえお"))

    def test_format_repl_value_booleans(self):
        self.assertEqual(irumi.format_repl_value(True), "真")
        self.assertEqual(irumi.format_repl_value(False), "偽")

    def test_format_repl_value_none(self):
        self.assertIsNone(irumi.format_repl_value(None))

    def test_format_repl_value_lists(self):
        self.assertEqual(irumi.format_repl_value([1, 2, 3]), "（1 2 3）")
        self.assertEqual(irumi.format_repl_value([True, False, "hello"]), "（真 偽 hello）")
        self.assertEqual(irumi.format_repl_value([1, [2, True]]), "（1 （2 真））")

    def test_repl_suppressed_commands(self):
        env = irumi.Environment()
        ast_kaku = irumi.parse(irumi.tokenize('("hello" 書く)'))[0]
        self.assertTrue(irumi.is_suppressed_repl_command(ast_kaku))
        res_kaku = irumi.evaluate(ast_kaku, env)
        self.assertEqual(res_kaku, "hello")

        ast_oebiru = irumi.parse(irumi.tokenize('(x 10 覚える)'))[0]
        self.assertTrue(irumi.is_suppressed_repl_command(ast_oebiru))
        res_oebiru = irumi.evaluate(ast_oebiru, env)
        self.assertEqual(res_oebiru, 10)

        # 通常の計算式は抑制されない
        ast_calc = irumi.parse(irumi.tokenize('(10 20 足す)'))[0]
        self.assertFalse(irumi.is_suppressed_repl_command(ast_calc))

if __name__ == '__main__':
    unittest.main()
