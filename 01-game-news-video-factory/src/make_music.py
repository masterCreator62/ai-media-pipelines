"""Своя фоновая музыка и звуки переходов — процедурная генерация (numpy), без чужих сэмплов.

Зачем: у такой музыки нет правообладателя, значит не будет заявок Content ID. Происхождение для метаданных:
"music & SFX: own procedural generation (make_music.py)".

Как модуль (так её вызывает make_news_video.py):
    from make_music import music_bed, sfx_track
    bed = music_bed(dur, style="calm_minor", bpm=100, seed=1)   # float32 (N, 2), 48 кГц
    fx = sfx_track(dur, cues=[3.1, 7.4, ...])                    # вжух перед сменой карточки + мягкий удар на ней
Из командной строки (послушать отдельно):
    python make_music.py out.wav 50 [--style calm_minor|tech_pulse] [--bpm 100] [--seed 1] [--cues 3.1,7.4]

Стили:
  calm_minor  — спокойный пэд в миноре (Am–F–C–G), мягкий пульс баса, тихая бочка на 1 и 3. Новости, таймлайны.
  tech_pulse  — чуть бодрее (Dm–B♭–F–C): пэд + арпеджио «щипком» 16-ми, бочка на каждую долю. Техно-разборы, Reels.
"""
import sys, wave
import numpy as np

SR = 48000

