#!/usr/bin/env python3
"""Lyric overlay QA (STEP 10 for the telop): exports frames around every caption and prints metrics.

Checks: safe area / cut-off, contrast vs. backdrop, anchor-vs-subject conflicts (from build_mv.ANCHOR_OK),
display timing (early/late/too short), gap to the next caption. Frames go to work/temp/qa_lyrics/.
"""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_mv", os.path.join(ROOT, "scripts/build_mv.py"))
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)
from PIL import Image

OUT = os.path.join(ROOT, "work/temp/qa_lyrics")
os.makedirs(OUT, exist_ok=True)
dur = bm.audio_duration()
r = bm.Renderer(dur)
W, H = bm.W, bm.H
SAFE_X, SAFE_Y = 96, 54      # title-safe margins (5% of 1920x1080 on top, 5% of width on the sides)
issues = []


def lum(c):
    f = lambda v: (v / 255) ** 2.2
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def cut_at(t):
    for c in r.cuts:
        if c["t0"] <= t < c["t1"]:
            return c
    return r.cuts[-1]


print(f"{'caption':16s} {'anchor':6s} {'show':>7s} {'sung':>7s} {'out':>7s} {'hold':>5s} {'gap':>5s} {'outlCR':>6s} {'bg90':>5s}  note")
caps = r.captions
for i, cap in enumerate(caps):
    lay = next(l for c, l in r.layouts if c is cap)
    notes = []
    # safe area
    for L in lay:
        x0, y0, x1, y1 = L["bbox"]
        if x0 < SAFE_X or x1 > W - SAFE_X or y0 < SAFE_Y or y1 > H - SAFE_Y:
            notes.append("OUT-OF-SAFE")
    # anchor conflicts over the display window
    pen = 0.0
    for c in r.cuts:
        ov = min(cap["t_out"], c["t1"]) - max(cap["t_in"], c["t0"])
        if ov > 0.05:
            p = bm.anchor_penalty(c, cap["anchor"])
            if p >= 4:
                notes.append(f"clash:{c['key']}{'@'+c['page'] if c['page'] else ''}")
            pen += ov * p
    # contrast at the moment every line of the caption is visible (backdrop after the adaptive scrim)
    t_full = min(cap["t_out"] - 0.1, max(l["show"] for l in cap["lines"]) + 1.3)
    t_mid = (max(l["show"] for l in cap["lines"]) + cap["t_out"]) / 2
    crs = []
    bright = []
    for tt in (t_full, t_mid):
        fr_bg = r.frame_at(tt, with_text=False)
        for L in lay:
            x0, y0, x1, y1 = L["bbox"]
            reg_bg = fr_bg.crop((x0, y0, x1, y1)).resize((max(1, (x1 - x0) // 6), max(1, (y1 - y0) // 6)))
            bpx = sorted(reg_bg.getdata(), key=lum)
            bright.append(lum(bpx[int(len(bpx) * 0.9)]))
        # worst-case local contrast = white glyph vs. dark outline (always high) and glyph vs. backdrop p90
    bright_p90 = max(bright)
    OUTLINE_CR = (lum((255, 247, 233)) + 0.05) / (lum((52, 30, 22)) + 0.05)
    crs = [OUTLINE_CR, (lum((255, 247, 233)) + 0.05) / (bright_p90 + 0.05)]
    min_cr = min(crs)
    if bright_p90 > 0.55:
        notes.append("bright-backdrop(outline+scrim)")
    first_show = cap["lines"][0]["show"]
    early = cap["lines"][0]["start"] - first_show
    hold = cap["t_out"] - cap["lines"][-1]["end"]
    gap = (caps[i + 1]["lines"][0]["show"] - cap["t_out"]) if i + 1 < len(caps) else float("nan")
    if hold + 0.15 < 0.25 and cap["id"] != "title":    # +0.15 = visible part of the 0.30s fade-out
        notes.append("disappears-early")
    if gap == gap and gap < 0.12:
        notes.append("next-too-soon")
    print(f"{cap['id']:16s} {cap['anchor']:6s} {first_show:7.2f} {cap['lines'][0]['start']:7.2f} {cap['t_out']:7.2f} {hold:5.2f} {gap:5.2f} {OUTLINE_CR:6.1f} {bright_p90:5.2f}  {' '.join(notes)}")
    for tt, tag in ((t_full, "a_full"), (cap["t_out"] + 0.05, "b_out")):
        r.frame_at(min(max(tt, 0), dur - 0.02)).save(os.path.join(OUT, f"{i:02d}_{cap['id']}_{tag}.png"))
    # frame just before the next caption appears (should be clean) and just after it appears
    if i + 1 < len(caps):
        r.frame_at(caps[i + 1]["lines"][0]["show"] + 0.2).save(os.path.join(OUT, f"{i:02d}_{cap['id']}_c_next.png"))
print("frames in", OUT)
