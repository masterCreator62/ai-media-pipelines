r"""Запуск сервера ComfyUI без окон. Вызывается заданием планировщика Windows «DAVE\ComfyUI Server»
(pythonw.exe H:\ComfyUI\server_launch.py), чтобы сервер жил отдельно от чата D.A.V.E.
Все кэши и временные файлы — на диске H.
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(r"H:\ComfyUI")
PORTABLE = ROOT / "portable"
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"

for d in (LOGS, CACHE, ROOT / "tmp", ROOT / "output"):
    d.mkdir(parents=True, exist_ok=True)

env = os.environ.copy()
env.update({
    "HF_HOME": str(CACHE / "huggingface"),
    "TORCH_HOME": str(CACHE / "torch"),
    "TRITON_CACHE_DIR": str(CACHE / "triton"),
    "CUDA_CACHE_PATH": str(CACHE / "cuda"),
    "XDG_CACHE_HOME": str(CACHE),
    "PIP_CACHE_DIR": str(CACHE / "pip"),
    "TEMP": str(ROOT / "tmp"),
    "TMP": str(ROOT / "tmp"),
    "PYTHONUTF8": "1",
})
args = [str(PORTABLE / "python_embeded" / "python.exe"), "-s", str(PORTABLE / "ComfyUI" / "main.py"),
        "--windows-standalone-build",
        "--listen", "127.0.0.1", "--port", "8188",
        "--disable-auto-launch",       # не открывать браузер
        "--disable-api-nodes",         # никаких платных облачных узлов
        "--output-directory", str(ROOT / "output"),
        "--temp-directory", str(ROOT / "tmp")]
with open(LOGS / "server.log", "ab") as log:
    p = subprocess.Popen(args, cwd=str(PORTABLE), env=env, stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, creationflags=0x08000000)  # CREATE_NO_WINDOW
    (LOGS / "server.pid").write_text(str(p.pid))
    p.wait()
