"""Находит самые «громкие» (насыщенные боем) окна в записи игры.

Использование: python find_highlights.py <video> <window_sec> <top_n> [out.json]
Печатает JSON: [{start, end, score}], окна не пересекаются.
Метрика: средняя громкость окна + плотность резких всплесков (взрывы, попадания).
"""
import json, subprocess, sys
import numpy as np

def main():
    path, win, top = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    out = sys.argv[4] if len(sys.argv) > 4 else None
    sr = 8000
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    hop = sr // 4  # 0.25 s
    n = len(a) // hop
    rms = np.sqrt(np.mean(a[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    # всплеск = рост громкости больше чем на 6 дБ относительно скользящей медианы 2 с
    k = 8
    pad = np.pad(db, (k, k), mode="edge")
    med = np.array([np.median(pad[i : i + 2 * k + 1]) for i in range(n)])
    spikes = (db - med > 6).astype(np.float32)
    w = int(win * 4)
    if n <= w:
        res = [{"start": 0.0, "end": n / 4, "score": 0.0}]
    else:
        cs_db = np.concatenate([[0], np.cumsum(db)])
        cs_sp = np.concatenate([[0], np.cumsum(spikes)])
        mean_db = (cs_db[w:] - cs_db[:-w]) / w
        sp = (cs_sp[w:] - cs_sp[:-w]) / w
        z = lambda x: (x - x.mean()) / (x.std() + 1e-9)
        score = z(mean_db) + 1.5 * z(sp)
        # первые/последние 5 с — экраны загрузки и итогов, исключаем
        score[: 20] = -1e9
        score[max(0, len(score) - 20 - w):] = np.minimum(score[max(0, len(score) - 20 - w):], -1e9)
        res = []
        s = score.copy()
        for _ in range(top):
            i = int(np.argmax(s))
            if s[i] < -1e8:
                break
            res.append({"start": round(i / 4, 2), "end": round((i + w) / 4, 2), "score": round(float(s[i]), 3)})
            s[max(0, i - w) : i + w] = -1e9
    txt = json.dumps({"file": path, "duration": round(n / 4, 2), "windows": res}, ensure_ascii=False)
    print(txt)
    if out:
        open(out, "w", encoding="utf-8").write(txt)

if __name__ == "__main__":
    main()
