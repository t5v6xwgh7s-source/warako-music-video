#!/usr/bin/env python3
"""Verify that lyrics_timing.tsv follows the supplied lyric order (from a given time on) and cross-check against the audio.

Usage: python3 scripts/check_lyric_order.py [from_seconds=93]
Order check : the TSV rows with start >= from_seconds must equal the lyric file's lines in order (no inserted/repeated lines),
              starts strictly increasing, no overlaps, 1 line per row.
Audio check : each line must not sit inside a detected drum-fill / break (bass drops >5 dB for >=1 bar) and should have
              vocal-band onsets inside its window (onset density reported). This is a plausibility check, not forced alignment.
"""
import os, subprocess, sys, tempfile, wave
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = float(sys.argv[1]) if len(sys.argv) > 1 else 93.0
lyr = [l.strip() for l in open(os.path.join(ROOT, "assets/lyrics/虹の向こうで会いたい_歌詞.txt"), encoding="utf8") if l.strip()]
rows = []
for ln in open(os.path.join(ROOT, "work/storyboard/lyrics_timing.tsv"), encoding="utf8"):
    if ln.startswith("#") or not ln.strip():
        continue
    s, e, cap, conf, text = ln.rstrip("\n").split("\t", 4)
    rows.append((float(s), float(e), cap, text))
rows.sort()
tail = [r for r in rows if r[0] >= T0 - 15]            # include a little context to find where the 1:33 block begins
# the expected block = lyric lines that follow the last chorus-2 line ("もう一度" #2 -> index 30)
exp = lyr[31:]
got = [r for r in rows if r[0] >= 93.0]
ok = True
print(f"== order check (rows from {T0:.0f}s) ==")
texts = [r[3] for r in got]
if texts != exp:
    ok = False
    print("FAIL: sequence differs from the lyric file")
    for i in range(max(len(texts), len(exp))):
        a = exp[i] if i < len(exp) else "-"
        b = texts[i] if i < len(texts) else "-"
        print(f"  {i+1:2d} expected {a:16s} got {b}")
else:
    print(f"PASS: {len(exp)} lines in the exact supplied order")
for a, b in zip(got, got[1:]):
    if b[0] <= a[0] or a[1] > b[0] - 0.05:
        ok = False
        print(f"FAIL: overlap/non-increasing {a[3]} -> {b[3]}")
for r in got:
    if r[1] <= r[0]:
        ok = False
        print("FAIL: non-positive duration", r)

# --- audio plausibility ---
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(ROOT, "assets/audio/song.m4a"), "-ac", "1", "-ar", "22050", p], check=True)
    w = wave.open(p); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
n_fft, hop = 2048, sr // 20
fr = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop]
S = np.abs(np.fft.rfft(fr * np.hanning(n_fft), axis=1)); f = np.fft.rfftfreq(n_fft, 1 / sr)
low = 10 * np.log10((S[:, f < 250] ** 2).sum(1) + 1e-9)
vb = (f > 350) & (f < 2800)
flux = np.maximum(np.diff(np.log1p(60 * S[:, vb]), axis=0), 0).sum(1)
fps = 20
t = np.arange(len(low)) / fps
sm = np.convolve(low, np.ones(20) / 20, "same")
med = np.array([np.median(sm[max(0, i - 160):i + 160]) for i in range(len(sm))])
dip = sm < med - 5
breaks, i = [], 0
while i < len(dip):
    if dip[i]:
        j = i
        while j < len(dip) and dip[j]:
            j += 1
        if (j - i) / fps >= 1.0:
            breaks.append((t[i], t[j - 1]))
        i = j
    else:
        i += 1
print("\n== audio check ==")
print("bass-drop breaks (>=1s):", ", ".join(f"{a:.1f}-{b:.1f}" for a, b in breaks if a > 80))
thr = np.percentile(flux, 75)
pk = np.array([t[k + 1] for k in range(2, len(flux) - 2) if flux[k] >= thr and flux[k] == flux[k - 2:k + 3].max()])
print(f"{'line':20s} {'window':>15s} {'in-break':>8s} {'onsets/s':>8s}  {'rms(dB, window)':>16s}")
base_on = len(pk) / t[-1]
for r in got:
    a, b = r[0], r[1]
    inb = sum(max(0, min(b, y) - max(a, x_)) for x_, y in breaks) / (b - a)
    dens = ((pk >= a) & (pk <= b)).sum() / (b - a)
    seg = x[int(a * sr):int(b * sr)]
    level = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9)
    flag = ""
    if inb > 0.3:
        flag = "IN-BREAK"; ok = False
    elif dens < 0.5 * base_on:
        flag = "few-onsets"
    print(f"{r[3]:20s} {a:7.2f}-{b:7.2f} {inb:8.2f} {dens:8.2f}  {level:16.1f} {flag}")
print(f"(average onset density over the whole song: {base_on:.2f}/s)")
print("\nRESULT:", "OK" if ok else "PROBLEMS FOUND")
sys.exit(0 if ok else 1)
