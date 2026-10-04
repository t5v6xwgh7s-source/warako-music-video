# image_requests (新規静止画の依頼リスト) v3b

方針: 虹は「離れた二つの場所をつなぐもの／まだ会えていない存在との距離／向こう側へ続く道」。
遠くに現れる → 向こうに会いたい存在がいる → 少しずつ近づく → 向こう側へ届く → 虹が役目を終える → 帰る場所(親分)。
**既存の絵本の絵を描き直さない / 既存の絵へ虹を合成しない。** 新規は差し込み用の静止画だけ。まだ生成していない。

## 既存素材の調査結果

- 既存45枚(HTML抽出)のうち、**虹が描かれているのは `p030_031_farewell` 左頁(虹の橋)の1枚だけ**。
- v3b の試写では、この1枚を切り出しとカメラ(R1 上部クロップ / R2 虹の拡大 / R3 虹に沿ってパン / R4 うさぎの後ろ姿つきの寄り / R5 虹の光へ寄る / R7 虹→光)で仮置きした。
  ただし同じ絵の再利用なので、R1〜R5 が似て見える。**RAINBOW_01〜03 が来たら差し替え、同じ絵は最大でも1回(R2)に減らす。**
- 切り出しは頁の上部31%に限られる(下はうさぎの耳が入る)。拡大は最大約3.5倍で、淡い空だから破綻は目立たないが、画質は仮。

分類: A=既存で対応可 / B=新規静止画が必要 / C=AI動画化すると効果的 / D=カメラ・編集のみで対応可

| 段階 | cue | 時間(推定) | 歌詞 | 現在の仮置き | 分類 |
|---|---|---|---|---|---|
| RAINBOW_01 遠い虹 | R1 / R7 | 18.1-23.2 / 167.6-170.6 | 空にかかった虹が／虹の向こうで(最後) | p030左頁の上部(淡く彩度を下げたクロップ) | **B** |
| RAINBOW_02 会いたい虹 | R2 | 33.7-38.6 | 虹の向こうで会いたい(1回目) | p030左頁の虹を拡大+彩度を少し上げる / 続けて頁全体(うさぎの後ろ姿が遠くに) | A(最終版でもほぼ可。画像が来たら比較) |
| RAINBOW_03 近づいた虹 | R3 / R4 / R5 | 48.0-52.0 / 75.4-81.4 / 88.1-92.25 | 虹の向こうで／もう一度(1回目) / 虹の向こうで会いたい(2回目) / 虹の向こうで／もう一度(2回目) | p030左頁の別の切り出し3種 | **B (3構図)** |
| RAINBOW_04 向こう側へ届く虹 | R6 | 146.8-150.0 | 虹の向こうで会えたなら | p066 扉の向こう側へ(光のブルームで越える)。虹は描かない | D / 任意でB・C |

## RAINBOW_01 = 遠い虹 (R1: 18.1〜23.2秒 / R7の最初にも再利用可)

- 使用位置: 1番Aメロ「空にかかった虹が／未来をつないだ」。雪の路地(p004)の後、「待つのをやめた」(p006)の前。R7(最後の虹)にも同じ絵を使ってよい(始まりと終わりの対)。
- 対応する歌詞: 空にかかった虹が／未来をつないだ
- 必要な構図: 16:9。雨上がりの淡い空に、遠くに小さくかかる自然な虹。広い空、低い地平線、遠景に小さな街並みや丘。虹は画面の右上〜中央、画面幅の1/3程度。
- 色: 雨上がりの水色と灰白色の雲、虹は淡く(彩度低め)。雪の青から暖色へ向かう手前の、かすかな明るさ。
- 人物/うさぎの有無: なし。
- 虹の位置: 遠い。手前に濡れた路面の反射があってもよい。
- 物語上の意味: 初めて「虹」が認識できる伏線。未来へつながっているが、まだ遠い。再会は見せない。
- prompt案: "Soft anime illustration, wide 16:9. A pale, natural rainbow appearing far away in a clearing sky just after rain, over a quiet distant town and hills. Wet street reflecting light in the foreground, low horizon, large calm sky, gentle blue-grey clouds. Muted pastel palette, hopeful but distant. No characters, no text. Painterly storybook style matching a warm picture book."

## RAINBOW_02 = 会いたい虹 (R2: 33.7〜38.6秒)

- 使用位置: 1サビの頭「虹の向こうで会いたい」。「虹」と歌う瞬間にすでに見えている。
- 対応する歌詞: 虹の向こうで会いたい／ひとりじゃないって思える
- 必要な構図: 16:9。R1より虹がはっきり大きく、色もはっきり。虹の向こう側に光や小さな気配(人影や金色の光)があるが、顔・種類は分からない。再会は見せない。
- 色: 水色の空に鮮やかな虹。向こう側は少し暖かな金色。
- 人物/うさぎの有無: 向こう側の小さな輪郭(後ろ姿か光のみ)。
- 虹の位置: 画面中央。虹の足元が遠くの丘の向こうに隠れている。
- 物語上の意味: 会いたいけれどまだ届いていない。
- 備考: 既存の p030左頁(虹の橋)で最終版でも成立する。新規が来たら比較して決める。
- prompt案: "Soft anime illustration, 16:9. A vivid but gentle rainbow arching over a green hill after rain; far beyond it, a small warm golden glow and the faint silhouette of a distant figure, impossible to identify. Large sky, no reunion, no faces. Painterly picture-book style, warm light. No text."

