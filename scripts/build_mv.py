#!/usr/bin/env python3
"""MV builder: stills + camera moves + dissolves + sparse text -> H.264/AAC MP4.

Usage:
  python3 scripts/build_mv.py [--out output/preview/mv_preview.mp4] [--fps 30] [--crf 20]
                              [--timeline-only] [--limit SECONDS]

Frames are rendered with PIL (sub-pixel crop, no zoompan jitter) and piped to ffmpeg.
The audio is stream-copied-free: encoded once to AAC, never otherwise processed.
Edit CUTS / TEXTS below; work/storyboard/timeline.md is regenerated on every run.
"""
import argparse, glob, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1920, 1080
AUDIO = os.path.join(ROOT, "assets/audio/song.m4a")
IMG = os.path.join(ROOT, "assets/images")
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
QR_GLOB = os.path.join(ROOT, "assets/qr/*.png")
QR_MIN_SECONDS = 10.0

# --- cuts ---------------------------------------------------------------
# (image-key, start, end, section, theme, motion, camera_from, camera_to, dissolve_in)
# camera = (cx, cy, zoom) ; cx,cy are 0..1 of the image, zoom>=1 relative to the largest 16:9 window.
S = lambda cx=.5, cy=.5, z=1.0: (cx, cy, z)
CUTS = [
    # key,                   t0,     t1,     section,       theme,                                     motion,    from,            to,              fade
    ("p001_title",           0.00,   5.50,   "INTRO",       "雪と灯り。物語はまだ始まらない",             "zoom in", S(.5,.66,1.00), S(.5,.66,1.07), 0.0),
    ("p002_003_warmth",      5.50,  12.00,   "INTRO",       "遠い記憶のぬくもり",                       "pan →",   S(.30,.5,1.02), S(.42,.5,1.06), 1.6),
    ("p004_005_snow",       12.00,  19.00,   "VERSE 1",     "ぬくもりが消える。雪",                      "still",   S(.5,.5,1.00),  S(.5,.5,1.02),  1.2),
    ("p006_007_stop_waiting",19.00, 26.00,   "VERSE 1",     "待つのをやめた",                           "zoom in", S(.5,.5,1.00),  S(.46,.5,1.09), 1.2),
    ("p008_009_found",      26.00,  33.50,   "VERSE 1",     "雪を踏む足音。女の子が来る",                 "pan →",   S(.32,.5,1.04), S(.62,.5,1.04), 1.2),
    ("p010_011_distance",   33.50,  38.75,   "PRE-CHORUS",  "怖かったね。すぐには信じられない",           "pan ←",   S(.62,.5,1.03), S(.40,.5,1.03), 1.0),
    ("p012_013_every_day",  38.75,  44.00,   "PRE-CHORUS",  "昨日もいた。今日もいる。(本の心臓)",         "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  1.0),
    ("p014_015_first_step", 44.00,  50.00,   "CHORUS 1",    "自分の足で近づく",                          "pan →",   S(.34,.5,1.02), S(.60,.5,1.02), 0.8),
    ("p016_017_safe",       50.00,  56.00,   "CHORUS 1",    "もう一度、春が来た",                        "zoom in", S(.5,.5,1.00),  S(.58,.55,1.12), 0.8),
    ("p018_019_seasons",    56.00,  66.00,   "BREATH",      "春夏秋冬。季節が過ぎる",                    "pan →",   S(.26,.5,1.00), S(.74,.5,1.00), 2.0),
    ("p020_021_farewell",   66.00,  75.75,   "VERSE 2",     "静かな別れ。空いた場所(長く止める)",         "still",   S(.5,.5,1.00),  S(.5,.5,1.02),  1.8),
    ("p022_023_new_friend", 75.75,  82.00,   "VERSE 2",     "黄金色のうさぎと暮らす",                    "zoom out",S(.55,.5,1.10), S(.5,.5,1.00),  1.2),
    ("p024_025_meals_naps", 82.00,  87.00,   "VERSE 2",     "一緒にごはん、お昼寝",                      "pan →",   S(.34,.5,1.02), S(.56,.5,1.02), 1.0),
    ("p026_027_seasons",    87.00,  92.25,   "VERSE 2",     "いつも、となりにいた",                      "pan →",   S(.30,.5,1.02), S(.66,.5,1.02), 1.0),
    ("p028_029_love",       92.25,  98.00,   "CHORUS 2",    "毎日がやさしかった",                        "zoom in", S(.5,.5,1.00),  S(.40,.5,1.08), 0.8),
    ("p030_031_farewell",   98.00, 104.75,   "CHORUS 2",    "虹の橋を渡る(静止)",                        "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  1.0),
    ("p032_033_quiet_room", 104.75,111.00,   "CHORUS 2",    "ぽっかり空いた場所",                        "zoom in", S(.5,.5,1.00),  S(.38,.55,1.10), 1.0),
    ("p034_035_figurine_found",111.00,116.50,"CHORUS 2",    "黄金のうさぎの置物と出会う",                 "pan →",   S(.34,.5,1.03), S(.66,.5,1.03), 0.8),
    ("p036_037_figurine_home",116.50,121.50, "CHORUS 2",    "あの子のいた場所の近くへ",                   "zoom out",S(.62,.5,1.10), S(.5,.5,1.00),  0.8),
    ("p038_039_not_a_replacement",121.50,127.25,"CHORUS 2", "代わりではない。胸の穴が少しやわらぐ",       "still",   S(.5,.5,1.00),  S(.5,.5,1.03),  1.0),
    ("p040_041_shadow",     127.25, 131.50,  "BRIDGE",      "置物の後ろの大きな影(違和感を残す)",         "zoom in", S(.30,.5,1.02), S(.26,.5,1.12), 1.0),
    ("p042_043_lost",       131.50, 135.00,  "BRIDGE",      "道に迷う",                                  "pan →",   S(.34,.5,1.03), S(.50,.5,1.03), 0.7),
    ("p044_045_voice",      135.00, 138.50,  "BRIDGE",      "「……こっちだよ。」",                         "zoom in", S(.5,.5,1.00),  S(.5,.5,1.08), 0.7),
    ("p060_061_light",      138.50, 142.00,  "BRIDGE",      "道の先の小さな灯り",                        "pan →",   S(.34,.5,1.03), S(.62,.5,1.03), 0.7),
    ("p064_065_door",       142.00, 145.00,  "BRIDGE",      "一枚の扉",                                  "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  0.6),
    ("p066_067_come_in",    145.00, 149.50,  "LAST CHORUS", "「おう。入んな。」",                         "zoom in", S(.5,.5,1.00),  S(.5,.5,1.06), 0.5),
    ("p068_069_first_sight",149.50, 154.00,  "LAST CHORUS", "声だけだった、大きなうさぎ",                  "pan →",   S(.36,.5,1.03), S(.60,.5,1.03), 0.8),
    ("p070_071_oyabun",     154.00, 160.00,  "LAST CHORUS", "親分。怖くない、頼もしい",                    "pan →",   S(.30,.5,1.02), S(.58,.5,1.02), 0.8),
    ("p080_081_recognition",160.00, 166.25,  "LAST CHORUS", "「やっと気づいたか。ずっとここにいたぞ」(静止)", "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  1.0),
    ("p084_085_empty_seat", 166.25, 169.50,  "OUTRO",       "席をひとつ空けておく",                      "still",   S(.5,.5,1.00),  S(.5,.5,1.02),  1.8),
    ("p086_087_home",       169.50, 172.50,  "OUTRO",       "どこにいても帰る場所はある",                 "zoom in", S(.5,.5,1.00),  S(.56,.5,1.05), 1.8),
    ("p088_welcome",        172.50, None,    "END CARD",    "宇宙酒場。親分。QRコード",                   "zoom in", S(.5,.58,1.00), S(.5,.58,1.04), 2.5),
]

# (text, start, end, style) -- sparse by design: key phrases only, no running subtitles.
TEXTS = [
    ("虹の向こうで会いたい — 続編", 2.0, 6.0, "title"),
    ("「おう。入んな。」",           146.0, 149.0, "line"),
    ("「やっと気づいたか。」",        161.0, 163.8, "line"),
    ("「ずっとここにいたぞ。」",      163.8, 166.0, "line"),
    ("「おう。帰ってきたか。」",      173.8, 177.4, "line_end"),
    ("「……まあ、座んな。」",         177.8, 181.2, "line_end"),
    ("おかえり",                     181.4, None,  "title_end"),
]
FADE_IN = 1.2
FADE_OUT = 1.2


def audio_duration():
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", AUDIO]).decode().strip()
    return float(out)


def ts(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def write_timeline(cuts, texts, qr_path, dur):
    p = os.path.join(ROOT, "work/storyboard/timeline.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    lines = ["# timeline (auto-generated by scripts/build_mv.py)", "",
             f"audio: assets/audio/song.m4a  ({ts(dur)})  / 約86BPM / 歌詞ファイル未提供のため区間はエネルギー解析ベース", "",
             "| start | end | section | lyric/theme | visual | motion | transition | source |",
             "|---|---|---|---|---|---|---|---|"]
    for c in cuts:
        key, t0, t1, sec, theme, motion, f, to, fade = c
        t1 = dur if t1 is None else t1
        tr = "fade in" if fade == 0 else f"dissolve {fade:.1f}s"
        lines.append(f"| {ts(t0)} | {ts(t1)} | {sec} | {theme} | {key} | {motion} | {tr} | assets/images/art_{key}_png.jpg |")
    lines += ["", "## text overlays", "", "| start | end | text |", "|---|---|---|"]
    for t, a, b, _ in texts:
        lines.append(f"| {ts(a)} | {ts(dur if b is None else b)} | {t} |")
    lines += ["", f"QR: {'`'+os.path.relpath(qr_path, ROOT)+'`' if qr_path else '**未配置 (assets/qr/*.png を置くと自動で終盤に表示)**'}"]
    open(p, "w").write("\n".join(lines) + "\n")


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Still:
    def __init__(self, key):
        path = os.path.join(IMG, f"art_{key}_png.jpg")
        self.im = Image.open(path).convert("RGB")
        w, h = self.im.size
        if w / h >= 16 / 9:
            self.bh, self.bw = h, h * 16 / 9
        else:
            self.bw, self.bh = w, w * 9 / 16

    def frame(self, cam, size=(W, H)):
        cx, cy, z = cam
        w, h = self.im.size
        bw, bh = self.bw / z, self.bh / z
        x0 = min(max(cx * w - bw / 2, 0), w - bw)
        y0 = min(max(cy * h - bh / 2, 0), h - bh)
        return self.im.transform(size, Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BICUBIC)


def lerp_cam(a, b, u):
    u = smoothstep(u) if False else u
    e = u * u * (3 - 2 * u)  # ease in/out
    return tuple(a[i] + (b[i] - a[i]) * e for i in range(3))


def text_layer(txt, style, font_cache={}):
    sizes = {"title": 54, "line": 62, "line_end": 62, "title_end": 120}
    size = sizes[style]
    if size not in font_cache:
        font_cache[size] = ImageFont.truetype(FONT, size)
    f = font_cache[size]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw = d.textlength(txt, font=f)
    # safe area: >= 8% margins. Lines sit in lower third, titles centered.
    if style == "title":
        xy = ((W - tw) / 2, 86)
    elif style == "title_end":
        xy = (150, 150)  # left, clear of the character's face on the right
    else:
        xy = ((W - tw) / 2, H - 190)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text(xy, txt, font=f, fill=(0, 0, 0, 230))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    layer = Image.alpha_composite(shadow, layer)
    ImageDraw.Draw(layer).text(xy, txt, font=f, fill=(255, 244, 222, 255))
    return layer


def qr_plate(path, size=380, margin=30):
    qr = Image.open(path).convert("RGB").resize((size, size), Image.NEAREST if Image.open(path).width >= size else Image.LANCZOS)
    plate = Image.new("RGB", (size + margin * 2, size + margin * 2), (255, 255, 255))
    plate.paste(qr, (margin, margin))
    return plate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "output/preview/mv_preview.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=23)
    ap.add_argument("--timeline-only", action="store_true")
    ap.add_argument("--limit", type=float, default=None, help="render only the first N seconds (debug)")
    a = ap.parse_args()

    dur = audio_duration()
    qrs = sorted(glob.glob(QR_GLOB))
    qr_path = qrs[0] if qrs else None
    cuts = [(k, t0, dur if t1 is None else t1, *rest) for (k, t0, t1, *rest) in CUTS]
    write_timeline(CUTS, TEXTS, qr_path, dur)
    if a.timeline_only:
        return
    end_card_start = cuts[-1][1]
    assert dur - end_card_start >= QR_MIN_SECONDS, "end card shorter than QR minimum"

    stills = {c[0]: Still(c[0]) for c in cuts}
    qr_img = qr_plate(qr_path) if qr_path else None
    texts = [(t, s, dur if e is None else e, st) for t, s, e, st in TEXTS]
    text_cache = {}

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    total = int(round((a.limit or dur) * a.fps))
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-",
         "-i", AUDIO,
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
         "-pix_fmt", "yuv420p", "-r", str(a.fps), "-c:a", "aac", "-b:a", "192k",
         "-t", f"{a.limit or dur:.3f}", "-movflags", "+faststart", a.out],
        stdin=subprocess.PIPE)

    def cut_frame(c, t):
        key, t0, t1, _, _, _, cf, ct, fade = c
        u = (t - t0) / max(t1 - t0, 1e-6)
        return stills[key].frame(lerp_cam(cf, ct, min(max(u, 0), 1)))

    for n in range(total):
        t = n / a.fps
        # find active cut(s): cut i owns [t0_i, t0_{i+1}); next cut dissolves in over its `fade` window ending at its t0+fade/2.
        idx = max(i for i, c in enumerate(cuts) if c[1] - c[8] / 2 <= t or i == 0)
        c = cuts[idx]
        # a dissolve into cut idx is active while t < t0 + fade/2
        fr = cut_frame(c, t)
        fade = c[8]
        if idx > 0 and fade > 0:
            u = (t - (c[1] - fade / 2)) / fade
            if u < 1:
                prev = cut_frame(cuts[idx - 1], t)
                fr = Image.blend(prev, fr, smoothstep(u))
        # fades from/to black
        k = smoothstep(t / FADE_IN) * smoothstep((dur - t) / FADE_OUT)
        if k < 1:
            fr = Image.blend(Image.new("RGB", (W, H)), fr, k)
        # text
        for txt, s, e, st in texts:
            if s - 0.01 <= t <= e:
                ka = smoothstep((t - s) / 0.7) * smoothstep((e - t) / 0.7)
                if ka > 0:
                    if (txt, st) not in text_cache:
                        text_cache[(txt, st)] = text_layer(txt, st)
                    layer = text_cache[(txt, st)]
                    if ka < 1:
                        layer = layer.copy()
                        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * ka)))
                    fr = Image.alpha_composite(fr.convert("RGBA"), layer).convert("RGB")
        # QR: static, un-rotated, opaque, on a white quiet-zone plate; shown for the whole end card
        if qr_img is not None and t >= end_card_start + 1.5:
            pos = (W - qr_img.width - 110, H - qr_img.height - 100)
            fr = fr.copy()
            fr.paste(qr_img, pos)
        ff.stdin.write(fr.tobytes())
        if n % 300 == 0:
            print(f"\r{ts(t)} / {ts(dur)}", end="", file=sys.stderr, flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"\nwrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
