# v3d_r3_continuous vs baseline_v3b

baseline: `output/final/baseline_v3b/mv_v3b_baseline_1080p.mp4`(変更しない) / 比較版: `output/preview/mv_v3d_r3_continuous.mp4`

## 変更したカット行(これだけ)

| 区分 | cut | start | end | transition | tag | 内容 |
|---|---|---|---|---|---|---|
| baseline | p030_031_farewell[Lc] | 0:48.00 | 0:52.00 | dissolve 0.5s | R3 | R3 少し近づいた虹。虹の奥へ視線が進む |
| baseline | p014_015_first_step | 0:52.00 | 0:56.00 | dissolve 1.0s | - | 自分の足で近づく(虹を残さず記憶へ戻る) |
| **変更後** | p030_031_farewell[Lc] | 0:48.00 | 0:53.70 | dissolve 0.5s | R3 | R3 + R3b 一本の連続した虹ショット: 虹の奥/光の方向へゆっくり進む(52.32「虹の向こうで」の間も止めない) |
| **変更後** | p014_015_first_step | 0:53.70 | 0:56.00 | dissolve 0.8s | - | 記憶の中の少女とうさぎ → 自分の足で進む(虹から柔らかく) |

全体の長さ: 変わらない。差が出る時間帯は 48.0〜56.0 秒のみ。

## 固定地点(R6 / R7 / END)の確認

| 地点 | baselineとのフレーム一致 (PSNR dB) | 判定 |
|---|---|---|
| R6 2:27.54 | 99.0 | 変化なし |
| R7 2:48.40 | 99.0 | 変化なし |
| END 2:59.00 | 99.0 | 変化なし |
| END またねじゃなくて 2:53.9 | 99.0 | 変化なし |

## 変更箇所の外が変わっていないこと

2秒おき(編集窓 47.5〜56.5秒を除く)のフレームをbaselineと比較: 最小PSNR 48.2 dB。 すべて一致(圧縮ノイズの範囲)。

## フレーム比較

`compare_baseline_vs_variant.jpg`(上段 baseline / 下段 変更版。0:51.5〜0:55.2)

## 結論(機械的な確認)

- 固定地点: 変化なし
- 変更窓の外: 変化なし
