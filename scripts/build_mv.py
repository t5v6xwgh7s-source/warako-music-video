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
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1920, 1080
AUDIO = os.path.join(ROOT, "assets/audio/song.m4a")
IMG = os.path.join(ROOT, "assets/images")
FONT = os.path.join(ROOT, "assets/fonts/ZenMaruGothic-Medium.ttf")   # soft rounded gothic (OFL)
LYRICS_TSV = os.path.join(ROOT, "work/storyboard/lyrics_timing.tsv")
QR_GLOB = os.path.join(ROOT, "assets/qr/*.png")
QR_MIN_SECONDS = 10.0
FADE_IN, FADE_OUT = 1.2, 1.2
PAGE_TOP = 190          # page-mode: top band reserved for lyrics (blurred backdrop)
GUTTER = 4              # px trimmed next to the fold in page-mode

S = lambda cx=.5, cy=.5, z=1.0: (cx, cy, z)
P = lambda z0=1.0, z1=1.0: ((.5, .5, z0), (.5, .5, z1))     # page-mode camera = zoom only

# --- cuts ---------------------------------------------------------------------------------------------
# key, t0, t1, section, theme, motion, cam_from, cam_to, dissolve_in, page(None|"L"|"R")
# Page rows ("@L"/"@R") show ONE page of a two-page spread on a blurred backdrop: the book's pages are
# independent paintings and the fold shows as a hard seam if the spread is panned across (see asset_review.md).
CUTS = [
    ("p001_title",            0.00,   5.50, "INTRO",       "雪と灯り。物語はまだ始まらない",          "zoom in", S(.5,.66,1.00), S(.5,.66,1.07), 0.0, None),
    ("p002_003_warmth",       5.50,  12.00, "INTRO",       "遠い記憶のぬくもり",                      "pan →",   S(.30,.5,1.02), S(.42,.5,1.06), 1.6, None),
    ("p004_005_snow",        12.00,  15.30, "VERSE 1",     "ぬくもりが消える。ひとりの雪の路地(左頁)", "still",   *P(1.0,1.02),                    1.2, "L"),
    ("p004_005_snow",        15.30,  19.00, "VERSE 1",     "ゴミ袋の陰の小さなうさぎ(右頁)",           "zoom in", *P(1.0,1.05),                    1.0, "R"),
    ("p006_007_stop_waiting",19.00,  26.00, "VERSE 1",     "待つのをやめた",                           "zoom in", S(.5,.5,1.00),  S(.46,.5,1.09), 1.2, None),
    ("p008_009_found",       26.00,  33.50, "VERSE 1",     "雪を踏む足音。女の子が来る",                "pan →",   S(.32,.5,1.04), S(.62,.5,1.04), 1.2, None),
    ("p010_011_distance",    33.50,  38.75, "PRE-CHORUS",  "怖かったね。すぐには信じられない",          "pan ←",   S(.62,.5,1.03), S(.40,.5,1.03), 1.0, None),
    ("p012_013_every_day",   38.75,  41.40, "PRE-CHORUS",  "昨日もいた(左頁)",                         "still",   *P(1.0,1.015),                   1.0, "L"),
    ("p012_013_every_day",   41.40,  44.00, "PRE-CHORUS",  "今日もいる。明日もたぶんいる(右頁)",        "still",   *P(1.0,1.015),                   0.9, "R"),
    ("p014_015_first_step",  44.00,  50.00, "CHORUS 1",    "自分の足で近づく",                         "pan →",   S(.34,.5,1.02), S(.60,.5,1.02), 0.8, None),
    ("p016_017_safe",        50.00,  56.00, "CHORUS 1",    "もう一度、春が来た",                       "zoom in", S(.5,.5,1.00),  S(.58,.55,1.12), 0.8, None),
    ("p018_019_seasons",     56.00,  66.00, "BREATH",      "春夏秋冬。季節が過ぎる",                   "pan →",   S(.26,.5,1.00), S(.74,.5,1.00), 2.0, None),
    ("p020_021_farewell",    66.00,  75.75, "VERSE 2",     "静かな別れ。空いた場所(長く止める)",        "still",   S(.5,.5,1.00),  S(.5,.5,1.02),  1.8, None),
    ("p022_023_new_friend",  75.75,  82.00, "VERSE 2",     "黄金色のうさぎと暮らす",                   "zoom out",S(.55,.5,1.10), S(.5,.5,1.00),  1.2, None),
    ("p024_025_meals_naps",  82.00,  84.60, "VERSE 2",     "一緒にごはん(左頁)",                       "zoom in", *P(1.0,1.03),                    1.0, "L"),
    ("p024_025_meals_naps",  84.60,  87.00, "VERSE 2",     "一緒にお昼寝(右頁)",                       "zoom in", *P(1.0,1.03),                    0.8, "R"),
    ("p026_027_seasons",     87.00,  92.25, "VERSE 2",     "四つの季節の、いつもとなり(4コマを一枚で)", "still",   S(.5,.5,1.00),  S(.5,.5,1.03),  1.0, None),
    ("p028_029_love",        92.25,  95.10, "CHORUS 2",    "毎日がやさしかった(左頁)",                 "zoom in", *P(1.0,1.04),                    0.8, "L"),
    ("p028_029_love",        95.10,  98.00, "CHORUS 2",    "抱きしめる(右頁)",                         "zoom in", *P(1.0,1.04),                    0.7, "R"),
    ("p030_031_farewell",    98.00, 102.50, "CHORUS 2",    "虹の橋を渡る(左頁・静止に近い)",           "still",   *P(1.0,1.02),                    1.0, "L"),
    ("p030_031_farewell",   102.50, 104.75, "CHORUS 2",    "空いた寝床(右頁)",                         "still",   *P(1.0,1.02),                    1.0, "R"),
    ("p032_033_quiet_room", 104.75, 107.90, "CHORUS 2",    "ぽっかり空いた場所(左頁)",                 "zoom in", *P(1.0,1.04),                    1.0, "L"),
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
    ("p064_065_door",       142.00, 145.00, "BRIDGE",      "一枚の扉",                                 "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  0.6, None),
    ("p066_067_come_in",    145.00, 149.50, "LAST CHORUS", "扉の向こうの声「入んな」",                  "zoom in", S(.5,.5,1.00),  S(.5,.5,1.06),  0.5, None),
    ("p068_069_first_sight",149.50, 154.00, "LAST CHORUS", "声だけだった、大きなうさぎ",                 "pan →",   S(.36,.5,1.03), S(.60,.5,1.03), 0.8, None),
    ("p070_071_oyabun",     154.00, 160.00, "LAST CHORUS", "親分。怖くない、頼もしい",                   "pan →",   S(.30,.5,1.02), S(.58,.5,1.02), 0.8, None),
    ("p080_081_recognition",160.00, 166.25, "LAST CHORUS", "雪の日|いま。「ずっとここにいたぞ」(静止)",  "still",   S(.5,.5,1.00),  S(.5,.5,1.00),  1.0, None),
    ("p084_085_empty_seat", 166.25, 169.50, "OUTRO",       "席をひとつ空けておく",                     "still",   S(.5,.5,1.00),  S(.5,.5,1.02),  1.8, None),
    ("p086_087_home",       169.50, 172.50, "OUTRO",       "どこにいても帰る場所はある",                "zoom in", S(.5,.5,1.00),  S(.56,.5,1.05), 1.8, None),
    ("END_CARD",            172.50, None,   "END CARD",    "宇宙酒場。親分。「おかえりって」の余韻。QR", "zoom in", S(.5,.58,1.00), S(.5,.58,1.04), 2.5, None),
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


def end_card_image_key():
    for p in sorted(glob.glob(os.path.join(IMG, "oyabun_bar.*"))):
        return os.path.splitext(os.path.basename(p))[0], p
    return END_CARD_KEY, os.path.join(IMG, f"art_{END_CARD_KEY}_png.jpg")


def resolve_cuts(dur):
    cuts = []
    for key, t0, t1, sec, theme, motion, cf, ct, fade, page in CUTS:
        cuts.append(dict(key=key, t0=t0, t1=dur if t1 is None else t1, sec=sec, theme=theme, motion=motion,
                         cf=cf, ct=ct, fade=fade, page=page))
    return cuts


def img_path(key):
    if key == "END_CARD":
        return end_card_image_key()[1]
    return os.path.join(IMG, f"art_{key}_png.jpg")


# --- stills ----------------------------------------------------------------------------------------
class Still:
    """One source image. frame() = full-bleed 16:9 window; page_frame() = a single book page on a blurred backdrop."""
    def __init__(self, key, page=None):
        self.im = Image.open(img_path(key)).convert("RGB")
        w, h = self.im.size
        if w / h >= 16 / 9:
            self.bh, self.bw = h, h * 16 / 9
        else:
            self.bw, self.bh = w, w * 9 / 16
        self.page = page
        if page:
            half = w // 2
            box = (0, 0, half - GUTTER, h) if page == "L" else (half + GUTTER, 0, w, h)
            self.pg = self.im.crop(box)
            bg = self.pg.resize((W, int(self.pg.height * W / self.pg.width)), Image.BICUBIC)
            y0 = (bg.height - H) // 2
            bg = bg.crop((0, y0, W, y0 + H)).filter(ImageFilter.GaussianBlur(48))
            self.bg = Image.eval(bg, lambda v: int(v * 0.55))

    def frame(self, cam):
        cx, cy, z = cam
        w, h = self.im.size
        bw, bh = self.bw / z, self.bh / z
        x0 = min(max(cx * w - bw / 2, 0), w - bw)
        y0 = min(max(cy * h - bh / 2, 0), h - bh)
        return self.im.transform((W, H), Image.EXTENT, (x0, y0, x0 + bw, y0 + bh), Image.BICUBIC)

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
        self.end_card_start = self.cuts[-1]["t0"]
        self.stills = {}
        self.qr = sorted(glob.glob(QR_GLOB))
        self.qr_img = None
        if self.qr:
            qr = Image.open(self.qr[0]).convert("RGB")
            size, margin = 380, 30
            qr = qr.resize((size, size), Image.NEAREST if qr.width >= size else Image.LANCZOS)
            plate = Image.new("RGB", (size + margin * 2, size + margin * 2), (255, 255, 255))
            plate.paste(qr, (margin, margin))
            self.qr_img = plate
        self.captions = build_captions(dur)
        self.title = dict(id="title", lines=[dict(text="虹の向こうで会いたい — 続編", start=2.0, end=6.0, show=2.0, conf="n/a")], t_in=2.0, t_out=6.4)
        self.layouts = []
        for cap in self.captions + [self.title]:
            anchor = "C" if cap["id"] == "title" else choose_anchor(cap, self.cuts, forced={"outro1": "L", "outro2": "L"}.get(cap["id"]))
            cap["anchor"] = anchor
            self.layouts.append((cap, layout_caption(cap, anchor)))

    def still(self, cut):
        k = (cut["key"], cut["page"])
        if k not in self.stills:
            self.stills[k] = Still(cut["key"], cut["page"])
        return self.stills[k]

    def cut_frame(self, cut, t):
        u = (t - cut["t0"]) / max(cut["t1"] - cut["t0"], 1e-6)
        cam = lerp_cam(cut["cf"], cut["ct"], min(max(u, 0), 1))
        st = self.still(cut)
        return st.page_frame(cam) if cut["page"] else st.frame(cam)

    def base_frame(self, t):
        cuts = self.cuts
        idx = max(i for i, c in enumerate(cuts) if c["t0"] - c["fade"] / 2 <= t or i == 0)
        c = cuts[idx]
        fr = self.cut_frame(c, t)
        if idx > 0 and c["fade"] > 0:
            u = (t - (c["t0"] - c["fade"] / 2)) / c["fade"]
            if u < 1:
                fr = Image.blend(self.cut_frame(cuts[idx - 1], t), fr, smoothstep(u))
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

    def frame_at(self, t, with_text=True, return_info=False):
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
        if self.qr_img is not None and t >= self.end_card_start + 1.5:
            fr = fr.copy()
            fr.paste(self.qr_img, (W - self.qr_img.width - 110, H - self.qr_img.height - 100))
        if k < 1:
            fr = Image.blend(Image.new("RGB", (W, H)), fr, k)
        return (fr, info) if return_info else fr


def write_timeline(cuts, caps, qr_path, dur, endkey):
    p = os.path.join(ROOT, "work/storyboard/timeline.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    L = ["# timeline (auto-generated by scripts/build_mv.py)", "",
         f"audio: assets/audio/song.m4a ({ts(dur)}) / 約86BPM (小節=2.79s, 1拍目=0.49s) / 歌詞: assets/lyrics/虹の向こうで会いたい_歌詞.txt (同期は推定。lyrics_timing.tsv 参照)", "",
         "| start | end | section | lyric/theme | visual | motion | transition | source |",
         "|---|---|---|---|---|---|---|---|"]
    for c in cuts:
        tr = "fade in" if c["fade"] == 0 else f"dissolve {c['fade']:.1f}s"
        key = endkey if c["key"] == "END_CARD" else c["key"]
        vis = key + (f" [{c['page']}頁]" if c["page"] else "")
        src = os.path.relpath(img_path(c["key"]), ROOT)
        L.append(f"| {ts(c['t0'])} | {ts(c['t1'])} | {c['sec']} | {c['theme']} | {vis} | {c['motion']} | {tr} | {src} |")
    L += ["", "## lyric captions (歌唱=推定位置 / 表示=実際の表示区間)", "",
          "| display in | display out | sung start-end | anchor | text | confidence |", "|---|---|---|---|---|---|"]
    for cap in caps:
        for ln in cap["lines"]:
            L.append(f"| {ts(ln['show'])} | {ts(cap['t_out'])} | {ts(ln['start'])}-{ts(ln['end'])} | {cap.get('anchor','?')} | {ln['text']} | {ln['conf']} |")
    L += ["", f"QR: {'`'+os.path.relpath(qr_path, ROOT)+'`' if qr_path else '**未配置 (assets/qr/*.png を置くと終盤に自動表示)**'}",
          f"end card image: `{os.path.relpath(img_path('END_CARD'), ROOT)}`"]
    open(p, "w", encoding="utf8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "output/preview/mv_preview.mp4"))
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=23)
    ap.add_argument("--timeline-only", action="store_true")
    ap.add_argument("--limit", type=float, default=None)
    ap.add_argument("--frames", default=None, help="comma-separated seconds: write PNG stills instead of a video")
    ap.add_argument("--frames-dir", default=os.path.join(ROOT, "work/temp/qa"))
    a = ap.parse_args()

    dur = audio_duration()
    r = Renderer(dur, a.fps)
    qr_path = r.qr[0] if r.qr else None
    write_timeline(r.cuts, r.captions, qr_path, dur, end_card_image_key()[0])
    if a.timeline_only:
        return
    assert dur - r.end_card_start >= QR_MIN_SECONDS, "end card shorter than QR minimum"
    if a.frames:
        os.makedirs(a.frames_dir, exist_ok=True)
        for t in [float(x) for x in a.frames.split(",")]:
            r.frame_at(t).save(os.path.join(a.frames_dir, f"t{t:07.2f}.png"))
        return

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    total = int(round((a.limit or dur) * a.fps))
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-",
         "-i", AUDIO, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
         "-pix_fmt", "yuv420p", "-r", str(a.fps), "-c:a", "aac", "-b:a", "192k",
         "-t", f"{a.limit or dur:.3f}", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for n in range(total):
        ff.stdin.write(r.frame_at(n / a.fps).tobytes())
        if n % 300 == 0:
            print(f"\r{ts(n / a.fps)} / {ts(dur)}", end="", file=sys.stderr, flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"\nwrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
