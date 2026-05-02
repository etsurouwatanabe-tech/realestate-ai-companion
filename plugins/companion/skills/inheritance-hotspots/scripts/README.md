# scripts/

inheritance-hotspots skill の動作スクリプト。

## 構成

| ファイル | 役割 | 必須API |
|---|---|---|
| `score.py` | 同梱CSVから任意エリアのスコア・タイプを返す | なし |
| `fetch_estat.py` | e-Stat API から世帯・人口データを再取得 | `ESTAT_APP_ID` |
| `fetch_landprice.py` | 国土数値情報 L01 ZIP から地価集計を再取得 | なし |

## セットアップ

```bash
pip install httpx python-dotenv dbfread
```

## 使い方

### スコア確認だけ（API キー不要）

```bash
python score.py --wards "世田谷,大田,目黒"
```

### データを最新化したい（再取得）

```bash
# e-Stat キーを設定
export ESTAT_APP_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 1) 世帯・人口データ
python fetch_estat.py --out ../data/_estat_tokyo23.csv

# 2) 地価データ（最新は 25 = 2025年版／毎年3〜4月公表）
python fetch_landprice.py --year 25 --out ../data/_landprice_tokyo23.csv

# 3) score.py 用の統合CSVは別途マージ（v1.1.0で merge.py 提供予定）
```

## データの出典

- e-Stat 住宅・土地統計調査（H30）：統計表ID `0003356490`
- e-Stat 国勢調査（R2）：統計表ID `0004019309`
- 国土数値情報 L01 地価公示（R7）：`https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-L01-v3_2.html`

## 注意

- `data/raw/` 以下は `.gitignore` 対象（生データZIP・dbf）
- 公開済みCSV `data/tokyo23_2025.csv` は MIT で再配布可
