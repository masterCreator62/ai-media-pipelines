"""Рендер вертикальных Shorts 1080x1920 из горизонтальных видео.

Использование: python render_shorts.py jobs.json
jobs.json: {"font": "путь к .ttf", "jobs": [{"src", "start", "dur", "out", "top1", "top2", "bottom", "fps", "crop"}]}
Макет: размытый фон из того же кадра + картинка по центру (crop = доля ширины исходника),
крупный крючок сверху (2 строки), подпись внизу, нормализация громкости -14 LUFS.
"""
import json, os, subprocess, sys, shutil

def esc(p):
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")

def render(job, font, work):
    os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
    tid = os.path.splitext(os.path.basename(job["out"]))[0]
    files = {}
    for key in ("top1", "top2", "bottom"):
        fn = os.path.join(work, f"{tid}_{key}.txt")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(job.get(key, ""))
        files[key] = os.path.basename(fn)
    fps = job.get("fps", 30)
    crop = job.get("crop", 0.8)
    dur = job["dur"]
    fo = max(0.0, dur - 0.8)
    vf = (
        f"[0:v]split=2[a][b];"
        f"[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,scale=270:480,gblur=sigma=6,scale=1080:1920,colorlevels=romax=0.72:gomax=0.72:bomax=0.72[bg];"
        f"[b]crop=iw*{crop}:ih,scale=1080:-2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2+40,"
        f"drawtext=fontfile=font.ttf:textfile={files['top1']}:fontsize=104:fontcolor=white:borderw=7:bordercolor=black:x=(w-text_w)/2:y=230,"
        f"drawtext=fontfile=font.ttf:textfile={files['top2']}:fontsize=78:fontcolor=0xFFD21F:borderw=6:bordercolor=black:x=(w-text_w)/2:y=350,"
        f"drawtext=fontfile=font.ttf:textfile={files['bottom']}:fontsize=50:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=1600,"
        f"fps={fps},fade=t=in:st=0:d=0.25,fade=t=out:st={fo:.2f}:d=0.8,setsar=1,format=yuv420p[v]"
    )
    af = f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.3,afade=t=out:st={max(0.0, dur-1.2):.2f}:d=1.2[aout]"
    br = "14M" if fps >= 50 else "10M"
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-ss", str(job["start"]), "-t", str(dur), "-i", job["src"],
        "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[aout]",
        "-c:v", "h264_mf", "-b:v", br, "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", job["out"],
    ]
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = r.returncode == 0 and os.path.exists(job["out"]) and os.path.getsize(job["out"]) > 500_000
    print(("OK  " if ok else "FAIL"), job["out"], (r.stderr[-600:] if not ok else ""), flush=True)
    return ok

def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    work = os.path.dirname(os.path.abspath(sys.argv[1]))
    shutil.copyfile(cfg["font"], os.path.join(work, "font.ttf"))
    only = sys.argv[2:] or None
    res = [render(j, cfg["font"], work) for j in cfg["jobs"] if not only or os.path.basename(j["out"]) in only]
    print(f"done {sum(res)}/{len(res)}")

if __name__ == "__main__":
    main()
