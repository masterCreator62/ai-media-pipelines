/* Город D.A.V.E. — интерьеры зданий (3D).
   Подключается после основного скрипта 3d/index.html и пользуется его сценой, камерой, композером и панелью.
   Кабинеты и сотрудники — из ../rooms.js (данные ../data.js). */
(function () {
  'use strict';
  // те же объекты, что пересобирает DAVE_BUILD_ROOMS при живом обновлении (rooms.js очищает и заполняет их заново)
  const ROOMS = window.DAVE_ROOMS || {}, K2R = window.DAVE_KEY2ROOM || {};
  const LIVE = '#37ff7a';
  const IS = new THREE.Scene();
  IS.background = new THREE.Color(0x03050b);
  const st = { active: false, room: null, pick: [], desks: [], figs: [], saved: null, overview: null, enterKey: null, focus: null };

  /* ---------- материалы и текстуры ---------- */
  const lm = (color, o = {}) => new THREE.MeshStandardMaterial(Object.assign({ color, roughness: .8, metalness: .05 }, o));
  const SKIN = [0xf1c27d, 0xe0ac69, 0xc68642, 0x8d5524, 0xffdbac, 0xd8a07a];
  const HAIR = [0x2b1b0e, 0x5a3825, 0x1a1a1a, 0xa0522d, 0xd9b26b, 0x3a3a46];
  let disposables = [];
  const track = x => (disposables.push(x), x);
  const untrack = x => { disposables = disposables.filter(y => y !== x); x && x.dispose && x.dispose(); };

  function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  function tex(c, srgb = true) { const t = track(new THREE.CanvasTexture(c)); if (srgb) t.encoding = THREE.sRGBEncoding; t.anisotropy = 8; return t; }
  function wrap(g, text, maxW) {
    const out = []; let line = '';
    for (const word of String(text).split(/\s+/)) {
      const test = line ? line + ' ' + word : word;
      if (g.measureText(test).width > maxW && line) { out.push(line); line = word; } else line = test;
    }
    if (line) out.push(line);
    return out;
  }
  const FONT = '"Segoe UI", system-ui, sans-serif';

  /* экран монитора: шапка с именем, строка статуса, текст задачи, метка точности */
  function screenTexture(s, color) {
    const W = 1024, H = 640, c = canvas(W, H), g = c.getContext('2d');
    const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#0d1630'); bg.addColorStop(1, '#091022');
    g.fillStyle = bg; g.fillRect(0, 0, W, H);
    const live = !!s.screen.live;
    g.fillStyle = color; g.globalAlpha = .9; g.fillRect(0, 0, W, 96); g.globalAlpha = 1;
    g.fillStyle = '#0a0f1e'; g.font = `700 46px ${FONT}`; g.textBaseline = 'middle';
    let pill = 0;
    if (live) {   // плашка «РАБОТАЕТ» в шапке
      g.font = `800 28px ${FONT}`; pill = g.measureText('● РАБОТАЕТ').width + 36;
      g.fillStyle = '#062611'; roundRect(g, W - pill - 18, 24, pill, 50, 25); g.fill();
      g.fillStyle = LIVE; g.fillText('● РАБОТАЕТ', W - pill, 50);
      g.font = `700 46px ${FONT}`; g.fillStyle = '#0a0f1e'; pill += 30;
    }
    let head = s.screen.head; while (g.measureText(head).width > W - 60 - pill && head.length > 4) head = head.slice(0, -2);
    if (head !== s.screen.head) head = head.slice(0, -1) + '…';
    g.fillText(head, 30, 50);
    // статус
    g.fillStyle = live ? LIVE : s.screen.ok ? '#5be39a' : '#ffc95a';
    g.beginPath(); g.arc(44, 140, 13, 0, 2 * Math.PI); g.fill();
    if (live) { g.strokeStyle = LIVE; g.lineWidth = 3; g.beginPath(); g.arc(44, 140, 21, 0, 2 * Math.PI); g.stroke(); }
    g.font = `600 32px ${FONT}`; g.fillStyle = live ? '#b9ffd0' : s.screen.ok ? '#9ff5c4' : '#ffe0a0';
    const stl = wrap(g, s.screen.status, W - 100);
    g.fillText(stl[0] + (stl.length > 1 ? '…' : ''), 72, 141);
    g.fillStyle = 'rgba(255,255,255,.12)'; g.fillRect(30, 178, W - 60, 2);
    // текст
    g.font = `400 34px ${FONT}`; g.fillStyle = '#e6ecff';
    let y = 222; const LH = 44, maxY = H - 70;
    outer: for (const para of s.screen.lines) {
      for (const ln of wrap(g, para, W - 70)) {
        if (y > maxY) { g.fillText('…', 35, y - LH + 2); break outer; }
        g.fillText(ln, 35, y); y += LH;
      }
      y += 12;
    }
    // точность
    const conf = s.conf, cc = conf.startsWith('Условно') ? ['#3a2c0c', '#f5b942'] : conf === 'Декор' ? ['#22273a', '#aab3d6'] : ['#0f3326', '#5be39a'];
    g.font = `600 24px ${FONT}`; const cw = g.measureText(conf).width + 36;
    g.fillStyle = cc[0]; roundRect(g, W - cw - 24, H - 52, cw, 36, 18); g.fill();
    g.fillStyle = cc[1]; g.fillText(conf, W - cw - 6, H - 33);
    g.fillStyle = 'rgba(200,210,245,.45)'; g.font = `400 22px ${FONT}`; g.fillText(cutTo(g, s.role, W - cw - 80), 30, H - 33);
    if (live) { g.strokeStyle = LIVE; g.lineWidth = 10; g.strokeRect(5, 5, W - 10, H - 10); }
    return tex(c);
  }
  function cutTo(g, t, w) { if (g.measureText(t).width <= w) return t; while (t.length > 3 && g.measureText(t + '…').width > w) t = t.slice(0, -1); return t + '…'; }

  function signTexture(room) {
    const c = canvas(2048, 300), g = c.getContext('2d');
    g.fillStyle = '#0b1124'; g.fillRect(0, 0, 2048, 300);
    g.strokeStyle = room.color; g.lineWidth = 8; roundRect(g, 8, 8, 2032, 284, 30); g.stroke();
    g.fillStyle = room.color; g.font = `700 112px ${FONT}`; g.textBaseline = 'middle'; g.textAlign = 'center';
    g.fillText(room.title, 1024, 118);
    g.fillStyle = '#c8d2f5'; g.font = `400 56px ${FONT}`; g.fillText(room.sub || '', 1024, 222);
    return tex(c);
  }
  function floorTexture(color) {
    const c = canvas(256, 256), g = c.getContext('2d');
    g.fillStyle = '#1a2033'; g.fillRect(0, 0, 256, 256);
    g.fillStyle = '#1f2640'; g.fillRect(0, 0, 128, 128); g.fillRect(128, 128, 128, 128);
    g.strokeStyle = 'rgba(255,255,255,.05)'; g.lineWidth = 2; g.strokeRect(0, 0, 256, 256);
    const t = tex(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
  }

  function add(geo, mat, parent, x = 0, y = 0, z = 0, shadow = true) {
    const m = new THREE.Mesh(track(geo), mat); m.position.set(x, y, z);
    if (shadow) { m.castShadow = true; m.receiveShadow = true; }
    parent.add(m); return m;
  }

  /* ---------- человечек (низкополигональный) ---------- */
  function person(parent, shirtCol, i, sitting) {
    const g = new THREE.Group(); parent.add(g);
    const skin = lm(SKIN[i % SKIN.length]), hair = lm(HAIR[(i * 7) % HAIR.length], { roughness: .9 });
    const shirt = lm(shirtCol, { roughness: .7 }), pants = lm(0x272c3e);
    track(skin); track(hair); track(shirt); track(pants);
    const hip = sitting ? .55 : .95;
    if (sitting) {
      for (const sx of [-.12, .12]) { add(new THREE.BoxGeometry(.17, .15, .5), pants, g, sx, hip, -.22); add(new THREE.BoxGeometry(.15, .5, .15), pants, g, sx, .3, -.45); }
    } else {
      for (const sx of [-.12, .12]) add(new THREE.BoxGeometry(.16, .9, .17), pants, g, sx, .45, 0);
    }
    add(new THREE.CylinderGeometry(.24, .29, .62, 8), shirt, g, 0, hip + .36, 0);
    const arms = [];
    for (const sx of [-.31, .31]) {
      const piv = new THREE.Group(); piv.position.set(sx, hip + .6, 0); g.add(piv);
      const a = add(new THREE.BoxGeometry(.12, .58, .12), shirt, piv, 0, -.27, 0);
      add(new THREE.SphereGeometry(.07, 6, 5), skin, a, 0, -.31, 0, false);
      piv.rotation.x = sitting ? 1.15 : .05; piv.rotation.z = sx > 0 ? -.08 : .08;
      arms.push(piv);
    }
    const head = new THREE.Group(); head.position.y = hip + .87; g.add(head);
    add(new THREE.SphereGeometry(.2, 14, 10), skin, head, 0, 0, 0);
    add(new THREE.SphereGeometry(.212, 14, 8, 0, 2 * Math.PI, 0, Math.PI * .55), hair, head, 0, .03, .02);
    st.figs.push({ g, arms, head, sitting, ph: i * 1.7 });
    return g;
  }

  /* ---------- стол с монитором ---------- */
  const deskMat = lm(0x3b4258, { roughness: .6 }), legMat = lm(0x232838, { metalness: .5, roughness: .4 });
  const frameMat = lm(0x111522, { metalness: .4, roughness: .4 }), chairMat = lm(0x2a3150);
  function desk(s, x, z, color, i) {
    const g = new THREE.Group(); g.position.set(x, 0, z); IS.add(g);
    add(new THREE.BoxGeometry(2.6, .08, 1.3), deskMat, g, 0, .78, 0);
    for (const [lx, lz] of [[-1.2, -.55], [1.2, -.55], [-1.2, .55], [1.2, .55]]) add(new THREE.BoxGeometry(.07, .78, .07), legMat, g, lx, .39, lz);
    // монитор
    const mon = new THREE.Group(); mon.position.set(.15, 0, -.32); g.add(mon);
    add(new THREE.BoxGeometry(.08, .3, .08), legMat, mon, 0, .97, -.02);
    add(new THREE.BoxGeometry(.5, .03, .3), legMat, mon, 0, .83, 0);
    add(new THREE.BoxGeometry(2.04, 1.3, .07), frameMat, mon, 0, 1.75, 0);
    const scr = add(new THREE.PlaneGeometry(1.92, 1.2), track(new THREE.MeshBasicMaterial({ map: screenTexture(s, color), toneMapped: false })), mon, 0, 1.75, .04, false);
    // мягкий отсвет экрана на стол (без отдельного источника света: 30+ ламп не влезут в шейдер)
    const halo = add(new THREE.PlaneGeometry(1.6, .7), track(new THREE.MeshBasicMaterial({ color: new THREE.Color(color), transparent: true, opacity: .1, depthWrite: false })), g, .15, .825, -.05, false);
    halo.rotation.x = -Math.PI / 2;
    // клавиатура и кружка
    add(new THREE.BoxGeometry(.9, .03, .3), frameMat, g, -.35, .835, .25);
    add(new THREE.CylinderGeometry(.06, .06, .14, 10), lm(0xd8dcea), g, .95, .89, .3);
    // кресло и сотрудник
    // кресло сбоку и вполоборота к монитору — голова не заслоняет экран при приближении
    const ch = new THREE.Group(); ch.position.set(-1.0, 0, .95); ch.rotation.y = -.42; g.add(ch);
    add(new THREE.BoxGeometry(.6, .08, .55), chairMat, ch, 0, .47, 0);
    add(new THREE.BoxGeometry(.6, .7, .07), chairMat, ch, 0, .85, .3);
    add(new THREE.CylinderGeometry(.04, .04, .45, 6), legMat, ch, 0, .23, 0);
    const shirt = new THREE.Color(color).lerp(new THREE.Color(0x2a3150), .35 + (i % 3) * .12);
    const p = person(ch, shirt, i, true); p.position.set(0, 0, -.02); p.rotation.y = 0;
    for (let k = 0; k < (s.crew || 0); k++) {   // команда у стола (проекты, экипажи)
      const q = person(g, new THREE.Color(color).lerp(new THREE.Color(0xffffff), .15 + k * .2), i + 11 + k, false);
      q.position.set(1.55 + k * .25, 0, .45 + k * .7); q.rotation.y = .9 + k * .25;
    }
    // индикатор «работает сейчас»: зелёный огонёк на рамке монитора (мигает в tick) и ореол
    const led = new THREE.Group(); led.position.set(.82, 2.4, .02); mon.add(led);
    add(new THREE.SphereGeometry(.13, 14, 10), ledMat, led, 0, .3, 0, false);
    add(new THREE.SphereGeometry(.3, 14, 10), ledGlow, led, 0, .3, 0, false);
    add(new THREE.CylinderGeometry(.025, .025, .3, 6), legMat, led, 0, .15, 0, false);
    led.visible = !!s.live;
    g.traverse(o => { if (o.isMesh) { o.userData.k = 'st:' + s.key; o.userData.root = g; st.pick.push(o); } });
    INFO['st:' + s.key] = [s.name, s.role, s.conf, s.text];
    st.desks.push({ key: s.key, g, scr, s, led, sig: deskSig(s) });
  }
  const ledMat = new THREE.MeshBasicMaterial({ color: LIVE, toneMapped: false });
  const ledGlow = new THREE.MeshBasicMaterial({ color: LIVE, transparent: true, opacity: .28, depthWrite: false, toneMapped: false });
  const deskSig = s => JSON.stringify([s.name, s.role, s.conf, s.screen]);

  /* ---------- сборка кабинета ---------- */
  function clear() {
    while (IS.children.length) IS.remove(IS.children[0]);
    for (const d of disposables) d.dispose && d.dispose();
    disposables = []; st.pick.length = 0; st.desks = []; st.figs = [];
  }
  function build(id) {
    clear();
    const room = ROOMS[id]; st.room = room;
    const n = Math.max(1, room.staff.length), cols = Math.max(2, Math.ceil(Math.sqrt(n * 1.3))), rows = Math.ceil(n / cols);
    const SX = 4.4, SZ = 4.7, W = cols * SX + 6, Dp = rows * SZ + 7, H = 5.5;
    // свет
    IS.add(new THREE.HemisphereLight(0xc8d6ff, 0x1a1f30, .55));
    const sun = new THREE.DirectionalLight(0xfff4e0, .7); sun.position.set(-W * .3, 22, Dp * .4); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -W / 2 - 2, right: W / 2 + 2, top: Dp / 2 + 2, bottom: -Dp / 2 - 2, near: 1, far: 70 });
    sun.shadow.bias = -.0008; sun.shadow.camera.updateProjectionMatrix(); IS.add(sun);
    const back = new THREE.PointLight(new THREE.Color(room.color), .8, W * 1.2, 1.5); back.position.set(0, H - .5, -Dp / 2 + 2); IS.add(back);
    // пол, стены, вывеска, окна
    const ft = floorTexture(room.color); ft.repeat.set(W / 3, Dp / 3);
    const floor = add(new THREE.PlaneGeometry(W, Dp), track(lm(0xffffff, { map: ft, roughness: .95 })), IS, 0, 0, 0, false);
    floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true;
    const wallM = track(lm(0x1c2236, { roughness: .9 }));
    add(new THREE.BoxGeometry(W, H, .3), wallM, IS, 0, H / 2, -Dp / 2);
    for (const sx of [-1, 1]) add(new THREE.BoxGeometry(.3, H, Dp), wallM, IS, sx * W / 2, H / 2, 0);
    const trim = track(new THREE.MeshBasicMaterial({ color: new THREE.Color(room.color), toneMapped: false }));
    add(new THREE.BoxGeometry(W, .08, .08), trim, IS, 0, .1, -Dp / 2 + .2, false);
    for (const sx of [-1, 1]) add(new THREE.BoxGeometry(.08, .08, Dp), trim, IS, sx * (W / 2 - .2), .1, 0, false);
    const sw = Math.min(W - 4, 22), sh = sw * 300 / 2048;
    st.sign = add(new THREE.PlaneGeometry(sw, sh), track(new THREE.MeshBasicMaterial({ map: signTexture(room), toneMapped: false })), IS, 0, H - sh / 2 - .3, -Dp / 2 + .17, false);
    st.signSub = room.sub;
    const winM = track(new THREE.MeshBasicMaterial({ color: 0x1d3b6e, toneMapped: false }));
    for (const sx of [-1, 1]) for (let z = -Dp / 2 + 3; z < Dp / 2 - 2; z += 4) {
      const w = add(new THREE.PlaneGeometry(2.6, 2), winM, IS, sx * (W / 2 - .17), 2.8, z, false); w.rotation.y = -sx * Math.PI / 2;
    }
    // растения по углам — декор
    for (const [px, pz] of [[-W / 2 + 1.2, -Dp / 2 + 1.2], [W / 2 - 1.2, -Dp / 2 + 1.2], [-W / 2 + 1.2, Dp / 2 - 1.5], [W / 2 - 1.2, Dp / 2 - 1.5]]) {
      add(new THREE.CylinderGeometry(.35, .28, .6, 10), track(lm(0x6a4a3a)), IS, px, .3, pz);
      add(new THREE.IcosahedronGeometry(.7, 0), track(lm(0x2f7a3a, { flatShading: true })), IS, px, 1.15, pz);
    }
    // столы
    room.staff.forEach((s, i) => {
      const c = i % cols, r = (i / cols) | 0;
      desk(s, (c - (cols - 1) / 2) * SX, (r - (rows - 1) / 2) * SZ - .6, room.color, i);
    });
    INFO['room:' + id] = [room.title, room.sub, room.conf, room.intro];
    st.overview = { t: V(0, .8, -.5), c: V(0, Math.max(10, W * .54), Dp / 2 + Math.max(8, W * .42)) };
    st.maxD = Math.max(40, W * 1.8);
    // список сотрудников в панели
    $('room-h').textContent = 'Сотрудники · ' + room.staff.length;
    const list = $('room-list'); list.innerHTML = '';
    const ov = document.createElement('button'); ov.innerHTML = '<span class="dot" style="background:#dfe6ff"></span><span class="nm">⌂ Обзор зала</span>';
    ov.onclick = overview; list.appendChild(ov);
    room.staff.forEach(s => {
      const b = document.createElement('button'); b.dataset.key = s.key; b.title = s.name;
      b.innerHTML = `<span class="dot"></span><span class="nm"></span>`;
      paintButton(b, s);
      b.onclick = () => focus(s.key); list.appendChild(b);
    });
  }
  function paintButton(b, s) {
    const dot = b.querySelector('.dot');
    dot.style.background = s.live ? LIVE : s.screen.ok ? '#5be39a' : '#ffc95a';
    dot.classList.toggle('live', !!s.live);
    b.querySelector('.nm').textContent = s.name;
    b.title = s.name + (s.live ? ' — работает сейчас' : '');
    let tg = b.querySelector('.now');
    if (s.live && !tg) { tg = document.createElement('span'); tg.className = 'now'; tg.textContent = 'сейчас'; b.appendChild(tg); }
    if (!s.live && tg) tg.remove();
  }

  /* ---------- живое обновление: новые данные без выхода из зала ---------- */
  function refresh() {
    if (!st.active || !st.room) return;
    const room = ROOMS[st.room.id];
    if (!room) { exit(); return; }
    st.room = room;
    INFO['room:' + room.id] = [room.title, room.sub, room.conf, room.intro];
    const same = room.staff.length === st.desks.length && room.staff.every((s, i) => st.desks[i].key === s.key);
    if (!same) {   // состав зала изменился — строим заново, но камера смотрит на тот же стол
      const cam = camera.position.clone(), tgt = controls.target.clone(), fk = st.focus;
      const od = fk && st.desks.find(d => d.key === fk), op = od ? od.g.position.clone() : null;
      build(room.id); IS.add(hl); hl.visible = false; hoverK = null; fly = null;
      controls.maxDistance = st.maxD;
      const nd = fk && st.desks.find(d => d.key === fk);
      if (nd && op) { const dv = nd.g.position.clone().sub(op); cam.add(dv); tgt.add(dv); st.focus = fk; markList(fk); }
      else st.focus = null;
      camera.position.copy(cam); controls.target.copy(tgt); controls.update();
      return 'rebuilt';
    }
    let n = 0;
    room.staff.forEach((s, i) => {
      const d = st.desks[i];
      INFO['st:' + s.key] = [s.name, s.role, s.conf, s.text];
      const sg = deskSig(s);
      if (sg !== d.sig) {   // перерисовать только изменившиеся экраны
        const old = d.scr.material.map;
        d.scr.material.map = screenTexture(s, room.color); d.scr.material.needsUpdate = true;
        untrack(old); d.sig = sg; n++;
      }
      d.s = s; d.led.visible = !!s.live;
    });
    if (st.signSub !== room.sub) {
      const old = st.sign.material.map; st.sign.material.map = signTexture(room); st.sign.material.needsUpdate = true;
      untrack(old); st.signSub = room.sub;
    }
    $('room-h').textContent = 'Сотрудники · ' + room.staff.length;
    for (const b of $('room-list').children) { const s = b.dataset.key && room.staff.find(x => x.key === b.dataset.key); if (s) paintButton(b, s); }
    return n;
  }

  /* ---------- камера ---------- */
  function overview() {
    flyTo(st.overview.t.clone(), st.overview.c.clone(), 1.1);
    st.focus = null; markList(null);
    pinned = 'room:' + st.room.id; show(pinned);
  }
  function focus(key) {
    const d = st.desks.find(x => x.key === key); if (!d) return;
    const sp = d.scr.getWorldPosition(V()), q = d.scr.getWorldQuaternion(new THREE.Quaternion());
    const nrm = V(0, 0, 1).applyQuaternion(q);
    flyTo(sp.clone().add(V(0, -.04, 0)), sp.clone().add(nrm.multiplyScalar(2.2)).add(V(0, .22, 0)), 1.1);
    st.focus = key; markList(key);
    pinned = 'st:' + key; show(pinned);
  }
  function markList(key) {
    for (const b of $('room-list').children) b.classList.toggle('on', !!key && b.dataset.key === key);
    const on = [...$('room-list').children].find(b => b.dataset.key === key);
    if (on) on.scrollIntoView({ block: 'nearest' });
  }

  /* ---------- вход и выход ---------- */
  function enter(id, focusKey) {
    if (!ROOMS[id]) return;
    if (!st.active) st.saved = { c: camera.position.clone(), t: controls.target.clone(), near: camera.near, minD: controls.minDistance,
      maxD: controls.maxDistance, pol: controls.maxPolarAngle, bs: bloom.strength, bt: bloom.threshold, rot: controls.autoRotate, pinned };
    build(id);
    st.active = true; fly = null;
    composer.passes[0].scene = IS; IS.add(hl); hl.visible = false; hoverK = null; $('tip').style.display = 'none';
    camera.near = .05; camera.updateProjectionMatrix();
    controls.minDistance = .8; controls.maxDistance = st.maxD; controls.maxPolarAngle = 1.53; controls.autoRotate = false;
    bloom.enabled = false;   // свечение размывает текст на мониторах
    camera.position.copy(st.overview.c); controls.target.copy(st.overview.t); controls.update();
    $('b-exit').style.display = ''; $('nav-sec').style.display = 'none'; $('room-sec').style.display = '';
    $('b-trace').style.display = 'none'; $('b-rot').style.display = 'none'; $('b-home').style.display = 'none';
    $('hint').textContent = 'Клик по монитору или сотруднику — приблизить экран · Esc или «Выйти в город» — назад';
    pinned = 'room:' + id; show(pinned);
    if (focusKey) setTimeout(() => focus(focusKey), 350);
  }
  function exit() {
    if (!st.active) return;
    st.active = false; fly = null;
    composer.passes[0].scene = scene; scene.add(hl); hl.visible = false; hoverK = null; $('tip').style.display = 'none';
    const s = st.saved;
    camera.near = s.near; camera.updateProjectionMatrix();
    controls.minDistance = s.minD; controls.maxDistance = s.maxD; controls.maxPolarAngle = s.pol; controls.autoRotate = s.rot;
    bloom.enabled = true; bloom.strength = s.bs; bloom.threshold = s.bt;
    camera.position.copy(s.c); controls.target.copy(s.t); controls.update();
    $('b-exit').style.display = 'none'; $('nav-sec').style.display = ''; $('room-sec').style.display = 'none';
    $('b-trace').style.display = ''; $('b-rot').style.display = ''; $('b-home').style.display = '';
    $('hint').textContent = 'Левая кнопка — вращать · правая — сдвигать · колесо — приближать · клик — описание · второй клик — войти';
    pinned = s.pinned; if (pinned) show(pinned); else showIntro();
    clear();
  }

  /* ---------- кнопка «Войти» в панели ---------- */
  const baseShow = show, baseIntro = showIntro;
  function updateEnter(k) {
    const r = !st.active && k && K2R[k];
    st.enterKey = r ? k : null;
    $('b-enter').style.display = r ? '' : 'none';
    if (r) $('b-enter').textContent = '🚪 Войти: ' + ROOMS[r[0]].title;
  }
  show = function (k) { baseShow(k); updateEnter(k); };
  showIntro = function () {
    if (st.active) { baseShow('room:' + st.room.id); return; }
    baseIntro(); updateEnter(null);
  };
  $('b-enter').onclick = () => { const k = st.enterKey; if (k && K2R[k]) enter(K2R[k][0], K2R[k][1]); };
  $('b-exit').onclick = exit;
  addEventListener('keydown', e => { if (e.key === 'Escape' && st.active) exit(); });
  $('hint').textContent += ' · второй клик — войти';

  function onClick(k, prev) {
    if (st.active) {
      if (k && k.startsWith('st:')) { focus(k.slice(3)); return true; }
      if (!k) { pinned = 'room:' + st.room.id; show(pinned); return true; }
      return false;
    }
    if (k && K2R[k] && k === prev) { enter(K2R[k][0], K2R[k][1]); return true; }
    return false;
  }
  function onDouble(k) { if (!st.active && k && K2R[k]) enter(K2R[k][0], K2R[k][1]); }

  /* ---------- оживление ---------- */
  function tick(dt, T) {
    if (!st.active) return;
    // вблизи рамка подсветки рисуется поверх экрана — прячем её, пока смотрим на монитор
    if (hl.visible && camera.position.distanceTo(controls.target) < 6) hl.visible = false;
    const on = Math.sin(T * Math.PI * 2.4) > -.3;   // мигание огонька «работает сейчас»
    for (const d of st.desks) if (d.s.live) { d.led.children[0].visible = on; d.led.children[1].material.opacity = on ? .3 : .08; }
    for (const f of st.figs) {
      if (f.sitting) {
        f.arms[0].rotation.x = 1.15 + Math.sin(T * 11 + f.ph) * .09;
        f.arms[1].rotation.x = 1.15 + Math.sin(T * 11 + f.ph + 1.6) * .09;
        f.head.rotation.y = Math.sin(T * .45 + f.ph) * .22;
        f.head.rotation.x = .12 + Math.sin(T * .7 + f.ph) * .05;
      } else {
        f.head.rotation.y = Math.sin(T * .6 + f.ph) * .35;
        f.arms[0].rotation.x = .05 + Math.sin(T * 1.2 + f.ph) * .25;
      }
    }
  }

  window.INTERIOR = { get active() { return st.active; }, get room() { return st.room && st.room.id; }, get focusKey() { return st.focus; },
    get desks() { return st.desks; }, pick: st.pick, onClick, onDouble, tick, enter, exit, focus, overview, refresh, rooms: ROOMS };
})();
