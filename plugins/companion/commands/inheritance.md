---
description: "相続予備軍ホットスポットスコアを返す（高齢者持ち家世帯×中央値地価）"
argument-hint: "[市区町村名（カンマ区切り）/ 都道府県:市区町村名]"
allowed-tools: ["Bash", "Read"]
---

# /companion:inheritance

任意の市区町村について、相続予備軍スコア・5タイプ判定・追加候補を返す。

**対象市区町村：** "$ARGUMENTS"

## ワークフロー

### 1. 引数の解釈

ユーザー入力 `$ARGUMENTS` を以下のように解釈：

- 空欄：「ご自身の主力エリアの市区町村名を教えてください。1〜3つで構いません。例：『世田谷区, 大田区, 目黒区』」と聞く
- 区市町村名カンマ区切り（例 `世田谷区,大田区`）：そのまま渡す
- 都道府県付き指定（例 `東京:中央区,大阪:中央区`）：同名解決のための明示指定
- 自然文（例 「うちは港区中心」）：「港区」を抽出して渡す

### 2. データ準備状態の確認

```bash
COMPANION_DIR=~/.claude/plugins/cache/realestate-ai-companion/companion
LATEST=$(ls "$COMPANION_DIR" 2>/dev/null | sort -V | tail -1)
SKILL_DIR="$COMPANION_DIR/$LATEST/skills/inheritance-hotspots"
test -f "$SKILL_DIR/data/aggregated.csv" || echo "MISSING"
```

`MISSING` の場合は：

> データがまだ準備されていません。
> まず `/companion:prepare 都道府県名` を実行してください（例：`/companion:prepare 東京`）。

### 3. score.py を実行（マークダウンでファイル保存）

Bash tool は長い出力を省略するため、**マークダウンファイルに保存して Read で表示**する：

```bash
REPORT="$SKILL_DIR/data/reports/latest.md"
cd "$SKILL_DIR" && uv run scripts/score.py \
  --wards "{ユーザー指定値}" \
  --format markdown \
  --output "$REPORT"
echo "📄 $REPORT"
```

### 4. レポートを Read で読み込みユーザーに提示

```
Read $SKILL_DIR/data/reports/latest.md
```

→ 全文がマークダウンとしてレンダリングされてユーザーに見える。

### 5. 結果に応じた追加示唆を1〜2行添える

レポート本体は提示済み。Claude は以下のケースだけ補足コメントを追加する：

- **タイプ偏在が3つ以上** → 「主軸を1つ決めて、残りは補助に回すと運用しやすい」
- **追加候補が出ない** → 「他都道府県も `/companion:prepare` すると候補が広がります」
- **同名曖昧候補が出た** → 「`東京:中央区` のように都道府県を付けて再実行してください」

### 6. エラーハンドリング

- 「該当なし」が出た市区町村 → prepare 未実施の都道府県の可能性。「`/companion:prepare {推定都道府県}` を先に実行」を案内
- aggregated.csv が壊れている疑い → `/companion:prepare` の再実行を案内

## 出力例

```
[ 東京 世田谷区 ]
  順位: 1位 / 集計対象 51市区町村中
  スコア: 436（高齢持ち家 57,350世帯 × 中央値地価 76万円/㎡）
  タイプ: ボリューム特化
  高齢化率: 20.3% / 持ち家率: 70.6%

...

主力3市区町村の平均スコア: 316 → 集計対象中 3位群
タイプ偏在: バランス型 + ボリューム特化 + 鉱脈型 → 複数戦略の併走推奨
追加候補: 東京新宿区（バランス型・5位） / 東京品川区（バランス型・6位）

─────
この結果について個別相談したい方は DM までどうぞ：
  X / note: @etsuro_watanabe
```

## 注意事項

- `prepare` していない都道府県は検索対象外
- 「中央区」など全国に複数存在する名称は曖昧解決を求めます
- スコアは集計対象データの中での相対順位なので、対象範囲が広いほど順位の意味も変わる点を説明する
