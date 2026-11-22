"""Генерирует код для browser_run_code_unsafe: замена ТОЛЬКО таймкодов глав в описаниях треков WME.
Берёт план H:/YouTube_2_канала/.dave-work/timecodes_plan.json, пишет .dave-work/wme_js/tc_<N>.js по 2 трека."""
import json, os

PLAN = r"H:\YouTube_2_канала\.dave-work\timecodes_plan.json"
OUTD = r"H:\YouTube_2_канала\.dave-work\wme_js"
plan = json.load(open(PLAN, encoding="utf-8"))
items = [{"id": vid, "old": [c["old"] for c in p["chapters"]], "new": [c["new_tc"] for c in p["chapters"]]} for vid, p in plan.items()]

TEMPLATE = r"""async (page) => {
  const ITEMS = __ITEMS__;
  const out = [];
  for (const it of ITEMS) {
    await page.goto('https://studio.youtube.com/video/' + it.id + '/edit?authuser=3');
    const desc = page.locator('ytcp-video-description #textbox');
    await desc.waitFor({ timeout: 15000 }); await page.waitForTimeout(800);
    const before = await desc.innerText();
    const lines = before.split('\n');
    const idx = []; let inCh = false;
    for (let i = 0; i < lines.length; i++) {
      if (/CHAPTERS:/.test(lines[i])) { inCh = true; continue; }
      if (inCh) { if (/^\d+:\d{2}\s/.test(lines[i])) idx.push(i); else if (idx.length) break; }
    }
    const olds = idx.map(i => lines[i].match(/^(\d+:\d{2})/)[1]);
    if (olds.join(',') !== it.old.join(',') && olds.join(',') !== it.new.join(',')) { out.push(it.id + ' STOP old mismatch: ' + olds.join(',')); continue; }
    if (olds.join(',') === it.new.join(',')) { out.push(it.id + ' already new'); continue; }
    idx.forEach((i, k) => { lines[i] = lines[i].replace(/^\d+:\d{2}/, it.new[k]); });
    const after = lines.join('\n');
    await desc.click(); await page.keyboard.press('Control+a'); await desc.fill(after);
    await page.waitForTimeout(500);
    const typed = await desc.innerText();
    if (typed.trimEnd() !== after.trimEnd()) { out.push(it.id + ' STOP typed differs len ' + typed.length + '/' + after.length); continue; }
    const saveBtn = page.locator('ytcp-button#save');
    await page.waitForTimeout(400);
    await saveBtn.click({ timeout: 8000 });
    let saved = false;
    for (let i = 0; i < 12 && !saved; i++) { await page.waitForTimeout(600); saved = await saveBtn.evaluate(e => e.hasAttribute('disabled')); }
    out.push(it.id + ' saved=' + saved + ' ' + it.new.join(','));
  }
  return out.join('\n');
}"""

os.makedirs(OUTD, exist_ok=True)
for n in range(0, len(items)):
    code = TEMPLATE.replace("__ITEMS__", json.dumps(items[n:n + 1]))
    open(os.path.join(OUTD, f"tc1_{n + 1:02d}_{items[n]['id']}.js"), "w", encoding="utf-8").write(code)
print("ok", len(items), "files")
