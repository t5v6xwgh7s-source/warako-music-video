#!/usr/bin/env python3
"""Compare the current timeline / lyric timing with the frozen baseline (work/storyboard/baseline_v3b.json).

  python3 scripts/check_baseline.py            # exit 1 if a FROZEN checkpoint (R6 / R7 / END) differs
  python3 scripts/check_baseline.py --snapshot # (re)write the baseline JSON from the current state (only deliberate, after a human decision)

Frozen = R6 (虹の向こうで会えたなら), R7 (虹の向こうで／また), END (またねじゃなくて／おかえりって → 親分) :
their cuts and their sung-line timings. They change only after a human listening check, never from automated analysis.
Everything else (other cuts, rainbow cues R1-R5, QR card) is reported as "changed" so that a change is never silent.
"""
import hashlib, importlib.util, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_mv", os.path.join(ROOT, "scripts/build_mv.py"))
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)
BASE = os.path.join(ROOT, "work/storyboard/baseline_v3b.json")
FROZEN_TAGS = {"R6", "R6b", "R7"}
FROZEN_KEYS = {"p084_085_empty_seat", "END_CARD"}
FROZEN_LINES = [("虹の向こうで会えたなら", 0), ("虹の向こうで", 3), ("また", 0), ("またねじゃなくて", 0), ("おかえりって", 0)]


def current():
    dur = bm.audio_duration()
    cuts = [dict(key=c["key"], page=c["page"], t0=round(c["t0"], 3), t1=round(c["t1"], 3), fade=c["fade"], tag=c.get("tag"),
                 cf=list(c["cf"]), ct=list(c["ct"]), sat=c.get("sat"), bloom=c.get("bloom", False)) for c in bm.resolve_cuts(dur)]
    rows = bm.load_lyrics()
    lines = []
    for text, n in FROZEN_LINES:
        r = [x for x in rows if x["text"] == text][n]
        lines.append(dict(text=text, nth=n, start=r["start"], end=r["end"]))
    allrows = [(r["start"], r["end"], r["text"]) for r in rows]
    return dict(duration=round(dur, 3), qr_mode=bm.QR_MODE, qr_tail=bm.QR_TAIL, cuts=cuts, frozen_lines=lines,
                lyrics_sha256=hashlib.sha256(json.dumps(allrows, ensure_ascii=False).encode()).hexdigest(),
                end_card_image=os.path.basename(bm.end_card_image_key()[1]))


def is_frozen(c):
    return c["tag"] in FROZEN_TAGS or c["key"] in FROZEN_KEYS


if "--snapshot" in sys.argv:
    cur = current()
    json.dump(cur, open(BASE, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    print("baseline written:", BASE)
    sys.exit(0)

base = json.load(open(BASE, encoding="utf8"))
cur = current()
bad = 0
def say(level, msg):
    global bad
    bad += level == "FROZEN-CHANGED"
    print(f"[{level}] {msg}")

bf = [c for c in base["cuts"] if is_frozen(c)]
cf = [c for c in cur["cuts"] if is_frozen(c)]
if bf == cf:
    say("OK", f"frozen cuts unchanged ({len(bf)} cuts: R6/R6b/R7/END)")
else:
    say("FROZEN-CHANGED", "frozen cuts differ from the baseline")
    for a, b in zip(bf, cf):
        if a != b:
            print("   baseline:", a["key"], a["t0"], a["t1"], " now:", b["key"], b["t0"], b["t1"])
if base["frozen_lines"] == cur["frozen_lines"]:
    say("OK", "frozen sung-line timings unchanged (R6 / R7 / また / またねじゃなくて / おかえりって)")
else:
    say("FROZEN-CHANGED", "frozen sung-line timings differ")
    for a, b in zip(base["frozen_lines"], cur["frozen_lines"]):
        if a != b:
            print(f"   {a['text']}: baseline {a['start']}-{a['end']}  now {b['start']}-{b['end']}")
nf_b = [c for c in base["cuts"] if not is_frozen(c)]
nf_c = [c for c in cur["cuts"] if not is_frozen(c)]
def sig(c):
    return json.dumps(c, sort_keys=True, ensure_ascii=False)
sb, sc = {sig(c): c for c in nf_b}, {sig(c): c for c in nf_c}
removed = [sb[k] for k in sb if k not in sc]
added = [sc[k] for k in sc if k not in sb]
if not removed and not added:
    say("OK", "all other cuts (incl. rainbow cues R1-R5) unchanged")
else:
    say("CHANGED", f"non-frozen cuts differ from the baseline (allowed only as a deliberate edit): {len(removed)} baseline rows replaced by {len(added)} rows")
    for c in removed:
        print(f"   - baseline {c['key']}{'['+c['page']+']' if c['page'] else ''} {c['t0']}-{c['t1']} fade {c['fade']} tag {c['tag']}")
    for c in added:
        print(f"   + now      {c['key']}{'['+c['page']+']' if c['page'] else ''} {c['t0']}-{c['t1']} fade {c['fade']} tag {c['tag']}")
for k in ("qr_mode", "qr_tail", "end_card_image"):
    if base[k] == cur[k]:
        say("OK", f"{k} = {cur[k]}")
    else:
        say("CHANGED", f"{k}: baseline {base[k]} -> now {cur[k]}")
if base["lyrics_sha256"] != cur["lyrics_sha256"]:
    say("CHANGED", "lyrics_timing.tsv differs from the baseline (rows other than the frozen ones are not guarded)")
print("RESULT:", "FROZEN CHECKPOINTS INTACT" if not bad else "FROZEN CHECKPOINT CHANGED")
sys.exit(1 if bad else 0)
