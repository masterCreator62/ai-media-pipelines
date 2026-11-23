/* Город D.A.V.E. — кабинеты и сотрудники. Общий модуль для 2D и 3D.
   Всё, что зависит от конфигурации, берётся из data.js (window.DAVE_DATA), который пишет build_data.py.
   Описания встроенных частей (законы, инструменты, спутник) — постоянные тексты; помечены по точности.
   Живое обновление: страница заново подгружает data.js и вызывает window.DAVE_BUILD_ROOMS(data) — объекты
   DAVE_ROOMS / DAVE_KEY2ROOM / DAVE_INFO_PATCH остаются теми же (очищаются и заполняются заново), поэтому ссылки на них не устаревают. */
(function () {
  'use strict';
  const ROOMS = {}, KEY2ROOM = {}, P = {};
  window.DAVE_ROOMS = ROOMS;
  window.DAVE_KEY2ROOM = KEY2ROOM;
  window.DAVE_INFO_PATCH = P;
  const OK = 'Подтверждено', COND = 'Условно', DECO = 'Декор';

  // склонение: plural(5, 'агент', 'агента', 'агентов')
  const plural = (n, a, b, c) => { const m10 = n % 10, m100 = n % 100; return n + ' ' + (m10 === 1 && m100 !== 11 ? a : m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20) ? b : c); };
  const cut = (s, n) => !s ? '' : s.length > n ? s.slice(0, n - 1).trimEnd() + '…' : s;

  const SKILL_GROUPS = {
    gamedev: 'Геймдев', 'roblox-s': 'Roblox', router: 'Маршрутизатор', youtube: 'YouTube Shorts',
    news: 'GAME PULSE', workshop: 'Мастерская (свои конвейеры)', builtin: 'Встроенные'
  };
  const MEM_TYPES = { user: 'о тебе', feedback: 'урок / правило', project: 'проект', reference: 'ссылка', note: 'заметка' };
  const RESULT = { done: 'выполнена', waiting: 'ждёт тебя', '': '' };

  /* ---------- сотрудник ----------
     key — уникальный, name — на экране, role — подпись, conf — точность,
     screen: { head, status, ok (зелёный статус), lines[] }, text — полный текст для панели, crew — сколько ещё людей у стола */
  function staff(key, name, role, conf, status, ok, lines, text, crew) {
    return { key, name, role, conf, crew: crew || 0, live: false, screen: { head: name, status, ok, live: false, lines: lines.filter(Boolean) }, text };
  }
  /* «работает сейчас»: журнал чата или агента менялся за последние live_min минут (по данным сборки) */
  function markLive(s, at, lines) {
    lines = lines.filter(Boolean);
    s.live = true; s.screen.live = true; s.screen.ok = true;
    s.screen.status = 'Работает сейчас · активность ' + at;
    s.screen.lines = lines.concat(s.screen.lines);
    s.text = 'Работает сейчас: журнал менялся ' + at + '. ' + lines.join(' ') + ' ' + s.text;
    return s;
  }

  function room(id, o) { ROOMS[id] = Object.assign({ id, staff: [] }, o); return ROOMS[id]; }

  function build(D) {
  D = D || {};
  for (const k of ['agents', 'builtin_agents', 'skills', 'memory', 'projects', 'scheduled', 'chats', 'mcp', 'sat']) D[k] = D[k] || [];
  const C = D.counts || {};
  for (const o of [ROOMS, KEY2ROOM, P]) for (const k of Object.keys(o)) delete o[k];
  const chatById = Object.fromEntries(D.chats.map(c => [c.id, c]));
  const agentLive = (s, a) => a.live ? markLive(s, a.live_at, [
    'Сейчас: «' + a.live_task + '»' + (a.live_n > 1 ? ' (и ещё ' + (a.live_n - 1) + ')' : ''),
    a.live_chat ? 'Чат «' + cut(a.live_chat, 70) + '»' + (chatById[a.live_chat_id] && chatById[a.live_chat_id].last_msg ? ': «' + chatById[a.live_chat_id].last_msg + '»' : '') : '']) : s;

  /* ---------- 1. Терминал агентов ---------- */
  {
    const r = room('agents', { title: 'Терминал агентов', sub: 'Аэропорт агентов · ' + plural(C.builtin_agents + C.agents, 'сотрудник', 'сотрудника', 'сотрудников'),
      color: '#b48cff', conf: OK,
      intro: 'За каждым столом — один агент. Встроенные агенты Claude Code сидят в первом ряду у вывески,' + plural(C.agents, 'специалист', 'специалиста', 'специалистов') +
        ' VoltAgent — в общем зале. На мониторе — специализация и статус: когда агента последний раз вызывали и с какой задачей (найдено в журналах чатов).' });
    const status = a => a.runs ? 'Последний вызов ' + a.last + ' · всего ' + plural(a.runs, 'раз', 'раза', 'раз') : 'Ожидает вызова — ещё не запускался';
    for (const a of D.builtin_agents) {
      r.staff.push(agentLive(staff('bi-' + a.id, a.ru + ' · ' + a.id, 'Встроенный агент Claude Code', OK, status(a), !!a.runs,
        [a.desc, a.task ? 'Последняя задача: «' + a.task + '»' : ''],
        a.desc + ' ' + status(a) + (a.task ? '. Последняя задача: «' + a.task + '».' : '.')), a));
    }
    for (const a of D.agents) {
      r.staff.push(agentLive(staff('ag-' + a.id, a.id, 'Специалист VoltAgent · DAVE\\agents', OK, status(a), !!a.runs,
        [cut(a.desc, 280), a.task ? 'Последняя задача: «' + a.task + '»' : 'Запускаю по твоей просьбе'],
        a.desc + ' ' + status(a) + (a.task ? '. Последняя задача: «' + a.task + '».' : '.') + (a.tools ? ' Инструменты: ' + a.tools + '.' : '')), a));
    }
    const nLive = r.staff.filter(s => s.live).length;
    if (nLive) r.sub += ' · ' + nLive + ' в работе';
  }

  /* ---------- 2. Академия навыков ---------- */
  {
    const r = room('skills', { title: 'Академия навыков', sub: plural(C.skills, 'преподаватель', 'преподавателя', 'преподавателей') + ' · DAVE\\skills',
      color: '#c3f25c', conf: OK,
      intro: 'Каждый преподаватель — один навык. В контексте висит только список навыков; полный текст (SKILL.md) я читаю, когда задача совпадает. На доске монитора — чему учит навык.' });
    const order = ['workshop', 'news', 'youtube', 'router', 'roblox-s', 'gamedev'];
    const list = D.skills.slice().sort((a, b) => order.indexOf(a.group) - order.indexOf(b.group) || a.id.localeCompare(b.id));
    for (const s of list) {
      r.staff.push(staff('sk-' + s.id, s.id, 'Корпус «' + SKILL_GROUPS[s.group] + '»', OK, 'Готов · обновлён ' + s.updated, true,
        [cut(s.desc, 330)], s.desc + ' Файл обновлён ' + s.updated + '.'));
    }
  }

  /* ---------- 3. Штаб проектов ---------- */
  {
    const r = room('projects', { title: 'Штаб проектов', sub: plural(C.projects, 'команда', 'команды', 'команд') + ' · DAVE\\projects', color: '#ff6fae', conf: OK,
      intro: 'Каждый стол — команда одного проекта. На мониторе — текущее состояние из его главного документа (overview.md или первый .md): описание и дата последнего обновления.' });
    for (const p of D.projects) {
      const big = p.files > 30 ? 2 : p.files > 8 ? 1 : 0;
      r.staff.push(staff('pr-' + p.slug, p.slug, cut(p.name, 60), OK, (p.doc ? p.doc + ' · ' : '') + 'обновлён ' + p.updated, true,
        [cut(p.desc, 230), p.where ? 'Диск ' + p.where + ' · ' + plural(p.files, 'объект', 'объекта', 'объектов') + ' в корне' : ''],
        p.desc + (p.lead ? ' — ' + p.lead : '') + ' Документ: ' + (p.doc || 'нет') + ', обновлён ' + p.updated + '.', big));
    }
  }

  /* ---------- 4. Часовая башня ---------- */
  {
    const r = room('clock', { title: 'Часовая башня · дежурные', sub: plural(C.scheduled, 'задача', 'задачи', 'задач') + ' по расписанию', color: '#ffe6b0', conf: OK,
      intro: 'Каждый дежурный — одна задача, которую D.A.V.E. сам запускает по времени. Данные — из списка «По расписанию» на момент снимка ' + D.snapshot_at + '.' });
    for (const t of D.scheduled) {
      const st = t.paused ? 'На паузе' : t.next ? 'Следующий запуск: ' + t.next : 'Больше не запускается';
      r.staff.push(staff('sc-' + t.name, t.name, t.schedule, OK, st, !t.paused && !!t.next,
        ['Расписание: ' + t.schedule, t.last_at ? 'Прошлый запуск ' + t.last_at + (RESULT[t.last_result] ? ' — ' + RESULT[t.last_result] : '') : '', cut(t.last_note, 170),
          t.skill ? 'Навык: ' + t.skill : ''],
        'Расписание: ' + t.schedule + '. ' + st + '. ' + (t.last_at ? 'Прошлый запуск ' + t.last_at + ': ' : '') + (t.last_note || '')));
    }
  }

  /* ---------- 5. Жители: чаты ---------- */
  for (const [id, withSum] of [['chats', true], ['chats-old', false]]) {
    const list = D.chats.filter(c => c.summary === withSum);
    const r = room(id, withSum
      ? { title: 'Жилой массив · жители', sub: plural(list.length, 'чат', 'чата', 'чатов') + ' со сводкой', color: '#ffcf8a', conf: OK,
          intro: 'Каждый житель — недавний чат, который уже сжимался: на экране его название и строка последней сводки из chat-summaries (как её записал движок, поэтому часто по-английски).' }
      : { title: 'Старый квартал · жители', sub: plural(list.length, 'чат', 'чата', 'чатов') + ' без сводки', color: '#8a96c4', conf: OK,
          intro: 'Чаты, которые ещё ни разу не сжимались, поэтому сводки у них нет. Названия — из снимка списка чатов (' + D.snapshot_at + '), меток передачи между чатами и первых сообщений.' });
    r.intro += ' Зелёный мигающий огонёк — чат работает сейчас (журнал менялся за последние ' + (D.live_min || 10) + ' минут), на экране — последнее сообщение человека.';
    for (const c of list) {
      const s = staff('ch-' + c.id, c.title, 'Чат ' + c.id, OK,
        withSum ? 'Сводка ' + c.at + ' · ' + plural(c.sections, 'раздел', 'раздела', 'разделов') : c.mt ? 'Последняя активность ' + c.mt : 'Сводки нет — чат не сжимался', withSum,
        withSum ? [cut(c.line, 230)] : ['Сводки нет — чат не сжимался. Полная история — в журнале чата; прочитать его можно по названию.'],
        withSum ? 'Последняя сводка (' + c.at + '): ' + c.line : 'Чат ещё не сжимался, поэтому сводки нет. Полная история лежит в журнале.' + (c.mt ? ' Последняя активность ' + c.mt + '.' : ''));
      if (c.live) markLive(s, c.mt, [c.last_msg ? 'Последняя задача: «' + c.last_msg + '»' : '']);
      r.staff.push(s);
    }
    const nLive = list.filter(c => c.live).length;
    if (nLive) r.sub += ' · ' + nLive + ' работают сейчас';
  }

  /* ---------- 6. Порт MCP ---------- */
  {
    const r = room('mcp', { title: 'Порт MCP · экипажи', sub: plural(C.mcp, 'корабль', 'корабля', 'кораблей'), color: '#4fd1ff', conf: OK,
      intro: 'Каждый пульт — экипаж одного MCP-модуля. На экране — откуда модуль подключён и его инструменты. Claude Docs виден в этой сессии как коннектор аккаунта claude.ai, но в настройках его могли выключить — поэтому «Условно».' });
    for (const m of D.mcp) {
      const tl = m.tools_known ? m.tools : [];
      r.staff.push(staff('mcp-' + m.key, m.name, 'MCP · ' + m.id, m.conf, m.source, m.conf === OK,
        [m.desc, tl.length ? plural(tl.length, 'инструмент', 'инструмента', 'инструментов') + ': ' + cut(tl.join(', '), 330) : 'Список инструментов неизвестен'],
        m.desc + ' Подключение: ' + m.source + '. ' + (tl.length ? 'Инструменты (' + tl.length + '): ' + tl.join(', ') + '.' : ''), tl.length > 20 ? 2 : 1));
    }
  }

  /* ---------- 7. Сад памяти ---------- */
  {
    const r = room('memory', { title: 'Сад памяти · архивариусы', sub: plural(C.memory, 'факт', 'факта', 'фактов') + ' · brain\\memory', color: '#ff6fae', conf: OK,
      intro: 'Каждый архивариус хранит один факт — один файл. Каталог этих описаний подаётся в каждый чат, поэтому я «помню» между чатами.' });
    for (const m of D.memory) {
      r.staff.push(staff('mem-' + m.file, m.name, 'Факт · ' + (MEM_TYPES[m.type] || m.type), OK, 'Обновлён ' + m.updated, true,
        [cut(m.desc, 240)], m.desc + ' Файл ' + m.file + ', обновлён ' + m.updated + '.'));
    }
  }

  /* ---------- 8. Хранилище сводок и журналов ---------- */
  {
    const sums = D.chats.filter(c => c.summary);
    const r = room('summaries', { title: 'Хранилище сводок и журналов', sub: plural(sums.length, 'сводка', 'сводки', 'сводок') + ' · ' + plural(C.transcripts, 'журнал', 'журнала', 'журналов'), color: '#ff6fae', conf: OK,
      intro: 'При каждом сжатии контекста сюда дописывается раздел сводки. Журналы — полные записи разговоров: по ним я нахожу то, что выпало при сжатии.' });
    r.staff.push(staff('jr-all', 'Журналы чатов', 'Хранитель журналов', OK, plural(C.transcripts, 'файл', 'файла', 'файлов') + ' .jsonl', true,
      ['Полные записи разговоров Claude Code.', 'Отсюда build_data.py узнал, каких агентов и когда вызывали.'],
      'Полные записи разговоров (' + C.transcripts + ' файлов). Из них я читаю другой чат по просьбе и нахожу потерянное при сжатии.'));
    for (const c of sums) {
      r.staff.push(staff('sm-' + c.id, c.title, 'Сводка чата ' + c.id, OK, plural(c.sections, 'раздел', 'раздела', 'разделов') + ' · ' + c.at, true,
        [cut(c.line, 200)], 'Разделов: ' + c.sections + '. Последний: ' + c.at + '. ' + c.line));
    }
  }

  /* ---------- 9. Квартал законов (постоянные тексты) ---------- */
  {
    const r = room('laws', { title: 'Квартал законов · канцелярия', sub: 'правила и библиотека гайдов', color: '#f5b942', conf: OK,
      intro: 'Тексты, которые лежат в контексте до твоего первого слова. Клерки — главные своды правил, библиотекари — гайды по функциям D.A.V.E., которые я загружаю только по делу.' });
    const LAWS = [
      ['core-brain', 'Core Brain', 'Базовые правила D.A.V.E.', 'Тон, самостоятельность, где хранить файлы, память и проекты, когда спрашивать подтверждение.'],
      ['yesman', 'Анти-лесть', 'Not a yes man', 'Оценка идей с рисками и цифрами, блок самопроверки при оценке твоих решений.'],
      ['security', 'Безопасность', 'Секреты и данные', 'Секреты не печатаются, пароли не хранятся в памяти, удаление и отправка — с подтверждением.'],
      ['brainmd', 'BRAIN.md', 'Твои правила · главнее базовых', 'Доводить до конца, минимум вопросов, «Задача завершена», перенос перегруженного чата, самообучение. Всё сохранять на диск H.'],
      ['onboarding', 'Онбординг', 'Знакомство', 'Показывать делом, а не лекцией.']];
    for (const [k, n, role, t] of LAWS) r.staff.push(staff('law-' + k, n, role, OK, 'Действует в каждом чате', true, [t], t));
    const GUIDES = [['apps', 'Программы на ПК'], ['authoring', 'Правка инструкций'], ['automation', 'Задачи по расписанию'], ['browser', 'Браузер'],
      ['chats', 'Чаты и файлы'], ['collaboration', 'Работа между чатами'], ['connections', 'Подключение сервисов'], ['files', 'Файлы и документы'],
      ['import-export', 'Импорт и экспорт'], ['knowledge', 'Память и проекты'], ['media-generation', 'Картинки и видео'], ['models', 'Движки и модели'],
      ['privacy', 'Приватность'], ['product', 'О D.A.V.E.'], ['scraping', 'Сбор данных с сайтов'], ['skills', 'Навыки и агенты'],
      ['support', 'Поиск неполадок'], ['telegram', 'Telegram']];
    for (const [k, n] of GUIDES) r.staff.push(staff('gd-' + k, 'Гайд «' + n + '»', 'Библиотека гайдов', OK, 'Загружается по необходимости', true,
      ['Подробная инструкция D.A.V.E. по теме «' + n + '». В контекст попадает только когда задача её требует.'],
      'Гайд «' + n + '» (' + k + '): загружается только когда нужен, чтобы не занимать контекст.'));
  }

  /* ---------- 10. Промзона ---------- */
  {
    const r = room('tools', { title: 'Промзона · цеха', sub: 'встроенные инструменты Claude Code', color: '#ff8a3d', conf: OK,
      intro: 'Мои «руки» на твоём ПК. Ядро только пишет заказ, а Claude Code исполняет его в одном из этих цехов. Список — инструменты, доступные в этой сессии.' });
    for (const [k, n, t] of [
      ['shell', 'PowerShell', 'Любая команда: запуск программ и скриптов, установка пакетов, git, видео.'],
      ['read', 'Read', 'Читает файлы, включая картинки и PDF.'],
      ['write', 'Write', 'Создаёт новые файлы.'],
      ['edit', 'Edit', 'Точечная правка: заменяет фрагмент, а не весь файл.'],
      ['grep', 'Grep', 'Поиск по содержимому файлов (ripgrep).'],
      ['glob', 'Glob', 'Поиск файлов по именам и шаблонам путей.'],
      ['agent', 'Agent', 'Запуск агента с отдельным контекстом.'],
      ['skill', 'Skill', 'Загрузка навыка из Академии.'],
      ['toolsearch', 'ToolSearch', 'Достаёт описание инструмента, которого нет в списке сразу.'],
      ['web', 'WebSearch и web-fetch', 'Поиск в интернете и чтение страниц.'],
      ['python', 'Python (свой)', 'Свой Python D.A.V.E.: данные, PDF, картинки — без установки в систему. На нём работает build_data.py.'],
      ['ffmpeg', 'ffmpeg (свой)', 'Видео и звук: нарезка, склейка, перекодирование.']])
      r.staff.push(staff('tl-' + k, n, 'Цех промзоны', OK, 'Работает по заказу ядра', true, [t], t));
  }

  /* ---------- 11. Город-спутник ---------- */
  {
    const up = Object.fromEntries((D.sat || []).map(s => [s.key, s.up]));
    const live = (k, port) => up[k] ? 'Запущен: порт ' + port + ' отвечал при сборке ' + D.generated : 'Не запущен при сборке ' + D.generated;
    const r = room('sat', { title: 'Город-спутник · операторы', sub: 'отдельные программы с ИИ на твоём ПК', color: '#ff6b6b', conf: OK,
      intro: 'Помощники за рекой — отдельные программы, не часть моего ядра. Статус «запущен» — проверка порта в момент сборки данных.' });
    r.staff.push(staff('sat-freellm', 'FreeLLMAPI · :31415', 'Роутер бесплатных моделей · подключён ко мне', OK, live('freellm', 31415), !!up.freellm,
      ['Сотни бесплатных моделей за одним адресом. Сюда уходит второстепенная работа — например, перевод описаний для этой карты.', 'Личные данные туда не отправляю.'],
      'Роутер бесплатных моделей. Подключён навыком freellmapi и скриптом ask.ps1; build_data.py переводит через него описания агентов и навыков. ' + live('freellm', 31415) + '.', 1));
    r.staff.push(staff('sat-lmstudio', 'LM Studio · :1234', 'Сервер локальных моделей', OK, live('lmstudio', 1234), !!up.lmstudio,
      ['Модели на твоей видеокарте и ОЗУ, без интернета. Загружает модель по первому запросу, выгружает через час простоя.'],
      'Локальный сервер моделей. ' + live('lmstudio', 1234) + '. Навыка для меня нет — дорога к нему пешеходная.'));
    r.staff.push(staff('sat-qwen36', 'Qwen3.6-35B-A3B', 'Основная модель Hermes', OK, up.lmstudio ? 'Сервер работает' : 'Ждёт запуска LM Studio', !!up.lmstudio,
      ['Около 30 токенов/с, контекст 128K, видеопамять ~7,4 ГБ.'], 'MoE-модель: около 30 токенов в секунду. Работает через LM Studio.'));
    r.staff.push(staff('sat-qwen38', 'Qwen3.8-27B', 'Запасная модель', OK, up.lmstudio ? 'Сервер работает' : 'Ждёт запуска LM Studio', !!up.lmstudio,
      ['Около 3 токенов/с: на 8 ГБ влезает 10 слоёв из 64.'], 'Плотная модель 27B, медленная на этой видеокарте.'));
    r.staff.push(staff('sat-hermes', 'Hermes Agent', 'Самостоятельный локальный агент', OK, 'Мне не подчиняется — статус не отслеживается', false,
      ['Свой агент на моделях LM Studio: файлы и команды. Запускается ярлыком «Hermes — локальный ИИ».'], 'Отдельный локальный агент, параллельный город со своим мэром.'));
    r.staff.push(staff('sat-comfyui', 'ComfyUI · :8188', 'Локальные картинки · новый', OK, live('comfyui-sat', 8188), !!up['comfyui-sat'],
      ['Z-Image-Turbo и FLUX.1 schnell (Apache-2.0) на RTX 3060 Ti. Бесплатно, без интернета.', 'Сервер запускается через gen.py --start или модуль MCP.'],
      'Генерация картинок на видеокарте: Z-Image-Turbo и FLUX.1 schnell. Подключён ко мне MCP-модулем comfyui и скриптом gen.py. ' + live('comfyui-sat', 8188) + '.', 1));
  }

  /* ---------- 12. Ратуша ---------- */
  {
    const r = room('gate', { title: 'Ратуша D.A.V.E.', sub: 'само приложение', color: '#e8ecff', conf: OK,
      intro: 'Службы приложения D.A.V.E., которые работают до и после каждого моего хода.' });
    r.staff.push(staff('gt-context', 'Сборщик контекста', 'Перед каждым ходом', OK, 'Работает на каждом сообщении', true,
      ['Законы + BRAIN.md + каталоги: ' + plural(C.memory, 'факт', 'факта', 'фактов') + ', ' + plural(C.projects, 'проект', 'проекта', 'проектов') + ', ' + plural(C.skills, 'навык', 'навыка', 'навыков') + ', ' + plural(C.agents, 'агент', 'агента', 'агентов') + '.', 'Плюс история чата.'],
      'Собирает контекст перед каждым ходом из законов, твоих правил, каталогов памяти, проектов, навыков и агентов.'));
    r.staff.push(staff('gt-tg', 'Telegram', 'Связь с телефона', OK, 'У каждого чата своя тема', true, ['Ответы и файлы уходят в тему этого чата в Telegram-группе.'], 'Связь с телефона через Telegram.'));
    r.staff.push(staff('gt-voice', 'Голосовой ввод', 'Голос → текст', OK, 'Облачное распознавание', true, ['Голос превращается в текст и едет дальше как обычное сообщение.'], 'Голосовой ввод через облачное распознавание.'));
    r.staff.push(staff('gt-sched', 'Диспетчер расписания', 'Запускает дежурных', OK, plural(C.scheduled, 'задача', 'задачи', 'задач'), true, ['Запускает задачи часовой башни в нужных чатах.'], 'Запускает задачи по расписанию.'));
    r.staff.push(staff('gt-db', 'Хранитель чатов', 'База и журналы', OK, plural(C.chats, 'чат', 'чата', 'чатов') + ' на карте · ' + (C.live_chats || 0) + ' работают сейчас', true, ['Хранит чаты, вкладки, превью и сводки.'], 'Хранит базу чатов.'));
  }

  /* ---------- 13. Внешний мир ---------- */
  {
    const r = room('world', { title: 'Внешний мир · узел связи', sub: 'интернет и программы ПК', color: '#5be39a', conf: OK,
      intro: 'Куда ведут дороги из города.' });
    r.staff.push(staff('wd-web', 'Интернет', 'WebSearch · web-fetch', OK, 'По запросу', true, ['Свежие факты, цены и версии проверяю здесь: мои знания — на дату обучения.'], 'Поиск и чтение страниц.'));
    r.staff.push(staff('wd-apps', 'Программы на ПК', 'Через «Управление ПК» и свои API', OK, 'С разрешения на каждую программу', true,
      ['Roblox Studio, Blender, ComfyUI, RHI, Discord, CapCut и другие.'], 'Программы на ПК: доступ через MCP-модуль «Управление ПК» или собственные API программ.'));
  }

  /* ---------- какой ключ ведёт в какой кабинет ---------- */
  const map =(room, keys, focus) => keys.forEach(k => KEY2ROOM[k] = [room, typeof focus === 'function' ? focus(k) : focus || null]);
  map('agents', ['dz-agents', 'plane']);
  map('agents', ['general', 'explore', 'plan', 'fork', 'workflow'], k => 'bi-' + { general: 'general-purpose', explore: 'Explore', plan: 'Plan', fork: 'fork', workflow: 'workflow' }[k]);
  D.agents.forEach(a => map('agents', ['ag-' + a.id], 'ag-' + a.id));
  map('skills', ['dz-skills']);
  Object.keys(SKILL_GROUPS).forEach(g => { const s = D.skills.find(x => x.group === g); map('skills', [g], s ? 'sk-' + s.id : null); });
  map('projects', ['projects']); map('memory', ['facts', 'dz-memory']); map('summaries', ['summaries']); map('summaries', ['transcripts'], 'jr-all');
  map('clock', ['scheduler']); map('chats', ['chats']); map('chats-old', ['chats-old']);
  map('mcp', ['dz-mcp']); D.mcp.forEach(m => map('mcp', [m.key], 'mcp-' + m.key));
  map('laws', ['dz-laws']); ['core-brain', 'yesman', 'security', 'brainmd', 'onboarding'].forEach(k => map('laws', [k], 'law-' + k)); map('laws', ['guides'], 'gd-apps');
  map('tools', ['dz-tools']); map('tools', ['shell'], 'tl-shell'); map('tools', ['files'], 'tl-read'); map('tools', ['search'], 'tl-grep'); map('tools', ['python'], 'tl-python');
  map('world', ['dz-world']); map('world', ['internet'], 'wd-web'); map('world', ['apps'], 'wd-apps');
  map('sat', ['dz-sat', 'road-free', 'road-lm']); ['freellm', 'lmstudio', 'qwen36', 'qwen38', 'hermes'].forEach(k => map('sat', [k], 'sat-' + k)); map('sat', ['comfyui-sat'], 'sat-comfyui');
  map('gate', ['dz-gate', 'daveapp']); map('gate', ['telegram'], 'gt-tg'); map('gate', ['voice'], 'gt-voice'); map('gate', ['sergey'], 'gt-context');

  /* ---------- обновлённые описания объектов города: [название, где, точность, текст] ---------- */
  const agentHangar = a => ['Агент ' + a.id, 'Второй терминал · VoltAgent' + (a.live ? ' · работает сейчас' : ''), OK,
    (a.live ? 'Работает сейчас (' + a.live_at + '): «' + a.live_task + '». ' : '') + a.desc + ' ' + (a.runs ? 'Последний вызов ' + a.last + (a.task ? ' — «' + a.task + '»' : '') + '.' : 'Ещё не запускался — ожидает вызова.')];
  D.agents.forEach(a => P['ag-' + a.id] = agentHangar(a));
  // встроенные ангары: описание меняется только пока агент работает (иначе — постоянный текст страницы)
  const BI_KEY = { 'general-purpose': 'general', Explore: 'explore', Plan: 'plan', fork: 'fork', workflow: 'workflow' };
  D.builtin_agents.forEach(a => { if (a.live && BI_KEY[a.id]) P[BI_KEY[a.id]] = [a.ru + ' · ' + a.id, 'Аэропорт агентов · работает сейчас', OK,
    'Работает сейчас (' + a.live_at + '): «' + a.live_task + '»' + (a.live_chat ? ' — в чате «' + cut(a.live_chat, 60) + '»' : '') + '. ' + a.desc + ' Всего вызовов: ' + a.runs + '.']; });
  P['dz-agents'] = ['Аэропорт агентов', C.builtin_agents + ' встроенных + ' + C.agents + ' специалистов', OK,
    'Отсюда «вылетают» мои копии с отдельным контекстом: поиск, ревью, исследование. Пять больших ангаров — встроенные агенты Claude Code. Второй терминал — ' +
    plural(C.agents, 'специалист', 'специалиста', 'специалистов') + ' из набора VoltAgent (MIT) в DAVE\\agents. Зайди внутрь — у каждого свой стол и монитор со статусом.'];
  const gc = g => D.skills.filter(s => s.group === g).length;
  P['dz-skills'] = ['Академия навыков', plural(C.skills, 'навык', 'навыка', 'навыков') + ' + встроенные', OK,
    'Навыки — папки с инструкциями и скриптами. В контексте висит только их список; полный текст я читаю, когда задача совпадает. Свои: ' + C.skills + ' (геймдев ' + gc('gamedev') + ', Roblox ' + gc('roblox-s') + ', мастерская ' + gc('workshop') + ', медиа ' + (gc('youtube') + gc('news')) + ', маршрутизатор ' + gc('router') + ').'];
  P.gamedev = ['Корпус «Геймдев · ' + gc('gamedev') + '»', 'Академия навыков', OK, 'ИИ врагов, камеры, физика, звук, UI, сохранения, процедурная генерация, RPG, tower defense, шейдеры, производительность.'];
  P['roblox-s'] = ['Корпус «Roblox · ' + gc('roblox-s') + '»', 'Академия навыков', OK, 'Luau, персонажи, DataStore, сеть и анти-чит, физика, экономика симуляторов, UI, безопасная работа со Studio.'];
  P.workshop = ['Корпус «Мастерская · ' + gc('workshop') + '»', 'Академия навыков · новый', OK, 'Свои конвейеры: agent-team-workflow (команда агентов с критиком и тестами), image-render-pipeline (картинки и рендеры), freellmapi (бесплатные модели).'];
  P.facts = ['Сад памяти · ' + C.memory, 'Архив памяти · brain\\memory', OK, 'Каждое светящееся дерево — один факт в отдельном файле. Каталог сада подаётся в каждый чат — так я «помню». Внутри — архивариусы, у каждого на экране свой факт.'];
  P.projects = ['Площадь проектов · ' + C.projects, 'Архив памяти · projects', OK, 'Обелиски — проекты: ' + D.projects.map(p => p.slug).join(', ') + '. Все лежат на диске H. Внутри — штаб, у каждой команды на мониторе состояние проекта.'];
  P.summaries = ['Хранилище сводок · ' + C.summaries, 'Архив памяти · chat-summaries', OK, 'При каждом сжатии контекста сюда дописывается раздел, чтобы потерянное можно было найти.'];
  P.transcripts = ['Хранилище журналов · ' + C.transcripts, 'Архив памяти', OK, 'Полные записи разговоров (' + C.transcripts + ' файлов). Из них же видно, каких агентов и когда вызывали.'];
  P.guides = ['Библиотека гайдов · 18', 'Квартал законов', OK, 'Подробные инструкции D.A.V.E. по функциям: браузер, файлы, программы, Telegram, медиа, расписание. Загружаются только когда нужны.'];
  P.scheduler = ['Часовая башня · ' + plural(C.scheduled, 'задача', 'задачи', 'задач'), 'Въезд', OK, 'Задачи, которые D.A.V.E. сам запускает по времени: ' + D.scheduled.map(t => t.name).join('; ') + '. Внутри — дежурные со статусом каждой задачи.'];
  P.chats = ['Жилой массив · ' + C.summaries + ' чатов со сводкой', 'Светящиеся дома', OK, 'Каждый светящийся дом — недавний чат D.A.V.E. Соседи не ходят друг к другу в гости: чаты не видят друг друга, пока ты не попросишь прочитать другой чат.' +
    (C.live_chats ? ' Сейчас работают ' + plural(C.live_chats, 'чат', 'чата', 'чатов') + ': ' + D.chats.filter(c => c.live).map(c => '«' + cut(c.title, 40) + '»').join(', ') + '.' : '')];
  P['chats-old'] = ['Старый квартал · ' + (C.chats - C.summaries) + ' чатов без сводки', 'Тусклые дома', OK, 'Чаты, которые ещё не сжимались. Они не удалены и открываются по названию.'];
  P['dz-mcp'] = ['Порт MCP · ' + plural(C.mcp, 'корабль', 'корабля', 'кораблей'), 'Подключённые модули', OK, 'MCP — стандарт, по которому к Claude Code пристыковываются внешние модули: ' + D.mcp.map(m => m.name).join(', ') + '.'];
  D.mcp.forEach(m => P[m.key] = ['Корабль «' + m.name + '»', 'Порт MCP · ' + m.id, m.conf, m.desc + ' ' + m.source + '. ' + (m.tools_known ? plural(m.tools.length, 'инструмент', 'инструмента', 'инструментов') + '.' : '')]);
  const sat = Object.fromEntries((D.sat || []).map(s => [s.key, s.up]));
  P['comfyui-sat'] = ['ComfyUI · :8188', 'Город-спутник · новый', OK, 'Локальная генерация картинок на RTX 3060 Ti: Z-Image-Turbo и FLUX.1 schnell (Apache-2.0). Подключён ко мне MCP-модулем и скриптом gen.py. ' + (sat['comfyui-sat'] ? 'Сервер работал при сборке.' : 'При сборке сервер не был запущен — стартует по запросу.')];
  P['dz-sat'] = ['Город-спутник', 'ИИ-помощники на твоём ПК', OK, 'Отдельные «мозги», не часть моего ядра. К FreeLLMAPI ведёт автомобильный мост (навык и скрипт), к ComfyUI — MCP-модуль, к LM Studio — только пешеходный мостик. Hermes мне не подчиняется.'];

  return ROOMS;
  }   /* build */

  window.DAVE_SKILL_GROUPS = SKILL_GROUPS;
  window.DAVE_BUILD_ROOMS = build;
  build(window.DAVE_DATA);
})();
