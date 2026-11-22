"""Оформление канала GAME PULSE: аватар 800x800, баннер 2560x1440, водяной знак 150x150, превью длинного ролика 1280x720."""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = "H:/GameClips_Канал/Оформление"
os.makedirs(OUT, exist_ok=True)
IMPACT = "C:/Windows/Fonts/impact.ttf"
BLACK = "C:/Windows/Fonts/ariblk.ttf" if os.path.exists("C:/Windows/Fonts/ariblk.ttf") else "C:/Windows/Fonts/arialbd.ttf"
Y, M, C = (255, 210, 31), (255, 46, 136), (0, 229, 255)

def gradient(w, h, c1=(10, 8, 24), c2=(46, 10, 60)):
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(0, w, 1):
            t = (x / w * 0.5 + y / h * 0.5)
            px[x, y] = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return im

def pulse(draw, x0, y0, w, h, width, color, s0=0.38, s1=0.62):
    pts, n = [], 400
    for i in range(n + 1):
        t = i / n
        x = x0 + t * w
        # плоская линия - всплеск ЭКГ - плоская линия
        if s0 < t < s1:
            k = (t - s0) / (s1 - s0)
            v = [0, -0.25, 0.9, -1.0, 0.35, 0][min(5, int(k * 6))]
            y = y0 - v * h / 2
        else:
            y = y0
        pts.append((x, y))
    draw.line(pts, fill=color, width=width, joint="curve")

def glow(im, layer, radius):
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    im.paste(Image.composite(g, im, g.convert("L")), (0, 0))
    im.paste(layer, (0, 0), layer)

# аватар
A = 800
av = gradient(A, A)
lay = Image.new("RGBA", (A, A), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
d.ellipse((40, 40, A - 40, A - 40), outline=M + (255,), width=22)
pulse(d, 110, 470, 580, 300, 26, C + (255,))
f = ImageFont.truetype(IMPACT, 210)
d.text((A / 2, 300), "GP", font=f, fill=Y + (255,), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, 255))
glow(av, lay, 14)
av.save(f"{OUT}/avatar_800.png")

# водяной знак (кнопка подписки в видео): 150x150, прозрачный фон
wm = Image.new("RGBA", (150, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(wm)
d.ellipse((4, 4, 146, 146), fill=(12, 10, 28, 235), outline=M + (255,), width=6)
d.text((75, 70), "GP", font=ImageFont.truetype(IMPACT, 64), fill=Y + (255,), anchor="mm")
wm.save(f"{OUT}/watermark_150.png")

# баннер 2560x1440, безопасная зона 1546x423 по центру
BW, BH = 2560, 1440
bn = gradient(BW, BH)
lay = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
for i in range(0, BW, 64):
    d.line([(i, 0), (i - 600, BH)], fill=(255, 255, 255, 10), width=2)
pulse(d, 0, 900, BW, 420, 12, C + (200,), 0.82, 0.90)
d.text((BW / 2, 650), "GAME PULSE", font=ImageFont.truetype(IMPACT, 230), fill=(255, 255, 255, 255), anchor="mm",
       stroke_width=8, stroke_fill=(0, 0, 0, 255))
d.text((BW / 2, 805), "DAILY GAMING NEWS  •  TOP 10s  •  SECRETS", font=ImageFont.truetype(BLACK, 62), fill=Y + (255,), anchor="mm",
       stroke_width=4, stroke_fill=(0, 0, 0, 255))
glow(bn, lay, 10)
bn.save(f"{OUT}/banner_2560x1440.png")

# превью для длинного ролика
src = sys.argv[1] if len(sys.argv) > 1 else None
if src:
    th = Image.open(src).convert("RGB")
    th = th.resize((1280, int(th.height * 1280 / th.width)), Image.LANCZOS).crop((0, 0, 1280, 720))
    dark = Image.new("RGBA", (1280, 720), (0, 0, 0, 0)); dd = ImageDraw.Draw(dark)
    for x in range(700):
        dd.line([(x, 0), (x, 720)], fill=(0, 0, 0, int(200 * (1 - x / 700))))
    th.paste(dark, (0, 0), dark)
    d = ImageDraw.Draw(th)
    d.text((50, 70), "GTA 6", font=ImageFont.truetype(IMPACT, 190), fill=Y, stroke_width=8, stroke_fill=(0, 0, 0))
    d.text((55, 300), "EVERYTHING", font=ImageFont.truetype(IMPACT, 110), fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
    d.text((55, 420), "YOU NEED", font=ImageFont.truetype(IMPACT, 110), fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
    d.text((55, 540), "TO KNOW", font=ImageFont.truetype(IMPACT, 110), fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
    d.rounded_rectangle((1010, 40, 1240, 140), radius=18, fill=M)
    d.text((1125, 90), "99/100", font=ImageFont.truetype(IMPACT, 70), fill=(255, 255, 255), anchor="mm")
    th.save(f"{OUT}/thumb_GP_L01.jpg", quality=92)
print("ok")
