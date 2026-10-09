#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRUMI (イルミ) 言語インタプリタ - 第6版
日本語語順 (SOV: 目的語 -> 動詞) で書ける、誰でも10分でわかるフル機能スクリプト言語
- 行番号付き親切エラー表示
- スペース不要の日本語トークナイズ
- 未定義変数の安全チェック
- 堅牢なインポートシステム（循環参照防止・探索パス表示）
- 安全モード（危険機能無効化: 外部呼出・OSモジュール・ファイルI/O遮断）
- 数学演算・標準関数の拡充
- 複数代入・分割代入・辞書リテラル拡張
- REPL (対話モード) の堅牢化と出力整形
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
# 0. 特殊シグナル例外・ASTノード
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
# 0B. インポート管理と安全モード
# ==========================================
IMPORT_STACK = []

def get_search_candidates(target: str):
    search_dirs = []
    if IMPORT_STACK:
        current_file_dir = os.path.dirname(os.path.abspath(IMPORT_STACK[-1]))
        if current_file_dir and current_file_dir not in search_dirs:
            search_dirs.append(current_file_dir)
    cwd = os.getcwd()
    if cwd not in search_dirs:
        search_dirs.append(cwd)

    if target.endswith(".ir"):
        target_vars = [target]
    else:
        target_vars = [target, target + ".ir"]

    candidates = []
    for d in search_dirs:
        for v in target_vars:
            cand = os.path.normpath(os.path.join(d, v))
            if cand not in candidates:
                candidates.append(cand)

    return candidates

def resolve_import_path(target: str):
    candidates = get_search_candidates(target)
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None

def is_dunder(name: str) -> bool:
    s = str(name)
    return s.startswith("__") and s.endswith("__")

def is_safe_mode_active() -> bool:
    return os.environ.get("IRUMI_SAFE", "0") in ("1", "true", "True") or "--safe" in sys.argv


