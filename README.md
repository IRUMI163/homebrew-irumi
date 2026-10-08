# homebrew-irumi

日本語本来の思考順序（SOV: 目的語 ➔ 動詞）で書けるスクリプト言語 **「IRUMI (イルミ)」** の公式 Homebrew Tap です。

---

## 🚀 インストール方法 (Install)

Mac のターミナルで以下の2行を実行するだけでインストールできます：

```bash
brew tap IRUMI163/irumi
brew install irumi
```

### 動作確認 (Check)
```bash
irumi -v
# => IRUMI v0.1.1
```

---

## ⚡️ 使い方 (Usage)

### 1. 対話モード (REPL)
```bash
irumi 対話
```
```text
irumi> （10に 20を 足す）
=> 30
irumi> （"こんにちは！" を 書く）
こんにちは！
```

### 2. ファイルを実行する
```bash
irumi main.ir
```

### 3. 新規ファイルのひな形を作る
```bash
irumi 作る hello.ir
```

---

## 📖 ライセンス
MIT License
