"""Генератор новостного видео: сценарий -> ИИ-озвучка (edge-tts) -> анимация картинок (Ken Burns) -> субтитры -> mp4.

python make_news_video.py script.json
script.json:
{
  "out": "H:/.../video.mp4", "format": "short" | "long", "voice": "en-US-AndrewNeural", "rate": "+8%",
  "hook": "текст плашки сверху в первые 3 с (short)", "watermark": "GAME PULSE",
  "segments": [{"text": "фраза диктора", "images": ["путь1.jpg", "путь2.jpg"], "title": "необяз. заголовок на экране (long)"}]
}
Необязательные поля (без них ролик собирается как раньше):
  "music": {"style": "calm_minor" | "tech_pulse", "bpm": 100, "seed": 1, "gain_db": -20, "gap_boost_db": 7}
           своя процедурная музыка (make_music.py), «приседает» под голос: gain_db — уровень под речью относительно речи
  "sfx": true, "sfx_gain_db": -14     вжух + мягкий удар на каждой смене картинки
  "sub_margin_v": 560, "sub_margin_h": 60, "sub_size": 92   субтитры Shorts: отступ снизу / по бокам, кегль (px кадра 1080x1920)
  "hook_y": 300                         верх плашки-хука
  "motion": "gentle"                    меньше бокового дрейфа (для карточек-инфографики: края не срезаются)
"""
import asyncio, json, math, os, random, re, subprocess, sys
import edge_tts
from PIL import Image, ImageFilter

FPS = 30

def synth(text, voice, rate, mp3):
    async def run():
        c = edge_tts.Communicate(text, voice, rate=rate)
        sents, audio = [], b""
        async for ch in c.stream():
            if ch["type"] == "audio":
                audio += ch["data"]
            elif ch["type"] in ("SentenceBoundary", "WordBoundary"):
                sents.append((ch["offset"] / 1e7, ch["duration"] / 1e7, ch["text"]))
        open(mp3, "wb").write(audio)
        return sents
    import time
    for attempt in range(10):
        try:
            return asyncio.run(run())
        except Exception as e:  # сервис иногда временно отказывает (NoAudioReceived) — повтор с растущей паузой
            if attempt == 9:
                raise
            time.sleep(min(60, 8 * (attempt + 1)))
    return []

