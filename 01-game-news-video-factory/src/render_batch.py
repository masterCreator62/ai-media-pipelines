"""Рендер списка заданий по очереди: спецификация инфографики (есть "card" в сегментах) -> make_infographic_cards --render,
задание с клипами -> make_clip_video. python render_batch.py jobs\\A.json jobs\\B.json ...  (лог — в stdout)"""
import json, os, subprocess, sys, time

here = os.path.dirname(os.path.abspath(__file__))
for job in sys.argv[1:]:
    cfg = json.load(open(job, encoding="utf-8"))
    info = any("card" in s for s in cfg["segments"])
    script = "make_infographic_cards.py" if info else "make_clip_video.py"
    args = [sys.executable, os.path.join(here, script), job] + (["--render"] if info else [])
    t = time.time()
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(f"[{time.strftime('%H:%M:%S')}] {os.path.basename(job)} rc={r.returncode} {time.time() - t:.0f}s", flush=True)
    print((r.stdout[-600:] + r.stderr[-1500:]).strip(), flush=True)
print("BATCH DONE", flush=True)
