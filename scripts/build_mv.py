#!/usr/bin/env python3
"""MV builder: stills + camera moves + dissolves + lyric captions -> H.264/AAC MP4.

Usage:
  python3 scripts/build_mv.py [--out output/preview/mv_preview.mp4] [--fps 30] [--crf 23]
                              [--timeline-only] [--limit SECONDS] [--frames t1,t2,... --frames-dir DIR]

* Frames are rendered with PIL (sub-pixel crop, no zoompan jitter) and piped to ffmpeg; audio is encoded once.
* CUTS / ANCHOR_OK below are the editorial decisions. Lyric timing lives in work/storyboard/lyrics_timing.tsv
  (written by scripts/lyric_sync.py, hand-editable). work/storyboard/timeline.md is regenerated on every run.
* Optional assets are picked up automatically when present:
    assets/qr/*.png            -> QR on the end card (un-rotated, opaque, white quiet zone, >= 10 s)
    assets/images/oyabun_bar.* -> used instead of the book's last spread for the end card (see END_CARD_IMAGE)
"""
import argparse, glob, os, subprocess, sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMAT = os.environ.get("MV_FORMAT", "")          # "vertical" = 1080x1920 (9:16) re-composition of the same cut list
VERTICAL = FORMAT == "vertical"
VFILL = VERTICAL and os.environ.get("MV_VFILL") == "1"   # rainbow cuts as bold full-bleed crops instead of fitted bands
W, H = (1080, 1920) if VERTICAL else (1920, 1080)
AUDIO = os.path.join(ROOT, "assets/audio/song.m4a")
IMG = os.path.join(ROOT, "assets/images")
FONT = os.path.join(ROOT, "assets/fonts/ZenMaruGothic-Medium.ttf")   # soft rounded gothic (OFL)
LYRICS_TSV = os.path.join(ROOT, "work/storyboard/lyrics_timing.tsv")
QR_GLOB = os.path.join(ROOT, "assets/qr/*.png")
QR_MIN_SECONDS = 10.0
QR_MODE = "after"      # "after": a QR card after the song ends (audio padded with silence); "overlay": QR over the end card
QR_TAIL = 13.0          # seconds of QR card after the song (fade-in 1.2s from black, fully opaque ~10.2s, fade-out 1.0s)
FADE_IN, FADE_OUT = 1.2, 1.2
SHOW_LYRICS = False     # v3 direction: no lyric telop, no title. lyrics_timing.tsv is kept as sync reference (enable with --lyrics)
SHOW_TITLE = False
PAGE_TOP = 190          # page-mode: top band reserved for lyrics (blurred backdrop)
GUTTER = 4              # px trimmed next to the fold in page-mode

S = lambda cx=.5, cy=.5, z=1.0: (cx, cy, z)
P = lambda z0=1.0, z1=1.0: ((.5, .5, z0), (.5, .5, z1))     # page-mode camera = zoom only

