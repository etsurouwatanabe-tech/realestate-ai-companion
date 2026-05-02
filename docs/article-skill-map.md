# 記事 ↔ skill マップ

各記事と、それを再現・カスタムするための skill の対応表。

## 一覧

| 記事 | 媒体 | 関連skill | skill バージョン | 公開日 |
|---|---|---|---|---|
| 世田谷でも目黒でもない。東京23区で『見落とされた相続予備軍の鉱脈』を1区だけ挙げるなら | note | inheritance-hotspots | v1.1.0 | 2026-05-03（予定） |
| 公開データで自社エリアの相続予備軍を分析する。Claudeを触ったことがない方向け、30分のセットアップ手順 | note | inheritance-hotspots | v1.1.0 | 2026-05-04（予定） |

## 更新履歴

### 2026-05-03
- **inheritance-hotspots v1.1.0 リリース**
- 全国47都道府県対応＋slash command（`/companion:prepare`／`/companion:inheritance`）
- N02記事末尾CTA を v1.1.0 対応に更新
- N03 ハンズオン記事も v1.1.0 対応に更新

### 2026-05-02
- inheritance-hotspots v1.0.0 リリース（東京23区限定・データ同梱）
- v1.0.1：APIキー前提に再設計
- v1.0.2：顧問フィードバック反映（DM CTA／pyproject.toml）
- N02記事「東京23区 相続予備軍ホットスポット」ドラフト完成

## 記事の数値とskillの対応

### N02記事 → inheritance-hotspots

記事に登場する以下の数値はすべて skill から再現可能：

| 記事内の表現 | skill出力との対応 |
|---|---|
| 「スコア = 高齢者持ち家世帯数 × 中央値地価」 | `score.py` の `score_100oku` カラム |
| 「世田谷区が1位（436）」 | `score.py --wards 世田谷` |
| 「大田区4位、地価地味でも世帯数で押し切る」 | `--wards 大田` でタイプ「鉱脈型」が返る |
| 「足立25.5%、葛飾25.1%、北24.8%が高齢化TOP3」 | `aging_rate` カラムから確認可能 |
| 「持ち家率48〜49%」 | `elderly_owner_rate` カラム |
| 「23区を4タイプに分けて」 | `score.py` の出力で各区のタイプが判定される |

### 自社で再現するには

```bash
# 記事と完全に同じデータで動かす
python score.py --wards "世田谷,港,渋谷,大田"

# 自社の主力エリアで動かす
python score.py --wards "御社の主力区名"
```
