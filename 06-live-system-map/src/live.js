/* Город D.A.V.E. — живое обновление данных (общий модуль 2D и 3D).
   Раз в минуту заново подгружает data.js тегом <script src="data.js?t=…"> (на file:// fetch не работает),
   пересобирает кабинеты (DAVE_BUILD_ROOMS) и сообщает странице через DAVE_LIVE.onUpdate(fn) —
   страница сама обновляет надписи и мониторы на месте, не трогая камеру и открытый кабинет.
   В углу — значок «обновлено ЧЧ:ММ» (время сборки data.js). data.js пишет build_data.py по расписанию
   (Планировщик заданий Windows, каждые 10 минут). Подключение: <script src="live.js" data-src="data.js"></script>. */
(function () {
  'use strict';
  const me = document.currentScript;
  const SRC = (me && me.dataset.src) || 'data.js';
  const PERIOD = +((me && me.dataset.period) || 60000);
  const STALE_MIN = 25;               // сборка старше — значит, автообновление не отработало
  const SNAP = !!window.DAVE_SNAPSHOT; // переносная копия (share\): данные вшиты, обновлять нечего
  const fns = [];
  let lastJson = JSON.stringify(window.DAVE_DATA || {}), busy = false, failed = false, checked = new Date();

  const badge = document.createElement('div');
  badge.id = 'live-badge';
  badge.setAttribute('role', 'status');
  badge.innerHTML = '<i></i><span></span>';
  (document.body || document.documentElement).appendChild(badge);

  const hhmm = d => String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  function paint() {
    const D = window.DAVE_DATA || {}, C = D.counts || {};
    const built = D.generated_ms ? new Date(D.generated_ms) : null;
    if (SNAP) {
      const dd = built ? String(built.getDate()).padStart(2, '0') + '.' + String(built.getMonth() + 1).padStart(2, '0') + ' ' + hhmm(built) : (D.generated || '—');
      badge.querySelector('span').textContent = 'снимок от ' + dd;
      badge.className = '';
      badge.title = 'Переносная копия: данные зафиксированы на момент сборки файла и не обновляются.';
      return;
    }
    const stale = !built || Date.now() - D.generated_ms > STALE_MIN * 60000;
    let txt = 'обновлено ' + (built ? hhmm(built) : (D.generated || '—').slice(-5));
    const live = (C.live_chats || 0) + (C.live_agents || 0);
    if (live) txt += ' · в работе: ' + (C.live_chats || 0) + ' ч., ' + (C.live_agents || 0) + ' аг.';
    if (failed) txt += ' · data.js не читается';
    else if (stale) txt += ' · данные устарели';
    badge.querySelector('span').textContent = txt;
    badge.className = failed || stale ? 'warn' : live ? 'live' : '';
    badge.title = 'Данные собраны: ' + (D.generated || '—') + '\nСтраница проверила data.js: ' + hhmm(checked) +
      '\nСборка идёт каждые 10 минут (Планировщик заданий Windows), страница проверяет раз в минуту.' +
      (stale ? '\nСборка старше ' + STALE_MIN + ' минут — проверь задание «DAVE City — обновление данных».' : '');
  }

  function apply(D) {
    const json = JSON.stringify(D || {});
    if (json === lastJson) return false;
    lastJson = json;
    if (window.DAVE_BUILD_ROOMS) window.DAVE_BUILD_ROOMS(D);
    for (const fn of fns) {
      try { fn(D); } catch (e) { console.error('[город] обновление не применилось:', e); }
    }
    return true;
  }

  function reload() {
    if (busy) return Promise.resolve(false);
    busy = true;
    return new Promise(res => {
      const s = document.createElement('script');
      s.src = SRC + (SRC.includes('?') ? '&' : '?') + 't=' + Date.now();
      s.onload = () => { s.remove(); busy = false; failed = false; checked = new Date(); const ch = apply(window.DAVE_DATA); paint(); res(ch); };
      s.onerror = () => { s.remove(); busy = false; failed = true; checked = new Date(); paint(); res(false); };
      document.head.appendChild(s);
    });
  }

  if (!SNAP) {
    setInterval(reload, PERIOD);
    setInterval(paint, 30000);        // «данные устарели» появляется и без новой загрузки
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') reload(); });
  }
  paint();
  window.DAVE_LIVE = { reload, paint, apply, onUpdate: fn => fns.push(fn), get checked() { return checked; } };
})();
