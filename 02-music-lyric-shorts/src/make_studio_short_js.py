# Генерирует JS для browser_run_code_unsafe (D.A.V.E.) — заполнение Short в окне загрузки YouTube Studio.
# Использование: python make_studio_short_js.py <id> [<id> ...]
#   -> .dave-work/wme_js/<id>_a.js (детали) и <id>_b.js (связанное видео + дата/время + Schedule)
# ВАЖНО (проверено 22.11.2026):
#  - параметр filename у browser_run_code_unsafe не работает ("not a function") — код вставлять текстом в поле code;
#  - page.setDefaultTimeout в D.A.V.E. нет — таймауты передавать в каждый вызов;
#  - один вызов run_code живёт ~30 с, поэтому детали (A) и расписание (B) — два отдельных вызова;
#  - Shorts в плейлист альбома НЕ добавлять (решение 024ee766/27cee33b от 22.11);
#  - часовой пояс расписания в Studio = GMT+3 (МСК), время не пересчитывать.
import json, sys, pathlib, datetime, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
META = ROOT / 'Канал1_World_Metal_Empire' / 'shorts_v2_meta.json'
OUT = ROOT / '.dave-work' / 'wme_js'
OUT.mkdir(parents=True, exist_ok=True)

# id полного трека -> начало названия ролика в окне «Choose specific video»
TRACK_OPT = {
    'jVF4Bd5hf58': 'Eternal War', 'SuPWEtXs6VI': 'Angels of Death', '4RIkiHsnZVc': "Winter's Gate",
    'lNd3SyeFPlg': 'Blood for the Red Angel', 'zn1HjnGAZrE': 'Ghosts of Istvaan', 'LQFQS7dd9nk': 'The Last Black Templar',
    'SB-V-fT3D4k': 'Children of the Void', 'qDKbA_LKlc0': 'Machine God Rising', 'zrQQxds13no': 'The Siege of Terra',
    '8UY25HMrsJw': 'When the Stars Remember Us', 'KPYAgghEaCU': 'The Rose in the Ashes', '8YL-SxKH_wQ': 'Green Tide Rising',
}

SURVEY = """  const closeSurvey = async () => { const sv = page.locator('iframe[name="google-hats-survey"]'); if (await sv.count()) { try { await sv.contentFrame().getByRole('button', { name: 'Close user survey dialog' }).click({ timeout: 2000 }); } catch (e) {} } };
"""

A = """async (page) => {
  const M = __M__; const T = { timeout: 9000 }; const log = [];
""" + SURVEY + """  try {
    await page.getByText('Reuse details').first().waitFor({ state: 'visible', timeout: 15000 });
    await closeSurvey();
    await page.getByRole('textbox', { name: /Add a title/ }).fill(M.title, T); log.push('title');
    await page.getByRole('textbox', { name: /Tell viewers/ }).fill(M.description, T); log.push('desc');
    await page.getByRole('radio', { name: "No, it's not made for kids" }).click(T); log.push('nfk');
    await page.getByRole('button', { name: 'Show advanced settings' }).click(T);
    await page.getByRole('radio', { name: 'Yes, AI was used' }).click(T); log.push('ai');
    await page.getByRole('radio', { name: /No, my video doesn/ }).click(T);
    const tg = page.getByRole('textbox', { name: 'Tags' }); await tg.fill(M.tags, T); await tg.press('Enter', T); log.push('tags');
    await page.waitForTimeout(600);
    log.push('chk:' + await page.evaluate(() => { const q = s => document.querySelector('ytcp-uploads-dialog ' + s); return [q('#title-textarea #textbox')?.innerText, q('#description-textarea #textbox')?.innerText.length, q('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')?.checked, q('[name="VIDEO_HAS_ALTERED_CONTENT_YES"]')?.checked, document.querySelectorAll('ytcp-uploads-dialog ytcp-chip').length, q('ytcp-video-metadata-playlists')?.innerText.trim()].join('/'); }));
  } catch (e) { log.push('ERR ' + String(e).slice(0, 160)); }
  return log.join(' > ');
}
"""

