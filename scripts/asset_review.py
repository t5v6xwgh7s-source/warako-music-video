#!/usr/bin/env python3
"""Writes work/storyboard/asset_review.md: per-cut quality review of the HTML-extracted preview images.

Auto metrics (resolution, upscale factor, estimated JPEG quality, fold/seam strength, whether the camera path crosses the fold)
are measured here; the classification and the recommended action are editorial notes kept in NOTES below.
A = usable as-is in a final   B = replace with the original image   C = would gain from AI video   D = solved by camera/composition
"""
import importlib.util, os
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_mv", os.path.join(ROOT, "scripts/build_mv.py"))
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

STD_LUMA = [16,11,10,16,24,40,51,61,12,12,14,19,26,58,60,55,14,13,16,24,40,57,69,56,14,17,22,29,51,87,80,62,
            18,22,37,56,68,109,103,77,24,35,55,64,81,104,113,92,49,64,78,87,103,121,120,101,72,92,95,98,112,100,103,99]

def jpeg_quality(im):
    q = im.quantization.get(0)
    if not q:
        return None
    ratio = np.mean(q) / np.mean(STD_LUMA)
    scale = ratio * 100
    return round((200 - scale) / 2 if scale <= 100 else 5000 / scale)

def seam_strength(im):
    a = np.asarray(im.convert("L"), dtype=float)
    h, w = a.shape
    d = np.abs(np.diff(a, axis=1)).mean(0)
    cs = w // 2
    col = a.mean(0)
    line = abs(col[cs - 1:cs + 2].mean() - np.r_[col[cs - 8:cs - 3], col[cs + 4:cs + 9]].mean())
    return float(max(d[cs - 4:cs + 3]) / np.median(d)), float(line)

