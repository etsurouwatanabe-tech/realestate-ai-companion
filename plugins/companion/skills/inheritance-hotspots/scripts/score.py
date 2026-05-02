#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv>=1.0"]
# ///
"""inheritance-hotspots: 相続予備軍スコア＋タイプ判定（全国対応 v1.1.0）

prepare.py で生成した aggregated.csv を読み込み、ユーザー指定の市区町村について
順位・スコア・タイプ・追加候補を返す。

実行例：
  python score.py --wards "世田谷区,大田区,目黒区"
  python score.py --wards "横浜市港北区,川崎市麻生区"
  python score.py --wards "東京:中央区,大阪府:中央区"   # 同名解決時
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "aggregated.csv"


# ─────────────────────────────────────────────────────────
# データ読込
# ─────────────────────────────────────────────────────────

def load_rows() -> list[dict[str, Any]]:
    if not CSV_PATH.exists():
        print(
            f"❌ {CSV_PATH.name} が見つかりません。\n"
            "\n"
            "初回はデータ準備が必要です：\n"
            "  1. e-Stat APIキーを取得：https://www.e-stat.go.jp/api/\n"
            "  2. 環境変数を設定：export ESTAT_APP_ID=取得したID\n"
            "  3. 準備スクリプト実行：uv run prepare.py --prefecture 13\n"
            "     （複数指定可：--prefecture 13,14,12 / --prefecture all）\n"
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


# ─────────────────────────────────────────────────────────
# 市区町村検索
# ─────────────────────────────────────────────────────────

def normalize(name: str) -> str:
    return name.strip()


def parse_ward_query(q: str) -> tuple[str | None, str]:
    """『東京:中央区』『東京都:中央区』のように都道府県付き指定を分離。
    戻り値：(都道府県名 or None, 市区町村クエリ)
    """
    if ":" in q:
        pref, name = q.split(":", 1)
        pref = pref.strip().replace("都", "").replace("府", "").replace("県", "").replace("道", "")
        return pref, name.strip()
    return None, q.strip()


_LAST_UNIT_RE = re.compile(r"[^市区町村]+[市区町村]$")


def extract_last_unit(name: str) -> str:
    """末尾の最小行政単位を抽出。
    『横浜市港北区』→『港北区』、『川崎市麻生区』→『麻生区』、『世田谷区』→『世田谷区』。
    マッチしなければそのまま返す。
    """
    m = _LAST_UNIT_RE.search(name)
    return m.group(0) if m else name


def find(rows: list[dict[str, Any]], pref: str | None, name: str) -> list[dict[str, Any]]:
    """市区町村検索。pref 指定で都道府県絞り込み。

    e-Stat メタ情報は政令市親（『横浜市』『川崎市』等）も含むが、その下の区も
    別エントリで持つ（『港北区』『麻生区』）。ユーザーが『横浜市港北区』と入力した
    場合は末尾単位『港北区』に落として検索する。
    """
    pool = rows if not pref else [r for r in rows if r["prefecture"] == pref]
    # 1. 完全一致（入力そのまま）
    exact = [r for r in pool if r["municipality"] == name]
    if exact:
        return exact
    # 2. 末尾単位で完全一致（『横浜市港北区』→『港北区』）
    last = extract_last_unit(name)
    if last != name:
        exact_last = [r for r in pool if r["municipality"] == last]
        if exact_last:
            return exact_last
    # 3. 部分一致（最後の保険、『世田谷』→『世田谷区』）
    return [r for r in pool if name in r["municipality"]]


# ─────────────────────────────────────────────────────────
# タイプ判定
# ─────────────────────────────────────────────────────────

def classify_type(r: dict[str, Any]) -> str:
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


def neighbors_of_type(
    rows: list[dict[str, Any]],
    target_type: str,
    exclude_codes: set[str],
    pref_filter: set[str] | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if r["code"] in exclude_codes:
            continue
        if pref_filter and r["prefecture"] not in pref_filter:
            continue
        if classify_type(r) == target_type:
            out.append(r)
            if len(out) >= limit:
                break
    return out


# ─────────────────────────────────────────────────────────
# レポート
# ─────────────────────────────────────────────────────────

def fmt_yen(yen_sqm: int) -> str:
    return f"{yen_sqm/10000:.0f}万円/㎡"


def format_one(r: dict[str, Any], total: int) -> str:
    t = classify_type(r)
    return (
        f"[ {r['prefecture']} {r['municipality']} ]\n"
        f"  順位: {r['rank']}位 / 集計対象 {total}市区町村中\n"
        f"  スコア: {r['score_100oku']:.0f}（高齢持ち家 {r['elderly_owner_hh']:,}世帯 × 中央値地価 {fmt_yen(r['land_median_yen_sqm'])}）\n"
        f"  タイプ: {t}\n"
        f"  高齢化率: {r['aging_rate']:.1f}% / 持ち家率: {r['elderly_owner_rate']:.1f}%"
    )


def format_ambiguous(name: str, candidates: list[dict[str, Any]]) -> str:
    lines = [f"⚠ 『{name}』は {len(candidates)}件の候補があります。都道府県を指定してください："]
    for c in candidates[:8]:
        lines.append(f"  - {c['prefecture']}:{c['municipality']}")
    if len(candidates) > 8:
        lines.append(f"  ... 他 {len(candidates)-8}件")
    lines.append(f"  例: --wards \"{candidates[0]['prefecture']}:{name}\"")
    return "\n".join(lines)


def report(wards: list[str]) -> str:
    rows = load_rows()
    total = len(rows)
    lines: list[str] = []
    selected: list[dict[str, Any]] = []
    types_used: set[str] = set()
    prefs_used: set[str] = set()

    for ward in wards:
        pref, name = parse_ward_query(ward)
        found = find(rows, pref, name)
        if not found:
            lines.append(f"[ {ward} ] ❌ 該当なし。prepare.py で対象都道府県を含めてください")
            continue
        if len(found) > 1:
            lines.append(format_ambiguous(name, found))
            continue
        r = found[0]
        selected.append(r)
        types_used.add(classify_type(r))
        prefs_used.add(r["prefecture"])
        lines.append(format_one(r, total))

    if selected:
        avg_score = sum(r["score_100oku"] for r in selected) / len(selected)
        rank_group = next(
            (str(rows[i]["rank"]) for i in range(len(rows)) if rows[i]["score_100oku"] <= avg_score),
            str(total),
        )
        lines.append("")
        lines.append(f"主力{len(selected)}市区町村の平均スコア: {avg_score:.0f} → 集計対象中 {rank_group}位群")
        if len(types_used) > 1:
            lines.append(f"タイプ偏在: {' + '.join(sorted(types_used))} → 複数戦略の併走推奨")
        else:
            t = next(iter(types_used))
            lines.append(f"タイプ統一: {t} → 同型エリア展開で深耕余地あり")

        # 同タイプの追加候補（同じ都道府県内優先）
        exclude = {r["code"] for r in selected}
        suggestions: list[str] = []
        for t in sorted(types_used):
            cand = neighbors_of_type(rows, t, exclude, pref_filter=prefs_used, limit=2)
            for c in cand:
                suggestions.append(f"{c['prefecture']}{c['municipality']}（{t}・{c['rank']}位）")
        if suggestions:
            lines.append(f"追加候補: {' / '.join(suggestions[:3])}")

    lines.append("")
    lines.append("─────")
    lines.append("この結果について個別相談したい方は DM までどうぞ：")
    lines.append("  X / note: @etsuro_watanabe")

    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="相続予備軍スコア（全国対応）")
    p.add_argument("--wards", required=True,
                   help="市区町村名カンマ区切り。例: 世田谷区,大田区 / 横浜市港北区 / 東京:中央区,大阪府:中央区")
    args = p.parse_args()
    wards = [w for w in (s.strip() for s in args.wards.split(",")) if w]
    if not wards:
        print("市区町村名を指定してください", file=sys.stderr)
        return 1
    print(report(wards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