## RAINBOW_03 = 近づいた虹 (R3 / R4 / R5 の3構図)

R2とも互いにも同じ構図にしない。段階が進むほど虹との距離が縮まる。

- **03a (R3: 48.0〜52.0秒 / 1サビ「虹の向こうで／もう一度」)**: R2より少し近い虹。虹の奥へ続く道の遠近感で、視線が奥へ進む。人物なし。
  prompt案: "Soft anime illustration, 16:9. A winding path through a flower meadow leading toward the glowing foot of a rainbow in the distance, strong depth, gentle warm light after rain. No characters, no text."
- **03b (R4: 75.4〜81.4秒 / 2回目「虹の向こうで会いたい」)**: 時間が経った。虹を近くから見る/人物の後ろ姿の背後に虹。うさぎではなく女の子の後ろ姿(顔なし)でもよい。向こう側にまだ誰かの気配。再会はまだ。
  prompt案: "Soft anime illustration, 16:9. A girl seen from behind standing on a hill path, a larger rainbow arching right above her, wet grass sparkling, golden late-afternoon light; far beyond the rainbow a faint warm glow. Face never shown. No text."
- **03c (R5: 88.1〜92.25秒 / 2回目「虹の向こうで／もう一度」)**: もう少しで届く。虹の光が画面を横切り、向こう側の暖かな光が見えている。虹の足元の光の柱に近い。
  prompt案: "Soft anime illustration, 16:9. Looking along a path into the soft glowing light at the foot of a rainbow, rainbow colours dissolving into warm gold light that crosses the frame. No characters, no text."

## RAINBOW_04 = 向こう側へ届く虹 (R6: 146.8〜150.0秒) — 任意

- 現在の仮置き(p066 扉の向こう側へ、光のブルームで越える)で成立する場合は新規不要。
- 使うなら: 虹を越えた**向こう側**から見た光景。女の子が淡い虹の光の中を通り抜け、暖かな灯りの路地と半開きの扉が目の前にある。虹は背後で消えかけている。顔は見せない。派手なファンタジーにしない。
- 対応する歌詞: 虹の向こうで会えたなら／もう手を離さないよ
- 物語上の意味: 「虹を見る側」→「虹の向こう側」へ。会いたい→会えたなら。説明しない。
- prompt案: "Anime illustration, 16:9. A girl from behind stepping out of the last band of a fading rainbow into a warm lantern-lit alley; the rainbow is behind and above her, dissolving into soft light; ahead, amber windows and a half-open wooden door glowing. No other characters, no text."

## R7 虹の終わり(新規不要)

- 虹そのもの(RAINBOW_01の再利用または既存クロップ) → 虹色の光 → 暖かな光 → 宇宙酒場。「また」の後は虹を主役に戻さない。
- 任意で: 夕暮れの空の端に虹の残光が消えかけ、星と天の川へ移る空(人物なし)。現在は既存クロップで成立。

## 注意

- 新規画像の女の子は後ろ姿・顔なしにして、既存の基準画との顔の不一致を避ける。
- 画像に文字を入れない。
- 「おかえりって」の時には虹を出さない(R7で終わらせる)。

## 追記: RAINBOW_03a-2 (R3b: 0:52.3〜0:53.7) — 比較版 v3c_r3b の差し込み用(任意)

- 使用位置: 1サビの2つ目の「虹の向こうで」(52.32)。虹を見て → 虹へ向かい → 次の `p014_015_first_step` で一歩踏み出す、の「虹へ向かう」。
- 対応する歌詞: 虹の向こうで(2つ目。もう一度の直前)
- 必要な構図: 16:9。RAINBOW_03a(R3: 虹の奥へ続く道)とは別の構図。**視点が虹へ向かって歩いている感じ**(手前の道・足元から虹の方へ)。人物は後ろ姿か影だけ(顔なし)、または人物なしで足元の道だけ。虹は画面上部〜中央に明確に見える。
- 色: R3 よりやや暖かい昼の光。
- 物語上の意味: 虹を見る → 虹へ向かう → 自分の足で一歩(p014)。まだ会えない。
- prompt案: "Soft anime illustration, 16:9. A first-person view from just behind a girl's feet on a gentle flower path that leads up toward a clear rainbow in the upper part of the frame; her shadow or the hem of her skirt barely visible, face never shown. Warm daylight after rain, pastel colours, painterly picture-book style. No text."
- 現在の仮置き: 既存の p030 左頁の別の切り出し(押し込み)。**同じ絵の再構図なので、R3 とは見た目の差が小さい。** 新規画像が来たら差し替える。