NOTES = {
 "p001_title": ("A", "暗いボケ主体。最大約1.7倍拡大でも破綻なし。", "そのまま。"),
 "p002_003_warmth": ("A", "毛並みのマクロ。ディテールが少なく拡大に強い。", "そのまま。"),
 "p004_005_snow": ("D", "ノドに白い溝(線強度170)。左頁=路地、右頁=ゴミ袋の陰のうさぎ。パンすると溝を横切る。", "解決済み: 左頁→右頁の片頁表示(静止→ゆっくりズーム)。元画像が来ても同構図で十分。"),
 "p006_007_stop_waiting": ("A", "継ぎ目弱。うさぎの顔は切れていない。", "そのまま。"),
 "p008_009_found": ("A", "3:2画像で上下が約16%クロップされるが、女の子・足跡・ランタンは収まる。立っている人物の頭部は元から画面外(絵本の意図)。", "そのまま。"),
 "p010_011_distance": ("A", "継ぎ目弱で連続した床。", "そのまま。"),
 "p012_013_every_day": ("D", "ノド強(白線+内容不連続)。左頁=女の子とうさぎとごはん、右頁=昼と夜の二枚積み。見開きのままパンすると継ぎ目が目立つ。", "解決済み: 左頁→右頁の片頁表示(静止)。右頁の昼/夜の積み重ねは『昨日・今日・明日』を表せるので原画があれば活かせる。"),
 "p014_015_first_step": ("A", "継ぎ目は弱いが連続した床をパンで横断。目立たない。", "そのまま。気になる場合のみパン幅を縮める。"),
 "p016_017_safe": ("A", "継ぎ目なし。", "そのまま。"),
 "p018_019_seasons": ("A", "継ぎ目に線(27)があるが、窓の外が春夏→秋冬へ切り替わる絵本の意図的な構図で、パン横断は不自然でない。", "そのまま。"),
 "p020_021_farewell": ("A", "連続したベンチ。静止で使用。", "そのまま(長く止める)。"),
 "p022_023_new_friend": ("A", "継ぎ目なし。", "そのまま。"),
 "p024_025_meals_naps": ("D", "ノド中〜強(線9)。左=ごはん、右=お昼寝で別構図。", "解決済み: 左頁→右頁の片頁表示。"),
 "p026_027_seasons": ("D", "1536x1024の中に縦長4コマ(各384px幅)。パンやズームでコマ境界が3本とも強調される。1コマ単位だと5倍拡大で破綻。", "解決済み: 4コマ全体を一枚で静止(ズーム最小)。個別に使いたい場合のみ元画像(B)。"),
 "p028_029_love": ("D", "ノド強(線27)。左右が別々の絵(どちらも女の子とうさぎ)。", "解決済み: 左頁→右頁の片頁表示。"),
 "p030_031_farewell": ("A", "**既存45枚で虹が描かれているのはこの左頁のみ**。ノド強(線122)のため片頁で使用。v3bでは虹の6段階(R1上部クロップ(淡)/R2拡大(強)+頁全体/R3虹に沿ってパン/R4うさぎの後ろ姿つきの寄り/R5虹の光へ寄る/R7最後の虹→光)に仮置き。切り出しは頁の上部31%に限られ(下はうさぎの耳が入る)、最大約3.5倍拡大でやわらかい。右頁(空いた寝床)は98〜104.75秒。", "R2はAのまま最終版でも可。**R1・R3・R4・R5は同じ絵の再利用なのでB: 新規静止画 RAINBOW_01 / 03a,b,c**(image_requests.md)。"),
 "p032_033_quiet_room": ("D", "ノド中(線15)。左=冬の窓辺、右=夕方の窓辺で内容が不連続。", "解決済み: 片頁表示。"),
 "p034_035_figurine_found": ("D", "ノド中(線14)。左=女の子、右=黄金のうさぎの置物。", "解決済み: 左頁→右頁(置物)。"),
 "p036_037_figurine_home": ("D", "ノド中(線16)。左=置物を抱く女の子、右=置かれた置物。", "解決済み: 片頁表示。"),
 "p038_039_not_a_replacement": ("D", "ノド中(線13)。左右で女の子の姿勢が違う別絵。", "解決済み: 片頁表示。"),
 "p040_041_shadow": ("D", "ノド弱〜中。左=大きな影と置物(鍵)、右=振り返る女の子。ズームで継ぎ目に近づく。", "解決済み: 左頁(影)→右頁。『影が動く』はC候補(video_requests参照外・任意)。"),
 "p042_043_lost": ("D", "ノド中(線15)。左=人混みの女の子、右=路地で別構図。", "解決済み: 片頁表示。"),
 "p044_045_voice": ("A", "継ぎ目なし。", "そのまま。"),
 "p060_061_light": ("A", "継ぎ目弱。", "そのまま。"),
 "p064_065_door": ("A", "継ぎ目弱。見開き全体で連続。", "静止で使用。C候補: 扉が開く瞬間(video_requests.md 1)。"),
 "p066_067_come_in": ("A", "継ぎ目なし。v3bでR6(虹の向こうで会えたなら)の位置。虹は描かず、光のブルームで扉の向こう側へ越える遷移。", "D: このまま。任意でRAINBOW_04(新規静止画)またはC候補4(video_requests.md)。"),
 "p068_069_first_sight": ("A", "細い線(11)があるがカウンターが連続。パン量小。", "そのまま。"),
 "p070_071_oyabun": ("A", "継ぎ目弱。顔・耳は切れていない。", "C候補: 親分が視線を向ける(video_requests.md 2)。"),
 "p080_081_recognition": ("D", "3:2。左=雪の日、右=酒場の対比(意図的なダイプティク)。ノドは目立つが意味がある。", "v3bでは使用しない(「やっと気づいたか」は答えを説明するため、親分の余白を優先して外した)。素材は温存。"),
 "p084_085_empty_seat": ("A", "継ぎ目弱。v3bでは「またねじゃなくて」(2:52.8〜)の親分と空いた席。静止。", "そのまま。C候補3(宇宙酒場への到着)にも使える。"),
 "p086_087_home": ("A", "継ぎ目弱。v3bでは「同じ空を見上げて笑おう」(2:40.4〜2:47.6)の空と光。虹の絵は入れない。", "そのまま。"),
 "END_CARD": ("B", "仮置き: 絵本の最終見開き(1254x1254)を16:9に切り出し(約1.5倍拡大)。専用の『宇宙酒場_親分』画像とQRが未取り込み。", "assets/images/oyabun_bar.(jpg|png) と assets/qr/*.png を置いて再ビルドで自動差し替え。新画像に『おかえりなさい』の文字がある場合は歌詞『おかえりって』と二重になるため、その部分を避ける/外す。C候補: 宇宙酒場への到着(video_requests.md 3)。"),
}