# ==========================================
# 1. 命令エイリアスマップ & 助詞定義
# ==========================================
ALIASES = {
    # 算術・結合
    "+": "足す", "足": "足す", "たす": "足す", "足す": "足す",
    "結合": "足す", "合体": "足す", "くっつける": "足す", "つなげる": "足す",
    "-": "引く", "引": "引く", "ひく": "引く", "引く": "引く",
    "*": "掛ける", "掛": "掛ける", "かける": "掛ける", "掛ける": "掛ける", "×": "掛ける",
    "/": "割る", "割": "割る", "わる": "割る", "割る": "割る", "÷": "割る",
    "%": "余り", "あまり": "余り", "余り": "余り",
    "//": "整除", "整除": "整除",
    "^": "べき乗", "**": "べき乗", "べき乗": "べき乗",
    "絶対値": "絶対値", "abs": "絶対値",
    "四捨五入": "四捨五入", "round": "四捨五入",
    "最大": "最大", "max": "最大",
    "最小": "最小", "min": "最小",

    # 比較
    ">": "大", "大きい": "大", "より大きい": "大", "大": "大",
    "<": "小", "小さい": "小", "より小さい": "小", "小": "小",
    ">=": "以上", "以上": "以上",
    "<=": "以下", "以下": "以下",
    "==": "等", "同じ": "等", "等しい": "等", "等": "等",
    "===": "厳密等", "厳密等": "厳密等", "厳密に等しい": "厳密等",
    "!=": "違う", "異": "違う", "等しくない": "違う", "違う": "違う",

    # 論理
    "かつ": "かつ", "and": "かつ", "&&": "かつ",
    "または": "または", "or": "または", "||": "または",
    "ではない": "ではない", "not": "ではない", "反転": "ではない", "否定": "ではない",

    # 入出力
    "書く": "書く", "出す": "書く", "表示": "書く", "出力": "書く", "print": "書く",
    "ログ": "ログ", "記録": "ログ",
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
    if type(cmd_name) is Symbol:
        return ALIASES.get(cmd_name, cmd_name)
    return cmd_name

OPTIONAL_PARTICLES = {"を", "に", "へ", "と", "で", "は", "の"}

def is_particle(x):
    return type(x) is Symbol and x in OPTIONAL_PARTICLES

def is_block(x):
    return isinstance(x, list) and len(x) > 0 and all(isinstance(e, list) for e in x)

def as_body(x):
    return list(x) if is_block(x) else [x]

BUILTIN_COMMANDS = {
    "足す", "引く", "掛ける", "割る", "余り", "整除", "べき乗", "絶対値", "四捨五入", "最大", "最小",
    "大", "小", "以上", "以下", "等", "厳密等", "違う",
    "かつ", "または", "ではない",
    "書く", "ログ", "聞く", "待つ",
    "定義", "設定", "もし", "順に", "関数", "返す",
    "繰り返す", "抜ける", "次へ", "試す",
    "設計図", "生み出す", "呼ぶ",
    "変換", "絞り込む", "読み込む",
    "リスト", "長さ", "番目", "追加", "並び替える", "逆順", "消す",
    "辞書", "取る", "キー一覧", "値一覧",
    "乱数", "選ぶ", "保存", "読む", "追記", "分ける", "つなぐ",
    "含む", "置き換える", "数値化", "文字化", "おわり", "いま", "外部呼出"
}

SYNTAX_KEYWORDS = {
    "なら", "ちがえば", "そうでなければ", "else", "間", "あいだ", "各",
    "失敗したら", "エラーなら", "かならず", "必ず", "最後に",
    "から", "まで", "の各要素を", "各要素", "の中から"
} | set(ALIASES.keys()) | set(ALIASES.values()) | OPTIONAL_PARTICLES


# ==========================================
# 2. 字句解析 (Tokenizer)
# ==========================================
def tokenize(code: str):
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
            
        # 空白文字
        if ch in (' ', '\t', '\r', '\u3000'):
            i += 1
            continue
            
        # カッコ
        if ch in ('(', '（'):
            tokens.append(('(', '(', line_num))
            i += 1
            continue
        elif ch in (')', '）'):
            tokens.append((')', ')', line_num))
            i += 1
            continue
            
        # 文字列リテラル
        if ch in ('"', '”', '“'):
            quote_char = ch
            str_val = []
            str_start_line = line_num
            i += 1
            closed = False
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
                    closed = True
                    break
                str_val.append(c)
                i += 1
            if not closed:
                raise SyntaxError(f"{str_start_line}行目: 閉じられていない文字列リテラルがあります。末尾に「\"」または「”」を付けてください。")
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
        
        # NFKC正規化
        norm_word = unicodedata.normalize('NFKC', raw_word)
        
        def split_norm_word(w):
            # 記号系（コロン、アロー）
            if w in (':', '：'):
                return [('IDENT', Symbol(':'))]
            if w in ('=>', '->'):
                return [('IDENT', Symbol(w))]

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

            # 真偽値
            if w in ('True', '真', 'はい', '正しい'):
                return [('BOOL', True)]
            elif w in ('False', '偽', 'いいえ'):
                return [('BOOL', False)]

            # 数字 + 助詞 (例: 10に / 1から)
            m_num = re.match(r'^([0-9]+(?:\.[0-9]+)?)(に|を|から|まで|へ|と|で)(.*)$', w)
            if m_num:
                n_str, p_str, r_str = m_num.groups()
                n_val = float(n_str) if '.' in n_str else int(n_str)
                res = [('NUM', n_val), ('IDENT', Symbol(p_str))]
                if r_str:
                    res.extend(split_norm_word(r_str))
                return res

            # 助詞 + 命令 (例: を書く -> を, 書く)
            if len(w) >= 2 and w[0] in ('を', 'に', 'へ', 'と', 'で'):
                p_lead = w[0]
                rest = w[1:]
                if rest in ALIASES or rest in ALIASES.values():
                    return [('IDENT', Symbol(p_lead)), ('IDENT', Symbol(rest))]

            # コロン終端 (例: 名前: -> 名前, :)
            if len(w) >= 2 and (w.endswith(':') or w.endswith('：')):
                prefix = w[:-1]
                return [('IDENT', Symbol(prefix)), ('IDENT', Symbol(':'))]

            # 助詞終端 (例: 空に -> 空, に / 無を -> 無, を)
            m_part = re.match(r'^(None|無|空)(に|を|から|まで|へ|と|で)(.*)$', w)
            if m_part:
                k_str, p_str, r_str = m_part.groups()
                res = [('IDENT', Symbol(k_str)), ('IDENT', Symbol(p_str))]
                if r_str:
                    res.extend(split_norm_word(r_str))
                return res

            return [('IDENT', Symbol(w))]

        for tag, val in split_norm_word(norm_word):
            tokens.append((tag, val, line_num))
        
    return tokens


# ==========================================
# 3. 構文解析 (Parser)
# ==========================================
def parse(tokens):
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
                raise SyntaxError(f"{tok_line}行目: 対応する閉じカッコ ')' または '）' がありません。カッコが正しく閉じられているか確認してください。")
            idx += 1  # ')' を消費
            return lst
        elif tag == ')':
            raise SyntaxError(
                f"{tok_line}行目: 対応する開きカッコのない余分な閉じカッコ ')' または '）' があります！\n"
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

    def call(self, arg_values, name=None):
        disp_name = name or self.name
        if len(arg_values) != len(self.params):
            raise TypeError(f"命令『{disp_name}』には引数が{len(self.params)}個必要ですが、{len(arg_values)}個しか渡されていません。")

        local_env = Environment(parent=self.closure_env)
        for i, p in enumerate(self.params):
            local_env.define(p, arg_values[i])
        
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

    def instantiate(self, arg_values, name=None):
        disp_name = name or self.name
        if len(arg_values) != len(self.params):
            raise TypeError(f"命令『{disp_name}』には引数が{len(self.params)}個必要ですが、{len(arg_values)}個しか渡されていません。")

        # インスタンス専用の環境を作成
        inst_env = Environment(parent=self.closure_env, is_instance_env=True)
        for i, p in enumerate(self.params):
            inst_env.define(p, arg_values[i])
        
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
    def __init__(self, parent=None, safe_mode=None, is_instance_env=False):
        self.bindings = {}
        self.parent = parent
        self.is_instance_env = is_instance_env
        if safe_mode is not None:
            self.safe_mode = safe_mode
        elif parent is not None:
            self.safe_mode = parent.safe_mode
        else:
            self.safe_mode = is_safe_mode_active()

        # デフォルトで空/無/NoneをNoneとして定義
        if parent is None:
            self.bindings["None"] = None
            self.bindings["無"] = None
            self.bindings["空"] = None

    def get(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"変数「{name}」が見つかりません。スペルミスがないか確認してください。")

    def define(self, name, value):
        self.bindings[name] = value

    def set(self, name, value):
        curr = self
        while curr:
            if name in curr.bindings:
                curr.bindings[name] = value
                return
            # インスタンス環境境界に到達した場合、グローバル変数を汚染せずインスタンスフィールドとして束縛
            if curr.is_instance_env:
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
# 4B. 分割代入と辞書構築の補助関数
# ==========================================
def _assign_destructured(target, val, env):
    if isinstance(target, list):
        if not isinstance(val, (list, tuple)):
            val = [val]
        for i, t in enumerate(target):
            v_val = val[i] if i < len(val) else None
            _assign_destructured(t, v_val, env)
    elif isinstance(target, (str, Symbol)):
        env.set(target, val)
    else:
        raise TypeError(f"変数名には名前（文字列）を指定してください: {target}")


def build_dictionary_from_tokens(items, env):
    """
    コロン : やアロー => を含むトークン列から辞書を構築します。
    キーが裸の識別子（シンボル）の場合は、変数参照せず文字列リテラルとして扱います。
    """
    d = {}
    i = 0
    while i < len(items):
        if i + 2 < len(items) and isinstance(items[i+1], Symbol) and items[i+1] in (':', '：', '=>', '->', '='):
            k = str(items[i])
            v = evaluate(items[i+2], env)
            d[k] = v
            i += 3
        elif i + 1 < len(items):
            k = str(items[i]) if isinstance(items[i], Symbol) else evaluate(items[i], env)
            v = evaluate(items[i+1], env)
            d[k] = v
            i += 2
        else:
            i += 1
    return d


# ==========================================
# 4C. 出力フォーマッタ & 日本語エラーメッセージ変換
# ==========================================
def format_display_value(val):
    """
    IRUMIの値を自然な日本語表記に整形します。
    """
    if val is None:
        return "なし"
    if isinstance(val, bool):
        return "真" if val else "偽"
    if isinstance(val, list):
        items = [format_display_value(x) for x in val]
        return f"（{' '.join(items)}）"
    return str(val)


def format_repl_value(val):
    """REPL用の整形"""
    if val is None:
        return None
    if isinstance(val, bool):
        return "真" if val else "偽"
    if isinstance(val, list):
        items = [format_repl_value(x) for x in val]
        str_items = [str(x) if x is not None else "空" for x in items]
        return f"（{' '.join(str_items)}）"
    return str(val)


TYPE_NAME_JA = {
    'int': '数値（整数）',
    'float': '数値（小数）',
    'str': '文字列',
    'list': 'リスト',
    'dict': '辞書',
    'bool': '真偽値',
    'tuple': 'タプル',
    'set': '集合',
    'NoneType': 'なし（None）',
}

def ja_type_name(obj_or_name):
    if isinstance(obj_or_name, type):
        name = obj_or_name.__name__
    elif isinstance(obj_or_name, str):
        name = obj_or_name
    else:
        name = type(obj_or_name).__name__
    return TYPE_NAME_JA.get(name, name)

def translate_exception(e):
    if isinstance(e, ZeroDivisionError):
        return "0で割ることはできません。"
    if isinstance(e, IndexError):
        return "指定された番号はリストの範囲外です。"
    if isinstance(e, TypeError):
        msg = str(e)
        if any('\u3000' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff' for c in msg):
            return msg

        m = re.search(r"unsupported operand type\(s\) for ([^:]+): '([^']+)' and '([^']+)'", msg)
        if m:
            op, t1, t2 = m.groups()
            return f"型が正しくありません。演算『{op}』は「{ja_type_name(t1)}」と「{ja_type_name(t2)}」の間では計算できません。"

        m2 = re.search(r"can only concatenate (\w+) \(not \"(\w+)\"\) to (\w+)", msg)
        if m2:
            t1, t2, _ = m2.groups()
            return f"型が正しくありません。「{ja_type_name(t1)}」には「{ja_type_name(t1)}」のみ結合できます（「{ja_type_name(t2)}」が渡されました）。"

        if "not iterable" in msg:
            m3 = re.search(r"'([^']+)' object is not iterable", msg)
            t = m3.group(1) if m3 else "対象"
            return f"型が正しくありません。「{ja_type_name(t)}」は繰り返し処理（リストやループ）に対応していません。"

        if "not subscriptable" in msg:
            m4 = re.search(r"'([^']+)' object is not subscriptable", msg)
            t = m4.group(1) if m4 else "対象"
            return f"型が正しくありません。「{ja_type_name(t)}」は『番目』や『取る』での要素取得に対応していません。"

        return f"型が正しくありません: {msg}"
    return str(e)

BUILTIN_REQUIRED_ARGS = {
    "引く": 1,
    "掛ける": 1,
    "割る": 2,
    "余り": 2,
    "整除": 2,
    "べき乗": 2,
    "絶対値": 1,
    "四捨五入": 1,
    "最大": 1,
    "最小": 1,
    "大": 2,
    "小": 2,
    "以上": 2,
    "以下": 2,
    "等": 2,
    "厳密等": 2,
    "違う": 2,
    "かつ": 1,
    "または": 1,
    "ではない": 1,
    "待つ": 1,
    "呼ぶ": 2,
    "番目": 2,
    "追加": 2,
    "長さ": 1,
    "並び替える": 1,
    "逆順": 1,
    "消す": 2,
    "取る": 2,
    "キー一覧": 1,
    "値一覧": 1,
    "乱数": 2,
    "選ぶ": 1,
    "保存": 2,
    "読む": 1,
    "追記": 2,
    "分ける": 2,
    "つなぐ": 2,
    "含む": 2,
    "置き換える": 3,
    "数値化": 1,
    "文字化": 1,
}


# ==========================================
# 5. 評価器 (Evaluator)
# ==========================================
def evaluate(node, env: Environment):
    if node is None:
        return None

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
        # 未定義の変数は安全にエラーにする
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
        except RecursionError:
            raise RuntimeError("再帰の深さが上限に達しました。")
        except Exception as e:
            err_msg = str(e)
            if "再帰の深さが上限に達しました。" in err_msg:
                raise
            if not err_msg.startswith("[エラー]"):
                translated = translate_exception(e)
                raise RuntimeError(f"[エラー] {line_num}行目: {translated}")
            raise


def _evaluate_list(node, env: Environment):
    # 辞書糖衣構文の検出 (名前: "アリス" 等)
    if any(isinstance(x, Symbol) and x in (':', '：', '=>', '->', '=') for x in node):
        return build_dictionary_from_tokens(node, env)

    if len(node) > 1 and type(node[0]) is Symbol:
        head_res = resolve_cmd(node[0])
        if head_res in ("もし", "試す"):
            tail_res = resolve_cmd(node[-1]) if type(node[-1]) is Symbol else None
            if tail_res != head_res:
                node = AstList(list(node[1:]) + [node[0]], line_num=getattr(node, "line_num", 1))

    raw_cmd = node[-1]
    
    # 命令が自作関数や設計図の場合
    cmd_candidate = raw_cmd
    if type(raw_cmd) is Symbol and env.contains(raw_cmd):
        val = env.get(raw_cmd)
        if isinstance(val, (UserFunction, Blueprint)):
            cmd_candidate = val

    cmd = resolve_cmd(cmd_candidate) if type(cmd_candidate) is Symbol else cmd_candidate
    raw_args = node[:-1]

    # --------------------------------------------------
    # 特殊構文 1: 変数定義 (おぼえる / 定義 / 設定)
    # --------------------------------------------------
    if cmd == "定義":
        args = [a for a in raw_args if not is_particle(a)]
        if len(args) == 2:
            var_target = args[0]
            val = evaluate(args[1], env)
            _assign_destructured(var_target, val, env)
            return val
        elif len(args) >= 3:
            # プロパティ更新 (名簿 "年齢" 21 設定)
            # 末尾がコマンド式でない場合のみプロパティ更新として扱う
            last_token = args[-1]
            is_nested_command = (type(last_token) is Symbol and (last_token in BUILTIN_COMMANDS or last_token in ALIASES or env.contains(last_token)))
            
            if len(args) == 3 and not is_nested_command and isinstance(args[0], (str, Symbol)) and env.contains(args[0]):
                target_obj = env.get(args[0])
                if isinstance(target_obj, dict):
                    k = evaluate(args[1], env)
                    if is_dunder(str(k)):
                        raise PermissionError(f"特殊属性「{k}」へのアクセスは禁止されています。")
                    val = evaluate(args[2], env)
                    target_obj[k] = val
                    return val
                elif isinstance(target_obj, Instance):
                    k = evaluate(args[1], env)
                    if is_dunder(str(k)):
                        raise PermissionError(f"特殊属性「{k}」へのアクセスは禁止されています。")
                    val = evaluate(args[2], env)
                    target_obj.set(k, val)
                    return val

            # カッコ省略代入 (変数 式... 覚える)
            var_target = args[0]
            val = evaluate(args[1:], env)
            _assign_destructured(var_target, val, env)
            return val
        else:
            raise ValueError("定義には「変数名」と「値」が必要です。例: (点数 80 覚える)")

    # --------------------------------------------------
    # 特殊構文 2: 条件分岐 (もし)
    # --------------------------------------------------
    if cmd == "もし":
        cleaned_args = [a for a in raw_args if not (type(a) is Symbol and a in ("もし", "なら", "ちがえば", "そうでなければ", "else"))]
        if len(cleaned_args) < 2:
            raise TypeError(f"命令『{raw_cmd}』には引数が2個必要ですが、{len(cleaned_args)}個渡されました。")

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
        if len(args) == 2:
            body = as_body(body_expr)
        else:
            raw_body = args[2] if len(args) == 3 else args[2:]
            body = as_body(raw_body)

        fn = UserFunction(fn_name, params, body, env)
        if len(args) >= 3:
            env.define(fn_name, fn)
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
        raw_body = body_expr[0] if len(body_expr) == 1 else body_expr
        body = as_body(raw_body)

        bp = Blueprint(class_name, params, body, env)
        env.define(class_name, bp)
        return bp

    # --------------------------------------------------
    # 特殊構文 4C: 生み出す（インスタンス生成 / new）
    # --------------------------------------------------
    if cmd == "生み出す":
        clean_args = [a for a in raw_args if not is_particle(a)]
        if not clean_args:
            raise TypeError(f"命令『{raw_cmd}』には引数が1個必要ですが、0個渡されました。")
        class_target = evaluate(clean_args[-1], env)
        init_args = [evaluate(a, env) for a in clean_args[:-1]]
        if isinstance(class_target, Blueprint):
            return class_target.instantiate(init_args, name=class_target.name)
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

        def _has_kw(kw):
            return any(type(a) is Symbol and a == kw for a in args)

        def _index_kw(kw):
            for i, a in enumerate(args):
                if type(a) is Symbol and a == kw:
                    return i
            return -1

        # 範囲ループ (〜から〜まで)
        if _has_kw("から") and _has_kw("まで"):
            from_idx = _index_kw("から")
            to_idx = _index_kw("まで")
            start_val = int(evaluate(args[from_idx - 1], env))
            end_val = int(evaluate(args[to_idx - 1], env))
            
            rest_args = args[to_idx + 1:]
            var_name = "番号"
            if any(type(a) is Symbol and a == "各" for a in rest_args):
                k_idx = [i for i, a in enumerate(rest_args) if type(a) is Symbol and a == "各"][0]
                if k_idx + 2 < len(rest_args):
                    var_name = rest_args[k_idx + 1]
                    body_expr = rest_args[k_idx + 2]
                elif k_idx - 1 >= 0 and k_idx + 1 < len(rest_args):
                    var_name = rest_args[k_idx - 1]
                    body_expr = rest_args[k_idx + 1]
                else:
                    body_expr = rest_args[-1]
            elif len(rest_args) >= 2 and isinstance(rest_args[0], (str, Symbol)):
                var_name = rest_args[0]
                body_expr = rest_args[1]
            else:
                body_expr = rest_args[0]

            body_list = as_body(body_expr)
            step = 1 if start_val <= end_val else -1
            last_res = None
            env_bindings = env.bindings
            if len(body_list) == 1:
                stmt = body_list[0]
                for cur in range(start_val, end_val + step, step):
                    env_bindings[var_name] = cur
                    try:
                        last_res = evaluate(stmt, env)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        continue
            else:
                for cur in range(start_val, end_val + step, step):
                    env_bindings[var_name] = cur
                    try:
                        for stmt in body_list:
                            last_res = evaluate(stmt, env)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        continue
            return last_res

        # リスト巡回 (foreach)
        if _has_kw("の各要素を") or _has_kw("各要素"):
            idx_kw = _index_kw("の各要素を") if _has_kw("の各要素を") else _index_kw("各要素")
            list_target = evaluate(args[0], env)
            item_var_name = args[idx_kw + 1]
            body_expr = args[idx_kw + 2]
            body_list = as_body(body_expr)

            last_res = None
            env_bindings = env.bindings
            if len(body_list) == 1:
                stmt = body_list[0]
                for item in list_target:
                    env_bindings[item_var_name] = item
                    try:
                        last_res = evaluate(stmt, env)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        continue
            else:
                for item in list_target:
                    env_bindings[item_var_name] = item
                    try:
                        for stmt in body_list:
                            last_res = evaluate(stmt, env)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        continue
            return last_res

        # 条件ループ (while)
        if _has_kw("間") or _has_kw("あいだ"):
            idx_kw = _index_kw("間") if _has_kw("間") else _index_kw("あいだ")
            cond_expr = args[0]
            body_expr = args[idx_kw + 1]
            body_list = as_body(body_expr)

            last_res = None
            if len(body_list) == 1:
                stmt = body_list[0]
                while bool(evaluate(cond_expr, env)):
                    try:
                        last_res = evaluate(stmt, env)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        continue
            else:
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
        body_list = as_body(body_expr)

        last_res = None
        count_int = int(count_val)
        if len(body_list) == 1:
            stmt = body_list[0]
            for _ in range(count_int):
                try:
                    last_res = evaluate(stmt, env)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue
        else:
            for _ in range(count_int):
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
        fail_kw = next((a for a in args if type(a) is Symbol and a in ("失敗したら", "エラーなら")), None)
        finally_kw = next((a for a in args if type(a) is Symbol and a in ("かならず", "必ず", "最後に")), None)

        def _eval_block(expr):
            if isinstance(expr, list) and expr and all(isinstance(x, list) for x in expr):
                res = None
                for sub in expr:
                    res = evaluate(sub, env)
                return res
            return evaluate(expr, env)

        f_idx = args.index(fail_kw) if fail_kw else None
        fin_idx = args.index(finally_kw) if finally_kw else None

        first_kw_idx = f_idx if f_idx is not None else fin_idx
        if first_kw_idx is not None:
            try_parts = args[:first_kw_idx]
        else:
            try_parts = args
        try_expr = try_parts if len(try_parts) > 1 else (try_parts[0] if try_parts else None)

        catch_expr = None
        if f_idx is not None:
            end_c_idx = fin_idx if fin_idx is not None and fin_idx > f_idx else len(args)
            c_parts = [a for a in args[f_idx + 1:end_c_idx] if not (type(a) is Symbol and a in ("エラー", "例外"))]
            catch_expr = c_parts if len(c_parts) > 1 else (c_parts[0] if c_parts else None)

        finally_expr = None
        if fin_idx is not None:
            fin_parts = args[fin_idx + 1:]
            finally_expr = fin_parts if len(fin_parts) > 1 else (fin_parts[0] if fin_parts else None)

        try:
            try:
                return _eval_block(try_expr) if try_expr is not None else None
            except (ReturnSignal, BreakSignal, ContinueSignal):
                raise
            except Exception as e:
                if catch_expr is not None:
                    env.set("エラー内容", translate_exception(e))
                    return _eval_block(catch_expr)
                else:
                    raise e
        finally:
            if finally_expr is not None:
                _eval_block(finally_expr)

    # --------------------------------------------------
    # 特殊構文 8: 一括変換 (map) & 絞り込み (filter)
    # --------------------------------------------------
    if cmd in ("変換", "絞り込む"):
        clean_args = [a for a in raw_args if not is_particle(a)]
        if len(clean_args) < 2:
            raise TypeError(f"命令『{raw_cmd}』には引数が2個必要ですが、{len(clean_args)}個渡されました。")
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
            item_env.define(var_param, item)
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
        if not args:
            raise TypeError(f"命令『{raw_cmd}』には引数が1個必要ですが、0個渡されました。")
        target = evaluate(args[0], env)

        if isinstance(target, str):
            resolved_path = resolve_import_path(target)
            if resolved_path:
                return run_file(resolved_path, env)

        if env.safe_mode:
            raise PermissionError(f"安全モード（--safe）ではPythonモジュール「{target}」の読み込みは禁止されています。")

        try:
            mod = importlib.import_module(str(target))
            env.set(str(target), mod)
            return mod
        except (ImportError, ValueError):
            candidates = get_search_candidates(str(target))
            searched_str = "\n".join(f"  - {p}" for p in candidates)
            raise FileNotFoundError(
                f"ファイルまたはPythonモジュール「{target}」が見つかりませんでした。\n"
                f"探索したパス:\n{searched_str}"
            )

    # --------------------------------------------------
    # 自作関数 / 設計図の実行・未定義チェック
    # --------------------------------------------------
    if isinstance(cmd, UserFunction):
        clean_args = [a for a in raw_args if not is_particle(a)]
        disp_name = cmd.name if cmd.name != "<無名関数>" else str(raw_cmd)
        eval_args = [evaluate(a, env) for a in clean_args]
        return cmd.call(eval_args, name=disp_name)

    if isinstance(cmd, Blueprint):
        raise TypeError(f"設計図「{cmd.name}」は直接実行できません。「生み出す」を使ってください。")

    if type(raw_cmd) is Symbol and not env.contains(raw_cmd) and cmd not in BUILTIN_COMMANDS:
        raise RuntimeError(f"命令「{raw_cmd}」の意味がわかりませんでした。スペルやエイリアスを確認してください。")

    # --- 短絡論理演算 (かつ / または) ---
    if cmd == "かつ":
        clean_args = [a for a in raw_args if not is_particle(a)]
        if len(clean_args) < 1:
            raise TypeError(f"命令『{raw_cmd}』には引数が1個必要ですが、0個渡されました。")
        for a in clean_args:
            if not bool(evaluate(a, env)):
                return False
        return True

    if cmd == "または":
        clean_args = [a for a in raw_args if not is_particle(a)]
        if len(clean_args) < 1:
            raise TypeError(f"命令『{raw_cmd}』には引数が1個必要ですが、0個渡されました。")
        for a in clean_args:
            if bool(evaluate(a, env)):
                return True
        return False

    # --------------------------------------------------
    # 通常組み込み関数の実行
    # --------------------------------------------------
    clean_args = [a for a in raw_args if not is_particle(a)]

    if isinstance(cmd, str) and cmd in BUILTIN_REQUIRED_ARGS:
        req_count = BUILTIN_REQUIRED_ARGS[cmd]
        if len(clean_args) < req_count:
            raise TypeError(f"命令『{raw_cmd}』には引数が{req_count}個必要ですが、{len(clean_args)}個しか渡されていません。")

    eval_args = [evaluate(a, env) for a in clean_args]

    # --- メソッド呼び出し (呼ぶ / 動かす) ---
    if cmd == "呼ぶ":
        target = eval_args[0]
        method_name = str(eval_args[1])
        m_args = eval_args[2:]

        if is_dunder(method_name):
            raise PermissionError(f"特殊属性「{method_name}」へのアクセスは禁止されています。")

        if isinstance(target, Instance):
            fn = target.get(method_name)
            if isinstance(fn, UserFunction):
                return fn.call(m_args, name=method_name)
            raise TypeError(f"「{method_name}」は関数ではありません。")
        
        py_method = getattr(target, method_name)
        if callable(py_method):
            return py_method(*m_args)
        return py_method

    # --- 算術・結合 ---
    elif cmd == "足す":
        if len(eval_args) == 2:
            a, b = eval_args[0], eval_args[1]
            a_type, b_type = type(a), type(b)
            if a_type is int and b_type is int:
                return a + b
            if a_type is str or b_type is str:
                return str(a) + str(b)
            if a_type is list and b_type is list:
                return a + b
            return a + b
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
        if len(eval_args) == 2:
            return eval_args[0] - eval_args[1]
        elif len(eval_args) == 1:
            return -eval_args[0]
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res - x
        return res

    elif cmd == "掛ける":
        if len(eval_args) == 2:
            return eval_args[0] * eval_args[1]
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res * x
        return res

    elif cmd == "割る":
        if len(eval_args) == 2:
            return eval_args[0] / eval_args[1]
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res / x
        return res

    elif cmd == "余り":
        return eval_args[0] % eval_args[1]

    elif cmd == "整除":
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res // x
        return res

    elif cmd == "べき乗":
        res = eval_args[0]
        for x in eval_args[1:]:
            res = res ** x
        return res

    elif cmd == "絶対値":
        return abs(eval_args[0])

    elif cmd == "四捨五入":
        if len(eval_args) >= 2:
            return round(eval_args[0], int(eval_args[1]))
        return round(eval_args[0])

    elif cmd == "最大":
        if len(eval_args) == 1 and isinstance(eval_args[0], (list, tuple)):
            return max(eval_args[0])
        return max(eval_args)

    elif cmd == "最小":
        if len(eval_args) == 1 and isinstance(eval_args[0], (list, tuple)):
            return min(eval_args[0])
        return min(eval_args)

    # --- 比較 ---
    elif cmd == "等":
        a, b = eval_args[0], eval_args[1]
        if a == b:
            return True
        if isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)) and not isinstance(a, bool) and not isinstance(b, bool):
            return str(a) == str(b)
        return False

    elif cmd == "厳密等":
        a, b = eval_args[0], eval_args[1]
        if a == b and type(a) is type(b):
            return True
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
            return a == b
        return False

    elif cmd == "違う":
        a, b = eval_args[0], eval_args[1]
        if a == b:
            return False
        if isinstance(a, (int, float, str)) and isinstance(b, (int, float, str)) and not isinstance(a, bool) and not isinstance(b, bool):
            return str(a) != str(b)
        return True

    elif cmd == "大":
        return eval_args[0] > eval_args[1]
    elif cmd == "小":
        return eval_args[0] < eval_args[1]
    elif cmd == "以上":
        return eval_args[0] >= eval_args[1]
    elif cmd == "以下":
        return eval_args[0] <= eval_args[1]

    # --- 論理演算 ---
    elif cmd == "ではない":
        return not bool(eval_args[0])

    # --- 入出力 ---
    elif cmd == "書く":
        output = " ".join(format_display_value(x) for x in eval_args)
        print(output)
        return output

    elif cmd == "ログ":
        output = " ".join(format_display_value(x) for x in eval_args)
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
        if any(isinstance(x, Symbol) and x in (':', '：', '=>', '->', '=') for x in raw_args):
            return build_dictionary_from_tokens(raw_args, env)
        items = eval_args[0] if (len(eval_args) == 1 and isinstance(eval_args[0], list)) else eval_args
        d = {}
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
        if is_dunder(str(key)):
            raise PermissionError(f"特殊属性「{key}」へのアクセスは禁止されています。")
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
        if env.safe_mode:
            raise PermissionError("安全モード（--safe）ではファイルの保存（書き込み）は禁止されています。")
        filename = str(eval_args[0])
        content = str(eval_args[1])
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    elif cmd == "読む":
        if env.safe_mode:
            raise PermissionError("安全モード（--safe）ではファイルの読み込みは禁止されています。")
        filename = str(eval_args[0])
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()

    elif cmd == "追記":
        if env.safe_mode:
            raise PermissionError("安全モード（--safe）ではファイルへの追記は禁止されています。")
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
        target = eval_args[0]
        item = eval_args[1]
        if isinstance(target, (list, tuple, set)):
            return item in target
        elif isinstance(target, dict):
            return item in target
        elif isinstance(target, str):
            return str(item) in target
        try:
            return item in target
        except Exception:
            return False

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
        code = 0
        msg = None
        if len(eval_args) == 1:
            if isinstance(eval_args[0], int):
                code = eval_args[0]
            else:
                msg = str(eval_args[0])
        elif len(eval_args) >= 2:
            msg = str(eval_args[0])
            code = int(eval_args[1])
        if msg:
            print(msg)
        sys.exit(code)

    # --- 時間 ---
    elif cmd == "いま":
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- 外部呼出 (Python直接呼出) ---
    elif cmd == "外部呼出":
        if env.safe_mode:
            raise PermissionError("安全モード（--safe）では外部呼出（Python関数の実行）は禁止されています。")
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
        return eval_args + [evaluate(raw_cmd, env)]


# ==========================================
# 6. プログラム実行ランタイム & CLI
# ==========================================
VERSION = "1.0.0"

TEMPLATE_CODE = """# ============================================
# IRUMI プログラム
# ============================================

（"こんにちは、IRUMI！" を 書く）

（名前 （"あなたのお名前は？: " 聞く） 覚える）
（（"ようこそ、" 名前 "さん！" 足す） 書く）
"""

def run_file(filepath: str, env=None, safe_mode=None):
    """
    指定されたIRUMIファイルを読み込み、循環インポートチェックを行いながら実行します。
    """
    abs_path = os.path.abspath(filepath)
    if abs_path in IMPORT_STACK:
        cycle_chain = " -> ".join(IMPORT_STACK + [abs_path])
        raise RuntimeError(f"循環インポート（循環読み込み）が検出されました: {cycle_chain}")

    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"ファイル「{filepath}」が見つかりませんでした。")

    with open(abs_path, 'r', encoding='utf-8') as f:
        code = f.read()

    IMPORT_STACK.append(abs_path)
    try:
        return run_code(code, env, safe_mode=safe_mode)
    finally:
        IMPORT_STACK.pop()


