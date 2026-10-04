#!/usr/bin/env python3
"""Generic technical inspection of a rendered music video (project independent).

  python3 mv_check.py VIDEO [--audio SRC_AUDIO] [--extra-tail SEC] [--size 1920x1080]
                            [--edge-fade SEC] [--qr IMAGE --qr-window START END] [--qr-min SEC]

Checks: full decode, size, codec/pix_fmt, audio stream, video/audio duration (= source audio + extra tail, e.g. an end card),
black frames in the middle (head/tail fades are ignored), audio present at the end of the song, and optionally that a QR image
decodes to the same payload in the rendered frames for at least --qr-min seconds. Prints PASS/WARN/FAIL; exit 1 on FAIL.
"""
import argparse, json, re, subprocess, sys, tempfile, os

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--audio", help="source audio: the video must be this long (+ extra tail)")
ap.add_argument("--extra-tail", type=float, default=0.0, help="seconds the video runs after the audio ends (silent end card, QR card ...)")
ap.add_argument("--size", default="1920x1080")
ap.add_argument("--edge-fade", type=float, default=1.5, help="black at the very start / end of the song is allowed up to this many seconds")
ap.add_argument("--qr", help="QR image whose payload must be readable in the video")
ap.add_argument("--qr-window", nargs=2, type=float, metavar=("START", "END"))
ap.add_argument("--qr-min", type=float, default=10.0)
a = ap.parse_args()
bad = 0


def say(level, msg):
    global bad
    bad += level == "FAIL"
    print(f"[{level}] {msg}")


def probe(p):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p]))


p = probe(a.video)
v = next(s for s in p["streams"] if s["codec_type"] == "video")
au = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
dec = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-f", "null", "-"], capture_output=True, text=True)
say("PASS" if not dec.stderr.strip() else "FAIL", "full decode without errors" + (f": {dec.stderr[:160]}" if dec.stderr.strip() else ""))
w, h = map(int, a.size.lower().split("x"))
say("PASS" if (v["width"], v["height"]) == (w, h) else "FAIL", f"size {v['width']}x{v['height']} (expected {w}x{h})")
say("PASS" if v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p" else "WARN", f"{v['codec_name']} {v['pix_fmt']} {v['r_frame_rate']}")
say("PASS" if au else "FAIL", f"audio stream {au['codec_name'] if au else 'missing'}")
vd = float(v.get("duration") or p["format"]["duration"])
ad = float(au["duration"]) if au else 0.0
src = None
if a.audio:
    src = float(probe(a.audio)["format"]["duration"])
    exp = src + a.extra_tail
    say("PASS" if abs(vd - exp) < 0.1 and abs(ad - exp) < 0.2 else "FAIL",
        f"durations video {vd:.2f}s audio {ad:.2f}s expected {exp:.2f}s (song {src:.2f}s + tail {a.extra_tail:.1f}s)")
else:
    say("PASS" if abs(vd - ad) < 0.2 else "WARN", f"video {vd:.2f}s / audio {ad:.2f}s")
end = src if src else vd
sd = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(max(end - 3, 0)), "-t", "2.9", "-i", a.video, "-af", "silencedetect=n=-60dB:d=2.5", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
say("WARN" if "silence_start" in sd else "PASS", "audio present at the end of the song" if "silence_start" not in sd else "last 3s of the song are silent (ok only if it fades out)")
bl = subprocess.run(["ffmpeg", "-v", "info", "-i", a.video, "-vf", "blackdetect=d=0.3:pix_th=0.06", "-an", "-f", "null", "-"], capture_output=True, text=True).stderr
mid = []
for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", bl):
    s, e = float(m.group(1)), float(m.group(2))
    if s > a.edge_fade and e < end - a.edge_fade and not (a.extra_tail and s >= end - 0.5):
        mid.append((round(s, 2), round(e, 2)))
say("PASS" if not mid else "FAIL", "no black-screen accidents" if not mid else f"black segments mid-video: {mid}")
if a.qr:
    import cv2
    det = cv2.QRCodeDetector()
    want = det.detectAndDecode(cv2.imread(a.qr))[0]
    if not want:
        say("WARN", "QR image itself does not decode with OpenCV (cannot verify)")
    else:
        t0, t1 = a.qr_window if a.qr_window else (end + 0.8, vd - 0.2)
        hits = n = 0
        first = last = None
        t = t0
        tmp = os.path.join(tempfile.gettempdir(), "_mv_qr.png")
        while t < t1:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1", tmp])
            got = det.detectAndDecode(cv2.imread(tmp))[0]
            n += 1
            if got == want:
                hits += 1
                first = t if first is None else first
                last = t
            t += 1.0
        span = (last - first + 1.0) if hits else 0.0
        say("PASS" if span >= a.qr_min else "FAIL", f"QR payload {want!r} readable in {hits}/{n} sampled seconds; span {span:.0f}s (needs >= {a.qr_min:.0f}s)")
print("RESULT:", "OK" if not bad else f"{bad} FAIL")
sys.exit(1 if bad else 0)
