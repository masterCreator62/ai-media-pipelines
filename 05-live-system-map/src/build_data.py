"""Собирает data.js для Города D.A.V.E. из реальных файлов.

Запуск (бандл-Python D.A.V.E.):
  $PY = Join-Path (Split-Path $env:APP_EXECUTABLE) 'binaries\\python\\python.exe'
  & $PY H:\\DAVE_City\\build_data.py            # обычная сборка
  & $PY H:\\DAVE_City\\build_data.py --no-llm   # без перевода через FreeLLMAPI

Читает: DAVE\\agents, DAVE\\skills, DAVE\\brain\\memory, DAVE\\projects, DAVE\\chat-summaries,
~/.claude.json (только имена MCP-серверов), журналы ~/.claude/projects (кто из агентов и когда
запускался), data/dave_snapshot.json (названия чатов и задачи по расписанию — их нет в файлах).
Пишет: data.js (window.DAVE_DATA) и cache/*.json — атомарно (временный файл + os.replace).
Секреты не читаются и не выводятся: почта, телефоны и похожие на ключи строки вырезаются.

Живой слой (без модели): чат или агент, чей журнал менялся за последние LIVE_MIN минут, помечается
«работает сейчас», и на его монитор выводится последнее сообщение человека (очищенное, до 120 знаков).
Чаты D.A.V.E. на Claude: журнал ~/.claude/projects/<папка DAVE>/<id чата>.jsonl; агенты —
<id чата>/subagents/agent-*.jsonl (+ .meta.json с типом и задачей). Живую базу D.A.V.E. (.hal) не открываем.
Любой сбой одного раздела не роняет сборку: раздел берётся из прежнего data.js. Журнал — cache/build.log.
Автозапуск каждые 10 минут — Планировщик заданий Windows, autoupdate/run_hidden.vbs (см. overview.md).
"""
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.path.expanduser('~'))
DAVE = HOME / 'DAVE'
CITY = Path(__file__).resolve().parent
CACHE = CITY / 'cache'
CACHE.mkdir(exist_ok=True)
NO_LLM = '--no-llm' in sys.argv
LIVE_MIN = 10                      # «работает сейчас» — журнал менялся не раньше стольких минут назад
TR_BUDGET = 150                    # секунд на перевод за один прогон, чтобы фоновая сборка не висела
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0   # CREATE_NO_WINDOW: дочерний pwsh без мелькающего окна
LOG_FILE = CACHE / 'build.log'
_log_lines = []

if sys.stdout is None:             # pythonw (Планировщик) — консоли нет, печать идёт в журнал
    class _Null:
        def write(self, s):
            return len(s)

        def flush(self):
            pass
    sys.stdout = sys.stderr = _Null()


def log(msg):
    _log_lines.append(msg)
    try:
        print(msg)
    except (OSError, ValueError, UnicodeEncodeError):
        pass


def write_atomic(path, text):
    """Пишет файл целиком или не пишет вовсе: страница никогда не увидит полузаписанный data.js."""
    path = Path(path)
    tmp = path.with_name(path.name + f'.tmp{os.getpid()}')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    for attempt in range(5):        # на Windows replace может упасть, пока браузер читает файл
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.2 * (attempt + 1))
    os.replace(tmp, path)

# ---------------------------------------------------------------- защита данных
RE_MAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
# телефон: с «+», со скобками кода или вида 123-456-78-90 (даты и время не задевает)
RE_PHONE = re.compile(r'(?<![\w.])(?:\+\d[\d\s\-()]{8,}\d|\(\d{2,4}\)[\d\s\-]{6,}\d|\d{3}[\s\-]\d{3}[\s\-]\d{2}[\s\-]\d{2})(?![\w.])')
RE_ISO = re.compile(r'\b(\d{4})-(\d{2})-(\d{2})(?= \d{2}:\d{2})')
# ключ/токен: известные префиксы или длинная строка, где есть и буквы, и цифры (обычные слова-слаги через дефис не трогаем)
RE_KEY = re.compile(r'\b(?:sk|pk|rk|ghp|gho|xox[abp])[-_][A-Za-z0-9_\-]{12,}'
                    r'|\b(?=[A-Za-z0-9+/_\-]*\d)(?=[A-Za-z0-9+/_\-]*[A-Za-z])[A-Za-z0-9+/_\-]{32,}\b')
RE_URL = re.compile(r'https?://([^/\s]+)\S*')
# «пароль: …», «token=…», «api key …» — значение после слова-маркера
RE_SECRET = re.compile(r'(?i)\b(парол\w*|password|passwd|pwd|token|токен\w*|secret|секрет\w*|api[\s_-]?key|ключ\w*)'
                       r'(\s*[:=]\s*|\s+)(?!\d{1,4}[.\-]\d{1,2}[.\-]\d{2,4}\b)(?=\S*[\d_\-])\S{6,}')


