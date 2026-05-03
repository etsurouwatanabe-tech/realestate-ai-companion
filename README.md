# realestate-ai-companion

不動産業のAI伴走者 — 公開API × Claude で物件分析・業務再設計を実装するskill群。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## なにこれ

中小不動産会社向けに、**公開API × AI** で営業エリア戦略・市場分析を支援する Claude Code 用 plugin です。

- **公開データのみ** を扱います（業者ログイン必須サービスは扱いません）
- **APIキー前提**で動的にデータ取得（最新データで毎回分析）
- **Slash command で対話起動**：`/companion:prepare` ／ `/companion:inheritance`
- **全国対応**（v1.1.0〜）。1都道府県ずつ段階的に追加可能（v1.1.4〜）

---

## クイックスタート（5ステップ・30〜45分）

```
1. Python 3.10+ と uv を入れる            （5〜10分）
2. e-Stat APIキーを無料で取得する          （5分）
3. 環境変数を設定する                      （2分）
4. Claude Code に plugin を入れる          （3分）
5. /companion:prepare 都道府県名 → 分析開始（5〜10分）
```

詳細は [環境構築](#環境構築) と [使い方](#使い方) を順に。詰まったら [トラブルシューティング](#トラブルシューティング)。

---

## 環境構築

### 前提：実機検証済みの環境

- WSL2 / Ubuntu 22.04 / Mac（Sonoma以降）/ 一般的な Linux
- 以下手順は **WSL Ubuntu 想定**で書いています（Mac/Linux はほぼ同じ）

### Step 1: Python 3.10+ を確認・インストール

```bash
python3 --version
```

Python 3.10 未満、または「コマンドが見つかりません」と出た場合：

```bash
# Ubuntu / WSL
sudo apt update && sudo apt install -y python3 python3-pip python-is-python3

# Mac（Homebrew）
brew install python@3.12
```

> **詰まりポイント**：Ubuntu/WSL の最小構成では `python` コマンドが無く `python3` だけです。`python-is-python3` パッケージを入れると `python` が `python3` のエイリアスになります。

### Step 2: uv をインストール（推奨）

各 script は **PEP 723 inline metadata** で依存パッケージを宣言しているので、`uv run` 一発で動きます。`pip install` は不要。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール後、PATH を通す（インストールスクリプトが自動で `~/.bashrc` に追加しますが、今のシェルにも反映が必要）：

```bash
source ~/.bashrc
which uv
# → /home/user/.local/bin/uv のように表示されればOK
```

> **詰まりポイント**：`uv` は `~/.local/bin/` に入ります。PATH に通っていないと `command not found` になるので、上記の `source ~/.bashrc` を必ず実行してください。

### Step 3: e-Stat APIキーを取得（無料・即日発行）

総務省統計局の公開API。住宅・土地統計／国勢調査のデータ取得に使います。

1. https://www.e-stat.go.jp/api/ にアクセス
2. 「ユーザー登録」→ メールアドレス・パスワードを設定
3. 確認メールのリンクをクリック → 本登録
4. ログイン → 「マイページ」→「アプリケーションID取得」
5. アプリケーション名（例：「不動産分析」）を入れて発行
6. **発行された40文字のID（`appId`）をコピー**

> **詰まりポイント**：登録時に「URL1」を求められたら、適当なURL（`http://localhost` 等）でOKです。実際には使われません。

### Step 4: 環境変数を設定（永続化）

ターミナル（bash）で以下を実行（`xxxxxx...` を Step 3 で取得したIDに置き換え）：

```bash
echo 'export ESTAT_APP_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' >> ~/.bashrc
source ~/.bashrc

# 確認（先頭8文字が見えればOK）
echo "${ESTAT_APP_ID:0:8}..."
```

`zsh` 派なら `~/.bashrc` を `~/.zshrc` に置き換えてください。

> **詰まりポイント**：`source ~/.bashrc` は **今開いているシェル**にしか反映されません。**Claude Code を既に起動している場合は一度終了してから再起動が必要**です（Claude Code は起動時の環境変数を引き継ぎます）。

### Step 5: Claude Code に plugin を入れる

```bash
claude plugin marketplace add etsurouwatanabe-tech/realestate-ai-companion
claude plugin install companion@realestate-ai-companion
```

確認：

```bash
claude plugin list | grep companion
ls ~/.claude/plugins/cache/realestate-ai-companion/companion/
# → 1.1.4（または最新バージョン）が見えればOK
```

> **詰まりポイント**：`claude plugin install companion` ではエラーになります。**`@realestate-ai-companion`（marketplace 名）を必ず付ける**こと。同じく更新時も `claude plugin update companion@realestate-ai-companion`。

---

## 使い方

### 初回データ準備

Claude Code を起動した状態で：

```
/companion:prepare 東京
```

ユーザーの好みで以下も可能：

| コマンド | 動作 | 所要時間 |
|---|---|---|
| `/companion:prepare 東京` | 東京のみ取得（既存データに追記） | 1〜3分 |
| `/companion:prepare 13` | コードでも指定可（13=東京） | 1〜3分 |
| `/companion:prepare 東京,神奈川,千葉,埼玉` | 1都3県を一度に | 5〜10分 |
| `/companion:prepare all` | 全国47都道府県 | 30〜60分 |
| `/companion:prepare 東京 --reset` | 既存データを破棄して東京のみで再構築 | 1〜3分 |

**差分追記**（v1.1.4〜）：別の都道府県を追加で `prepare` すると、既存データを保持したまま追加されます。

```
/companion:prepare 東京         → 東京51件
/companion:prepare 神奈川       → 東京残る＋神奈川追加 = 103件
/companion:prepare 千葉         → さらに千葉追加 = 149件
```

### スコア確認

```
/companion:inheritance 世田谷区,大田区,目黒区
```

出力は **マークダウンレポート**として `data/reports/latest.md` に保存され、Claude が Read tool で全文を表示します。

| 入力例 | 動作 |
|---|---|
| `世田谷区,大田区,目黒区` | 東京23区を直接指定 |
| `横浜市港北区,川崎市麻生区` | 政令市配下の区も冗長な指定でOK |
| `東京:中央区,大阪:中央区` | 同名複数候補は `都道府県:市区町村名` で曖昧解決 |

### 自然文でも動きます

```
> 「世田谷・大田・目黒の相続予備軍スコアを出して」
→ /companion:inheritance が自動起動

> 「うちは横浜中心。同タイプの隣接区は？」
→ 神奈川県内の同タイプ区を提案
```

### CLI で直接動かす場合

```bash
SKILL_DIR=~/.claude/plugins/cache/realestate-ai-companion/companion/$(ls ~/.claude/plugins/cache/realestate-ai-companion/companion | sort -V | tail -1)/skills/inheritance-hotspots
cd "$SKILL_DIR"
uv run scripts/prepare.py --prefecture 13,14
uv run scripts/score.py --wards "世田谷区,横浜市港北区" --format markdown --output data/reports/latest.md
```

---

## 提供している skill

| skill | 概要 | APIキー | 関連記事 |
|---|---|---|---|
| **inheritance-hotspots** v1.1.4 | 任意都道府県の相続予備軍ホットスポット分析。営業エリアの数値判定 | e-Stat | [N02記事（公開予定）](articles/INDEX.md) |

詳細は各 skill の `SKILL.md` を参照。

---

## トラブルシューティング

実機検証で実際に踏んだ詰まり点と対処法。

### Q1. `claude plugin install companion` でエラーが出る

A. `@realestate-ai-companion` を付ける必要があります：

```bash
claude plugin install companion@realestate-ai-companion
claude plugin update companion@realestate-ai-companion
```

### Q2. `pip` も `python` も使えない（Ubuntu/WSL）

A. apt で入れるか、`uv` だけで完結させる：

```bash
sudo apt install -y python3-pip python-is-python3
# または
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`uv` を使えば `pip install` は完全に不要です（PEP 723 メタデータが効くため）。

### Q3. `uv: command not found`

A. PATH が通っていません：

```bash
source ~/.bashrc
which uv   # /home/user/.local/bin/uv が出ればOK
```

それでもダメなら：

```bash
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Q4. `ESTAT_APP_ID が未設定です` と出る

A. シェルでは設定済みでも、**Claude Code は起動時の環境変数を引き継ぐ**ので、設定後に Claude Code を一度終了して再起動が必要です。

```bash
# シェルで確認
echo "${ESTAT_APP_ID:0:8}..."   # 40文字のIDの先頭8文字が見えればOK

# Claude Code を一度終了（/exit または Ctrl+D）して再起動
claude
```

**それでも認識しない時の保険**：skill 直下に `.env` を直接置く：

```bash
SKILL_DIR=~/.claude/plugins/cache/realestate-ai-companion/companion/$(ls ~/.claude/plugins/cache/realestate-ai-companion/companion | sort -V | tail -1)/skills/inheritance-hotspots
echo "ESTAT_APP_ID=取得した40文字のID" > "$SKILL_DIR/.env"
```

`prepare.py` は `python-dotenv` で `.env` を読むので、これで動きます。

### Q5. `unrecognized arguments: --prefecture 東京` 等の古いエラーが出る

A. **古いバージョンの cache が残っている**ことが原因です：

```bash
COMPANION_DIR=~/.claude/plugins/cache/realestate-ai-companion/companion

# 残っているバージョンを確認
ls "$COMPANION_DIR"
# → 例: 1.0.2  1.1.0  1.1.1  1.1.4  ← 複数並んでいる

# 最新版以外を削除
ls "$COMPANION_DIR" | sort -V | head -n -1 | xargs -I{} rm -rf "$COMPANION_DIR/{}"

# 旧フォーマットの aggregated CSV も削除
LATEST=$(ls "$COMPANION_DIR" | sort -V | tail -1)
rm -f "$COMPANION_DIR/$LATEST/skills/inheritance-hotspots/data/"*.csv
```

その後 `/companion:prepare 都道府県名` を再実行。

### Q6. `aggregated.csv のフォーマットが古いため破棄します` と出る

A. v1.1.0→v1.1.3 などでCSVのフィールド構造が変わった場合に出ます。**自動で破棄されて新規取得**になるので、そのまま `prepare` を続行すれば問題ありません。

### Q7. レポートの出力が `+33 lines (ctrl+o to expand)` で省略される

A. v1.1.3 以降、`/companion:inheritance` は自動で `data/reports/latest.md` に**マークダウン保存**して Read tool で全文表示します。古いバージョンを使っている場合は Q5 の手順で更新してください。

CLI 直接実行時は `--format markdown --output report.md` を付けると同じ挙動：

```bash
uv run scripts/score.py --wards "世田谷区" --format markdown --output report.md
```

### Q8. 「中央区」を入力したら警告が出た

A. 同名の市区町村が全国に複数あるため、曖昧解決を求めています：

```
⚠ 『中央区』は 8件の候補があります。都道府県を指定してください：
  - 東京:中央区
  - 大阪:中央区
  ...
  例: --wards "東京:中央区"
```

`都道府県名:市区町村名` 形式で再指定してください：

```
/companion:inheritance 東京:中央区
```

### Q9. 「横浜市港北区」と入れたら該当なしになる

A. v1.1.0以降は **末尾の最小行政単位を抽出して検索**するので大丈夫です。「横浜市港北区」→「港北区」として検索されます。

該当なしの場合は **その都道府県の prepare がまだ未実施**です：

```
/companion:prepare 神奈川
```

### Q10. 目黒区・練馬区など末尾0コードの区が「集計対象なし」になる

A. v1.1.2 以前のバグです。Q5 の手順で v1.1.3 以降に更新してください。

### Q11. 神奈川を prepare したら東京のデータが消えた

A. v1.1.3 以前の上書き仕様です。**v1.1.4 で差分追記方式に変更済み**なので、Q5 の手順で v1.1.4 以降に更新してください。

```
/companion:prepare 東京   → 東京残ったまま
/companion:prepare 神奈川 → 東京＋神奈川になる
```

### それでも解決しない場合

DM までどうぞ。**画面のスクショを送ってもらえれば、その場で原因を見つけます**。

- X / note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)

