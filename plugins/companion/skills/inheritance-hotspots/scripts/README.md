# scripts/

inheritance-hotspots skill の動作スクリプト。

## 構成

| ファイル | 役割 | 必須 |
|---|---|---|
| `prepare.py` | e-Stat API + 地価公示でデータ取得 → 集計CSV生成（初回・年次更新時） | `ESTAT_APP_ID` |
| `score.py` | 集計CSVからエリア指定でスコア・タイプ・追加候補を返す | なし（CSV生成済前提） |

## セットアップ

### 依存パッケージ

```bash
pip install httpx python-dotenv dbfread
```

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

### 初回：データ準備

```bash
python prepare.py
# ↓ 数分後
# ✅ 完了 → data/tokyo23_aggregated.csv
```

地価公示の年度を指定したい場合：

```bash
python prepare.py --year 25  # 令和7年（2025年版）
```

### 通常使用：スコア確認

```bash
python score.py --wards "世田谷,大田,目黒"
```

### データ更新

新年度の地価公示が出たら（毎年3〜4月）：

```bash
python prepare.py --year 26  # 令和8年（2026年版）
```

## 使い方がわからない場合

DM までどうぞ。要望が多ければ使用方法の解説記事を作成します。

- X / note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)

## データの出典

- e-Stat 住宅・土地統計調査（H30）：統計表ID `0003356490`
- e-Stat 国勢調査（R2）：統計表ID `0004019309`
- 国土数値情報 L01 地価公示（R7）：`https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-v3_2.html`

## 注意

- `data/tokyo23_aggregated.csv` と `data/raw/` は `.gitignore` 対象（ユーザー側で生成）
- 生成後のCSVは MIT で再配布可（社内共有・派生利用OK）
