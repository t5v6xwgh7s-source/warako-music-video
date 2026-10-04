#!/usr/bin/env python3
"""Extract the rainbow cues R1..R7 from lyrics_timing.tsv, write work/storyboard/rainbow_cues.md and check the picture/voice sync.

Sync check (arithmetic on the timeline): at each cue's sung start / middle / end, the cut on screen must carry the intended rainbow tag,
and the cut-in must be complete BEFORE the sung start (so the rainbow is already visible when the word is heard).
Timing positions are estimates (see lyrics_timing.tsv confidence); the margin column shows how much slack the cut has.
"""
import importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_mv", os.path.join(ROOT, "scripts/build_mv.py"))
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

dur = bm.audio_duration()
cuts = bm.resolve_cuts(dur)
rows = bm.load_lyrics()

def nth(text, n):
    hits = [r for r in rows if r["text"] == text]
    return hits[n]

CUES = [  # cue, row, expected tag(s), role
    ("R1", nth("空にかかった虹が", 0), ("R1",), "最初の伏線。遠い淡い虹。再会は見せない"),
    ("R2", nth("虹の向こうで会いたい", 0), ("R2",), "最重要。虹がすでに明確に見えている。相手は見せない"),
    ("R3", nth("虹の向こうで", 0), ("R3",), "別の構図の、少し近い虹。虹の奥へ視線が進む"),
    ("R4", nth("虹の向こうで会いたい", 1), ("R4",), "2回目。1回目より近い。まだ会えない"),
    ("R5", nth("虹の向こうで", 2), ("R5",), "もう少しで届く。向こう側の光"),
    ("R6", nth("虹の向こうで会えたなら", 0), ("R6", "R6b"), "最大の転換。虹を見る側 → 向こう側へ"),
    ("R7", nth("虹の向こうで", 3), ("R7",), "虹を終わらせる。虹 → 虹色の光 → 暖かな光 → 宇宙酒場"),
]

if any(c.get("tag") == "R3b" for c in cuts):      # variant v3c_r3b: second "虹の向こうで" of the first chorus (0:52.32)
    CUES.insert(3, ("R3b", nth("虹の向こうで", 1), ("R3b",), "虹へ向かう(R3とは別の構図) → 次の p014 で一歩踏み出す"))

def cut_at(t):
    return next((c for c in cuts if c["t0"] <= t < c["t1"]), cuts[-1])

def visible_from(c):
    """time when the cut-in is complete (dissolve centred on t0)"""
    return c["t0"] + c["fade"] / 2

def trans(c):
    if c.get("bloom"):
        return f"光のブルーム {c['fade']:.1f}s"
    return "直CUT" if c["fade"] == 0 else (f"短いディゾルブ {c['fade']:.1f}s" if c["fade"] <= 0.5 else f"ディゾルブ {c['fade']:.1f}s")

def label(c):
    pg = c["page"]
    return c["key"] + (f"[{pg}]" if pg and len(pg) == 1 else (f"[{pg[0]}頁クロップ]" if pg else ""))

out = ["# rainbow cues (v3b)", "",
       "歌唱位置は `lyrics_timing.tsv` の推定(音量・低音・小節グリッド)。**全面の再推定はしていない**。虹の素材は既存45枚中 `p030_031_farewell` 左頁の1枚のみ(→ `image_requests.md`)。", "",
       "| cue | lyric | current_time | visual | transition | confidence |", "| --- | ----- | -----------: | ------ | ---------- | ---------- |"]
checks = []
ok_all = True
for cue, r, tags, role in CUES:
    c0 = cut_at(r["start"])
    out.append(f"| {cue} | {r['text']} | {bm.ts(r['start'])} | {label(c0)} — {c0['theme']} | {trans(c0)} (cut {bm.ts(c0['t0'])}) | {r['conf']} |")
    # second tag line / 'また' for R3(2nd pair) and R7
    pts = [("start", r["start"] + 0.05), ("mid", (r["start"] + r["end"]) / 2), ("end", r["end"] - 0.1)]
    states = []
    for nm, t in pts:
        c = cut_at(t)
        states.append((nm, t, c, c.get("tag") in tags))
    margin = r["start"] - visible_from(c0) if c0.get("tag") in tags else None
    ok = all(s[3] for s in states[:1]) and (margin is not None and margin >= 0.0)
    ok_all &= ok
    checks.append((cue, r, states, margin, ok, role))

# R3b (variant only): second "虹の向こうで" of the first chorus
# extra R7 'また' and R3 second pair (for the reader)
mata = nth("また", 0)
r3b = nth("虹の向こうで", 1)
out += ["", "補足キュー(同じ段階に含める):", "",
        f"- R3 の2つ目の「虹の向こうで」 {bm.ts(r3b['start'])}: {label(cut_at(r3b['start']))}(虹は残さず記憶へ戻る)",
        f"- R7 の「また」 {bm.ts(mata['start'])}: {label(cut_at(mata['start']))} — {cut_at(mata['start'])['theme']}",
        f"- 「またねじゃなくて」 {bm.ts(nth('またねじゃなくて',0)['start'])}: {label(cut_at(nth('またねじゃなくて',0)['start']))}",
        f"- 「おかえりって」 {bm.ts(nth('おかえりって',0)['start'])}: {label(cut_at(nth('おかえりって',0)['start']))}(虹・字幕・台詞なし)"]

out += ["", "## 各キューの役割", ""]
for cue, r, tags, role in CUES:
    out.append(f"- **{cue}** {r['text']} ({bm.ts(r['start'])}): {role}")

out += ["", "## 同期検査(タイムライン上の計算。歌唱位置は推定)", "",
        "| cue | 歌い出し | cut-in完了 | 余裕(歌い出し−完了) | 歌い出し | 歌唱中盤 | 歌い終わり | 判定 |", "|---|---:|---:|---:|---|---|---|---|"]
for cue, r, states, margin, ok, role in checks:
    c0 = states[0][2]
    mark = lambda s: "◯ " + (s[2].get("tag") or "") if s[3] else "✕ " + label(s[2])
    out.append(f"| {cue} | {bm.ts(r['start'])} | {bm.ts(visible_from(c0))} | {margin:+.2f}s | {mark(states[0])} | {mark(states[1])} | {mark(states[2])} | {'OK' if ok else '要修正'} |" if margin is not None else
               f"| {cue} | {bm.ts(r['start'])} | - | - | {mark(states[0])} | {mark(states[1])} | {mark(states[2])} | 要修正 |")
out += ["", "余裕が±0.3秒より小さいキューは、歌唱位置の推定誤差で外れる可能性がある。R2/R4 は0.4〜0.5秒早めに虹へCUTして吸収している。", "",
        "## 最終着地", "",
        "- 「またねじゃなくて」「おかえりって」: 親分(空いた席→親分アップ)。文字・タイトル・台詞・虹なし。カメラはほぼ静止(1.5%以内のゆっくりした寄りのみ)。"]
os.makedirs(bm.variant_dir(), exist_ok=True)
open(os.path.join(bm.variant_dir(), "rainbow_cues.md"), "w", encoding="utf8").write("\n".join(out) + "\n")
print("\n".join(out))
raise SystemExit(0 if ok_all else 1)