実際の詰まり点は順次 [N03 解説記事](#) のQ&Aに反映していきます。

---

## 設計思想

### 公開データだけを使う
業者ログイン必須サービスはこのリポジトリでは扱いません。すべての分析はオープンデータで再現可能。

### APIキー前提（最新データで毎回分析）
集計済みCSVの同梱はしません。**毎回最新データを取得**して分析します。年次更新時もスクリプト再実行で即対応。

### Slash command で対話起動
CLI でも動きますが、**Claude Code の slash command を使えば自然文で完結**します。エンジニア知識ゼロでも使える設計を目指しています。

### skillは記事と1:1
1記事1skill（または少数）の対応で、**記事を読んだ読者が即同じ分析を自社で動かせる** 状態を作ります。

### 更新前提・差分追記
- データは年次更新（地価は毎年、住宅・土地統計は5年に1度）
- prepare は差分追記方式（必要な都道府県を段階的に追加可能）
- skillは v1.x.y の小バージョンで継続更新

---

## ロードマップ

| バージョン | 内容 | 時期 |
|---|---|---|
| v1.0.0 | inheritance-hotspots（東京23区・データ同梱） | 2026-05-02 |
| v1.0.1 | APIキー前提に再設計 | 2026-05-02 |
| v1.0.2 | 顧問フィードバック反映（DM CTA／pyproject.toml） | 2026-05-02 |
| v1.1.0 | 全国対応＋slash command＋PEP 723 | 2026-05-03 |
| v1.1.1 | マルチバージョンcache対応 | 2026-05-03 |
| v1.1.2 | 政令市親判定の構造化（目黒区・練馬区誤除外を修正） | 2026-05-03 |
| v1.1.3 | マークダウン出力＋ファイル保存（出力省略回避） | 2026-05-03 |
| **v1.1.4** | **差分追記の prepare（都道府県を段階的に追加可能）** | **2026-05-03** |
| v1.2.0 | 自社CSV取込（自店舗位置→半径Xkmで再ランキング） | 2026-06 |
| v1.3.0 | 世帯年収・空き家率を加えた多軸分析 | 2026-07 |
| v2.0.0 | competitor-overlay skill 追加／MCP統合 | 2026-Q3 |

---

## ライセンス

MIT License — [LICENSE](LICENSE)

## 作者

[etsurouwatanabe-tech](https://github.com/etsurouwatanabe-tech)
note: [@etsuro_watanabe](https://note.com/etsuro_watanabe)

不動産仲介業のAI伴走に関するご相談は X / note の DM からどうぞ。
