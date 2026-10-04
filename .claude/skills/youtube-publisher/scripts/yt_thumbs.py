#!/usr/bin/env python3
"""Make 1280x720 thumbnail candidates (project independent).

  yt_thumbs.py --video V.mp4 --at 34.3 --text "TITLE" --out thumbnails/a.jpg [--font F.ttf] [--pos bottom|top|center]
  yt_thumbs.py --image IMG --text "..." --out ...   (cover-crop of a still)

Cover-crops the frame/image to 16:9, adds a soft dark gradient where the text sits, and draws the text (outline + shadow, fitted
to ~90% of the width). The text is a human decision; leave --text out for a text-free candidate. Keeps the JPG under 2 MB.
"""
import argparse, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--video"); ap.add_argument("--at", type=float, default=0.0); ap.add_argument("--image")
ap.add_argument("--text", default=""); ap.add_argument("--out", required=True)
ap.add_argument("--font", default=""); ap.add_argument("--pos", default="bottom", choices=["bottom", "top", "center"])
a = ap.parse_args()
if a.video:
    tmp = os.path.join(tempfile.gettempdir(), "_thumb_src.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.at), "-i", a.video, "-frames:v", "1", tmp], check=True)
    im = Image.open(tmp).convert("RGB")
elif a.image:
    im = Image.open(a.image).convert("RGB")
else:
    sys.exit("give --video/--at or --image")
W, H = 1280, 720
s = max(W / im.width, H / im.height)
im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
x0, y0 = (im.width - W) // 2, (im.height - H) // 2
im = im.crop((x0, y0, x0 + W, y0 + H))
if a.text:
    font_path = a.font or next((p for p in ("assets/fonts/ZenMaruGothic-Medium.ttf",) if os.path.exists(p)), "")
    size = 130
    while size > 40:
        f = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        w = ImageDraw.Draw(im).textlength(a.text, font=f)
        if w <= W * 0.9:
            break
        size -= 4
    ty = {"bottom": H - size - 70, "top": 50, "center": (H - size) // 2}[a.pos]
    band = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(band)
    by0, by1 = (H * 0.45, H) if a.pos == "bottom" else ((0, H * 0.55) if a.pos == "top" else (H * 0.3, H * 0.75))
    for y in range(int(by0), int(by1)):
        t = (y - by0) / (by1 - by0)
        a_ = (t if a.pos == "bottom" else (1 - t) if a.pos == "top" else 1 - abs(2 * t - 1))
        d.line([(0, y), (W, y)], fill=int(150 * a_))
    im = Image.composite(Image.new("RGB", (W, H), (10, 6, 4)), im, band)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tx = (W - w) / 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((tx, ty), a.text, font=f, fill=(0, 0, 0, 210), stroke_width=8, stroke_fill=(0, 0, 0, 210))
    layer = Image.alpha_composite(layer, sh.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(layer).text((tx, ty), a.text, font=f, fill=(255, 248, 235, 255), stroke_width=5, stroke_fill=(60, 34, 24, 255))
    im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
q = 92
im.save(a.out, quality=q)
while os.path.getsize(a.out) > 1.9 * 1024 * 1024 and q > 60:
    q -= 6
    im.save(a.out, quality=q)
print(f"wrote {a.out} ({os.path.getsize(a.out)/1024:.0f} KiB)")
