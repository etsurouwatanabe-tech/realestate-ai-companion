# scripts/

inheritance-hotspots skill の動作スクリプト（v1.1.0 全国対応）。

## 構成

| ファイル | 役割 | 必須 |
|---|---|---|
| `prepare.py` | e-Stat API + 地価公示で任意都道府県のデータ取得→集計CSV生成 | `ESTAT_APP_ID` |
| `score.py` | 集計CSVから指定市区町村のスコア・タイプ・追加候補を返す | なし（CSV生成済前提） |

両ファイルとも **PEP 723 inline metadata** で依存を宣言しているため、`uv run` 一発で動きます。

## セットアップ

### uv（推奨）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

PEP 723 メタデータが効くので個別の `pip install` 不要。

### e-Stat APIキー取得

無料・即日発行。

1. https://www.e-stat.go.jp/api/ でユーザー登録
2. アプリケーションID（appId）を取得
3. 環境変数として設定：

```bash
export ESTAT_APP_ID=取得したID
```

`.env` ファイルでもOK（`python-dotenv` が自動読み込み）。

## 使い方

### Slash command 経由（推奨）

Claude Code 内で：

```
/companion:prepare 東京        # データ準備
/companion:inheritance 世田谷区,大田区,目黒区   # スコア確認
```

### CLI で直接

```bash
# 初回データ準備（1〜3分／都道府県）
uv run prepare.py --prefecture 13              # 東京
uv run prepare.py --prefecture 13,14           # 東京＋神奈川
uv run prepare.py --prefecture 東京,神奈川     # 都道府県名でも可
uv run prepare.py --prefecture all             # 全国（30〜60分）

# スコア確認
uv run score.py --wards "世田谷区,大田区,目黒区"
uv run score.py --wards "横浜市港北区,川崎市麻生区"
uv run score.py --wards "東京:中央区,大阪:中央区"   # 同名解決
```

### データ更新

新年度の地価公示が出たら（毎年3〜4月）：

```bash
uv run prepare.py --prefecture 13 --year 26    # 令和8年（2026年版）
```

## 同名市区町村の曖昧解決

「中央区」「北区」など全国に複数ある名称は、警告＋候補一覧を返します：

```
⚠ 『中央区』は 8件の候補があります。都道府県を指定してください：
  - 東京:中央区
  - 大阪:中央区
  ...
  例: --wards "東京:中央区"
```

`都道府県名:市区町村名` 形式で再指定してください。

## 「横浜市港北区」のような冗長指定

`score.py` は末尾の最小行政単位を抽出して検索します：

- 「横浜市港北区」 → 「港北区」として検索
- 「川崎市麻生区」 → 「麻生区」として検索
- 「世田谷区」 → そのまま「世田谷区」

## 使い方がわからない場合

DM までどうぞ。要望が多ければ使用方法の解説記事を作成します。

- X / note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)

## データの出典

- e-Stat 住宅・土地統計調査（H30）：統計表ID `0003356490`
- e-Stat 国勢調査（R2）：統計表ID `0004019309`
- 国土数値情報 L01 地価公示（R7）：`https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-v3_2.html`

## 注意

- `data/aggregated.csv` と `data/raw/` は `.gitignore` 対象（ユーザー側で生成）
- 生成後のCSVは MIT で再配布可（社内共有・派生利用OK）
- e-Stat メタ情報（市区町村コード一覧）は初回のみ取得しキャッシュ（`data/raw/area_codes.json`）
