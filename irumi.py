#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRUMI (イルミ) 言語インタプリタ - 第5版
日本語語順 (SOV: 目的語 -> 動詞) で書ける、誰でも10分でわかるフル機能スクリプト言語
- 行番号付き親切エラー表示
- スペース不要の日本語トークナイズ
- 未定義変数の安全チェック
"""

import sys
import os
import re
import time
import random
import datetime
import importlib
import unicodedata

try:
    import readline
except ImportError:
    pass


# ==========================================
# 0. 特殊シグナル例外とASTノード
# ==========================================
class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass

class AstList(list):
    """行番号情報を保持するASTリスト"""
    def __init__(self, items=None, line_num=1):
        super().__init__(items or [])
        self.line_num = line_num

class Symbol(str):
    """変数名・識別子を表すシンボル型"""
    pass


# ==========================================
# 1. 命令エイリアスマップ & 助詞定義
# ==========================================
ALIASES = {
    # 算術・結合（数値の加算も、文字・リストの結合もすべて「足す」に統合）
    "+": "足す", "足": "足す", "たす": "足す", "足す": "足す",
    "結合": "足す", "合体": "足す", "くっつける": "足す", "つなげる": "足す",
    "-": "引く", "引": "引く", "ひく": "引く", "引く": "引く",
    "*": "掛ける", "掛": "掛ける", "かける": "掛ける", "掛ける": "掛ける", "×": "掛ける",
    "/": "割る", "割": "割る", "わる": "割る", "割る": "割る", "÷": "割る",
    "%": "余り", "あまり": "余り", "余り": "余り",

    # 比較
    ">": "大", "大きい": "大", "より大きい": "大", "大": "大",
    "<": "小", "小さい": "小", "より小さい": "小", "小": "小",
    ">=": "以上", "以上": "以上",
    "<=": "以下", "以下": "以下",
    "==": "等", "同じ": "等", "等しい": "等", "等": "等",
    "!=": "違う", "異": "違う", "等しくない": "違う", "違う": "違う",

    # 論理
    "かつ": "かつ", "and": "かつ", "&&": "かつ",
    "または": "または", "or": "または", "||": "または",
    "ではない": "ではない", "not": "ではない", "反転": "ではない", "否定": "ではない",

    # 入出力
    "書く": "書く", "出す": "書く", "表示": "書く", "出力": "書く", "print": "書く",
    "ログ": "ログ", "記録": "ログ", "残す": "ログ",
    "聞く": "聞く", "尋ねる": "聞く", "入力": "聞く", "input": "聞く",
    "待つ": "待つ", "待機": "待つ", "sleep": "待つ",

    # 特殊構文
    "定義": "定義", "定": "定義", "設定": "定義", "おぼえる": "定義", "覚える": "定義",
    "もし": "もし", "なら": "もし", "if": "もし",
    "順に": "順に", "実行": "順に", "まとめて": "順に", "ブロック": "順に",
    "関数": "関数", "手順": "関数", "やり方": "関数", "作る": "関数", "def": "関数", "fn": "関数",
    "返す": "返す", "戻す": "返す", "return": "返す",
    "繰り返す": "繰り返す", "くりかえす": "繰り返す", "ループ": "繰り返す", "loop": "繰り返す",
    "抜ける": "抜ける", "break": "抜ける",
    "次へ": "次へ", "continue": "次へ",
    "試す": "試す", "試みる": "試す", "やってみる": "試す", "try": "試す",

    # 設計図（クラス・オブジェクト）
    "設計図": "設計図", "クラス": "設計図", "ひな形": "設計図", "class": "設計図",
    "生み出す": "生み出す", "新規": "生み出す", "new": "生み出す",
    "呼ぶ": "呼ぶ", "呼び出す": "呼ぶ", "メソッド呼出": "呼ぶ", "動かす": "呼ぶ",

    # 高階コレクション操作（map / filter）
    "変換": "変換", "すべて": "変換", "一括変換": "変換", "map": "変換",
    "絞り込む": "絞り込む", "絞り込み": "絞り込む", "抽出": "絞り込む", "残す": "絞り込む", "filter": "絞り込む",

    # モジュール・インポート
    "読み込む": "読み込む", "読込": "読み込む", "つかう": "読み込む", "使う": "読み込む",
    "取り込む": "読み込む", "参照": "読み込む", "インポート": "読み込む", "import": "読み込む",

    # リスト・データ操作
    "リスト": "リスト", "配列": "リスト", "一覧": "リスト",
    "番目": "番目", "目": "番目", "番": "番目",
    "追加": "追加", "足すリスト": "追加",
    "長さ": "長さ", "件数": "長さ", "個数": "長さ", "サイズ": "長さ",
    "並び替える": "並び替える", "整列": "並び替える", "ソート": "並び替える",
    "逆順": "逆順", "ひっくり返す": "逆順",
    "消す": "消す", "削除": "消す", "取り除く": "消す",

    # 辞書 (マップ / 連想配列 / オブジェクト)
    "辞書": "辞書", "連想配列": "辞書", "マップ": "辞書", "オブジェクト": "辞書",
    "取る": "取る", "取得": "取る", "キー値": "取る",
    "キー一覧": "キー一覧", "値一覧": "値一覧",

    # ランダム
    "乱数": "乱数", "ランダム": "乱数", "サイコロ": "乱数",
    "選ぶ": "選ぶ", "抽選": "選ぶ", "おみくじ": "選ぶ",

    # ファイル操作
    "保存": "保存", "書き込む": "保存", "保存する": "保存",
    "読む": "読む", "読み出し": "読む", "開く": "読む",
    "追記": "追記",

    # 文字列操作
    "分ける": "分ける", "分割": "分ける",
    "つなぐ": "つなぐ", "連結": "つなぐ",
    "含む": "含む", "入っている": "含む",
    "置き換える": "置き換える", "置換": "置き換える",

    # 型変換
    "数値化": "数値化", "整数化": "数値化", "数値": "数値化", "int": "数値化",
    "文字化": "文字化", "文字列化": "文字化", "文字": "文字化", "str": "文字化",

    # 制御・終了
    "おわり": "おわり", "終了": "おわり", "やめる": "おわり", "停止": "おわり", "exit": "おわり", "quit": "おわり",

    # 時間
    "いま": "いま", "現在": "いま", "今": "いま",

    # 外部連携
    "外部呼出": "外部呼出", "外部": "外部呼出", "python": "外部呼出",
}

def resolve_cmd(cmd_name):
    return ALIASES.get(cmd_name, cmd_name)

# 自然な助詞のスキップセット
OPTIONAL_PARTICLES = {"を", "に", "へ", "と", "で", "は", "の"}

def is_particle(x):
    return isinstance(x, str) and x in OPTIONAL_PARTICLES

# 構文キーワード（未定義変数エラーから除外する単語）
SYNTAX_KEYWORDS = {
    "なら", "ちがえば", "そうでなければ", "else", "間", "あいだ", "各",
    "失敗したら", "エラーなら", "かならず", "必ず", "最後に",
    "から", "まで", "の各要素を", "各要素", "の中から"
} | set(ALIASES.keys()) | set(ALIASES.values()) | OPTIONAL_PARTICLES


# ==========================================
# 2. 字句解析 (Tokenizer - スペース不要対応＆行番号追跡)
# ==========================================
def tokenize(code: str):
    """
    ソースコードを行番号つきトークンのリストに分解します。
    スペースを空けずに書いた日本語（例: ”こんにちは”を書く / 10に20を足す）も自動で正しく分割します。
    """
    tokens = []
    i = 0
    n = len(code)
    line_num = 1
    
    while i < n:
        ch = code[i]
        
        # 改行
        if ch == '\n':
            line_num += 1
            i += 1
            continue

        # コメント: # または ＃ から行末までスキップ
        if ch in ('#', '＃'):
            while i < n and code[i] != '\n':
                i += 1
            continue
            
        # 空白文字 (全角スペース含む)
        if ch in (' ', '\t', '\r', '\u3000'):
            i += 1
            continue
            
        # カッコ (全角・半角両対応)
        if ch in ('(', '（'):
            tokens.append(('(', '(', line_num))
            i += 1
            continue
        elif ch in (')', '）'):
            tokens.append((')', ')', line_num))
            i += 1
            continue
            
        # 文字列リテラル (半角 " または 全角 ” “)
        if ch in ('"', '”', '“'):
            quote_char = ch
            str_val = []
            str_start_line = line_num
            i += 1
            while i < n:
                c = code[i]
                if c == '\n':
                    line_num += 1
                if c == '\\' and i + 1 < n:
                    next_c = code[i + 1]
                    if next_c == 'n':
                        str_val.append('\n')
                    elif next_c == 't':
                        str_val.append('\t')
                    else:
                        str_val.append(next_c)
                    i += 2
                    continue
                if (quote_char in ('"',) and c == '"') or (quote_char in ('”', '“') and c in ('”', '“')):
                    i += 1
                    break
                str_val.append(c)
                i += 1
            tokens.append(('STR', "".join(str_val), str_start_line))
            continue
            
        # 通常の単語・数値・記号
        start = i
        while i < n:
            c = code[i]
            if c in ('(', '（', ')', '）', '#', '＃', '"', '”', '“', ' ', '\t', '\r', '\n', '\u3000'):
                break
            i += 1
        raw_word = code[start:i]
        
        # NFKC正規化 (全角数字・英字を半角へ)
        norm_word = unicodedata.normalize('NFKC', raw_word)
        
        # 単語の安全な自動分割（助詞境界でのみ分割）
        def split_norm_word(w):
            # 純粋な数値判定
            try:
                if '.' in w:
                    return [('NUM', float(w))]
                return [('NUM', int(w))]
            except ValueError:
                pass

            # 回数表記 (例: 3回 -> 3)
            if w.endswith("回") and len(w) > 1:
                try:
                    return [('NUM', int(w[:-1]))]
                except ValueError:
                    pass

            # 数字 + 助詞 (例: 10に / 10に20を足す / 1から / 5まで)
            m_num = re.match(r'^([0-9]+(?:\.[0-9]+)?)(に|を|から|まで|へ|と|で)(.*)$', w)
            if m_num:
                n_str, p_str, r_str = m_num.groups()
                n_val = float(n_str) if '.' in n_str else int(n_str)
                res = [('NUM', n_val), ('IDENT', Symbol(p_str))]
                if r_str:
                    res.extend(split_norm_word(r_str))
                return res

            # 助詞 + 命令 (例: を書く -> を, 書く / に足す -> に, 足す)
            if len(w) >= 2 and w[0] in ('を', 'に', 'へ', 'と', 'で'):
                p_lead = w[0]
                rest = w[1:]
                if rest in ALIASES or rest in ALIASES.values():
                    return [('IDENT', Symbol(p_lead)), ('IDENT', Symbol(rest))]

            # 真偽値
            if w in ('True', '真', 'はい', '正しい'):
                return [('BOOL', True)]
            elif w in ('False', '偽', 'いいえ', '違う'):
                return [('BOOL', False)]

            return [('IDENT', Symbol(w))]

        for tag, val in split_norm_word(norm_word):
            tokens.append((tag, val, line_num))
        
    return tokens


# ==========================================
# 3. 構文解析 (Parser - 行番号付きAST生成)
# ==========================================
def parse(tokens):
    """
    トークン列を行番号情報付きのAstListに変換します。
    """
    if not tokens:
        return []

    expressions = []
    idx = 0

    def parse_expr():
        nonlocal idx
        if idx >= len(tokens):
            last_line = tokens[-1][2] if tokens else 1
            raise SyntaxError(f"{last_line}行目: プログラムの途中で式が終わっています。カッコの数を確認してください。")

        tag, val, tok_line = tokens[idx]
        idx += 1

        if tag == '(':
            lst = AstList(line_num=tok_line)
            while idx < len(tokens) and tokens[idx][0] != ')':
                lst.append(parse_expr())
            if idx >= len(tokens):
                raise SyntaxError(f"{tok_line}行目: 閉じカッコ ')' または '）' が足りません！")
            idx += 1  # ')' を消費
            return lst
        elif tag == ')':
            raise SyntaxError(
                f"{tok_line}行目: 余分な閉じカッコ ')' または '）' があります！\n"
                f"💡 ヒント: 自動補完などで末尾の閉じカッコが2重「）））」になっていないか確認してください。"
            )
        else:
            return val

    while idx < len(tokens):
        expressions.append(parse_expr())

    return expressions


# ==========================================
# 4. 実行環境 (Environment) と自作関数・設計図
# ==========================================
class UserFunction:
    """IRUMIユーザー定義関数"""
    def __init__(self, name, params, body, closure_env):
        self.name = name
        self.params = params
        self.body = body
        self.closure_env = closure_env

    def call(self, arg_values):
        local_env = Environment(parent=self.closure_env)
        for i, p in enumerate(self.params):
            if i < len(arg_values):
                local_env.set(p, arg_values[i])
            else:
                local_env.set(p, None)
        
        result = None
        try:
            for expr in self.body:
                result = evaluate(expr, local_env)
        except ReturnSignal as ret:
            return ret.value
        return result


class Blueprint:
    """IRUMIクラス（設計図）"""
    def __init__(self, name, params, body, closure_env):
        self.name = name
        self.params = params
        self.body = body
        self.closure_env = closure_env

    def instantiate(self, arg_values):
        inst_env = Environment(parent=self.closure_env)
        for i, p in enumerate(self.params):
            if i < len(arg_values):
                inst_env.set(p, arg_values[i])
            else:
                inst_env.set(p, None)
        
        for expr in self.body:
            evaluate(expr, inst_env)

        return Instance(self, inst_env)


class Instance:
    """IRUMIオブジェクト（設計図から生み出されたもの）"""
    def __init__(self, blueprint, env):
        self.blueprint = blueprint
        self.env = env

    def get(self, name):
        return self.env.get(name)

    def set(self, name, value):
        self.env.set(name, value)

    def __repr__(self):
        return f"<{self.blueprint.name} オブジェクト>"


class Environment:
    def __init__(self, parent=None):
        self.bindings = {}
        self.parent = parent

    def get(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"変数「{name}」が見つかりません。スペルミスがないか確認してください。")

    def set(self, name, value):
        curr = self
        while curr:
            if name in curr.bindings:
                curr.bindings[name] = value
                return
            curr = curr.parent
        self.bindings[name] = value

    def contains(self, name):
        if name in self.bindings:
            return True
        if self.parent:
            return self.parent.contains(name)
        return False


# ==========================================
# 5. 評価器 (Evaluator - 行番号付きエラーハンドリング)
# ==========================================
def evaluate(node, env: Environment):
    # 数値、真偽値
    if isinstance(node, (int, float, bool)):
        return node

    # 文字列リテラルはそのまま値を返す
    if type(node) is str:
        return node

    # シンボル（変数名）なら環境から参照
    if isinstance(node, Symbol):
        if env.contains(node):
            return env.get(node)
        # 構文キーワードならそのままシンボル文字列として扱う
        if node in SYNTAX_KEYWORDS:
            return str(node)
        # 未定義の変数は安全にエラーにする！
        raise NameError(f"変数「{node}」が見つかりません。スペルミスがないか確認してください。")

    # リスト形式の式
    if isinstance(node, list):
        if len(node) == 0:
            return None

        line_num = getattr(node, "line_num", 1)

        try:
            return _evaluate_list(node, env)
        except (ReturnSignal, BreakSignal, ContinueSignal, SystemExit):
            raise
        except Exception as e:
            err_msg = str(e)
            if not err_msg.startswith("[エラー]"):
                raise RuntimeError(f"[エラー] {line_num}行目: {err_msg}")
            raise


def _evaluate_list(node, env: Environment):
    raw_cmd = node[-1]
    
    # 命令が自作関数や設計図の場合
    cmd_candidate = raw_cmd
    if isinstance(raw_cmd, str) and env.contains(raw_cmd):
        val = env.get(raw_cmd)
        if isinstance(val, (UserFunction, Blueprint)):
            cmd_candidate = val

    cmd = resolve_cmd(cmd_candidate) if isinstance(cmd_candidate, str) else cmd_candidate
    raw_args = node[:-1]

    # --------------------------------------------------
    # 特殊構文 1: 変数定義 (おぼえる / 定義 / 設定)
    # --------------------------------------------------
    if cmd == "定義":
        args = [a for a in raw_args if not is_particle(a)]
        if len(args) == 2:
            var_name = args[0]
            if not isinstance(var_name, str):
                raise TypeError(f"変数名には名前（文字列）を指定してください: {var_name}")
            val = evaluate(args[1], env)
            env.set(var_name, val)
            return val
        elif len(args) >= 3:
            # 辞書またはインスタンスの更新 (名簿 "年齢" 21 設定)
            if isinstance(args[0], str) and env.contains(args[0]):
                target_obj = env.get(args[0])
                if isinstance(target_obj, dict):
                    k = evaluate(args[1], env)
                    v = evaluate(args[2], env)
                    target_obj[k] = v
                    return v
                elif isinstance(target_obj, Instance):
                    k = evaluate(args[1], env)
                    v = evaluate(args[2], env)
                    target_obj.set(k, v)
                    return v
            # カッコ省略代入 (名簿 (データ...) 辞書 覚える)
            var_name = args[0]
            val = evaluate(args[1:], env)
            env.set(var_name, val)
            return val
        else:
            raise ValueError("定義には「変数名」と「値」が必要です。例: (点数 80 覚える)")

    # --------------------------------------------------
    # 特殊構文 2: 条件分岐 (もし)
    # --------------------------------------------------
    if cmd == "もし":
        cleaned_args = [a for a in raw_args if a not in ("もし", "なら", "ちがえば", "そうでなければ", "else")]
        if len(cleaned_args) < 2:
            raise ValueError("『もし』には「条件式」と「合致したときの処理」が必要です。")

        cond_expr = cleaned_args[0]
        then_expr = cleaned_args[1]
        else_expr = cleaned_args[2] if len(cleaned_args) >= 3 else None

        def _eval_block(expr):
            if isinstance(expr, list) and expr and all(isinstance(x, list) for x in expr):
                res = None
                for sub in expr:
                    res = evaluate(sub, env)
                return res
            return evaluate(expr, env)

        cond_res = evaluate(cond_expr, env)
        if bool(cond_res):
            return _eval_block(then_expr)
        else:
            return _eval_block(else_expr) if else_expr is not None else None

    # --------------------------------------------------
    # 特殊構文 3: 順次実行 (順に / まとめて / 実行)
    # --------------------------------------------------
    if cmd == "順に":
        result = None
        for expr in raw_args:
            result = evaluate(expr, env)
        return result

    # --------------------------------------------------
    # 特殊構文 4: 関数定義 (関数 / 手順 / やり方)
    # --------------------------------------------------
    if cmd == "関数":
        args = raw_args
        if len(args) == 2:
            params_expr, body_expr = args
            fn_name = "<無名関数>"
        elif len(args) >= 3:
            fn_name = args[0]
            params_expr = args[1]
            body_expr = args[2:]
        else:
            raise ValueError("関数には「引数」と「処理内容」が必要です。")

        params = params_expr if isinstance(params_expr, list) else [params_expr]
        if len(args) >= 3 and len(args[2:]) == 1 and isinstance(args[2], list) and (len(args[2]) > 0 and isinstance(args[2][0], list)):
            body = args[2]
        else:
            body = body_expr if isinstance(body_expr, list) else [body_expr]

        fn = UserFunction(fn_name, params, body, env)
        if len(args) >= 3:
            env.set(fn_name, fn)
        return fn

    # --------------------------------------------------
    # 特殊構文 4B: 設計図（クラス / クラス定義）
    # --------------------------------------------------
    if cmd == "設計図":
        args = raw_args
        class_name = args[0]
        params_expr = args[1] if len(args) >= 2 else []
        body_expr = args[2:] if len(args) >= 3 else []

        params = params_expr if isinstance(params_expr, list) else [params_expr]
        if len(body_expr) == 1 and isinstance(body_expr[0], list) and body_expr[0] and isinstance(body_expr[0][0], list):
            body = body_expr[0]
        else:
            body = body_expr

        bp = Blueprint(class_name, params, body, env)
        env.set(class_name, bp)
        return bp

    # --------------------------------------------------
    # 特殊構文 4C: 生み出す（インスタンス生成 / new）
    # --------------------------------------------------
    if cmd == "生み出す":
        clean_args = [a for a in raw_args if not is_particle(a)]
        if not clean_args:
            raise ValueError("生み出すには対象の設計図（クラス）が必要です。")
        class_target = evaluate(clean_args[-1], env)
        init_args = [evaluate(a, env) for a in clean_args[:-1]]
        if isinstance(class_target, Blueprint):
            return class_target.instantiate(init_args)
        raise TypeError(f"「{clean_args[-1]}」は設計図（クラス）ではありません。")

    # --------------------------------------------------
    # 特殊構文 5: 戻り値 (返す)
    # --------------------------------------------------
    if cmd == "返す":
        args = [a for a in raw_args if not is_particle(a)]
        if not args:
            raise ReturnSignal(None)
        if len(args) == 1:
            val = evaluate(args[0], env)
        else:
            val = evaluate(args, env)
        raise ReturnSignal(val)

    # --------------------------------------------------
    # 特殊構文 6: 繰り返し (ループ)
    # --------------------------------------------------
    if cmd == "繰り返す":
        args = raw_args

        # 範囲ループ (〜から〜まで)
        if "から" in args and "まで" in args:
            from_idx = args.index("から")
            to_idx = args.index("まで")
            start_val = int(evaluate(args[from_idx - 1], env))
            end_val = int(evaluate(args[to_idx - 1], env))
            
            rest_args = args[to_idx + 1:]
            var_name = "番号"
            if "各" in rest_args:
                k_idx = rest_args.index("各")
                var_name = rest_args[k_idx + 1]
                body_expr = rest_args[k_idx + 2]
            elif len(rest_args) >= 2 and isinstance(rest_args[0], str):
                var_name = rest_args[0]
                body_expr = rest_args[1]
            else:
                body_expr = rest_args[0]

            body_list = body_expr if (isinstance(body_expr, list) and body_expr and isinstance(body_expr[0], list)) else [body_expr]

            step = 1 if start_val <= end_val else -1
            last_res = None
            for cur in range(start_val, end_val + step, step):
                env.set(var_name, cur)
                try:
                    for stmt in body_list:
                        last_res = evaluate(stmt, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return last_res

        # リスト巡回 (foreach)
        if "の各要素を" in args or "各要素" in args:
            idx_kw = args.index("の各要素を") if "の各要素を" in args else args.index("各要素")
            list_target = evaluate(args[0], env)
            item_var_name = args[idx_kw + 1]
            body_expr = args[idx_kw + 2]
            body_list = body_expr if (isinstance(body_expr, list) and body_expr and isinstance(body_expr[0], list)) else [body_expr]

            last_res = None
            for item in list_target:
                env.set(item_var_name, item)
                try:
                    for stmt in body_list:
                        last_res = evaluate(stmt, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return last_res

        # 条件ループ (while)
        if "間" in args or "あいだ" in args:
            idx_kw = args.index("間") if "間" in args else args.index("あいだ")
            cond_expr = args[0]
            body_expr = args[idx_kw + 1]
            body_list = body_expr if (isinstance(body_expr, list) and body_expr and isinstance(body_expr[0], list)) else [body_expr]

            last_res = None
            while bool(evaluate(cond_expr, env)):
                try:
                    for stmt in body_list:
                        last_res = evaluate(stmt, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
            return last_res

        # 回数ループ (for N times)
        count_val = evaluate(args[0], env)
        body_expr = args[1]
        body_list = body_expr if (isinstance(body_expr, list) and body_expr and isinstance(body_expr[0], list)) else [body_expr]

        last_res = None
        for _ in range(int(count_val)):
            try:
                for stmt in body_list:
                    last_res = evaluate(stmt, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue
        return last_res

    if cmd == "抜ける":
        raise BreakSignal()

    if cmd == "次へ":
        raise ContinueSignal()

    # --------------------------------------------------
    # 特殊構文 7: エラー処理 (試す / 失敗したら / かならず)
    # --------------------------------------------------
    if cmd == "試す":
        args = raw_args
        fail_kw = "失敗したら" if "失敗したら" in args else ("エラーなら" if "エラーなら" in args else None)
        finally_kw = "かならず" if "かならず" in args else ("必ず" if "必ず" in args else ("最後に" if "最後に" in args else None))

        try_expr = args[0]
        catch_expr = None
        finally_expr = None

        if fail_kw:
            f_idx = args.index(fail_kw)
            if finally_kw and args.index(finally_kw) > f_idx:
                fin_idx = args.index(finally_kw)
                catch_expr = args[f_idx + 1]
                finally_expr = args[fin_idx + 1]
            else:
                catch_expr = args[f_idx + 1]
        elif finally_kw:
            fin_idx = args.index(finally_kw)
            finally_expr = args[fin_idx + 1]

        try:
            try:
                return evaluate(try_expr, env)
            except Exception as e:
                if catch_expr is not None:
                    env.set("エラー内容", str(e))
                    return evaluate(catch_expr, env)
                else:
                    raise e
        finally:
            if finally_expr is not None:
                evaluate(finally_expr, env)

    # --------------------------------------------------
    # 特殊構文 8: 一括変換 (map) & 絞り込み (filter)
    # --------------------------------------------------
    if cmd in ("変換", "絞り込む"):
        clean_args = [a for a in raw_args if not is_particle(a)]
        list_target = evaluate(clean_args[0], env)
        
        if len(clean_args) >= 3:
            var_param = clean_args[1][0] if isinstance(clean_args[1], list) else clean_args[1]
            body_expr = clean_args[2]
        else:
            var_param = "x"
            body_expr = clean_args[1]

        if isinstance(body_expr, list) and len(body_expr) == 1 and isinstance(body_expr[0], list):
            body_expr = body_expr[0]

        res_list = []
        for item in list_target:
            item_env = Environment(parent=env)
            item_env.set(var_param, item)
            val = evaluate(body_expr, item_env)
            if cmd == "変換":
                res_list.append(val)
            elif cmd == "絞り込む":
                if bool(val):
                    res_list.append(item)
        return res_list

    # --------------------------------------------------
    # 特殊構文 9: インポート (読み込む / つかう)
    # --------------------------------------------------
    if cmd == "読み込む":
        args = [a for a in raw_args if not is_particle(a)]
        target = evaluate(args[0], env)
        if isinstance(target, str) and (os.path.exists(target) or os.path.exists(target + ".ir")):
            filepath = target if os.path.exists(target) else target + ".ir"
            with open(filepath, 'r', encoding='utf-8') as f:
                sub_code = f.read()
            sub_tokens = tokenize(sub_code)
            sub_asts = parse(sub_tokens)
            sub_res = None
            for ast in sub_asts:
                sub_res = evaluate(ast, env)
            return sub_res

        try:
            mod = importlib.import_module(str(target))
            env.set(str(target), mod)
            return mod
        except ImportError:
            raise FileNotFoundError(f"ファイルまたはPythonモジュール「{target}」が見つかりませんでした。")

    # --------------------------------------------------
    # 自作関数 / 設計図の実行
    # --------------------------------------------------
    if isinstance(cmd, UserFunction):
        clean_args = [a for a in raw_args if not is_particle(a)]
        eval_args = [evaluate(a, env) for a in clean_args]
        return cmd.call(eval_args)

    # --------------------------------------------------
    # 通常組み込み関数の実行
    # --------------------------------------------------
    clean_args = [a for a in raw_args if not is_particle(a)]
    eval_args = [evaluate(a, env) for a in clean_args]

    # --- メソッド呼び出し (呼ぶ / 動かす) ---
    if cmd == "呼ぶ":
        target = eval_args[0]
        method_name = str(eval_args[1])
        m_args = eval_args[2:]
        
        if isinstance(target, Instance):
            fn = target.get(method_name)
            if isinstance(fn, UserFunction):
                return fn.call(m_args)
            raise TypeError(f"「{method_name}」は関数ではありません。")
        
        py_method = getattr(target, method_name)
        if callable(py_method):
            return py_method(*m_args)
        return py_method

    # --- 算術・結合 ---
    elif cmd == "足す":
        if not eval_args:
            return 0
        res = eval_args[0]
        for x in eval_args[1:]:
            if isinstance(res, str) or isinstance(x, str):
                res = str(res) + str(x)
            elif isinstance(res, list) and isinstance(x, list):
                res = res + x
            else:
                res = res + x
        return res

    elif cmd == "引く":
        if len(eval_args) == 1:
            return -eval_args[0]
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res - x
        return res

    elif cmd == "掛ける":
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res * x
        return res

    elif cmd == "割る":
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res / x
        return res

    elif cmd == "余り":
        return eval_args[0] % eval_args[1]

    # --- 比較 ---
    elif cmd == "大":
        return eval_args[0] > eval_args[1]
    elif cmd == "小":
        return eval_args[0] < eval_args[1]
    elif cmd == "以上":
        return eval_args[0] >= eval_args[1]
    elif cmd == "以下":
        return eval_args[0] <= eval_args[1]
    elif cmd == "等":
        a, b = eval_args[0], eval_args[1]
        if a == b:
            return True
        if isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)):
            return str(a) == str(b)
        return False
    elif cmd == "違う":
        a, b = eval_args[0], eval_args[1]
        if a == b:
            return False
        if isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)):
            return str(a) != str(b)
        return True

    # --- 論理演算 ---
    elif cmd == "かつ":
        return all(bool(x) for x in eval_args)
    elif cmd == "または":
        return any(bool(x) for x in eval_args)
    elif cmd == "ではない":
        return not bool(eval_args[0])

    # --- 入出力 ---
    elif cmd == "書く":
        output = " ".join(str(x) for x in eval_args)
        print(output)
        return output

    elif cmd == "ログ":
        output = " ".join(str(x) for x in eval_args)
        print(f"［ログ］ {output}")
        return output

    elif cmd == "聞く":
        prompt = str(eval_args[0]) if eval_args else ""
        user_input = input(prompt)
        norm_in = unicodedata.normalize('NFKC', user_input).strip()
        try:
            if '.' in norm_in:
                return float(norm_in)
            return int(norm_in)
        except ValueError:
            return user_input

    elif cmd == "待つ":
        sec = eval_args[0]
        time.sleep(sec)
        return sec

    # --- リスト（配列）操作 ---
    elif cmd == "リスト":
        return eval_args

    elif cmd == "番目":
        lst = eval_args[0]
        idx_num = int(eval_args[1])
        return lst[idx_num]

    elif cmd == "追加":
        lst = eval_args[0]
        val = eval_args[1]
        if isinstance(lst, list):
            lst.append(val)
            return lst
        raise TypeError("追加できるのはリストだけです。")

    elif cmd == "長さ":
        return len(eval_args[0])

    elif cmd == "並び替える":
        return sorted(eval_args[0])

    elif cmd == "逆順":
        return list(reversed(eval_args[0]))

    elif cmd == "消す":
        lst = eval_args[0]
        idx_num = int(eval_args[1])
        return lst.pop(idx_num)

    # --- 辞書（連想配列 / オブジェクト） ---
    elif cmd == "辞書":
        d = {}
        items = eval_args[0] if (len(eval_args) == 1 and isinstance(eval_args[0], list)) else eval_args
        if items and all(isinstance(x, list) and len(x) == 2 for x in items):
            for k, v in items:
                d[k] = v
        elif len(items) % 2 == 0:
            for i in range(0, len(items), 2):
                d[items[i]] = items[i + 1]
        else:
            for item in items:
                if isinstance(item, list) and len(item) == 2:
                    d[item[0]] = item[1]
        return d

    elif cmd == "取る":
        target = eval_args[0]
        key = eval_args[1]
        if isinstance(target, dict):
            return target.get(key)
        elif isinstance(target, Instance):
            return target.get(str(key))
        elif isinstance(target, list):
            return target[int(key)]
        return getattr(target, str(key), None)

    elif cmd == "キー一覧":
        return list(eval_args[0].keys())

    elif cmd == "値一覧":
        return list(eval_args[0].values())

    # --- ランダム（乱数・おみくじ） ---
    elif cmd == "乱数":
        min_v = int(eval_args[0])
        max_v = int(eval_args[1])
        return random.randint(min_v, max_v)

    elif cmd == "選ぶ":
        return random.choice(eval_args[0])

    # --- ファイル操作 ---
    elif cmd == "保存":
        filename = str(eval_args[0])
        content = str(eval_args[1])
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    elif cmd == "読む":
        filename = str(eval_args[0])
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()

    elif cmd == "追記":
        filename = str(eval_args[0])
        content = str(eval_args[1])
        with open(filename, 'a', encoding='utf-8') as f:
            f.write(content)
        return True

    # --- 文字列操作 ---
    elif cmd == "分ける":
        target_str = str(eval_args[0])
        sep = str(eval_args[1])
        return target_str.split(sep)

    elif cmd == "つなぐ":
        target_list = eval_args[0]
        sep = str(eval_args[1])
        return sep.join(str(x) for x in target_list)

    elif cmd == "含む":
        return str(eval_args[1]) in str(eval_args[0])

    elif cmd == "置き換える":
        return str(eval_args[0]).replace(str(eval_args[1]), str(eval_args[2]))

    # --- 型変換 ---
    elif cmd == "数値化":
        val_str = str(eval_args[0])
        if '.' in val_str:
            return float(val_str)
        return int(val_str)

    elif cmd == "文字化":
        return str(eval_args[0])

    # --- 制御・終了 ---
    elif cmd == "おわり":
        msg = eval_args[0] if eval_args else None
        if msg:
            print(msg)
        sys.exit(0)

    # --- 時間 ---
    elif cmd == "いま":
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- 外部呼出 (Python直接呼出) ---
    elif cmd == "外部呼出":
        mod_name = str(eval_args[0])
        fn_name = str(eval_args[1])
        call_args = eval_args[2:]
        
        if isinstance(mod_name, str):
            mod = importlib.import_module(mod_name)
        else:
            mod = mod_name
        py_fn = getattr(mod, fn_name)
        return py_fn(*call_args)

    else:
        # 末尾が命令でない場合はデータリストとして解釈
        try:
            return [evaluate(x, env) for x in node]
        except Exception:
            raise RuntimeError(f"命令「{raw_cmd}」の意味がわかりませんでした。スペルやエイリアスを確認してください。")


# ==========================================
# 6. プログラム実行ランタイム & CLI
# ==========================================
VERSION = "1.0.0"

TEMPLATE_CODE = """# ============================================
# IRUMI プログラム
# ============================================

