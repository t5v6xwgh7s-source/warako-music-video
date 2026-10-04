#!/usr/bin/env python3
"""Compare a variant video with the frozen baseline and write work/storyboard/variants/<name>/diff_vs_baseline.md (+ a frame sheet).

  python3 scripts/variant_diff.py v3c_r3b [--from 47.5 --to 56.5] [--times 51.8,52.1,...]

Shows: which cut rows changed, that the frozen points (R6/R7/END) are intact (cut table + sampled frames), and that the video is
unchanged outside the edited window (frame PSNR vs the baseline every 2 s; the baseline mp4 is never modified).
"""
import argparse, importlib.util, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("variant")
ap.add_argument("--from", dest="t0", type=float, default=47.5)
ap.add_argument("--to", dest="t1", type=float, default=56.5)
ap.add_argument("--times", default="51.5,52.0,52.32,52.8,53.4,53.9,54.34,55.2")
a = ap.parse_args()
os.environ["MV_VARIANT"] = a.variant
spec = importlib.util.spec_from_file_location("build_mv", os.path.join(ROOT, "scripts/build_mv.py"))
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)
BASE = os.path.join(ROOT, "output/final/baseline_v3b/mv_v3b_baseline_1080p.mp4")
VAR = os.path.join(ROOT, f"output/preview/mv_{a.variant}.mp4")
out_dir = bm.variant_dir()
os.makedirs(out_dir, exist_ok=True)


def frame(path, t, size=None):
    tmp = "/tmp/_vd.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", tmp], check=True)
    im = Image.open(tmp).convert("RGB")
    return im.resize(size) if size else im


def psnr(x, y):
    d = ((np.asarray(x, float) - np.asarray(y, float)) ** 2).mean()
    return 99.0 if d == 0 else 10 * np.log10(255 ** 2 / d)


# 1) rows changed (against the baseline CUTS list)
os.environ["MV_VARIANT"] = ""
base_cuts = bm.resolve_cuts(bm.audio_duration()) if False else None
import copy
bm.VARIANT = ""
base_rows = bm.resolve_cuts(184.16)
bm.VARIANT = a.variant
var_rows = bm.resolve_cuts(184.16)
sig = lambda c: (c["key"], c["page"], round(c["t0"], 3), round(c["t1"], 3), c["fade"], c.get("tag"), tuple(c["cf"]), tuple(c["ct"]))
bs, vs = {sig(c): c for c in base_rows}, {sig(c): c for c in var_rows}
removed = [bs[k] for k in bs if k not in vs]
added = [vs[k] for k in vs if k not in bs]
lab = lambda c: f"{c['key']}{'['+c['page']+']' if c['page'] else ''}"
L = [f"# {a.variant} vs baseline_v3b", "",
     f"baseline: `output/final/baseline_v3b/mv_v3b_baseline_1080p.mp4`(変更しない) / 比較版: `output/preview/mv_{a.variant}.mp4`", "",
     "## 変更したカット行(これだけ)", "", "| 区分 | cut | start | end | transition | tag | 内容 |", "|---|---|---|---|---|---|---|"]
for c in removed:
    L.append(f"| baseline | {lab(c)} | {bm.ts(c['t0'])} | {bm.ts(c['t1'])} | dissolve {c['fade']:.1f}s | {c.get('tag') or '-'} | {c['theme']} |")
for c in added:
    L.append(f"| **変更後** | {lab(c)} | {bm.ts(c['t0'])} | {bm.ts(c['t1'])} | dissolve {c['fade']:.1f}s | {c.get('tag') or '-'} | {c['theme']} |")
same_total = abs(base_rows[-1]["t1"] - var_rows[-1]["t1"]) < 1e-6
L += ["", f"全体の長さ: {'変わらない' if same_total else '変わった(要確認)'}。差が出る時間帯は {min(c['t0'] for c in removed+added):.1f}〜{max(c['t1'] for c in removed+added):.1f} 秒のみ。"]

# 2) frozen points
fz = [("R6 2:27.54", 147.54), ("R7 2:48.40", 168.40), ("END 2:59.00", 179.00), ("END またねじゃなくて 2:53.9", 173.9)]
L += ["", "## 固定地点(R6 / R7 / END)の確認", "", "| 地点 | baselineとのフレーム一致 (PSNR dB) | 判定 |", "|---|---|---|"]
ok = True
for name, t in fz:
    p = psnr(frame(BASE, t), frame(VAR, t))
    good = p >= 40
    ok &= good
    L.append(f"| {name} | {p:.1f} | {'変化なし' if good else '**変化あり(要確認)**'} |")

# 3) unchanged outside the window
bad = []
t = 1.0
worst = 99
while t < 184.0:
    if not (a.t0 <= t <= a.t1):
        p = psnr(frame(BASE, t, (480, 270)), frame(VAR, t, (480, 270)))
        worst = min(worst, p)
        if p < 38:
            bad.append((t, p))
    t += 2.0
L += ["", "## 変更箇所の外が変わっていないこと", "",
      f"2秒おき(編集窓 {a.t0:.1f}〜{a.t1:.1f}秒を除く)のフレームをbaselineと比較: 最小PSNR {worst:.1f} dB。" +
      (" 差が大きい時刻: " + ", ".join(f"{bm.ts(t)}({p:.0f}dB)" for t, p in bad) if bad else " すべて一致(圧縮ノイズの範囲)。")]
# 4) sheet
times = [float(x) for x in a.times.split(",")]
W_, H_ = 480, 270
sheet = Image.new("RGB", (W_ * 4, (H_ + 18) * 4), (20, 20, 20))
for i, tt in enumerate(times):
    for r, (nm, path) in enumerate((("baseline", BASE), (a.variant, VAR))):
        im = frame(path, tt, (W_, H_))
        x, y = (i % 4) * W_, ((i // 4) * 2 + r) * (H_ + 18)
        sheet.paste(im, (x, y + 18))
        ImageDraw.Draw(sheet).text((x + 4, y + 3), f"{nm}  {int(tt//60)}:{tt%60:05.2f}", fill=(255, 230, 120))
sheet.save(os.path.join(out_dir, "compare_baseline_vs_variant.jpg"), quality=84)
L += ["", "## フレーム比較", "", "`compare_baseline_vs_variant.jpg`(上段 baseline / 下段 変更版。0:51.5〜0:55.2)", "",
      f"## 結論(機械的な確認)", "", f"- 固定地点: {'変化なし' if ok else '要確認'}", f"- 変更窓の外: {'変化なし' if not bad else '要確認'}"]
open(os.path.join(out_dir, "diff_vs_baseline.md"), "w", encoding="utf8").write("\n".join(L) + "\n")
print("\n".join(L))
sys.exit(0 if ok and not bad else 1)
