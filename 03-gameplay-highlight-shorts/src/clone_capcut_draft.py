"""Создаёт проект CapCut копированием рабочего черновика-шаблона и заменой таймлайна.

python clone_capcut_draft.py <шаблон> <папка_черновиков> <имя> <ширина> <высота> <fps> file1.mp4 ...
Структура шаблона (id таймлайна, служебные файлы) сохраняется — меняются только клипы, длительность и имя.
"""
import copy, json, os, re, shutil, subprocess, sys, time, uuid

def uid():
    return str(uuid.uuid4()).upper()

def probe(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    dur = int(round((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * 1_000_000))
    v = re.search(r"Video: .*?, (\d{3,5})x(\d{3,5})", r.stderr)
    return dur, int(v.group(1)), int(v.group(2)), "Audio:" in r.stderr

def main():
    tpl, root, name, W, H, fps = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6])
    files = [os.path.abspath(f) for f in sys.argv[7:]]
    dst = os.path.join(root, name)
    if os.path.exists(dst):
        sys.exit(f"уже существует: {dst}")
    ignore = shutil.ignore_patterns("*.mp4", "*.mp3", "draft_cover.jpg", "*.bak", "template*.tmp", "mini_draft.json")
    shutil.copytree(tpl, dst, ignore=ignore)

    d = json.load(open(os.path.join(tpl, "draft_content.json"), encoding="utf-8"))
    m = d["materials"]
    vtrack = next(t for t in d["tracks"] if t["type"] == "video")
    atrack = next((t for t in d["tracks"] if t["type"] == "audio"), None)
    pseg = vtrack["segments"][0]
    pvid = next(v for v in m["videos"] if v["id"] == pseg["material_id"])
    extras = []
    for ref in pseg["extra_material_refs"]:
        for k, lst in m.items():
            if isinstance(lst, list):
                hit = next((x for x in lst if isinstance(x, dict) and x.get("id") == ref), None)
                if hit:
                    extras.append((k, hit)); break
    keep_lists = {k for k, _ in extras} | {"videos"}
    for k in list(m.keys()):
        if isinstance(m[k], list) and k in keep_lists:
            m[k] = []
    # аудио-дорожку шаблона и её материалы убираем
    if atrack:
        aids = {s["material_id"] for s in atrack["segments"]}
        arefs = {r for s in atrack["segments"] for r in s.get("extra_material_refs", [])}
        for k in list(m.keys()):
            if isinstance(m[k], list):
                m[k] = [x for x in m[k] if not (isinstance(x, dict) and x.get("id") in aids | arefs)]
    segs, meta_vals, t, size = [], [], 0, 0
    now = int(time.time())
    for f in files:
        dur, w, h, has_a = probe(f)
        size += os.path.getsize(f)
        vid = copy.deepcopy(pvid)
        vid.update({"id": uid(), "path": f.replace("\\", "/"), "material_name": os.path.basename(f),
                    "duration": dur, "width": w, "height": h, "has_audio": has_a})
        m["videos"].append(vid)
        refs = []
        for k, proto in extras:
            x = copy.deepcopy(proto); x["id"] = uid(); m[k].append(x); refs.append(x["id"])
        s = copy.deepcopy(pseg)
        s.update({"id": uid(), "material_id": vid["id"], "extra_material_refs": refs,
                  "source_timerange": {"start": 0, "duration": dur}, "target_timerange": {"start": t, "duration": dur},
                  "volume": 1.0, "speed": 1.0, "keyframe_refs": []})
        segs.append(s)
        meta_vals.append({"ai_group_type": "", "create_time": now, "duration": dur, "enter_from": 0,
                          "extra_info": os.path.basename(f), "file_Path": f.replace("\\", "/"), "height": h,
                          "id": str(uuid.uuid4()), "import_time": now, "import_time_ms": now * 1_000_000, "item_source": 1,
                          "material_color_tag": "", "md5": "", "metetype": "video",
                          "roughcut_time_range": {"duration": dur, "start": 0},
                          "sub_time_range": {"duration": -1, "start": -1}, "type": 0, "width": w})
        t += dur
    vtrack["segments"] = segs
    d["tracks"] = [vtrack]
    d["duration"] = t
    d["fps"] = fps
    d["canvas_config"].update({"width": W, "height": H})
    txt = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    for p in [os.path.join(dst, "draft_content.json"), os.path.join(dst, "Timelines", d["id"], "draft_content.json")]:
        if os.path.exists(os.path.dirname(p)):
            open(p, "w", encoding="utf-8").write(txt)
    meta = json.load(open(os.path.join(tpl, "draft_meta_info.json"), encoding="utf-8"))
    us = now * 1_000_000
    mats = meta["draft_materials"]
    for grp in mats:
        if grp["type"] == 0:
            grp["value"] = meta_vals
        elif grp["type"] == 3:
            grp["value"] = []
    meta.update({"draft_cover": "", "draft_fold_path": dst.replace("\\", "/"), "draft_id": str(uuid.uuid4()).upper(),
                 "draft_name": name, "draft_timeline_materials_size_": size, "tm_draft_create": us, "tm_draft_modified": us,
                 "tm_duration": t})
    json.dump(meta, open(os.path.join(dst, "draft_meta_info.json"), "w", encoding="utf-8"), ensure_ascii=False)
    vs = json.load(open(os.path.join(tpl, "draft_virtual_store.json"), encoding="utf-8"))
    for grp in vs["draft_virtual_store"]:
        if grp["type"] == 1:
            grp["value"] = [{"child_id": v["id"], "parent_id": ""} for v in meta_vals]
    json.dump(vs, open(os.path.join(dst, "draft_virtual_store.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"OK {dst} клипов={len(files)} длительность={t/1e6:.1f} c")

if __name__ == "__main__":
    main()
