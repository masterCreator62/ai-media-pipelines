"""Нарезка горизонтальных сегментов 1920x1080 с подписью в углу (для сборки в CapCut).

python cut_segments.py segments.json
segments.json: {"font": "...ttf", "fps": 60, "segments": [{"src", "start", "dur", "out", "label"}]}
"""
import json, os, shutil, subprocess, sys

def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    work = os.path.dirname(os.path.abspath(sys.argv[1]))
    shutil.copyfile(cfg["font"], os.path.join(work, "font.ttf"))
    fps = cfg.get("fps", 60)
    ok = 0
    for i, s in enumerate(cfg["segments"]):
        os.makedirs(os.path.dirname(s["out"]), exist_ok=True)
        tf = f"seg_{i}.txt"
        open(os.path.join(work, tf), "w", encoding="utf-8").write(s.get("label", ""))
        d = s["dur"]
        label = ""
        if s.get("label"):
            label = (f",drawtext=fontfile=font.ttf:textfile={tf}:fontsize=84:fontcolor=white:borderw=6:bordercolor=black"
                     f":box=1:boxcolor=black@0.45:boxborderw=24:x=60:y=60:enable='lt(t,5)'")
        vf = (f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={fps}{label},"
              f"fade=t=in:st=0:d=0.3,fade=t=out:st={d-0.4:.2f}:d=0.4,setsar=1,format=yuv420p")
        af = f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.3,afade=t=out:st={d-0.5:.2f}:d=0.5"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(s["start"]), "-t", str(d), "-i", s["src"],
               "-vf", vf, "-af", af, "-c:v", "h264_mf", "-b:v", cfg.get("bitrate", "16M"),
               "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", s["out"]]
        r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
        good = r.returncode == 0 and os.path.exists(s["out"]) and os.path.getsize(s["out"]) > 300_000
        ok += good
        print("OK  " if good else "FAIL", s["out"], "" if good else r.stderr[-500:], flush=True)
    print(f"done {ok}/{len(cfg['segments'])}")

if __name__ == "__main__":
    main()
