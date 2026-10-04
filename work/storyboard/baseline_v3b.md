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
| コードの基準 | git コミット `2693956`(main)。同じ位置にローカルタグ `baseline-v3b-2026-10-04` を付けたが、**この環境ではタグをGitHubへpushできなかった**(接続エラー)ため、リモートにはコミット番号で残す | `build_mv.py` の状態 |

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

## 変種(variant)の作り方(baselineを変えずに1箇所ずつ試す)
- `build_mv.py` の `VARIANTS` に、基準のカット表への小さな差分を名前付きで登録する。基準のカット表(`CUTS`)は変更しない。
- `python3 scripts/build_mv.py --variant <name>` → `output/preview/mv_<name>.mp4` と `work/storyboard/variants/<name>/timeline.md`(基準の `timeline.md` は上書きしない)。
- `MV_VARIANT=<name> python3 scripts/check_baseline.py` で固定地点(R6/R7/END)が変わっていないことと、変更した行の一覧を確認。
- `python3 scripts/variant_diff.py <name>` で、baselineとのフレーム比較・変更窓の外が同一であることの確認(`diff_vs_baseline.md`)。
- 登録済み: `v3c_r3b`(0:52.32 R3b。下記)。

### v3c_r3b (0:48〜0:56 だけを変更)
- 変更: R3(虹パン)の終わりを52.0→51.9秒、別構図の虹R3b(51.9〜53.7、押し込み)を挿入、p014は53.7〜56.0(パンの始点を.34→.40)。
- 変更窓の外・R6/R7/ENDは、baselineとフレームが完全一致(PSNR 99dB)。
- 比較資料: `work/storyboard/variants/v3c_r3b/`(`diff_vs_baseline.md`、`compare_baseline_vs_variant.jpg`、`rainbow_cues.md`、`timeline.md`)。

### v3d_r3_continuous (v3c_r3b の方向を採用し、再カットをなくした版。0:48〜0:56 だけを変更)
- 変更: R3(0:48.00)とR3b(0:52.32)を**一本の連続した虹ショット**(0:48.00〜0:53.70)にした。カメラは虹の奥/光の方向へゆっくり進み続け、0:52.32「虹の向こうで」の歌唱中も途切れない。同じ画像の切り直しカットはない。
- 0:53.70から p014 へ0.8秒で柔らかくディゾルブ(p014のパンの始点は.34→.40)。
- RAINBOW_03a-2(新規虹画像)は保留・制作不要。
- 比較資料: `work/storyboard/variants/v3d_r3_continuous/`。R6 / R7 / END と、編集窓の外はbaselineと一致。
- `v3c_r3b`(再カット版)は比較のため残してある。
