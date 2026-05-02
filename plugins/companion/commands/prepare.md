---
description: "相続予備軍ホットスポット分析の初回データ準備（e-Stat + 地価公示を取得）"
argument-hint: "[都道府県名/コード（カンマ区切り）/all]"
allowed-tools: ["Bash", "Read"]
---

# /companion:prepare

inheritance-hotspots skill のデータを準備する。

**対象都道府県：** "$ARGUMENTS"

## ワークフロー

### 1. 引数の解釈

ユーザー入力 `$ARGUMENTS` を以下のように解釈：

- 空欄：「どの都道府県を準備しますか？東京・神奈川・千葉・埼玉などの都道府県名、またはコード（13など）を教えてください。複数可、`all` で全国も可能です」と聞く
- 数字（例 `13`）：そのまま渡す
- 都道府県名（例 `東京`、`神奈川`）：そのまま渡す（複数カンマ区切りもOK）
- `all`：全国

### 2. ESTAT_APP_ID の確認

```bash
echo "${ESTAT_APP_ID:0:8}..." 2>/dev/null || echo "未設定"
```

未設定なら以下を案内し、ここで停止：

> ESTAT_APP_ID が未設定です。
> 1. https://www.e-stat.go.jp/api/ で無料登録
> 2. アプリケーションIDを取得
> 3. `export ESTAT_APP_ID=取得したID` を実行
> 4. 再度 `/companion:prepare` を実行

### 3. prepare.py を実行

skill のディレクトリに移動して `uv run` で実行：

```bash
SKILL_DIR=$(claude plugin path companion 2>/dev/null || echo ~/.claude/plugins/cache/realestate-ai-companion/companion/*/skills/inheritance-hotspots)
cd "$SKILL_DIR"
uv run scripts/prepare.py --prefecture "{ユーザー指定値}"
```

**所要時間目安**：
- 1都道府県：1〜3分
- 1都3県（13,14,12,11）：5〜10分
- `all`：30〜60分

### 4. 結果の整形

prepare.py の出力をそのままユーザーに見せ、最後に次のアクションを案内：

> ✅ データ準備完了。
> `/companion:inheritance 区市町村名` で分析できます。
> 例：`/companion:inheritance 世田谷区,大田区`

### 5. エラーハンドリング

- ESTAT_APP_ID 関連エラー → Step 2 の案内
- 通信エラー → 「e-Stat API がタイムアウトしました。少し時間を置いて再試行してください」
- DL失敗 → 「国土数値情報のZIP取得に失敗しました。手動で `wget https://nlftp.mlit.go.jp/ksj/gml/data/L01/L01-25/L01-25_GML.zip -P data/raw/` でも可能です」

## 注意事項

- 同一都道府県を再準備すると上書きされます（年次更新時はそれが正しい挙動）
- area_codes.json は初回のみe-Stat APIから取得しキャッシュされます
- 地価公示ZIP（約20MB）は初回DL後はキャッシュされます
