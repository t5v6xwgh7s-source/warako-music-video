#!/usr/bin/env python3
"""YouTube upload package manager (project independent; run from the repository root).

  yt_package.py init ID --source VERSION [--title T] [--description-file F] [--tags a,b]
  yt_package.py prepare ID        # technical check + metadata/thumbnail validation -> state "prepared"
  yt_package.py validate ID       # re-run the validation only
  yt_package.py card ID           # STUDIO_UPLOAD_CARD.md (copy/paste card for the human upload, rendered from package.json)
  yt_package.py record ID --url URL [--at "2026-10-04 21:30"]   # after the HUMAN published it
  yt_package.py index             # work/youtube/index.json (read by the command centre)
  yt_package.py show ID

One source of truth per work: work/youtube/<ID>/package.json. Everything else (card, index) is generated from it, so nothing is typed twice.
Safety: this tool never talks to YouTube. Visibility is a constant ("private until a human publishes"); there is no publish/delete/update code here.
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys

ROOT = os.getcwd()
YT = os.path.join(ROOT, "work/youtube")
BASEL = os.path.join(ROOT, "work/storyboard/baselines")
MVCHECK = os.path.join(ROOT, ".claude/skills/music-video-maker/scripts/mv_check.py")
SECRET_PAT = re.compile(r"(client_secret|refresh_token|access_token|api[_-]?key|GOCSPX-|ya29\.|1//0)", re.I)
STATES = ["draft", "prepared", "uploaded_private", "published"]


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pdir(i):
    return os.path.join(YT, i)


def load(i):
    p = os.path.join(pdir(i), "package.json")
    if not os.path.exists(p):
        sys.exit(f"no package {i}: {p}")
    return json.load(open(p, encoding="utf8"))


def save(pk):
    json.dump(pk, open(os.path.join(pdir(pk["id"]), "package.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)


def probe(p):
    j = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", p]))
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    return dict(width=v["width"], height=v["height"], codec=v["codec_name"], pix_fmt=v["pix_fmt"], fps=v["r_frame_rate"],
                duration=round(float(j["format"]["duration"]), 2), bytes=int(j["format"]["size"]))


def channel():
    p = os.path.join(YT, "channel.json")
    return json.load(open(p, encoding="utf8")) if os.path.exists(p) else {}


def event(pk, state, note=""):
    pk["status"]["state"] = state
    pk["status"]["history"].append(dict(at=now(), state=state, note=note))


def cmd_init(a):
    d = pdir(a.id)
    if os.path.exists(os.path.join(d, "package.json")):
        sys.exit(f"{a.id} already exists (packages are not overwritten)")
    man = json.load(open(os.path.join(BASEL, f"{a.source}.json"), encoding="utf8"))
    vid = next((v for v in man["videos"] if v["path"].endswith(("_full.mp4", "1080p.mp4"))), man["videos"][0])
    ch = channel()
    title = a.title or ch.get("title_format", "{title}").format(title=a.id)
    desc = open(a.description_file, encoding="utf8").read().strip() if a.description_file else ""
    pk = dict(schema="warako.youtube-package/1", id=a.id,
              work=dict(title=a.work_title or a.id, kind=a.kind),
              source=dict(version=a.source, manifest=os.path.relpath(os.path.join(BASEL, f"{a.source}.json"), ROOT),
                          video=vid["path"], sha256=vid["sha256"], audio=a.audio, extra_tail_seconds=a.extra_tail,
                          qr_image=a.qr, qr_window_note="QR card after the song" if a.extra_tail else ""),
              upload_video=dict(path=vid["path"]),
              thumbnail=dict(selected=None, candidates=[], text=a.thumb_text or ""),
              title=title, description=desc, tags=[t for t in (a.tags or "").split(",") if t],
              language=ch.get("language", "ja"), category_id=ch.get("category_id", "10"),
              visibility="private_until_human_publishes",
              validation={},
              status=dict(state="draft", history=[]),
              youtube=dict(video_id=None, url=None, published_at=None, upload_method=None))
    os.makedirs(os.path.join(d, "thumbnails"), exist_ok=True)
    event(pk, "draft", "created")
    save(pk)
    print(f"created {os.path.relpath(d, ROOT)}/package.json (source {a.source})")


def check_meta(pk):
    blocking, warn = [], []
    t, d = pk["title"], pk["description"]
    if not t.strip():
        blocking.append("title is empty")
    if len(t) > 100:
        blocking.append(f"title is {len(t)} chars (max 100)")
    if re.search(r"[<>]", t + d):
        blocking.append("title/description contains < or > (not allowed by YouTube)")
    if not d.strip():
        blocking.append("description is empty")
    if len(d.encode("utf8")) > 5000:
        blocking.append(f"description is {len(d.encode('utf8'))} bytes (max 5000)")
    if sum(len(x) for x in pk["tags"]) + len(pk["tags"]) > 500:
        blocking.append("tags exceed 500 characters")
    if re.search(r"TODO|XXX|FIXME|仮タイトル", t + d):
        blocking.append("placeholder text left in title/description")
    if SECRET_PAT.search(json.dumps(pk, ensure_ascii=False)):
        blocking.append("package.json contains something that looks like a secret")
    if pk["visibility"] != "private_until_human_publishes":
        blocking.append("visibility must stay 'private_until_human_publishes'")
    if not pk["tags"]:
        warn.append("no tags (optional)")
    return blocking, warn


def check_thumb(pk):
    blocking, warn = [], []
    th = pk["thumbnail"]
    if not th["candidates"]:
        warn.append("no thumbnail candidates yet")
        return blocking, warn
    for c in th["candidates"]:
        p = os.path.join(ROOT, c)
        if not os.path.exists(p):
            blocking.append(f"thumbnail candidate missing: {c}")
            continue
        from PIL import Image
        w, h = Image.open(p).size
        if (w, h) != (1280, 720):
            warn.append(f"{c} is {w}x{h} (1280x720 recommended)")
        if os.path.getsize(p) > 2 * 1024 * 1024:
            blocking.append(f"{c} is over 2 MB")
    if not th["selected"]:
        warn.append("no thumbnail selected yet (human choice)")
    elif th["selected"] not in th["candidates"]:
        blocking.append("selected thumbnail is not in the candidates")
    return blocking, warn


def validate(pk):
    blocking, warn, lines = [], [], []
    v = os.path.join(ROOT, pk["upload_video"]["path"])
    if not os.path.exists(v):
        blocking.append(f"video missing: {pk['upload_video']['path']}")
    else:
        if sha(v) != pk["source"]["sha256"]:
            blocking.append("video checksum differs from the source baseline/candidate manifest")
        info = probe(v)
        pk["upload_video"].update(info, sha256=sha(v))
        if (info["width"], info["height"]) != (1920, 1080):
            warn.append(f"video is {info['width']}x{info['height']} (1080p recommended)")
        cmd = [sys.executable, MVCHECK, v]
        if pk["source"].get("audio"):
            cmd += ["--audio", pk["source"]["audio"], "--extra-tail", str(pk["source"].get("extra_tail_seconds", 0))]
        if pk["source"].get("qr_image") and os.path.exists(pk["source"]["qr_image"]):
            cmd += ["--qr", pk["source"]["qr_image"]]
        r = subprocess.run(cmd, capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if l.startswith("[") or l.startswith("RESULT")]
        if r.returncode != 0:
            blocking.append("technical inspection failed (see validation.technical)")
    b, w = check_meta(pk)
    blocking += b; warn += w
    b, w = check_thumb(pk)
    blocking += b; warn += w
    pk["validation"] = dict(checked_at=now(), technical=lines, blocking=blocking, warnings=warn, ok=not blocking)
    return pk["validation"]


def cmd_prepare(a, only_validate=False):
    pk = load(a.id)
    val = validate(pk)
    if not only_validate and val["ok"] and pk["status"]["state"] == "draft":
        event(pk, "prepared", "validation OK")
    save(pk)
    print(json.dumps(val, ensure_ascii=False, indent=1))
    sys.exit(0 if val["ok"] else 1)


def cmd_card(a):
    pk = load(a.id)
    v = pk["upload_video"]
    sel = pk["thumbnail"]["selected"] or "(未選択: 候補から選ぶ) " + ", ".join(pk["thumbnail"]["candidates"])
    L = [f"# YouTube アップロードカード — {pk['work']['title']}", "",
         "このファイルは `package.json` から自動生成(手で編集しない)。", "",
         "## 1. 動画ファイル", f"- `{v['path']}`  ({v.get('width')}x{v.get('height')}, {v.get('duration')}s, {v.get('bytes', 0)/1048576:.1f} MiB)",
         f"- sha256: `{v.get('sha256','')[:16]}…`", "", "## 2. タイトル", "```", pk["title"], "```", "",
         "## 3. 概要欄(そのままコピー)", "```", pk["description"], "```", "",
         "## 4. タグ", ", ".join(pk["tags"]) or "(なし)", "", "## 5. サムネイル", f"- {sel}", "",
         "## 6. 公開の手順(人間が行う)",
         "1. YouTube Studio → 作成 → 動画をアップロード → 上のファイル",
         "2. タイトル・概要欄を貼る、サムネイルをアップロード",
         "3. 「視聴者」(子供向けかどうか)を選ぶ ← 人間が申告する項目",
         "4. まず**非公開**で保存し、Studio上で再生して最後まで確認する",
         "5. 問題なければ**公開**にする(この操作は人間だけが行う)",
         "6. 公開できたら、動画のURLをClaudeへ渡す(記録は `yt_package.py record`)", "",
         "## 検査結果", f"- {'OK' if pk['validation'].get('ok') else '要確認'} / 確認日時 {pk['validation'].get('checked_at','-')}"]
    for w in pk["validation"].get("warnings", []):
        L.append(f"- 注意: {w}")
    p = os.path.join(pdir(a.id), "STUDIO_UPLOAD_CARD.md")
    open(p, "w", encoding="utf8").write("\n".join(L) + "\n")
    print("wrote", os.path.relpath(p, ROOT))


def parse_url(u):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/live/)([A-Za-z0-9_-]{11})", u)
    if not m:
        sys.exit(f"not a recognisable YouTube video URL: {u}")
    return m.group(1)


def cmd_record(a):
    pk = load(a.id)
    vid = parse_url(a.url)
    at = a.at or now()
    pk["youtube"].update(video_id=vid, url=f"https://www.youtube.com/watch?v={vid}", published_at=at,
                         upload_method=a.method)
    event(pk, "published", f"recorded by tool; published_at={at}" + (" (approximate: recorded time)" if not a.at else ""))
    save(pk)
    cmd_index(a)
    print("recorded", pk["youtube"]["url"])


def cmd_index(a):
    items = []
    for d in sorted(os.listdir(YT)) if os.path.isdir(YT) else []:
        p = os.path.join(YT, d, "package.json")
        if os.path.exists(p):
            k = json.load(open(p, encoding="utf8"))
            items.append(dict(id=k["id"], work=k["work"], title=k["title"], source_version=k["source"]["version"],
                              state=k["status"]["state"], url=k["youtube"]["url"], video_id=k["youtube"]["video_id"],
                              published_at=k["youtube"]["published_at"], package=os.path.relpath(p, ROOT)))
    json.dump(dict(schema="warako.youtube-index/1", generated=now(), items=items), open(os.path.join(YT, "index.json"), "w", encoding="utf8"),
              ensure_ascii=False, indent=1)


def cmd_show(a):
    print(json.dumps(load(a.id), ensure_ascii=False, indent=1))


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="action", required=True)
s = sub.add_parser("init"); s.add_argument("id"); s.add_argument("--source", required=True, help="baseline/candidate name registered by mv_baseline.py")
s.add_argument("--title"); s.add_argument("--work-title"); s.add_argument("--kind", default="music-video"); s.add_argument("--description-file")
s.add_argument("--tags"); s.add_argument("--audio"); s.add_argument("--extra-tail", type=float, default=0.0); s.add_argument("--qr"); s.add_argument("--thumb-text")
for n in ("prepare", "validate", "card", "show"):
    sub.add_parser(n).add_argument("id")
s = sub.add_parser("record"); s.add_argument("id"); s.add_argument("--url", required=True); s.add_argument("--at"); s.add_argument("--method", default="manual-studio")
sub.add_parser("index")
a = ap.parse_args()
{"init": cmd_init, "prepare": cmd_prepare, "validate": lambda x: cmd_prepare(x, True), "card": cmd_card, "record": cmd_record,
 "index": cmd_index, "show": cmd_show}[a.action](a)
