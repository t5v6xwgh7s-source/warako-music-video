#!/usr/bin/env python3
"""Automatic inspection of the rendered MV (STEP 10). Prints PASS/WARN/FAIL lines.

Usage: python3 scripts/check_mv.py [output/preview/mv_preview.mp4]
"""
import glob, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mp4 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "output/preview/mv_preview.mp4")
audio = os.path.join(ROOT, "assets/audio/song.m4a")
bad = 0


def say(level, msg):
    global bad
    bad += level == "FAIL"
    print(f"[{level}] {msg}")


def probe(path):
    return json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]))


p = probe(mp4)
v = next(s for s in p["streams"] if s["codec_type"] == "video")
a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
src = float(probe(audio)["format"]["duration"])

# playable to the end: decode everything, errors surface on stderr
dec = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "null", "-"], capture_output=True, text=True)
say("PASS" if not dec.stderr.strip() else "FAIL", "full decode without errors" + (f": {dec.stderr[:200]}" if dec.stderr.strip() else ""))

say("PASS" if (v["width"], v["height"]) == (1920, 1080) else "FAIL", f"size {v['width']}x{v['height']}")
say("PASS" if v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p" else "FAIL", f"{v['codec_name']} {v['pix_fmt']} {v['r_frame_rate']}")
say("PASS" if a and a["codec_name"] == "aac" else "FAIL", f"audio {a and a['codec_name']}")
vd, ad = float(v.get("duration") or p["format"]["duration"]), float(a["duration"]) if a else 0
say("PASS" if abs(vd - src) < 0.1 and abs(ad - src) < 0.1 else "FAIL", f"durations video {vd:.2f}s audio {ad:.2f}s source {src:.2f}s")

# audio present to the end (last 3s not silent)
sd = subprocess.run(["ffmpeg", "-v", "info", "-ss", str(max(src - 3, 0)), "-i", mp4, "-af", "silencedetect=n=-60dB:d=2.5", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
say("WARN" if "silence_start" in sd else "PASS", "audio present in last 3s" if "silence_start" not in sd else "last 3s silent (fine only if the song fades out)")

# black frames (excluding the intentional fade-in/out at both ends)
bl = subprocess.run(["ffmpeg", "-v", "info", "-i", mp4, "-vf", "blackdetect=d=0.3:pix_th=0.06", "-an", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
mid = []
for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", bl):
    s, e = float(m.group(1)), float(m.group(2))
    if s > 1.5 and e < src - 1.5:
        mid.append((s, e))
say("PASS" if not mid else "FAIL", "no black-screen accidents" if not mid else f"black segments mid-video: {mid}")

# QR
qrs = sorted(glob.glob(os.path.join(ROOT, "assets/qr/*.png")))
if not qrs:
    say("WARN", "no QR in assets/qr/ -> QR checks skipped (end card rendered without QR)")
else:
    import cv2
    det = cv2.QRCodeDetector()
    want, _, _ = det.detectAndDecode(cv2.imread(qrs[0]))
    ok_t, hits = [], 0
    for t in [src - 10 + i for i in range(0, 9)]:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", mp4, "-frames:v", "1", "/tmp/_qrframe.png"])
        got, _, _ = det.detectAndDecode(cv2.imread("/tmp/_qrframe.png"))
        if got and got == want:
            hits += 1
            ok_t.append(t)
    say("PASS" if hits >= 8 else "FAIL", f"QR decodes to the original payload in {hits}/9 sampled seconds of the end card")

print("RESULT:", "OK" if not bad else f"{bad} FAIL")
sys.exit(1 if bad else 0)
