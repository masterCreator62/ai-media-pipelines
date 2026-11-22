"""Карточки глав 1920x1080 для длинных роликов (своя графика в стиле инфографики GAME PULSE).

Зачем: каждая глава длинного видео открывается собственной карточкой — меньше чужого футажа,
больше «существенного отличия» (правила YouTube о повторно используемом контенте).

from make_chapter_cards import chapter_card
chapter_card(path, kicker="CHAPTER 3", big="30 FPS", headline="The frame rate debate", color="#ff4040")
Безопасная зона: содержимое x 260..1660, y 150..900 (низ — субтитры, правый верх — водяной знак).
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1920, 1080
BG = (17, 12, 9)
F_IMPACT = "C:/Windows/Fonts/impact.ttf"
F_BLACK = "C:/Windows/Fonts/ariblk.ttf"
F_BOLD = "C:/Windows/Fonts/segoeuib.ttf"


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _fit(path, size, text, max_w, min_size=40):
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    while size > min_size and d.textlength(text, font=ImageFont.truetype(path, size)) > max_w:
        size -= 6
    return ImageFont.truetype(path, size)


def chapter_card(path, kicker, big, headline, color="#ff8a2a", label="GAME PULSE · GTA 6"):
    col = _rgb(color)
    im = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W // 2 - 700, 180, W // 2 + 700, 900), fill=tuple(int(c * 0.25) for c in col))
    im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(170)))
    d = ImageDraw.Draw(im)
    # тонкая рамка-сетка: узнаваемый стиль канала
    d.rounded_rectangle((200, 110, W - 200, 930), 36, outline=tuple(int(c * 0.45) for c in col), width=3)
    d.text((W // 2, 175), "•  " + label.upper(), font=ImageFont.truetype(F_BOLD, 34), fill=(200, 140, 90), anchor="mm")
    d.text((W // 2, 260), kicker.upper(), font=ImageFont.truetype(F_BLACK, 44), fill=col, anchor="mm")
    bf = _fit(F_IMPACT, 260, big, 1350, 120)
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(layer).text((W // 2, 500), big, font=bf, fill=tuple(int(c * 0.55) for c in col), anchor="mm")
    im = ImageChops.add(im, layer.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(im)
    d.text((W // 2, 500), big, font=bf, fill=col, anchor="mm")
    hf = _fit(F_BLACK, 70, headline, 1380, 40)
    d.text((W // 2, 760), headline, font=hf, fill=(245, 240, 235), anchor="mm")
    im.save(path)
    return path


if __name__ == "__main__":
    import sys
    chapter_card(sys.argv[1], "CHAPTER 1", "7.91M", "The biggest launch in streaming history")