def clean(s, limit=None):
    if s is None:
        return ''
    s = str(s)
    s = RE_SECRET.sub(lambda m: m.group(1) + m.group(2) + '[скрыто]', s)
    s = RE_MAIL.sub('[почта скрыта]', s)
    s = RE_KEY.sub('[скрыто]', s)
    s = RE_PHONE.sub('[номер скрыт]', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if limit and len(s) > limit:
        s = s[:limit - 1].rstrip() + '…'
    return s


def short_url(s):
    """Ссылку в названии показываем только сайтом."""
    return RE_URL.sub(lambda m: m.group(1).replace('www.', '') + '/…', s)


# ---------------------------------------------------------------- frontmatter
def frontmatter(path):
    try:
        text = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return {}, ''
    meta, body = {}, text
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end > 0:
            head, body = text[3:end], text[end + 4:]
            lines = head.splitlines()
            i = 0
            while i < len(lines):
                m = re.match(r'^\s*([A-Za-z_]+):\s*(.*)$', lines[i])
                i += 1
                if not m:
                    continue
                v = m.group(2).strip()
                if v in ('>', '|', '>-', '|-', '>+', '|+'):      # многострочное значение YAML
                    block = []
                    while i < len(lines) and (lines[i].startswith((' ', '\t')) or not lines[i].strip()):
                        block.append(lines[i].strip())
                        i += 1
                    v = ' '.join(b for b in block if b)
                if v:
                    if len(v) > 1 and v[0] == v[-1] and v[0] in '"\'':
                        v = v[1:-1]
                    meta.setdefault(m.group(1), v)
    return meta, body


def first_paragraph(body, limit=220):
    for block in re.split(r'\n\s*\n', body):
        t = block.strip()
        if not t or t.startswith('#') or t.startswith('<!--') or t.startswith('|') or t.startswith('```'):
            continue
        return clean(re.sub(r'[*_`>#]', '', t), limit)
    return ''


def mtime_iso(p):
    try:
        return datetime.fromtimestamp(p.stat().st_mtime).strftime('%d.%m.%Y %H:%M')
    except OSError:
        return ''


# ---------------------------------------------------------------- перевод (FreeLLMAPI)
TR_FILE = CACHE / 'translations.json'
TR = json.loads(TR_FILE.read_text(encoding='utf-8')) if TR_FILE.exists() else {}


def tr_key(s):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:16]


def translate_batch(texts):
    """Публичные описания агентов и навыков → русский. Кэш по хэшу; без сервера — оригинал."""
    todo = [t for t in dict.fromkeys(texts) if t and tr_key(t) not in TR and re.search(r'[A-Za-z]{4}', t)
            and not re.search(r'[А-Яа-я]{4}', t)]
    if todo and not NO_LLM and port_open(31415) and time.time() - T_START < TR_BUDGET:
        ask = DAVE / 'projects' / 'freellmapi' / 'ask.ps1'
        work = CITY / '.dave-work'
        work.mkdir(exist_ok=True)
        src = work / f'tr_in{os.getpid()}.json'
        for i in range(0, len(todo), 12):
            if time.time() - T_START > TR_BUDGET:
                log('  перевод: бюджет времени исчерпан, остальное — в следующий прогон')
                break
            chunk = todo[i:i + 12]
            src.write_text(json.dumps({str(n): t for n, t in enumerate(chunk)}, ensure_ascii=False, indent=0), encoding='utf-8')
            prompt = ('Переведи значения этого JSON на русский язык: коротко, понятно, без кавычек-ёлочек внутри. '
                      'Имена навыков, программ и движков (Godot, Unity, Roblox, Luau, Blender, ComfyUI, React и т.п.) '
                      'оставь латиницей. Ответь ТОЛЬКО JSON-объектом с теми же ключами.')
            try:
                # ask.ps1 сохранён в UTF-8 без BOM — Windows PowerShell 5 читает его криво, нужен pwsh 7
                shell = shutil.which('pwsh') or 'powershell'
                out = subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ask),
                                      '-File', str(src), '-Prompt', prompt, '-Model', 'auto:smart'],
                                     capture_output=True, timeout=120, encoding='utf-8', errors='replace',
                                     stdin=subprocess.DEVNULL, creationflags=NO_WINDOW).stdout or ''
                m = re.search(r'\{.*\}', out, re.S)
                data = json.loads(m.group(0)) if m else {}
                for n, t in enumerate(chunk):
                    ru = data.get(str(n))
                    if isinstance(ru, str) and re.search(r'[А-Яа-я]', ru):
                        TR[tr_key(t)] = clean(ru, 900)
            except Exception as e:  # noqa: BLE001 — перевод необязателен
                log(f'  перевод: пропущен блок {i} ({type(e).__name__})')
        try:
            src.unlink()
            work.rmdir()
        except OSError:
            pass
        write_atomic(TR_FILE, json.dumps(TR, ensure_ascii=False, indent=1))


def ru(s):
    return TR.get(tr_key(s), s) if s else s


def port_open(port, host='127.0.0.1'):
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------- запуски агентов (из журналов)
RUNS_FILE = CACHE / 'agent_runs.json'


