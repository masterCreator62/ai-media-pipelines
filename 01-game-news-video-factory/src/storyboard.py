"""Раскадровка длинного видео: кадр каждые STEP секунд -> листы 8x6 с таймкодами (для выбора моментов).
python storyboard.py video.mp4 outdir [step]
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
step = float(sys.argv[3]) if len(sys.argv) > 3 else 8
os.makedirs(out, exist_ok=True)
r = subprocess.run(["ffmpeg", "-hide_banner", "-i", src], capture_output=True, text=True, encoding="utf-8", errors="replace")
import re
m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
ts = [i * step for i in range(int(dur // step))]

def grab(t):
    p = os.path.join(out, f"f_{int(t):05d}.jpg")
    if not os.path.exists(p):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", src, "-frames:v", "1", "-vf", "scale=320:-1", p])
    return t, p

with ThreadPoolExecutor(6) as ex:
    frames = list(ex.map(grab, ts))
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
per = 48
for s in range(0, len(frames), per):
    chunk = frames[s:s + per]
    sheet = Image.new("RGB", (8 * 320, 6 * 180), "black")
    d = ImageDraw.Draw(sheet)
    for k, (t, p) in enumerate(chunk):
        if not os.path.exists(p):
            continue
        im = Image.open(p).resize((320, 180))
        x, y = (k % 8) * 320, (k // 8) * 180
        sheet.paste(im, (x, y))
        lab = f"{int(t // 60)}:{int(t % 60):02d}"
        d.rectangle((x, y, x + 70, y + 26), fill="black")
        d.text((x + 4, y + 1), lab, fill="yellow", font=font)
    sheet.save(os.path.join(out, f"sheet_{s // per:02d}.jpg"), quality=85)
print(len(frames), "frames")
