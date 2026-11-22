"""Критик, этап 1 — автоматический контроль ролика ДО публикации.

python qa_check.py job.json            (job — спецификация с полями out_video / metadata / facts)
Код выхода 0 — PASS, 1 — есть ошибки (FAIL). Предупреждения (WARN) публикацию не блокируют.
Пишет отчёт <video>_qa.md рядом с роликом и лист кадров <video>_qa_frames.jpg для глазной проверки.
"""
import json, os, re, subprocess, sys

BANNED = ["warhammer", "for the emperor", "free robux", "get rich", "guaranteed", "leak", "leaked", "mod menu", "cheat",
          "гарантирован", "без вложений", "лёгкие деньги", "легкие деньги", "бесплатные робуксы", "слив", "чит"]
CLICKBAIT_LIES = ["official trailer", "gameplay leak"]


def probe(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    e = r.stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0
    v = re.search(r"Stream.*Video: (\w+).*?, (\d{3,5})x(\d{3,5})", e)
    a = re.search(r"Stream.*Audio: (\w+)", e)
    return dur, (v.group(1), int(v.group(2)), int(v.group(3))) if v else None, a.group(1) if a else None


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(i[-1]) if i else None


def main():
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    out = job.get("out_video") or job.get("out")
    md = job.get("metadata", {})
    errs, warns, oks = [], [], []
    if not os.path.exists(out):
        print("FAIL: нет файла", out); sys.exit(1)
    dur, v, a = probe(out)
    short = "/Shorts/" in out.replace("\\", "/") or job.get("format", "short") == "short"
    if not v:
        errs.append("нет видеодорожки")
    else:
        codec, w, h = v
        if short and (w, h) != (1080, 1920):
            errs.append(f"Shorts должен быть 1080x1920, а не {w}x{h}")
        else:
            oks.append(f"видео {codec} {w}x{h}")
    if not a:
        errs.append("нет звука")
    if short:
        if dur > 60:
            warns.append(f"длительность {dur:.1f} с > 60 с: удержание у Shorts дольше минуты падает")
        elif dur < 15:
            warns.append(f"длительность {dur:.1f} с — слишком коротко для сюжета")
        else:
            oks.append(f"длительность {dur:.1f} с")
    if short and job.get("hook"):  # плашка-хук: Impact 88 + поля 28 с каждой стороны должна влезать в 1080 с запасом под кнопки Shorts
        try:
            from PIL import ImageFont
            hw = ImageFont.truetype("C:/Windows/Fonts/impact.ttf", 88).getlength(job["hook"]) + 56
            if hw > 970:
                errs.append(f"хук «{job['hook']}» шириной {hw:.0f} px не влезает в кадр (максимум 970) — сократить")
            else:
                oks.append(f"хук {hw:.0f} px")
        except Exception as ex:
            warns.append(f"ширину хука проверить не удалось: {ex}")
    lu = loudness(out)
    if lu is None or not (-17 <= lu <= -11):
        warns.append(f"громкость {lu} LUFS вне диапазона −17…−11")
    else:
        oks.append(f"громкость {lu} LUFS")
    title = md.get("title", "")
    if not title:
        errs.append("нет заголовка")
    elif len(title) > 100:
        errs.append(f"заголовок {len(title)} > 100 символов")
    else:
        oks.append(f"заголовок {len(title)} симв.")
    m = re.search(r"in (\d+) seconds", title, re.I)
    if m and (dur > int(m.group(1)) + 0.5 or int(m.group(1)) - dur > 5):
        errs.append(f"заголовок обещает {m.group(1)} с, а ролик {dur:.0f} с")
    text_all = " ".join([title, md.get("description", "")] + [s.get("text", "") for s in job.get("segments", [])]).lower()
    # qa_allow: {"word": "reason"} — explicit per-spec exception (e.g. built-in single-player cheat codes, not cheat tools)
    allow = {k.lower(): v for k, v in (job.get("qa_allow") or {}).items() if str(v).strip()}
    for b in BANNED:
        if b in allow:
            if re.search(r"\b" + re.escape(b) + r"\b", text_all):
                warns.append(f"слово «{b}» разрешено спецификацией: {allow[b]}")
            continue
        if re.search(r"\b" + re.escape(b) + r"\b", text_all):
            errs.append(f"запрещённое/рискованное слово: «{b}»")
    for b in CLICKBAIT_LIES:
        if b in text_all:
            errs.append(f"ложное обещание в тексте: «{b}»")
    facts = job.get("facts", [])
    if not facts:
        errs.append("нет списка фактов с источниками")
    else:
        bad = [f["claim"] for f in facts if not str(f.get("source", "")).startswith(("http", "file:"))]
        if bad:
            errs.append("факты без источника: " + "; ".join(bad))
        else:
            oks.append(f"фактов с источниками: {len(facts)}")
        # источник должен вести на конкретную статью, а не на главную страницу, и открываться
        import urllib.parse, urllib.request
        for fct in facts:
            u = str(fct.get("source", ""))
            if u.startswith("file:"):
                # факт из собственного проекта: источник — существующий файл проекта
                lp = urllib.request.url2pathname(urllib.parse.urlparse(u).path)
                if not os.path.exists(lp):
                    errs.append(f"файл-источник не найден: {u}")
                continue
            path = urllib.parse.urlparse(u).path.strip("/")
            if u.startswith("http") and path.count("/") == 0 and len(path) < 12:
                errs.append(f"источник — главная страница, факт по нему не проверить: {u}")
                continue
            try:
                req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130 Safari/537.36"})
                code = urllib.request.urlopen(req, timeout=15).status
            except Exception as ex:
                code = getattr(ex, "code", None) or str(ex)[:60]
            if code == 404 or code == 410:
                errs.append(f"источник не существует ({code}): {u}")
            elif code != 200:
                warns.append(f"источник не открылся автоматически ({code}) — проверить вручную: {u}")
    origin = md.get("assets_origin", "").lower()
    if not origin:
        errs.append("не указано происхождение визуала (assets_origin)")
    elif "third-party" in origin and "no third-party" not in origin:
        warns.append("в ролике чужой материал — нужна проверка прав и «существенного отличия»")
    else:
        oks.append("визуал: " + md["assets_origin"])
    if md.get("made_for_kids") is None:
        warns.append("не указан флаг «для детей»")
    if len(md.get("tags", [])) < 3:
        warns.append("мало тегов")
    sheet = os.path.splitext(out)[0] + "_qa_frames.jpg"
    fps = 10 / max(dur, 1)  # ровно 10 кадров на весь ролик (раньше у длинных лист покрывал только начало)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-vf", f"fps={fps:.4f},scale=270:-1,tile=5x2", "-frames:v", "1", sheet])
    verdict = "FAIL" if errs else "PASS"
    rep = [f"# QA: {os.path.basename(out)} — {verdict}", ""]
    rep += ["## Ошибки (блокируют публикацию)"] + [f"- {x}" for x in errs or ["нет"]] + [""]
    rep += ["## Предупреждения"] + [f"- {x}" for x in warns or ["нет"]] + [""]
    rep += ["## Пройдено"] + [f"- {x}" for x in oks] + ["", f"Лист кадров для глазной проверки: {sheet}"]
    open(os.path.splitext(out)[0] + "_qa.md", "w", encoding="utf-8").write("\n".join(rep) + "\n")
    print("\n".join(rep))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
