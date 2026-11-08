/* Busy Bun — the game engine. Runs one level on a canvas. Used by the game (GamePage) and by the
   level editor's playtest (AdminPage).

   var g = BB.Game(canvas, {level, theme, items, perks, hat, minimap, onHud, onEvent});
   g.start(); g.pause(); g.resume(); g.setStick(x, y); g.dash(); g.destroy();
   onEvent(name, data): 'talk' {npc, text, done, have, need}, 'toast' {text}, 'win' {result}, 'lose' {}, 'found' {kind}
   World units are tiles; drawing converts with S (pixels per tile). */
(function () {
  'use strict';
  var BB = window.BB = window.BB || {};
  var Art = BB.Art;
  var TAU = Math.PI * 2;

  var PEST = {
    ant: { hp: 1, r: 0.3, speed: 1.15 },
    rat: { hp: 1, r: 0.32, speed: 2.9 },
    fly: { hp: 1, r: 0.26, speed: 1.75 },
    roach: { hp: 2, r: 0.32, speed: 3.3 },
    gull: { hp: 2, r: 0.36, speed: 1.3 },
    king: { hp: 8, r: 0.62, speed: 1.55 },
    snail: { hp: 2, r: 0.32, speed: 0.75 },
    mould: { hp: 1, r: 0.34, speed: 1.9 },
    frog: { hp: 1, r: 0.3, speed: 1 },
    weevil: { hp: 3, r: 0.33, speed: 0.9 },
    spider: { hp: 2, r: 0.32, speed: 2.2 },
    wasp: { hp: 1, r: 0.26, speed: 2.4 },
    queen: { hp: 10, r: 0.6, speed: 2.2 }
  };
  var BOSS = { king: 'the Rat King', queen: 'the Wasp Queen' };
  var BONUS = { magnet: 1, bubble: 1, bag: 1, anise: 1, clock: 1 };
  var DIRS = { R: [1, 0], L: [-1, 0], U: [0, -1], D: [0, 1] };
  var MEATS = {};

  function dist(a, b) { var dx = a.x - b.x, dy = a.y - b.y; return Math.sqrt(dx * dx + dy * dy); }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function rnd(a, b) { return a + Math.random() * (b - a); }

  BB.Game = function (canvas, opts) {
    var ctx = canvas.getContext('2d');
    var L = JSON.parse(JSON.stringify(opts.level));
    var th = Art.theme(opts.theme);
    var ITEMS = opts.items || {};
    Object.keys(ITEMS).forEach(function (k) { if (ITEMS[k].cat === 'meat') MEATS[k] = 1; });
    var perks = {}; (opts.perks || []).forEach(function (p) { perks[p] = 1; });
    var W = L.w, H = L.h;
    var tiles = L.tiles.map(function (r) { return r.split(''); });
    var goals = L.goals || {};

    // ---------------------------------------------------------------- world state
    var S = 48, dpr = 1, viewW = 0, viewH = 0, cam = { x: 0, y: 0, shake: 0 };
    var running = false, paused = false, ended = false, raf = 0, last = 0, t = 0, time = 0, hudT = 0, flowT = 0, mapT = 0;
    var keys = {}, stick = { x: 0, y: 0 }, wantDash = false;
    var parts = [], lastHud = '';
    var startE = null, exitE = null;
    var player, items = [], pickups = [], pests = [], nests = [], npcs = [];
    var bag = {}, picked = {}, stats = { coins: 0, pests: 0, crates: 0, nests: 0, kings: 0, damage: 0, errands: [], chopsticks: false, postcard: false, knobs: 0, bonuses: 0 };
    var infest = new Float32Array(W * H), infestTarget = new Float32Array(W * H), slime = new Float32Array(W * H);
    // Oven knobs: every hot stove in the level goes off (for good, or for stoveT seconds with a kitchen timer).
    var stovesOff = false, stoveT = 0, hasStoves = L.tiles.some(function (r) { return r.indexOf('^') >= 0; });
    var hasKnob = (L.ents || []).some(function (e) { return e.t === 'pickup' && (e.k === 'knob' || e.k === 'timer'); });
    var BUFF = perks.snacker ? 2 : 1;
    var flow = new Int32Array(W * H);
    var hintCd = 0, combo = 0, comboT = 0, winT = -1, loseT = -1;

    (L.ents || []).forEach(function (e) {
      var c = { x: e.x + 0.5, y: e.y + 0.5 };
      if (e.t === 'start') startE = c;
      else if (e.t === 'exit') exitE = c;
      else if (e.t === 'item') items.push({ x: c.x, y: c.y, k: e.k, item: ITEMS[e.k] || { emoji: '❔', name: e.k }, taken: false });
      else if (e.t === 'pickup') pickups.push({ x: c.x, y: c.y, k: e.k, taken: false });
      else if (e.t === 'pest') addPest(e.k, c.x, c.y, null);
      else if (e.t === 'nest') nests.push({ x: c.x, y: c.y, k: e.k || 'ant', r: e.r || 4, hp: 3, maxHp: 3, spawnT: rnd(1.5, 3.5), alive: true, flash: 0, kids: 0 });
      else if (e.t === 'npc') npcs.push({ x: c.x, y: c.y, e: e, done: false, talkCd: 0, idx: npcs.length, pop: 0 });
    });
    startE = startE || { x: 1.5, y: 1.5 };
    exitE = exitE || { x: W - 1.5, y: H - 1.5 };
    var maxHearts = 3 + (perks.hearty ? 1 : 0);
    player = { x: startE.x, y: startE.y, vx: 0, vy: 0, r: 0.34, hearts: maxHearts, inv: 0, dashT: 0, dashCd: 0, dx: 0, dy: 1,
      shield: !!perks.shield, revive: !!perks.revive, tea: 0, hits: [], squash: 0, lookX: 0, lookY: 1, safe: 0, postDash: 0, fullHint: 0,
      magnet: 0, anise: 0, clock: 0 };
    var totalItems = items.length, meatTotal = items.filter(function (i) { return MEATS[i.k]; }).length;
    var kingsTotal = pests.filter(function (p) { return BOSS[p.k]; }).length;
    var bossNames = []; pests.forEach(function (p) { if (BOSS[p.k] && bossNames.indexOf(BOSS[p.k]) < 0) bossNames.push(BOSS[p.k]); });

    function addPest(k, x, y, nest) {
      var d = PEST[k] || PEST.ant;
      var p = { k: k, x: x, y: y, vx: 0, vy: 0, r: d.r, hp: d.hp, maxHp: d.hp, speed: d.speed, ang: Math.random() * TAU,
        wander: 0, state: 'idle', st: rnd(0.5, 2), stun: 0, flash: 0, nest: nest, homeX: x, homeY: y, alive: true, id: Math.random() };
      if (k === 'king') { p.summon = 4; p.charge = 3; }
      if (k === 'queen') { p.summon = 3; p.cd = 3; p.state = 'hover'; }
      if (k === 'gull' || k === 'wasp') { p.cd = rnd(1, 2.5); }
      if (k === 'spider') { p.state = 'hide'; }
      if (k === 'frog') { p.state = 'sit'; p.z = 0; }
      pests.push(p);
      return p;
    }
    function flying(p) { return p.k === 'fly' || p.k === 'wasp' || p.k === 'queen' || (p.k === 'gull' && (p.state === 'swoop' || p.state === 'idle')); }
    // A pest that can't hurt you right now (resting, dizzy).
    function harmless(p) { return (p.k === 'gull' && p.state === 'rest') || (p.k === 'weevil' && p.state === 'dizzy') || (p.k === 'spider' && p.state === 'rest') || (p.k === 'queen' && p.state === 'tired'); }
    // Is there a clear straight line (no solid tiles) between two points?
    function clearLine(a, b) {
      var n = Math.ceil(dist(a, b) * 3);
      for (var i = 1; i < n; i++) { var x = a.x + (b.x - a.x) * i / n, y = a.y + (b.y - a.y) * i / n; if (solidAt(Math.floor(x), Math.floor(y))) return false; }
      return true;
    }

    // ---------------------------------------------------------------- tiles
    function tileCh(tx, ty) { return (tx < 0 || ty < 0 || tx >= W || ty >= H) ? '#' : tiles[ty][tx]; }
    function solidAt(tx, ty) { return !!Art.SOLID[tileCh(tx, ty)]; }
    function computeInfest(target) {
      target.fill(0);
      nests.forEach(function (n) {
        if (!n.alive) return;
        var R = n.r;
        for (var y = Math.floor(n.y - R); y <= n.y + R; y++) for (var x = Math.floor(n.x - R); x <= n.x + R; x++) {
          if (x < 0 || y < 0 || x >= W || y >= H) continue;
          var d = Math.sqrt((x + 0.5 - n.x) * (x + 0.5 - n.x) + (y + 0.5 - n.y) * (y + 0.5 - n.y));
          if (d <= R) target[y * W + x] = Math.max(target[y * W + x], clamp(1.25 - d / R, 0, 1));
        }
      });
    }
    computeInfest(infestTarget); infest.set(infestTarget);

    // Circle vs solid tiles; `pass` lets flying things ignore walls.
    function collide(o, r) {
      var minX = Math.floor(o.x - r), maxX = Math.floor(o.x + r), minY = Math.floor(o.y - r), maxY = Math.floor(o.y + r), hit = null;
      for (var ty = minY; ty <= maxY; ty++) for (var tx = minX; tx <= maxX; tx++) {
        if (!solidAt(tx, ty)) continue;
        var cx = clamp(o.x, tx, tx + 1), cy = clamp(o.y, ty, ty + 1), dx = o.x - cx, dy = o.y - cy, d2 = dx * dx + dy * dy;
        if (d2 < r * r) {
          var d = Math.sqrt(d2) || 0.0001;
          if (d2 === 0) { dx = o.x - (tx + 0.5); dy = o.y - (ty + 0.5); d = Math.sqrt(dx * dx + dy * dy) || 1; }
          var push = r - Math.sqrt(d2);
          o.x += dx / d * push; o.y += dy / d * push;
          hit = hit || { tx: tx, ty: ty, nx: dx / d, ny: dy / d };
        }
      }
      return hit;
    }
    function moveBody(o, dx, dy, r, fly) {
      var steps = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) / (r * 0.5))), hit = null;
      for (var i = 0; i < steps; i++) {
        o.x += dx / steps; o.y += dy / steps;
        if (fly) { o.x = clamp(o.x, 0.4, W - 0.4); o.y = clamp(o.y, 0.4, H - 0.4); }
        else hit = collide(o, r) || hit;
      }
      return hit;
    }

    // Distance-to-player map for chasers (breadth first over walkable tiles).
    function computeFlow() {
      flow.fill(-1);
      var px = Math.floor(player.x), py = Math.floor(player.y);
      if (px < 0 || py < 0 || px >= W || py >= H) return;
      var q = new Int32Array(W * H), head = 0, tail = 0;
      flow[py * W + px] = 0; q[tail++] = py * W + px;
      while (head < tail) {
        var cur = q[head++], cx = cur % W, cy = (cur / W) | 0, d = flow[cur];
        if (d > 40) continue;
        for (var k = 0; k < 4; k++) {
          var nx = cx + (k === 0 ? 1 : k === 1 ? -1 : 0), ny = cy + (k === 2 ? 1 : k === 3 ? -1 : 0);
          if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
          var ni = ny * W + nx;
          if (flow[ni] >= 0 || solidAt(nx, ny)) continue;
          flow[ni] = d + 1; q[tail++] = ni;
        }
      }
    }
    function flowDir(o) {
      var tx = Math.floor(o.x), ty = Math.floor(o.y), here = flow[ty * W + tx];
      if (here < 0) return null;
      if (here === 0) return { x: player.x - o.x, y: player.y - o.y };
      var best = null, bd = here;
      [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (d) {
        var nx = tx + d[0], ny = ty + d[1];
        if (nx < 0 || ny < 0 || nx >= W || ny >= H) return;
        var v = flow[ny * W + nx];
        if (v >= 0 && v < bd) { bd = v; best = d; }
      });
      if (!best) return null;
      return { x: tx + best[0] + 0.5 - o.x, y: ty + best[1] + 0.5 - o.y };
    }

    // ---------------------------------------------------------------- effects
    function burst(x, y, n, color, spd, size) {
      for (var i = 0; i < n; i++) {
        var a = Math.random() * TAU, v = rnd(0.3, 1) * (spd || 3);
        parts.push({ kind: 'dot', x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 1, life: rnd(0.4, 0.8), max: 0.8, color: color, size: size || rnd(0.05, 0.11), g: 6 });
      }
    }
    function steam(x, y, n, size) {
      for (var i = 0; i < n; i++) parts.push({ kind: 'steam', x: x + rnd(-0.2, 0.2), y: y + rnd(-0.1, 0.1), vx: rnd(-0.4, 0.4), vy: rnd(-1.2, -0.4), life: rnd(0.4, 0.9), max: 0.9, size: size || rnd(0.12, 0.22) });
    }
    function sparkle(x, y, n, color) {
      for (var i = 0; i < n; i++) { var a = Math.random() * TAU, v = rnd(1, 3); parts.push({ kind: 'star', x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: rnd(0.5, 0.9), max: 0.9, color: color || '#fff6c2', size: rnd(0.08, 0.14) }); }
    }
    function floatText(x, y, text, color, big) { parts.push({ kind: 'text', x: x, y: y, vx: 0, vy: -1.3, life: 1.1, max: 1.1, text: text, color: color || '#fff', size: big ? 0.55 : 0.38 }); }
    function ring(x, y, color, maxR) { parts.push({ kind: 'ring', x: x, y: y, life: 0.5, max: 0.5, color: color || '#fff', size: maxR || 1.2 }); }
    function shake(a) { cam.shake = Math.max(cam.shake, a); }
    function emit(name, data) { if (opts.onEvent) opts.onEvent(name, data || {}); }
    function sfx(n) { if (BB.Sound) BB.Sound.play(n); }

    // ---------------------------------------------------------------- goals
    function meatCount() { var n = 0; for (var k in picked) if (MEATS[k]) n += picked[k]; return n; }
    function goalState() {
      var meat = meatCount(), errandsDone = npcs.filter(function (n) { return n.done; }).length;
      var nestsLeft = nests.filter(function (n) { return n.alive; }).length;
      var kingsLeft = pests.filter(function (p) { return BOSS[p.k] && p.alive; }).length;
      var ok = meat >= (goals.meat || 0) && (!goals.errands || errandsDone === npcs.length) && (!goals.nests || nestsLeft === 0) && kingsLeft === 0;
      return { meat: meat, meatGoal: goals.meat || 0, meatTotal: meatTotal, errandsDone: errandsDone, errandsTotal: npcs.length, errandsGoal: !!goals.errands,
        nestsLeft: nestsLeft, nestsTotal: nests.length, nestsGoal: !!goals.nests, kingsLeft: kingsLeft, kingsTotal: kingsTotal, ok: ok };
    }
    function missingText(g) {
      var need = [];
      if (g.meat < g.meatGoal) need.push((g.meatGoal - g.meat) + ' more meat');
      if (g.errandsGoal && g.errandsDone < g.errandsTotal) need.push((g.errandsTotal - g.errandsDone) + ' errand' + (g.errandsTotal - g.errandsDone > 1 ? 's' : ''));
      if (g.nestsGoal && g.nestsLeft) need.push(g.nestsLeft + ' nest' + (g.nestsLeft > 1 ? 's' : ''));
      if (g.kingsLeft) pests.forEach(function (p) { if (BOSS[p.k] && p.alive && need.indexOf(BOSS[p.k]) < 0) need.push(BOSS[p.k]); });
      return need.join(', ');
    }

    // ---------------------------------------------------------------- damage
    // Attacking vs touching: while dashing (and a moment after), touching a pest bonks it and can't hurt you.
    // Star Anise makes every touch a bonk.
    function attacking() { return player.dashT > 0 || player.postDash > 0 || player.anise > 0; }
    function hurtPlayer(fromX, fromY, why) {
      if (player.inv > 0 || winT >= 0 || loseT >= 0 || player.anise > 0) return;
      if (why !== 'stove' && (attacking() || player.safe > 0)) return;
      if (why === 'stove' && player.dashT > 0) return;
      var dx = player.x - fromX, dy = player.y - fromY, d = Math.sqrt(dx * dx + dy * dy) || 1;
      player.vx = dx / d * 7; player.vy = dy / d * 7;
      if (player.shield) {
        player.shield = false; player.inv = 1.0; sfx('bonk'); ring(player.x, player.y, '#9fd8ff', 1.4); floatText(player.x, player.y - 0.6, 'Shield!', '#9fd8ff');
        return;
      }
      player.hearts--; player.inv = 1.4; stats.damage++; shake(0.35); sfx('hurt');
      burst(player.x, player.y, 10, '#fff7ea', 4);
      floatText(player.x, player.y - 0.6, why === 'stove' ? 'Hot hot hot!' : 'Ouch!', '#ffb3a8');
      if (player.hearts <= 0) {
        if (player.revive) {
          player.revive = false; player.hearts = 1; player.inv = 2.2; sfx('unlock'); sparkle(player.x, player.y, 18, '#ffe08a');
          emit('toast', { text: '🌕 Second Helping! Back on your feet.' });
        } else {
          loseT = 0; sfx('fail');
        }
      }
    }
    function hitPest(p, fromDash) {
      if (!p.alive) return;
      var boss = !!BOSS[p.k];
      if (boss && p.inv > 0) return;
      p.hp--; p.flash = 0.25; p.stun = boss ? 0.5 : 0.6;
      if (p.k === 'spider' || p.k === 'weevil') p.state = 'idle';
      var dx = p.x - player.x, dy = p.y - player.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
      p.vx = dx / d * (boss ? 4 : 8); p.vy = dy / d * (boss ? 4 : 8);
      if (boss) p.inv = 0.6;
      sfx('bonk'); shake(boss ? 0.3 : 0.12); burst(p.x, p.y, 6, '#fff', 3);
      if (p.hp <= 0) {
        p.alive = false;
        if (p.nest) p.nest.kids = Math.max(0, p.nest.kids - 1);
        if (boss) {
          stats.kings++; sfx('boss'); shake(0.8); sparkle(p.x, p.y, 40, '#ffe08a'); burst(p.x, p.y, 30, p.k === 'queen' ? '#f4b63c' : '#b8322a', 6);
          floatText(p.x, p.y - 0.8, (p.k === 'queen' ? 'Wasp Queen' : 'Rat King') + ' defeated!', '#ffe08a', true);
          pests.forEach(function (q) { if (q.owner === p && q.alive) { q.alive = false; burst(q.x, q.y, 6, '#9d99a6', 3); } });
        } else {
          stats.pests++;
          burst(p.x, p.y, 10, { gull: '#ffffff', roach: '#7a4220', mould: '#8fbf5a', snail: '#e8b46a', frog: '#6fbf4a', weevil: '#5a3a28', spider: '#3a3040', wasp: '#f4c430' }[p.k] || '#8f8b99', 4);
          floatText(p.x, p.y - 0.4, '+' + (perks.lucky ? 2 : 1) + ' 🪙', '#ffe08a');
          // A big mould blob splits into two little ones.
          if (p.k === 'mould' && !p.small) {
            for (var s = -1; s <= 1; s += 2) {
              var m = addPest('mould', p.x + s * 0.35 * (dy / d || 1), p.y - s * 0.35 * (dx / d), null);
              m.small = true; m.r = 0.22; m.hp = m.maxHp = 1; m.speed = 2.3; m.stun = 0.45;
              m.vx = (dx / d) * 3 + s * (dy / d) * 3; m.vy = (dy / d) * 3 - s * (dx / d) * 3;
            }
            floatText(p.x, p.y - 0.8, 'Split!', '#c8f0b0');
          }
        }
      }
    }
    // Oven knobs and kitchen timers.
    function stovesSwitch(off, secs) {
      if (off === stovesOff && !secs) return;
      stovesOff = off; stoveT = off ? (secs || 0) : 0; mapImg = null;
      if (off) { stats.knobs++; sfx('unlock'); emit('toast', { text: secs ? '⏲️ Stoves off for ' + secs + ' seconds. Hurry!' : '🎛️ Click! Every hot stove is off.' }); }
      else { sfx('hurt'); emit('toast', { text: '🔥 The stoves are hot again!' }); }
    }
    function hitNest(n) {
      if (!n.alive || n.flash > 0) return;
      n.hp--; n.flash = 0.35; sfx('crate'); shake(0.25); burst(n.x, n.y, 12, '#6b4a6e', 4);
      if (n.hp <= 0) {
        n.alive = false; stats.nests++; sfx('nest'); setTimeout(function () { sfx('clear'); }, 250); shake(0.5);
        sparkle(n.x, n.y, 30, '#e8d4ff'); ring(n.x, n.y, '#e8d4ff', n.r);
        floatText(n.x, n.y - 0.6, 'Area cleared!', '#e8d4ff', true);
        computeInfest(infestTarget);
        var left = nests.filter(function (q) { return q.alive; }).length;
        if (!left && nests.length > 1) emit('toast', { text: '💜 Every nest is gone!' });
      }
    }

    // ---------------------------------------------------------------- update
    function input() {
      var x = 0, y = 0;
      if (keys.ArrowLeft || keys.KeyA) x -= 1;
      if (keys.ArrowRight || keys.KeyD) x += 1;
      if (keys.ArrowUp || keys.KeyW) y -= 1;
      if (keys.ArrowDown || keys.KeyS) y += 1;
      x += stick.x; y += stick.y;
      var m = Math.sqrt(x * x + y * y);
      if (m > 1) { x /= m; y /= m; }
      return { x: x, y: y, m: Math.min(1, m) };
    }

    function updatePlayer(dt) {
      var p = player, inp = input();
      if (winT >= 0) {
        winT += dt;
        p.x += (exitE.x - p.x) * Math.min(1, dt * 6); p.y += (exitE.y - 0.15 - p.y) * Math.min(1, dt * 6);
        if (winT > 1.1 && !ended) finish(true);
        return;
      }
      if (loseT >= 0) { loseT += dt; if (loseT > 1.2 && !ended) finish(false); return; }
      p.inv = Math.max(0, p.inv - dt); p.dashCd = Math.max(0, p.dashCd - dt); p.tea = Math.max(0, p.tea - dt);
      p.safe = Math.max(0, p.safe - dt); p.postDash = Math.max(0, p.postDash - dt); p.fullHint = Math.max(0, p.fullHint - dt);
      p.magnet = Math.max(0, p.magnet - dt); p.anise = Math.max(0, p.anise - dt); p.clock = Math.max(0, p.clock - dt);
      if (stovesOff && stoveT > 0) { stoveT -= dt; if (stoveT <= 0) stovesSwitch(false); }
      var ch = tileCh(Math.floor(p.x), Math.floor(p.y)), slimy = slime[Math.floor(p.y) * W + Math.floor(p.x)] > 0.15;
      var slow = perks.steady ? 1 : (ch === '%' ? 0.5 : slimy ? 0.55 : 1);
      var speed = 4.4 * (perks.swift ? 1.12 : 1) * (p.tea > 0 ? 1.35 : 1) * (p.anise > 0 ? 1.15 : 1) * slow;
      if (inp.m > 0.1) { p.dx = inp.x / inp.m; p.dy = inp.y / inp.m; p.lookX += (p.dx - p.lookX) * Math.min(1, dt * 10); p.lookY += (p.dy - p.lookY) * Math.min(1, dt * 10); }
      // Steam Dash
      if (wantDash && p.dashCd <= 0 && p.dashT <= 0) {
        p.dashT = 0.19 * (perks.longdash ? 1.4 : 1); p.dashCd = 0.9 * (perks.quickdash ? 0.7 : 1);
        if (inp.m > 0.1) { p.dx = inp.x / inp.m; p.dy = inp.y / inp.m; }
        p.hits = []; p.safe = p.dashT + 0.25; sfx('dash'); steam(p.x, p.y + 0.2, 6);
      }
      wantDash = false;
      if (p.dashT > 0) {
        p.dashT -= dt;
        if (p.dashT <= 0) p.postDash = 0.15;
        p.vx = p.dx * 12.5; p.vy = p.dy * 12.5;
        if (Math.random() < 0.7) steam(p.x - p.dx * 0.3, p.y + 0.15, 1, 0.14);
      } else {
        var k = (ch === '=' && !perks.steady) ? 2.2 : 16;
        p.vx += (inp.x * speed - p.vx) * Math.min(1, dt * k);
        p.vy += (inp.y * speed - p.vy) * Math.min(1, dt * k);
      }
      var push = DIRS[ch];
      var mx = p.vx * dt + (push ? push[0] * 2.6 * dt : 0), my = p.vy * dt + (push ? push[1] * 2.6 * dt : 0);
      var hit = moveBody(p, mx, my, p.r);
      // Smash crates while dashing.
      if (p.dashT > 0) {
        var fx = Math.floor(p.x + p.dx * (p.r + 0.15)), fy = Math.floor(p.y + p.dy * (p.r + 0.15));
        [[fx, fy], hit ? [hit.tx, hit.ty] : null].forEach(function (c) {
          if (c && tileCh(c[0], c[1]) === 'X') {
            tiles[c[1]][c[0]] = '.'; stats.crates++; sfx('crate'); shake(0.15);
            burst(c[0] + 0.5, c[1] + 0.5, 14, '#c98f52', 4, 0.1); floatText(c[0] + 0.5, c[1] + 0.3, '+1 🪙', '#ffe08a');
            computeFlow();
          }
        });
      }
      // Nests and neighbours are round obstacles.
      nests.forEach(function (n) {
        if (!n.alive) return;
        var d = dist(p, n), rr = p.r + 0.42;
        if (d < rr) {
          var nx = (p.x - n.x) / (d || 1), ny = (p.y - n.y) / (d || 1);
          p.x = n.x + nx * rr; p.y = n.y + ny * rr;
          if (attacking()) { hitNest(n); p.dashT = 0; p.postDash = 0; p.safe = Math.max(p.safe, 0.5); p.vx = nx * 6; p.vy = ny * 6; }
        }
      });
      npcs.forEach(function (n) {
        var d = dist(p, n), rr = p.r + 0.4;
        if (d < rr) { var nx = (p.x - n.x) / (d || 1), ny = (p.y - n.y) / (d || 1); p.x = n.x + nx * rr; p.y = n.y + ny * rr; }
        if (d < rr + 0.25) talk(n);
      });
      collide(p, p.r);
      // Hot stoves.
      if (tileCh(Math.floor(p.x), Math.floor(p.y)) === '^' && !stovesOff && !perks.fireproof && p.dashT <= 0) hurtPlayer(p.x - p.dx * 0.5, p.y - p.dy * 0.5, 'stove');
      // The exit.
      var g = goalState();
      if (dist(p, exitE) < 0.75) {
        if (g.ok) { winT = 0; sfx('steam'); setTimeout(function () { sfx('win'); }, 350); steam(exitE.x, exitE.y - 0.3, 14, 0.3); }
        else if (hintCd <= 0) { hintCd = 2.5; emit('toast', { text: '🔒 The steamer needs: ' + missingText(g) }); }
      }
      p.squash = (Math.abs(p.vx) + Math.abs(p.vy)) > 0.5 ? Math.sin(t * 16) * 0.06 : 0;
    }

    function talk(n) {
      if (n.talkCd > 0) return;
      n.talkCd = 3;
      var e = n.e, need = Math.max(1, e.count || 1), have = bag[e.wants] || 0, it = ITEMS[e.wants] || { emoji: '❔', name: e.wants };
      if (n.done) { emit('talk', { npc: e, text: e.thanks || 'Thank you!', done: true, have: need, need: need, item: it }); return; }
      if (have >= need) {
        bag[e.wants] = have - need; n.done = true; n.pop = 1; stats.errands.push(n.idx);
        sfx('errand'); sparkle(n.x, n.y - 0.4, 16, '#ffd1dc'); floatText(n.x, n.y - 0.9, 'Errand done! +5 🪙', '#ffe08a', true);
        if (e.gift && ITEMS[e.gift]) {
          parts.push({ kind: 'emoji', x: n.x, y: n.y - 0.6, vx: 0, vy: -1, life: 1.4, max: 1.4, text: ITEMS[e.gift].emoji + '×' + (e.gift_count || 1), size: 0.5 });
        }
        emit('talk', { npc: e, text: e.thanks || 'Thank you so much!', done: true, justDone: true, have: need, need: need, item: it,
          gift: e.gift && ITEMS[e.gift] ? { item: ITEMS[e.gift], count: e.gift_count || 1 } : null });
      } else {
        sfx('talk');
        emit('talk', { npc: e, text: e.say || ('Could you bring me ' + need + ' ' + it.name + '?'), done: false, have: have, need: need, item: it });
      }
    }

    function updateItems(dt) {
      var magR = player.magnet > 0 ? 3.6 : perks.magnet ? 2.6 : 0.9;
      items.forEach(function (it) {
        if (it.taken) return;
        var d = dist(player, it);
        if (d < magR && winT < 0 && loseT < 0) { var k = Math.min(1, dt * (magR > 1 ? 7 : 10)); it.x += (player.x - it.x) * k; it.y += (player.y - it.y) * k; }
        if (d < 0.5 && winT < 0 && loseT < 0) {
          it.taken = true; picked[it.k] = (picked[it.k] || 0) + 1; bag[it.k] = (bag[it.k] || 0) + 1;
          combo = comboT > 0 ? combo + 1 : 1; comboT = 1.6;
          sfx(MEATS[it.k] ? 'meat' : 'pickup');
          sparkle(it.x, it.y, 8, it.item.gold ? '#ffe08a' : '#fff6c2');
          parts.push({ kind: 'emoji', x: it.x, y: it.y - 0.2, vx: 0, vy: -1.6, life: 0.8, max: 0.8, text: '+' + it.item.emoji, size: 0.42 });
          if (combo >= 3) floatText(player.x, player.y - 1.0, 'Combo ×' + combo + '!', '#ffd34d');
          if (it.item.rarity === 'legendary') { emit('toast', { text: '🌟 LEGENDARY! ' + it.item.emoji + ' ' + it.item.name }); shake(0.3); }
          if (MEATS[it.k]) player.squash = -0.2;
        }
      });
      comboT = Math.max(0, comboT - dt);
      pickups.forEach(function (pk) {
        if (pk.taken) return;
        var d = dist(player, pk);
        if ((pk.k === 'coin' || pk.k === 'bag') && d < magR) { var k2 = Math.min(1, dt * 10); pk.x += (player.x - pk.x) * k2; pk.y += (player.y - pk.y) * k2; }
        if (d >= 0.55 || winT >= 0 || loseT >= 0) return;
        // Oven knobs stay where they are: touching one turns the stoves off.
        if (pk.k === 'knob' || pk.k === 'timer') {
          if (!stovesOff) { stovesSwitch(true, pk.k === 'timer' ? 12 : 0); pk.flash = 1; sparkle(pk.x, pk.y, 14, '#9fd8ff'); ring(pk.x, pk.y, '#9fd8ff', 3); }
          return;
        }
        if (BONUS[pk.k]) { stats.bonuses++; }
        if (pk.k === 'heart' && player.hearts >= maxHearts) { if (player.fullHint <= 0) { player.fullHint = 2.5; floatText(pk.x, pk.y - 0.5, 'Hearts full! Come back later', '#ffd1d1'); } return; }
        pk.taken = true;
        if (pk.k === 'coin') { stats.coins++; sfx('coin'); sparkle(pk.x, pk.y, 5, '#ffe08a'); }
        else if (pk.k === 'heart') { player.hearts++; sfx('unlock'); sparkle(pk.x, pk.y, 12, '#ffb3b3'); floatText(pk.x, pk.y - 0.4, '+1 ♥ healed!', '#ff9b9b'); emit('heal', { hearts: player.hearts }); }
        else if (pk.k === 'tea') { player.tea = 6 * BUFF; sfx('unlock'); floatText(pk.x, pk.y - 0.4, 'Zoom!', '#b7f5b0'); }
        else if (pk.k === 'magnet') { player.magnet = 10 * BUFF; sfx('unlock'); ring(pk.x, pk.y, '#ff8a8a', 3.6); floatText(pk.x, pk.y - 0.4, 'Magnet!', '#ffb3b3'); }
        else if (pk.k === 'bubble') { player.shield = true; sfx('unlock'); ring(pk.x, pk.y, '#9fd8ff', 1.4); floatText(pk.x, pk.y - 0.4, 'Shield bubble!', '#9fd8ff'); }
        else if (pk.k === 'bag') { stats.coins += 5; sfx('coin'); setTimeout(function () { sfx('coin'); }, 90); sparkle(pk.x, pk.y, 14, '#ffe08a'); floatText(pk.x, pk.y - 0.4, '+5 🪙', '#ffe08a', true); }
        else if (pk.k === 'anise') { player.anise = 7 * BUFF; sfx('clear'); sparkle(pk.x, pk.y, 24, '#ffe08a'); floatText(pk.x, pk.y - 0.4, 'STAR ANISE!', '#ffe08a', true); emit('toast', { text: '🌟 Star Anise! Bonk everything you touch.' }); }
        else if (pk.k === 'clock') { player.clock = 8 * BUFF; sfx('unlock'); ring(pk.x, pk.y, '#c8b6ff', 2); floatText(pk.x, pk.y - 0.4, 'Time stops!', '#d9ccff'); }
        else if (pk.k === 'chopsticks') { stats.chopsticks = true; sfx('clear'); sparkle(pk.x, pk.y, 24, '#ffe08a'); emit('found', { kind: 'chopsticks' }); emit('toast', { text: '🥢 Golden Chopsticks found!' }); }
        else if (pk.k === 'postcard') { stats.postcard = true; sfx('clear'); sparkle(pk.x, pk.y, 24, '#ffc2d6'); emit('found', { kind: 'postcard' }); emit('toast', { text: "✉️ One of Grandma's postcards!" }); }
      });
    }

    function updatePests(dt) {
      var alive = 0;
      pests.forEach(function (p) {
        if (!p.alive) return;
        alive++;
        p.flash = Math.max(0, p.flash - dt); p.inv = Math.max(0, (p.inv || 0) - dt);
        var fly = flying(p);
        if (p.stun > 0) {
          p.stun -= dt; p.vx *= Math.pow(0.02, dt); p.vy *= Math.pow(0.02, dt);
          moveBody(p, p.vx * dt, p.vy * dt, p.r, fly);
          return;
        }
        var dp = dist(p, player), tx = 0, ty = 0, spd = p.speed;
        p.st -= dt;
        switch (p.k) {
          case 'ant':
            if (dp < 2.6) { tx = player.x - p.x; ty = player.y - p.y; spd = 1.6; }
            else { if (p.st <= 0) { p.wander = Math.random() * TAU; p.st = rnd(1, 2.5); } tx = Math.cos(p.wander); ty = Math.sin(p.wander); }
            break;
          case 'rat':
            p.chasing = dp < 7.5 && flow[Math.floor(p.y) * W + Math.floor(p.x)] >= 0 && flow[Math.floor(p.y) * W + Math.floor(p.x)] < 14;
            if (p.chasing) { var f = flowDir(p); if (f) { tx = f.x; ty = f.y; } }
            else { spd = 1.3; if (p.st <= 0) { p.wander = Math.random() * TAU; p.st = rnd(0.8, 2); } tx = Math.cos(p.wander); ty = Math.sin(p.wander); }
            break;
          case 'fly':
            if (dp < 6.5) { var a = Math.atan2(player.y - p.y, player.x - p.x) + Math.sin(t * 3 + p.id * 10) * 0.9; tx = Math.cos(a); ty = Math.sin(a); }
            else { tx = Math.cos(t * 0.8 + p.id * 9); ty = Math.sin(t * 1.1 + p.id * 7); spd = 1; }
            break;
          case 'roach':
            if (p.st <= 0) {
              var dirs = [0, Math.PI / 2, Math.PI, -Math.PI / 2];
              p.wander = (dp < 4.5 && Math.random() < 0.6) ? Math.round(Math.atan2(player.y - p.y, player.x - p.x) / (Math.PI / 2)) * Math.PI / 2 : dirs[Math.floor(Math.random() * 4)];
              p.st = rnd(1.5, 3);
            }
            tx = Math.cos(p.wander); ty = Math.sin(p.wander);
            break;
          case 'gull':
            p.cd -= dt;
            if (p.state === 'idle') {
              var ga = t * 0.9 + p.id * 10; tx = p.homeX + Math.cos(ga) * 1.6 - p.x; ty = p.homeY + Math.sin(ga) * 1.2 - p.y; spd = 1.6;
              if (dp < 6.5 && p.cd <= 0) { p.state = 'aim'; p.st = 0.75; sfx('squawk'); }
            } else if (p.state === 'aim') {
              p.tx = player.x; p.ty = player.y; tx = 0; ty = 0; p.ang = Math.atan2(player.y - p.y, player.x - p.x);
              if (p.st <= 0) { p.state = 'swoop'; p.st = 0.75; var sa = Math.atan2(p.ty - p.y, p.tx - p.x); p.sx = Math.cos(sa); p.sy = Math.sin(sa); }
            } else if (p.state === 'swoop') {
              p.vx = p.sx * 8.5; p.vy = p.sy * 8.5; moveBody(p, p.vx * dt, p.vy * dt, p.r, true);
              if (p.st <= 0) { p.state = 'rest'; p.st = 1.6; }
              tx = null;
            } else if (p.state === 'rest') {
              tx = 0; ty = 0;
              if (p.st <= 0) { p.state = 'idle'; p.cd = rnd(1.5, 3); p.homeX = p.x; p.homeY = p.y; }
            }
            break;
          case 'king':
            p.summon -= dt; p.charge -= dt;
            if (p.state === 'aim') { tx = 0; ty = 0; p.ang = Math.atan2(player.y - p.y, player.x - p.x); if (p.st <= 0) { p.state = 'charge'; p.st = 0.7; p.sx = Math.cos(p.ang); p.sy = Math.sin(p.ang); sfx('boss'); } }
            else if (p.state === 'charge') {
              var h = moveBody(p, p.sx * 7.5 * dt, p.sy * 7.5 * dt, p.r, false); tx = null;
              if (h) { shake(0.2); p.st = 0; }
              if (p.st <= 0) { p.state = 'idle'; p.charge = rnd(3.5, 5); }
            } else {
              var f2 = flowDir(p); if (f2) { tx = f2.x; ty = f2.y; } else { tx = player.x - p.x; ty = player.y - p.y; }
              if (p.charge <= 0 && dp < 8) { p.state = 'aim'; p.st = 0.65; }
              if (p.summon <= 0) {
                p.summon = 6;
                var mine = pests.filter(function (q) { return q.alive && q.fromKing; }).length;
                for (var s = 0; s < 2 && mine + s < 4; s++) { var nr = addPest('rat', p.x + rnd(-0.6, 0.6), p.y + rnd(-0.6, 0.6), null); nr.fromKing = true; nr.stun = 0.4; }
                floatText(p.x, p.y - 1, 'Squeak! Get him!', '#ffb3a8'); sfx('squawk');
                pests.forEach(function (q) { if (q.fromKing && !q.owner) q.owner = p; });
              }
            }
            break;
          case 'snail':
            // Slow, and leaves slime behind that slows the bun.
            if (dp < 6) { tx = player.x - p.x; ty = player.y - p.y; }
            else { if (p.st <= 0) { p.wander = Math.random() * TAU; p.st = rnd(2, 4); } tx = Math.cos(p.wander); ty = Math.sin(p.wander); }
            var si = Math.floor(p.y) * W + Math.floor(p.x); if (si >= 0 && si < slime.length) slime[si] = 1;
            break;
          case 'mould':
            // Bounces after you in little hops.
            var hop = Math.max(0, Math.sin(t * 7 + p.id * 20));
            if (dp < 7) { tx = player.x - p.x; ty = player.y - p.y; } else { if (p.st <= 0) { p.wander = Math.random() * TAU; p.st = rnd(1, 2); } tx = Math.cos(p.wander); ty = Math.sin(p.wander); }
            spd = p.speed * (0.25 + hop * 1.3) * (dp < 7 ? 1 : 0.5);
            break;
          case 'frog':
            if (p.state === 'sit') {
              tx = 0; ty = 0; p.z = 0;
              if (p.st <= 0) {
                var fa = dp < 7 ? Math.atan2(player.y - p.y, player.x - p.x) + rnd(-0.35, 0.35) : Math.random() * TAU;
                p.state = 'hop'; p.st = 0.38; p.sx = Math.cos(fa); p.sy = Math.sin(fa); p.ang = fa;
              }
            } else {
              p.z = Math.sin((1 - p.st / 0.38) * Math.PI) * 0.5;
              var fh = moveBody(p, p.sx * 6.5 * dt, p.sy * 6.5 * dt, p.r, false); tx = null;
              if (fh) { p.sx = -p.sx * 0.3; p.sy = -p.sy * 0.3; }
              if (p.st <= 0) { p.state = 'sit'; p.st = rnd(0.7, 1.3); p.z = 0; }
            }
            break;
          case 'weevil':
            // Armoured: charges along a straight line when it sees you, and gets dizzy when it hits a wall.
            if (p.state === 'aim') {
              tx = 0; ty = 0;
              if (p.st <= 0) { p.state = 'charge'; p.st = 1.6; }
            } else if (p.state === 'charge') {
              var wh = moveBody(p, p.sx * 7.5 * dt, p.sy * 7.5 * dt, p.r, false); tx = null; p.ang = Math.atan2(p.sy, p.sx);
              if (wh) { p.state = 'dizzy'; p.st = 1.5; shake(0.12); sfx('bonk'); floatText(p.x, p.y - 0.6, 'Dizzy!', '#fff6c2'); }
              else if (p.st <= 0) { p.state = 'idle'; p.st = rnd(1, 2); }
            } else if (p.state === 'dizzy') {
              tx = 0; ty = 0; if (p.st <= 0) { p.state = 'idle'; p.st = rnd(0.8, 1.6); }
            } else {
              if (p.st <= 0) { p.wander = Math.floor(Math.random() * 4) * Math.PI / 2; p.st = rnd(1.2, 2.5); }
              tx = Math.cos(p.wander); ty = Math.sin(p.wander);
              var ax = Math.abs(player.x - p.x), ay = Math.abs(player.y - p.y);
              if (dp < 7 && (ax < 0.5 || ay < 0.5) && clearLine(p, player)) {
                p.state = 'aim'; p.st = 0.45; sfx('squawk');
                if (ax < 0.5) { p.sx = 0; p.sy = Math.sign(player.y - p.y); } else { p.sx = Math.sign(player.x - p.x); p.sy = 0; }
                p.ang = Math.atan2(p.sy, p.sx);
              }
            }
            break;
          case 'spider':
            // Hides, then pounces when you come close.
            if (p.state === 'hide') {
              tx = 0; ty = 0;
              if (dp < 3.2 && clearLine(p, player)) { p.state = 'aim'; p.st = 0.3; }
            } else if (p.state === 'aim') {
              tx = 0; ty = 0; p.ang = Math.atan2(player.y - p.y, player.x - p.x);
              if (p.st <= 0) { p.state = 'pounce'; p.st = 0.34; p.sx = Math.cos(p.ang); p.sy = Math.sin(p.ang); }
            } else if (p.state === 'pounce') {
              moveBody(p, p.sx * 9 * dt, p.sy * 9 * dt, p.r, false); tx = null;
              if (p.st <= 0) { p.state = 'rest'; p.st = 0.8; }
            } else if (p.state === 'rest') {
              tx = 0; ty = 0; if (p.st <= 0) { p.state = 'chase'; p.st = 2.2; }
            } else {
              var f3 = flowDir(p); if (f3 && dp < 8) { tx = f3.x; ty = f3.y; } else { tx = 0; ty = 0; }
              if (p.st <= 0) { p.state = 'hide'; }
            }
            break;
          case 'wasp':
            // Flies over everything, hovers near you, then darts.
            p.cd -= dt;
            if (p.state === 'aim') {
              tx = 0; ty = 0; p.ang = Math.atan2(player.y - p.y, player.x - p.x);
              if (p.st <= 0) { p.state = 'dart'; p.st = 0.35; p.sx = Math.cos(p.ang); p.sy = Math.sin(p.ang); }
            } else if (p.state === 'dart') {
              moveBody(p, p.sx * 10 * dt, p.sy * 10 * dt, p.r, true); tx = null;
              if (p.st <= 0) { p.state = 'idle'; p.cd = rnd(1.4, 2.6); }
            } else if (dp < 7) {
              var wa = t * 2.2 + p.id * 10; tx = player.x + Math.cos(wa) * 2.2 - p.x; ty = player.y + Math.sin(wa) * 2.2 - p.y;
              if (p.cd <= 0 && dp < 4) { p.state = 'aim'; p.st = 0.45; }
            } else { tx = Math.cos(t * 0.9 + p.id * 9); ty = Math.sin(t * 1.3 + p.id * 7); spd = 1.2; }
            break;
          case 'queen':
            // Boss: hovers around you, calls her wasps, then dives.
            p.summon -= dt; p.cd -= dt;
            if (p.state === 'aim') {
              tx = 0; ty = 0; p.ang = Math.atan2(player.y - p.y, player.x - p.x);
              if (p.st <= 0) { p.state = 'dive'; p.st = 0.6; p.sx = Math.cos(p.ang); p.sy = Math.sin(p.ang); sfx('boss'); }
            } else if (p.state === 'dive') {
              moveBody(p, p.sx * 8.5 * dt, p.sy * 8.5 * dt, p.r, true); tx = null;
              if (p.st <= 0) { p.state = 'tired'; p.st = 1.3; }
            } else if (p.state === 'tired') {
              tx = 0; ty = 0; if (p.st <= 0) { p.state = 'hover'; p.cd = rnd(3, 4.5); }
            } else {
              var qa = t * 0.9 + p.id * 10; tx = player.x + Math.cos(qa) * 3.2 - p.x; ty = player.y + Math.sin(qa) * 2.6 - p.y;
              if (dp > 9) { tx = player.x - p.x; ty = player.y - p.y; }
              if (p.cd <= 0 && dp < 7) { p.state = 'aim'; p.st = 0.7; }
              if (p.summon <= 0) {
                p.summon = 7;
                var mine2 = pests.filter(function (q) { return q.alive && q.owner === p; }).length;
                for (var s2 = 0; s2 < 2 && mine2 + s2 < 4; s2++) { var nw = addPest('wasp', p.x + rnd(-0.6, 0.6), p.y + rnd(-0.6, 0.6), null); nw.fromKing = true; nw.owner = p; nw.stun = 0.4; }
                floatText(p.x, p.y - 1, 'Bzzz! Sting him!', '#ffe08a'); sfx('squawk');
              }
            }
            break;
        }
        if (tx !== null) {
          var m = Math.sqrt(tx * tx + ty * ty);
          if (m > 0.01) { tx /= m; ty /= m; } else { tx = 0; ty = 0; }
          p.vx += (tx * spd - p.vx) * Math.min(1, dt * 8); p.vy += (ty * spd - p.vy) * Math.min(1, dt * 8);
          var ch = tileCh(Math.floor(p.x), Math.floor(p.y));
          var push = !fly && DIRS[ch];
          var hit = moveBody(p, p.vx * dt + (push ? push[0] * 2.6 * dt : 0), p.vy * dt + (push ? push[1] * 2.6 * dt : 0), p.r, fly);
          if (hit && (p.k === 'roach' || p.k === 'ant' || p.k === 'rat' || p.k === 'weevil' || p.k === 'snail' || p.k === 'mould')) p.st = 0;
        }
        if (Math.abs(p.vx) + Math.abs(p.vy) > 0.2 && p.state !== 'aim' && p.k !== 'frog' && !(p.k === 'weevil' && p.state !== 'idle')) {
          var target = Math.atan2(p.vy, p.vx), da = ((target - p.ang + Math.PI * 3) % TAU) - Math.PI;
          p.ang += da * Math.min(1, dt * 12);
        }
        // Touching the bun.
        if (winT < 0 && loseT < 0) {
          var dd = dist(p, player), atk = attacking();
          if (dd < p.r + player.r + (atk ? 0.15 : 0)) {
            if (atk) {
              if (player.hits.indexOf(p) < 0 && !(BOSS[p.k] && p.inv > 0) && !(player.anise > 0 && p.flash > 0)) {
                player.hits.push(p); hitPest(p, true);
                if (player.anise > 0 && player.dashT <= 0) { var ai = player.hits.indexOf(p); player.hits.splice(ai, 1); }
                if (p.alive && player.anise <= 0) {
                  // It survived: the bun bounces off instead of rolling on into it.
                  var bx = player.x - p.x, by = player.y - p.y, bd = Math.sqrt(bx * bx + by * by) || 1;
                  player.dashT = 0; player.postDash = 0; player.vx = bx / bd * 6; player.vy = by / bd * 6;
                  player.safe = Math.max(player.safe, 0.6);
                }
              }
            } else if (p.stun <= 0 && !harmless(p)) {
              hurtPlayer(p.x, p.y);
            }
          }
        }
      });
      // Keep pests from stacking up.
      for (var i = 0; i < pests.length; i++) {
        var a2 = pests[i]; if (!a2.alive) continue;
        for (var j = i + 1; j < pests.length; j++) {
          var b = pests[j]; if (!b.alive) continue;
          var dx = b.x - a2.x, dy = b.y - a2.y, d2 = dx * dx + dy * dy, rr = (a2.r + b.r) * 0.9;
          if (d2 < rr * rr && d2 > 0) { var d = Math.sqrt(d2), o = (rr - d) / 2; a2.x -= dx / d * o; a2.y -= dy / d * o; b.x += dx / d * o; b.y += dy / d * o; }
        }
      }
      if (pests.length > 80) pests = pests.filter(function (p) { return p.alive; });
      // Nests spawn their pests while the bun is near.
      nests.forEach(function (n) {
        if (!n.alive) return;
        n.flash = Math.max(0, n.flash - dt);
        n.spawnT -= dt;
        if (n.spawnT <= 0) {
          n.spawnT = rnd(4, 5.5);
          if (n.kids < 3 && dist(n, player) < 11 && alive < 40) {
            var a3 = Math.random() * TAU, np = addPest(n.k, n.x + Math.cos(a3) * 0.7, n.y + Math.sin(a3) * 0.7, n);
            np.stun = 0.3; n.kids++; burst(n.x, n.y, 6, '#6b4a6e', 2);
          }
        }
      });
    }

    function updateParts(dt) {
      for (var i = parts.length - 1; i >= 0; i--) {
        var q = parts[i];
        q.life -= dt;
        if (q.life <= 0) { parts.splice(i, 1); continue; }
        q.x += (q.vx || 0) * dt; q.y += (q.vy || 0) * dt;
        if (q.g) q.vy += q.g * dt;
        if (q.kind === 'star') { q.vx *= 0.92; q.vy *= 0.92; }
      }
    }

    function update(dt) {
      t += dt;
      if (winT < 0 && loseT < 0 && player.clock <= 0) time += dt;
      for (var si = 0; si < slime.length; si++) if (slime[si] > 0) slime[si] = Math.max(0, slime[si] - dt * 0.12);
      hintCd = Math.max(0, hintCd - dt);
      npcs.forEach(function (n) { n.talkCd = Math.max(0, n.talkCd - dt); n.pop = Math.max(0, n.pop - dt * 2); });
      flowT -= dt; if (flowT <= 0) { computeFlow(); flowT = 0.3; }
      updatePlayer(dt); updateItems(dt); updatePests(dt); updateParts(dt);
      for (var i = 0; i < infest.length; i++) if (infest[i] !== infestTarget[i]) infest[i] += (infestTarget[i] - infest[i]) * Math.min(1, dt * 2.5);
      cam.shake = Math.max(0, cam.shake - dt * 1.6);
      hudT -= dt; if (hudT <= 0) { hudT = 0.1; sendHud(); }
    }

    function sendHud() {
      if (!opts.onHud) return;
      var g = goalState();
      var h = { hearts: player.hearts, maxHearts: maxHearts, shield: player.shield, time: Math.floor(time * 10) / 10, par: L.par || 60,
        dash: player.dashCd > 0 ? 1 - player.dashCd / (0.9 * (perks.quickdash ? 0.7 : 1)) : 1, coins: stats.coins,
        found: items.filter(function (i) { return i.taken; }).length, totalItems: totalItems, tea: player.tea > 0,
        goals: g, chopsticks: stats.chopsticks, postcard: stats.postcard, bosses: bossNames,
        buffs: { magnet: Math.ceil(player.magnet), anise: Math.ceil(player.anise), clock: Math.ceil(player.clock), tea: Math.ceil(player.tea),
          stoves: hasStoves && hasKnob ? (stovesOff ? (stoveT > 0 ? Math.ceil(stoveT) : 'off') : 'on') : null } };
      var s = JSON.stringify(h);
      if (s !== lastHud) { lastHud = s; opts.onHud(h); }
    }

    function finish(won) {
      ended = true; running = false;
      if (won) {
        var res = { time: Math.round(time * 100) / 100, picked: picked, errands: stats.errands.slice(), nests: stats.nests, kings: stats.kings,
          coins: stats.coins, pests: stats.pests, crates: stats.crates, damage: stats.damage, chopsticks: stats.chopsticks, postcard: stats.postcard,
          knobs: stats.knobs, bonuses: stats.bonuses };
        emit('win', { result: res, goals: goalState(), totalItems: totalItems, found: items.filter(function (i) { return i.taken; }).length });
      } else emit('lose', {});
    }

    // ---------------------------------------------------------------- drawing
    var staticLayer = null, staticScale = 0;
    function buildStatic() {
      var scale = Math.min(S * dpr, 4096 / W, 4096 / H);
      staticScale = scale;
      staticLayer = document.createElement('canvas');
      staticLayer.width = Math.ceil(W * scale); staticLayer.height = Math.ceil(H * scale);
      var c = staticLayer.getContext('2d');
      var base = tiles.map(function (r) { return r.map(function (ch) { return ch === 'X' ? '.' : ch; }); });
      c.fillStyle = th.bg; c.fillRect(0, 0, staticLayer.width, staticLayer.height);
      for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) Art.drawTile(c, th, base, x, y, x * scale, y * scale, scale + 0.5, 0);
    }
    function resize() {
      var r = canvas.getBoundingClientRect();
      dpr = Math.min(2, window.devicePixelRatio || 1);
      viewW = Math.max(100, r.width); viewH = Math.max(100, r.height);
      canvas.width = Math.round(viewW * dpr); canvas.height = Math.round(viewH * dpr);
      var newS = clamp(Math.min(viewW / (viewW < 640 ? 8.5 : 15), viewH / 9.5), 34, 64);
      if (Math.abs(newS - S) > 0.5 || !staticLayer) { S = newS; buildStatic(); }
      snapCam();
    }
    function camTarget() {
      var vw = viewW / S, vh = viewH / S, x, y;
      // a little slack past the edges so the HUD never hides the bun
      x = W + 1 <= vw ? W / 2 - vw / 2 : clamp(player.x - vw / 2, -0.5, W - vw + 0.5);
      y = H + 2.5 <= vh ? H / 2 - vh / 2 - 0.6 : clamp(player.y - vh / 2, -1.8, H - vh + 1);
      return { x: x, y: y };
    }
    function snapCam() { var c = camTarget(); cam.x = c.x; cam.y = c.y; }

    function draw() {
      var c = ctx;
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.fillStyle = th.bg; c.fillRect(0, 0, viewW, viewH);
      var ct = camTarget();
      cam.x += (ct.x - cam.x) * 0.15; cam.y += (ct.y - cam.y) * 0.15;
      var sx = cam.shake > 0 ? (Math.random() - 0.5) * cam.shake * 18 : 0, sy = cam.shake > 0 ? (Math.random() - 0.5) * cam.shake * 18 : 0;
      var ox = Math.round(-cam.x * S + sx), oy = Math.round(-cam.y * S + sy);
      c.save(); c.translate(ox, oy);
      c.drawImage(staticLayer, 0, 0, staticLayer.width, staticLayer.height, 0, 0, W * S, H * S);
      var x0 = Math.max(0, Math.floor(cam.x) - 1), y0 = Math.max(0, Math.floor(cam.y) - 1);
      var x1 = Math.min(W - 1, Math.ceil(cam.x + viewW / S) + 1), y1 = Math.min(H - 1, Math.ceil(cam.y + viewH / S) + 1);
      var aopts = { fireproof: !!perks.fireproof, off: stovesOff, warn: stovesOff && stoveT > 0 && stoveT < 3 };
      for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) {
        var ch = tiles[y][x];
        if (Art.ANIMATED[ch]) Art.drawAnimated(c, th, tiles, x, y, x * S, y * S, S + 0.5, t, aopts);
      }
      for (y = y0; y <= y1; y++) for (x = x0; x <= x1; x++) {
        var v = infest[y * W + x];
        if (v > 0.02 && !Art.SOLID[tiles[y][x]]) Art.drawGoo(c, x * S, y * S, S + 0.5, t, v, x, y);
        var sl = slime[y * W + x];
        if (sl > 0.05) Art.drawSlime(c, x * S, y * S, S, sl, x, y);
      }
      for (y = y0; y <= y1; y++) for (x = x0; x <= x1; x++) if (tiles[y][x] === 'X') Art.drawCrate(c, x * S, y * S, S);
      var gs = goalState();
      Art.drawSteamer(c, exitE.x * S, exitE.y * S, S * 0.42, { open: gs.ok, t: t });

      // Everything that stands up, back to front.
      var list = [];
      items.forEach(function (it) { if (!it.taken) list.push({ y: it.y, f: function () { Art.drawItem(c, it.item, it.x * S, it.y * S, S, t); } }); });
      pickups.forEach(function (pk) {
        if (pk.taken) return;
        if (pk.k === 'knob' || pk.k === 'timer') list.push({ y: pk.y, f: function () { Art.drawKnob(c, pk.x * S, pk.y * S, S, t, { timer: pk.k === 'timer', off: stovesOff, frac: stoveT > 0 ? stoveT / 12 : 0 }); } });
        else list.push({ y: pk.y, f: function () { Art.drawPickup(c, pk.k, pk.x * S, pk.y * S, S, t); } });
      });
      nests.forEach(function (n) { if (n.alive) list.push({ y: n.y, f: function () { Art.drawNest(c, n.x * S, n.y * S, S * 0.45, { t: t, hp: n.hp, maxHp: n.maxHp, flash: n.flash > 0 }); } }); });
      npcs.forEach(function (n) { list.push({ y: n.y, f: function () { Art.drawNPC(c, n.e.style, n.x * S, n.y * S, S * 0.4 * (1 + n.pop * 0.25), { t: t, happy: n.done }); } }); });
      pests.forEach(function (p) {
        if (!p.alive) return;
        list.push({ y: p.y + ((p.k === 'fly' || p.k === 'gull' || p.k === 'wasp' || p.k === 'queen') ? 0.5 : 0), f: function () {
          Art.drawPest(c, p.k, p.x * S, p.y * S, p.r * S * 1.05, { t: t + p.id * 5, ang: p.ang, hp: p.hp, maxHp: p.maxHp, flash: p.flash > 0,
            chasing: p.chasing || p.state === 'charge' || p.state === 'dive' || p.state === 'dart', swooping: p.state === 'swoop' || p.state === 'dive',
            alert: p.state === 'aim', hidden: p.k === 'spider' && p.state === 'hide', z: p.z || 0, dizzy: p.state === 'dizzy' || p.state === 'tired', small: p.small });
        } });
      });
      var pl = player;
      list.push({ y: pl.y, f: function () {
        if (winT > 0.5) return;
        var a = 1;
        if (pl.inv > 0 && loseT < 0) a = 0.45 + 0.55 * (Math.sin(t * 30) > 0 ? 1 : 0);
        c.globalAlpha = a;
        var dash = pl.dashT > 0, sq = pl.squash;
        var sxx = dash ? 1.18 : 1 - sq, syy = dash ? 0.86 : 1 + sq;
        if (loseT >= 0) { sxx = 1 + Math.min(1, loseT * 2) * 0.5; syy = 1 - Math.min(1, loseT * 2) * 0.55; }
        if (winT >= 0) { sxx = syy = Math.max(0.2, 1 - winT); }
        var fill = gs.meatGoal ? Math.min(1, gs.meat / gs.meatGoal) : Math.min(1, gs.meat / Math.max(1, meatTotal));
        if (pl.tea > 0) { c.globalAlpha = 0.25 * a; Art.circle(c, pl.x * S, pl.y * S, S * 0.5, '#b7f5b0'); c.globalAlpha = a; }
        if (pl.magnet > 0) { c.globalAlpha = 0.18 * a + 0.08 * Math.sin(t * 6); Art.circle(c, pl.x * S, pl.y * S, S * 3.6, null, '#ff8a8a', 2); c.globalAlpha = a; }
        if (pl.anise > 0) {
          c.globalAlpha = (pl.anise < 2 ? (Math.sin(t * 20) > 0 ? 0.5 : 0.15) : 0.45) * a;
          Art.circle(c, pl.x * S, pl.y * S, S * 0.6, 'rgba(255,214,80,.6)'); c.globalAlpha = a;
          if (Math.random() < 0.3) sparkle(pl.x + rnd(-0.3, 0.3), pl.y + rnd(-0.3, 0.3), 1, '#ffe08a');
        }
        Art.drawBun(c, pl.x * S, pl.y * S - S * 0.06, S * pl.r * (1 + fill * 0.12), { t: t, sx: sxx, sy: syy, fill: fill, hat: opts.hat, lookX: pl.lookX, lookY: pl.lookY,
          back: pl.lookY < -0.75 && Math.abs(pl.lookX) < 0.5, face: loseT >= 0 ? 'ouch' : dash ? 'dash' : (pl.inv > 0 ? 'ouch' : winT >= 0 ? 'joy' : 'happy') });
        if (pl.shield) { c.globalAlpha = 0.35 + 0.15 * Math.sin(t * 5); Art.circle(c, pl.x * S, pl.y * S, S * 0.52, null, '#9fd8ff', 3); }
        c.globalAlpha = 1;
      } });
      list.sort(function (a, b) { return a.y - b.y; });
      list.forEach(function (d) { d.f(); });

      // Particles.
      parts.forEach(function (q) {
        var a = Math.max(0, q.life / q.max), px = q.x * S, py = q.y * S;
        if (q.kind === 'dot') { c.globalAlpha = a; Art.circle(c, px, py, q.size * S, q.color); }
        else if (q.kind === 'steam') { c.globalAlpha = a * 0.75; Art.circle(c, px, py, q.size * S * (1.6 - a * 0.6), '#ffffff'); }
        else if (q.kind === 'star') { c.globalAlpha = a; c.fillStyle = q.color; Art.star(c, px, py, q.size * S); }
        else if (q.kind === 'ring') { c.globalAlpha = a; Art.circle(c, px, py, q.size * S * (1 - a) + 2, null, q.color, 4 * a + 1); }
        else if (q.kind === 'text' || q.kind === 'emoji') {
          c.globalAlpha = Math.min(1, a * 2);
          c.font = (q.kind === 'emoji' ? '' : '700 ') + Math.round(q.size * S) + 'px Fredoka, "Segoe UI Emoji", "Apple Color Emoji", sans-serif';
          c.textAlign = 'center'; c.lineJoin = 'round';
          if (q.kind === 'text') { c.lineWidth = Math.max(3, S * 0.09); c.strokeStyle = '#3d2416'; c.strokeText(q.text, px, py); c.fillStyle = q.color; }
          else c.fillStyle = '#fff';
          c.fillText(q.text, px, py);
        }
      });
      c.globalAlpha = 1;

      // What each neighbour wants, above their heads.
      npcs.forEach(function (n) {
        var e = n.e, it = ITEMS[e.wants], bx = n.x * S, by = n.y * S - S * 0.85;
        c.save();
        c.font = '700 ' + Math.round(S * 0.24) + 'px Fredoka, sans-serif'; c.textAlign = 'center';
        c.lineWidth = 3; c.strokeStyle = 'rgba(61,36,22,.85)'; c.fillStyle = '#fff';
        c.strokeText(e.name || '', bx, n.y * S + S * 0.72); c.fillText(e.name || '', bx, n.y * S + S * 0.72);
        var text = n.done ? '♥' : (it ? it.emoji : '?') + ' ' + Math.min(bag[e.wants] || 0, e.count || 1) + '/' + (e.count || 1);
        c.font = '700 ' + Math.round(S * 0.26) + 'px Fredoka, "Segoe UI Emoji", sans-serif';
        var w = c.measureText(text).width + S * 0.3, hh = S * 0.42, bob = Math.sin(t * 3 + n.idx) * S * 0.04;
        Art.rr(c, bx - w / 2, by - hh / 2 + bob, w, hh, hh / 2);
        c.fillStyle = n.done ? '#ffd1dc' : ((bag[e.wants] || 0) >= (e.count || 1) ? '#c8f0b0' : '#fff7ea'); c.fill();
        c.lineWidth = 2; c.strokeStyle = '#3d2416'; c.stroke();
        c.beginPath(); c.moveTo(bx - S * 0.06, by + hh / 2 + bob - 1); c.lineTo(bx, by + hh / 2 + S * 0.1 + bob); c.lineTo(bx + S * 0.06, by + hh / 2 + bob - 1); c.fill(); c.stroke();
        c.fillStyle = n.done ? '#d63031' : '#3d2416'; c.textBaseline = 'middle';
        c.fillText(text, bx, by + bob + 1);
        c.restore();
      });
      c.restore();

      // Night markets are dark, lit by lanterns.
      if (th.night) drawNight(c, ox, oy, x0, y0, x1, y1, gs);
      drawPointers(c, ox, oy, gs);
    }

    var nightC = null;
    function drawNight(c, ox, oy, x0, y0, x1, y1, gs) {
      if (!nightC) nightC = document.createElement('canvas');
      if (nightC.width !== canvas.width || nightC.height !== canvas.height) { nightC.width = canvas.width; nightC.height = canvas.height; }
      var n = nightC.getContext('2d');
      n.setTransform(dpr, 0, 0, dpr, 0, 0);
      n.globalCompositeOperation = 'source-over'; n.clearRect(0, 0, viewW, viewH);
      n.fillStyle = 'rgba(12,6,34,0.5)'; n.fillRect(0, 0, viewW, viewH);
      n.globalCompositeOperation = 'destination-out';
      function light(x, y, r, a) {
        var g = n.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, 'rgba(0,0,0,' + a + ')'); g.addColorStop(1, 'rgba(0,0,0,0)');
        n.fillStyle = g; n.fillRect(x - r, y - r, r * 2, r * 2);
      }
      light(player.x * S + ox, player.y * S + oy, S * 4, 1);
      if (gs.ok) light(exitE.x * S + ox, exitE.y * S + oy, S * 2.5, 0.9);
      for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) if (tiles[y][x] === 'P') light((x + 0.5) * S + ox, (y + 0.3) * S + oy, S * (2.4 + 0.1 * Math.sin(t * 3 + x)), 0.85);
      c.drawImage(nightC, 0, 0, nightC.width, nightC.height, 0, 0, viewW, viewH);
      // a warm tint where the lanterns are
      c.save(); c.globalCompositeOperation = 'lighter'; c.globalAlpha = 0.12;
      for (y = y0; y <= y1; y++) for (x = x0; x <= x1; x++) if (tiles[y][x] === 'P') { var px = (x + 0.5) * S + ox, py = (y + 0.3) * S + oy, g2 = c.createRadialGradient(px, py, 0, px, py, S * 2); g2.addColorStop(0, '#ff9a3c'); g2.addColorStop(1, 'rgba(255,154,60,0)'); c.fillStyle = g2; c.fillRect(px - S * 2, py - S * 2, S * 4, S * 4); }
      c.restore();
    }

    // Arrows at the screen edge pointing to the exit (when open), pending errands and nests.
    function drawPointers(c, ox, oy, gs) {
      var targets = [];
      if (gs.ok) targets.push({ x: exitE.x, y: exitE.y, icon: '♨️', color: '#f4b63c' });
      npcs.forEach(function (n) { if (!n.done && (bag[n.e.wants] || 0) >= (n.e.count || 1)) targets.push({ x: n.x, y: n.y, icon: (ITEMS[n.e.wants] || {}).emoji || '❗', color: '#c8f0b0' }); });
      if (gs.nestsGoal) nests.forEach(function (n) { if (n.alive) targets.push({ x: n.x, y: n.y, icon: '💥', color: '#d9b8ff' }); });
      pickups.forEach(function (pk) {
        if (pk.taken) return;
        if ((pk.k === 'knob' || pk.k === 'timer') && !stovesOff) targets.push({ x: pk.x, y: pk.y, icon: pk.k === 'timer' ? '⏲️' : '🎛️', color: '#bfe8ff' });
        if (perks.nose && (pk.k === 'chopsticks' || pk.k === 'postcard')) targets.push({ x: pk.x, y: pk.y, icon: pk.k === 'postcard' ? '✉️' : '🥢', color: '#ffe08a' });
      });
      var pad = 26;
      targets.forEach(function (tg) {
        var sx = tg.x * S + ox, sy = tg.y * S + oy;
        if (sx > 0 && sy > 0 && sx < viewW && sy < viewH) return;
        var cx = viewW / 2, cy = viewH / 2, dx = sx - cx, dy = sy - cy;
        var k = Math.min((viewW / 2 - pad) / Math.abs(dx || 1), (viewH / 2 - pad) / Math.abs(dy || 1));
        var px = cx + dx * k, py = cy + dy * k, a = Math.atan2(dy, dx);
        c.save(); c.translate(px, py);
        c.globalAlpha = 0.9 + 0.1 * Math.sin(t * 6);
        c.save(); c.rotate(a); c.beginPath(); c.moveTo(24, 0); c.lineTo(12, -8); c.lineTo(12, 8); c.closePath(); c.fillStyle = '#3d2416'; c.fill(); c.restore();
        Art.circle(c, 0, 0, 15, tg.color, '#3d2416', 2.5);
        Art.drawEmoji(c, tg.icon, 0, 0, 16);
        c.restore();
      });
    }

    var mapImg = null;
    function drawMinimap() {
      var m = opts.minimap;
      if (!m) return;
      var mw = m.clientWidth || 120, mh = m.clientHeight || 80;
      var dp = Math.min(2, window.devicePixelRatio || 1);
      if (m.width !== Math.round(mw * dp)) { m.width = Math.round(mw * dp); m.height = Math.round(mh * dp); mapImg = null; }
      var c = m.getContext('2d'), s = Math.min(mw / W, mh / H), ox = (mw - W * s) / 2, oy = (mh - H * s) / 2;
      c.setTransform(dp, 0, 0, dp, 0, 0); c.clearRect(0, 0, mw, mh);
      if (!mapImg) {
        mapImg = document.createElement('canvas'); mapImg.width = Math.ceil(W * s * dp); mapImg.height = Math.ceil(H * s * dp);
        var mc = mapImg.getContext('2d');
        for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) {
          var ch = L.tiles[y][x];
          mc.fillStyle = ch === '#' ? th.wallFace : ch === '~' ? th.water : Art.SOLID[ch] ? th.ctrFace : ch === '^' ? (stovesOff ? '#556' : '#a33') : ch === ',' ? th.alt : th.floorA;
          mc.fillRect(Math.floor(x * s * dp), Math.floor(y * s * dp), Math.ceil(s * dp), Math.ceil(s * dp));
        }
      }
      c.drawImage(mapImg, ox, oy, W * s, H * s);
      for (var yy = 0; yy < H; yy++) for (var xx = 0; xx < W; xx++) { var v = infest[yy * W + xx]; if (v > 0.1) { c.fillStyle = 'rgba(120,40,160,' + (0.5 * v) + ')'; c.fillRect(ox + xx * s, oy + yy * s, s, s); } }
      function dot(x, y, col, r) { Art.circle(c, ox + x * s, oy + y * s, r || Math.max(1.6, s * 0.45), col, '#3d2416', 1); }
      items.forEach(function (it) { if (!it.taken) dot(it.x, it.y, MEATS[it.k] ? '#e0483a' : '#5e9c4a'); });
      npcs.forEach(function (n) { if (!n.done) dot(n.x, n.y, '#3d8fd1', Math.max(2.4, s * 0.6)); });
      nests.forEach(function (n) { if (n.alive) dot(n.x, n.y, '#a35bd6', Math.max(2.4, s * 0.6)); });
      pickups.forEach(function (pk) { if (!pk.taken && (pk.k === 'knob' || pk.k === 'timer')) dot(pk.x, pk.y, stovesOff ? '#9fd8ff' : '#3d8fd1', Math.max(2.2, s * 0.55)); });
      pests.forEach(function (p) { if (p.alive && BOSS[p.k]) dot(p.x, p.y, '#e0483a', Math.max(2.8, s * 0.7)); });
      dot(exitE.x, exitE.y, goalState().ok ? '#f4b63c' : '#9a7a62', Math.max(2.6, s * 0.7));
      dot(player.x, player.y, '#ffffff', Math.max(3, s * 0.75));
      c.strokeStyle = 'rgba(255,255,255,.8)'; c.lineWidth = 1;
      c.strokeRect(ox + cam.x * s, oy + cam.y * s, viewW / S * s, viewH / S * s);
    }

    // ---------------------------------------------------------------- loop & input
    function frame(now) {
      raf = requestAnimationFrame(frame);
      var dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
      if (running && !paused) update(dt);
      else t += dt * 0.5;
      draw();
      mapT -= dt; if (mapT <= 0) { mapT = 0.2; drawMinimap(); }
    }
    function onKey(e) {
      var down = e.type === 'keydown';
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].indexOf(e.code) >= 0 && running && document.activeElement && document.activeElement.tagName !== 'INPUT') e.preventDefault();
      keys[e.code] = down;
      if (down && !e.repeat && (e.code === 'Space' || e.code === 'ShiftLeft' || e.code === 'ShiftRight' || e.code === 'KeyJ' || e.code === 'KeyK')) wantDash = true;
      if (down && !e.repeat && (e.code === 'Escape' || e.code === 'KeyP') && running) emit('pause', {});
    }
    function onBlur() { keys = {}; if (running && !paused) emit('pause', {}); }
    window.addEventListener('keydown', onKey);
    window.addEventListener('keyup', onKey);
    window.addEventListener('blur', onBlur);
    var ro = window.ResizeObserver ? new ResizeObserver(resize) : null;
    if (ro) ro.observe(canvas); else window.addEventListener('resize', resize);
    resize(); computeFlow();
    raf = requestAnimationFrame(frame);

    return {
      start: function () { running = true; paused = false; last = 0; },
      pause: function () { paused = true; keys = {}; },
      resume: function () { paused = false; last = 0; },
      isPaused: function () { return paused; },
      setStick: function (x, y) { stick.x = x; stick.y = y; },
      dash: function () { wantDash = true; },
      resize: resize,
      destroy: function () {
        cancelAnimationFrame(raf); running = false;
        window.removeEventListener('keydown', onKey); window.removeEventListener('keyup', onKey); window.removeEventListener('blur', onBlur);
        if (ro) ro.disconnect(); else window.removeEventListener('resize', resize);
      },
      // for tests and the editor
      debug: function () { return { player: player, pests: pests, nests: nests, npcs: npcs, items: items, pickups: pickups, stats: stats, picked: picked, bag: bag, goals: goalState(), time: time, tiles: tiles, exit: exitE, stovesOff: stovesOff, stoveT: stoveT, slime: slime }; },
      teleport: function (x, y) { player.x = x; player.y = y; snapCam(); }
    };
  };
})();