B = """async (page) => {
  const M = __M__; const T = { timeout: 8000 }; const log = [];
""" + SURVEY + """  try {
    await closeSurvey();
    const next = () => page.getByRole('button', { name: 'Next', exact: true }).click(T);
    await next();
    await page.locator('#shorts-content-links-add-button').getByRole('button', { name: 'Add' }).click(T);
    await page.getByRole('option', { name: new RegExp('^' + M.opt, 'i') }).click(T);
    await page.waitForTimeout(900);
    log.push('rel:' + await page.evaluate(() => /Related video Connect another of your videos to your video (.{0,40})/.exec((document.querySelector('ytcp-uploads-dialog ytcp-uploads-video-elements')?.innerText || '').replace(/\\s+/g, ' '))?.[1]));
    await next(); await page.waitForTimeout(700); await next(); await page.waitForTimeout(700);
    await closeSurvey();
    if (!(await page.locator('ytcp-uploads-dialog ytcp-visibility-scheduler input').count())) await page.getByRole('button', { name: 'Click to expand' }).last().click(T);
    await page.waitForTimeout(400);
    await page.locator('ytcp-uploads-dialog ytcp-visibility-scheduler').getByRole('button', { name: /, 2026/ }).last().click(T);
    const di = page.getByLabel('Enter date').locator('input'); await di.click(T); await page.keyboard.press('Control+a'); await di.fill(M.date, T); await di.press('Enter', T);
    await page.waitForTimeout(500);
    const ti = page.locator('ytcp-uploads-dialog ytcp-visibility-scheduler input'); await ti.click(T); await page.keyboard.press('Control+a'); await ti.fill(M.time, T); await ti.press('Enter', T);
    await page.waitForTimeout(500);
    const sched = await page.evaluate(() => { const s = document.querySelector('ytcp-uploads-dialog ytcp-visibility-scheduler'); return (s?.innerText || '').replace(/\\s+/g, ' ').slice(0, 30) + '|' + s?.querySelector('input')?.value; });
    log.push('sched:' + sched);
    if (!sched.includes(M.date) || !sched.endsWith('|' + M.time)) return 'STOP ' + log.join(' > ');
    await page.getByRole('button', { name: 'Schedule', exact: true }).click(T); log.push('clicked');
  } catch (e) { log.push('ERR ' + String(e).slice(0, 160)); }
  return log.join(' > ');
}
"""

TAGS = "epic metal,symphonic metal,power metal,metal shorts,war metal,epic music,gaming music,workout music,battle music,world metal empire,"


def dedupe_hashtags(desc):
    lines = desc.split('\n')
    last = lines[-1]
    if last.startswith('#'):
        seen, out = set(), []
        for t in last.split():
            if t.lower() not in seen:
                seen.add(t.lower()); out.append(t)
        lines[-1] = ' '.join(out)
    return '\n'.join(lines)


def main(vid):
    items = {m['id']: m for m in json.loads(META.read_text(encoding='utf-8'))}
    m = items[vid]
    d = datetime.date.fromisoformat(m['date'])
    hh, mm = map(int, m['time_msk'].split(':'))
    meta = {
        'title': m['title'], 'description': dedupe_hashtags(m['description']), 'tags': TAGS,
        'opt': re.escape(TRACK_OPT[m['full_video']]),
        'date': d.strftime('%b ') + str(d.day) + d.strftime(', %Y'),
        'time': f"{hh % 12 or 12}:{mm:02d} {'AM' if hh < 12 else 'PM'}",
    }
    js = json.dumps(meta, ensure_ascii=False)
    (OUT / f'{vid}_a.js').write_text(A.replace('__M__', js), encoding='utf-8')
    (OUT / f'{vid}_b.js').write_text(B.replace('__M__', js), encoding='utf-8')
    print(vid, meta['date'], meta['time'], TRACK_OPT[m['full_video']])


if __name__ == '__main__':
    for v in sys.argv[1:]:
        main(v)