def dur_of(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

def words_timed(sents, t0):
    """Слова с временем: внутри предложения время делится пропорционально длине слова."""
    out = []
    for off, d, txt in sents:
        ws = txt.split()
        if not ws:
            continue
        total = sum(len(w) + 1 for w in ws)
        t = off
        for w in ws:
            wd = d * (len(w) + 1) / total
            out.append((t0 + t, t0 + t + wd, w))
            t += wd
    return out

def ass_time(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def make_groups(words, group, seg_starts):
    """Группы слов для субтитров: не переходят через границу сегмента и не отрывают число от слова перед ним
    («GTA 5», «May 26»), если перед числом не конец фразы."""
    groups, cur = [], []
    for i, wd in enumerate(words):
        w = wd[2]
        boundary = i in seg_starts
        glue = bool(re.match(r"[\d#$]", w)) and cur and not re.search(r"[.!?]$", cur[-1][2])
        # короткий предлог/союз («с», «и», «на», «в», «a», «of») не оставляем висеть в конце группы
        glue = glue or (cur and len(cur[-1][2]) <= 2 and cur[-1][2].isalpha())
        if cur and (boundary or (len(cur) >= group and not glue) or len(cur) >= group + 2):
            groups.append(cur); cur = []
        cur.append(wd)
    if cur:
        groups.append(cur)
    return groups

def make_ass(words, path, fmt, W, H, seg_starts=(), margin_v=560, margin_h=60, size=92):
    if fmt == "short":
        style = f"Style: C,Impact,{size},&H00FFFFFF,&H0000D7FF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,7,3,2,{margin_h},{margin_h},{margin_v},1"
        group = 3
    else:
        style = f"Style: C,Arial Black,64,&H00FFFFFF,&H0000D7FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,120,120,90,1"
        group = 5
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             style, "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    groups = make_groups(words, group, set(seg_starts))
    for gi, g in enumerate(groups):
        start, end = g[0][0], g[-1][1]
        if gi + 1 < len(groups):
            end = min(end + 0.15, groups[gi + 1][0][0])
        for j, (ws, we, w) in enumerate(g):
            parts = []
            for k, (_, _, ww) in enumerate(g):
                t = ww.upper() if fmt == "short" else ww
                t = t.replace("{", "(").replace("}", ")")
                parts.append("{\\c&H00D7FF&}" + t + "{\\c&HFFFFFF&}" if k == j else t)
            s = ws if j else start
            e = g[j + 1][0] if j + 1 < len(g) else end
            lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},C,,0,0,0,,{' '.join(parts)}")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

def render_frames(images_with_dur, W, H, proc, motion=None):
    """Ken Burns: каждое изображение плавно приближается/сдвигается; кадры пишутся в stdin ffmpeg."""
    rnd = random.Random(7)
    for path, d in images_with_dur:
        im = Image.open(path).convert("RGB")
        # подготовка: заполнить кадр с запасом 18% под движение
        sc = max(W / im.width, H / im.height) * 1.18
        if W < H:  # вертикаль: заранее вырезаем центральную полосу, чтобы не таскать 4K-ширину
            need_w = im.height * W / H * 1.35
            x = (im.width - need_w) / 2
            im = im.crop((int(x), 0, int(x + need_w), im.height))
            sc = max(W / im.width, H / im.height) * 1.18
        base = im.resize((max(W, int(im.width * sc)), max(H, int(im.height * sc))), Image.BILINEAR)
        n = max(1, int(round(d * FPS)))
        z0, z1 = (1.0, 1.12) if rnd.random() < 0.6 else (1.12, 1.0)
        bw, bh = base.size
        cx0, cy0 = rnd.uniform(0.42, 0.58), rnd.uniform(0.42, 0.58)
        cx1, cy1 = cx0 + rnd.uniform(-0.06, 0.06), cy0 + rnd.uniform(-0.04, 0.04)
        if motion == "gentle":  # центр окна 0.43..0.57 ширины: у карточки 1460 px всегда видна полоса x 320..1140
            cx0 = 0.5 + (cx0 - 0.5) * 0.5
            cx1 = cx0 + (cx1 - cx0) * 0.6
        for f in range(n):
            t = f / max(1, n - 1)
            e = t * t * (3 - 2 * t)  # плавный старт/финиш
            z = z0 + (z1 - z0) * e
            win_w = (bw / 1.18) / z
            win_h = win_w * H / W
            if win_h > bh:
                win_h = bh; win_w = win_h * W / H
            cx = (cx0 + (cx1 - cx0) * e) * bw
            cy = (cy0 + (cy1 - cy0) * e) * bh
            x0 = min(max(0, cx - win_w / 2), bw - win_w)
            y0 = min(max(0, cy - win_h / 2), bh - win_h)
            fr = base.transform((W, H), Image.EXTENT, (x0, y0, x0 + win_w, y0 + win_h), Image.BILINEAR)
            proc.stdin.write(fr.tobytes())

def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    fmt = cfg.get("format", "short")
    W, H = (1080, 1920) if fmt == "short" else (1920, 1080)
    out = cfg["out"]
    work = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), os.path.splitext(os.path.basename(out))[0] + "_tmp")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    voice, rate = cfg.get("voice", "en-US-AndrewNeural"), cfg.get("rate", "+8%")
    # 1. озвучка по сегментам
    t0, words, plan, alist, starts, seg_starts = 0.0, [], [], [], [], []
    gap = 0.25
    for i, seg in enumerate(cfg["segments"]):
        starts.append(round(t0, 2))
        mp3 = os.path.join(work, f"a{i:02d}.mp3")
        sents = synth(seg["text"], voice, rate, mp3)
        wav = os.path.join(work, f"a{i:02d}.wav")  # точная длительность только после декодирования
        subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-i", mp3, "-ar", "24000", "-ac", "1", wav], check=True)
        import wave
        with wave.open(wav) as wf:
            d = wf.getnframes() / wf.getframerate()
        mp3 = wav
        seg_starts.append(len(words))
        words += words_timed(sents, t0)
        imgs = seg["images"]
        per = (d + gap) / len(imgs)
        plan += [(p, per) for p in imgs]
        alist.append(mp3)
        t0 += d + gap
    total = t0
    # аудио: склейка с паузами
    lst = os.path.join(work, "alist.txt")
    sil = os.path.join(work, "sil.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(gap), sil], check=True)
    with open(lst, "w", encoding="utf-8") as f:
        for a in alist:
            f.write(f"file '{a.replace(chr(92), '/')}'\nfile '{sil.replace(chr(92), '/')}'\n")
    voice_wav = os.path.join(work, "voice.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ar", "48000", "-ac", "2", voice_wav], check=True)
    # 2. субтитры
    make_ass(words, os.path.join(work, "subs.ass"), fmt, W, H, seg_starts,
             cfg.get("sub_margin_v", 560), cfg.get("sub_margin_h", 60), cfg.get("sub_size", 92))
    # 2b. своя музыка + звуки переходов (необязательно)
    audio_in = voice_wav
    if cfg.get("music") or cfg.get("sfx"):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import make_music
        vw = make_music.read_wav(voice_wav)
        cues, tc = [], 0.0
        for _, d in plan:
            cues.append(tc); tc += d
        mixed, st = make_music.mix_with_voice(vw, vw.shape[0] / make_music.SR, cfg.get("music"),
                                              cues if cfg.get("sfx") else None, cfg.get("sfx_gain_db", -14.0))
        audio_in = os.path.join(work, "mix.wav")
        make_music.write_wav(audio_in, mixed)
        print("mix:", {k: round(float(v), 1) for k, v in st.items()})
    # 3. видео: кадры -> ffmpeg (+ субтитры, плашка, водяной знак, голос)
    open(os.path.join(work, "hook.txt"), "w", encoding="utf-8").write(cfg.get("hook", ""))
    open(os.path.join(work, "wm.txt"), "w", encoding="utf-8").write(cfg.get("watermark", ""))
    import shutil
    shutil.copyfile("C:/Windows/Fonts/impact.ttf", os.path.join(work, "font.ttf"))
    vf = "subtitles=subs.ass"
    if fmt == "short" and cfg.get("hook"):
        vf += (",drawtext=fontfile=font.ttf:textfile=hook.txt:fontsize=88:fontcolor=black:box=1:boxcolor=0xFFD21F@1:boxborderw=28"
               f":x=(w-text_w)/2:y={cfg.get('hook_y', 300)}:enable='lt(t,3.2)'")
    if cfg.get("watermark"):
        y = "70" if fmt == "short" else "40"  # у Shorts низ кадра перекрыт интерфейсом — знак наверху
        x = "(w-text_w)/2" if fmt == "short" else "w-text_w-50"
        vf += f",drawtext=fontfile=font.ttf:textfile=wm.txt:fontsize=40:fontcolor=white@0.75:borderw=3:bordercolor=black@0.6:x={x}:y={y}"
    vf += ",format=yuv420p"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", audio_in, "-vf", vf, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "h264_mf", "-b:v", "12M" if fmt == "short" else "10M", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-shortest", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, cwd=work)
    render_frames(plan, W, H, proc, cfg.get("motion"))
    proc.stdin.close()
    rc = proc.wait()
    ok = rc == 0 and os.path.exists(out) and os.path.getsize(out) > 300_000
    print(("OK " if ok else "FAIL ") + out + f"  {total:.1f}s")
    if ok:
        json.dump({"total": total, "starts": starts}, open(os.path.splitext(out)[0] + "_timing.json", "w"), indent=1)
        shutil.rmtree(work, ignore_errors=True)

if __name__ == "__main__":
    main()
