"""Generates Playwright scripts (for D.A.V.E. browser_run_code_unsafe) that upload one video to
YouTube Studio (Game Pulse News) and schedule it. A_<id>.js = upload + details, B_<id>.js = schedule.
Usage: python yt_studio_scripts.py  -> writes into H:\\GameClips_Канал\\.dave-work\\yt\\"""
import json, pathlib

ROOT = pathlib.Path(r"H:\GameClips_Канал")
OUT = ROOT / ".dave-work" / "yt"
OUT.mkdir(parents=True, exist_ok=True)
MONTHS = ["янв.", "февр.", "мар.", "апр.", "мая", "июн.", "июл.", "авг.", "сент.", "окт.", "нояб.", "дек."]
CHANNEL = "UCVTV79tn8Ap07EiKKa3qBng"

A = r"""async (page) => {
const d = __DATA__;
const out = {id: d.id};
const navTxt = await page.evaluate(() => (document.querySelector('ytcp-navigation-drawer, ytcp-navigation, #navigation')||document.body).innerText.slice(0,400));
if (!navTxt.includes('Game Pulse News')) return {err: 'wrong channel', navTxt};
const dlg = page.locator('ytcp-uploads-dialog');
await page.getByRole('button', {name: 'Создать'}).click();
await page.waitForTimeout(700);
await page.getByRole('menuitem', {name: /Загрузить видео|Добавить видео/}).first().click();
await page.waitForTimeout(1500);
await dlg.locator('input[type=file]').first().setInputFiles(d.file);
return out;
}"""

F = r"""async (page) => {
const d = __DATA__;
const out = {id: d.id};
try {
const dlg = page.locator('ytcp-uploads-dialog');
await page.waitForFunction(() => { const b = document.querySelectorAll('ytcp-uploads-dialog #textbox[contenteditable]'); return b.length >= 2 && b[0].innerText.trim().length > 0; }, null, {timeout: 40000});
await page.waitForTimeout(1500);
out.fill = await page.evaluate(async (d) => {
  const boxes = [...document.querySelectorAll('ytcp-uploads-dialog #textbox[contenteditable]')];
  const put = async (el, text) => { el.focus(); document.execCommand('selectAll'); document.execCommand('delete');
    const lines = text.split('\n'); for (let i = 0; i < lines.length; i++) { if (i) document.execCommand('insertLineBreak'); if (lines[i]) document.execCommand('insertText', false, lines[i]); }
    el.blur(); await new Promise(r => setTimeout(r, 400)); };
  await put(boxes[0], d.title); await put(boxes[1], d.description);
  return {titleOk: boxes[0].innerText.trim() === d.title, descLen: boxes[1].innerText.trim().length};
}, d);
await dlg.getByRole('radio', {name: 'Нет, это видео не для детей'}).click();
await dlg.getByRole('button', {name: 'Показать дополнительные настройки'}).click();
await page.waitForTimeout(800);
await dlg.getByRole('radio', {name: 'Нет, в видео нет прямой рекламы'}).click();
await dlg.getByRole('radio', {name: 'Да, ИИ использовался'}).click();
await dlg.getByRole('textbox', {name: 'Теги'}).fill(d.tags + ',');
await page.waitForTimeout(500);
out.lc = await page.evaluate(async () => { const sl = ms => new Promise(r => setTimeout(r, ms)); const dl = document.querySelector('ytcp-uploads-dialog'); const res = {};
  const vis = e => e.getBoundingClientRect().height > 0;
  const trig = [...dl.querySelectorAll('ytcp-dropdown-trigger [role=button]')].filter(e => e.innerText.includes('Язык видео')); trig[trig.length - 1].click();
  let it; for (let i = 0; i < 20 && !it; i++) { await sl(200); it = [...document.querySelectorAll('tp-yt-paper-item')].find(x => x.innerText.trim() === 'Английский' && vis(x)); }
  res.lang = !!it; it?.click(); await sl(800);
  const ct = [...dl.querySelectorAll('ytcp-dropdown-trigger [role=button]')].filter(e => e.innerText.trim() === 'Люди и блоги'); res.cn = ct.length;
  if (ct.length) { ct[ct.length - 1].click(); let opt; for (let i = 0; i < 20 && !opt; i++) { await sl(200); opt = [...document.querySelectorAll('tp-yt-paper-item, [role=option]')].find(o => o.innerText.trim() === 'Игры' && vis(o)); }
    res.opt = !!opt; opt?.click(); await sl(1000); }
  return res; });
const game = dlg.getByRole('textbox', {name: 'Название игры (необязательно)'});
await game.pressSequentially('Grand Theft Auto VI', {delay: 30});
await page.waitForTimeout(1500);
out.game = await page.evaluate(async () => { const o = [...document.querySelectorAll('tp-yt-paper-item, [role=option]')].find(o => /^Grand Theft Auto VI\s*2026/.test(o.innerText.trim()) && o.getBoundingClientRect().height > 0);
  if (!o) return 'no opt'; o.click(); await new Promise(r => setTimeout(r, 1000)); return 'ok'; });
if (d.thumbnail) {
  try { await dlg.locator('input[type=file][accept*=image]').first().setInputFiles(d.thumbnail); out.thumb = 'sent'; } catch (e) { out.thumb = 'err ' + String(e).slice(0, 120); }
  await page.waitForTimeout(3000);
}
out.check = await page.evaluate(() => { const t = document.querySelector('ytcp-uploads-dialog').innerText;
  const g = (re) => (t.match(re) || [null])[0];
  return {lang: g(/Язык видео\s*\n?\s*[^\n]+/), cat: t.includes('\nИгры\n'), tags: g(/\d+\/500/),
          game: [...document.querySelectorAll('ytcp-uploads-dialog input')].map(i => i.value).filter(v => /Grand Theft/.test(v)),
          progress: (document.querySelector('ytcp-uploads-dialog .progress-label, ytcp-video-upload-progress')||{}).innerText || '',
          thumbErr: g(/[^\n]*(подтвер|Подтвер)[^\n]*/)}; });
return out;
} catch (e) { out.err = String(e).slice(0, 400); return out; }
}"""

