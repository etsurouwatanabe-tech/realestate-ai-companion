"""inheritance-hotspots: 初回データ準備スクリプト

e-Stat API + 国土数値情報 L01 を取得し、score.py が読む統合CSVを生成する。

実行に必要：
  - 環境変数 ESTAT_APP_ID（e-Stat API キー）
    取得：https://www.e-stat.go.jp/api/

実行例：
  export ESTAT_APP_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  python prepare.py --year 25
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import httpx
from dbfread import DBF

ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"
LANDPRICE_BASE_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/L01"

TABLE_HOUSING = "0003356490"
TABLE_CENSUS = "0004019309"

WARDS_TOKYO_23 = {f"131{i:02d}": n for i, n in enumerate([
    "千代田", "中央", "港", "新宿", "文京", "台東", "墨田", "江東", "品川", "目黒",
    "大田", "世田谷", "渋谷", "中野", "杉並", "豊島", "北", "荒川", "板橋", "練馬",
    "足立", "葛飾", "江戸川",
], start=1)}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "raw"
OUTPUT_CSV = DATA_DIR / "tokyo23_aggregated.csv"


def require_estat_app_id() -> str:
    app_id = os.environ.get("ESTAT_APP_ID")
    if app_id:
        return app_id
    print(
        "❌ ESTAT_APP_ID が設定されていません。\n"
        "\n"
        "1. e-Stat 利用登録（無料）：https://www.e-stat.go.jp/api/\n"
        "2. アプリケーションIDを取得\n"
        "3. 環境変数として設定：\n"
        "     export ESTAT_APP_ID=取得したID\n"
        "\n"
        "使い方がわからなければ DM までどうぞ：\n"
        "  X / note: @etsuro_watanabe\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


def fetch_estat(app_id: str) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    """住宅・土地統計（高齢者持ち家）と 国勢調査（年齢別人口）を23区分まとめて取得。"""
    print("[1/3] e-Stat API: 住宅・土地統計（高齢者持ち家世帯）取得中...", file=sys.stderr)
    codes = ",".join(WARDS_TOKYO_23.keys())
    with httpx.Client(timeout=60) as c:
        r1 = c.get(f"{ESTAT_BASE_URL}/getStatsData", params={
            "appId": app_id, "statsDataId": TABLE_HOUSING, "cdArea": codes, "limit": 500,
        })
        r1.raise_for_status()
        housing: dict[str, dict[str, int]] = {}
        values = r1.json()["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
        if isinstance(values, dict):
            values = [values]
        for v in values:
            if v.get("@tab") != "12-2018" or v.get("@cat01") != "0":
                continue
            a = v["@area"]
            try:
                val = int(v["$"])
            except (TypeError, ValueError):
                continue
            housing.setdefault(a, {"owner": 0, "total": 0})
            if v["@cat02"] == "1":
                housing[a]["owner"] = val
            elif v["@cat02"] == "0":
                housing[a]["total"] = val

        print("[2/3] e-Stat API: 国勢調査（年齢別人口）取得中...", file=sys.stderr)
        r2 = c.get(f"{ESTAT_BASE_URL}/getStatsData", params={
            "appId": app_id, "statsDataId": TABLE_CENSUS, "cdArea": codes, "limit": 10000,
        })
        r2.raise_for_status()
        census: dict[str, dict[str, int]] = {}
        values = r2.json()["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
        if isinstance(values, dict):
            values = [values]
        for v in values:
            if v.get("@cat02") != "0" or v.get("@cat03") != "0":
                continue
            a = v["@area"]
            c1 = v["@cat01"]
            try:
                val = int(v["$"])
            except (TypeError, ValueError):
                continue
            census.setdefault(a, {"pop_total": 0, "pop_65plus": 0})
            if c1 == "00":
                census[a]["pop_total"] = val
            elif c1 == "R3":
                census[a]["pop_65plus"] = val
    return housing, census


def fetch_landprice(year_yy: int) -> dict[str, dict[str, int]]:
    """国土数値情報 L01 ZIPをDL（キャッシュ有）→ dbf集計。"""
    print(f"[3/3] 国土数値情報 L01-{year_yy}（地価公示）取得中...", file=sys.stderr)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE_DIR / f"L01-{year_yy}_GML.zip"
    if not zip_path.exists():
        url = f"{LANDPRICE_BASE_URL}/L01-{year_yy}/L01-{year_yy}_GML.zip"
        print(f"  DL（初回のみ・約20MB）: {url}", file=sys.stderr)
        urllib.request.urlretrieve(url, zip_path)
    extract_dir = CACHE_DIR / f"L01-{year_yy}_GML"
    if not extract_dir.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(CACHE_DIR)
    dbf_path = extract_dir / f"L01-{year_yy}.dbf"
    if not dbf_path.exists():
        print(f"❌ {dbf_path} が見つかりません", file=sys.stderr)
        raise SystemExit(1)

    bucket: dict[str, list[int]] = defaultdict(list)
    for rec in DBF(str(dbf_path), encoding="cp932"):
        code = rec.get("L01_001", "")
        if code not in WARDS_TOKYO_23:
            continue
        use = rec.get("L01_028", "") or ""
        price = rec.get("L01_008")
        if price and "住宅" in use:
            bucket[code].append(price)

    return {
        code: {"median": int(statistics.median(prices)), "mean": int(statistics.mean(prices)), "n": len(prices)}
        for code, prices in bucket.items()
    }


def main() -> int:
    p = argparse.ArgumentParser(description="inheritance-hotspots: 初回データ準備")
    p.add_argument("--year", type=int, default=25,
                   help="地価公示の年度（西暦下2桁。例: 25 = 令和7年/2025年版）")
    args = p.parse_args()

    app_id = require_estat_app_id()
    housing, census = fetch_estat(app_id)
    land = fetch_landprice(args.year)

    rows = []
    for code, name in WARDS_TOKYO_23.items():
        h = housing.get(code, {"owner": 0, "total": 0})
        c = census.get(code, {"pop_total": 0, "pop_65plus": 0})
        l = land.get(code, {"median": 0, "mean": 0, "n": 0})
        own_rate = h["owner"] / h["total"] * 100 if h["total"] else 0
        aging = c["pop_65plus"] / c["pop_total"] * 100 if c["pop_total"] else 0
        score = h["owner"] * l["median"] / 1e8 if l["median"] else 0
        rows.append({
            "code": code,
            "ward": name,
            "pop_total": c["pop_total"],
            "pop_65plus": c["pop_65plus"],
            "aging_rate": round(aging, 1),
            "elderly_owner_hh": h["owner"],
            "elderly_owner_rate": round(own_rate, 1),
            "land_median_yen_sqm": l["median"],
            "land_mean_yen_sqm": l["mean"],
            "n_points": l["n"],
            "score_100oku": round(score, 1),
        })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n✅ 完了 → {OUTPUT_CSV}", file=sys.stderr)
    print(f"   23区分のデータを集計しました。次は score.py を実行してください：", file=sys.stderr)
    print(f"     python score.py --wards \"世田谷,大田,目黒\"", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
