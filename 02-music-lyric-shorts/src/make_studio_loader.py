# Короткий режим загрузки Shorts WME (22.11.2026): один раз кладёт в localStorage вкладки Studio
# общий код и данные всех роликов, дальше на каждый ролик — вызов в одну строку:
#   browser_run_code_unsafe filename=.dave-work/wme_js/_loader.js      (один раз на вкладку)
#   browser_run_code_unsafe code="async page => eval(await page.evaluate(() => localStorage.wmeFn))(page, 'V24')"
#   (после browser_act Create→Upload→Select files и browser_file_upload)
# Функция делает детали + связанное видео + расписание; если первая часть заняла >10 с, возвращает SPLIT —
# тогда тот же вызов с третьим аргументом 'p2' (лимит одного вызова run_code ~30 с).
import json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = ROOT / '.dave-work' / 'wme_js'

data = {}
for f in sorted(JS.glob('WME_V*_a.js')):
    vid = re.match(r'WME_(V\d+)_', f.name).group(1)
    data[vid] = json.loads(re.search(r'const M = (\{.*?\}); const T', f.read_text(encoding='utf-8'), re.S).group(1))

FN = r"""(async (page, id, mode) => {
  const M = JSON.parse(await page.evaluate(() => localStorage.wmeData))[id]; const T = { timeout: 9000 }; const log = [id]; const t0 = Date.now();
  const closeSurvey = async () => { const sv = page.locator('iframe[name="google-hats-survey"]'); if (await sv.count()) { try { await sv.contentFrame().getByRole('button', { name: 'Close user survey dialog' }).click({ timeout: 2000 }); } catch (e) {} } };
  const norm = s => String(s || '').replace(/[\s  ]+/g, ' ').trim();
  const next = () => page.getByRole('button', { name: 'Next', exact: true }).click(T);
  try {
    if (mode !== 'p2') {
      await page.getByText('Reuse details').first().waitFor({ state: 'visible', timeout: 20000 }); await page.waitForTimeout(1500);
      await closeSurvey();
      await page.locator('ytcp-uploads-dialog #title-textarea #textbox').fill(M.title, T);
      await page.locator('ytcp-uploads-dialog #description-textarea #textbox').fill(M.description, T);
      await page.getByRole('radio', { name: "No, it's not made for kids" }).click(T);
      if (!(await page.getByRole('radio', { name: 'Yes, AI was used' }).isVisible())) await page.getByRole('button', { name: 'Show advanced settings' }).click(T);
      await page.getByRole('radio', { name: 'Yes, AI was used' }).click(T);
      await page.getByRole('radio', { name: /No, my video doesn/ }).click(T);
      if (await page.locator('ytcp-uploads-dialog ytcp-chip').count() < 10) { const tg = page.getByRole('textbox', { name: 'Tags' }); await tg.fill(M.tags, T); await tg.press('Enter', T); }
      await page.waitForTimeout(500);
      const chk = await page.evaluate(() => { const q = s => document.querySelector('ytcp-uploads-dialog ' + s); return [q('#title-textarea #textbox')?.innerText, q('#description-textarea #textbox')?.innerText.length, q('[name="VIDEO_MADE_FOR_KIDS_NOT_MFK"]')?.checked, q('[name="VIDEO_HAS_ALTERED_CONTENT_YES"]')?.checked, document.querySelectorAll('ytcp-uploads-dialog ytcp-chip').length, q('ytcp-video-metadata-playlists')?.innerText.trim()].join('/'); });
      log.push('chk:' + chk);
      if (!chk.startsWith(M.title + '/') || !chk.endsWith('/true/true/10/Select')) return 'STOP ' + log.join(' > ');
      await closeSurvey();
      await next();
      await page.locator('#shorts-content-links-add-button').getByRole('button', { name: 'Add' }).click(T);
      await page.getByRole('option', { name: new RegExp('^' + M.opt, 'i') }).click(T);
      await page.waitForTimeout(800);
      const rel = await page.evaluate(() => /Related video Connect another of your videos to your video (.{0,40})/.exec((document.querySelector('ytcp-uploads-dialog ytcp-uploads-video-elements')?.innerText || '').replace(/\s+/g, ' '))?.[1]);
      log.push('rel:' + rel);
      if (!rel || !new RegExp('^' + M.opt, 'i').test(rel)) return 'STOP ' + log.join(' > ');
      await next(); await page.waitForTimeout(600); await next(); await page.waitForTimeout(600);
      log.push('link:' + await page.evaluate(() => [...document.querySelectorAll('ytcp-uploads-dialog a[href*="/shorts/"]')].map(a => a.href.split('/shorts/')[1].split('?')[0]).join(',')));
      if (Date.now() - t0 > 10000) return 'SPLIT ' + log.join(' > ') + ' [' + Math.round((Date.now() - t0) / 1000) + 's]';
    }
    await closeSurvey();
    if (!(await page.locator('ytcp-uploads-dialog ytcp-visibility-scheduler input').count())) await page.getByRole('button', { name: 'Click to expand' }).last().click(T);
    await page.waitForTimeout(400);
    await page.locator('ytcp-uploads-dialog ytcp-visibility-scheduler').getByRole('button', { name: /, 2026/ }).last().click(T);
    const di = page.getByLabel('Enter date').locator('input'); await di.click(T); await page.keyboard.press('Control+a'); await di.fill(M.date, T); await di.press('Enter', T);
    await page.waitForTimeout(500);
    const ti = page.locator('ytcp-uploads-dialog ytcp-visibility-scheduler input'); await ti.click(T); await page.keyboard.press('Control+a'); await ti.fill(M.time, T); await ti.press('Enter', T);
    await page.waitForTimeout(500);
    const sched = norm(await page.evaluate(() => { const s = document.querySelector('ytcp-uploads-dialog ytcp-visibility-scheduler'); return (s?.innerText || '').slice(0, 15) + '|' + s?.querySelector('input')?.value; }));
    log.push('sched:' + sched);
    if (!sched.includes(M.date) || !sched.endsWith('|' + norm(M.time))) return 'STOP ' + log.join(' > ');
    if (mode === 'p2') log.push('link:' + await page.evaluate(() => [...document.querySelectorAll('ytcp-uploads-dialog a[href*="/shorts/"]')].map(a => a.href.split('/shorts/')[1].split('?')[0]).join(',')));
    await page.getByRole('button', { name: 'Schedule', exact: true }).click(T);
    const msg = page.getByText(/will be set to public on/).last(); await msg.waitFor({ state: 'visible', timeout: 12000 });
    log.push('done:' + norm(await msg.innerText()).replace(/^Your video will be set to public on /, '').slice(0, 40));
    try { await page.locator('tp-yt-paper-dialog, ytcp-dialog, ytcp-video-share-dialog').getByRole('button', { name: 'Close', exact: true }).last().click({ timeout: 3000 }); } catch (e) {}
  } catch (e) { log.push('ERR ' + String(e).slice(0, 200)); }
  return log.join(' > ') + ' [' + Math.round((Date.now() - t0) / 1000) + 's]';
})"""

loader = ("async (page) => { await page.evaluate(([f, d]) => { localStorage.wmeFn = f; localStorage.wmeData = d; }, "
          + json.dumps([FN, json.dumps(data, ensure_ascii=False)], ensure_ascii=False)
          + "); return 'loaded ' + Object.keys(JSON.parse(await page.evaluate(() => localStorage.wmeData))).length; }")
(JS / '_loader.js').write_text(loader, encoding='utf-8')
print('ok', len(data), len(loader))