def new_lines(path, entry):
    """Журналы только дописываются: читаем с прошлого смещения целые строки. Файл укоротился — с начала.
    entry — словарь кэша; в нём обновляются off/size. Возвращает (строки, начали_с_нуля)."""
    st = path.stat()
    off = entry.get('off', 0)
    fresh = st.st_size < off or entry.get('ino') not in (None, st.st_ino) or 'off' not in entry
    if fresh:
        off = 0
    out = []
    with path.open('rb') as fh:
        fh.seek(off)
        data = fh.read()
    end = data.rfind(b'\n')
    if end >= 0:
        out = data[:end].split(b'\n')
        off += end + 1
    entry['off'], entry['ino'] = off, st.st_ino
    return out, fresh


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def scan_agent_runs():
    cache = load_json(RUNS_FILE, {})
    root = HOME / '.claude' / 'projects'
    seen = set()
    for f in root.rglob('*.jsonl'):
        key = str(f)
        seen.add(key)
        ent = cache.setdefault(key, {})
        try:
            lines, fresh = new_lines(f, ent)
        except OSError:
            continue
        if fresh:
            ent['runs'] = []
        runs = ent.setdefault('runs', [])
        ent.pop('sig', None)
        for raw in lines:
            if b'"subagent_type"' not in raw:
                continue
            try:
                rec = json.loads(raw)
            except ValueError:
                continue
            msg = rec.get('message') or {}
            content = msg.get('content') if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') in ('Agent', 'Task'):
                    inp = c.get('input') or {}
                    st_ = inp.get('subagent_type') or 'general-purpose'
                    runs.append([st_, rec.get('timestamp', ''), clean(inp.get('description', ''), 80)])
    for k in list(cache):
        if k not in seen:
            del cache[k]
    write_atomic(RUNS_FILE, json.dumps(cache, ensure_ascii=False))
    agg = {}
    for v in cache.values():
        for name, ts, desc in v['runs']:
            a = agg.setdefault(name, {'runs': 0, 'last': '', 'task': ''})
            a['runs'] += 1
            if ts > a['last']:
                a['last'], a['task'] = ts, desc
    return agg


def local_time(ts):
    if not ts:
        return ''
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone()
        return dt.strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return ts[:16]