def run_code(code: str, env=None, safe_mode=None):
    if env is None:
        env = Environment(safe_mode=safe_mode)
    elif safe_mode is not None:
        env.safe_mode = safe_mode
    tokens = tokenize(code)
    ast_list = parse(tokens)
    result = None
    try:
        for ast in ast_list:
            result = evaluate(ast, env)
    except RecursionError:
        raise RuntimeError("再帰の深さが上限に達しました。")
    return result


def has_unclosed_brackets(code: str) -> bool:
    i = 0
    n = len(code)
    depth = 0

    while i < n:
        ch = code[i]

        # コメント
        if ch in ('#', '＃'):
            while i < n and code[i] != '\n':
                i += 1
            continue

        # 文字列リテラル
        if ch in ('"', '”', '“'):
            quote_char = ch
            i += 1
            while i < n:
                c = code[i]
                if c == '\\' and i + 1 < n:
                    i += 2
                    continue
                if (quote_char == '"' and c == '"') or (quote_char in ('”', '“') and c in ('”', '“')):
                    i += 1
                    break
                i += 1
            continue

        # カッコ
        if ch in ('(', '（'):
            depth += 1
        elif ch in (')', '）'):
            depth -= 1

        i += 1

    return depth > 0


def is_suppressed_repl_command(ast_node):
    """REPLにおいて出力を抑制すべきトップレベルコマンドかを判定します"""
    if isinstance(ast_node, list) and ast_node:
        tail = ast_node[-1]
        resolved = resolve_cmd(tail) if type(tail) is Symbol else None
        if resolved in ("書く", "ログ", "定義", "設定", "おぼえる", "覚える"):
            return True
        head = ast_node[0]
        resolved_h = resolve_cmd(head) if type(head) is Symbol else None
        if resolved_h in ("定義", "設定", "おぼえる", "覚える"):
            return True
    return False


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
            prompt = "irumi> " if not buffer else "... "
            line = input(prompt)
            
            # 空行判定（バッファが空のときはスキップ）
            if not buffer and not line.strip():
                continue
            if not buffer and line.strip() in ("exit", "終了", "quit", "おわり"):
                print("またね！")
                break
                
            buffer.append(line)
            full_code = "\n".join(buffer)
            
            # カッコの深さを確認（未終了なら継続）
            if has_unclosed_brackets(full_code):
                continue
            
            # 実行
            code_to_run = full_code
            buffer = []
            tokens = tokenize(code_to_run)
            ast_list = parse(tokens)
            res = None
            last_ast = ast_list[-1] if ast_list else None
            for ast in ast_list:
                res = evaluate(ast, env)

            # 最上位コマンドが「書く」「定義」等でなければ結果を表示
            if not is_suppressed_repl_command(last_ast):
                formatted = format_repl_value(res)
                if formatted is not None:
                    print(f"=> {formatted}")
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
  irumi --safe <ファイル名>               : 制限実行モードで実行 (Run in safe mode)
