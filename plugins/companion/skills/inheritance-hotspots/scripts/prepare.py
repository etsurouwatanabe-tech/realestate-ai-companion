#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "dbfread>=2.0", "python-dotenv>=1.0"]
# ///
"""inheritance-hotspots: データ準備スクリプト（全国対応 v1.1.0）

e-Stat API + 国土数値情報 L01 を取得し、score.py が読む統合CSVを生成する。
任意の都道府県を指定可能（全国対応）。

実行に必要：
  - 環境変数 ESTAT_APP_ID（e-Stat API キー）
    取得：https://www.e-stat.go.jp/api/

実行例：
  python prepare.py --prefecture 13                # 東京都のみ
  python prepare.py --prefecture 13,14,12,11       # 1都3県
  python prepare.py --prefecture all               # 全国（数十分かかる）
  python prepare.py --prefecture 東京,神奈川       # 都道府県名でも可

uv で動かすなら（依存解決込み）：
  uv run prepare.py --prefecture 13,14
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

import httpx
from dbfread import DBF
from dotenv import load_dotenv

load_dotenv()

ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"
LANDPRICE_BASE_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/L01"

TABLE_HOUSING = "0003356490"
TABLE_CENSUS = "0004019309"

# 都道府県コード→名称（JIS X 0401）
PREFECTURES = {
    "01": "北海道", "02": "青森", "03": "岩手", "04": "宮城", "05": "秋田",
    "06": "山形", "07": "福島", "08": "茨城", "09": "栃木", "10": "群馬",
    "11": "埼玉", "12": "千葉", "13": "東京", "14": "神奈川", "15": "新潟",
    "16": "富山", "17": "石川", "18": "福井", "19": "山梨", "20": "長野",
    "21": "岐阜", "22": "静岡", "23": "愛知", "24": "三重", "25": "滋賀",
    "26": "京都", "27": "大阪", "28": "兵庫", "29": "奈良", "30": "和歌山",
    "31": "鳥取", "32": "島根", "33": "岡山", "34": "広島", "35": "山口",
    "36": "徳島", "37": "香川", "38": "愛媛", "39": "高知", "40": "福岡",
    "41": "佐賀", "42": "長崎", "43": "熊本", "44": "大分", "45": "宮崎",
    "46": "鹿児島", "47": "沖縄",
}
NAME_TO_PREF = {v: k for k, v in PREFECTURES.items()}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_DIR = DATA_DIR / "raw"
AREA_CODES_CACHE = CACHE_DIR / "area_codes.json"
OUTPUT_CSV = DATA_DIR / "aggregated.csv"


# ─────────────────────────────────────────────────────────
# 共通
# ─────────────────────────────────────────────────────────

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


def parse_prefectures(arg: str) -> list[str]:
    """引数を都道府県コード（2桁ゼロ埋め）のリストに正規化。"""
    if arg.lower() == "all":
        return list(PREFECTURES.keys())
    out: list[str] = []
    for raw in arg.split(","):
        s = raw.strip()
        if not s:
            continue
        if s.isdigit():
            code = s.zfill(2)
            if code in PREFECTURES:
                out.append(code)
                continue
        # 名前として解決（「東京」「東京都」両対応）
        n = s.replace("都", "").replace("府", "").replace("県", "").replace("道", "")
        if n in NAME_TO_PREF:
            out.append(NAME_TO_PREF[n])
            continue
        print(f"⚠ 未知の都道府県指定: {s}（無視）", file=sys.stderr)
    return out


# ─────────────────────────────────────────────────────────
# 市区町村コード一覧（e-Stat メタ情報からキャッシュ）
# ─────────────────────────────────────────────────────────

def fetch_area_codes(app_id: str) -> dict[str, str]:
    """住宅・土地統計のメタ情報から area code → name の全国マップを取得。
    キャッシュ済なら再利用。
    戻り値：{area_code(5桁): area_name}
    """
    if AREA_CODES_CACHE.exists():
        return json.loads(AREA_CODES_CACHE.read_text(encoding="utf-8"))

    print("[meta] e-Stat メタ情報取得中（初回のみ・1分程度）...", file=sys.stderr)
    with httpx.Client(timeout=120) as c:
        r = c.get(f"{ESTAT_BASE_URL}/getMetaInfo", params={
            "appId": app_id, "statsDataId": TABLE_HOUSING,
        })
        r.raise_for_status()
        classes = r.json()["GET_META_INFO"]["METADATA_INF"]["CLASS_INF"]["CLASS_OBJ"]
        area_class = next(co for co in classes if co.get("@id") == "area")
        cls = area_class.get("CLASS", [])
        if isinstance(cls, dict):
            cls = [cls]
        codes = {x["@code"]: x["@name"] for x in cls if x.get("@code")}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    AREA_CODES_CACHE.write_text(json.dumps(codes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[meta] {len(codes)}件キャッシュ → {AREA_CODES_CACHE}", file=sys.stderr)
    return codes


def municipalities_for_pref(area_codes: dict[str, str], pref_code: str) -> dict[str, str]:
    """指定都道府県内の市区町村コード→名称（都道府県全体・政令市親エンティティは除外）。

    e-Stat メタ情報には『横浜市』『川崎市』『さいたま市』のような政令市の親エンティティが
    含まれるが、配下の区（横浜市港北区→『港北区』など）が独立エントリで存在するため、
    親はスコア重複・順位歪みを避けるため除外する。
    判定：JIS X 0402 で都道府県内コード（下3桁）が `0` で終わるもの。
      - 000 → 都道府県全体
      - 100, 130, 150, 180 等 → 政令市親
      - それ以外（101, 102, 213, 561 等） → 通常の市区町村
    """
    out = {}
    for code, name in area_codes.items():
        if not code.startswith(pref_code) or len(code) != 5:
            continue
        if code.endswith("000"):
            continue
        if code[-1] == "0":
            continue
        out[code] = name
    return out


# ─────────────────────────────────────────────────────────
# e-Stat 取得
# ─────────────────────────────────────────────────────────

def fetch_housing(app_id: str, area_codes_csv: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    with httpx.Client(timeout=120) as c:
        r = c.get(f"{ESTAT_BASE_URL}/getStatsData", params={
            "appId": app_id, "statsDataId": TABLE_HOUSING,
            "cdArea": area_codes_csv, "limit": 5000,
        })
        r.raise_for_status()
        values = r.json()["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
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
            out.setdefault(a, {"owner": 0, "total": 0})
            if v["@cat02"] == "1":
                out[a]["owner"] = val
            elif v["@cat02"] == "0":
                out[a]["total"] = val
    return out


def fetch_census(app_id: str, area_codes_csv: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    with httpx.Client(timeout=120) as c:
        r = c.get(f"{ESTAT_BASE_URL}/getStatsData", params={
            "appId": app_id, "statsDataId": TABLE_CENSUS,
            "cdArea": area_codes_csv, "limit": 100000,
        })
        r.raise_for_status()
        values = r.json()["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
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
            out.setdefault(a, {"pop_total": 0, "pop_65plus": 0})
            if c1 == "00":
                out[a]["pop_total"] = val
            elif c1 == "R3":
                out[a]["pop_65plus"] = val
    return out


# ─────────────────────────────────────────────────────────
# 地価公示（全国ZIP・キャッシュ）
# ─────────────────────────────────────────────────────────

def download_landprice_dbf(year_yy: int) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = CACHE_DIR / f"L01-{year_yy}_GML.zip"
    if not zip_path.exists():
        url = f"{LANDPRICE_BASE_URL}/L01-{year_yy}/L01-{year_yy}_GML.zip"
        print(f"[landprice] DL（初回のみ・約20MB）: {url}", file=sys.stderr)
        urllib.request.urlretrieve(url, zip_path)
    extract_dir = CACHE_DIR / f"L01-{year_yy}_GML"
    if not extract_dir.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(CACHE_DIR)
    dbf_path = extract_dir / f"L01-{year_yy}.dbf"
    if not dbf_path.exists():
        print(f"❌ {dbf_path} が見つかりません", file=sys.stderr)
        raise SystemExit(1)
    return dbf_path


def aggregate_landprice(dbf_path: Path, target_codes: set[str]) -> dict[str, dict[str, int]]:
    """指定市区町村コードの住宅地について、中央値・平均を集計。"""
    bucket: dict[str, list[int]] = defaultdict(list)
    for rec in DBF(str(dbf_path), encoding="cp932"):
        code = rec.get("L01_001", "")
        if code not in target_codes:
            continue
        use = rec.get("L01_028", "") or ""
        price = rec.get("L01_008")
        if price and "住宅" in use:
            bucket[code].append(price)
    return {
        code: {
            "median": int(statistics.median(prices)),
            "mean": int(statistics.mean(prices)),
            "n": len(prices),
        }
        for code, prices in bucket.items()
    }


# ─────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="inheritance-hotspots: 全国対応データ準備")
    p.add_argument("--prefecture", required=True,
                   help="都道府県コード/名称（カンマ区切り、all 可）。例: 13 / 13,14 / 東京,神奈川 / all")
    p.add_argument("--year", type=int, default=25,
                   help="地価公示の年度（西暦下2桁。例: 25 = 令和7年/2025年版）")
    args = p.parse_args()

    app_id = require_estat_app_id()
    pref_codes = parse_prefectures(args.prefecture)
    if not pref_codes:
        print("❌ 有効な都道府県が指定されていません", file=sys.stderr)
        return 1
    print(f"対象: {len(pref_codes)}都道府県 → {[PREFECTURES[c] for c in pref_codes]}", file=sys.stderr)

    # 全国メタ情報（市区町村コード一覧）
    area_codes = fetch_area_codes(app_id)

    # 都道府県ごとに e-Stat 取得（API負荷軽減）
    housing_all: dict[str, dict[str, int]] = {}
    census_all: dict[str, dict[str, int]] = {}
    municipalities_all: dict[str, dict[str, str]] = {}

    for i, pref in enumerate(pref_codes, 1):
        munis = municipalities_for_pref(area_codes, pref)
        if not munis:
            print(f"⚠ {PREFECTURES[pref]}: 市区町村が見つかりません", file=sys.stderr)
            continue
        municipalities_all[pref] = munis
        codes_csv = ",".join(munis.keys())
        print(f"[{i}/{len(pref_codes)}] {PREFECTURES[pref]}: {len(munis)}市区町村 取得中...", file=sys.stderr)
        housing_all.update(fetch_housing(app_id, codes_csv))
        census_all.update(fetch_census(app_id, codes_csv))

    # 地価公示（全国ZIP1ファイル → 対象市区町村のみ集計）
    target_codes: set[str] = set()
    for munis in municipalities_all.values():
        target_codes.update(munis.keys())
    dbf_path = download_landprice_dbf(args.year)
    print(f"[landprice] 集計中（対象 {len(target_codes)}市区町村）...", file=sys.stderr)
    land_all = aggregate_landprice(dbf_path, target_codes)

    # 統合
    rows = []
    for pref, munis in municipalities_all.items():
        pref_name = PREFECTURES[pref]
        for code, name in munis.items():
            h = housing_all.get(code, {"owner": 0, "total": 0})
            c = census_all.get(code, {"pop_total": 0, "pop_65plus": 0})
            l = land_all.get(code, {"median": 0, "mean": 0, "n": 0})
            own_rate = h["owner"] / h["total"] * 100 if h["total"] else 0
            aging = c["pop_65plus"] / c["pop_total"] * 100 if c["pop_total"] else 0
            score = h["owner"] * l["median"] / 1e8 if l["median"] else 0
            rows.append({
                "code": code,
                "prefecture": pref_name,
                "municipality": name,
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
    print(f"   {len(rows)}市区町村のデータを集計しました。次は score.py を実行してください：", file=sys.stderr)
    print(f"     uv run score.py --wards \"区市町村名（カンマ区切り）\"", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
