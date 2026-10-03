# video_requests (C候補: AI動画にしたいカット)

preview v1 を観て確定する前の**候補**。確定したものだけ残す。画像はすべて `assets/images/art_<key>_png.jpg`。

## 1. 扉が開く — 2:22.0〜2:25.0 (3秒) / 次の「入んな」へつなぐ
- 元画像: `p064_065_door` (右半分: 扉の前に立つ女の子)
- 必要秒数: 3〜4秒(使用3.0秒)
- 動かす対象: 扉がゆっくり内側へ開き、暖かい光が路地へこぼれる。ランタンの炎の微かな揺れ、女の子の髪が風で少し揺れる。
- 動かしてはいけない対象: 女の子の顔・服・髪飾り(白い花)・バッグ、扉の造形、背景の街並み・月。
- カメラ: 固定、またはごく僅かな dolly in。
- prompt: "Warm anime-style night alley. The wooden door in front of the girl slowly opens inward, golden light spilling out onto the cobblestones. Lantern flames flicker gently, her long hair sways slightly in a soft breeze. Camera nearly static, very slow push-in. Keep the girl's face, outfit, hair flower and bag exactly as in the source image. No new characters, no text."

## 2. 親分がこちらを見る — 2:34.0〜2:40.0 (使用4秒程度)
- 元画像: `p070_071_oyabun` (左: カウンターの親分と女の子)
- 動かす対象: 親分の湯呑みの湯気、耳のわずかな動き、ランタンの揺れ。頬杖のまま、視線だけゆっくり女の子の方へ。
- 動かしてはいけない対象: 親分の顔立ち・紫の鉢巻・星月柄の着物・首飾り、女の子の顔と髪飾り。大きな動き(立ち上がる等)は不可。
- カメラ: ゆっくり左→右のパン。
- prompt: "Anime-style cozy space tavern counter. The large rabbit boss rests his chin on his paw; only his eyes and ears move slightly as he looks toward the girl. Steam rises from the cup, lanterns flicker, stars outside the window twinkle. Slow pan left to right. Preserve both characters' faces and costumes exactly. No text."

## 3. 宇宙酒場への到着 — 2:52.5〜2:57 (エンドカード頭、4〜5秒)
- 元画像: `p088_welcome` (星空と天の川、親分アップ、湯気の立つ湯呑み)
- 動かす対象: 湯気、窓の外の星のまたたき、天の川の微かな流れ、ランタンの灯り。
- 動かしてはいけない対象: 親分の顔・鉢巻・着物・首飾り、手前の椅子。画面下側はQRと文字を載せるので大きな動きなし。
- カメラ: ごくゆっくりのdolly in(2〜4%)。
- prompt: "Anime-style close-up of the large rabbit boss at a wooden counter in a space tavern, the Milky Way and a harbor town visible through the window. Gentle steam from the cup, twinkling stars, softly flickering lanterns. Extremely slow push-in. Keep the character's face, purple headband, star-and-moon kimono and necklace unchanged. No text."

## 備考
- 秒数はpreview v1のtimeline.md準拠。`scripts/build_mv.py` の CUTS で `p0xx` を動画ファイルに差し替える改修は第2版で行う(Skillはまだ改造しない)。
