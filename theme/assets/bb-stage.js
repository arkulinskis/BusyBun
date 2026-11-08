/* bb-stage.js: the drawn parts of the game screens that stay JavaScript (Python wraps them in client_code/bun.py and
   the Components): the play stage (canvas + heads-up display + touch stick + neighbour speech), the floating-food
   title background, the journey road (nodes on a curvy SVG path) and the click sound for buttons.

   BB.mountStage(el, opts, onEvent) -> {start, pause, resume, isPaused, destroy, game}
       opts: {level, theme, items, perks, hat} (plain objects); onEvent(name, jsonText) gets pause / toast / win / lose.
   BB.titleBg(canvas) -> stop()      BB.layoutRoad(roadEl)  (nodes = .g-node inside, positioned like the old map) */
(function () {
  'use strict';
  var BB = window.BB;
  var esc = function (s) { return BB.esc(s); };
  function em(e) { return '<span class="bb-emoji">' + e + '</span>'; }

  BB.mountStage = function (el, opts, onEvent) {
    var Art = BB.Art, touch = BB.isTouch(), talkTimer = 0, alive = true;
    function send(name, d) { if (alive && onEvent) onEvent(name, JSON.stringify(d || {})); }
    el.innerHTML = '<canvas class="g-cv" aria-label="The level"></canvas><div class="g-hud">' +
      '<div class="tl"><div class="g-hearts"></div><div class="g-goalbar"></div><div class="g-buffs"></div></div>' +
      '<div class="g-timer"></div>' +
      '<div class="tr"><canvas class="g-mm" aria-hidden="true"></canvas><button type="button" class="g-iconbtn" data-a="pause" aria-label="Pause (Esc)" title="Pause (Esc)">⏸</button></div>' +
      (touch ? '<div class="g-stick"><div class="base"></div><div class="knob"></div><div class="hint">◀ drag to move ▶</div></div>' : '') +
      '<div class="g-dash ' + (touch ? '' : 'kb') + '"><svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="47" fill="none" stroke="#3d8fd1" stroke-width="6" stroke-dasharray="295" stroke-dashoffset="0"/></svg>' + em('💨') + (touch ? 'DASH' : 'SPACE') + '</div>' +
      '</div>';
    var cv = el.querySelector('.g-cv'), hud = {
      hearts: el.querySelector('.g-hearts'), goals: el.querySelector('.g-goalbar'), buffs: el.querySelector('.g-buffs'), timer: el.querySelector('.g-timer'),
      dash: el.querySelector('.g-dash'), ring: el.querySelector('.g-dash circle')
    };
    var game = BB.Game(cv, {
      level: opts.level, theme: opts.theme, items: opts.items, perks: opts.perks, hat: opts.hat, minimap: el.querySelector('.g-mm'),
      onHud: function (h) { drawHud(h); },
      onEvent: function (name, d) {
        if (name === 'heal') { hud.hearts.classList.remove('heal'); void hud.hearts.offsetWidth; hud.hearts.classList.add('heal'); }
        else if (name === 'talk') showTalk(d);
        else if (name === 'toast') BB.toast(esc(d.text));
        else if (name === 'win') send('win', { result: d.result, found: d.found, totalItems: d.totalItems });
        else if (name === 'pause' || name === 'lose') send(name, d);
      }
    });
    if (touch) {
      var area = el.querySelector('.g-stick'), base = area.querySelector('.base'), knob = area.querySelector('.knob'), hint = area.querySelector('.hint'), id = null, ox = 0, oy = 0;
      area.addEventListener('touchstart', function (e) {
        var tch = e.changedTouches[0]; id = tch.identifier; var r = area.getBoundingClientRect();
        ox = tch.clientX - r.left; oy = tch.clientY - r.top;
        base.style.display = knob.style.display = 'block'; hint.style.display = 'none';
        base.style.left = knob.style.left = ox + 'px'; base.style.top = knob.style.top = oy + 'px'; e.preventDefault();
      }, { passive: false });
      area.addEventListener('touchmove', function (e) {
        for (var i = 0; i < e.changedTouches.length; i++) {
          var tch = e.changedTouches[i]; if (tch.identifier !== id) continue;
          var r = area.getBoundingClientRect(), dx = tch.clientX - r.left - ox, dy = tch.clientY - r.top - oy, d = Math.sqrt(dx * dx + dy * dy), max = 52;
          if (d > max) { dx = dx / d * max; dy = dy / d * max; }
          knob.style.left = (ox + dx) + 'px'; knob.style.top = (oy + dy) + 'px';
          game.setStick(dx / max, dy / max);
        }
        e.preventDefault();
      }, { passive: false });
      var end = function (e) {
        for (var i = 0; i < e.changedTouches.length; i++) if (e.changedTouches[i].identifier === id) {
          id = null; base.style.display = knob.style.display = 'none'; game.setStick(0, 0);
        }
      };
      area.addEventListener('touchend', end); area.addEventListener('touchcancel', end);
      hud.dash.addEventListener('touchstart', function (e) { e.preventDefault(); game.dash(); }, { passive: false });
    } else {
      hud.dash.addEventListener('mousedown', function () { game.dash(); });
    }
    el.querySelector('[data-a="pause"]').addEventListener('click', function () { send('pause'); });
    function onVis() { if (document.hidden && !game.isPaused()) send('pause'); }
    document.addEventListener('visibilitychange', onVis);

    function drawHud(h) {
      var hs = '';
      for (var i = 0; i < h.maxHearts; i++) hs += '<span class="' + (i < h.hearts ? '' : 'off') + '">♥</span>';
      if (h.shield) hs += '<span class="sh">◆</span>';
      hud.hearts.innerHTML = hs;
      var g = h.goals, chips = [];
      if (g.meatGoal) chips.push([g.meat >= g.meatGoal, '🥩', Math.min(g.meat, g.meatGoal) + '/' + g.meatGoal]);
      if (g.errandsGoal && g.errandsTotal) chips.push([g.errandsDone >= g.errandsTotal, '🤝', g.errandsDone + '/' + g.errandsTotal]);
      if (g.nestsGoal && g.nestsTotal) chips.push([!g.nestsLeft, '💥', (g.nestsTotal - g.nestsLeft) + '/' + g.nestsTotal]);
      if (g.kingsTotal) chips.push([!g.kingsLeft, '👑', g.kingsLeft ? (g.kingsLeft > 1 ? g.kingsLeft + ' bosses' : 'Beat the boss!') : 'Done']);
      chips.push([h.found >= h.totalItems, '🧺', h.found + '/' + h.totalItems]);
      if (g.ok) chips.push([true, '♨️', 'Steamer open!']);
      hud.goals.innerHTML = chips.map(function (c) { return '<span class="g-gchip ' + (c[0] ? 'ok' : '') + '">' + em(c[1]) + c[2] + '</span>'; }).join('') +
        (h.coins ? '<span class="g-gchip">' + em('🪙') + h.coins + '</span>' : '') + (h.chopsticks ? '<span class="g-gchip ok">' + em('🥢') + '</span>' : '') + (h.postcard ? '<span class="g-gchip ok">' + em('✉️') + '</span>' : '');
      var b = h.buffs || {}, bs = [];
      if (b.magnet) bs.push(['', '🧲', b.magnet + 's']);
      if (b.anise) bs.push(['', '🌟', b.anise + 's']);
      if (b.clock) bs.push(['', '⏳', 'Clock stopped ' + b.clock + 's']);
      if (b.tea) bs.push(['', '🍵', b.tea + 's']);
      if (b.stoves === 'on') bs.push(['hot', '🔥', 'Stoves hot']);
      else if (b.stoves === 'off') bs.push(['cool', '🎛️', 'Stoves off']);
      else if (b.stoves) bs.push(['cool', '⏲️', 'Stoves off ' + b.stoves + 's']);
      hud.buffs.innerHTML = bs.map(function (c) { return '<span class="g-gchip ' + c[0] + '">' + em(c[1]) + c[2] + '</span>'; }).join('');
      hud.timer.className = 'g-timer' + (h.time > h.par ? ' over' : '') + (b.clock ? ' frozen' : '');
      hud.timer.innerHTML = '⏱ ' + BB.fmtTime(h.time) + ' <small>/ par ' + BB.fmtTime(h.par) + '</small>';
      hud.ring.setAttribute('stroke-dashoffset', String(295 * (1 - h.dash)));
      hud.dash.classList.toggle('ready', h.dash >= 1);
    }
    function showTalk(d) {
      var old = el.querySelector('.g-talk'); if (old) old.remove();
      var box = document.createElement('div'); box.className = 'g-talk' + (touch ? ' touch' : '');
      box.setAttribute('role', 'status');
      var c = Art.canvas(58, 58); Art.drawNPC(c.ctx, d.npc.style, 29, 28, 20, { happy: d.done });
      box.appendChild(c.el);
      var tx = document.createElement('div');
      tx.innerHTML = '<b>' + esc(d.npc.name) + '</b><p>' + esc(d.text) + '</p>' +
        (d.done ? (d.gift ? '<span class="need">Gift: ' + em(d.gift.item.emoji) + ' ' + esc(d.gift.item.name) + ' ×' + d.gift.count + '</span>' : '')
          : '<span class="need">' + em(d.item.emoji) + ' ' + esc(d.item.name) + ' ' + Math.min(d.have, d.need) + '/' + d.need + '</span>');
      box.appendChild(tx);
      el.querySelector('.g-hud').appendChild(box);
      clearTimeout(talkTimer);
      talkTimer = setTimeout(function () { box.remove(); }, d.justDone ? 4200 : 3600);
    }
    return {
      start: function () { game.start(); },
      pause: function () { game.pause(); },
      resume: function () { game.resume(); },
      isPaused: function () { return game.isPaused(); },
      game: function () { return game; },
      destroy: function () {
        alive = false; clearTimeout(talkTimer);
        document.removeEventListener('visibilitychange', onVis);
        game.destroy(); el.innerHTML = '';
      }
    };
  };

  // The title screen's slowly falling ingredients.
  BB.titleBg = function (cv) {
    var Art = BB.Art, ctx = cv.getContext('2d'), fl = [], t0 = performance.now(), raf = 0;
    var em2 = ['🥓', '🍗', '🌿', '🥚', '🦐', '🍄', '🌶️', '🍯', '🥬', '🧄', '🦀', '🍖', '🌽'];
    var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    for (var i = 0; i < 26; i++) fl.push({ x: Math.random(), y: Math.random(), s: 18 + Math.random() * 26, v: 0.02 + Math.random() * 0.04, e: em2[i % em2.length], r: Math.random() * 6, vr: (Math.random() - 0.5) * 0.6 });
    function frame(now) {
      if (!still) raf = requestAnimationFrame(frame);
      var dpr = Math.min(2, window.devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
      if (!w || !h) return;
      if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
      var t = (now - t0) / 1000;
      fl.forEach(function (f) {
        if (!still) { f.y += f.v / 60; if (f.y > 1.1) { f.y = -0.1; f.x = Math.random(); } }
        ctx.save(); ctx.globalAlpha = 0.55; ctx.translate(f.x * w, f.y * h); ctx.rotate(f.r + t * f.vr);
        Art.drawEmoji(ctx, f.e, 0, 0, f.s); ctx.restore();
      });
    }
    raf = requestAnimationFrame(frame);
    return function () { cancelAnimationFrame(raf); raf = 0; still = true; };
  };

  // A world's road: 3 (phone) or 5 nodes a row, snaking left-right, joined by a dashed curvy path.
  BB.layoutRoad = function (r) {
    var nodes = r.querySelectorAll('.g-node'), n = nodes.length, w = r.clientWidth || 600, per = w < 520 ? 3 : 5, rows = Math.ceil(n / per), rowH = 136;
    if (!n) return;
    r.style.height = (rows * rowH + 40) + 'px';
    var pts = [];
    nodes.forEach(function (nd, i) {
      var row = Math.floor(i / per), j = i % per, cnt = Math.min(per, n - row * per);
      var span = cnt > 1 ? (cnt - 1) : 1, xs = cnt > 1 ? 12 + j * (76 / span) : 50;
      if (row % 2) xs = 100 - xs;
      var y = row * rowH + 70 + (j % 2 ? 24 : 0);
      nd.style.left = xs + '%'; nd.style.top = y + 'px';
      pts.push([xs / 100 * w, y]);
    });
    var svg = r.querySelector('svg');
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + (rows * rowH + 40));
    var d = pts.map(function (p, i) {
      if (!i) return 'M' + p[0] + ' ' + p[1];
      var q = pts[i - 1], mx = (q[0] + p[0]) / 2;
      return 'C' + mx + ' ' + q[1] + ' ' + mx + ' ' + p[1] + ' ' + p[0] + ' ' + p[1];
    }).join(' ');
    svg.innerHTML = '<path d="' + d + '" fill="none" stroke="#3d2416" stroke-width="12" stroke-linecap="round"/>' +
      '<path d="' + d + '" fill="none" stroke="#fff7ea" stroke-width="6" stroke-linecap="round" stroke-dasharray="2 12"/>';
  };

  // Minutes until the next daily box (local midnight).
  BB.minutesToMidnight = function () {
    var now = new Date(), mid = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    return Math.round((mid - now) / 60000);
  };

  // Buttons and links answer with the little "click" (the old game played it on every press).
  document.addEventListener('click', function (e) {
    var t = e.target && e.target.closest && e.target.closest('.bb button, .bb a, .bb-dlg button, .bb-dlg a');
    if (t && !t.disabled && BB.Sound) BB.Sound.play('click');
  }, true);
})();
