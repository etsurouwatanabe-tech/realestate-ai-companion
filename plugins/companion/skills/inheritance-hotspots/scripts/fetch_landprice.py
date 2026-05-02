"""国土数値情報 L01 地価公示 ZIP をDLし、住宅地の市区町村別中央値を集計する。

v1.0.0 は東京23区。ダウンロードURL構造は L01-{YY}_GML.zip（YY=西暦下2桁）。
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from dbfread import DBF

BASE_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/L01"

WARDS_TOKYO_23 = {f"131{i:02d}": n for i, n in enumerate([
    "千代田", "中央", "港", "新宿", "文京", "台東", "墨田", "江東", "品川", "目黒",
    "大田", "世田谷", "渋谷", "中野", "杉並", "豊島", "北", "荒川", "板橋", "練馬",
    "足立", "葛飾", "江戸川",
], start=1)}


def download_and_extract(year_yy: int, work_dir: Path) -> Path:
    """指定年度（西暦下2桁、例: 25）のZIPを取得・展開し、dbfパスを返す。"""
    work_dir.mkdir(parents=True, exist_ok=True)
    zip_path = work_dir / f"L01-{year_yy}_GML.zip"
    if not zip_path.exists():
        url = f"{BASE_URL}/L01-{year_yy}/L01-{year_yy}_GML.zip"
        print(f"DL: {url}", file=sys.stderr)
        urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(work_dir)
    dbf = work_dir / f"L01-{year_yy}_GML" / f"L01-{year_yy}.dbf"
    if not dbf.exists():
        raise FileNotFoundError(dbf)
    return dbf


def aggregate(dbf_path: Path, area_codes: dict[str, str]) -> list[dict]:
    """住宅地の標準地について、市区町村コード別に中央値・平均を集計。"""
    bucket: dict[str, list[int]] = defaultdict(list)
    for rec in DBF(str(dbf_path), encoding="cp932"):
        code = rec.get("L01_001", "")
        if code not in area_codes:
            continue
        use = rec.get("L01_028", "") or ""
        price = rec.get("L01_008")
        if price and "住宅" in use:
            bucket[code].append(price)

    rows = []
    for code, name in area_codes.items():
        prices = bucket.get(code, [])
        if not prices:
            continue
        rows.append({
            "code": code,
            "ward": name,
            "n_points": len(prices),
            "mean_yen_sqm": int(statistics.mean(prices)),
            "median_yen_sqm": int(statistics.median(prices)),
        })
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=25, help="西暦下2桁（例: 25 = 令和7年/2025年版）")
    p.add_argument("--work", default="data/raw", help="作業ディレクトリ（ZIP/dbf配置先）")
    p.add_argument("--out", required=True, help="出力CSV")
    p.add_argument("--prefecture", default="13", help="v1.0.0は 13=東京")
    args = p.parse_args()

    if args.prefecture != "13":
        print(f"⚠ v1.0.0 は東京（13）のみ動作確認済", file=sys.stderr)

    dbf_path = download_and_extract(args.year, Path(args.work))
    rows = aggregate(dbf_path, WARDS_TOKYO_23)

    with open(args.out, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"saved → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