（"こんにちは、IRUMI！" を 書く）

（名前 （"あなたのお名前は？: " 聞く） 覚える）
（（"ようこそ、" 名前 足す "さん！" 足す） 書く）
"""

def run_code(code: str, env=None):
    if env is None:
        env = Environment()
    tokens = tokenize(code)
    ast_list = parse(tokens)
    result = None
    for ast in ast_list:
        result = evaluate(ast, env)
    return result


def start_repl():
    """対話型シェル (REPL) - 複数行入力＆キーボードヒストリ対応"""
    print("=" * 48)
    print(" IRUMI (イルミ) 対話モード へようこそ！")
    print(" 終了するには '終了' または 'exit' と入力してください")
    print("=" * 48)
    env = Environment()
    
    buffer = []
    
    while True:
        try:
            prompt = "irumi> " if not buffer else " ...>  "
            line = input(prompt)
            
            # 空行判定（バッファが空のときはスキップ）
            if not buffer and not line.strip():
                continue
            if not buffer and line.strip() in ("exit", "終了", "quit"):
                print("またね！")
                break
                
            buffer.append(line)
            full_code = "\n".join(buffer)
            
            # カッコの深さを確認（まだ閉じていなければ次の行を待つ）
            open_count = sum(full_code.count(c) for c in ('(', '（'))
            close_count = sum(full_code.count(c) for c in (')', '）'))
            
            if open_count > close_count:
                continue
            
            # 実行
            code_to_run = full_code
            buffer = []
            res = run_code(code_to_run, env)
            if res is not None:
                print(f"=> {res}")
        except KeyboardInterrupt:
            print("\n（入力をキャンセルしました）")
            buffer = []
        except EOFError:
            print("\nまたね！")
            break
        except Exception as e:
            buffer = []
            print(e)


def show_help():
    print(f"""IRUMI (イルミ) 言語 - バージョン {VERSION}
