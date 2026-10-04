# baseline v3b (2026-10-04) — 最終確認候補として保持

## 内容(この版を基準として保存)
- 歌詞・タイトルなし。虹キュー R1〜R7(`rainbow_cues.md`)。32カット構成(片頁表示の12カットを含む)。
- 「おかえりって」(2:59〜)は手を差し伸べる親分(宇宙酒場の画像・虹/字幕/台詞なし)。
- **QRは曲終了後の独立カード**(3:04.16〜3:17.16)。本編中にはQRを表示しない。説明文・CTA・タイトルなし。作品終了後の静かな入口。
- QRのリンク先: `https://ichingeki.warako39stars.com/oyabun_readable.html`(正しいものとして進行)。

## ファイル
| 何 | どこ | 備考 |
|---|---|---|
| 基準版 1080p | `output/final/baseline_v3b/mv_v3b_baseline_1080p.mp4` | 読み取り専用(chmod 444)。SHA256: `05e93500…c9c8b3`(全体は `SHA256SUMS`) |
| 基準版 720p | `output/final/baseline_v3b/mv_v3b_baseline_720p.mp4` | 送信用(25MB) |
| 基準のスナップショット | `work/storyboard/baseline_v3b.json` | カット表・固定行・QR設定 |
| 固定チェック | `scripts/check_baseline.py` | R6/R7/ENDが変わると失敗する |
| 視聴確認ポイント | `work/storyboard/listening_checkpoints.md` | 3地点と記入欄 |
| コードの基準 | git タグ `baseline-v3b-2026-10-04` | `build_mv.py` の状態 |

`output/` はGit管理外(大きなメディア)。このコンテナは使い捨てなので、**基準版のmp4は、ダウンロードして手元にも保存してください。**
コード(タグ)から `python3 scripts/build_mv.py` で、同じ映像を再生成できる(素材: `assets/audio/song.m4a`、`assets/images/*`、`assets/qr/qr.png` が必要)。

## 上書き事故の防止
- `build_mv.py` は、`output/final/` 内の既存ファイルへの書き出しを拒否する(通常の書き出し先は `output/preview/mv_preview.mp4`)。
- `output/final/baseline_v3b/` は読み取り専用。新しい版は別の名前(例 `baseline_v3c/`)で保存し、過去の基準版は消さない。
- `lyrics_timing.tsv` に `# LOCK` 行。`lyric_sync.py` は `--force` なしでは上書きしない(手編集した位置を消さないため)。

## 高解像度の宇宙酒場原画が来たとき
- `assets/images/oyabun_bar_hires.jpg`(または .png)として置いて再ビルドするだけ。**現在の構図・クロップは変わらない**(窓位置は画像に対する割合: 中心 横50%・縦35%、ズーム1.0→1.03)。
- 条件: アスペクト比が現在と同じ **2:3(縦長)**。違う場合は警告を出す(構図が変わるため、目で確認してから採用する)。
- 現在の画像は `assets/images/oyabun_bar_v1_900x1350.jpg` に控えがある。置き換えると `check_baseline.py` が「end_card_image が変わった」と報告する(固定地点のタイミングは変わらない)。
- 差し替えたら、END の3地点を目で確認する(顔・手・徳利が窓に収まっているか)。
