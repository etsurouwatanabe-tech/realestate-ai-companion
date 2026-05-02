"""inheritance-hotspots: 東京23区の相続予備軍スコア・タイプ判定

CSVを読み込み、ユーザー指定の区について順位・スコア・タイプを返す。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "tokyo23_aggregated.csv"


def load_rows() -> list[dict[str, Any]]:
    """CSV を読み込み、スコア降順でソートした list を返す。CSV未生成時は prepare.py 実行を促す。"""
    if not CSV_PATH.exists():
        print(
            f"❌ {CSV_PATH.name} が見つかりません。\n"
            "\n"
            "初回はデータ準備が必要です：\n"
            "  1. e-Stat APIキーを取得：https://www.e-stat.go.jp/api/\n"
            "  2. 環境変数を設定：export ESTAT_APP_ID=取得したID\n"
            "  3. 準備スクリプト実行：python prepare.py\n"
            "\n"
            "使い方がわからなければ DM までどうぞ：X / note @etsuro_watanabe\n",
            file=sys.stderr,
        )
        raise SystemExit(1)
    rows: list[dict[str, Any]] = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["pop_total"] = int(r["pop_total"])
            r["pop_65plus"] = int(r["pop_65plus"])
            r["aging_rate"] = float(r["aging_rate"])
            r["elderly_owner_hh"] = int(r["elderly_owner_hh"])
            r["elderly_owner_rate"] = float(r["elderly_owner_rate"])
            r["land_median_yen_sqm"] = int(r["land_median_yen_sqm"])
            r["score_100oku"] = float(r["score_100oku"])
            rows.append(r)
    rows.sort(key=lambda x: -x["score_100oku"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def classify_type(r: dict[str, Any]) -> str:
    """5タイプ分類のロジック。判定優先度：沈む→単価→ボリューム→鉱脈→バランス→賃貸シフト。"""
    own_hh = r["elderly_owner_hh"]
    own_rate = r["elderly_owner_rate"]
    aging_rate = r["aging_rate"]
    land_med = r["land_median_yen_sqm"]

    if own_rate < 50 and aging_rate >= 24:
        return "沈む高齢化トップ"
    if land_med >= 1500000:
        return "単価特化"
    if own_hh >= 50000:
        return "ボリューム特化"
    if own_hh >= 40000 and land_med < 800000:
        return "鉱脈型"
    if own_rate >= 60:
        return "バランス型"
    return "賃貸シフト型"


def find_by_name(rows: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """『世田谷』『世田谷区』のどちらでもヒットさせる。"""
    norm = name.replace("区", "").strip()
    for r in rows:
        if r["ward"] == norm:
            return r
    return None


def neighbors_of_type(
    rows: list[dict[str, Any]],
    target_type: str,
    exclude: set[str],
    limit: int = 2,
) -> list[dict[str, Any]]:
    """同タイプの上位区を返す（指定区を除外）。"""
    out = []
    for r in rows:
        if r["ward"] in exclude:
            continue
        if classify_type(r) == target_type:
            out.append(r)
            if len(out) >= limit:
                break
    return out


def fmt_yen(yen_sqm: int) -> str:
    """円/㎡ を 万円表記に。"""
    return f"{yen_sqm/10000:.0f}万円/㎡"


def report(wards: list[str]) -> str:
    rows = load_rows()
    lines: list[str] = []
    selected: list[dict[str, Any]] = []
    types_used: set[str] = set()

    for w in wards:
        r = find_by_name(rows, w)
        if r is None:
            lines.append(f"[ {w} ] ❌ 23区に該当なし（v1.0.0は東京23区のみ対応）")
            continue
        t = classify_type(r)
        types_used.add(t)
        selected.append(r)
        lines.append(
            f"[ {r['ward']}区 ]\n"
            f"  順位: {r['rank']}位 / 23区中\n"
            f"  スコア: {r['score_100oku']:.0f}（高齢持ち家 {r['elderly_owner_hh']:,}世帯 × 中央値地価 {fmt_yen(r['land_median_yen_sqm'])}）\n"
            f"  タイプ: {t}\n"
            f"  高齢化率: {r['aging_rate']:.1f}% / 持ち家率: {r['elderly_owner_rate']:.1f}%"
        )

    if selected:
        avg_score = sum(r["score_100oku"] for r in selected) / len(selected)
        rank_group = next((str(rows[i]["rank"]) for i in range(len(rows)) if rows[i]["score_100oku"] <= avg_score), "23")
        lines.append("")
        lines.append(f"主力{len(selected)}区の平均スコア: {avg_score:.0f} → 23区中 {rank_group}位群")
        if len(types_used) > 1:
            lines.append(f"タイプ偏在: {' + '.join(sorted(types_used))} → 複数戦略の併走推奨")
        else:
            t = next(iter(types_used))
            lines.append(f"タイプ統一: {t} → 同型エリア展開で深耕余地あり")

        # 同タイプの追加候補
        exclude = {r["ward"] for r in selected}
        suggestions: list[str] = []
        for t in types_used:
            cand = neighbors_of_type(rows, t, exclude, limit=2)
            for c in cand:
                suggestions.append(f"{c['ward']}区（{t}・{c['rank']}位）")
        if suggestions:
            lines.append(f"追加候補: {' / '.join(suggestions[:3])}")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="東京23区 相続予備軍スコア")
    p.add_argument("--wards", required=True, help="区名カンマ区切り（例: 世田谷,大田,目黒）")
    args = p.parse_args()
    wards = [w.strip() for w in args.wards.split(",") if w.strip()]
    if not wards:
        print("区名を指定してください（例: --wards 世田谷,大田,目黒）", file=sys.stderr)
        return 1
    print(report(wards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
