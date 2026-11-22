"""Собирает переносную копию Города D.A.V.E. в ОДИН html-файл (share\Город_DAVE.html).

Внутри: 2D-схема и 3D-город со всеми скриптами (three.js, data.js, rooms.js, live.js, interior.js).
Файл открывается двойным кликом на любом компьютере с Chrome/Edge/Firefox, без интернета и без папок проекта.
Данные — снимок на момент сборки (live.js в режиме DAVE_SNAPSHOT не перечитывает data.js).
Запуск: python make_share.py  (перед этим полезно прогнать build_data.py, чтобы снимок был свежим).
"""
import base64, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'share' / 'Город_DAVE.html'
SCRIPT_RE = re.compile(r'<script\s+src="([^"]+)"[^>]*>\s*</script>', re.I)


def inline(page: Path, nav_from: str, nav_to: str) -> str:
    html = page.read_text(encoding='utf-8')

    def repl(m):
        src = (page.parent / m.group(1)).resolve()
        if not src.is_file():
            sys.exit(f'нет файла {src}')
        js = src.read_text(encoding='utf-8').replace('</script', '<\\/script')
        return '<script>\n' + js + '\n</script>'

    left = SCRIPT_RE.findall(html)
    html, n = SCRIPT_RE.subn(repl, html)
    if n != len(left):
        sys.exit(f'в {page} не все скрипты вшиты')
    # снимок: live.js должен узнать об этом до своего запуска
    html = html.replace('<head>', '<head>\n<script>window.DAVE_SNAPSHOT=true;</script>', 1)
    # переход между 2D и 3D — через родительскую страницу-обёртку
    if nav_from not in html:
        sys.exit(f'в {page} не найден переход {nav_from}')
    html = html.replace(nav_from, nav_to)
    print(f'{page.relative_to(ROOT)}: вшито скриптов {n}, {len(html)//1024} КБ')
    return html


def main():
    p2 = inline(ROOT / 'index.html', "location.href='3d/index.html'", "parent.postMessage('go:3d','*')")
    p3 = inline(ROOT / '3d' / 'index.html', "location.href='../index.html'", "parent.postMessage('go:2d','*')")
    b = lambda s: base64.b64encode(s.encode('utf-8')).decode('ascii')
    wrapper = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Город D.A.V.E.</title>
<style>html,body{{margin:0;height:100%;background:#05070f;overflow:hidden}}
iframe{{border:0;width:100%;height:100%;display:block}}
#tip{{position:fixed;left:50%;top:40%;transform:translateX(-50%);color:#9fb3ff;font:16px system-ui,sans-serif}}</style>
</head><body><div id="tip">Загрузка города…</div>
<script>
const PAGES = {{ '2d': '{b(p2)}', '3d': '{b(p3)}' }};
const dec = s => new TextDecoder().decode(Uint8Array.from(atob(s), c => c.charCodeAt(0)));
let frame = null;
function show(k) {{
  if (frame) frame.remove();            // старая сцена освобождает видеопамять
  frame = document.createElement('iframe');
  frame.setAttribute('allow', 'fullscreen');
  frame.srcdoc = dec(PAGES[k]);
  document.body.appendChild(frame);
  document.getElementById('tip').style.display = 'none';
  location.hash = k;
}}
addEventListener('message', e => {{ if (typeof e.data === 'string' && e.data.startsWith('go:')) show(e.data.slice(3)); }});
show(location.hash === '#3d' ? '3d' : '2d');
</script></body></html>
"""
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_suffix('.tmp')
    tmp.write_text(wrapper, encoding='utf-8')
    tmp.replace(OUT)
    print(f'готово: {OUT} ({OUT.stat().st_size/1024/1024:.2f} МБ)')


if __name__ == '__main__':
    main()
