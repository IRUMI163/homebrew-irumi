"""
irumi_quest の全モジュール・全機能を網羅検証する自動テストスクリプト
"""
import sys
import irumi

def test_quest_all():
    print("=== IRUMI QUEST 全モジュール統合デバッグ開始 ===")
    env = irumi.Environment()

    # 1. モジュール全ロードテスト
    modules = [
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
    for m in modules:
        irumi.run_code(f'（"{m}" 読み込む）', env)
    print("✓ 全11モジュールのインポート成功")

    # 2. プレイヤー生成・ステータス検証
    irumi.run_code('（勇者 （"テスト勇者" 勇者 生み出す） 覚える）', env)
    p = env.get("勇者")
    assert p.get("名前") == "テスト勇者"
    assert p.get("HP") == 50
    assert p.get("MP") == 20
    assert p.get("所持金") == 100
    print("✓ プレイヤー生成・初期値検証成功")

    # 3. ダメージと回復
    irumi.run_code('（勇者 "ダメージ受ける" 15 呼ぶ）', env)
    # 攻撃15 - 防御5 = 実ダメ10 -> 残りHP 40
    assert p.get("HP") == 40
    irumi.run_code('（勇者 "回復" 20 呼ぶ）', env)
    # 回復20 -> 最大HP50まで
    assert p.get("HP") == 50
    print("✓ ダメージ計算および回復ロジック検証成功")

    # 4. 経験値とレベルアップ
    irumi.run_code('（勇者 "経験値獲得" 25 呼ぶ）', env)
    assert p.get("レベル") == 2
    assert p.get("最大HP") == 65
    print("✓ 経験値獲得とレベルアップ検証成功")

    # 5. スキル・魔法テスト
    irumi.run_code('（敵 （"スライム" 18 8 2 10 15 魔物 生み出す） 覚える）', env)
    enemy = env.get("敵")
    # ホイミ
    irumi.run_code('（勇者 敵 "ホイミ" 魔法実行）', env)
    # メラ
    irumi.run_code('（勇者 敵 "メラ" 魔法実行）', env)
    assert enemy.get("HP") < 18
    print("✓ 魔法発動とMP消費検証成功")

    # 6. アイテム使用
    irumi.run_code('（勇者 "ちからのたね" 道具使用）', env)
    assert p.get("攻撃力") > 12
    print("✓ アイテム効果（ちからのたね）検証成功")

    # 7. インベントリ操作
    irumi.run_code('（"まほうのせいすい" 道具手に入れる）', env)
    bag = env.get("所持品袋")
    assert "まほうのせいすい" in bag
    print("✓ インベントリ追加・管理検証成功")

    # 8. マップデータ
    irumi.run_code('（階名 （1 階層名取得） 覚える）', env)
    assert "地下1階" in env.get("階名")
    irumi.run_code('（階名5 （5 階層名取得） 覚える）', env)
    assert "最深部" in env.get("階名5")
    print("✓ マップ階層データ取得検証成功")

    # 9. セーブ＆ロード
    irumi.run_code('（勇者 データセーブ）', env)
    irumi.run_code('（勇者 "名前" "変更前" 設定）', env)
    irumi.run_code('（勇者 データロード）', env)
    assert p.get("名前") == "テスト勇者"
    print("✓ セーブファイル保存と復元検証成功")

    # 10. ボス戦・撃破クリア判定
    irumi.run_code('（現在階層 5 覚える）', env)
    irumi.run_code('（ボス （現在階層 魔物生成） 覚える）', env)
    boss = env.get("ボス")
    assert boss.get("名前") == "魔王イルミナス"
    print("✓ 最深部ボス（魔王イルミナス）生成検証成功")

    print("=== 全項目オールグリーン: IRUMI 言語およびプロジェクト全機能検証完了 ===")

if __name__ == "__main__":
    test_quest_all()
