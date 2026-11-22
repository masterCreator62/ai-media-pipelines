"""Shorts v2 для World Metal Empire: 1080x1920, крупный арт, хук сверху, строки песни по времени.

Использование: python render_shorts_v2.py jobs.json [имя_файла.mp4 ...]
jobs.json:
{
  "fonts": {"hook": "Cinzel-Bold.ttf", "lyric": "Oswald-Bold.ttf", "mark": "Cinzel-Bold.ttf", "cta": "Oswald-Bold.ttf"},
  "jobs": [{
     "src": "клип 1920x1080", "start": 94.3, "dur": 30, "out": "....mp4",
     "hook": ["СТРОКА 1", "СТРОКА 2"],             # 1–2 строки, вопрос или эмоция
     "lines": [{"t": 94.8, "text": "..."}, ...],  # время строк по треку (абсолютное)
     "crop": 0.66, "zoom": 0.06                     # доля ширины кадра, наезд за ролик
  }]
}
Слои: размытый фон -> арт (медленный наезд) -> оверлей из Pillow (хук, рамка, полоса прогресса,
строки песни, «FULL SONG ↓» в последние 2,6 с, водяной знак). Звук: loudnorm −14 LUFS в два прохода.
Кодек h264_mf (в ffmpeg D.A.V.E. нет libx264). Старый render_shorts.py не трогаем.
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
ART_Y = 470                 # верх арта
GOLD = (226, 182, 82)
WHITE = (255, 255, 255)
SAFE_L, SAFE_R = 60, 940    # справа в Shorts кнопки — текст строк держим левее
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")


def font(name, size):
    p = name if os.path.isabs(name) else os.path.join(FONT_DIR, name)
    return ImageFont.truetype(p, size)


def spaced_width(f, text, track):
    return sum(f.getlength(ch) for ch in text) + track * max(0, len(text) - 1)


def draw_spaced(d, xy, text, f, fill, track, stroke=0, stroke_fill=(0, 0, 0)):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += f.getlength(ch) + track


def shadowed(layer_fn, blur=10, alpha=170, offset=(0, 4)):
    """Рисует текст на отдельном слое и подкладывает мягкую тень."""
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer_fn(ImageDraw.Draw(txt))
    a = txt.split()[3]
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: v * alpha // 255))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.alpha_composite(sh, offset)
    base.alpha_composite(txt)
    return base


def wrap(f, text, maxw):
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def balanced_two(f, text, maxw):
    """Если строка не влезает — делим на две примерно равные части по словам."""
    if f.getlength(text) <= maxw:
        return [text]
    words = text.split()
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        m = max(f.getlength(a), f.getlength(b))
        if best is None or m < best[0]:
            best = (m, [a, b])
    return best[1]


def static_layer(job, fonts, art_h):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # хук: 1–2 строки, Cinzel с разрядкой, вторая строка — золотом
    hook = [h for h in job.get("hook", []) if h][:2]
    size = 92
    track_k = 0.08
    while size > 50:
        f = font(fonts["hook"], size)
        if all(spaced_width(f, h, size * track_k) <= W - 120 for h in hook):
            break
        size -= 4
    f = font(fonts["hook"], size)
    lh = int(size * 1.18)
    total = lh * len(hook)
    y0 = 300 - total // 2

    def hook_fn(d):
        for i, h in enumerate(hook):
            tw = spaced_width(f, h, size * track_k)
            col = WHITE if (i == 0 or len(hook) == 1) else GOLD
            draw_spaced(d, ((W - tw) / 2, y0 + i * lh), h, f, col, size * track_k, stroke=3)
    img.alpha_composite(shadowed(hook_fn, blur=12, alpha=200))
    d = ImageDraw.Draw(img)
    # тонкие золотые линии по краям арта
    d.rectangle([0, ART_Y - 3, W, ART_Y - 1], fill=GOLD + (170,))
    d.rectangle([0, ART_Y + art_h, W, ART_Y + art_h + 1], fill=GOLD + (120,))
    # водяной знак — внутри арта, левый верхний угол
    fm = font(fonts["mark"], 26)
    mark = "WORLD METAL EMPIRE"
    draw_spaced(d, (34, ART_Y + 22), mark, fm, (255, 255, 255, 150), 26 * 0.18, stroke=1, stroke_fill=(0, 0, 0, 120))
    return img


def lyric_image(text, fonts):
    size = 66
    while size > 46:
        f = font(fonts["lyric"], size)
        parts = balanced_two(f, text, SAFE_R - SAFE_L)
        if len(parts) <= 2 and all(f.getlength(p) <= SAFE_R - SAFE_L for p in parts):
            break
        size -= 4
    f = font(fonts["lyric"], size)
    parts = balanced_two(f, text, SAFE_R - SAFE_L)
    lh = int(size * 1.12)
    cx = (SAFE_L + SAFE_R) / 2

    def fn(d):
        y = 1475 - (lh * len(parts)) // 2
        for p in parts:
            tw = f.getlength(p)
            d.text((cx - tw / 2, y), p, font=f, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
            y += lh
    return shadowed(fn, blur=9, alpha=200)


def cta_image(fonts):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(fonts["cta"], 58)
    text = "FULL SONG"
    tw = f.getlength(text)
    aw = 46
    gap = 18
    bw, bh = int(tw + gap + aw + 70), 96
    cx = (SAFE_L + SAFE_R) // 2
    x0, y0 = cx - bw // 2, 1262
    d.rounded_rectangle([x0 + 4, y0 + 6, x0 + bw + 4, y0 + bh + 6], 22, fill=(0, 0, 0, 120))
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 22, fill=GOLD + (245,))
    ty = y0 + (bh - 58 * 1.25) / 2 - 4
    d.text((x0 + 35, ty), text, font=f, fill=(18, 12, 6))
    # стрелка вниз рисуется фигурой — не зависит от глифов шрифта
    ax = x0 + 35 + tw + gap
    ay = y0 + 20
    d.rectangle([ax + aw / 2 - 6, ay, ax + aw / 2 + 6, ay + 34], fill=(18, 12, 6))
    d.polygon([(ax, ay + 28), (ax + aw, ay + 28), (ax + aw / 2, ay + 58)], fill=(18, 12, 6))
    return img


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def schedule(job):
    """Строки -> интервалы показа относительно начала ролика."""
    st, dur = job["start"], job["dur"]
    ls = sorted([l for l in job.get("lines", []) if l.get("t") is not None], key=lambda l: l["t"])
    out = []
    for i, l in enumerate(ls):
        a = l["t"] - st - 0.12
        nxt = ls[i + 1]["t"] - st - 0.12 if i + 1 < len(ls) else dur
        b = min(nxt, a + l.get("hold", 4.6), dur)  # плашка FULL SONG выше строк — не мешает
        if b <= 0.15 or a >= dur - 0.3:
            continue
        out.append((max(0.0, a), b, l["text"]))
    return out


def loudnorm_params(job):
    cmd = ["ffmpeg", "-hide_banner", "-v", "info", "-ss", str(job["start"]), "-t", str(job["dur"]), "-i", job["src"],
           "-vn", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    return json.loads(m.group(0)) if m else None


def render(job, fonts):
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    dur = float(job["dur"])
    n = int(round(dur * FPS))
    crop = job.get("crop", 0.66)
    zoom = job.get("zoom", 0.06)
    full_h = W / (16 / 9 * crop)  # исходник 16:9
    art_h = int(round(min(full_h, 930) / 2) * 2)  # ниже арта — строки песни (y≈1440), не залезать
    crop_hf = round(art_h / full_h, 4)
    static = static_layer(job, fonts, art_h)
    lines = schedule(job)
    lyr_imgs = [lyric_image(t, fonts) for _, _, t in lines]
    cta = cta_image(fonts)
    cta_start = dur - 2.6

    ln = loudnorm_params(job)
    if ln:
        af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={ln['input_i']}:measured_TP={ln['input_tp']}:"
              f"measured_LRA={ln['input_lra']}:measured_thresh={ln['input_thresh']}:offset={ln['target_offset']}:linear=true")
    else:
        af = "loudnorm=I=-14:TP=-1.5:LRA=11"
    af = f"[0:a]{af},afade=t=in:st=0:d=0.12,afade=t=out:st={max(0.0, dur - 0.9):.2f}:d=0.9,aresample=48000[aout]"
    vf = (
        f"[0:v]fps={FPS},split=2[a][b];"
        f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},scale=270:480,gblur=sigma=7,"
        f"scale={W}:{H},colorlevels=romax=0.55:gomax=0.55:bomax=0.6[bg];"
        f"[b]crop=iw*{crop}:ih*{crop_hf},scale={W * 2}:{art_h * 2},"
        f"zoompan=z='1+{zoom}*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{art_h}:fps={FPS}[fg];"
        f"[bg][fg]overlay=0:{ART_Y}[base];"
        f"[1:v]format=rgba[ov];[base][ov]overlay=0:0:format=auto,setsar=1,format=yuv420p[v]"
    )
    cmd = ["ffmpeg", "-v", "error", "-y",
           "-ss", str(job["start"]), "-t", str(dur), "-i", job["src"],
           "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[aout]", "-frames:v", str(n),
           "-c:v", "h264_mf", "-b:v", "10M", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", job["out"]]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    cache = {}
    bar_y = ART_Y + art_h + 4
    try:
        for i in range(n):
            t = i / FPS
            key = []
            # хук и рамка появляются за 0,25 с
            ha = ease(t / 0.25)
            key.append(round(ha, 2))
            act = None
            for k, (a, b, _) in enumerate(lines):
                if a <= t < b:
                    act = k
            if act is not None:
                a, b, _ = lines[act]
                fin = ease((t - a) / 0.14)
                fout = ease((b - t) / 0.10)
                key += [act, round(min(fin, fout), 2), round(fin, 2)]
            ca = ease((t - cta_start) / 0.3) if t >= cta_start else 0.0
            pulse = 0
            if ca > 0:
                pulse = int(6 * abs(((t - cta_start) * 1.6) % 2 - 1))
            key += [round(ca, 2), pulse]
            key = tuple(key)
            frame = cache.get(key)
            if frame is None:
                frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                if ha >= 0.999:
                    frame.alpha_composite(static)
                else:
                    s = static.copy()
                    s.putalpha(s.split()[3].point(lambda v, ha=ha: int(v * ha)))
                    frame.alpha_composite(s)
                if act is not None:
                    al, fin = key[2], key[3]
                    li = lyr_imgs[act]
                    if al < 0.999:
                        li = li.copy()
                        li.putalpha(li.split()[3].point(lambda v, al=al: int(v * al)))
                    frame.alpha_composite(li, (0, int(14 * (1 - fin))))
                if ca > 0:
                    c = cta
                    if ca < 0.999:
                        c = cta.copy()
                        c.putalpha(c.split()[3].point(lambda v, ca=ca: int(v * ca)))
                    frame.alpha_composite(c, (0, -pulse + int(20 * (1 - ca))))
                if len(cache) > 400:
                    cache.clear()
                cache[key] = frame
            # полоса прогресса рисуется на копии кадра
            fr = frame.copy()
            d = ImageDraw.Draw(fr)
            d.rectangle([0, bar_y, W, bar_y + 5], fill=(0, 0, 0, 110))
            d.rectangle([0, bar_y, int(W * (i + 1) / n), bar_y + 5], fill=GOLD + (235,))
            p.stdin.write(fr.tobytes())
        p.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    err = p.stderr.read().decode("utf-8", "replace")
    p.wait()
    ok = p.returncode == 0 and os.path.exists(job["out"]) and os.path.getsize(job["out"]) > 500_000
    print(("OK  " if ok else "FAIL"), os.path.basename(job["out"]), "" if ok else err[-800:], flush=True)
    return ok


def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    fonts = {"hook": "Cinzel-Bold.ttf", "lyric": "Oswald-Bold.ttf", "mark": "Cinzel-Bold.ttf", "cta": "Oswald-Bold.ttf"}
    fonts.update(cfg.get("fonts", {}))
    only = set(sys.argv[2:])
    res = [render(j, fonts) for j in cfg["jobs"] if not only or os.path.basename(j["out"]) in only]
    print(f"done {sum(res)}/{len(res)}")


if __name__ == "__main__":
    main()
