"""Считает правильные таймкоды глав для 12 треков WME по картам строк (.dave-work/lines)
и распознанным окнам (.dave-work/lyrics). Пишет план в H:/YouTube_2_канала/.dave-work/timecodes_plan.json."""
import json, os, re, statistics, difflib

BASE = r"H:\YouTube_2_канала\Канал1_World_Metal_Empire\.dave-work"
OUT = r"H:\YouTube_2_канала\.dave-work\timecodes_plan.json"

TRACKS = {
    "jVF4Bd5hf58": ("Eternal War", ["0:00 Intro", "0:25 Verse 1", "0:55 Pre-Chorus", "1:15 Chorus", "2:00 Verse 2", "3:00 Bridge", "3:30 Breakdown", "3:50 Guitar Solo", "4:10 Final Chorus", "5:30 Outro"]),
    "SuPWEtXs6VI": ("Angels of Death", ["0:00 Instrumental intro", "0:20 Verse 1", "0:55 Pre-Chorus", "1:05 Chorus", "1:45 Verse 2", "2:20 Breakdown", "2:50 Guitar Solo", "3:10 Final Chorus"]),
    "4RIkiHsnZVc": ("Winter's Gate", ["0:00 Instrumental intro", "0:30 Verse 1", "1:05 Pre-Chorus", "1:20 Chorus", "2:15 Verse 2", "2:50 Bridge", "3:40 Guitar Solo", "4:05 Final Chorus"]),
    "lNd3SyeFPlg": ("Blood for the Red Angel", ["0:00 Instrumental intro", "0:20 Verse 1", "0:55 Pre-Chorus", "1:10 Chorus", "1:45 Verse 2", "2:20 Pre-Chorus", "2:35 Chorus", "3:00 Breakdown", "3:20 Guitar Solo", "3:40 Final Chorus"]),
    "zn1HjnGAZrE": ("Ghosts of Istvaan", ["0:00 Instrumental intro", "0:35 Verse 1", "1:20 Pre-Chorus", "1:40 Chorus", "2:45 Verse 2", "3:30 Pre-Chorus", "3:50 Guitar Solo", "4:20 Final Chorus"]),
    "LQFQS7dd9nk": ("The last Black Templar", ["0:00 Instrumental intro", "0:30 Verse 1", "1:10 Pre-Chorus", "1:25 Chorus", "2:05 Verse 2", "2:45 Pre-Chorus", "3:00 Chorus", "3:40 Bridge", "4:00 Guitar Solo", "4:25 Final Chorus"]),
    "SB-V-fT3D4k": ("Children of the Void", ["0:00 Instrumental intro", "0:25 Verse 1", "1:05 Pre-Chorus", "1:20 Chorus", "1:55 Verse 2", "2:50 Breakdown", "3:05 Bridge", "3:20 Guitar Solo", "3:45 Final Chorus"]),
    "qDKbA_LKlc0": ("Machine God Rising", ["0:00 Instrumental intro", "0:30 Verse 1", "1:10 Pre-Chorus", "1:25 Chorus", "2:05 Verse 2", "2:45 Pre-Chorus", "3:00 Chorus", "3:40 Bridge", "4:00 Guitar Solo", "4:25 Final Chorus"]),
    "zrQQxds13no": ("The Siege of Terra", ["0:00 Instrumental intro", "0:40 Verse 1", "1:20 Pre-Chorus", "1:40 Chorus", "2:25 Interlude", "2:50 Verse 2", "3:30 Pre-Chorus", "3:50 Bridge", "4:20 Guitar Solo", "4:50 Final Chorus"]),
    "8UY25HMrsJw": ("When the Stars remember US", ["0:00 Intro", "0:35 Verse 1", "1:25 Pre-Chorus", "1:45 Chorus", "2:25 Interlude", "2:50 Verse 2", "3:40 Pre-Chorus", "4:00 Bridge", "4:30 Guitar Solo", "5:00 Final Chorus"]),
    "KPYAgghEaCU": ("The Rose in the Ashes", ["0:00 Intro", "0:40 Verse 1", "1:30 Pre-Chorus", "1:55 Chorus", "2:40 Interlude", "3:05 Verse 2", "3:55 Pre-Chorus", "4:20 Bridge", "4:50 Guitar Solo", "5:20 Final Chorus"]),
    "8YL-SxKH_wQ": ("Green Tide Rising", ["0:00 Intro", "0:20 Verse 1", "0:55 Pre-Chorus", "1:10 Chorus", "1:45 Verse 2", "2:35 Breakdown", "3:00 Final Chorus"]),
}
NONVOCAL = {"Guitar Solo", "Interlude"}


def fmt(s):
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"


def norm(t):
    return re.sub(r"[^a-z' ]", " ", t.lower()).split()


FILL_WORDS = set("yeah oh hey you thank i'm out go let's my god we'll be right back i don't know of here going to uh ah".split())


def is_filler(text):
    toks = norm(text)
    return not toks or all(t in FILL_WORDS for t in toks)


def blocks_of(lines):
    bl = []
    for x in lines:
        if not bl or bl[-1]["s"] != x["section"]:
            bl.append({"s": x["section"], "lines": []})
        bl[-1]["lines"].append(x)
    for b in bl:
        ts = [(i, x["t"]) for i, x in enumerate(b["lines"]) if x["t"] is not None]
        steps = [b2 - a2 for (i1, a2), (i2, b2) in zip(ts, ts[1:]) if i2 == i1 + 1 and b2 > a2]
        step = min(5.0, max(2.0, statistics.median(steps))) if steps else 3.0
        b["step"] = step
        if ts:
            i0, t0 = ts[0]
            b["start"] = t0 - i0 * step
            il, tl = ts[-1]
            b["end"] = tl + (len(b["lines"]) - 1 - il) * step + step
        else:
            b["start"] = b["end"] = None
    return bl


