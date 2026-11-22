"""Время начала каждой строки песни по окнам транскрипции (lyric_map.py).

Использование:
  python align_lyrics.py <lyrics.md> <windows_dir> <out_dir> [трек ...]
lyrics.md — all_tracks_ready.md (блоки ## N. TITLE + ```LYRICS```).
windows_dir — папка с <трек>.windows.json от lyric_map.py.
Результат: <out_dir>/<трек>.lines.json  [{"t", "text", "section", "score", "heard"}]
  t — оценка начала строки (с), score — доля слов строки, найденных в транскрипции (0..1),
  heard — текст окон вокруг строки (для ручной проверки).
Строки, не найденные в транскрипции (Suno их не спел), идут с t = null.
"""
import difflib, json, os, re, sys

# имя файла клипа -> заголовок блока в all_tracks_ready.md
TITLE_MAP = {
    "Eternal War": "ETERNAL WAR",
    "Angels of Death": "ANGELS OF DEATH",
    "Winter's Gate": "THE WOLF AT WINTER'S GATE",
    "Blood for the Red Angel": "BLOOD FOR THE RED ANGEL",
    "Ghosts of Istvaan": "GHOSTS OF ISTVAAN",
    "The last Black Templar": "THE LAST BLACK TEMPLAR",
    "Children of the Void": "CHILDREN OF THE VOID",
    "Machine God Rising": "MACHINE GOD RISING",
    "The Siege of Terra": "THE SIEGE OF TERRA",
    "Green Tide Rising": "GREEN TIDE RISING",
    "When the Stars remember US": "WHEN THE STARS REMEMBER US",
    "The Rose in the Ashes": "ROSE IN THE ASHES",
}

STOP = {"the", "a", "an", "and", "of", "in", "to", "we", "i", "is", "on", "at", "by", "for", "oh"}


def parse_lyrics(md):
    text = open(md, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^## \d+b?\. ([^\n(]+?)\s*(?:\(|\n)", text, re.M):
        title = m.group(1).strip()
        rest = text[m.end():]
        lm = re.search(r"\*\*LYRICS:\*\*\s*```\n(.*?)```", rest, re.S)
        if not lm:
            continue
        lines, sec = [], ""
        for raw in lm.group(1).splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith("["):
                sec = s.strip("[]").split(":")[0].strip()
                continue
            lines.append({"text": s, "section": sec})
        out[title] = lines
    return out


def toks(s):
    return [w for w in re.findall(r"[a-z0-9']+", s.lower().replace("’", "'"))]


def content(ws):
    c = [w for w in ws if w not in STOP]
    return c or ws


def tok_match(w, pool):
    if w in pool:
        return 1.0
    best = max((difflib.SequenceMatcher(None, w, p).ratio() for p in pool), default=0)
    return 1.0 if best >= 0.8 else 0.0


def score(line_t, pool):
    if not line_t or not pool:
        return 0.0
    return sum(tok_match(w, pool) for w in line_t) / len(line_t)


def align(lines, wins):
    n, m = len(lines), len(wins)
    wt = [set(toks(w["text"])) for w in wins]
    lt = [content(toks(l["text"])) for l in lines]
    # пул слов окна j = окна j и j+1 (строка длиннее одного окна)
    pools = [wt[j] | (wt[j + 1] if j + 1 < m else set()) for j in range(m)]
    S = [[score(lt[i], pools[j]) for j in range(m)] for i in range(n)]
    NEG = -1e9
    # dp[i][j]: лучшая сумма для строк 0..i, где последняя назначенная строка стоит в окне <= j
    best = [[NEG] * (m + 1) for _ in range(n + 1)]
    back = [[None] * (m + 1) for _ in range(n + 1)]
    for j in range(m + 1):
        best[0][j] = 0.0
    for i in range(1, n + 1):
        for j in range(m + 1):
            # строку i-1 пропускаем (не спета)
            cand = best[i - 1][j] - 0.05
            choice = ("skip", j)
            if j >= 1:
                # строка i-1 стоит в окне j-1, предыдущие — не дальше окна j-2
                sc = S[i - 1][j - 1]
                if sc >= 0.34:
                    prev = best[i - 1][j - 1] if j - 1 >= 0 else NEG
                    v = prev + sc
                    if v > cand:
                        cand, choice = v, ("take", j - 1)
                # переносим лучшее из меньшего j
                if best[i][j - 1] > cand:
                    cand, choice = best[i][j - 1], ("carry", j - 1)
            best[i][j], back[i][j] = cand, choice
    # обратный проход
    pos = [None] * n
    i, j = n, m
    while i > 0:
        kind, k = back[i][j]
        if kind == "carry":
            j = k
            continue
        if kind == "take":
            pos[i - 1] = k
            j = k  # следующая (предыдущая по порядку) строка — в окне < k
        i -= 1
    res = []
    for i, l in enumerate(lines):
        j = pos[i]
        if j is None:
            res.append({"t": None, "text": l["text"], "section": l["section"], "score": 0.0, "heard": ""})
            continue
        first = lt[i][:1]
        # самое раннее окно рядом (j-2..j), где уже слышно первое значимое слово
        k = j
        for kk in range(max(0, j - 2), j + 1):
            if first and tok_match(first[0], wt[kk]):
                k = kk
                break
        prev_has = k - 1 >= 0 and first and tok_match(first[0], wt[k - 1])
        t = wins[k]["t0"] + (0.25 if prev_has else 0.8)
        heard = " | ".join(wins[x]["text"] for x in range(max(0, k - 1), min(m, j + 3)))
        res.append({"t": round(t, 2), "text": l["text"], "section": l["section"],
                    "score": round(S[i][j], 2), "heard": heard})
    # монотонность времени
    last = -1
    for r in res:
        if r["t"] is not None:
            if r["t"] <= last:
                r["t"] = round(last + 0.6, 2)
            last = r["t"]
    # пропущенные транскрипцией строки внутри одного раздела — ставим равномерно между соседями,
    # если между ними хватает места (≥ 1,6 с на строку); помечаем interp
    i = 0
    while i < len(res):
        if res[i]["t"] is None:
            j = i
            while j < len(res) and res[j]["t"] is None:
                j += 1
            if i > 0 and j < len(res):
                a, b = res[i - 1]["t"], res[j]["t"]
                k = j - i
                same = all(res[x]["section"] == res[i - 1]["section"] for x in range(i, j))
                if same and (b - a) / (k + 1) >= 1.6 and (b - a) <= 4.0 * (k + 1):
                    for x in range(i, j):
                        res[x]["t"] = round(a + (b - a) * (x - i + 1) / (k + 1), 2)
                        res[x]["interp"] = True
            i = j
        else:
            i += 1
    return res


def main():
    md, wdir, odir = sys.argv[1:4]
    only = sys.argv[4:]
    os.makedirs(odir, exist_ok=True)
    lyr = parse_lyrics(md)
    for base, title in TITLE_MAP.items():
        if only and base not in only:
            continue
        wp = os.path.join(wdir, base + ".windows.json")
        if not os.path.exists(wp) or title not in lyr:
            print("skip", base, "(нет окон)" if not os.path.exists(wp) else "(нет текста)")
            continue
        wins = sorted(json.load(open(wp, encoding="utf-8")), key=lambda w: w["t0"])
        res = align(lyr[title], wins)
        json.dump(res, open(os.path.join(odir, base + ".lines.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        got = sum(1 for r in res if r["t"] is not None)
        print(f"OK {base}: {got}/{len(res)} строк найдено")


if __name__ == "__main__":
    main()
