# realestate-ai-companion

不動産業のAI伴走者 — 公開API × Claude で物件分析・業務再設計を実装するskill群。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## なにこれ

中小不動産会社向けに、**公開データ × AI** で営業エリア戦略・市場分析を支援する Claude Code 用 plugin です。

- **公開データのみ** を扱います（業者ログイン必須サービスは扱いません）
- 集計済みCSVを内蔵しているので、**APIキーなしでも動きます**（再取得時のみキー必要）
- 記事と1:1で対応するskillが増えていきます。**記事↔skillマップ**は [docs/article-skill-map.md](docs/article-skill-map.md) を参照

## インストール

```bash
claude plugin marketplace add etsurouwatanabe-tech/realestate-ai-companion
claude plugin install companion
```

依存パッケージ：

```bash
pip install httpx python-dotenv dbfread
```

## 提供している skill

| skill | 概要 | 関連記事 |
|---|---|---|
| **inheritance-hotspots** v1.0.0 | 東京23区の相続予備軍ホットスポット分析。営業エリアの数値判定 | [N02記事（公開予定）](articles/INDEX.md) |

詳細は各 skill の `SKILL.md` を参照。

## 使い方の例

```
> 「世田谷・大田・目黒の相続予備軍スコアを出して」
→ inheritance-hotspots skill が起動 → 順位・スコア・タイプを返答
```

```
> 「うちは港区中心。隣接区で同タイプの追加候補は？」
→ 単価特化型として 中央区／渋谷区 が提案される
```

## 設計思想

### 公開データだけを使う
業者ログイン必須サービスはこのリポジトリでは扱いません。すべての分析はオープンデータで再現可能。

### skillは記事と1:1
1記事1skill（または少数）の対応で、**記事を読んだ読者が即同じ分析を自社で動かせる** 状態を作ります。

### 更新前提
- データは年次更新（地価は毎年、住宅・土地統計は5年に1度）
- skillは v1.x.y の小バージョンで継続更新
- 各 skill のロードマップは SKILL.md 末尾参照

## ロードマップ

| バージョン | 内容 | 時期 |
|---|---|---|
| v1.0.0 | inheritance-hotspots（東京23区） | 2026-05-02 |
| v1.1.0 | 神奈川・千葉・埼玉対応 | 2026-06 |
| v1.2.0 | 自社CSV取込（自店舗位置→半径Xkmで再ランキング） | 2026-07 |
| v2.0.0 | competitor-overlay skill 追加 | 2026-Q3 |

## ライセンス

MIT License — [LICENSE](LICENSE)

## 作者

[etsurouwatanabe-tech](https://github.com/etsurouwatanabe-tech)
note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)

不動産仲介業のAI伴走に関するご相談は X / note の DM からどうぞ。
