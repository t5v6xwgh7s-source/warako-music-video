#!/usr/bin/env python3
"""Estimate lyric timing from the audio structure and write work/storyboard/lyrics_timing.tsv.

No speech-recognition model is reachable from this environment, so this is an *estimate*:
  1. section boundaries come from the energy / bass-drop analysis of the song (86 BPM, bar = 2.79s, first beat 0.49s),
  2. each section's lines are spread over its sung window in proportion to their mora count,
  3. each line start is snapped to the nearest vocal-band onset (+-0.3s) when one is clear.
The TSV is the source of truth for build_mv.py: listen, then edit the start/end columns by hand.

Usage: python3 scripts/lyric_sync.py
"""
import os, subprocess, wave, tempfile
import numpy as np
import pykakasi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "assets/audio/song.m4a")
LYRICS = os.path.join(ROOT, "assets/lyrics/虹の向こうで会いたい_歌詞.txt")
OUT = os.path.join(ROOT, "work/storyboard/lyrics_timing.tsv")

# name, confidence, window start, window end (seconds), caption groups (1-2 lines each) given as line-index lists
# Line indices refer to LYRICS lines (0-based).
V1 = [[0, 1], [2, 3], [4, 5], [6]]
CH = [[7, 8], [9, 10], [11], [12, 13], [14, 15]]           # chorus 1 (incl. two "虹の向こうで/もう一度" tags)
V2 = [[16, 17], [18, 19], [20, 21], [22, 23]]
C2 = [[24, 25], [26, 27], [28], [29, 30]]
BR1 = [[31, 32], [33, 34]]
BR2 = [[35, 36], [37], [38]]
CH_REPEAT = CH                                              # last chorus: assumed repeat of chorus 1 (same 8-bar length)
SECTIONS = [
    # name,            conf,   t0,     t1,     groups,     line-index offset
    ("verse1",         "mid",  12.25,  32.90,  V1,         0),
    ("chorus1",        "mid",  34.20,  55.60,  CH,         0),
    ("verse2",         "mid",  57.00,  75.20,  V2,         0),
    ("chorus2",        "mid",  76.10,  91.60,  C2,         0),
    # NOTE: no "last chorus = repeat of chorus 1" assumption. After chorus 2 the supplied lyrics only continue with the
    # bridge (雨上がり...), the final lines (会えたなら...) and the outro, in exactly that order -> see SLOTS below.
]
# Slow two-bar phrases (one line per 2-bar slot, 8 bars per 4-line block). Block 1 = bars 38-45 (quiet bridge),
# block 2 = bars 53-59 (the loud last section, before the drum fill at 165.1). 92.6-103.7, 126-145.6 are left without
# lyrics (instrumental / break); this is an inference from the 8-bar symmetry and the energy map, not a measurement.
SLOTS = [
    # name,       conf,  line indices,       slot start, slot len, lead-in, hard end
    ("bridge",    "low", [31, 32, 33, 34],   106.70,     4.85,     0.10,    126.0),   # bass is out 104.2-106.7: voice enters with the bass
    ("final",     "low", [35, 36, 37, 38],   147.40,     4.45,     0.10,    165.2),   # drum fill 143.0-147.4
]
# Outro is slow and sparse (each phrase sits on its own bar); placed by hand from the bar grid.
OUTRO = [  # (line index, start, end, caption)
    (-4, 168.40, 170.60, "outro1"),   # 虹の向こうで
    (-3, 172.20, 173.30, "outro1"),   # また (enters as the bass returns at ~172.4)
    (-2, 173.90, 177.40, "outro2"),   # またねじゃなくて
    (-1, 179.10, 182.90, "outro2"),   # おかえりって
]
BREATH = 0.30      # silence between lines inside a group
GROUP_BREATH = 0.60


def moras(text, kks=pykakasi.kakasi()):
    hira = "".join(i["hira"] for i in kks.convert(text))
    return sum(1 for c in hira if c not in "ゃゅょぁぃぅぇぉ ")