def window_search(windows, ref_lines, lo, hi):
    """Самое раннее окно в [lo, hi), похожее на первую (или вторую) строку раздела."""
    best = None
    for w in windows:
        if w["t0"] < lo or w["t0"] >= hi:
            continue
        wt = " ".join(norm(w["text"]))
        if not wt:
            continue
        for k, ref in enumerate(ref_lines[:2]):
            r = difflib.SequenceMatcher(None, wt, " ".join(norm(ref))).ratio()
            # окно 2,5 с вмещает кусок строки — сравниваем и с началом строки
            r2 = difflib.SequenceMatcher(None, wt, " ".join(norm(ref))[: len(wt) + 4]).ratio()
            r = max(r, r2)
            if r >= 0.62:
                t = w["t0"] - k * 3.0
                return t, round(r, 2), w["text"], k
    return best


plan = {}
for vid, (name, chapters) in TRACKS.items():
    lines = json.load(open(os.path.join(BASE, "lines", name + ".lines.json"), encoding="utf-8"))
    windows = json.load(open(os.path.join(BASE, "lyrics", name + ".windows.json"), encoding="utf-8"))
    bl = blocks_of(lines)
    first_occ = {}
    for b in bl:
        first_occ.setdefault(b["s"], b)
    parsed = []
    for c in chapters:
        tm, label = c.split(" ", 1)
        parsed.append({"old": tm, "label": label, "base": label.split(" — ")[0].split(" (")[0].strip()})

    # 1) прямые совпадения с блоками
    ptr = 0
    for ch in parsed:
        base = ch["base"]
        if ch is parsed[0]:
            ch.update(new=0.0, how="intro")
            continue
        if base in NONVOCAL:
            continue
        for j in range(ptr, len(bl)):
            if bl[j]["s"] == base and bl[j]["start"] is not None:
                ch.update(new=bl[j]["start"], end=bl[j]["end"], how="lines")
                ptr = j + 1
                break
    # 2) пропущенные вокальные — поиск в окнах распознавания
    for i, ch in enumerate(parsed):
        if "new" in ch or ch["base"] in NONVOCAL:
            continue
        lo = max([p.get("end", p.get("new", 0)) for p in parsed[:i] if "new" in p] or [0])
        hi = min([p["new"] for p in parsed[i + 1:] if "new" in p] or [1e9])
        ref = first_occ.get(ch["base"])
        if not ref:
            ch["how"] = "MISSING"
            continue
        r = window_search(windows, [x["text"] for x in ref["lines"]], lo, hi)
        if r:
            ch.update(new=r[0], end=r[0] + (ref["end"] - ref["start"]), how=f"window r={r[1]} '{r[2]}'")
        else:
            ch["how"] = f"MISSING window {lo:.1f}-{hi:.1f}"
    # 3) невокальные — первое место после предыдущего раздела, где распознавание
    #    выдаёт только «мусор» (галлюцинации Whisper на музыке без голоса) два окна подряд
    grid = [w for w in windows if abs(w["t0"] / 2.5 - round(w["t0"] / 2.5)) < 1e-6]
    for i, ch in enumerate(parsed):
        if ch["base"] not in NONVOCAL:
            continue
        prev = parsed[i - 1]
        nxt = min([p["new"] for p in parsed[i + 1:] if "new" in p] or [1e9])
        t = None
        for a, b in zip(grid, grid[1:]):
            floor = max(prev["new"] + 8, prev.get("end", 0) - 2.5)  # не раньше последней спетой строки
            if a["t0"] >= floor and a["t0"] < nxt and is_filler(a["text"]) and is_filler(b["text"]):
                t = a["t0"]
                break
        how = "first no-vocal window"
        if t is None:
            t = prev.get("end", prev["new"] + 10)
            how = "after prev vocal"
        ch.update(new=t, how=f"{how} (next {nxt:.1f})")
    # 4) YouTube требует разделы не короче 10 с: короткий раздел начинаем раньше
    secs_all = [p for p in parsed if "new" in p]
    for k in range(len(secs_all) - 1, 0, -1):
        cur, nx, pv = secs_all[k - 1], secs_all[k], secs_all[k - 2] if k >= 2 else None
        if int(nx["new"]) - int(cur["new"]) < 10 and cur is not parsed[0]:
            moved = int(nx["new"]) - 10
            if pv is None or moved - int(pv["new"]) >= 10:
                cur["how"] += f" | moved earlier from {fmt(cur['new'])} (10 s rule)"
                cur["new"] = moved

    for ch in parsed:
        if "new" in ch:
            ch["new_tc"] = fmt(ch["new"])
    # проверки
    problems = []
    secs = [int(ch["new"]) for ch in parsed if "new" in ch]
    if len(secs) != len(parsed):
        problems.append("не все разделы найдены")
    for a, b in zip(secs, secs[1:]):
        if b - a < 10:
            problems.append(f"короче 10 с: {fmt(a)} -> {fmt(b)}")
    plan[vid] = {"track": name, "chapters": [{k: ch.get(k) for k in ("label", "old", "new_tc", "how")} for ch in parsed], "problems": problems}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(plan, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for vid, p in plan.items():
    print(vid, p["track"], "PROBLEMS:" if p["problems"] else "", p["problems"] or "")
    for c in p["chapters"]:
        print(f"   {c['old']:>5} -> {str(c['new_tc']):>5}  {c['label'][:40]:40} {c['how']}")