B = r"""async (page) => {
const d = __DATA__;
try {
const dlg = page.locator('ytcp-uploads-dialog');
const t = await page.evaluate(() => document.querySelector('ytcp-uploads-dialog').innerText.split('\n')[0].trim());
if (t !== d.title) return {err: 'title mismatch', t};
await dlg.getByRole('tab', {name: 'Доступ'}).click();
await page.waitForTimeout(1200);
const sched = dlg.getByRole('button', {name: 'Запланировать публикацию'});
if (!(await sched.isVisible().catch(() => false))) { await dlg.getByRole('button', {name: 'Click to expand'}).last().click(); await page.waitForTimeout(1000); }
await page.evaluate(() => { const els = [...document.querySelectorAll('ytcp-uploads-dialog [role=button]')].filter(e => /^\d+\s\S+\s2026\sг\.$/.test(e.innerText.replace(/\s+/g, ' ').trim()) && e.getBoundingClientRect().height > 0);
  els.forEach(e => e.removeAttribute('data-dv')); if (els.length) els[els.length - 1].setAttribute('data-dv', 'date'); });
await page.locator('[data-dv=date]').click();
await page.waitForTimeout(700);
const di = page.getByLabel('Укажите дату').locator('input');
await di.fill(d.dateRu); await di.press('Enter');
await page.waitForTimeout(700);
await page.evaluate(() => { const i = [...document.querySelectorAll('ytcp-uploads-dialog input')].find(x => /^\d{1,2}:\d\d$/.test(x.value) && x.getBoundingClientRect().height > 0); if (i) i.setAttribute('data-dv', 'time'); });
const ti = page.locator('[data-dv=time]');
await ti.click(); await ti.press('Control+a'); await ti.fill(d.time); await ti.press('Enter');
await page.waitForTimeout(800);
const rb = await page.evaluate(() => ({date: document.querySelector('[data-dv=date]')?.innerText.replace(/\s+/g, ' ').trim(), time: document.querySelector('[data-dv=time]')?.value,
  tz: (document.querySelector('ytcp-uploads-dialog').innerText.match(/GMT[^)]*\)/) || [''])[0],
  progress: (document.querySelector('ytcp-uploads-dialog .progress-label, ytcp-video-upload-progress') || {}).innerText || ''}));
if (rb.date !== d.dateRu || rb.time !== d.time) return {err: 'date/time mismatch', rb};
if (!d.commit) return {ready: true, rb};
await sched.click();
await page.getByText('Публикация видео запланирована').waitFor({timeout: 45000});
const res = await page.evaluate(() => { const dl = [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog')].find(x => x.innerText.includes('Публикация видео запланирована'));
  return {text: dl.innerText.slice(0, 250), link: dl.querySelector('a[href*="youtu"]')?.href}; });
await page.getByRole('button', {name: 'Закрыть', exact: true}).last().click().catch(() => {});
return {done: true, rb, res};
} catch (e) { return {err: String(e).slice(0, 400)}; }
}"""

