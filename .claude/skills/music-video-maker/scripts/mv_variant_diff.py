#!/usr/bin/env python3
"""Compare a variant video with its baseline and check that only the intended window changed (project independent).

  python3 mv_variant_diff.py --baseline B.mp4 --variant V.mp4 --window START END
                             [--frozen LABEL=SEC ...] [--times T1,T2,...] [--step 2] [--out DIR] [--name NAME]

Reports: durations equal; frozen points identical (frame PSNR >= 40 dB); outside the window identical (sampled every --step s,
PSNR >= 38 dB); inside the window actually different; plus a baseline-vs-variant frame sheet and diff_vs_baseline.md in --out.
The baseline file is only read. Exit 1 if a frozen point or the outside changed, or if nothing changed inside the window.
"""
import argparse, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--baseline", required=True)
ap.add_argument("--variant", required=True)
ap.add_argument("--window", nargs=2, type=float, required=True, metavar=("START", "END"))
ap.add_argument("--frozen", nargs="*", default=[], help="LABEL=SECONDS points that must not change")
ap.add_argument("--times", default="", help="comma separated seconds for the frame sheet (default: 8 points across the window)")
ap.add_argument("--step", type=float, default=2.0)
ap.add_argument("--margin", type=float, default=0.5, help="seconds around the window not judged (dissolves)")
ap.add_argument("--out", default=".")
ap.add_argument("--name", default="variant")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], text=True))


def frame(p, t, size=None):
    tmp = os.path.join(a.out, "_f.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", p, "-frames:v", "1", tmp], check=True)
    im = Image.open(tmp).convert("RGB")
    return im.resize(size) if size else im


def psnr(x, y):
    d = ((np.asarray(x, float) - np.asarray(y, float)) ** 2).mean()
    return 99.0 if d == 0 else 10 * np.log10(255 ** 2 / d)


ts = lambda t: f"{int(t // 60)}:{t % 60:05.2f}"
w0, w1 = a.window
bd, vd = dur(a.baseline), dur(a.variant)
L = [f"# {a.name} vs baseline", "", f"- baseline: `{a.baseline}`(読み取りのみ)", f"- variant : `{a.variant}`",
     f"- 変更窓: {ts(w0)} 〜 {ts(w1)}", ""]
bad = False
same_len = abs(bd - vd) < 0.1
L += [f"## 長さ", "", f"- baseline {bd:.2f}s / variant {vd:.2f}s → {'同じ' if same_len else '**違う(要確認)**'}", ""]
bad |= not same_len
L += ["## 固定地点", "", "| 地点 | PSNR dB | 判定 |", "|---|---|---|"]
for fz in a.frozen:
    name, t = fz.split("=", 1)
    t = float(t)
    p = psnr(frame(a.baseline, t, (480, 270)), frame(a.variant, t, (480, 270)))
    ok = p >= 40
    bad |= not ok
    L.append(f"| {name} {ts(t)} | {p:.1f} | {'変化なし' if ok else '**変化あり**'} |")
if not a.frozen:
    L.append("| (なし) | - | - |")
worst, bads = 99.0, []
t = 0.5
end = min(bd, vd) - 0.5
while t < end:
    if not (w0 - a.margin <= t <= w1 + a.margin):
        p = psnr(frame(a.baseline, t, (480, 270)), frame(a.variant, t, (480, 270)))
        worst = min(worst, p)
        if p < 38:
            bads.append((t, p))
    t += a.step
bad |= bool(bads)
L += ["", "## 変更窓の外", "", f"- {a.step:g}秒おきに比較: 最小PSNR {worst:.1f} dB → " + ("**差あり: " + ", ".join(f"{ts(t)}({p:.0f}dB)" for t, p in bads) + "**" if bads else "変化なし(圧縮ノイズの範囲)")]
inside = []
t = w0
while t <= w1:
    inside.append(psnr(frame(a.baseline, t, (480, 270)), frame(a.variant, t, (480, 270))))
    t += 0.5
changed = min(inside) < 35 if inside else False
bad |= not changed
L += ["", "## 変更窓の中", "", f"- 0.5秒おきの最小PSNR {min(inside):.1f} dB → " + ("実際に変わっている" if changed else "**ほぼ変わっていない(意図した変更が入っていない可能性)**")]
times = [float(x) for x in a.times.split(",")] if a.times else [w0 + (w1 - w0) * i / 7 for i in range(8)]
cols = 4
rows = (len(times) + cols - 1) // cols
W_, H_ = 480, 270
sheet = Image.new("RGB", (W_ * cols, (H_ + 18) * 2 * rows), (20, 20, 20))
for i, tt in enumerate(times):
    for r, (nm, p) in enumerate((("baseline", a.baseline), (a.name, a.variant))):
        im = frame(p, tt, (W_, H_))
        x, y = (i % cols) * W_, ((i // cols) * 2 + r) * (H_ + 18)
        sheet.paste(im, (x, y + 18))
        ImageDraw.Draw(sheet).text((x + 4, y + 3), f"{nm}  {ts(tt)}", fill=(255, 230, 120))
sheet.save(os.path.join(a.out, "compare_baseline_vs_variant.jpg"), quality=84)
L += ["", "## フレーム比較", "", "`compare_baseline_vs_variant.jpg`(上段 baseline / 下段 variant)", "",
      "## 結論", "", "- " + ("固定地点・窓の外は維持され、窓の中だけが変わった" if not bad else "**要確認の項目あり(上の表を参照)**")]
os.remove(os.path.join(a.out, "_f.png")) if os.path.exists(os.path.join(a.out, "_f.png")) else None
open(os.path.join(a.out, "diff_vs_baseline.md"), "w", encoding="utf8").write("\n".join(L) + "\n")
print("\n".join(L))
sys.exit(1 if bad else 0)
