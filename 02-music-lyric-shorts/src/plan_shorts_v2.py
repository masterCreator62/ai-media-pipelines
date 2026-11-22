"""Сборка jobs.json для render_shorts_v2.py из плана фрагментов и карты строк (align_lyrics.py).

Использование:
  python plan_shorts_v2.py sections <lines_dir> [трек ...]     — показать разделы и время их начала
  python plan_shorts_v2.py build <plan.json> <lines_dir> <clips_dir> <out_jobs.json> [--show]
plan.json: {"out_dir": "...", "segments": [{
    "id": "WME_V01", "track": "Eternal War",
    "from": ["Chorus", 1]  или  "start": 93.7,      # раздел и номер его появления (с 1)
    "to":   ["Chorus", 1]  или  "end": 126,          # до конца этого раздела (+ хвост) или до времени
    "max": 35, "min": 25, "lead": 0.35, "tail": 2.6,
    "hook": ["...", "..."], "crop": 0.66,
    "fix": {"старый текст строки": "что реально поётся"}   # необязательно
}]}
"""
import json, os, sys


def occurrences(lines, sec):
    """Список (первый_индекс, последний_индекс) для каждого появления раздела."""
    occ, cur = [], None
    for i, l in enumerate(lines):
        if l["section"] == sec:
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
        elif cur is not None:
            occ.append(tuple(cur))
            cur = None
    if cur is not None:
        occ.append(tuple(cur))
    return occ


def first_t(lines, a, b):
    for i in range(a, b + 1):
        if lines[i]["t"] is not None:
            return lines[i]["t"]
    return None


def last_t(lines, a, b):
    for i in range(b, a - 1, -1):
        if lines[i]["t"] is not None:
            return lines[i]["t"]
    return None


def cmd_sections(ldir, only):
    for fn in sorted(os.listdir(ldir)):
        if not fn.endswith(".lines.json"):
            continue
        tr = fn[:-11]
        if only and tr not in only:
            continue
        lines = json.load(open(os.path.join(ldir, fn), encoding="utf-8"))
        print("==", tr)
        seen = {}
        for i, l in enumerate(lines):
            if i == 0 or l["section"] != lines[i - 1]["section"]:
                seen[l["section"]] = seen.get(l["section"], 0) + 1
                occ = occurrences(lines, l["section"])[seen[l["section"]] - 1]
                print(f"  {l['section']:<14} #{seen[l['section']]}  {first_t(lines, *occ)} .. {last_t(lines, *occ)}"
                      f"  ({sum(1 for x in range(occ[0], occ[1] + 1) if lines[x]['t'] is not None)}/{occ[1] - occ[0] + 1})")


def cmd_build(plan_p, ldir, cdir, out_p, show):
    plan = json.load(open(plan_p, encoding="utf-8"))
    jobs = []
    for s in plan["segments"]:
        lines = json.load(open(os.path.join(ldir, s["track"] + ".lines.json"), encoding="utf-8"))
        lead, tail = s.get("lead", 0.35), s.get("tail", 2.6)
        if "start" in s:
            start = s["start"]
        else:
            sec, k = s["from"]
            a, b = occurrences(lines, sec)[k - 1]
            start = first_t(lines, a, b) - lead
        if "end" in s:
            end = s["end"]
        else:
            sec, k = s.get("to", s.get("from"))
            a, b = occurrences(lines, sec)[k - 1]
            end = last_t(lines, a, b) + tail
        dur = max(s.get("min", 25), min(s.get("max", 35), end - start))
        fix = s.get("fix", {})
        sel = []
        for l in lines:
            if l["t"] is None or not (start - 0.5 <= l["t"] < start + dur - 0.4):
                continue
            txt = fix.get(l["text"], l["text"])
            if txt:
                sel.append({"t": max(l["t"], start + 0.05), "text": txt})
        if "lines" in s:  # строки, выверенные вручную по транскрипции
            sel = [{"t": max(l["t"], start + 0.05), "text": l["text"]} for l in s["lines"]
                   if start - 0.5 <= l["t"] < start + dur - 0.4]
        clip = os.path.join(cdir, s["track"] + ".mp4")
        job = {"src": clip, "start": round(start, 2), "dur": round(dur, 2),
               "out": os.path.join(plan["out_dir"], s["id"] + ".mp4"),
               "hook": s["hook"], "lines": sel, "crop": s.get("crop", 0.66), "zoom": s.get("zoom", 0.06)}
        jobs.append(job)
        if show:
            print(f"== {s['id']} {s['track']} start={job['start']} dur={job['dur']} hook={' / '.join(s['hook'])}")
            for l in sel:
                src = next((x for x in lines if fix.get(x["text"], x["text"]) == l["text"] and x["t"] is not None
                            and abs(max(x["t"], start + 0.05) - l["t"]) < 0.01), {})
                flag = "~" if src.get("interp") else (" " if src.get("score", 1) >= 0.6 else "?")
                print(f"  {flag}{l['t'] - start:6.2f}  {l['text'][:48]:<48} :: {src.get('heard', '')[:70]}")
    json.dump({"jobs": jobs}, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"jobs: {len(jobs)} -> {out_p}")


if __name__ == "__main__":
    if sys.argv[1] == "sections":
        cmd_sections(sys.argv[2], sys.argv[3:])
    else:
        cmd_build(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], "--show" in sys.argv)
