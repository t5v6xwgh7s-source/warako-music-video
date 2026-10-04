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

## 3. 宇宙酒場への到着 — 2:52.8〜2:57 (エンドカード頭、4〜5秒。「またねじゃなくて」の親分と空いた席)
- 元画像: `p088_welcome` (星空と天の川、親分アップ、湯気の立つ湯呑み)
- 動かす対象: 湯気、窓の外の星のまたたき、天の川の微かな流れ、ランタンの灯り。
- 動かしてはいけない対象: 親分の顔・鉢巻・着物・首飾り、手前の椅子。画面下側はQRと文字を載せるので大きな動きなし。
- カメラ: ごくゆっくりのdolly in(2〜4%)。
- prompt: "Anime-style close-up of the large rabbit boss at a wooden counter in a space tavern, the Milky Way and a harbor town visible through the window. Gentle steam from the cup, twinkling stars, softly flickering lanterns. Extremely slow push-in. Keep the character's face, purple headband, star-and-moon kimono and necklace unchanged. No text."

## 備考
- 秒数はpreview v1のtimeline.md準拠。`scripts/build_mv.py` の CUTS で `p0xx` を動画ファイルに差し替える改修は第2版で行う(Skillはまだ改造しない)。

## 4. 虹の向こうへ届く瞬間(R6) — 2:26.8〜2:30.0 (使用3〜4秒) / 第一候補
- 対応する歌声: 「虹の向こうで会えたなら」(推定 2:27.5〜2:31.5)。虹の物語の最大の転換点。「虹を見る側」→「虹の向こう側」。
- 第一候補(ユーザー指定): **カメラがゆっくり虹／光の境界を越え、暖かな世界へ入っていく。** 派手なファンタジー映像にしない。
- 元画像: 新規静止画 RAINBOW_04(`image_requests.md`)が来た場合はそれ。無ければ `p066_067_come_in`(扉の向こうの暖かな光)。
- 動かす対象: 淡い虹の光が背後へ流れて消え、前方の暖かな光が画面いっぱいに広がる。髪と光の粒がわずかに揺れる。扉がもう少しだけ開く。
- 動かしてはいけない対象: 女の子の顔の向き・服・髪飾り・バッグ。虹を主役にしない。説明的な動き(振り返る・誰かが現れる)は不可。
- カメラ: 固定の位置からごくゆっくりのdolly in。境界(光のにじみ)を通り抜ける。
- prompt: "Anime-style, a girl seen from behind at a glowing wooden door in a lantern-lit alley. The camera glides slowly forward through a faint boundary of rainbow-tinted light into a warm golden world; the rainbow glow drifts behind and fades, warm light widens. Hair and light particles move slightly. No face shown, no new characters, no text. Not flashy fantasy."
- 備考: v3bの試写では静止画+光のブルーム遷移で成立する見込み。静止の余韻を優先し、AI動画は必要が確認できたときだけ。

## 更新メモ(v3b)
- 歌詞テロップ・タイトルを外したため、「歌声 × 映像」で意味が伝わるかが基準。扉(1)・視線(2)・宇宙酒場(3)・虹の向こうへ届く(4)は、いずれも**静止のままの試写で足りないと分かった場合のみ**発注する。
- 時間はv3bのタイムラインに合わせた(扉 2:22 / 視線 2:34 / 宇宙酒場(おかえりって) 2:59 / 届く瞬間 2:26.8)。
- 「おかえりって」(2:59〜)はカメラをほぼ動かさず、親分と虹なし・文字なしで着地させる。
