# realestate-ai-companion

不動産業のAI伴走者 — 公開API × Claude で物件分析・業務再設計を実装するskill群。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## なにこれ

中小不動産会社向けに、**公開API × AI** で営業エリア戦略・市場分析を支援する Claude Code 用 plugin です。

- **公開データのみ** を扱います（業者ログイン必須サービスは扱いません）
- 各 skill は **APIキー前提**で動的にデータ取得します（最新データで毎回分析）
- **Slash command で対話起動**：`/companion:prepare`／`/companion:inheritance`
- 記事と1:1で対応するskillが増えていきます。**記事↔skillマップ**は [docs/article-skill-map.md](docs/article-skill-map.md) を参照

## インストール

```bash
claude plugin marketplace add etsurouwatanabe-tech/realestate-ai-companion
claude plugin install companion
```

## 使う前の準備（初回のみ）

### 1. e-Stat APIキー取得（無料・即日発行）

総務省統計局の公開API。住宅・土地統計／国勢調査のデータ取得に使用。

- 取得サイト：**https://www.e-stat.go.jp/api/**
- ユーザー登録 → アプリケーションID発行

### 2. 環境変数を設定

```bash
export ESTAT_APP_ID=取得したID
```

`.env` ファイルでも可（`python-dotenv` が自動読み込み）。

### 3. uv を入れておく（依存解決が一発）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

各 script は **PEP 723 inline metadata** を持っているので、`uv run` で依存解決ごと一発です。手動の `pip install` は不要。

## 使い方（Slash command で対話起動）

### 初回データ準備

```
/companion:prepare 東京
```

- 都道府県名・コード・複数指定（`13,14,12`）・`all`（全国）すべて可
- 1都道府県：1〜3分／1都3県：5〜10分／全国：30〜60分

### スコア確認

```
/companion:inheritance 世田谷区,大田区,目黒区
```

出力：

```
[ 東京 世田谷区 ] 順位: 1位 / スコア436 / タイプ: ボリューム特化
[ 東京 大田区 ]   順位: 4位 / スコア289 / タイプ: 鉱脈型
...
追加候補: 東京新宿区（バランス型・5位） / ...
```

### CLI で直接動かす場合

```bash
SKILL_DIR=~/.claude/plugins/cache/realestate-ai-companion/companion/*/skills/inheritance-hotspots
cd "$SKILL_DIR"
uv run scripts/prepare.py --prefecture 13,14
uv run scripts/score.py --wards "世田谷区,横浜市港北区"
```

## 提供している skill

| skill | 概要 | APIキー | 関連記事 |
|---|---|---|---|
| **inheritance-hotspots** v1.1.0 | 任意都道府県の相続予備軍ホットスポット分析。営業エリアの数値判定 | e-Stat | [N02記事（公開予定）](articles/INDEX.md) |

詳細は各 skill の `SKILL.md` を参照。

## 使い方の例

```
> 「世田谷・大田・目黒の相続予備軍スコアを出して」
→ /companion:inheritance が起動 → 順位・スコア・タイプを返答

> 「うちは横浜中心。隣接区で同タイプの追加候補は？」
→ 自動で /companion:inheritance を実行 → 神奈川県内の同タイプ区を提案
```

## 使い方がわからない場合

DM までどうぞ。要望が多ければ使用方法の解説記事を作成します。

- X / note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)
- 解説記事（執筆中）：N03「Claudeを触ったことがない方向け、30分のセットアップ手順」

## 設計思想

### 公開データだけを使う
業者ログイン必須サービスはこのリポジトリでは扱いません。すべての分析はオープンデータで再現可能。

### APIキー前提（最新データで毎回分析）
集計済みCSVの同梱はしません。**毎回最新データを取得**して分析します。年次更新時もスクリプト再実行で即対応。

### Slash command で対話起動
CLI でも動きますが、**Claude Code の slash command を使えば自然文で完結**します。エンジニア知識ゼロでも使える設計。

### skillは記事と1:1
1記事1skill（または少数）の対応で、**記事を読んだ読者が即同じ分析を自社で動かせる** 状態を作ります。

### 更新前提
- データは年次更新（地価は毎年、住宅・土地統計は5年に1度）
- skillは v1.x.y の小バージョンで継続更新
- 各 skill のロードマップは SKILL.md 末尾参照

## ロードマップ

| バージョン | 内容 | 時期 |
|---|---|---|
| v1.0.0 | inheritance-hotspots（東京23区・データ同梱） | 2026-05-02 |
| v1.0.1 | APIキー前提に再設計（同梱CSV廃止／prepare.py 導入） | 2026-05-02 |
| v1.0.2 | 顧問フィードバック反映（DM CTA／pyproject.toml） | 2026-05-02 |
| **v1.1.0** | **全国対応＋slash command＋PEP 723** | **2026-05-03** |
| v1.2.0 | 自社CSV取込（自店舗位置→半径Xkmで再ランキング） | 2026-06 |
| v1.3.0 | 世帯年収・空き家率を加えた多軸分析 | 2026-07 |
| v2.0.0 | competitor-overlay skill 追加 | 2026-Q3 |

## ライセンス

MIT License — [LICENSE](LICENSE)

## 作者

[etsurouwatanabe-tech](https://github.com/etsurouwatanabe-tech)
note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)

不動産仲介業のAI伴走に関するご相談は X / note の DM からどうぞ。
