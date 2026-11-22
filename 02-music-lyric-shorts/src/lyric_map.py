"""Карта слов песни во времени через транскрипцию D.A.V.E. окнами.

Использование: python lyric_map.py <out_dir> <video_or_audio> [<video_or_audio> ...]
Для каждого файла: аудио -> окна 2.5 с с шагом 1.25 с -> текст каждого окна.
Результат: <out_dir>/<basename>.windows.json  [{"t0","t1","text"}...]
Повторный запуск продолжает с места остановки (кэш по окнам).
"""
import json, os, subprocess, sys, tempfile, wave

WIN, STEP = 2.5, 1.25
APP = os.environ["APP_EXECUTABLE"]


def transcribe(path):
    for attempt in range(3):
        r = subprocess.run([APP, "--transcription-client", path], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        out = (r.stdout or "").strip()
        try:
            j = json.loads(out.splitlines()[-1])
        except Exception:
            continue
        if j.get("status") == "ready":
            return j.get("text", "")
        jid = j.get("job_id")
        while j.get("status") == "queued" and jid:
            r = subprocess.run([APP, "--transcription-client-status", jid], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=180)
            j = json.loads(r.stdout.strip().splitlines()[-1])
        if j.get("status") == "ready":
            return j.get("text", "")
    return None


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, "_chunks")
    os.makedirs(work, exist_ok=True)
    for src in sys.argv[2:]:
        base = os.path.splitext(os.path.basename(src))[0]
        jpath = os.path.join(out_dir, base + ".windows.json")
        done = json.load(open(jpath, encoding="utf-8")) if os.path.exists(jpath) else []
        have = {round(w["t0"], 2) for w in done}
        wav = os.path.join(work, base + ".wav")
        if not os.path.exists(wav):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
        with wave.open(wav) as w:
            dur = w.getnframes() / w.getframerate()
        t = 0.0
        while t + 1.0 < dur:
            if round(t, 2) not in have:
                c = os.path.join(work, "chunk.wav")
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-t", str(WIN), "-i", wav, c], check=True)
                txt = transcribe(c)
                done.append({"t0": round(t, 2), "t1": round(min(t + WIN, dur), 2), "text": txt if txt is not None else ""})
                if len(done) % 10 == 0:
                    json.dump(done, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
            t += STEP
        done.sort(key=lambda w: w["t0"])
        json.dump(done, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        print("OK", base, len(done), flush=True)


if __name__ == "__main__":
    main()
