"""После рендера партии «Тренды стримов»: главы из _timing.json -> описания, превью длинных,
строки в youtube_upload_plan.json (без дублей) и раздел в МЕТАДАННЫЕ_GAME_PULSE.md.
python build_trend_plan.py            (повторный запуск безопасен: заменяет свои строки и свой раздел)"""
import json, os, re, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = "H:/GameClips_Канал"
AUTO = f"{ROOT}/Автоматизация"
SRC = f"{ROOT}/Исходники/Rockstar_official/GTAVI_Videos_4K/GTAVI_An_Extended_Look.mp4"
PIN = "What should I cover next — secrets, money glitches or PC news? 👇"
PIN_SECRET = "Which GTA 6 secret should I find next? 👇"
SLOTS = [  # решение 20.11.2026: Shorts с 28.11 по 12:00/19:00 МСК, длинные 23.11 и 26.11 в 20:00
 ("GP_L03_gta6_first_48_hours", "2026-11-23", "20:00"),
 ("GP_L04_gta6_every_secret_at_launch", "2026-11-26", "20:00"),
 ("GP_T01_gta6_7_9_million_watching", "2026-11-28", "12:00"),
 ("GP_T03_gta6_30_fps", "2026-11-28", "19:00"),
 ("GP_T05_gta6_ufo_abduction", "2026-11-29", "12:00"),
 ("GP_T06_gta6_day1_glitches", "2026-11-29", "19:00"),
 ("GP_T02_gta6_biggest_streamer", "2026-11-30", "12:00"),
 ("GP_T04_gta6_cool_dog", "2026-11-30", "19:00"),
 ("GP_T08_gta6_gta5_hidden", "2026-12-01", "12:00"),
 ("GP_T07_gta6_honeymad_ban", "2026-12-01", "19:00"),
 ("GP_T09_gta6_streamer_records", "2026-12-02", "12:00"),
 ("GP_T10_gta6_chores", "2026-12-02", "19:00"),
]
THUMB = {
 "GP_L03": ("9:04", ["GTA 6", "FIRST", "48 HOURS"], "7.9M"),
 "GP_L04": ("18:56", ["GTA 6", "10", "SECRETS"], "UFO"),
}


def mmss(t):
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


def thumb(sid, stamp, lines, badge):
    m, s = stamp.split(":")
    frame = f"{AUTO}/jobs/{sid}_thumb_src.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(int(m) * 60 + int(s)), "-i", SRC, "-frames:v", "1",
                    "-vf", "scale=1280:720", frame], check=True)
    th = Image.open(frame).convert("RGB")
    dark = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dark)
    for x in range(760):
        dd.line([(x, 0), (x, 720)], fill=(0, 0, 0, int(215 * (1 - x / 760))))
    th.paste(dark, (0, 0), dark)
    d = ImageDraw.Draw(th)
    imp = "C:/Windows/Fonts/impact.ttf"
    d.text((50, 50), lines[0], font=ImageFont.truetype(imp, 170), fill=(255, 210, 31), stroke_width=8, stroke_fill=(0, 0, 0))
    d.text((55, 260), lines[1], font=ImageFont.truetype(imp, 150), fill=(255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0))
    d.text((55, 440), lines[2], font=ImageFont.truetype(imp, 150), fill=(255, 255, 255), stroke_width=7, stroke_fill=(0, 0, 0))
    d.rounded_rectangle((1000, 40, 1240, 150), radius=18, fill=(255, 46, 136))
    d.text((1120, 95), badge, font=ImageFont.truetype(imp, 78), fill=(255, 255, 255), anchor="mm")
    out = f"{ROOT}/Оформление/thumb_{sid}.jpg"
    th.save(out, quality=92)
    os.remove(frame)
    return out


def main():
    plan_p = f"{AUTO}/youtube_upload_plan.json"
    plan = json.load(open(plan_p, encoding="utf-8"))
    ids = {sid for sid in (n.split("_")[0] + "_" + n.split("_")[1] for n, _, _ in SLOTS)}
    plan = [p for p in plan if p["id"] not in ids]
    md = ["# Партия «Тренды стримов» (20.11.2026)", "",
          "Темы — `GTA6\\ТРЕНДЫ_СТРИМОВ_2026-11-20.md`. Футаж стримеров не используется: своя инфографика или фрагменты официального Extended Look. Сценарии — `Автоматизация\\scripts_gta6_trends.py`.", ""]
    for name, date, time in SLOTS:
        sid = "_".join(name.split("_")[:2])
        job = json.load(open(f"{AUTO}/jobs/{name}.json", encoding="utf-8"))
        out = job.get("out_video") or job["out"]
        m = job["metadata"]
        desc = m["description"]
        if "__CHAPTERS__" in desc:
            tm = json.load(open(os.path.splitext(out)[0] + "_timing.json", encoding="utf-8"))
            ch = "\n".join(f"{mmss(tm['starts'][c['seg']]) if c['seg'] else '0:00'} {c['title']}" for c in job["chapters"])
            desc = desc.replace("__CHAPTERS__", ch)
        entry = {"id": sid, "file": out.replace("/", "\\"), "title": m["title"], "description": desc,
                 "tags": ", ".join(m["tags"]), "date": date, "time": time,
                 "pinned_comment": PIN_SECRET if sid in ("GP_T04", "GP_T05", "GP_T08", "GP_L04") else PIN}
        if sid in THUMB:
            entry["thumbnail"] = thumb(sid, *THUMB[sid]).replace("/", "\\")
        plan.append(entry)
        d, mo = date[8:10], date[5:7]
        md += [f"**{os.path.basename(out)}** — {d}.{mo} {time} МСК", f"- Заголовок: `{m['title']}`",
               "- Описание:", "```", desc, "```", f"- Теги: {', '.join(m['tags'])}", f"- Закреп: `{entry['pinned_comment']}`", ""]
    json.dump(plan, open(plan_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    mp = f"{ROOT}/МЕТАДАННЫЕ_GAME_PULSE.md"
    txt = open(mp, encoding="utf-8").read()
    txt = re.split(r"\n# Партия «Тренды стримов»", txt)[0].rstrip() + "\n\n" + "\n".join(md) + "\n"
    open(mp, "w", encoding="utf-8").write(txt)
    print("plan entries:", len(plan), "| new:", len(SLOTS))


if __name__ == "__main__":
    main()