def onset_peaks():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "a.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", AUDIO, "-ac", "1", "-ar", "22050", p], check=True)
        w = wave.open(p)
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
        sr = w.getframerate()
    n_fft, hop = 1024, sr // 50
    fr = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop]
    S = np.abs(np.fft.rfft(fr * np.hanning(n_fft), axis=1))
    f = np.fft.rfftfreq(n_fft, 1 / sr)
    band = (f > 350) & (f < 2800)
    flux = np.maximum(np.diff(np.log1p(60 * S[:, band]), axis=0), 0).sum(1)
    t = (np.arange(len(flux)) + 1) * hop / sr
    thr = np.percentile(flux, 75)
    peaks = [t[i] for i in range(2, len(flux) - 2) if flux[i] >= thr and flux[i] == flux[i - 2:i + 3].max()]
    return np.array(peaks)


def main():
    import sys
    if os.path.exists(OUT) and "--force" not in sys.argv:
        head = open(OUT, encoding="utf8").read(2000)
        if "# LOCK" in head:
            sys.exit("lyrics_timing.tsv is LOCKED (baseline v3b: R6 / R7 / END are frozen until a human listening check). "
                     "Edit the TSV by hand, or run with --force to regenerate.")
    lines = [l.strip() for l in open(LYRICS, encoding="utf8") if l.strip()]
    assert len(lines) == 43, len(lines)
    peaks = onset_peaks()
    rows = []   # dict(start,end,cap,text,conf)
    cap_no = 0
    for name, conf, t0, t1, groups, _ in SECTIONS:
        flat = [i for g in groups for i in g]
        # gaps: BREATH between lines in a group, GROUP_BREATH after a group; none after the last line
        gaps = []
        for g in groups:
            gaps += [BREATH] * (len(g) - 1) + [GROUP_BREATH]
        gaps = gaps[:-1]
        avail = (t1 - t0) - sum(gaps)
        w = np.array([moras(lines[i]) + 1.0 for i in flat])
        dur = avail * w / w.sum()
        starts, t = [], t0
        for k, i in enumerate(flat):
            starts.append(t)
            t += dur[k] + (gaps[k] if k < len(gaps) else 0)
        ends = [s + d for s, d in zip(starts, dur)]
        # snap starts to vocal onsets
        for k in range(1 if name != "verse1" else 0, len(starts)):
            near = peaks[np.abs(peaks - starts[k]) <= 0.30]
            if len(near):
                s_new = near[np.abs(near - starts[k]).argmin()]
                lo = ends[k - 1] + 0.15 if k else t0 - 0.5
                if s_new > lo:
                    shift = s_new - starts[k]
                    starts[k] += shift
                    ends[k] += shift
        k = 0
        for g in groups:
            cap_no += 1
            for i in g:
                rows.append(dict(start=starts[k], end=ends[k], cap=f"{name}_{cap_no}", text=lines[i], conf=conf, sec=name))
                k += 1
    for name, conf, idxs, s0, slot, lead, hard_end in SLOTS:
        for k, i in enumerate(idxs):
            cap_no += 1
            start = s0 + k * slot + lead
            near = peaks[np.abs(peaks - start) <= 0.30]
            if len(near):
                start = float(near[np.abs(near - start).argmin()])
            end = min(start + min(slot - 0.85, 0.40 * moras(lines[i]) + 0.6), hard_end)
            rows.append(dict(start=start, end=end, cap=f"{name}_{cap_no}", text=lines[i], conf=conf, sec=name))
    rows.sort(key=lambda r: r["start"])
    for idx, s, e, cap in OUTRO:
        rows.append(dict(start=s, end=e, cap=cap, text=lines[idx], conf="low", sec="outro"))
    with open(OUT, "w", encoding="utf8") as fh:
        fh.write("# start\tend\tcaption\tconfidence\ttext   (edit start/end by ear; build_mv.py reads this file)\n")
        for r in rows:
            fh.write(f"{r['start']:.2f}\t{r['end']:.2f}\t{r['cap']}\t{r['conf']}\t{r['text']}\n")
    for r in rows:
        print(f"{int(r['start']//60)}:{r['start']%60:05.2f}-{r['end']:6.2f} {r['cap']:14s} {r['conf']:3s} {r['text']}")


if __name__ == "__main__":
    main()