def parse_ts(ts):
    """ISO-время журнала (UTC, с Z) или снимка (местное) → aware datetime; плохое — None."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        return dt if dt.tzinfo else dt.astimezone()
    except ValueError:
        return None


# ---------------------------------------------------------------- живой слой: чаты и агенты из журналов
LIVE_FILE = CACHE / 'live_scan.json'
RE_UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
RE_SYSREM = re.compile(r'<system-reminder>.*?(?:</system-reminder>|$)', re.S)
RE_TAGBLOCK = re.compile(r'<(command-[a-z-]+|local-command-[a-z-]+)>.*?</\1>', re.S)
RE_TAG = re.compile(r'</?(?:pasted_content|attachment|user-prompt-submit-hook)[^>]*>')
RE_HANDOFF = re.compile(r'\[hal:handoff-from\b([^\]]*)\]')
RE_SRC_MSG = re.compile(r'sourceMessageId\W+(handoff-[0-9a-f]+)')


def dave_transcript_dirs():
    """Папки журналов, где cwd — DAVE (имя папки = путь cwd с заменой не-букв на «-»; старые версии писали «_»)."""
    root = HOME / '.claude' / 'projects'
    slug = re.sub(r'[^A-Za-z0-9]', '-', str(DAVE))
    try:
        return [p for p in root.iterdir() if p.is_dir() and re.sub(r'[^A-Za-z0-9]', '-', p.name) == slug]
    except OSError:
        return []


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(x, dict) and x.get('type') == 'tool_result' for x in content):
            return ''
        return '\n'.join(x.get('text', '') for x in content if isinstance(x, dict) and x.get('type') == 'text')
    return ''


def human_message(rec):
    """Сообщение человека: (первая строка-маркер [hal:…] или '', текст). Не человек — None."""
    if rec.get('type') != 'user' or rec.get('isMeta') or rec.get('isSidechain') or rec.get('isCompactSummary') \
            or rec.get('isVisibleInTranscriptOnly'):
        return None
    t = _text_of((rec.get('message') or {}).get('content'))
    if not t:
        return None
    t = RE_TAG.sub('', RE_TAGBLOCK.sub('', RE_SYSREM.sub('', t))).strip()
    marker = ''
    if t.startswith('[hal:'):
        first, _, rest = t.partition('\n')
        marker, t = first, rest
    t = re.sub(r'\[hal:[^\]]*\]', '', t).strip()
    if not t and not marker:
        return None
    return marker, t


def _attr(s, name):
    m = re.search(r'\b' + name + r'=(\S+)', s)
    return m.group(1) if m else ''


def _b64(s):
    try:
        return base64.b64decode(s + '=' * (-len(s) % 4)).decode('utf-8', 'replace')
    except (ValueError, TypeError):
        return ''


def screen_text(t, limit=120):
    """Текст для монитора: ссылки — только сайтом, без почты, телефонов, ключей и паролей."""
    return clean(short_url(t), limit)


def scan_live():
    """Сканирует журналы чатов D.A.V.E. инкрементально. Возвращает (chats{uuid: …}, agents_live{type: …}, titles{uuid: (ts, title)}, spawn_titles{uuid: (ts, title)})."""
    cache = load_json(LIVE_FILE, {})
    seen, chats, titles = set(), {}, {}
    now = time.time()
    for d in dave_transcript_dirs():
        for f in d.glob('*.jsonl'):
            sid = f.stem
            if not RE_UUID.match(sid):
                continue
            key = str(f)
            seen.add(key)
            ent = cache.setdefault(key, {})
            try:
                lines, fresh = new_lines(f, ent)
                st = f.stat()
            except OSError:
                continue
            if fresh:
                for k in ('first', 'last', 'last_at', 'hid', 'spawns', 'pend', 'parents', 'sched'):
                    ent.pop(k, None)
            pend, spawns, parents = ent.setdefault('pend', {}), ent.setdefault('spawns', {}), ent.setdefault('parents', {})
            for raw in lines:
                if b'"type":"user"' in raw:
                    try:
                        rec = json.loads(raw)
                    except ValueError:
                        continue
                    if b'sourceMessageId' in raw and pend:          # результат spawn_chat: заголовок ↔ id передачи
                        for c in (rec.get('message') or {}).get('content') or []:
                            if isinstance(c, dict) and c.get('type') == 'tool_result' and c.get('tool_use_id') in pend:
                                m = RE_SRC_MSG.search(json.dumps(c.get('content'), ensure_ascii=False))
                                if m:
                                    spawns[m.group(1)] = pend.pop(c['tool_use_id'])
                    hm = human_message(rec)
                    if not hm:
                        continue
                    marker, text = hm
                    ts = rec.get('timestamp', '')
                    if marker.startswith('[hal:handoff-from'):
                        a = RE_HANDOFF.search(marker)
                        a = a.group(1) if a else marker
                        pid, ttl = _attr(a, 'id'), _b64(_attr(a, 't'))
                        if RE_UUID.match(pid) and ttl:
                            parents[pid] = [ts, ttl]
                        if 'first' not in ent and _attr(a, 'kind') == 'spawned-by':
                            ent['hid'] = _attr(a, 'm')
                    elif marker.startswith('[hal:scheduled-run'):        # чат задачи по расписанию: t= — имя задачи
                        ttl = _b64(_attr(marker, 't').rstrip(']'))
                        if ttl and 'sched' not in ent:
                            ent['sched'] = [ts, clean(ttl, 90)]
                    if not text:
                        continue
                    if 'first' not in ent:
                        ent['first'] = screen_text(text, 70)
                    ent['last'], ent['last_at'] = screen_text(text, 120), ts
                elif b'spawn_chat' in raw and b'"tool_use"' in raw:
                    try:
                        rec = json.loads(raw)
                    except ValueError:
                        continue
                    for c in (rec.get('message') or {}).get('content') or []:
                        if isinstance(c, dict) and c.get('type') == 'tool_use' and str(c.get('name', '')).endswith('spawn_chat'):
                            title = (c.get('input') or {}).get('title')
                            if title:
                                pend[c['id']] = [rec.get('timestamp', ''), clean(short_url(title), 90)]
            if len(pend) > 50:
                for k in list(pend)[:-50]:
                    del pend[k]
            ent['mtime'], ent['ctime'], ent['sid'] = st.st_mtime, st.st_ctime, sid
            chats[sid] = ent
            for pid, (ts, ttl) in parents.items():
                old = titles.get(pid)
                if not old or ts > old[0]:
                    titles[pid] = (ts, clean(short_url(ttl), 90))
    # заголовки, выданные при spawn_chat, — детям по id передачи
    by_hid = {}
    for ent in chats.values():
        for hid, val in ent.get('spawns', {}).items():
            by_hid[hid] = val
    spawn_titles = {sid: by_hid[e['hid']] for sid, e in chats.items() if e.get('hid') in by_hid}

    # агенты: <чат>/subagents/agent-*.meta.json
    agents_live = {}
    root = HOME / '.claude' / 'projects'
    for meta in root.glob('*/*/subagents/agent-*.meta.json'):
        jl = meta.with_name(meta.name[:-len('.meta.json')] + '.jsonl')
        try:
            mt = jl.stat().st_mtime
        except OSError:
            continue
        if now - mt > LIVE_MIN * 60:
            continue
        m = load_json(meta, {})
        typ = m.get('agentType') or 'general-purpose'
        cur = agents_live.get(typ)
        if not cur or mt > cur['mt']:
            agents_live[typ] = {'mt': mt, 'task': screen_text(m.get('description', ''), 120), 'chat': meta.parent.parent.name,
                                'n': (cur or {}).get('n', 0) + 1}
        else:
            cur['n'] += 1
    for k in list(cache):
        if k not in seen:
            del cache[k]
    write_atomic(LIVE_FILE, json.dumps(cache, ensure_ascii=False))
    return chats, agents_live, titles, spawn_titles


def hm_time(ts_epoch):
    return datetime.fromtimestamp(ts_epoch).strftime('%d.%m %H:%M') if ts_epoch else ''


# ---------------------------------------------------------------- MCP: известные наборы инструментов
MCP_TOOLS = {
    'dave-browser': ['browser_navigate', 'browser_snapshot', 'browser_click', 'browser_type', 'browser_fill_form',
                     'browser_take_screenshot', 'browser_evaluate', 'browser_tabs', 'browser_resize', 'browser_hover',
                     'browser_press_key', 'browser_select_option', 'browser_file_upload', 'browser_drag', 'browser_drop',
                     'browser_find', 'browser_act', 'browser_wait_for', 'browser_console_messages',
                     'browser_network_requests', 'browser_network_request', 'browser_handle_dialog',
                     'browser_navigate_back', 'browser_close', 'browser_run_code_unsafe'],
    'dave-computer': ['computer_control'],
    'dave': ['spawn_chat', 'send_to_chat', 'manage_chat', 'compact_chat', 'switch_config', 'goal',
             'create_scheduled_task', 'list_scheduled_tasks', 'update_scheduled_task', 'run_scheduled_task',
             'delete_scheduled_task', 'load_dave_guide', 'pin_chat_file', 'share_chat', 'import_chat_file',
             'browser_task', 'execute_web_route', 'prepare_scraping_service', 'prepare_higgsfield_service',
             'request_capability_setup', 'open_settings', 'support_report', 'list_team_chats'],
    'Roblox_Studio': ['execute_luau', 'script_read', 'script_search', 'script_grep', 'multi_edit', 'search_game_tree',
                      'inspect_instance', 'start_stop_play', 'get_console_output', 'screen_capture', 'video_capture',
                      'save_place', 'insert_asset', 'search_asset', 'generate_mesh', 'generate_material',
                      'generate_texture', 'generate_scene', 'generate_avatar', 'generate_animation',
                      'generate_procedural_model', 'character_navigation', 'user_mouse_input',
                      'user_keyboard_input', 'open_cloud_invoke', 'upload_image', 'http_get', 'subagent',
                      'list_roblox_skills', 'get_roblox_skill'],
    'blender': ['execute_blender_code', 'get_objects_summary', 'get_object_detail_summary',
                'get_screenshot_of_window_as_image', 'get_screenshot_of_area_as_image', 'render_viewport_to_path',
                'render_thumbnail_to_path', 'jump_to_view3d_object_by_name', 'get_blendfile_summary_datablocks',
                'get_blendfile_summary_missing_files', 'search_api_docs', 'search_manual_docs',
                'get_python_api_docs'],
    'comfyui': ['server_info', 'generate_image', 'run_workflow', 'run_template', 'search_templates',
                'fetch_template', 'validate_workflow', 'list_workflow_slots', 'set_workflow_slot', 'job',
                'fetch_outputs', 'preview_media', 'download_model', 'search_models', 'install_node', 'nodes',
                'system_stats', 'free_memory', 'launch_comfyui', 'stop_comfyui', 'restart_comfyui', 'get_logs'],
    'claude_ai_Claude_Docs': ['create', 'read', 'query', 'batch', 'update', 'export', 'delete', 'guide'],
}
MCP_META = {
    'dave-browser': ('Браузер D.A.V.E.', 'browser', 'Собственный Chrome D.A.V.E.: страницы, клики, формы, скриншоты.'),
    'dave-computer': ('Управление ПК', 'computer', 'Программы Windows по окнам, с разрешения на каждую программу.'),
    'dave': ('Диспетчер чатов', 'davemcp', 'Чаты, передача задач, расписание, смена модели.'),
    'Roblox_Studio': ('Roblox Studio', 'roblox', 'Прямой канал в Studio: Luau, скрипты, тест-плей, генерация.'),
    'blender': ('Blender MCP', 'blender', 'Blender 5.3: сцены, модели, материалы, рендер.'),
    'comfyui': ('ComfyUI', 'comfyui', 'Локальные картинки на видеокарте: Z-Image-Turbo и FLUX schnell.'),
    'claude_ai_Claude_Docs': ('Claude Docs', 'docs', 'Живые документы из аккаунта claude.ai.'),
}


def build_mcp():
    out = []
    builtin = ['dave-browser', 'dave-computer', 'dave']
    try:
        cfg = json.loads((HOME / '.claude.json').read_text(encoding='utf-8'))
        user = list((cfg.get('mcpServers') or {}).keys())   # только имена, значения не читаем
    except (OSError, ValueError):
        user = []
    for sid in builtin + user + ['claude_ai_Claude_Docs']:
        name, key, desc = MCP_META.get(sid, (sid, 'mcp-' + re.sub(r'\W+', '-', sid.lower()), 'Подключённый MCP-модуль.'))
        if sid in builtin:
            src, conf = 'встроен в D.A.V.E.', 'Подтверждено'
        elif sid in user:
            src, conf = 'подключён в ~/.claude.json', 'Подтверждено'
        else:
            src, conf = 'коннектор аккаунта claude.ai — виден в сессии 22.11.2026', 'Условно'
        tools = MCP_TOOLS.get(sid, [])
        out.append({'id': sid, 'key': key, 'name': name, 'desc': desc, 'source': src, 'conf': conf,
                    'tools': tools, 'tools_known': bool(tools)})
    return out


# ---------------------------------------------------------------- сборка
def load_prev():
    """Прежний data.js — запасной источник для раздела, который в этот раз не собрался."""
    try:
        txt = (CITY / 'data.js').read_text(encoding='utf-8')
        body = txt[txt.index('window.DAVE_DATA = ') + len('window.DAVE_DATA = '):].rstrip().rstrip(';')
        return json.loads(body)
    except (OSError, ValueError):
        return {}


PREV = {}
ERRORS = []


def section(name, fn, fallback):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — один сломанный раздел не должен ронять сборку
        ERRORS.append(f'{name}: {type(e).__name__}: {e}'[:300])
        return fallback


def build_agents(runs, live_agents, chat_title):
    agents = []
    for f in sorted((DAVE / 'agents').glob('*.md')):
        m, _ = frontmatter(f)
        name = m.get('name', f.stem)
        r = runs.get(name, {})
        agents.append({'id': name, 'desc_en': clean(m.get('description', ''), 700), 'tools': m.get('tools', ''),
                       'runs': r.get('runs', 0), 'last': local_time(r.get('last', '')), 'task': r.get('task', '')})
    builtin_agents = []
    for aid, nm, d in [('general-purpose', 'Универсал', 'Сложные многошаговые задачи: поиск, исследование, выполнение.'),
                       ('Explore', 'Разведчик', 'Только читает: прочёсывает много файлов и возвращает вывод.'),
                       ('Plan', 'Архитектор', 'Проектирует план: шаги, ключевые файлы, компромиссы.'),
                       ('fork', 'Форк', 'Моя копия со всем контекстом, работает параллельно.'),
                       ('workflow', 'Workflow', 'Конвейер из многих агентов — только по прямой просьбе.')]:
        r = runs.get(aid, {})
        builtin_agents.append({'id': aid, 'ru': nm, 'desc': d, 'runs': r.get('runs', 0),
                               'last': local_time(r.get('last', '')), 'task': r.get('task', '')})
    for a in agents + builtin_agents:
        lv = live_agents.get(a['id'])
        a['live'] = bool(lv)
        if lv:
            a['live_at'] = hm_time(lv['mt'])
            a['live_task'] = lv['task']
            a['live_n'] = lv['n']
            a['live_chat'] = chat_title(lv['chat'])
            a['live_chat_id'] = lv['chat'][:8]
    return agents, builtin_agents


def build_skills():
    skills = []
    for d in sorted(p for p in (DAVE / 'skills').iterdir() if (p / 'SKILL.md').exists()):
        m, _ = frontmatter(d / 'SKILL.md')
        sid = m.get('name', d.name)
        if sid.startswith('roblox-'):
            grp = 'roblox-s'
        elif sid == 'router':
            grp = 'router'
        elif sid == 'youtube-shorts-pipeline':
            grp = 'youtube'
        elif sid == 'game-news-pipeline':
            grp = 'news'
        elif sid in ('agent-team-workflow', 'image-render-pipeline', 'freellmapi'):
            grp = 'workshop'
        else:
            grp = 'gamedev'
        skills.append({'id': sid, 'group': grp, 'desc_en': clean(m.get('description', ''), 700), 'updated': mtime_iso(d / 'SKILL.md')})
    return skills


def translate_all(agents, skills):
    for _ in range(3):   # бесплатные модели иногда отвечают битым JSON — до трёх проходов, готовое берётся из кэша
        try:
            translate_batch([a['desc_en'] for a in agents] + [s['desc_en'] for s in skills])
        except Exception as e:  # noqa: BLE001 — без перевода остаётся оригинал
            ERRORS.append(f'перевод: {type(e).__name__}')
            break
    for a in agents:
        a['desc'] = ru(a['desc_en'])
    for s in skills:
        s['desc'] = ru(s['desc_en'])
    used = {tr_key(x['desc_en']) for x in agents + skills}   # убрать из кэша переводы удалённых агентов и навыков
    if set(TR) - used:
        for k in set(TR) - used:
            del TR[k]
        write_atomic(TR_FILE, json.dumps(TR, ensure_ascii=False, indent=1))


def build_memory():
    memory = []
    for f in sorted((DAVE / 'brain' / 'memory').glob('*.md')):
        m, body = frontmatter(f)
        memory.append({'name': clean(m.get('name', f.stem), 60), 'desc': clean(m.get('description', ''), 260),
                       'type': m.get('type', 'note'), 'file': f.name, 'updated': mtime_iso(f)})
    return memory


def build_projects():
    projects = []
    for p in sorted((DAVE / 'projects').iterdir(), key=lambda x: x.name.lower()):
        if not p.is_dir():
            continue
        doc = next((p / n for n in ('overview.md', 'brief.md', 'architecture.md', 'README.md') if (p / n).exists()), None)
        if doc is None:
            doc = next(iter(sorted(p.glob('*.md'))), None)
        m, body = frontmatter(doc) if doc else ({}, '')
        try:
            entries = list(p.iterdir())
        except OSError:
            entries = []
        projects.append({'slug': p.name, 'name': clean(m.get('name', p.name), 70),
                         'desc': clean(m.get('description', '') or first_paragraph(body), 300),
                         'lead': first_paragraph(body, 240) if m.get('description') else '',
                         'doc': doc.name if doc else '', 'where': os.path.realpath(p)[:1] if os.name == 'nt' else '',
                         'files': len(entries), 'updated': mtime_iso(doc) if doc else mtime_iso(p)})
    return projects


def load_snapshot():
    """Названия чатов и расписание: их без модели не узнать. Снимок перезаписывает D.A.V.E. по просьбе «обнови город»."""
    snap = json.loads((CITY / 'data' / 'dave_snapshot.json').read_text(encoding='utf-8'))
    scheduled = [{k: RE_ISO.sub(r'\3.\2.\1', clean(v, 240)) if isinstance(v, str) else v for k, v in t.items()}
                 for t in snap.get('scheduled', [])]
    taken = RE_ISO.sub(r'\3.\2.\1', snap.get('taken_at', '').replace('T', ' ')[:16])
    return snap, scheduled, taken


def build_chats(snap, live, titles_seen, spawn_titles, now):
    """Сводки + снимок + журналы. Порядок стабильный: со сводкой — по дате файла сводки, без — по дате создания журнала."""
    snap_at = parse_ts(snap.get('taken_at', ''))
    by_short = {sid[:8]: sid for sid in live}
    cand = {}                          # short id → [(время, название)]

    def add(short, ts, title):
        if title:
            cand.setdefault(short, []).append((ts or datetime.min.replace(tzinfo=timezone.utc), title))
    for c in snap.get('chats', []):
        add(c['id'][:8], snap_at, clean(short_url(c['title']), 90))
    for sid, (ts, title) in titles_seen.items():
        add(sid[:8], parse_ts(ts), title)
    for sid, (ts, title) in spawn_titles.items():
        add(sid[:8], parse_ts(ts), title)
    for sid, ent in live.items():
        if ent.get('sched'):
            add(sid[:8], parse_ts(ent['sched'][0]), ent['sched'][1])

    def title_of(short, fallback=''):
        if short in cand:
            return max(cand[short], key=lambda x: x[0])[1]
        ent = live.get(by_short.get(short, ''), {})
        return fallback or ent.get('first') or 'Чат ' + short

    def live_fields(short):
        ent = live.get(by_short.get(short, ''))
        if not ent:
            return {'mt': '', 'mt_ms': 0, 'live': False, 'last_msg': '', 'last_at': ''}
        is_live = now - ent['mtime'] <= LIVE_MIN * 60
        return {'mt': hm_time(ent['mtime']), 'mt_ms': int(ent['mtime'] * 1000), 'live': is_live,
                'last_msg': ent.get('last', '') if is_live else '', 'last_at': local_time(ent.get('last_at', '')) if is_live else ''}

    chats, have = [], set()
    for f in sorted((DAVE / 'chat-summaries').glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True):
        m, body = frontmatter(f)
        sid = m.get('short_id') or f.stem.rsplit('_', 1)[-1]
        if sid in have:
            continue
        have.add(sid)
        title = title_of(sid, '') if sid in cand else (f.stem.split('_chat-summary_')[0].replace('-', ' '))
        sections = len(re.findall(r'^## ', body, re.M))
        chats.append(dict({'id': sid, 'title': title, 'line': clean(m.get('description', ''), 200),
                           'at': local_time(m.get('last_run_at', '')), 'sections': sections, 'summary': True}, **live_fields(sid)))
    rest = []
    for sid, ent in live.items():
        short = sid[:8]
        if short not in have:
            have.add(short)
            rest.append((ent.get('ctime', 0), short))
    for c in snap.get('chats', []):
        short = c['id'][:8]
        if short not in have:
            have.add(short)
            rest.append((0, short))
    for _, short in sorted(rest, key=lambda x: -x[0]):
        chats.append(dict({'id': short, 'title': title_of(short), 'line': '', 'at': '', 'sections': 0, 'summary': False},
                          **live_fields(short)))
    return chats, title_of


def main():
    global PREV
    t0 = T_START
    log('Город D.A.V.E.: сбор данных…')
    PREV = load_prev()
    now = time.time()

    snap, scheduled, taken = section('snapshot', load_snapshot, ({'chats': [], 'scheduled': []}, PREV.get('scheduled', []),
                                                                PREV.get('snapshot_at', '')))
    live, live_agents, titles_seen, spawn_titles = section('live', scan_live, ({}, {}, {}, {}))
    chats_title = section('chats', lambda: build_chats(snap, live, titles_seen, spawn_titles, now), (PREV.get('chats', []), None))
    chats, title_of = chats_title
    if title_of is None:
        def title_of(short):
            return next((c['title'] for c in chats if c['id'] == short[:8]), 'Чат ' + short[:8])

    runs = section('runs', scan_agent_runs, {})
    agents, builtin_agents = section('agents', lambda: build_agents(runs, live_agents, lambda s: title_of(s[:8])),
                                     (PREV.get('agents', []), PREV.get('builtin_agents', [])))
    skills = section('skills', build_skills, PREV.get('skills', []))
    section('translate', lambda: translate_all(agents, skills), False)
    for x in agents + skills:
        x.setdefault('desc', x.get('desc_en', ''))
    memory = section('memory', build_memory, PREV.get('memory', []))
    projects = section('projects', build_projects, PREV.get('projects', []))
    mcp = section('mcp', build_mcp, PREV.get('mcp', []))

    sat = [
        {'key': 'freellm', 'name': 'FreeLLMAPI', 'port': 31415, 'up': port_open(31415)},
        {'key': 'lmstudio', 'name': 'LM Studio', 'port': 1234, 'up': port_open(1234)},
        {'key': 'comfyui-sat', 'name': 'ComfyUI', 'port': 8188, 'up': port_open(8188)},
    ]
    transcripts = section('transcripts', lambda: sum(1 for _ in (HOME / '.claude' / 'projects').rglob('*.jsonl')),
                          PREV.get('counts', {}).get('transcripts', 0))

    data = {
        'generated': datetime.now().strftime('%d.%m.%Y %H:%M'),
        'generated_ms': int(now * 1000),
        'live_min': LIVE_MIN,
        'snapshot_at': taken,
        'counts': {'agents': len(agents), 'builtin_agents': len(builtin_agents), 'skills': len(skills),
                   'memory': len(memory), 'projects': len(projects), 'scheduled': len(scheduled),
                   'chats': len(chats), 'summaries': sum(1 for c in chats if c.get('summary')),
                   'transcripts': transcripts, 'mcp': len(mcp),
                   'live_chats': sum(1 for c in chats if c.get('live')),
                   'live_agents': sum(1 for a in agents + builtin_agents if a.get('live'))},
        'agents': agents, 'builtin_agents': builtin_agents, 'skills': skills, 'memory': memory,
        'projects': projects, 'scheduled': scheduled, 'chats': chats, 'mcp': mcp, 'sat': sat,
        'build_errors': len(ERRORS),
    }
    js = '/* Сгенерировано build_data.py — не править руками. */\nwindow.DAVE_DATA = ' + \
         json.dumps(data, ensure_ascii=False, indent=1) + ';\n'
    write_atomic(CITY / 'data.js', js)
    c = data['counts']
    tr_done = sum(1 for x in agents + skills if x.get('desc') != x.get('desc_en'))
    log(f"  агентов {c['agents']} (+{c['builtin_agents']} встроенных), навыков {c['skills']}, фактов {c['memory']}, "
        f"проектов {c['projects']}, задач {c['scheduled']}, чатов {c['chats']}, MCP {c['mcp']}")
    log(f"  работают сейчас: чатов {c['live_chats']}, агентов {c['live_agents']}; переведено описаний: {tr_done} из "
        f"{len(agents) + len(skills)}; запусков агентов найдено: {sum(a['runs'] for a in agents) + sum(a['runs'] for a in builtin_agents)}")
    for e in ERRORS:
        log('  ⚠ раздел взят из прежних данных — ' + e)
    log(f"  data.js записан за {time.time() - t0:.1f} с")


def remember_python():
    """Путь к pythonw рядом с текущим интерпретатором — для run_hidden.vbs, если папка D.A.V.E. сменится после обновления."""
    exe = Path(sys.executable)
    w = exe.with_name('pythonw.exe') if exe.name.lower() == 'python.exe' else exe
    if w.exists():
        f = CITY / 'autoupdate' / 'python_path.txt'
        try:
            if not f.exists() or f.read_text(encoding='utf-8').strip() != str(w):
                f.parent.mkdir(exist_ok=True)
                write_atomic(f, str(w) + '\n')
        except OSError:
            pass


def write_log(status):
    line = f"{datetime.now():%d.%m.%Y %H:%M:%S} {status} {time.time() - T_START:.1f}с " + \
           ' | '.join(x.strip() for x in _log_lines[1:] if x.strip())
    try:
        old = LOG_FILE.read_text(encoding='utf-8').splitlines()[-299:] if LOG_FILE.exists() else []
        write_atomic(LOG_FILE, '\n'.join(old + [line]) + '\n')
    except OSError:
        pass


if __name__ == '__main__':
    T_START = time.time()
    lock = CACHE / 'build.lock'
    try:                               # два прогона сразу (Планировщик + ручной) не нужны
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        try:
            age = time.time() - lock.stat().st_mtime
        except OSError:
            age = 0
        if age < 600:
            log('Уже идёт другая сборка — пропускаю.')
            sys.exit(0)
        lock.touch()
    status = 'ok'
    try:
        remember_python()
        main()
        if ERRORS:
            status = 'частично'
    except Exception as e:  # noqa: BLE001
        status = f'ОШИБКА {type(e).__name__}: {e}'[:300]
        log(status)
        write_log(status)
        try:
            lock.unlink()
        except OSError:
            pass
        sys.exit(1)
    write_log(status)
    try:
        lock.unlink()
    except OSError:
        pass
else:
    T_START = time.time()
