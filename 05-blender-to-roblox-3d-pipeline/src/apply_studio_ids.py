# Compares parts imported by Studio Import 3D (dumped to .dave-work/studio_parts.json:
# name -> [meshId, sx, sy, sz, px, py, pz], pos relative to the model pivot) with meta.json,
# then writes the ids into ids.json. Run with D.A.V.E.'s bundled Python.
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
meta = json.load(open(os.path.join(ROOT, "meta.json"), encoding="utf-8"))
studio = json.load(open(os.path.join(ROOT, ".dave-work", "studio_parts.json"), encoding="utf-8"))
ids_path = os.path.join(ROOT, "ids.json")
ids = json.load(open(ids_path, encoding="utf-8"))
yaws = ids.get("_yaw", {})

bad, missing, worst = [], [], {}
for wid, w in meta.items():
    yaw = yaws.get(wid, 0)
    # pivot = scene origin; studio pos is relative to it. Weapons with yaw 180 were imported turned.
    for p in w["pieces"]:
        s = studio.get(p["name"])
        if not s:
            missing.append(p["name"]); continue
        size, pos = p["size"], p["pos"]
        spos = s[4:7]
        if yaw == 180:
            spos = [-spos[0], spos[1], -spos[2]]
        ds = max(abs(a - b) for a, b in zip(size, s[1:4]))
        dp = max(abs(a - b) for a, b in zip(pos, spos))
        worst[wid] = max(worst.get(wid, 0), ds, dp)
        if ds > 0.02 or dp > 0.02:
            bad.append((p["name"], round(ds, 3), round(dp, 3), size, s[1:4], pos, spos))
        ids[p["name"]] = "rbxassetid://" + s[0]

print("missing:", missing)
print("worst per weapon:", {k: round(v, 3) for k, v in sorted(worst.items())})
for b in bad[:40]:
    print("BAD", b)
print("bad count:", len(bad))
if "--write" in sys.argv and not missing:
    json.dump(ids, open(ids_path, "w", encoding="utf-8"), indent=1)
    print("ids.json written:", len([k for k in ids if not k.startswith("_")]))
