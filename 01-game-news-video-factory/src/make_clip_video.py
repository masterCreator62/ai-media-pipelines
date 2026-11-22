"""Shorts/видео из видеофрагментов (официальные ролики Rockstar) + своя озвучка + субтитры по словам.

python make_clip_video.py job.json
job.json:
{
  "out": "H:/.../GP_C01.mp4", "format": "short" | "long", "voice": "en-US-AndrewNeural", "rate": "+10%",
  "hook": "ПЛАШКА", "watermark": "GAME PULSE", "game_volume": 0.22,
  "segments": [{"text": "фраза диктора", "clips": [{"src": "путь.mp4", "t": 123.4, "x": 0.5}]}]
}
Каждый сегмент длится столько, сколько звучит его фраза; клипы сегмента делят это время поровну.
x — центр вертикального кадра по ширине исходника (0 = левый край, 1 = правый), только для short.
"""
import json, os, shutil, subprocess, sys, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_news_video import synth, words_timed, make_ass

FPS = 30
GAP = 0.25


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd[:6]) + "...\n" + r.stderr[-1500:])


def main():
    job = sys.argv[1]
    cfg = json.load(open(job, encoding="utf-8"))
    fmt = cfg.get("format", "short")
    W, H = (1080, 1920) if fmt == "short" else (1920, 1080)
    out = cfg["out"]
    work = os.path.join(os.path.dirname(os.path.abspath(job)), os.path.splitext(os.path.basename(out))[0] + "_tmp")
    os.makedirs(work, exist_ok=True)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    voice, rate = cfg.get("voice", "en-US-AndrewNeural"), cfg.get("rate", "+10%")

    t0, words, voices, pieces, starts = 0.0, [], [], [], []
    for i, seg in enumerate(cfg["segments"]):
        starts.append(round(t0, 2))
        mp3 = os.path.join(work, f"a{i:02d}.mp3")
        sents = synth(seg["text"], voice, rate, mp3)
        wav = os.path.join(work, f"a{i:02d}.wav")
        run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "24000", "-ac", "1", wav])
        with wave.open(wav) as wf:
            d = wf.getnframes() / wf.getframerate()
        words += words_timed(sents, t0)
        voices.append(wav)
        L = d + GAP
        clips = seg["clips"]
        per = L / len(clips)
        for j, c in enumerate(clips):
            p = os.path.join(work, f"v{i:02d}_{j}.mp4")
            is_img = c["src"].lower().endswith((".png", ".jpg", ".jpeg"))  # своя карточка (глава, инфографика)
            if fmt == "short" and not is_img:
                x = float(c.get("x", 0.5))
                vf = f"crop=ih*9/16:ih:(iw-ih*9/16)*{x:.3f}:0,scale={W}:{H}:flags=lanczos"
            else:
                vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
            vf += f",fps={FPS},setsar=1,format=yuv420p"
            if is_img:
                run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{per:.3f}", "-i", c["src"],
                     "-f", "lavfi", "-t", f"{per:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
                     "-vf", vf, "-map", "0:v", "-map", "1:a", "-shortest",
                     "-c:v", "h264_mf", "-b:v", "20M", "-c:a", "aac", "-b:a", "192k", p])
            else:
                run(["ffmpeg", "-v", "error", "-y", "-ss", f"{c['t']:.3f}", "-t", f"{per:.3f}", "-i", c["src"],
                     "-vf", vf, "-af", "aresample=48000,aformat=channel_layouts=stereo",
                     "-c:v", "h264_mf", "-b:v", "20M", "-c:a", "aac", "-b:a", "192k", p])
            pieces.append(p)
        t0 += L
    total = t0

    sil = os.path.join(work, "sil.wav")
    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(GAP), sil])
    with open(os.path.join(work, "alist.txt"), "w", encoding="utf-8") as f:
        for a in voices:
            f.write(f"file '{a.replace(chr(92), '/')}'\nfile '{sil.replace(chr(92), '/')}'\n")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "alist.txt", "-ar", "48000", "-ac", "2", "voice.wav"], cwd=work)
    with open(os.path.join(work, "vlist.txt"), "w", encoding="utf-8") as f:
        for p in pieces:
            f.write(f"file '{p.replace(chr(92), '/')}'\n")

    # с 20.11.2026 задания могут задать безопасную зону Shorts (см. make_infographic_cards.py); без полей — как раньше
    make_ass(words, os.path.join(work, "subs.ass"), fmt, W, H, (), cfg.get("sub_margin_v", 560),
             cfg.get("sub_margin_h", 60), cfg.get("sub_size", 92))
    open(os.path.join(work, "hook.txt"), "w", encoding="utf-8").write(cfg.get("hook", ""))
    open(os.path.join(work, "wm.txt"), "w", encoding="utf-8").write(cfg.get("watermark", ""))
    shutil.copyfile("C:/Windows/Fonts/impact.ttf", os.path.join(work, "font.ttf"))
    vf = "subtitles=subs.ass"
    if fmt == "short" and cfg.get("hook"):
        vf += (",drawtext=fontfile=font.ttf:textfile=hook.txt:fontsize=88:fontcolor=black:box=1:boxcolor=0xFFD21F@1:boxborderw=28"
               f":x=(w-text_w)/2:y={cfg.get('hook_y', 300)}:enable='lt(t,3.2)'")
    if cfg.get("note"):  # постоянная плашка-оговорка (например «официальный трейлер, клипов с багами нет»)
        open(os.path.join(work, "note.txt"), "w", encoding="utf-8").write(cfg["note"])
        vf += (",drawtext=fontfile=font.ttf:textfile=note.txt:fontsize=34:fontcolor=white@0.85:box=1:boxcolor=black@0.45:boxborderw=12"
               f":x=(w-text_w)/2:y={cfg.get('note_y', 150)}")
    if cfg.get("watermark"):
        y = str(cfg.get("wm_y", "h-120")) if fmt == "short" else "40"
        x = "(w-text_w)/2" if fmt == "short" else "w-text_w-50"
        vf += f",drawtext=fontfile=font.ttf:textfile=wm.txt:fontsize=40:fontcolor=white@0.75:borderw=3:bordercolor=black@0.6:x={x}:y={y}"
    gv = float(cfg.get("game_volume", 0.22))
    fc = (f"[0:v]{vf},format=yuv420p[v];[0:a]volume={gv}[g];[1:a]volume=1.0[n];"
          f"[g][n]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "vlist.txt", "-i", "voice.wav",
         "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
         "-c:v", "h264_mf", "-b:v", "12M" if fmt == "short" else "10M", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", os.path.abspath(out)], cwd=work)
    ok = os.path.exists(out) and os.path.getsize(out) > 300_000
    print(("OK " if ok else "FAIL ") + out + f"  {total:.1f}s")
    if ok:
        json.dump({"total": total, "starts": starts}, open(os.path.splitext(out)[0] + "_timing.json", "w"), indent=1)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