STYLES = {
    # аккорды — MIDI-номера (тоника, терция, квинта, октава); по 2 такта на аккорд
    "calm_minor": {"bpm": 100, "chords": [[57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60], [55, 59, 62, 67]],
                   "arp": False, "kick": (0, 2), "hat": 0.05, "bass": 0.32, "pad": 1.0, "cutoff": 2600},
    "tech_pulse": {"bpm": 110, "chords": [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]],
                   "arp": True, "kick": (0, 1, 2, 3), "hat": 0.08, "bass": 0.36, "pad": 0.75, "cutoff": 3400},
}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, cutoff, sr=SR, slope=2.0):
    """Мягкий фильтр через FFT (scipy не нужен): затухание выше cutoff ~ (f/cutoff)^-slope."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(x.shape[0], 1 / sr)
    g = 1 / np.sqrt(1 + (f / cutoff) ** (2 * slope))
    return np.fft.irfft(X * (g[:, None] if x.ndim == 2 else g), n=x.shape[0], axis=0)


def highpass(x, cutoff, sr=SR):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    g = 1 - 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X * g, n=len(x))


def tone(freq, n, harmonics=6, roll=1.8, phase=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, harmonics + 1):
        if freq * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * freq * k * t + phase * k) / k ** roll
    return out


def music_bed(dur, style="calm_minor", bpm=None, seed=1):
    st = STYLES.get(style, STYLES["calm_minor"])
    bpm = bpm or st["bpm"]
    rng = np.random.default_rng(seed)
    n = int(dur * SR) + SR
    beat = 60.0 / bpm
    chord_len = beat * 8  # 2 такта на аккорд
    out = np.zeros((n, 2))
    # --- пэд: 3 расстроенных голоса на ноту, мягкие склейки аккордов
    ci, t0 = 0, 0.0
    while t0 < dur + 1:
        notes = st["chords"][ci % len(st["chords"])]
        a, b = int(t0 * SR), min(n, int((t0 + chord_len + 1.2) * SR))
        m = b - a
        if m <= 0:
            break
        env = np.ones(m)
        att, rel = max(1, min(int(0.9 * SR), m // 2)), max(1, min(int(1.2 * SR), m // 2))  # последний аккорд бывает короче атаки
        env[:att] = np.sin(np.linspace(0, np.pi / 2, att)) ** 2
        env[-rel:] *= np.cos(np.linspace(0, np.pi / 2, rel)) ** 2
        for ch in (0, 1):
            sig = np.zeros(m)
            for note in notes:
                for det in (-7, 0, 7):
                    cents = det + (3 if ch else -3)
                    sig += tone(hz(note) * 2 ** (cents / 1200), m, phase=rng.uniform(0, 6.28)) * (0.55 if det else 0.8)
            out[a:b, ch] += sig * env * 0.045 * st["pad"]
        t0 += chord_len
        ci += 1
    out = lowpass(out, st["cutoff"])
    tt = np.arange(n) / SR
    out *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * tt))[:, None]  # медленное «дыхание»
    # --- бас: тоника октавой ниже, восьмые с мягким затуханием
    steps = int(dur / (beat / 2)) + 2
    for s in range(steps):
        ts = s * beat / 2
        ci = int(ts // chord_len)
        root = st["chords"][ci % len(st["chords"])][0] - 12
        a = int(ts * SR)
        m = min(int(beat / 2 * SR), n - a)
        if m <= 0:
            break
        e = np.exp(-np.arange(m) / SR / 0.16) * (1 - np.exp(-np.arange(m) / SR / 0.008))
        acc = 1.0 if s % 2 == 0 else 0.6
        sig = (np.sin(2 * np.pi * hz(root) * np.arange(m) / SR) + 0.25 * np.sin(4 * np.pi * hz(root) * np.arange(m) / SR))
        out[a:a + m] += (sig * e * 0.12 * st["bass"] * acc)[:, None]
    # --- арпеджио «щипком» (tech_pulse)
    if st["arp"]:
        step = beat / 4
        for s in range(int(dur / step) + 1):
            ts = s * step
            ci = int(ts // chord_len)
            notes = st["chords"][ci % len(st["chords"])]
            note = notes[[0, 1, 2, 3, 2, 1][s % 6]] + 12
            a = int(ts * SR)
            m = min(int(0.3 * SR), n - a)
            if m <= 0:
                break
            e = np.exp(-np.arange(m) / SR / 0.07)
            sig = tone(hz(note), m, harmonics=4, roll=1.4) * e * 0.035
            pan = 0.5 + 0.35 * np.sin(s * 0.7)
            out[a:a + m, 0] += sig * (1 - pan)
            out[a:a + m, 1] += sig * pan
    # --- бочка и хэт
    bars = int(dur / (beat * 4)) + 2
    for bar in range(bars):
        for k in st["kick"]:
            a = int((bar * 4 + k) * beat * SR)
            m = min(int(0.3 * SR), n - a)
            if m <= 0:
                continue
            tk = np.arange(m) / SR
            f = 45 + 75 * np.exp(-tk / 0.03)
            sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tk / 0.12)
            out[a:a + m] += (sig * 0.16)[:, None]
        for k in range(4):
            a = int(((bar * 4 + k) + 0.5) * beat * SR)
            m = min(int(0.05 * SR), n - a)
            if m <= 0:
                continue
            sig = highpass(rng.standard_normal(m), 7000) * np.exp(-np.arange(m) / SR / 0.012)
            out[a:a + m, 0] += sig * st["hat"] * 0.6
            out[a:a + m, 1] += sig * st["hat"] * 0.4
    out = out[:int(dur * SR)]
    fi, fo = int(0.6 * SR), int(min(2.5, dur / 4) * SR)
    out[:fi] *= np.linspace(0, 1, fi)[:, None]
    out[-fo:] *= (np.cos(np.linspace(0, np.pi / 2, fo)) ** 2)[:, None]
    return (out / (np.abs(out).max() + 1e-9) * 0.9).astype(np.float32)


def whoosh(length=0.55, seed=0):
    """Нарастающий шум с поднимающимся фильтром, обрывается к моменту смены карточки."""
    rng = np.random.default_rng(seed)
    m = int(length * SR)
    noise = rng.standard_normal(m + 4096)
    hop, win = 512, 2048
    out = np.zeros(m + 4096)
    w = np.hanning(win)
    for i, a in enumerate(range(0, m, hop)):
        prog = a / m
        seg = noise[a:a + win] * w
        X = np.fft.rfft(seg)
        f = np.fft.rfftfreq(win, 1 / SR)
        cut = 400 + 5600 * prog ** 1.6
        X *= 1 / np.sqrt(1 + (f / cut) ** 4) * (1 - 1 / np.sqrt(1 + (f / 150) ** 4))
        out[a:a + win] += np.fft.irfft(X, n=win)
    out = out[:m]
    env = (np.linspace(0, 1, m) ** 2.2)
    env[-int(0.04 * SR):] *= np.linspace(1, 0, int(0.04 * SR))
    out = out * env
    pan = np.linspace(0.25, 0.75, m)  # слева направо
    st = np.stack([out * (1 - pan), out * pan], axis=1)
    return st / (np.abs(st).max() + 1e-9)


def soft_hit(seed=0):
    m = int(0.9 * SR)
    t = np.arange(m) / SR
    f = 55 + 60 * np.exp(-t / 0.05)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.28)
    shimmer = (np.sin(2 * np.pi * 1318.5 * t) + 0.5 * np.sin(2 * np.pi * 1975.5 * t)) * np.exp(-t / 0.35) * 0.18
    rng = np.random.default_rng(seed)
    click = lowpass(rng.standard_normal(m), 2500) * np.exp(-t / 0.012) * 0.35
    sig = body + shimmer + click
    st = np.stack([sig, sig], axis=1)
    return st / (np.abs(st).max() + 1e-9)


def sfx_track(dur, cues, intro_hit=True):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    W, Hh = whoosh(), soft_hit()

    def put(sig, start, gain):
        a = int(start * SR)
        b0 = max(0, -a)
        a = max(0, a)
        m = min(len(sig) - b0, n - a)
        if m > 0:
            out[a:a + m] += sig[b0:b0 + m] * gain

    if intro_hit:
        put(Hh, 0.02, 0.8)
    for c in cues:
        if c <= 0.3 or c >= dur - 0.2:
            continue
        put(W, c - len(W) / SR, 0.55)
        put(Hh, c, 0.7)
    return out.astype(np.float32)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((x * 32767).astype("<i2").tobytes())


def read_wav(path):
    with wave.open(path) as wf:
        ch, sw, sr, nf = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
        raw = wf.readframes(nf)
    assert sw == 2 and sr == SR, f"ожидается 16 бит / {SR} Гц: {path}"
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    x = x.reshape(-1, ch)
    return np.repeat(x, 2, axis=1) if ch == 1 else x


def looped_bed(dur, style="calm_minor", bpm=None, seed=1, cycles=4, xf_s=1.0):
    """Музыка для длинного ролика: 4 круга аккордов (~80 с) повторяются с плавной склейкой 1 с.
    Памяти — как у Shorts, а не гигабайты на FFT всей длины (22.11.2026: 9-минутный рендер падал по памяти)."""
    st = STYLES.get(style, STYLES["calm_minor"])
    bpm = bpm or st["bpm"]
    L = int(round(60.0 / bpm * 8 * len(st["chords"]) * cycles * SR))
    xf = int(xf_s * SR)
    seg = music_bed(L / SR + 2 * xf_s, style, bpm, seed)[:L + xf].astype(np.float32)
    n = int(dur * SR) + SR
    out = np.zeros((n + L + xf, 2), dtype=np.float32)
    fade_in = np.sin(np.linspace(0, np.pi / 2, xf, dtype=np.float32))[:, None] ** 2
    for k, a in enumerate(range(0, n, L)):
        piece = seg.copy()
        if k:
            piece[:xf] *= fade_in
        piece[L:] *= fade_in[::-1]
        out[a:a + L + xf] += piece
    return out[:n]


def mix_with_voice(voice, dur, music=None, sfx_cues=None, sfx_gain_db=-14.0):
    """Голос + музыка с «приседанием» под речь + звуки переходов. Уровни — относительно RMS речи.

    music: {"style": "calm_minor", "bpm": 100, "seed": 1, "gain_db": -20, "gap_boost_db": 7}
      gain_db — уровень музыки под речью относительно речи (−18…−22 рекомендуется);
      gap_boost_db — на сколько музыка поднимается в паузах и в конце.
    Возвращает (микс, статистика)."""
    n = voice.shape[0]
    mono = np.abs(voice).mean(axis=1)
    hop = SR // 100  # огибающая 100 Гц
    frames = n // hop
    env = mono[:frames * hop].reshape(frames, hop).max(axis=1)
    thr = 0.06 * env.max()
    act = (env > thr).astype(float)
    sm = np.zeros(frames)
    v = 0.0
    for i, a in enumerate(act):  # атака 60 мс, отпускание 400 мс
        k = 0.15 if a > v else 0.025
        v += (a - v) * k
        sm[i] = v
    # заглядывание вперёд: музыка начинает уходить вниз за 120 мс до фразы
    sm = np.maximum(sm, np.concatenate([sm[12:], np.zeros(12)]))
    act_s = np.interp(np.arange(n), np.arange(frames) * hop, sm)
    speech_mask = np.pad(np.repeat(act, hop), (0, max(0, n - frames * hop)))[:n].astype(bool)
    v_rms = float(np.sqrt(np.mean(np.square(voice[speech_mask]))) + 1e-9)
    out = voice.astype(np.float32 if dur > 120 else np.float64).copy()  # длинные: вдвое меньше памяти
    stats = {"voice_rms_db": 20 * np.log10(v_rms)}
    if music:
        if dur > 120:  # длинные ролики: FFT-фильтр на всю длину съедает гигабайты памяти — собираем из петли
            bed = looped_bed(dur, music.get("style", "calm_minor"), music.get("bpm"), music.get("seed", 1))
        else:
            bed = music_bed(dur, music.get("style", "calm_minor"), music.get("bpm"), music.get("seed", 1))
        bed = np.pad(bed, ((0, max(0, n - len(bed))), (0, 0)))[:n]
        m_rms = float(np.sqrt(np.mean(np.square(bed))) + 1e-9)
        g_speech = v_rms / m_rms * 10 ** (music.get("gain_db", -20) / 20)
        g_gap = g_speech * 10 ** (music.get("gap_boost_db", 7) / 20)
        gain = g_gap + (g_speech - g_gap) * act_s
        out += bed * gain[:, None]
        sp = act_s > 0.9
        if sp.any():
            stats["music_under_voice_db"] = 20 * np.log10(np.sqrt(np.mean(np.square(bed[sp] * gain[sp, None]))) / v_rms)
    if sfx_cues is not None:
        fx = sfx_track(dur, sfx_cues)
        fx = np.pad(fx, ((0, max(0, n - len(fx))), (0, 0)))[:n]
        out += fx * (v_rms * 10 ** (sfx_gain_db / 20) / 0.25)  # пики эффектов ≈ на sfx_gain_db ниже типичного пика речи
    pk = np.abs(out).max()
    stats["pre_norm_peak"] = float(pk)
    if pk > 0.98:
        out *= 0.98 / pk  # loudnorm дальше выставит −14 LUFS
    return out.astype(np.float32), stats


if __name__ == "__main__":
    a = sys.argv[1:]
    path, dur = a[0], float(a[1])
    opt = {a[i][2:]: a[i + 1] for i in range(2, len(a) - 1, 2) if a[i].startswith("--")}
    bed = music_bed(dur, opt.get("style", "calm_minor"), float(opt["bpm"]) if "bpm" in opt else None, int(opt.get("seed", 1)))
    if "cues" in opt:
        bed = bed * 0.6 + sfx_track(dur, [float(c) for c in opt["cues"].split(",")]) * 0.5
    write_wav(path, bed)
    print("OK", path, f"{dur:.1f}s")
