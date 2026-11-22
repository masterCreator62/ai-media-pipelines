"""Инфографика своими силами: карточки-таймлайн в стиле «светящиеся узлы на тёмном фоне» -> script.json для make_news_video.py.

Зачем: ролик целиком из собственной графики — без чужого видео и пресс-кита, поэтому без риска
Content ID и с «существенным отличием» по правилам YouTube о повторно используемом контенте.

python make_infographic_cards.py spec.json
spec.json:
{
  "out_video": "H:/.../GP_I01.mp4", "work_dir": "H:/.../cards_GP_I01",
  "label": "GTA 6 · THE 13-YEAR WAIT", "hook": "THE 13-YEAR WAIT", "watermark": "GAME PULSE",
  "voice": "en-US-AndrewNeural", "rate": "+6%",
  "nodes": [{"label": "2013", "color": "#3da5ff"}, ...],
  "segments": [
    {"text": "фраза диктора", "card": {"type": "title", "big": "13", "sub": "YEARS", "line": "2013 -> 2026", "color": "#ff8a2a"}},
    {"text": "...", "card": {"type": "node", "node": 0, "big": "2013", "date": "SEPTEMBER 17, 2013", "headline": "..."}},
    {"text": "...", "card": {"type": "end", "big": "13 YEARS", "sub": "2 MONTHS", "line": "WORTH IT?", "color": "#b06bff"}}
  ],
  "sources": ["https://...", ...],
  "music": {"style": "calm_minor", "gain_db": -20},   необязательно: своя музыка (make_music.py)
  "sfx": true                                          необязательно: вжух + удар на смене карточки
}
Безопасная зона (с 20.11.2026, вариант «по центру»). Карточка 1460x1920 ложится в кадр 1:1 по вертикали
(y карточки = y кадра), по горизонтали видна полоса 1080 px; с motion=gentle всегда видно x 320..1140 карточки.
  • содержимое карточки: x 330..1130, y 230..1340 (центр композиции ≈ y 880 — оптический центр кадра);
  • субтитры: низ строки на y 1520 (sub_margin_v 400), кегль 84, бока 110 px — строка x 110..970, правая колонка кнопок Shorts свободна;
  • ниже y 1536 (нижние 20 %) — подпись и кнопки Shorts, туда ничего не ставим; водяной знак — y 70, хук — y 370 (первые 3,2 с).
"""
import json, os, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CW, CH = 1460, 1920
CX = CW // 2
BG = (17, 12, 9)
# вертикальная сетка карточки (см. «Безопасная зона» выше)
Y_LABEL, Y_CHAIN, Y_BIG, Y_DATE, Y_HEAD = 250, 520, 850, 1050, 1150
F_IMPACT = "C:/Windows/Fonts/impact.ttf"
F_BLACK = "C:/Windows/Fonts/ariblk.ttf"
F_BOLD = "C:/Windows/Fonts/segoeuib.ttf"


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def font(path, size):
    return ImageFont.truetype(path, size)


