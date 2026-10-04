#!/usr/bin/env python3
"""Protect a good preview as a baseline (project independent).

  python3 mv_baseline.py save NAME --video FULL.mp4 [--proxy SMALL.mp4] [--timeline FILE ...] [--asset FILE ...]
                              [--freeze LABEL=SECONDS ...] [--cmd "build command"] [--note TEXT]
  python3 mv_baseline.py register NAME --dir EXISTING_DIR [--freeze ...] [--timeline ...] [--asset ...] [--note ...]
  python3 mv_baseline.py verify NAME

save     copies the video(s) to output/final/NAME/ (read-only, refuses to overwrite), writes SHA256SUMS and a manifest
register records a baseline that already exists in output/final/NAME/ (does not touch the files)
verify   re-computes the checksums and checks the files are still read-only
Manifest (tracked in Git): work/storyboard/baselines/NAME.json = checksums, duration, frozen points, copies of the timeline files
(work/storyboard/baselines/NAME/), assets with checksums, build command, git commit, tool versions.
"""
import argparse, hashlib, json, os, shutil, stat, subprocess, sys, time

ROOT = os.getcwd()
FINAL = os.path.join(ROOT, "output/final")
MAN = os.path.join(ROOT, "work/storyboard/baselines")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run(*c):
    try:
        return subprocess.check_output(c, text=True, stderr=subprocess.STDOUT).strip()
    except Exception:
        return ""


def duration(p):
    try:
        return float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p))
    except ValueError:
        return None


def manifest(name, files, a):
    os.makedirs(os.path.join(MAN, name), exist_ok=True)
    tl = []
    for t in a.timeline or []:
        dst = os.path.join(MAN, name, os.path.basename(t))
        shutil.copy2(t, dst)
        tl.append(os.path.relpath(dst, ROOT))
    m = dict(name=name, created=time.strftime("%Y-%m-%d %H:%M:%S %Z"), note=a.note or "",
             git_commit=run("git", "rev-parse", "HEAD"), git_dirty=bool(run("git", "status", "--porcelain")),
             build_cmd=a.cmd or "", ffmpeg=run("ffmpeg", "-version").split("\n")[0], python=sys.version.split()[0],
             videos=[dict(path=os.path.relpath(f, ROOT), sha256=sha(f), bytes=os.path.getsize(f), duration=duration(f)) for f in files],
             frozen={k: float(v) for k, v in (x.split("=", 1) for x in (a.freeze or []))},
             timeline_copies=tl,
             assets=[dict(path=p, sha256=sha(p), bytes=os.path.getsize(p)) for p in (a.asset or []) if os.path.exists(p)])
    os.makedirs(MAN, exist_ok=True)
    json.dump(m, open(os.path.join(MAN, f"{name}.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    return m


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="action", required=True)
for c in ("save", "register"):
    s_ = sub.add_parser(c)
    s_.add_argument("name")
    s_.add_argument("--video"); s_.add_argument("--proxy"); s_.add_argument("--dir")
    s_.add_argument("--timeline", nargs="*"); s_.add_argument("--asset", nargs="*"); s_.add_argument("--freeze", nargs="*")
    s_.add_argument("--note"); s_.add_argument("--cmd", help="the build command that produced the video")
v_ = sub.add_parser("verify"); v_.add_argument("name")
a = ap.parse_args()
action = a.action

if action == "save":
    d = os.path.join(FINAL, a.name)
    if os.path.exists(d):
        sys.exit(f"{d} already exists: baselines are never overwritten. Use a new name.")
    os.makedirs(d)
    files = []
    for src, tag in ((a.video, "full"), (a.proxy, "proxy")):
        if src:
            dst = os.path.join(d, f"{a.name}_{tag}{os.path.splitext(src)[1]}")
            shutil.copy2(src, dst)
            files.append(dst)
    with open(os.path.join(d, "SHA256SUMS"), "w") as f:
        for p in files:
            f.write(f"{sha(p)}  {os.path.basename(p)}\n")
    m = manifest(a.name, files, a)
    for p in files + [os.path.join(d, "SHA256SUMS")]:
        os.chmod(p, 0o444)
    os.chmod(d, 0o555)
    print(f"saved baseline {a.name}: {len(files)} video(s), read-only; manifest {os.path.relpath(os.path.join(MAN, a.name + '.json'), ROOT)}")
elif action == "register":
    d = os.path.abspath(a.dir)
    files = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith((".mp4", ".mov", ".mkv")))
    m = manifest(a.name, files, a)
    print(f"registered {a.name}: {len(files)} video(s) (files untouched)")
else:
    m = json.load(open(os.path.join(MAN, f"{a.name}.json"), encoding="utf8"))
    ok = True
    for vd in m["videos"]:
        p = os.path.join(ROOT, vd["path"])
        if not os.path.exists(p):
            print(f"[FAIL] missing {vd['path']}"); ok = False; continue
        same = sha(p) == vd["sha256"]
        ro = not (os.stat(p).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        print(f"[{'PASS' if same else 'FAIL'}] checksum {vd['path']}  [{'read-only' if ro else 'WRITABLE'}]")
        ok &= same
    print("RESULT:", "BASELINE INTACT" if ok else "BASELINE CHANGED OR MISSING")
    sys.exit(0 if ok else 1)
