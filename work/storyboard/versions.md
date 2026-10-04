# versions (版の一覧)

| 版 | 状態 | 動画 | 内容 | 記録 |
|---|---|---|---|---|
| `baseline_v3b` | **凍結(基準版)** | `output/final/baseline_v3b/mv_v3b_baseline_1080p.mp4`(+720p) | 歌詞・タイトルなし、虹キュー R1〜R7、QRは曲終了後の独立カード | `work/storyboard/baselines/baseline_v3b.json`、`baseline_v3b.md` |
| `v3c_r3b` | 比較履歴 | `output/preview/mv_v3c_r3b.mp4` | 0:52.32 の虹をつなぐため、同じ虹を別構図で寄り直す(R3→R3bの切り直しあり) | `work/storyboard/variants/v3c_r3b/` |
| `v3d_r3_continuous` | **現時点の採用候補**(人間の最終採否は未) | `output/final/candidate_v3d_r3_continuous/candidate_v3d_r3_continuous_full.mp4`(+proxy 720p) | R3とR3bを一本の連続した虹ショット(0:48.00〜0:53.70)にし、0:53.70から p014 へ0.8秒で柔らかくディゾルブ | `work/storyboard/baselines/candidate_v3d_r3_continuous.json`、`work/storyboard/variants/v3d_r3_continuous/` |

- 3版とも R6(2:27.54) / R7(2:48.40) / END(2:59.00) は同一(フレーム一致)。
- `output/` はGit管理外。このコンテナは使い捨てなので、動画は手元にも保存すること。
- 次の修正は、採用候補を基準に、新しいvariantとして作る(baseline・候補は上書きしない)。
- 見つかった編集ルール: 「歌詞の単語に合わせてカットする」のではなく、**その言葉が届くための時間を映像側に作る**(歌より少し前から準備し、歌唱中は同じ世界に留まり、同じ絵の再カットより連続した動きで受け止める)。→ `music-video-maker` Skill §4。