""")


def main():
    raw_args = sys.argv[1:]
    safe_mode = is_safe_mode_active()
    args = [a for a in raw_args if a != "--safe"]

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
            env = Environment(safe_mode=safe_mode)
            run_code(inline_code, env)
        except Exception as e:
            sys.stderr.write(f"{e}\n")
            sys.exit(1)
        return

    # 新規ファイル作成 (new / 作る / 新規)
    if first in ("new", "create", "作る", "新規") and len(args) >= 2:
        target_name = args[1]
        if not target_name.endswith(".ir"):
            target_name += ".ir"
        if os.path.exists(target_name):
            sys.stderr.write(f"[エラー] ファイル「{target_name}」は既に存在します。\n")
            sys.exit(1)
        with open(target_name, 'w', encoding='utf-8') as f:
            f.write(TEMPLATE_CODE)
        print(f"新しいIRUMIファイルを作成しました: {target_name}")
        print(f"実行方法: irumi {target_name}")
        return

    # ファイル実行 (run / 実行 <ファイル名> または直接 <ファイル名>)
    filename = args[1] if (first in ("run", "実行") and len(args) >= 2) else first

    try:
        env = Environment(safe_mode=safe_mode)
        run_file(filename, env)
    except FileNotFoundError:
        sys.stderr.write(f"[エラー] ファイル「{filename}」が見つかりませんでした。\n")
        sys.exit(1)
    except SystemExit as se:
        sys.exit(se.code)
    except Exception as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
