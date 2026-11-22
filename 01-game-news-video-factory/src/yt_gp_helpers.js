() => { window.__gp = {
  sl: ms => new Promise(r => setTimeout(r, ms)),
  vis: e => e.getBoundingClientRect().height > 0,
  dlg: () => document.querySelector('ytcp-uploads-dialog'),
  chan: () => ((document.querySelector('ytcp-navigation-drawer, ytcp-navigation, #navigation') || document.body).innerText).includes('Game Pulse News'),
  ready: () => { const b = document.querySelectorAll('ytcp-uploads-dialog #textbox[contenteditable]'); return b.length >= 2 && b[0].innerText.trim().length > 0; },
  async fill(d) {
    const boxes = [...this.dlg().querySelectorAll('#textbox[contenteditable]')];
    const put = async (el, text) => { el.focus(); document.execCommand('selectAll'); document.execCommand('delete');
      const lines = text.split('\n'); for (let i = 0; i < lines.length; i++) { if (i) document.execCommand('insertLineBreak'); if (lines[i]) document.execCommand('insertText', false, lines[i]); }
      el.blur(); await this.sl(400); };
    await put(boxes[0], d.title); await put(boxes[1], d.description);
    return {titleOk: boxes[0].innerText.trim() === d.title, descLen: boxes[1].innerText.trim().length};
  },
  async lc() { const dl = this.dlg(); const res = {};
    const trig = [...dl.querySelectorAll('ytcp-dropdown-trigger [role=button]')].filter(e => e.innerText.includes('Язык видео')); trig[trig.length - 1].click();
    let it; for (let i = 0; i < 20 && !it; i++) { await this.sl(200); it = [...document.querySelectorAll('tp-yt-paper-item')].find(x => x.innerText.trim() === 'Английский' && this.vis(x)); }
    res.lang = !!it; it?.click(); await this.sl(800);
    const ct = [...dl.querySelectorAll('ytcp-dropdown-trigger [role=button]')].filter(e => e.innerText.trim() === 'Люди и блоги'); res.cn = ct.length;
    if (ct.length) { ct[ct.length - 1].click(); let opt; for (let i = 0; i < 20 && !opt; i++) { await this.sl(200); opt = [...document.querySelectorAll('tp-yt-paper-item, [role=option]')].find(o => o.innerText.trim() === 'Игры' && this.vis(o)); }
      res.opt = !!opt; opt?.click(); await this.sl(1000); }
    return res; },
  async game() { let o; for (let i = 0; i < 15 && !o; i++) { await this.sl(200); o = [...document.querySelectorAll('tp-yt-paper-item, [role=option]')].find(o => /^Grand Theft Auto VI\s*2026/.test(o.innerText.trim()) && this.vis(o)); }
    if (!o) return 'no opt'; o.click(); await this.sl(1000); return 'ok'; },
  check() { const dl = this.dlg(); const t = dl.innerText; const g = re => (t.match(re) || [null])[0];
    return {lang: g(/Язык видео\s*\n?\s*[^\n]+/)?.replace(/\s+/g, ' '), cat: t.includes('\nИгры\n'), tags: g(/\d+\/500/),
      game: [...dl.querySelectorAll('input')].map(i => i.value).filter(v => /Grand Theft/.test(v)).length,
      radios: [...dl.querySelectorAll('tp-yt-paper-radio-button[checked]')].map(r => r.innerText.trim().slice(0, 12)).join('|'),
      progress: (dl.querySelector('.progress-label, ytcp-video-upload-progress') || {}).innerText || '', verify: g(/[^\n]*(подтвер|Подтвер)[^\n]*/)}; },
  head() { return this.dlg().innerText.split('\n')[0].trim(); },
  tagDate() { const els = [...this.dlg().querySelectorAll('[role=button]')].filter(e => /^\d+\s\S+\s2026\sг\.$/.test(e.innerText.replace(/\s+/g, ' ').trim()) && this.vis(e));
    document.querySelectorAll('[data-dv]').forEach(e => e.removeAttribute('data-dv')); if (els.length) els[els.length - 1].setAttribute('data-dv', 'date'); return els.length; },
  tagTime() { const i = [...this.dlg().querySelectorAll('input')].find(x => /^\d{1,2}:\d\d$/.test(x.value) && this.vis(x)); if (i) i.setAttribute('data-dv', 'time'); return !!i; },
  rb() { return {date: document.querySelector('[data-dv=date]')?.innerText.replace(/\s+/g, ' ').trim(), time: document.querySelector('[data-dv=time]')?.value}; },
  doneDlg() { return [...document.querySelectorAll('tp-yt-paper-dialog, ytcp-dialog')].filter(this.vis).find(x => x.innerText.includes('Публикация видео запланирована') || (x.innerText.startsWith('Обработка видео') && x.innerText.includes('установим'))); },
  async closeRes() { const dl = this.doneDlg(); if (!dl) return {none: true}; const t = dl.innerText.split('\n'); const r = {text: t.find(l => /2026 г\. в \d/.test(l)), link: dl.querySelector('a[href*="youtu"]')?.href};
    const b = [...dl.querySelectorAll('ytcp-button, button')].find(x => x.innerText.trim() === 'Закрыть'); b?.click(); await this.sl(1200); return r; }
}; return 'ok'; }
