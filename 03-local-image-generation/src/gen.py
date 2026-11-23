r"""Локальная генерация картинок через ComfyUI (RTX 3060 Ti, всё на диске H).

Примеры:
  python gen.py "neon samurai cat, youtube thumbnail" --preset cover
  python gen.py "cute candy flower icon, game asset" --preset square --n 4
  python gen.py "..." --model flux --seed 42 --out H:\RobloxSweetGarden\art
  python gen.py --jobs H:\ComfyUI\jobs\example.json      # серия из файла
  python gen.py --start | --stop | --status                # управление сервером

Только стандартная библиотека Python: работает из встроенного Python D.A.V.E. и из python_embeded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(r"H:\ComfyUI")
PORTABLE = ROOT / "portable"
PY_EMB = PORTABLE / "python_embeded" / "python.exe"
MAIN = PORTABLE / "ComfyUI" / "main.py"
OUTPUT = ROOT / "output"
LOGS = ROOT / "logs"
HOST, PORT = "127.0.0.1", 8188
URL = f"http://{HOST}:{PORT}"
TE_DEVICE = os.environ.get("COMFY_TE_DEVICE", "default")  # cpu | default
TE_FILE = os.environ.get("COMFY_TE_FILE", "qwen_3_4b_fp8_mixed.safetensors")  # текстовый кодировщик Z-Image

PRESETS = {  # стороны кратны 16
    "cover": (1280, 720),      # обложка YouTube
    "square": (1024, 1024),    # иконка, аватар, ассет
    "shorts": (864, 1536),     # вертикаль 9:16 (потом апскейл до 1080x1920)
    "wide": (1344, 768),
    "portrait": (896, 1152),
}

MODELS = {
    "zimage": {
        "license": "Apache-2.0 (Tongyi-MAI/Z-Image-Turbo), коммерция разрешена",
        "steps": 8,
    },
    "flux": {
        "license": "Apache-2.0 (black-forest-labs/FLUX.1-schnell), коммерция разрешена",
        "steps": 4,
    },
}


# ---------------------------------------------------------------- сервер
def server_up(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(URL + "/system_stats", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


TASK = r"\DAVE\ComfyUI Server"  # задание планировщика: pythonw server_launch.py


def start_server(wait: int = 240) -> None:
    """Сервер запускается заданием планировщика Windows, а не дочерним процессом:
    так он живёт отдельно от чата/скрипта (D.A.V.E. останавливает тяжёлые процессы своих команд)."""
    if server_up():
        print("ComfyUI уже работает:", URL)
        return
    r = subprocess.run(["schtasks", "/Run", "/TN", TASK], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Не удалось запустить задание {TASK}: {r.stderr.strip() or r.stdout.strip()}")
    t0 = time.time()
    while time.time() - t0 < wait:
        if server_up():
            print(f"ComfyUI запущен за {time.time() - t0:.0f} с: {URL}")
            return
        time.sleep(2)
    sys.exit(f"ComfyUI не ответил за {wait} с; см. {LOGS / 'server.log'}")


def stop_server() -> None:
    pidf = LOGS / "server.pid"
    subprocess.run(["schtasks", "/End", "/TN", TASK], capture_output=True)
    if pidf.exists():
        pid = pidf.read_text().strip()
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
        pidf.unlink(missing_ok=True)
    print("ComfyUI остановлен" if not server_up(3) else "ComfyUI всё ещё отвечает — проверьте процессы")


def free_vram() -> None:
    """Выгрузить модели из видеопамяти (сервер остаётся работать)."""
    req = urllib.request.Request(URL + "/free", data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


# ---------------------------------------------------------------- воркфлоу
def wf_zimage(prompt: str, w: int, h: int, seed: int, steps: int, prefix: str) -> dict:
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": TE_FILE, "type": "lumina2", "device": TE_DEVICE}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
                                                   "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": 1.0,
                                                   "sampler_name": "res_multistep", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def wf_flux(prompt: str, w: int, h: int, seed: int, steps: int, prefix: str) -> dict:
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "flux1-schnell-fp8.safetensors"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["1", 1], "text": prompt}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptySD3LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0],
                                                   "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": 1.0,
                                                   "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["1", 2]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


BUILDERS = {"zimage": wf_zimage, "flux": wf_flux}


# ---------------------------------------------------------------- генерация
def post(path: str, data: dict) -> dict:
    req = urllib.request.Request(URL + path, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"ComfyUI отклонил задание ({e.code}): {e.read().decode('utf-8', 'replace')[:2000]}")


def get(path: str) -> dict:
    with urllib.request.urlopen(URL + path, timeout=60) as r:
        return json.loads(r.read())


def slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:n].rstrip("-") or "img")


def generate(prompt: str, model: str = "zimage", w: int = 1024, h: int = 1024, seed: int | None = None,
             steps: int | None = None, name: str | None = None, out: str | None = None,
             timeout: int = 900) -> list[Path]:
    if model not in BUILDERS:
        sys.exit(f"Неизвестная модель {model}; есть: {', '.join(BUILDERS)}")
    w, h = (w // 16) * 16, (h // 16) * 16
    seed = random.randint(0, 2**48) if seed is None else seed
    steps = steps or MODELS[model]["steps"]
    day = dt.date.today().isoformat()
    prefix = f"gen/{day}/{name or slug(prompt)}_{model}_s{seed}"
    wf = BUILDERS[model](prompt, w, h, seed, steps, prefix)
    t0 = time.time()
    pid = post("/prompt", {"prompt": wf, "client_id": str(uuid.uuid4()), "extra_data": {}})["prompt_id"]
    while True:
        hist = get(f"/history/{pid}")
        if pid in hist:
            item = hist[pid]
            st = item.get("status", {})
            if st.get("status_str") == "error":
                msgs = [m for m in st.get("messages", []) if m[0] == "execution_error"]
                sys.exit(f"Ошибка генерации: {json.dumps(msgs, ensure_ascii=False)[:2000]}")
            break
        if time.time() - t0 > timeout:
            sys.exit(f"Нет результата за {timeout} с (задание {pid})")
        time.sleep(0.5)
    secs = time.time() - t0
    files = []
    for node in item["outputs"].values():
        for im in node.get("images", []):
            p = OUTPUT / im.get("subfolder", "") / im["filename"]
            if out:
                Path(out).mkdir(parents=True, exist_ok=True)
                dst = Path(out) / im["filename"]
                shutil.copy2(p, dst)
                p = dst
            files.append(p)
    rec = {"time": dt.datetime.now().isoformat(timespec="seconds"), "model": model, "license": MODELS[model]["license"],
           "prompt": prompt, "seed": seed, "steps": steps, "size": [w, h], "seconds": round(secs, 1),
           "files": [str(f) for f in files]}
    with open(OUTPUT / "gen_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    for f in files:
        print(f"{f}  ({secs:.1f} с, {model}, seed {seed}, {w}x{h})")
    return files


def main() -> None:
    ap = argparse.ArgumentParser(description="Генерация картинок локально через ComfyUI")
    ap.add_argument("prompt", nargs="?", help="описание картинки (лучше по-английски)")
    ap.add_argument("--model", default="zimage", choices=list(BUILDERS), help="zimage (по умолчанию) или flux")
    ap.add_argument("--preset", choices=list(PRESETS), help="cover | square | shorts | wide | portrait")
    ap.add_argument("--w", type=int); ap.add_argument("--h", type=int)
    ap.add_argument("--seed", type=int); ap.add_argument("--steps", type=int)
    ap.add_argument("--n", type=int, default=1, help="сколько вариантов (seed подряд)")
    ap.add_argument("--name", help="префикс имени файла")
    ap.add_argument("--out", help="куда дополнительно скопировать PNG (по умолчанию H:\\ComfyUI\\output\\gen\\<дата>)")
    ap.add_argument("--jobs", help="JSON-файл со списком заданий [{prompt, model, preset, seed, n, name, out}]")
    ap.add_argument("--start", action="store_true"); ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true"); ap.add_argument("--free", action="store_true",
                                                                         help="выгрузить модели из видеопамяти")
    a = ap.parse_args()
    if a.stop:
        return stop_server()
    if a.status:
        print("работает" if server_up() else "не запущен", URL)
        if server_up():
            dev = get("/system_stats")["devices"][0]
            print(f"{dev['name']}: свободно VRAM {dev['vram_free']/2**30:.1f} из {dev['vram_total']/2**30:.1f} ГБ")
        return
    start_server()
    if a.start:
        return
    if a.free:
        free_vram(); print("видеопамять освобождена"); return
    jobs = []
    if a.jobs:
        jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    elif a.prompt:
        jobs = [{"prompt": a.prompt, "model": a.model, "preset": a.preset, "w": a.w, "h": a.h, "seed": a.seed,
                 "steps": a.steps, "n": a.n, "name": a.name, "out": a.out}]
    else:
        ap.error("нужен prompt или --jobs")
    for j in jobs:
        w, h = PRESETS.get(j.get("preset") or "square")
        w, h = j.get("w") or w, j.get("h") or h
        seed = j.get("seed")
        base = random.randint(0, 2**48) if seed is None else seed
        for i in range(j.get("n") or 1):
            generate(j["prompt"], j.get("model") or "zimage", w, h, base + i, j.get("steps"), j.get("name"), j.get("out"))


if __name__ == "__main__":
    main()