日本語語順スクリプト言語 (SOV: 目的語 -> 動詞)

使用方法 (Usage):
  irumi [ファイル名.ir]                   : ファイルを実行 (Run file)
  irumi run / 実行 <ファイル名>           : ファイルを実行 (Run file)
  irumi repl / 対話                       : 対話型シェルを起動 (Interactive REPL)
  irumi new / 作る <ファイル名>           : 新しい.irファイルを生成 (Create new template)
  irumi -c <コード>                       : 1行コードを即座に実行 (Eval inline code)
  irumi -v / --version / バージョン       : バージョンを表示 (Show version)
  irumi -h / --help / 使い方              : このヘルプを表示 (Show help)
""")


def main():
    args = sys.argv[1:]
    
    # 引数なし: 対話モード起動
    if not args:
        start_repl()
        return

    first = args[0]

    # バージョン表示
    if first in ("-v", "--version", "version", "バージョン", "版"):
        print(f"IRUMI v{VERSION}")
        return

    # ヘルプ表示
    if first in ("-h", "--help", "help", "使い方", "ヘルプ"):
        show_help()
        return

    # 対話モード
    if first in ("repl", "対話", "shell"):
        start_repl()
        return

    # インライン実行 (-c または -e)
    if first in ("-c", "-e", "eval") and len(args) >= 2:
        inline_code = args[1]
        try:
            env = Environment()
            run_code(inline_code, env)
        except Exception as e:
            print(e)
        return

    # 新規ファイル作成 (new / 作る / 新規)
    if first in ("new", "create", "作る", "新規") and len(args) >= 2:
        target_name = args[1]
        if not target_name.endswith(".ir"):
            target_name += ".ir"
        if os.path.exists(target_name):
            print(f"[エラー] ファイル「{target_name}」は既に存在します。")
            return
        with open(target_name, 'w', encoding='utf-8') as f:
            f.write(TEMPLATE_CODE)
        print(f"✨ 新しいIRUMIファイルを作成しました: {target_name}")
        print(f"実行方法: irumi {target_name}")
        return

    # ファイル実行 (run / 実行 <ファイル名> または直接 <ファイル名>)
    filename = args[1] if (first in ("run", "実行") and len(args) >= 2) else first

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            code = f.read()
        env = Environment()
        run_code(code, env)
    except FileNotFoundError:
        print(f"[エラー] ファイル「{filename}」が見つかりませんでした。")
    except SystemExit:
        pass
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
