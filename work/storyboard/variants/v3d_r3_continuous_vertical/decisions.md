# v3d_r3_continuous 縦版(9:16, 1080x1920)— 判断記録

- 原器: `v3d_r3_continuous`(横版)。カット表(key, t0, t1, fade, tag, bloom)は横版・縦A・縦Bで完全一致(`MV_FORMAT` 切替で比較済み)。音声・R6 2:27.54・R7 2:48.40・END 2:59.00 は不変。横版の baseline/candidate/出力は無変更。
- 縦化は `scripts/build_mv.py` の `VERT_PLAN`(カットごとの構図)。中央クロップではなく、被写体(少女・うさぎ・親分・扉・光)ごとに cx/cy/zoom と緩いパンを指定。
- 虹カット(R1/R2/R3/R5/R7)の比較:
  - **A: blurred-extension版** — 横の虹帯を全部見せて幅に合わせ、ぼかし拡張で埋める。`output/preview/mv_v3d_r3_continuous_vertical_A_blurext.mp4`(基準標本・読み取り専用)。9:16 では虹が小さく弱い。
  - **B: fill版** — `--vfill`(`VERT_FILL`)。既存の p030 左頁を大胆に縦クロップし、虹と光で画面を満たす。左右の情報は捨てる。
    距離感: R1 遠い(アーチの左端・雲) → R2 アーチ中央 → R3 光へ寄る → R5 光の中 → R6 扉(向こう側)→ R7 最後の遠い虹(反対側)→ 虹色から暖色へ。
    うさぎの耳が下端にわずかに入るカットがある(R3/R5/R7 の一部)。気配として許容、気になる場合は cx を右下げ。
- 新しい虹画像は、この A/B 比較を人間が見るまで制作・依頼しない。
- QR: 曲後の独立カード。縦用に再配置(16px/module=720px の白台紙、実フレームで13/13秒デコード確認)。

## 採否(2026-10-04): **B(fill版)を縦版の正式candidateに採用**(人間の判断)
- 理由: Aは横画面の情報を保存するが、虹が小さく弱い。Bは「遠くに虹を見る → 近づく → 虹の中へ入る → 光の向こうへ進む」という意味と距離感を9:16で保てる。既存素材の柔らかさは許容。新規虹画像は作らない。
- 正式candidate: `output/final/candidate_v3d_r3_continuous_vertical/`(`..._full.mp4` 1080×1920 / `..._proxy.mp4` 720×1280、読み取り専用、`SHA256SUMS`)。manifest: `work/storyboard/baselines/candidate_v3d_r3_continuous_vertical.json`。
- 比較資料(不採用): `output/final/reference_v3d_r3_continuous_vertical_A_blurext/`、manifest `work/storyboard/baselines/reference_v3d_r3_continuous_vertical_A_blurext.json`、比較シート `compare_A_vs_B.jpg`。
- 最終検査(B, `mv_check.py --size 1080x1920 --extra-tail 13 --qr`): 全PASS(デコード/1080×1920/h264 yuv420p 30fps/aac/長さ197.17s=曲184.16+QR13/曲末に音声/黒画面なし/QRは13/13秒デコード一致)。
- タイミング: カット表(key,t0,t1,fade,tag,bloom)が横版・A・Bで一致。R6 2:27.54 / R7 2:48.40 / END 2:59.00 不変。
- SHA256: full `1c9916f98bbd26dca044c212efedc8659cac38c92a669f71147591a44aadc860` / proxy `7f27f1a59c0c333dd70199ccebf31274d9e529239b31a7a7b512200261b83dcb`。
- 既知の許容: R3/R5/R7の一部でうさぎの耳先が下端に入る。R5・R7後半は拡大でやや柔らかい。
- 横版baseline・横版candidate・YouTube投稿パッケージは未変更。