U = r"""async (page) => { const d = __DATA__; const o = {id: d.id}; const dlg = page.locator('ytcp-uploads-dialog'); try {
if (!(await page.evaluate(() => !!window.__gp))) return {err: 'inject'};
if (!(await page.evaluate(() => __gp.chan()))) return {err: 'channel'};
if (d.up) {
await page.getByRole('button', {name: 'Создать'}).click(); await page.waitForTimeout(700);
await page.getByRole('menuitem', {name: /Загрузить видео|Добавить видео/}).first().click(); await page.waitForTimeout(1500);
await dlg.locator('input[type=file]').first().setInputFiles(d.file);
await page.waitForFunction(() => __gp.ready(), null, {timeout: 40000}); await page.waitForTimeout(1500);
o.fill = await page.evaluate(d => __gp.fill(d), d);
await dlg.getByRole('radio', {name: 'Нет, это видео не для детей'}).click();
await dlg.getByRole('button', {name: 'Показать дополнительные настройки'}).click(); await page.waitForTimeout(800);
await dlg.getByRole('radio', {name: 'Нет, в видео нет прямой рекламы'}).click();
await dlg.getByRole('radio', {name: 'Да, ИИ использовался'}).click();
await dlg.getByRole('textbox', {name: 'Теги'}).fill(d.tags + ','); await page.waitForTimeout(500);
o.lc = await page.evaluate(() => __gp.lc());
await dlg.getByRole('textbox', {name: 'Название игры (необязательно)'}).pressSequentially('Grand Theft Auto VI', {delay: 30});
o.game = await page.evaluate(() => __gp.game());
if (d.thumbnail) { try { await dlg.locator('input[type=file][accept*=image]').first().setInputFiles(d.thumbnail); await page.waitForTimeout(3000); o.thumb = 'sent'; } catch (e) { o.thumb = String(e).slice(0, 150); } }
o.check = await page.evaluate(() => __gp.check());
if (!o.fill.titleOk || !o.check.cat || !o.check.game || !/Английский/.test(o.check.lang || '')) return o;
}
if (await page.evaluate(() => __gp.head()) !== d.title) { o.err = 'title mismatch'; return o; }
await dlg.getByRole('tab', {name: 'Доступ'}).click(); await page.waitForTimeout(1200);
const sched = dlg.getByRole('button', {name: 'Запланировать публикацию'});
if (!(await sched.isVisible().catch(() => false))) { await dlg.getByRole('button', {name: 'Click to expand'}).last().click(); await page.waitForTimeout(1000); }
await page.evaluate(() => __gp.tagDate()); await page.locator('[data-dv=date]').click(); await page.waitForTimeout(700);
const di = page.getByLabel('Укажите дату').locator('input'); await di.fill(d.dateRu); await di.press('Enter'); await page.waitForTimeout(700);
await page.evaluate(() => __gp.tagTime()); const ti = page.locator('[data-dv=time]');
await ti.click(); await ti.press('Control+a'); await ti.fill(d.time); await ti.press('Enter'); await page.waitForTimeout(800);
o.rb = await page.evaluate(() => __gp.rb());
if (o.rb.date !== d.dateRu || o.rb.time !== d.time) { o.err = 'date/time mismatch'; return o; }
await sched.click();
await page.waitForFunction(() => !!__gp.doneDlg(), null, {timeout: 45000});
o.res = await page.evaluate(() => __gp.closeRes());
o.done = true; return o;
} catch (e) { o.err = String(e).slice(0, 300); return o; } }"""

plan = json.loads((ROOT / "Автоматизация" / "youtube_upload_plan.json").read_text(encoding="utf-8"))
for p in plan:
    y, m, dd = map(int, p["date"].split("-"))
    data = dict(p, dateRu=f"{dd} {MONTHS[m - 1]} {y} г.", commit=True)
    js = json.dumps(data, ensure_ascii=False)
    (OUT / f"A_{p['id']}.js").write_text(A.replace("__DATA__", js).replace("__CH__", CHANNEL), encoding="utf-8")
    (OUT / f"F_{p['id']}.js").write_text(F.replace("__DATA__", js), encoding="utf-8")
    (OUT / f"B_{p['id']}.js").write_text(B.replace("__DATA__", json.dumps({k: data[k] for k in ("id", "title", "dateRu", "time", "commit")}, ensure_ascii=False)), encoding="utf-8")
    keys = ("id", "file", "title", "description", "tags", "dateRu", "time") + (("thumbnail",) if "thumbnail" in p else ())
    ud = {k: data[k] for k in keys}; ud["up"] = True
    (OUT / f"U_{p['id']}.js").write_text(U.replace("__DATA__", json.dumps(ud, ensure_ascii=False)), encoding="utf-8")
print("written", len(plan), "x2 to", OUT)