# --- cuts ---------------------------------------------------------------------------------------------
# key, t0, t1, section, theme, motion, cam_from, cam_to, dissolve_in, page(None|"L"|"R")
# Page rows ("@L"/"@R") show ONE page of a two-page spread on a blurred backdrop: the book's pages are
# independent paintings and the fold shows as a hard seam if the spread is panned across (see asset_review.md).
# Rainbow cues R1..R7 (v3b). Cut-in at a rainbow lyric is short (0.3s) so the rainbow is already on screen when the word is sung;
# elsewhere the calm dissolves are kept. tag=Rn marks the cut that must be on screen at that cue (checked by scripts/rainbow_cues.py).
# sat = colour grade only (no painting): R1 paler/farther, R2 stronger.
RB = "p030_031_farewell"      # the only existing picture with a rainbow (left page = rainbow bridge)
CUTS = [
    ("p001_title",            0.00,   5.50, "INTRO",       "雪と灯り。まだ虹は見せない",              "zoom in", S(.5,.66,1.00), S(.5,.66,1.07), 0.0, None),
    ("p002_003_warmth",       5.50,  12.00, "INTRO",       "遠い記憶のぬくもり",                      "pan →",   S(.30,.5,1.02), S(.42,.5,1.06), 1.6, None),
    ("p004_005_snow",        12.00,  15.30, "VERSE 1",     "ぬくもりが消える。ひとりの雪の路地(左頁)", "still",   *P(1.0,1.02),                    1.2, "L"),
    ("p004_005_snow",        15.30,  18.10, "VERSE 1",     "ゴミ袋の陰の小さなうさぎ(右頁)",           "zoom in", *P(1.0,1.05),                    1.0, "R"),
    # R1 「空にかかった虹が」 18.80: 遠い淡い虹。再会は見せない。仮素材=虹の橋の頁の上部(新規静止画RAINBOW_01が来たら差替)
    (RB,                     18.10,  23.20, "VERSE 1",     "R1 遠い淡い虹(未来をつないだ)",           "zoom out",S(.5,.12,1.34), S(.5,.12,1.26), 0.9, "Lc", dict(tag="R1", sat=0.80)),
    ("p006_007_stop_waiting",23.20,  26.00, "VERSE 1",     "待つのをやめた(記憶へ戻る)",               "zoom in", S(.5,.5,1.00),  S(.46,.5,1.09), 1.0, None),
    ("p008_009_found",       26.00,  31.00, "VERSE 1",     "雪を踏む足音。女の子が来る",                "pan →",   S(.32,.5,1.04), S(.62,.5,1.04), 1.2, None),
    ("p010_011_distance",    31.00,  33.70, "PRE-CHORUS",  "怖かったね。すぐには信じられない",          "pan ←",   S(.62,.5,1.03), S(.48,.5,1.03), 1.0, None),
    # R2 「虹の向こうで会いたい」 34.20: 虹がすでに明確に見えている状態でCUT(0.3秒)。R1より強く。相手は見せない。
    (RB,                     33.70,  36.90, "CHORUS 1",    "R2 明確な虹。会いたいがまだ届かない",       "zoom in", S(.5,.15,1.42), S(.5,.17,1.50), 0.3, "Lc", dict(tag="R2", sat=1.12)),
    (RB,                     36.90,  38.60, "CHORUS 1",    "R2' 虹の道の遠くに存在の気配(ひとりじゃない)", "zoom in", *P(1.0,1.05),                   0.9, "L", dict(tag="R2")),
    ("p012_013_every_day",   38.60,  41.30, "PRE-CHORUS",  "昨日もいた(左頁)",                         "still",   *P(1.0,1.015),                   1.0, "L"),
    ("p012_013_every_day",   41.30,  44.00, "PRE-CHORUS",  "今日もいる。明日もたぶんいる(右頁)",        "still",   *P(1.0,1.015),                   0.9, "R"),
    ("p016_017_safe",        44.00,  48.00, "CHORUS 1",    "心に咲く君の笑顔(温かい絵。動かしすぎない)", "zoom in", S(.5,.5,1.00),  S(.56,.53,1.07), 0.9, None),
    # R3 「虹の向こうで／もう一度」 48.46: R2とは別の構図。虹の奥へ視線が進む(少し近づいた虹)
    (RB,                     48.00,  52.00, "CHORUS 1",    "R3 少し近づいた虹。虹の奥へ視線が進む",      "pan →",   S(.30,.15,1.45), S(.64,.17,1.45), 0.5, "Lc", dict(tag="R3")),
    ("p014_015_first_step",  52.00,  56.00, "CHORUS 1",    "自分の足で近づく(虹を残さず記憶へ戻る)",    "pan →",   S(.34,.5,1.02), S(.60,.5,1.02), 1.0, None),
    ("p018_019_seasons",     56.00,  63.00, "BREATH",      "春夏秋冬。季節が過ぎる(虹はいったん消す)",   "pan →",   S(.26,.5,1.00), S(.74,.5,1.00), 2.0, None),
    ("p020_021_farewell",    63.00,  70.00, "VERSE 2",     "静かな別れ。空いた場所(長く止める)",        "still",   S(.5,.5,1.00),  S(.5,.5,1.02),  1.8, None),
    ("p022_023_new_friend",  70.00,  75.40, "VERSE 2",     "黄金色のうさぎと暮らす",                   "zoom out",S(.55,.5,1.10), S(.5,.5,1.00),  1.2, None),
    # R4 2回目「虹の向こうで会いたい」 76.10: 1回目より近い。虹とその下の道、うさぎの後ろ姿(再会はまだ)。仮素材=同頁の寄り(RAINBOW_03a)
    (RB,                     75.40,  81.40, "CHORUS 2",    "R4 近くの虹。道とうさぎの後ろ姿(まだ会えない)", "pan ↓",  S(.5,.30,1.00), S(.5,.335,1.02), 0.3, "Lc", dict(tag="R4", sat=1.05)),
    ("p024_025_meals_naps",  81.40,  83.40, "VERSE 2",     "一緒にごはん(左頁・虹から記憶へ)",          "zoom in", *P(1.0,1.03),                    1.0, "L"),
    ("p024_025_meals_naps",  83.40,  85.30, "VERSE 2",     "一緒にお昼寝(右頁)",                       "zoom in", *P(1.0,1.03),                    0.8, "R"),
    ("p026_027_seasons",     85.30,  88.10, "VERSE 2",     "四つの季節の記憶(再会直前まで行かない)",    "still",   S(.5,.5,1.00),  S(.5,.5,1.03),  1.0, None),
    # R5 2回目「虹の向こうで／もう一度」 88.76: もう少しで届く。虹の向こう側の光(RAINBOW_03b)
    (RB,                     88.10,  92.25, "CHORUS 2",    "R5 もう少しで届く。虹の向こうの光へ寄る",    "zoom in", S(.5,.17,1.50), S(.5,.185,2.00), 0.5, "Lc", dict(tag="R5")),
    ("p028_029_love",        92.25,  95.10, "CHORUS 2",    "毎日がやさしかった(左頁)",                 "zoom in", *P(1.0,1.04),                    0.8, "L"),
    ("p028_029_love",        95.10,  98.00, "CHORUS 2",    "抱きしめる(右頁)",                         "zoom in", *P(1.0,1.04),                    0.7, "R"),
    ("p030_031_farewell",    98.00, 104.75, "CHORUS 2",    "空いた寝床(右頁・虹は出さない)",            "still",   *P(1.0,1.02),                    1.2, "R"),
    ("p032_033_quiet_room", 104.75, 107.90, "CHORUS 2",    "雨上がりの窓辺(左頁・虹なし)",              "zoom in", *P(1.0,1.04),                    1.0, "L"),
    ("p032_033_quiet_room", 107.90, 111.00, "CHORUS 2",    "同じ窓辺、夕方(右頁)",                     "zoom in", *P(1.0,1.04),                    1.0, "R"),
    ("p034_035_figurine_found",111.00,113.70,"CHORUS 2",   "旅の途中の女の子(左頁)",                   "zoom in", *P(1.0,1.03),                    0.8, "L"),
    ("p034_035_figurine_found",113.70,116.50,"CHORUS 2",   "黄金のうさぎの置物と出会う(右頁)",         "zoom in", *P(1.0,1.03),                    0.8, "R"),
    ("p036_037_figurine_home",116.50,119.00, "CHORUS 2",   "置物を家へ(左頁)",                         "zoom in", *P(1.0,1.03),                    0.8, "L"),
    ("p036_037_figurine_home",119.00,121.50, "CHORUS 2",   "あの子のいた場所の近くへ(右頁)",           "zoom in", *P(1.0,1.03),                    0.8, "R"),
    ("p038_039_not_a_replacement",121.50,124.40,"CHORUS 2","代わりではない(左頁)",                     "still",   *P(1.0,1.02),                    1.0, "L"),
    ("p038_039_not_a_replacement",124.40,127.25,"CHORUS 2","胸の穴が少しやわらぐ(右頁)",               "still",   *P(1.0,1.02),                    1.0, "R"),
    ("p040_041_shadow",     127.25, 129.90, "BRIDGE",      "置物の後ろの大きな影(左頁・違和感)",       "zoom in", *P(1.0,1.05),                    1.0, "L"),
    ("p040_041_shadow",     129.90, 131.50, "BRIDGE",      "振り返る(右頁)",                           "still",   *P(1.0,1.02),                    0.7, "R"),
    ("p042_043_lost",       131.50, 133.20, "BRIDGE",      "知らない街で道に迷う(左頁)",               "still",   *P(1.0,1.02),                    0.7, "L"),
    ("p042_043_lost",       133.20, 135.00, "BRIDGE",      "暗くなっていく路地(右頁)",                 "zoom in", *P(1.0,1.03),                    0.6, "R"),
    ("p044_045_voice",      135.00, 138.50, "BRIDGE",      "「……こっちだよ。」",                        "zoom in", S(.5,.5,1.00),  S(.5,.5,1.08),  0.7, None),
    ("p060_061_light",      138.50, 142.00, "BRIDGE",      "道の先の小さな灯り",                       "pan →",   S(.34,.5,1.03), S(.62,.5,1.03), 0.7, None),
    ("p064_065_door",       142.00, 146.80, "BRIDGE",      "一枚の扉(こちら側)",                       "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  0.6, None),
    # R6 「虹の向こうで会えたなら」 147.54: 虹を見る側 -> 向こう側へ。ここだけ通常と違う遷移(暖かな光のブルーム)。虹は描かない(RAINBOW_04は任意)
    ("p066_067_come_in",    146.80, 150.00, "LAST SECTION","R6 扉の向こう側へ。光のブルームで越える",    "zoom in", S(.5,.5,1.00),  S(.5,.5,1.06),  1.0, None, dict(tag="R6", bloom=True)),
    ("p068_069_first_sight",150.00, 154.00, "LAST SECTION","もう手を離さないよ=到着。声だけだった大きなうさぎ(答えは言わない)", "pan →",   S(.36,.5,1.03), S(.60,.5,1.03), 0.8, None, dict(tag="R6b")),
    ("p070_071_oyabun",     154.00, 160.40, "LAST SECTION","親分へ近づく。まだ答えを言わない",          "pan →",   S(.30,.5,1.02), S(.58,.5,1.02), 0.8, None),
    ("p086_087_home",       160.40, 167.60, "LAST SECTION","同じ空を見上げる。空と光(虹はほぼ消える)",   "zoom in", S(.5,.5,1.00),  S(.56,.5,1.05), 1.2, None),
    # R7 「虹の向こうで／また」 168.40 / 172.20: 虹そのもの -> 虹色の光 -> 暖かな光 -> 宇宙酒場。「また」の後は虹を主役に戻さない
    (RB,                    167.60,  170.60, "OUTRO",       "R7 最後の虹(遠く・淡く)",                  "zoom out",S(.5,.15,1.30), S(.5,.14,1.20), 0.8, "Lc", dict(tag="R7", sat=0.85)),
    (RB,                    170.60,  172.80, "OUTRO",       "R7 虹色の光 → 暖かな光(虹の輪郭は消える)",   "zoom in", S(.5,.18,2.00), S(.5,.15,2.60), 1.2, "Lc", dict(tag="R7")),
    ("p084_085_empty_seat", 172.80,  179.00, "END CARD",    "「またねじゃなくて」 親分と空いた席。静止",  "still",   S(.5,.5,1.00),  S(.5,.5,1.015), 2.0, None),
    ("END_CARD",            179.00, None,   "END CARD",    "「おかえりって」 親分だけ。虹・字幕・台詞なし", "zoom in", S(.5,.58,1.00), S(.5,.58,1.02), 1.6, None),
]
END_CARD_KEY = "p088_welcome"          # replaced automatically if assets/images/oyabun_bar.* exists

# Lyric anchor (top-left / top-centre / top-right), best first. Anything not listed is treated as a face/ear/key-object clash.
# Page-mode rows always use the blurred top band, so only "C" is allowed there.
ANCHOR_OK = {
    "p001_title": "CLR", "p002_003_warmth": "LC", "p006_007_stop_waiting": "CLR", "p008_009_found": "CL",
    "p010_011_distance": "LC", "p014_015_first_step": "LC", "p016_017_safe": "L", "p018_019_seasons": "CLR",
    "p020_021_farewell": "RC", "p022_023_new_friend": "LC", "p026_027_seasons": "C", "p044_045_voice": "RC",
    "p060_061_light": "LC", "p064_065_door": "CL", "p066_067_come_in": "LC", "p068_069_first_sight": "C",
    "p070_071_oyabun": "C", "p080_081_recognition": "CL", "p084_085_empty_seat": "L", "p086_087_home": "RCL",
    "p088_welcome": "L", "END_CARD": "L",
}

# --- helpers -----------------------------------------------------------------------------------------
def audio_duration():
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", AUDIO]).decode().strip()
    return float(out)


def ts(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


END_CARD_ASPECT = 900 / 1350      # the preview picture (portrait 2:3). A higher-resolution original keeps the same crop if it has this aspect.


def end_card_image_key():
    """Order: oyabun_bar_hires.* (a high-resolution original, if provided) > oyabun_bar.* (current) > the book's last spread.
    The crop (cx/cy/zoom as fractions of the picture) is unchanged, so a same-aspect original drops in with the same composition."""
    for pat in ("oyabun_bar_hires.*", "oyabun_bar.*"):
        for p in sorted(glob.glob(os.path.join(IMG, pat))):
            try:
                w, h = Image.open(p).size
                if abs(w / h - END_CARD_ASPECT) > 0.01:
                    print(f"WARNING: {os.path.basename(p)} is {w}x{h} (aspect {w/h:.3f}); the baseline crop assumes 2:3 ({END_CARD_ASPECT:.3f}) - "
                          "the framing will differ. Re-check the end card by eye.", file=sys.stderr)
            except Exception:
                pass
            return os.path.splitext(os.path.basename(p))[0], p
    return END_CARD_KEY, os.path.join(IMG, f"art_{END_CARD_KEY}_png.jpg")


# --- variants (the baseline CUTS above stay untouched; a variant is a small, named patch of that list) ---------
VARIANT = os.environ.get("MV_VARIANT", "")


def _v3c_r3b(rows):
    """R3b (human-requested, one spot only): at 0:52.32 "虹の向こうで" the baseline shows p014 (no rainbow).
    Keep R3 as it is, then a short different-framing rainbow (push-in toward the glow = "虹へ向かう"), then p014 (= "一歩踏み出す").
    R6 / R7 / END are not touched."""
    out = []
    for r in rows:
        key, t0, t1, sec, theme, motion, cf, ct, fade, page, *extra = r
        tag = extra[0].get("tag") if extra else None
        if tag == "R3":
            out.append((key, t0, 51.90, sec, theme, motion, cf, ct, fade, page, *extra))
            out.append((RB, 51.90, 53.70, "CHORUS 1", "R3b 虹へ向かう(別の構図: 虹の光へ寄る)", "zoom in",
                        S(.5, .14, 1.30), S(.5, .17, 1.75), 0.3, "Lc", dict(tag="R3b")))
        elif key == "p014_015_first_step":
            out.append((key, 53.70, t1, sec, "自分の足で一歩踏み出す(虹から p014 へ)", "pan →", S(.40, .5, 1.02), S(.60, .5, 1.02), 0.8, page))
        else:
            out.append(r)
    return out


def _v3d_r3_continuous(rows):
    """Adopted direction of v3c_r3b, without the re-cut: R3 and R3b are ONE continuous rainbow shot 0:48.00-0:53.70
    (a single slow camera move toward the light beyond the rainbow, still moving while "虹の向こうで" (0:52.32) is sung),
    then a soft 0.8s dissolve into p014 (memory -> "自分の足で進む"). R6 / R7 / END are not touched."""
    out = []
    for r in rows:
        key, t0, t1, sec, theme, motion, cf, ct, fade, page, *extra = r
        tag = extra[0].get("tag") if extra else None
        if tag == "R3":
            out.append((key, 48.00, 53.70, sec, "R3 + R3b 一本の連続した虹ショット: 虹の奥/光の方向へゆっくり進む(52.32「虹の向こうで」の間も止めない)",
                        "zoom in", S(.42, .15, 1.40), S(.50, .18, 1.95), 0.5, "Lc", dict(tag="R3")))
        elif key == "p014_015_first_step":
            out.append((key, 53.70, t1, sec, "記憶の中の少女とうさぎ → 自分の足で進む(虹から柔らかく)", "pan →", S(.40, .5, 1.02), S(.60, .5, 1.02), 0.8, page))
        else:
            out.append(r)
    return out


VARIANTS = {"v3c_r3b": _v3c_r3b, "v3d_r3_continuous": _v3d_r3_continuous}


def variant_dir():
    name = (VARIANT + (("_vertical_fill" if VFILL else "_vertical") if VERTICAL else "")) if VARIANT else ("vertical" if VERTICAL else "")
    return os.path.join(ROOT, "work/storyboard/variants", name) if name else os.path.join(ROOT, "work/storyboard")


# --- vertical (9:16) re-composition ---------------------------------------------------------------------
# Same cut list, same timing, same transitions (so the sync / frozen points are untouched); only the framing changes.
# t0 -> (mode, region, cam_from, cam_to).  cover: a 9:16 window over the image (or one page), subject-aware centre + slow pan;
# fit: a region shown whole, fitted to the width, on a blurred extension of itself (used where a crop would lose the story).
# cam = (cx, cy, zoom); zoom 1.0 = the largest 9:16 window; for fit, zoom scales the fitted band around (cx, cy) of the region.
_V = lambda cx, cy=.5, z=1.0: (cx, cy, z)
RB_TOP = (0.0, 0.04, 1.0, 0.34)       # the sky/rainbow strip of the rainbow page: no animal in it
VERT_PLAN = {
    0.00: ("cover", None, _V(.56, .66, 1.0), _V(.56, .66, 1.07)),
    5.50: ("cover", None, _V(.60), _V(.56, .5, 1.06)),
    12.00: ("cover", None, _V(.5), _V(.5, .5, 1.02)),
    15.30: ("cover", None, _V(.62), _V(.70, .72, 1.35)),
    18.10: ("fit", RB_TOP, _V(.5, .5, 1.65), _V(.5, .5, 1.5)),                 # R1 far, pale
    23.20: ("cover", None, _V(.76), _V(.72, .5, 1.08)),                           # the curled rabbit: waiting is over (no sweeping pan over empty snow)
    26.00: ("cover", None, _V(.36), _V(.84)),
    31.00: ("cover", None, _V(.78), _V(.56)),
    33.70: ("fit", (0.0, 0.06, 1.0, 0.32), _V(.5, .5, 1.8), _V(.5, .5, 1.9)),  # R2 clear rainbow
    36.90: ("cover", None, _V(.5), _V(.5, .5, 1.06)),                              # R2' whole page: the path and a presence beyond
    38.60: ("fit", None, _V(.5), _V(.5, .5, 1.02)),                                # both the rabbit and the girl, uncropped
    41.30: ("fit", None, _V(.5), _V(.5, .5, 1.02)),                                # stacked day/night page, shown whole
    44.00: ("cover", None, _V(.60), _V(.64, .55, 1.06)),
    48.00: ("fit", RB_TOP, _V(.45, .5, 1.7), _V(.5, .55, 2.2)),                   # R3 one continuous shot toward the glow
    53.70: ("cover", None, _V(.58), _V(.78)),
    56.00: ("cover", None, _V(.28), _V(.80)),
    63.00: ("cover", None, _V(.27), _V(.72)),
    70.00: ("cover", None, _V(.72, .5, 1.1), _V(.66)),
    75.40: ("cover", None, _V(.5, .40, 1.18), _V(.5, .46, 1.28)),         # R4 nearer: arc + the rabbit seen from behind
    81.40: ("cover", None, _V(.5), _V(.5, .5, 1.03)),
    83.40: ("cover", None, _V(.5), _V(.5, .5, 1.03)),
    85.30: ("fit", None, _V(.5), _V(.5, .5, 1.04)),                                # four-seasons collage, whole
    88.10: ("fit", (0.2, 0.12, 0.8, 0.34), _V(.5, .5, 1.3), _V(.5, .5, 1.9)),       # R5 toward the light
    92.25: ("cover", None, _V(.40), _V(.42, .5, 1.05)),
    95.10: ("cover", None, _V(.46), _V(.48, .5, 1.05)),
    98.00: ("cover", None, _V(.5), _V(.5, .5, 1.02)),
    104.75: ("cover", None, _V(.5), _V(.45, .5, 1.06)),
    107.90: ("cover", None, _V(.5), _V(.55, .5, 1.06)),
    111.00: ("cover", None, _V(.36), _V(.44, .5, 1.04)),
    113.70: ("cover", None, _V(.62), _V(.64, .5, 1.04)),
    116.50: ("cover", None, _V(.34), _V(.38, .5, 1.04)),
    119.00: ("cover", None, _V(.68), _V(.70, .5, 1.04)),
    121.50: ("cover", None, _V(.44), _V(.56)),
    124.40: ("cover", None, _V(.58), _V(.60, .5, 1.02)),
    127.25: ("cover", None, _V(.55), _V(.55, .5, 1.1)),
    129.90: ("cover", None, _V(.66), _V(.66, .5, 1.02)),
    131.50: ("cover", None, _V(.38), _V(.40, .5, 1.02)),
    133.20: ("cover", None, _V(.5), _V(.5, .5, 1.06)),
    135.00: ("cover", None, _V(.22), _V(.28, .5, 1.06)),
    138.50: ("cover", None, _V(.30), _V(.64)),
    142.00: ("cover", None, _V(.60), _V(.60)),
    146.80: ("cover", None, _V(.50), _V(.66)),                           # R6 the door opens onto warm light
    150.00: ("cover", None, _V(.28), _V(.72)),
    154.00: ("cover", None, _V(.25), _V(.66)),
    160.40: ("cover", None, _V(.22), _V(.40, .5, 1.05)),
    167.60: ("fit", RB_TOP, _V(.5, .5, 1.6), _V(.5, .5, 1.5)),                     # R7 the last, faint rainbow
    170.60: ("fit", (0.2, 0.12, 0.8, 0.34), _V(.5, .5, 1.5), _V(.5, .5, 2.0)),     # R7 rainbow colours -> warm light
    172.80: ("cover", None, _V(.62), _V(.62, .5, 1.015)),
    179.00: ("cover", None, _V(.5), _V(.5, .5, 1.03)),                              # END: the boss's face, hand and bottle fit the 9:16 window
}


def resolve_cuts(dur):
    cuts = []
    custom_end = end_card_image_key()[0].startswith("oyabun_bar")
    rows = VARIANTS[VARIANT](list(CUTS)) if VARIANT else CUTS
    for key, t0, t1, sec, theme, motion, cf, ct, fade, page, *extra in rows:
        if key == "END_CARD" and custom_end:     # portrait 宇宙酒場 picture: frame the boss's face, hand and the bottle (16:9 window)
            cf, ct = S(.5, .35, 1.00), S(.5, .35, 1.03)
        vmode = region = None
        if VERTICAL:
            vp = VERT_FILL.get(round(t0, 2)) if VFILL and round(t0, 2) in VERT_FILL else VERT_PLAN[round(t0, 2)]
            vmode, region, cf, ct = vp
            if page in ("L", "R"):
                page = page + "c"                       # pages are cropped (not letterboxed) in 9:16
            if vmode == "fit" and page == "Lc" and region is None:
                pass
        cuts.append(dict(vmode=vmode, region=region, key=key, t0=t0, t1=dur if t1 is None else t1, sec=sec, theme=theme, motion=motion,
                         cf=cf, ct=ct, fade=fade, page=page, tag=(extra[0].get('tag') if extra else None),
                         sat=(extra[0].get('sat') if extra else None), bloom=bool(extra and extra[0].get('bloom'))))
    return cuts


# "Fill" alternative for the rainbow cuts (same t0/t1/timing; framing only): the 9:16 screen is filled with rainbow and light.
# Left/right information is given up on purpose. Distance story: far (side of the arc) -> the arc -> toward the glow -> into the light.
# Page p030 left is 3:4, so z=2 shows its top half, z=3 its top third. Used only with MV_VFILL=1 (--vfill).
VERT_FILL = {
    18.10: ("cover", None, _V(.25, .20, 2.3), _V(.31, .21, 2.1)),     # R1 far: the left end of the arc in cloud, small and pale
    33.70: ("cover", None, _V(.44, .15, 2.8), _V(.45, .16, 2.6)),     # R2 the arc, centred and clear
    48.00: ("cover", None, _V(.43, .22, 2.3), _V(.46, .25, 3.4)),     # R3 one continuous move toward the glow
    88.10: ("cover", None, _V(.46, .25, 3.0), _V(.47, .27, 4.2)),     # R5 inside the light, nearly there
    167.60: ("cover", None, _V(.84, .17, 2.4), _V(.82, .18, 2.3)),    # R7 the last far rainbow, from the other side
    170.60: ("cover", None, _V(.46, .24, 3.0), _V(.47, .26, 4.0)),    # R7 rainbow colours -> warm light
}


def img_path(key):
    if key == "END_CARD":
        return end_card_image_key()[1]
    return os.path.join(IMG, f"art_{key}_png.jpg")


# --- stills ----------------------------------------------------------------------------------------
def load_qr_plate():
    """Clean, un-rotated, opaque QR on a white plate with a 4-module quiet zone.
    The picture is cropped to the dark modules, the module grid is re-sampled at module centres and re-drawn crisp
    (same modules, no recolouring). Verified by decoding; falls back to a plain resize if the grid guess is wrong."""
    import numpy as np
    files = sorted(glob.glob(QR_GLOB))
    if not files:
        return None, None
    src = Image.open(files[0]).convert("RGB")
    g = np.asarray(src.convert("L"))
    ys, xs = np.where(g < 100)
    crop = src.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    cg = np.asarray(crop.convert("L")) < 128
    row = cg[min(3, cg.shape[0] - 1)]
    run = 0
    for v in row:
        if not v:
            break
        run += 1
    mod = run / 7.0                                  # the finder pattern is 7 modules wide
    n = int(round(crop.width / mod))
    px = 16 if VERTICAL else 12
    plate = None
    try:
        cell_w, cell_h = crop.width / n, crop.height / n
        mat = np.zeros((n, n), dtype=bool)
        for j in range(n):
            for i in range(n):
                mat[j, i] = cg[int((j + .5) * cell_h), int((i + .5) * cell_w)]
        quiet = 4
        side = (n + 2 * quiet) * px
        canvas = np.full((side, side), 255, dtype=np.uint8)
        for j in range(n):
            for i in range(n):
                if mat[j, i]:
                    canvas[(j + quiet) * px:(j + quiet + 1) * px, (i + quiet) * px:(i + quiet + 1) * px] = 0
        plate = Image.fromarray(canvas).convert("RGB")
    except Exception:
        plate = None
    try:
        import cv2
        det = cv2.QRCodeDetector()
        want = det.detectAndDecode(cv2.cvtColor(np.asarray(src), cv2.COLOR_RGB2BGR))[0]
        got = det.detectAndDecode(cv2.cvtColor(np.asarray(plate), cv2.COLOR_RGB2BGR))[0] if plate is not None else ""
        if want and got != want:
            plate = None                              # re-draw disagrees with the source -> use the plain crop instead
    except ImportError:
        pass
    if plate is None:
        side = 540
        plate = Image.new("RGB", (side, side), (255, 255, 255))
        sq = crop.resize((side - 120, side - 120), Image.LANCZOS)
        plate.paste(sq, (60, 60))
    return plate, files[0]


class Still:
    """One source image.
    page=None : full-bleed window (aspect W:H) over the whole image.
    page="L"/"R": a single book page shown whole on a blurred backdrop (page_frame; landscape only).
    page="Lc"/"Rc": full-bleed window limited to one page (cam = cx, cy, zoom relative to that page).
    vmode="fit" (vertical): a region of the image/page shown whole, fitted to the width, on a blurred extension of itself."""
    def __init__(self, key, page=None, vmode=None, region=None):
        self.im = Image.open(img_path(key)).convert("RGB")
        w, h = self.im.size
        A = W / H
        if w / h >= A:
            self.bh, self.bw = h, h * A
        else:
            self.bw, self.bh = w, w / A
        self.page = page
        self.vmode = vmode
        if page:
            half = w // 2
            side = page[0]
            box = (0, 0, half - GUTTER, h) if side == "L" else (half + GUTTER, 0, w, h)
            self.pg = self.im.crop(box)
            if len(page) == 1 and not VERTICAL:
                bg = self.pg.resize((W, int(self.pg.height * W / self.pg.width)), Image.BICUBIC)
                y0 = (bg.height - H) // 2
                bg = bg.crop((0, y0, W, y0 + H)).filter(ImageFilter.GaussianBlur(48))
                self.bg = Image.eval(bg, lambda v: int(v * 0.55))
        if vmode == "fit":
            base = self.pg if page else self.im
            bw_, bh_ = base.size
            r = region or (0, 0, 1, 1)
            self.fit_src = base.crop((int(r[0] * bw_), int(r[1] * bh_), int(r[2] * bw_), int(r[3] * bh_)))
            fs = self.fit_src
            sc = max(W / fs.width, H / fs.height)
            bg = fs.resize((int(fs.width * sc) + 1, int(fs.height * sc) + 1), Image.BICUBIC)
            x0, y0 = (bg.width - W) // 2, (bg.height - H) // 2
            bg = bg.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(70))
            self.bg = Image.eval(bg, lambda v: int(v * 0.92))
            self._masks = {}

    def frame(self, cam):
        cx, cy, z = cam
        w, h = self.im.size
        bw, bh = self.bw / z, self.bh / z
        x0 = min(max(cx * w - bw / 2, 0), w - bw)
        y0 = min(max(cy * h - bh / 2, 0), h - bh)
        return self.im.transform((W, H), Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BICUBIC)

    def crop_frame(self, cam):
        cx, cy, z = cam
        pw, ph = self.pg.size
        A = W / H
        if pw / ph >= A:
            bh = ph / z
            bw = bh * A
        else:
            bw = pw / z
            bh = bw / A
        x0 = min(max(cx * pw - bw / 2, 0), pw - bw)
        y0 = min(max(cy * ph - bh / 2, 0), ph - bh)
        return self.pg.transform((W, H), Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BICUBIC)

    def fit_frame(self, cam):
        cx, cy, z = cam
        fs = self.fit_src
        fw = W * z
        fh = fw * fs.height / fs.width
        fg = fs.resize((int(round(fw)), int(round(fh))), Image.BICUBIC)
        out = self.bg.copy()
        x = int(round(W / 2 - cx * fw))
        y = int(round(H / 2 - cy * fh))
        key = fg.size
        if key not in self._masks:                  # soft top/bottom edge so the sharp band melts into its blurred extension
            from PIL import ImageChops
            m = Image.new("L", fg.size, 255)
            ramp = min(60, fg.height // 4)
            d = ImageDraw.Draw(m)
            for i in range(ramp):
                v = int(255 * i / ramp)
                d.line([(0, i), (fg.width, i)], fill=v)
                d.line([(0, fg.height - 1 - i), (fg.width, fg.height - 1 - i)], fill=v)
            self._masks[key] = m
        out.paste(fg, (x, y), self._masks[key])
        return out

    def page_frame(self, cam):
        z = cam[2]
        fh = int(round((H - PAGE_TOP) * z))
        fw = int(round(fh * self.pg.width / self.pg.height))
        fg = self.pg.resize((fw, fh), Image.BICUBIC)
        out = self.bg.copy()
        out.paste(fg, ((W - fw) // 2, H - fh))
        return out


def lerp_cam(a, b, u):
    e = ease(u)
    return tuple(a[i] + (b[i] - a[i]) * e for i in range(3))


# --- lyric captions ----------------------------------------------------------------------------------
def load_lyrics():
    rows = []
    for ln in open(LYRICS_TSV, encoding="utf8"):
        if ln.startswith("#") or not ln.strip():
            continue
        s, e, cap, conf, text = ln.rstrip("\n").split("\t", 4)
        rows.append(dict(start=float(s), end=float(e), cap=cap, conf=conf, text=text))
    return rows


def build_captions(dur):
    """Group TSV rows into captions (1-2 lines) with display timing, size and anchor."""
    rows = load_lyrics()
    caps = []
    for r in rows:
        if not caps or caps[-1]["id"] != r["cap"]:
            caps.append(dict(id=r["cap"], lines=[]))
        caps[-1]["lines"].append(r)
    for i, c in enumerate(caps):
        last_end = c["lines"][-1]["end"]
        nxt = caps[i + 1]["lines"][0]["start"] if i + 1 < len(caps) else None
        c["t_in"] = c["lines"][0]["start"] - 0.08
        end = last_end + 0.60
        if nxt is not None:
            end = min(end, nxt - 0.08 - 0.34)     # fade-out (0.30s) must finish before the next caption starts
        if c["id"] == "outro2":
            end = dur - 0.65      # let the last word linger into the closing fade
        c["t_out"] = max(end, last_end + 0.15)
        for ln in c["lines"]:
            ln["show"] = ln["start"] - 0.08
        # a line that follows another inside the caption must not appear before its sung start - 0.12
    return caps


def anchor_penalty(cut, anchor):
    if cut["page"]:
        return 0 if anchor == "C" else 4
    ok = ANCHOR_OK.get(cut["key"], "C")
    return ok.index(anchor) if anchor in ok else 4


def choose_anchor(cap, cuts, forced=None):
    if forced:
        return forced
    best = None
    for a in "CLR":
        cost = 0.0
        for cut in cuts:
            ov = min(cap["t_out"], cut["t1"]) - max(cap["t_in"], cut["t0"])
            if ov > 0:
                cost += ov * anchor_penalty(cut, a)
        if best is None or cost < best[0] - 1e-9:
            best = (cost, a)
    return best[1]


_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(FONT, size)
    return _fonts[size]


ANCHOR_X = {"L": 0.30, "C": 0.50, "R": 0.70}


def layout_caption(cap, anchor, big_last=False):
    """Pre-render each line (RGBA, cropped) and compute its position. Returns list of dicts."""
    margin = 110
    max_w = {"C": 1560, "L": 1160, "R": 1160}[anchor]
    specs = []
    for k, ln in enumerate(cap["lines"]):
        size = 60
        if cap["id"] == "outro2" and k == len(cap["lines"]) - 1:
            size = 92
        while size > 48:
            if font(size).getlength(ln["text"]) <= max_w:
                break
            size -= 2
        specs.append((ln, size))
    gap = 10
    heights = [font(s).getbbox("あ")[3] for _, s in specs]
    top = 56 if cap["id"] != "title" else 78
    y = top
    cx = ANCHOR_X[anchor] * W
    out = []
    extra = 0
    for (ln, size), hh in zip(specs, heights):
        f = font(size)
        tw = f.getlength(ln["text"])
        x = min(max(cx - tw / 2, margin), W - margin - tw)
        if cap["id"] == "outro2" and size >= 90:
            y += 26   # a held breath before the last word
        pad = 28
        layer = Image.new("RGBA", (int(tw) + pad * 2 + 12, hh + pad * 2 + 16), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad, pad), ln["text"], font=f, fill=(0, 0, 0, 200), stroke_width=4, stroke_fill=(0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        layer = Image.alpha_composite(layer, sh)
        d = ImageDraw.Draw(layer)
        d.text((pad, pad), ln["text"], font=f, fill=(255, 247, 233, 255), stroke_width=3, stroke_fill=(52, 30, 22, 235))
        out.append(dict(line=ln, layer=layer, pos=(int(x) - pad, int(y) - pad), bbox=(int(x), int(y), int(x + tw), int(y + hh)),
                        slow=(cap["id"] == "outro2" and size >= 90)))
        y += hh + gap
    return out


def luminance(img_rgb):
    g = img_rgb.convert("L").resize((max(1, img_rgb.width // 8), max(1, img_rgb.height // 8)))
    px = list(g.tobytes())
    px.sort()
    return px[int(len(px) * 0.8)] / 255.0     # 80th percentile: the bright part is what hurts white text


# --- renderer --------------------------------------------------------------------------------------
class Renderer:
    def __init__(self, dur, fps=30):
        self.dur, self.fps = dur, fps
        self.cuts = resolve_cuts(dur)
        self.end_card_start = next(c["t0"] for c in self.cuts if c["sec"] == "END CARD")
        self.stills = {}
        self.qr = sorted(glob.glob(QR_GLOB))
        self.qr_img, _ = load_qr_plate()
        self.qr_bg = None
        if self.qr_img is not None and QR_MODE == "after":
            self.tail = QR_TAIL
            ekey, epath = end_card_image_key()
            eim = Image.open(epath).convert("RGB")
            bg = eim.resize((W, int(eim.height * W / eim.width)), Image.BICUBIC)
            y0 = (bg.height - H) // 2
            bg = bg.crop((0, y0, W, y0 + H)).filter(ImageFilter.GaussianBlur(38))
            self.qr_bg = Image.eval(bg, lambda v: int(v * 0.30))
        else:
            self.tail = 0.0
        self.captions = build_captions(dur) if SHOW_LYRICS else []
        self.title = dict(id="title", lines=[dict(text="虹の向こうで会いたい — 続編", start=2.0, end=6.0, show=2.0, conf="n/a")], t_in=2.0, t_out=6.4)
        self.layouts = []
        for cap in self.captions + ([self.title] if SHOW_TITLE else []):
            anchor = "C" if cap["id"] == "title" else choose_anchor(cap, self.cuts, forced={"outro1": "L", "outro2": "L"}.get(cap["id"]))
            cap["anchor"] = anchor
            self.layouts.append((cap, layout_caption(cap, anchor)))

    def still(self, cut):
        k = (cut["key"], cut["page"], cut.get("vmode"), tuple(cut["region"]) if cut.get("region") else None)
        if k not in self.stills:
            self.stills[k] = Still(cut["key"], cut["page"], cut.get("vmode"), cut.get("region"))
        return self.stills[k]

    def cut_frame(self, cut, t):
        u = (t - cut["t0"]) / max(cut["t1"] - cut["t0"], 1e-6)
        cam = lerp_cam(cut["cf"], cut["ct"], min(max(u, 0), 1))
        st = self.still(cut)
        if cut.get("vmode") == "fit":
            fr = st.fit_frame(cam)
        elif cut["page"] and len(cut["page"]) == 2:
            fr = st.crop_frame(cam)
        else:
            fr = st.page_frame(cam) if cut["page"] else st.frame(cam)
        if cut.get("sat"):
            fr = ImageEnhance.Color(fr).enhance(cut["sat"])
        return fr

    def base_frame(self, t):
        cuts = self.cuts
        idx = max(i for i, c in enumerate(cuts) if c["t0"] - c["fade"] / 2 <= t or i == 0)
        c = cuts[idx]
        fr = self.cut_frame(c, t)
        if idx > 0 and c["fade"] > 0:
            u = (t - (c["t0"] - c["fade"] / 2)) / c["fade"]
            if u < 1:
                fr = Image.blend(self.cut_frame(cuts[idx - 1], t), fr, smoothstep(u))
                if c.get("bloom"):      # R6: cross the boundary through a wash of warm light instead of a plain dissolve
                    import math
                    fr = Image.blend(fr, Image.new("RGB", (W, H), (255, 232, 190)), 0.62 * math.sin(math.pi * max(0.0, min(1.0, u))) ** 2)
        return fr

    def text_items(self, t):
        """[(layer, pos, alpha, bbox)] for everything visible at t."""
        items = []
        for cap, lay in self.layouts:
            if not (cap["t_in"] - 0.01 <= t <= cap["t_out"] + 1.0):
                continue
            fo = 0.9 if cap["id"] == "outro2" else 0.30
            k_out = smoothstep((cap["t_out"] + fo - t) / fo) if t > cap["t_out"] else 1.0
            for L in lay:
                dur_in = 1.1 if L["slow"] else 0.35
                k_in = smoothstep((t - L["line"]["show"]) / dur_in)
                a = k_in * k_out
                if a > 0.003:
                    items.append((L["layer"], L["pos"], a, L["bbox"]))
        return items

    def qr_card(self, t):
        """After the song: black -> dimmed tavern backdrop + QR (un-rotated, opaque) -> black."""
        tr = t - self.dur
        card = self.qr_bg.copy()
        card.paste(self.qr_img, ((W - self.qr_img.width) // 2, (H - self.qr_img.height) // 2))
        k = smoothstep((tr - 0.4) / 1.2) * smoothstep((self.tail - tr) / 1.0)
        return Image.blend(Image.new("RGB", (W, H)), card, k)

    def frame_at(self, t, with_text=True, return_info=False):
        if self.tail and t >= self.dur:
            fr = self.qr_card(t)
            return (fr, []) if return_info else fr
        fr = self.base_frame(t)
        k = smoothstep(t / FADE_IN) * smoothstep((self.dur - t) / FADE_OUT)
        info = []
        if with_text:
            items = self.text_items(t)
            if items:
                x0 = min(i[3][0] for i in items) - 40
                y0 = min(i[3][1] for i in items) - 30
                x1 = max(i[3][2] for i in items) + 40
                y1 = max(i[3][3] for i in items) + 30
                box = (max(x0, 0), max(y0, 0), min(x1, W), min(y1, H))
                lum = luminance(fr.crop(box))
                amax = max(i[2] for i in items)
                strength = max(0.0, min(1.0, (lum - 0.30) / 0.45)) * 0.42 * amax    # adaptive, only on bright backdrops
                if strength > 0.01:
                    ex = (max(box[0] - 60, 0), max(box[1] - 60, 0), min(box[2] + 60, W), min(box[3] + 60, H))
                    patch = fr.crop(ex)
                    dark = Image.new("RGB", patch.size, (12, 6, 4))
                    mask = Image.new("L", patch.size, 0)
                    ImageDraw.Draw(mask).rectangle((box[0] - ex[0], box[1] - ex[1], box[2] - ex[0], box[3] - ex[1]), fill=int(255 * strength))
                    mask = mask.filter(ImageFilter.GaussianBlur(28))
                    fr = fr.copy()
                    fr.paste(Image.composite(dark, patch, mask), ex[:2])
                fr = fr.convert("RGBA")
                for layer, pos, a, bb in items:
                    lay = layer if a >= 0.995 else layer.copy()
                    if a < 0.995:
                        lay.putalpha(lay.getchannel("A").point(lambda v, a=a: int(v * a)))
                    fr.alpha_composite(lay, (max(pos[0], 0), max(pos[1], 0))) if pos[0] >= 0 and pos[1] >= 0 else fr.alpha_composite(lay, (0, 0), (-pos[0] if pos[0] < 0 else 0, -pos[1] if pos[1] < 0 else 0))
                fr = fr.convert("RGB")
                info = items
        if self.qr_img is not None and QR_MODE == "overlay" and t >= self.end_card_start + 1.5:
            fr = fr.copy()
            fr.paste(self.qr_img, (W - self.qr_img.width - 110, H - self.qr_img.height - 100))
        if k < 1:
            fr = Image.blend(Image.new("RGB", (W, H)), fr, k)
        return (fr, info) if return_info else fr


def rainbow_table(cuts):
    """Which cut is on screen while each rainbow lyric is sung (sync reference; positions are estimates)."""
    must = ("虹の向こうで会いたい", "空にかかった虹が", "虹の向こうで会えたなら")
    rows = []
    try:
        for r in load_lyrics():
            if "虹" not in r["text"]:
                continue
            c = next((c for c in cuts if c["t0"] <= r["start"] + 0.3 < c["t1"]), cuts[-1])
            c_end = next((c for c in cuts if c["t0"] <= r["end"] - 0.1 < c["t1"]), cuts[-1])
            need = r["text"] in must
            tag = c.get("tag") or ""
            ok = ("OK" if tag else "要確認") if need else "-"
            vis = c["key"] + (f"[{c['page']}]" if c["page"] else "")
            if c_end is not c:
                vis += " → " + c_end["key"] + (f"[{c_end['page']}]" if c_end["page"] else "")
            rows.append(f"| {ts(r['start'])}-{ts(r['end'])} | {r['text']} | {vis} | {tag or '-'} | {ok} |")
    except FileNotFoundError:
        pass
    return ["", "## 虹の歌唱位置と映像(歌唱位置は推定)", "",
            "| sung | lyric | cut on screen | rainbow beat | 虹の存在 |", "|---|---|---|---|---|"] + rows


def write_timeline(cuts, caps, qr_path, dur, endkey):
    p = os.path.join(variant_dir(), "timeline.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    L = ["# timeline (auto-generated by scripts/build_mv.py)", "",
         f"audio: assets/audio/song.m4a ({ts(dur)}) / 約86BPM (小節=2.79s, 1拍目=0.49s) / 歌詞は映像に表示しない(v3)。同期資料: lyrics_timing.tsv (推定)", "",
         "| start | end | section | lyric/theme | visual | motion | transition | source |",
         "|---|---|---|---|---|---|---|---|"]
    for c in cuts:
        tr = "fade in" if c["fade"] == 0 else f"dissolve {c['fade']:.1f}s"
        key = endkey if c["key"] == "END_CARD" else c["key"]
        vis = key + ((f" [{c['page'][0]}頁クロップ]" if len(c["page"]) == 2 else f" [{c['page']}頁]") if c["page"] else "") + (f" **{c['tag']}**" if c.get("tag") else "")
        src = os.path.relpath(img_path(c["key"]), ROOT)
        L.append(f"| {ts(c['t0'])} | {ts(c['t1'])} | {c['sec']} | {c['theme']} | {vis} | {c['motion']} | {tr} | {src} |")
    L += rainbow_table(cuts)
    if caps:
      L += ["", "## lyric captions (歌唱=推定位置 / 表示=実際の表示区間)", "",
          "| display in | display out | sung start-end | anchor | text | confidence |", "|---|---|---|---|---|---|"]
    for cap in caps:
        for ln in cap["lines"]:
            L.append(f"| {ts(ln['show'])} | {ts(cap['t_out'])} | {ts(ln['start'])}-{ts(ln['end'])} | {cap.get('anchor','?')} | {ln['text']} | {ln['conf']} |")
    if qr_path and QR_MODE == "after":
        L += ["", "## QR card (曲が終わったあと)", "",
              "| start | end | visual | note |", "|---|---|---|---|",
              f"| {ts(dur)} | {ts(dur + QR_TAIL)} | 暗い宇宙酒場の背景 + QR(回転・変形なし・不透明の白い台紙) | 1.2秒で暗転から現れ、約10秒保持、1秒で暗転へ。音声は無音で延長。文言は未決定のため文字なし |"]
    L += ["", f"QR: {'`'+os.path.relpath(qr_path, ROOT)+'`' if qr_path else '**未配置 (assets/qr/*.png を置くと終盤に自動表示)**'}",
          f"end card image: `{os.path.relpath(img_path('END_CARD'), ROOT)}`"]
    open(p, "w", encoding="utf8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "output/preview/mv_preview.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=23)
    ap.add_argument("--variant", default=None, help="named patch of the baseline cut list (see VARIANTS); output goes to output/preview/mv_<variant>.mp4")
    ap.add_argument("--format", default=None, choices=["landscape", "vertical"], help="vertical = 1080x1920 (9:16) re-composition of the same cut list")
    ap.add_argument("--vfill", action="store_true", help="vertical: rainbow cuts as bold full-bleed crops (VERT_FILL)")
    ap.add_argument("--timeline-only", action="store_true")
    ap.add_argument("--lyrics", action="store_true", help="draw the lyric telop (off by default since v3)")
    ap.add_argument("--title", action="store_true", help="draw the intro title (off by default since v3)")
    ap.add_argument("--limit", type=float, default=None)
    ap.add_argument("--frames", default=None, help="comma-separated seconds: write PNG stills instead of a video")
    ap.add_argument("--frames-dir", default=os.path.join(ROOT, "work/temp/qa"))
    a = ap.parse_args()

    if a.format == "vertical" and os.environ.get("MV_FORMAT") != "vertical":   # W/H are module constants: re-run with the format set
        os.environ["MV_FORMAT"] = "vertical"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    if a.vfill and os.environ.get("MV_VFILL") != "1":
        os.environ["MV_VFILL"] = "1"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    global SHOW_LYRICS, SHOW_TITLE, VARIANT
    SHOW_LYRICS, SHOW_TITLE = a.lyrics, a.title
    if a.variant:
        if a.variant not in VARIANTS:
            sys.exit(f"unknown variant {a.variant}; known: {', '.join(VARIANTS)}")
        VARIANT = a.variant
        if a.out == ap.get_default("out"):
            a.out = os.path.join(ROOT, f"output/preview/mv_{a.variant}{('_vertical_fill' if VFILL else '_vertical') if VERTICAL else ''}.mp4")
    dur = audio_duration()
    r = Renderer(dur, a.fps)
    qr_path = r.qr[0] if r.qr else None
    write_timeline(r.cuts, r.captions, qr_path, dur, end_card_image_key()[0])
    if a.timeline_only:
        return
    if QR_MODE == "overlay":
        assert dur - r.end_card_start >= QR_MIN_SECONDS, "end card shorter than QR minimum"
    else:
        assert not r.tail or r.tail - 1.6 >= QR_MIN_SECONDS, "QR card shorter than the 10 s minimum"
    if a.frames:
        os.makedirs(a.frames_dir, exist_ok=True)
        for t in [float(x) for x in a.frames.split(",")]:
            r.frame_at(t).save(os.path.join(a.frames_dir, f"t{t:07.2f}.png"))
        return

    if os.path.exists(a.out) and os.path.abspath(a.out).startswith(os.path.join(ROOT, "output/final") + os.sep):
        sys.exit(f"refusing to overwrite {a.out}: output/final holds frozen baselines. Write to output/preview/ (or another name).")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    full = dur + r.tail
    total = int(round((a.limit or full) * a.fps))
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-",
         "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
         "-pix_fmt", "yuv420p", "-r", str(a.fps), "-af", "apad", "-c:a", "aac", "-b:a", "192k",
         "-t", f"{a.limit or full:.3f}", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for n in range(total):
        ff.stdin.write(r.frame_at(n / a.fps).tobytes())
        if n % 300 == 0:
            print(f"\r{ts(n / a.fps)} / {ts(dur)}", end="", file=sys.stderr, flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"\nwrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
