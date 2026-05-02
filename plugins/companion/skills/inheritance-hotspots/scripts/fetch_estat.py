"""e-Stat API から 高齢者持ち家世帯 + 高齢化率 を任意の市区町村単位で取得する。

v1.0.0 は東京23区での動作確認のみ。全国対応の素地は組み込み済み。
APIキーは環境変数 `ESTAT_APP_ID` に設定する。
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Any

import httpx

BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"

# 平成30年 住宅・土地統計調査：市区町村別×高齢世帯型×住宅所有関係 高齢者主世帯数
TABLE_HOUSING = "0003356490"

# 令和2年 国勢調査：年齢5歳階級×日本人別人口（市区町村）
TABLE_CENSUS = "0004019309"

WARDS_TOKYO_23 = {f"131{i:02d}": n for i, n in enumerate([
    "千代田", "中央", "港", "新宿", "文京", "台東", "墨田", "江東", "品川", "目黒",
    "大田", "世田谷", "渋谷", "中野", "杉並", "豊島", "北", "荒川", "板橋", "練馬",
    "足立", "葛飾", "江戸川",
], start=1)}


def _get(client: httpx.Client, path: str, params: dict[str, Any]) -> dict[str, Any]:
    r = client.get(f"{BASE_URL}{path}", params=params)
    r.raise_for_status()
    return r.json()


def fetch_elderly_owner(app_id: str, area_codes: list[str]) -> dict[str, dict[str, int]]:
    """戻り値: {area_code: {"owner": x, "total": y}}"""
    out: dict[str, dict[str, int]] = {}
    with httpx.Client(timeout=60) as c:
        data = _get(c, "/getStatsData", {
            "appId": app_id,
            "statsDataId": TABLE_HOUSING,
            "cdArea": ",".join(area_codes),
            "limit": 500,
        })
        values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
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


def fetch_aging_rate(app_id: str, area_codes: list[str]) -> dict[str, dict[str, int]]:
    """戻り値: {area_code: {"pop_total": x, "pop_65plus": y}}"""
    out: dict[str, dict[str, int]] = {}
    with httpx.Client(timeout=60) as c:
        data = _get(c, "/getStatsData", {
            "appId": app_id,
            "statsDataId": TABLE_CENSUS,
            "cdArea": ",".join(area_codes),
            "limit": 10000,
        })
        values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
        if isinstance(values, dict):
            values = [values]
        for v in values:
            if v.get("@cat02") != "0" or v.get("@cat03") != "0":
                continue  # 国籍総数 / 男女総数のみ
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prefecture", default="13", help="都道府県コード（v1.0.0は 13=東京 のみ動作確認）")
    p.add_argument("--out", required=True, help="出力CSVパス")
    args = p.parse_args()

    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        print("ESTAT_APP_ID 環境変数を設定してください", file=sys.stderr)
        return 1

    if args.prefecture != "13":
        print(f"⚠ v1.0.0 は東京（13）のみ動作確認済。指定: {args.prefecture}", file=sys.stderr)

    codes = list(WARDS_TOKYO_23.keys()) if args.prefecture == "13" else []
    if not codes:
        print("対象市区町村コードがありません", file=sys.stderr)
        return 1

    print(f"e-Stat 取得中: {len(codes)} 市区町村", file=sys.stderr)
    housing = fetch_elderly_owner(app_id, codes)
    census = fetch_aging_rate(app_id, codes)

    rows = []
    for code in codes:
        h = housing.get(code, {"owner": 0, "total": 0})
        c = census.get(code, {"pop_total": 0, "pop_65plus": 0})
        own_rate = h["owner"] / h["total"] * 100 if h["total"] else 0
        aging = c["pop_65plus"] / c["pop_total"] * 100 if c["pop_total"] else 0
        rows.append({
            "code": code,
            "ward": WARDS_TOKYO_23.get(code, code),
            "pop_total": c["pop_total"],
            "pop_65plus": c["pop_65plus"],
            "aging_rate": round(aging, 1),
            "elderly_owner_hh": h["owner"],
            "elderly_owner_rate": round(own_rate, 1),
        })

    with open(args.out, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"saved → {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