def main():
    dur = bm.audio_duration()
    cuts = bm.resolve_cuts(dur)
    groups = {}
    for c in cuts:
        groups.setdefault(c["key"], []).append(c)
    rows, auto = [], []
    for key, cs in groups.items():
        segs = []
        for c in sorted(cs, key=lambda c: c["t0"]):
            if segs and abs(segs[-1][1] - c["t0"]) < 1e-6:
                segs[-1][1] = c["t1"]
            else:
                segs.append([c["t0"], c["t1"]])
        trange = ", ".join(f"{bm.ts(a)}-{bm.ts(b)}" for a, b in segs)
        path = bm.img_path(key)
        im = Image.open(path)
        w, h = im.size
        q = jpeg_quality(im)
        ratio, line = seam_strength(im) if w / h > 1.2 else (0, 0)
        ups, modes = [], []
        for c in cs:
            z = max(c["cf"][2], c["ct"][2])
            pg = c["page"]
            if pg and len(pg) == 2:                      # full-bleed crop inside one page
                ups.append(bm.W / (w / 2 / z)); modes.append(f"{pg[0]}頁クロップ")
            elif pg:                                      # whole page on blurred backdrop
                ups.append((bm.H - bm.PAGE_TOP) * z / h); modes.append(f"{pg}頁全体")
            else:
                bw = (h * 16 / 9 if w / h >= 16 / 9 else w) / z
                ups.append(bm.W / bw); modes.append("見開き")
        up = max(ups)
        mode = " + ".join(dict.fromkeys(modes))
        cls, prob, act = NOTES[key]
        rows.append((key, trange, os.path.relpath(path, ROOT), cls, prob, act))
        auto.append((key, f"{w}x{h}", mode, f"{up:.2f}x", f"~{q}" if q else "-", f"{ratio:.1f}", f"{line:.0f}"))
    out = ["# asset review (HTML抽出画像 = 試写用素材) v3", "",
           "A = HTML抽出画像のまま最終版でも使用可 / B = 元画像への差し替えを推奨 / C = AI動画化すると効果的 / D = カメラワーク・構成変更で解決済み(または解決可能)", "",
           "判定方針: 継ぎ目(ノド)が見えたら新規画像を要求せず、①パン停止 ②ズーム量を減らす ③中心移動 ④片頁クロップ ⑤表示時間を短く、の順で救済。今回は④(片頁を全体表示、背景は同じ頁のぼかし)で解決。画像生成AIによる描き直しはしていない。", "",
           "## cut review", "", "| cut | time | source | classification | problem | recommended_action |", "| --- | ---- | ------ | -------------- | ------- | ------------------ |"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    n = {k: sum(1 for r in rows if r[3] == k) for k in "ABCD"}
    out += ["", f"集計: A={n['A']} B={n['B']} D={n['D']} (C候補は A/B の備考に併記: 扉が開く / 親分の視線 / 宇宙酒場への到着)", "",
            "## auto metrics", "", "| cut | source size | mode | max upscale to 1080p | est. JPEG quality | fold edge ratio | fold line |", "|---|---|---|---|---|---|---|"]
    for a in auto:
        out.append("| " + " | ".join(a) + " |")
    out += ["", "- 拡大率は最大でも約1.7倍(p001: 暗いボケ)。見開きは約1.3〜1.5倍、片頁は1.1倍以下で、解像度不足は目立たない(ズームイン最大のp016でも1.5倍)。",
            "- HTML埋め込みJPEGは1枚約100〜340KB、推定品質は全画像82前後で『強い圧縮』ではない。暗部のバンディング/ブロックノイズは暗い雪景色・夜景(p004/p006/p064〜)で出やすいので、元画像が来たらそこを優先して比較。",
            "- 絵本本文はHTML側のオーバーレイで、抽出画像自体に文字は含まれていない(確認済)ため、歌詞テロップとの競合はない。ただし新しい『宇宙酒場_親分』画像は画像内に『おかえりなさい』の文字を含むので注意。",
            "- **虹素材の調査(v3)**: 45枚を目視で確認し、虹が描かれているのは p030_031_farewell の左頁のみ。他は雪・室内・夜景・酒場で、虹の合成は画質を落とすので行っていない。新規が必要な虹は `work/generated/image_requests.md` に RAINBOW_01 遠い虹 / 02 会いたい虹 / 03a,b,c 近づいた虹 / 04 向こう側へ届く虹 として記録(まだ生成していない)。",
            "- 顔の切れ: 見開きの16:9窓は縦いっぱいの全高(3:2画像のみ上下約16%クロップ)で、顔の切れは確認されない。片頁表示は頁全体を表示。"]
    open(os.path.join(ROOT, "work/storyboard/asset_review.md"), "w", encoding="utf8").write("\n".join(out) + "\n")
    print("\n".join(out[:60]))

if __name__ == "__main__":
    main()