def fit_font(path, size, text, max_w=780, min_size=90):
    """Уменьшает кегль, пока текст не влезет в безопасную ширину (кириллица шире латиницы)."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while size > min_size and probe.textlength(text, font=font(path, size)) > max_w:
        size -= 10
    return font(path, size)


def base_canvas(accent):
    im = Image.new("RGB", (CW, CH), BG)
    glow = Image.new("RGB", (CW, CH), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((CX - 520, 540, CX + 520, 1300), fill=tuple(int(c * 0.22) for c in accent))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return _add(im, glow)


def _add(a, b):
    from PIL import ImageChops
    return ImageChops.add(a, b)


def glow_text(im, xy, text, fnt, color, anchor="mm", blur=26, strength=1):
    layer = Image.new("RGB", im.size, (0, 0, 0))
    dim = tuple(int(c * 0.55) for c in color)  # приглушённое свечение: цифры остаются читаемыми
    ImageDraw.Draw(layer).text(xy, text, font=fnt, fill=dim, anchor=anchor)
    g = layer.filter(ImageFilter.GaussianBlur(blur))
    for _ in range(strength):
        im = _add(im, g)
    ImageDraw.Draw(im).text(xy, text, font=fnt, fill=color, anchor=anchor)
    return im


def draw_label(im, label):
    d = ImageDraw.Draw(im)
    d.text((CX, Y_LABEL), "•  " + label.upper(), font=font(F_BOLD, 40), fill=(200, 140, 90), anchor="mm")
    return im


def draw_chain(im, nodes, cur):
    """Цепочка узлов: пройденные — с галочкой, текущий — светится, будущие — тусклые."""
    n = len(nodes)
    span = 700
    x0 = CX - span // 2
    step = span / (n - 1)
    y = Y_CHAIN
    d = ImageDraw.Draw(im)
    for i in range(n - 1):
        col = (150, 90, 45) if i < cur else (60, 48, 40)
        d.line((x0 + i * step + 34, y, x0 + (i + 1) * step - 34, y), fill=col, width=5)
    for i, nd in enumerate(nodes):
        x = x0 + i * step
        c = rgb(nd.get("color", "#ff8a2a"))
        if i == cur:
            layer = Image.new("RGB", im.size, (0, 0, 0))
            ImageDraw.Draw(layer).ellipse((x - 46, y - 46, x + 46, y + 46), fill=c)
            im = _add(im, layer.filter(ImageFilter.GaussianBlur(26)))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((x - 34, y - 34, x + 34, y + 34), 14, fill=(30, 22, 16), outline=c, width=6)
            d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=c)
        elif i < cur:
            d.rounded_rectangle((x - 30, y - 30, x + 30, y + 30), 12, fill=(36, 26, 18), outline=(170, 100, 45), width=4)
            d.line((x - 12, y, x - 3, y + 10, x + 14, y - 10), fill=(255, 150, 60), width=6)
        else:
            d.rounded_rectangle((x - 30, y - 30, x + 30, y + 30), 12, fill=(26, 20, 16), outline=(70, 56, 46), width=3)
        d.text((x, y + 66), nd["label"], font=font(F_BOLD, 30),
               fill=c if i == cur else ((190, 130, 80) if i < cur else (95, 80, 70)), anchor="mm")
    return im


def wrap(text, fnt, max_w, draw):
    words, lines, cur = text.split(" "), [], ""  # неразрывный пробел (\u00a0) склеивает дату
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    # разделитель «·» на краю строки после переноса не нужен
    return [ln.strip(" ·").strip() if ln.endswith("·") or ln.startswith("·") else ln for ln in lines]


def card_node(nodes, c):
    nd = nodes[c["node"]]
    col = rgb(c.get("color", nd.get("color", "#ff8a2a")))
    im = base_canvas(col)
    im = draw_label(im, SPEC["label"])
    im = draw_chain(im, nodes, c["node"])
    big = c.get("big", nd["label"])
    size = 300 if len(big) <= 4 else 230
    im = glow_text(im, (CX, Y_BIG), big, fit_font(F_IMPACT, size, big), col)
    d = ImageDraw.Draw(im)
    d.text((CX, Y_DATE), c["date"], font=fit_font(F_BOLD, 58, c["date"], min_size=36), fill=col, anchor="mm")
    hf = font(F_BLACK, 56)
    lines = wrap(c["headline"], hf, 800, d)
    y = Y_HEAD
    for ln in lines[:3]:
        d.text((CX, y), ln, font=hf, fill=(245, 240, 235), anchor="mm")
        y += 78
    return im


def card_big(c, nodes, done_all):
    col = rgb(c.get("color", "#ff8a2a"))
    im = base_canvas(col)
    im = draw_label(im, SPEC["label"])
    if done_all:
        im = draw_chain(im, nodes, len(nodes))
    size = 420 if len(c["big"]) <= 3 else 200
    im = glow_text(im, (CX, Y_BIG - 30), c["big"], fit_font(F_IMPACT, size, c["big"]), col, blur=34)
    d = ImageDraw.Draw(im)
    if c.get("sub"):
        d.text((CX, Y_BIG + 230), c["sub"], font=fit_font(F_BLACK, 96, c["sub"], min_size=50), fill=(245, 240, 235), anchor="mm")
    if c.get("line"):
        d.text((CX, Y_BIG + 360), c["line"], font=fit_font(F_BOLD, 64, c["line"], min_size=40), fill=col, anchor="mm")
    return im


def main():
    global SPEC
    SPEC = json.load(open(sys.argv[1], encoding="utf-8"))
    work = SPEC["work_dir"]
    os.makedirs(work, exist_ok=True)
    nodes = SPEC["nodes"]
    segs = []
    for i, seg in enumerate(SPEC["segments"]):
        c = seg["card"]
        if c["type"] == "node":
            im = card_node(nodes, c)
        else:
            im = card_big(c, nodes, c["type"] == "end")
        p = os.path.join(work, f"card_{i:02d}.png")
        im.save(p)
        segs.append({"text": seg["text"], "images": [p]})
    script = {"out": SPEC["out_video"], "format": "short", "voice": SPEC.get("voice", "en-US-AndrewNeural"),
              "rate": SPEC.get("rate", "+6%"), "hook": SPEC.get("hook", ""), "watermark": SPEC.get("watermark", "GAME PULSE"),
              "segments": segs,
              "sub_margin_v": SPEC.get("sub_margin_v", 400), "sub_margin_h": SPEC.get("sub_margin_h", 110), "sub_size": SPEC.get("sub_size", 84),
              "hook_y": SPEC.get("hook_y", 370), "motion": SPEC.get("motion", "gentle")}
    for k in ("music", "sfx", "sfx_gain_db"):
        if k in SPEC:
            script[k] = SPEC[k]
    sp = os.path.join(work, "script.json")
    json.dump(script, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("cards:", len(segs), "->", sp)
    if "--render" in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        subprocess.run([sys.executable, os.path.join(here, "make_news_video.py"), sp], check=True)


SPEC = {}
if __name__ == "__main__":
    main()
