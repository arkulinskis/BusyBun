/* bb-builder.js: the level builder engine (Admin page, Levels tab). Canvas editor with tiles, entities, undo/redo,
   checks and a playtest overlay. Python mounts it through client_code/Components/LevelBuilder:
       BB.mount('builder', el, '{}', emit)  ->  {isDirty(), destroy()}
   emit('call', {fn, args}) -> Promise of the server reply (Python whitelists the admin functions);
   emit('newlevel', {territory}) -> Promise of {name, territory, w, h} from the Python "New level" dialog, or null.
   Territories, players and feedback are Python Forms now (Pages/Admin). */
(function () {
  'use strict';
  var BB = window.BB;
  var esc = function (s) { return BB.esc(s); };

  BB.define('builder', function (root, init, emit) {
    var Art = BB.Art;
    var S = { who: null, data: null, tab: 'levels', players: null };
    var CAT = null, ITEMS = {};
    var ed = null;  // the level being edited
    var playGame = null;

    function call(fn, args) {
      return emit('call', { fn: fn, args: args || [] }).then(function (r) { return r; }, function (e) { console.error(e); return { ok: false, error: 'Server error.' }; });
    }
    function setData(d) {
      if (!d) return;
      if (d.ok === false && d.error) BB.toast(esc(d.error), 'err');
      if (!d.territories) return;
      S.data = d; CAT = d.catalog; ITEMS = {}; CAT.items.forEach(function (i) { ITEMS[i.key] = i; });
    }

    // ------------------------------------------------------------ start
    function start() {
      root.innerHTML = '<p class="a-loading">Loading the levels…</p>';
      call('admin_state').then(function (d) { setData(d); if (S.data && alive) renderLevels(root); });
    }
    var alive = true;

    function confirmLeave() { return !(ed && ed.dirty) || window.confirm('You have unsaved changes to "' + ed.name + '". Leave without saving?'); }
    function onUnload(e) { if (ed && ed.dirty) { e.preventDefault(); e.returnValue = ''; } }
    window.addEventListener('beforeunload', onUnload);

    // ------------------------------------------------------------ levels tab
    function territoryOf(key) { return S.data.territories.filter(function (t) { return t.key === key; })[0]; }
    function openLevel(tkey, lv) {
      ed = { key: lv.key, name: lv.name, territory: tkey, published: lv.published, builtin: lv.builtin, data: JSON.parse(JSON.stringify(lv.data)),
        dirty: false, undo: [], redo: [], sel: -1, tool: 'paint', brush: ed ? ed.brush : { kind: 'tile', ch: '#' }, zoom: ed ? ed.zoom : 32, grid: ed ? ed.grid : true, serverMsgs: lv.errors ? { errors: lv.errors, warnings: lv.warnings } : null };
    }
    function blankLevel(name, tkey, w, h) {
      var tiles = [];
      for (var y = 0; y < h; y++) { var r = ''; for (var x = 0; x < w; x++) r += (x === 0 || y === 0 || x === w - 1 || y === h - 1) ? '#' : '.'; tiles.push(r); }
      return { key: null, name: name, published: false, builtin: false,
        data: { w: w, h: h, tiles: tiles, ents: [{ t: 'start', x: 1, y: 1 }, { t: 'exit', x: w - 2, y: h - 2 }], goals: { meat: 0, errands: false, nests: false }, par: 60, intro: '' } };
    }
    function renderLevels(body) {
      if (!ed) {
        var t0 = S.data.territories[0];
        if (t0 && t0.levels[0]) openLevel(t0.key, t0.levels[0]);
        else { var b = blankLevel('New level', t0 ? t0.key : null, 24, 14); openLevel(t0 ? t0.key : null, b); }
      }
      body.innerHTML = '<aside class="a-side"></aside><section class="a-center"><div class="a-tools"></div><div class="a-canvas"><canvas></canvas></div><div class="a-status"></div></section><aside class="a-right"></aside>';
      drawSide(body.querySelector('.a-side'));
      drawTools(body.querySelector('.a-tools'));
      drawRight(body.querySelector('.a-right'));
      setupCanvas(body.querySelector('.a-canvas canvas'));
      render();
    }
    function drawSide(side) {
      var html = '';
      S.data.territories.forEach(function (t) {
        html += '<div class="a-terr"><h4><span class="bb-emoji">' + esc(t.emoji) + '</span>' + esc(t.name) + (t.published ? '' : ' <small class="bb-muted">(hidden)</small>') + '<span class="n">' + t.levels.length + '</span></h4>';
        t.levels.forEach(function (l, i) {
          var on = ed && ed.key === l.key;
          html += '<div class="a-lv ' + (on ? 'on' : '') + '" data-lv="' + esc(l.key) + '" data-t="' + esc(t.key) + '"><span class="th"></span><div class="nm">' + esc(l.name) +
            '<small>' + l.data.w + '×' + l.data.h + ' · ' + (l.clears || 0) + ' clears' + (l.errors.length ? ' · <span style="color:#b8352a">' + l.errors.length + ' error' + (l.errors.length > 1 ? 's' : '') + '</span>' : '') + '</small></div>' +
            '<span class="a-dot ' + (l.errors.length ? 'err' : l.published ? 'pub' : '') + '" title="' + (l.published ? 'Published' : 'Draft') + '"></span>' +
            '<div class="mv"><button data-mv="-1" title="Move up">▲</button><button data-mv="1" title="Move down">▼</button></div></div>';
        });
        html += '<button class="a-add" data-new="' + esc(t.key) + '">+ New level</button></div>';
      });
      if (ed && !ed.key) html = '<div class="a-lv on"><div class="nm">' + esc(ed.name) + '<small>Not saved yet</small></div></div>' + html;
      html += '<p class="bb-muted" style="font-size:12px;font-weight:700;margin:6px 2px">● green = published · ● grey = draft · ● red = has errors</p>';
      side.innerHTML = html;
      side.querySelectorAll('.a-lv[data-lv]').forEach(function (row) {
        var t = territoryOf(row.dataset.t), l = t.levels.filter(function (x) { return x.key === row.dataset.lv; })[0];
        row.querySelector('.th').appendChild(Art.levelThumb(l.data, t.theme, 54));
      });
      side.onclick = function (e) {
        var mv = e.target.closest('[data-mv]');
        if (mv) { e.stopPropagation(); var row = mv.closest('[data-lv]'); call('move_level', [row.dataset.lv, +mv.dataset.mv]).then(function (d) { setData(d); drawSide(side); }); return; }
        var nw = e.target.closest('[data-new]');
        if (nw) { if (!confirmLeave()) return; newLevelModal(nw.dataset.new); return; }
        var r2 = e.target.closest('.a-lv[data-lv]');
        if (r2 && (!ed || r2.dataset.lv !== ed.key)) {
          if (!confirmLeave()) return;
          var t2 = territoryOf(r2.dataset.t), l2 = t2.levels.filter(function (x) { return x.key === r2.dataset.lv; })[0];
          openLevel(t2.key, l2); renderLevels(root);
        }
      };
    }
    function newLevelModal(tkey) {
      emit('newlevel', { territory: tkey, territories: S.data.territories.map(function (t) { return [t.emoji + ' ' + t.name, t.key]; }) }).then(function (r) {
        if (!r || !r.name || !alive) return;
        var b = blankLevel(r.name, r.territory, +r.w, +r.h);
        openLevel(r.territory, b); ed.dirty = true; renderLevels(root);
      });
    }

    // ---------- tools bar
    var TOOLS = [['paint', '✏️ Paint', 'B'], ['rect', '▭ Rectangle', 'R'], ['fill', '🪣 Fill', 'F'], ['erase', '🧽 Erase', 'E'], ['select', '↖ Select', 'V']];
    function drawTools(bar) {
      bar.innerHTML = '<span class="lvname">' + esc(ed.name) + '</span><span class="dirty">' + (ed.dirty ? '● unsaved' : '') + '</span>' +
        '<div class="grp">' + TOOLS.map(function (t) { return '<button class="t ' + (ed.tool === t[0] ? 'on' : '') + '" data-tool="' + t[0] + '" title="' + t[1] + ' (' + t[2] + ')">' + t[1] + '</button>'; }).join('') + '</div>' +
        '<div class="grp"><button class="t" data-a="undo" title="Undo (Ctrl+Z)" ' + (ed.undo.length ? '' : 'disabled') + '>↶</button><button class="t" data-a="redo" title="Redo (Ctrl+Y)" ' + (ed.redo.length ? '' : 'disabled') + '>↷</button></div>' +
        '<div class="grp"><button class="t" data-a="zout" title="Zoom out">−</button><button class="t" data-a="zin" title="Zoom in">+</button><button class="t ' + (ed.grid ? 'on' : '') + '" data-a="grid" title="Grid">#</button></div>' +
        '<span class="sp"></span>' +
        '<button class="bb-btn small jade" data-a="play">▶ Playtest</button>' +
        '<button class="bb-btn small cream" data-a="dup">⧉ Duplicate</button>' +
        (ed.key ? '<button class="bb-btn small cream" data-a="del">🗑 Delete</button>' : '') +
        (ed.builtin ? '<button class="bb-btn small cream" data-a="restore" title="Put this built-in level back as it shipped">↺ Original</button>' : '') +
        '<button class="bb-btn small red" data-a="save">💾 Save</button>';
      bar.onclick = function (e) {
        var t = e.target.closest('[data-tool]');
        if (t) { ed.tool = t.dataset.tool; drawTools(bar); return; }
        var a = e.target.closest('[data-a]'); if (!a || a.disabled) return;
        var k = a.dataset.a;
        if (k === 'undo') undo(); else if (k === 'redo') redo();
        else if (k === 'zin') { ed.zoom = Math.min(64, ed.zoom + 6); render(); }
        else if (k === 'zout') { ed.zoom = Math.max(12, ed.zoom - 6); render(); }
        else if (k === 'grid') { ed.grid = !ed.grid; drawTools(bar); render(); }
        else if (k === 'save') save();
        else if (k === 'play') playtest();
        else if (k === 'dup') { var copy = { key: null, name: (ed.name + ' (copy)').slice(0, 40), published: false, builtin: false, data: JSON.parse(JSON.stringify(ed.data)) }; openLevel(ed.territory, copy); ed.dirty = true; renderLevels(root); BB.toast('Copy made. Save it to keep it.'); }
        else if (k === 'del') {
          if (!window.confirm('Delete "' + ed.name + '"? Players lose its leaderboard. This can\'t be undone.')) return;
          call('delete_level', [ed.key]).then(function (d) { setData(d); ed = null; BB.toast('Level deleted.'); renderLevels(root); });
        } else if (k === 'restore') {
          if (!window.confirm('Put "' + ed.name + '" back to how it shipped? Your edits to it will be lost.')) return;
          call('restore_level', [ed.key]).then(function (d) { setData(d); reopen(ed.key); BB.toast('Restored.'); });
        }
      };
    }
    function reopen(key) {
      S.data.territories.forEach(function (t) { t.levels.forEach(function (l) { if (l.key === key) openLevel(t.key, l); }); });
      renderLevels(root);
    }

    // ---------- right panel: palette, inspector, settings, checks
    var PICKUP_EMOJI = { coin: '🪙', heart: '❤️', tea: '🍵', chopsticks: '🥢', postcard: '✉️' };
    function swatch(kind, val, title) {
      var on = ed.brush.kind === kind && (ed.brush.ch === val || ed.brush.k === val || (kind === 'start' || kind === 'exit' || kind === 'npc') && ed.brush.kind === kind);
      return '<div class="a-sw ' + (on ? 'on' : '') + '" data-b="' + kind + '" data-v="' + esc(val || '') + '" title="' + esc(title) + '"></div>';
    }
    function drawRight(panel) {
      var th = territoryOf(ed.territory) || { theme: 'kitchen' };
      var d = ed.data, g = d.goals || {};
      var html = '<div class="a-box"><h3>🧱 Tiles</h3><div class="a-pal">' + CAT.tiles.map(function (t) { return swatch('tile', t.ch, t.name + ' (' + t.ch + ')'); }).join('') + '</div></div>' +
        '<div class="a-box"><h3>📍 Start, exit, neighbours</h3><div class="a-pal">' + swatch('start', 'start', 'Bun start') + swatch('exit', 'exit', 'Exit steamer') + swatch('npc', 'npc', 'Neighbour with an errand') +
        CAT.pickups.map(function (p) { return swatch('pickup', p.key, p.name); }).join('') + '</div></div>' +
        '<div class="a-box"><h3>🐀 Pests & nests</h3><div class="a-pal">' + CAT.pests.map(function (p) { return swatch('pest', p.key, p.name + ': ' + p.desc); }).join('') +
        CAT.pests.filter(function (p) { return !p.boss; }).map(function (p) { return swatch('nest', p.key, p.name + ' nest'); }).join('') + '</div></div>' +
        CAT.categories.map(function (c) {
          return '<div class="a-box"><h3>' + esc(c.emoji + ' ' + c.name) + '</h3><div class="a-pal">' + CAT.items.filter(function (i) { return i.cat === c.key; }).map(function (i) { return swatch('item', i.key, i.name + ' (' + i.rarity + ')'); }).join('') + '</div></div>';
        }).join('') +
        '<div class="a-box a-insp"></div>' +
        '<div class="a-box"><h3>⚙️ Level settings</h3>' +
        '<div class="a-f"><label>Name</label><input data-s="name" maxlength="40" value="' + esc(ed.name) + '"></div>' +
        '<div class="a-f"><label>Territory</label><select data-s="territory">' + S.data.territories.map(function (t) { return '<option value="' + esc(t.key) + '"' + (t.key === ed.territory ? ' selected' : '') + '>' + esc(t.emoji + ' ' + t.name) + '</option>'; }).join('') + '</select></div>' +
        '<label class="a-chk"><input type="checkbox" data-s="published"' + (ed.published ? ' checked' : '') + '> Published (players can see it)</label>' +
        '<div class="a-row"><div class="a-f"><label>Width</label><input type="number" min="8" max="64" data-s="w" value="' + d.w + '"></div><div class="a-f"><label>Height</label><input type="number" min="6" max="48" data-s="h" value="' + d.h + '"></div></div>' +
        '<div class="a-row" style="margin-bottom:8px"><button class="bb-btn small cream" data-a="resize">Resize</button><button class="bb-btn small cream" data-a="border">Wall border</button></div>' +
        '<div class="a-row"><div class="a-f"><label>Meat goal</label><input type="number" min="0" max="200" data-s="meat" value="' + (g.meat || 0) + '"></div><div class="a-f"><label>Par time (s)</label><input type="number" min="5" max="3600" data-s="par" value="' + (d.par || 60) + '"></div></div>' +
        '<label class="a-chk"><input type="checkbox" data-s="errands"' + (g.errands ? ' checked' : '') + '> Must finish every errand</label>' +
        '<label class="a-chk"><input type="checkbox" data-s="nests"' + (g.nests ? ' checked' : '') + '> Must destroy every nest</label>' +
        '<div class="a-f"><label>Intro text (shown before the level)</label><textarea data-s="intro" maxlength="400">' + esc(d.intro || '') + '</textarea></div></div>' +
        '<div class="a-box"><h3>✅ Checks</h3><div class="a-msgs"></div></div>';
      panel.innerHTML = html;
      panel.querySelectorAll('.a-sw').forEach(function (sw) {
        var c = Art.canvas(34, 34), b = sw.dataset.b, v = sw.dataset.v;
        drawBrushIcon(c.ctx, b, v, th.theme, 34);
        sw.appendChild(c.el);
      });
      drawInspector();
      drawChecks();
      panel.onclick = function (e) {
        var sw = e.target.closest('.a-sw');
        if (sw) {
          var b = sw.dataset.b, v = sw.dataset.v;
          ed.brush = b === 'tile' ? { kind: 'tile', ch: v } : { kind: b, k: v };
          if (ed.tool !== 'paint' && !(ed.tool === 'rect' || ed.tool === 'fill') || (b !== 'tile' && ed.tool !== 'paint')) ed.tool = 'paint';
          panel.querySelectorAll('.a-sw.on').forEach(function (x) { x.classList.remove('on'); }); sw.classList.add('on');
          drawTools(root.querySelector('.a-tools'));
          return;
        }
        var a = e.target.closest('[data-a]'); if (!a) return;
        if (a.dataset.a === 'resize') {
          var w = clampInt(panel.querySelector('[data-s="w"]').value, 8, 64), h = clampInt(panel.querySelector('[data-s="h"]').value, 6, 48);
          change(function () { resizeTo(w, h); }); drawRight(panel);
        } else if (a.dataset.a === 'border') {
          change(function () { var dd = ed.data; dd.tiles = dd.tiles.map(function (r, y) { return r.split('').map(function (ch, x) { return (x === 0 || y === 0 || x === dd.w - 1 || y === dd.h - 1) ? '#' : ch; }).join(''); }); });
        } else if (a.dataset.a === 'delent' && ed.sel >= 0) { change(function () { ed.data.ents.splice(ed.sel, 1); ed.sel = -1; }); drawInspector(); }
      };
      panel.oninput = panel.onchange = function (e) {
        var el = e.target;
        if (el.dataset.s) {
          var k = el.dataset.s, d2 = ed.data;
          if (k === 'name') ed.name = el.value;
          else if (k === 'territory') { ed.territory = el.value; markDirty(); render(); if (e.type === 'change') drawRight(panel); return; }
          else if (k === 'published') ed.published = el.checked;
          else if (k === 'meat') d2.goals.meat = clampInt(el.value, 0, 200);
          else if (k === 'par') d2.par = clampInt(el.value, 5, 3600);
          else if (k === 'errands') d2.goals.errands = el.checked;
          else if (k === 'nests') d2.goals.nests = el.checked;
          else if (k === 'intro') d2.intro = el.value;
          else return;
          markDirty(); drawChecks();
          if (k === 'name') root.querySelector('.lvname').textContent = ed.name;
        } else if (el.dataset.p && ed.sel >= 0) {
          var en = ed.data.ents[ed.sel], p = el.dataset.p;
          if (p === 'count' || p === 'gift_count' || p === 'r') en[p] = clampInt(el.value, p === 'gift_count' ? 0 : 1, p === 'r' ? 12 : 20);
          else if (p === 'gift') { en.gift = el.value || null; if (en.gift && !en.gift_count) en.gift_count = 1; }
          else en[p] = el.value;
          markDirty(); drawChecks(); render();
        }
      };
    }
    function drawBrushIcon(c, b, v, theme, s) {
      var th = Art.theme(theme);
      if (b === 'tile') {
        var tiles = [v + v + v, v + v + v, v + v + v];
        if (v === '#') tiles = ['###', '###', '...'];
        c.save(); c.beginPath(); c.rect(0, 0, s, s); c.clip();
        c.translate(-s, -s);
        for (var y = 0; y < 3; y++) for (var x = 0; x < 3; x++) Art.drawTile(c, th, tiles, x, y, x * s, y * s, s, 0.3);
        c.restore();
      } else drawEntity(c, { t: b, k: v, style: 'dumpling' }, s / 2, s / 2, s, 0);
    }
    function drawEntity(c, e, cx, cy, s, t) {
      if (e.t === 'start') Art.drawBun(c, cx, cy, s * 0.32, { t: t, hat: 'none' });
      else if (e.t === 'exit') Art.drawSteamer(c, cx, cy, s * 0.4, { open: false, t: t, noLock: true });
      else if (e.t === 'item') Art.drawItem(c, ITEMS[e.k] || { emoji: '❔' }, cx, cy, s, t, { still: true });
      else if (e.t === 'pickup') { if (e.k === 'coin') Art.drawCoin(c, cx, cy, s * 0.24, 0, true); else Art.drawPickup(c, e.k, cx, cy, s, 0); }
      else if (e.t === 'pest') Art.drawPest(c, e.k, cx, cy, s * (e.k === 'king' || e.k === 'queen' ? 0.42 : 0.3), { t: t, ang: -Math.PI / 2 + 0.0001, hp: 1, maxHp: 1 });
      else if (e.t === 'nest') { Art.drawNest(c, cx, cy, s * 0.4, { t: 0 }); Art.drawEmoji(c, { ant: '🐜', rat: '🐀', fly: '🪰', roach: '🪳', gull: '🐦', snail: '🐌', mould: '🦠', frog: '🐸', weevil: '🪲', spider: '🕷️', wasp: '🐝' }[e.k] || '🐜', cx + s * 0.28, cy - s * 0.28, s * 0.32); }
      else if (e.t === 'npc') Art.drawNPC(c, e.style || 'dumpling', cx, cy, s * 0.36, { t: t });
    }
    function drawInspector() {
      var box = root.querySelector('.a-insp'); if (!box) return;
      if (ed.sel < 0 || !ed.data.ents[ed.sel]) { box.innerHTML = '<h3>🔍 Selected</h3><p class="bb-muted" style="font-size:13px;font-weight:700;margin:0">Use ↖ Select and click something on the map to edit it. Neighbours have errands to set up here.</p>'; return; }
      var e = ed.data.ents[ed.sel];
      var itemOpts = function (cur, none) { return (none ? '<option value="">— nothing —</option>' : '') + CAT.items.map(function (i) { return '<option value="' + i.key + '"' + (i.key === cur ? ' selected' : '') + '>' + i.emoji + ' ' + esc(i.name) + '</option>'; }).join(''); };
      var html = '<h3>🔍 Selected: ' + esc({ start: 'Start', exit: 'Exit', item: 'Ingredient', pickup: 'Pickup', pest: 'Pest', nest: 'Nest', npc: 'Neighbour' }[e.t]) + ' <span class="bb-muted" style="font-size:12px">at ' + e.x + ',' + e.y + '</span></h3>';
      if (e.t === 'item') html += '<div class="a-f"><label>Ingredient</label><select data-p="k">' + itemOpts(e.k) + '</select></div>';
      if (e.t === 'pickup') html += '<div class="a-f"><label>Pickup</label><select data-p="k">' + CAT.pickups.map(function (p) { return '<option value="' + p.key + '"' + (p.key === e.k ? ' selected' : '') + '>' + p.emoji + ' ' + esc(p.name) + '</option>'; }).join('') + '</select></div>';
      if (e.t === 'pest' || e.t === 'nest') html += '<div class="a-f"><label>' + (e.t === 'nest' ? 'Spawns' : 'Pest') + '</label><select data-p="k">' + CAT.pests.filter(function (p) { return e.t === 'pest' || !p.boss; }).map(function (p) { return '<option value="' + p.key + '"' + (p.key === e.k ? ' selected' : '') + '>' + esc(p.name) + '</option>'; }).join('') + '</select></div>';
      if (e.t === 'nest') html += '<div class="a-f"><label>Infested radius (tiles)</label><input type="number" min="1" max="12" data-p="r" value="' + (e.r || 4) + '"></div>';
      if (e.t === 'npc') {
        html += '<div class="a-row"><div class="a-f"><label>Name</label><input data-p="name" maxlength="30" value="' + esc(e.name || '') + '"></div><div class="a-f"><label>Looks like</label><select data-p="style">' + CAT.npc_styles.map(function (s) { return '<option value="' + s.key + '"' + (s.key === e.style ? ' selected' : '') + '>' + esc(s.name) + '</option>'; }).join('') + '</select></div></div>' +
          '<div class="a-row"><div class="a-f" style="flex:2"><label>Wants</label><select data-p="wants">' + itemOpts(e.wants) + '</select></div><div class="a-f"><label>How many</label><input type="number" min="1" max="20" data-p="count" value="' + (e.count || 1) + '"></div></div>' +
          '<div class="a-row"><div class="a-f" style="flex:2"><label>Thank-you gift</label><select data-p="gift">' + itemOpts(e.gift, true) + '</select></div><div class="a-f"><label>How many</label><input type="number" min="0" max="20" data-p="gift_count" value="' + (e.gift_count || 0) + '"></div></div>' +
          '<div class="a-f"><label>Asks (before the errand)</label><textarea data-p="say" maxlength="240">' + esc(e.say || '') + '</textarea></div>' +
          '<div class="a-f"><label>Says thanks</label><textarea data-p="thanks" maxlength="240">' + esc(e.thanks || '') + '</textarea></div>';
      }
      if (e.t !== 'start' && e.t !== 'exit') html += '<button class="bb-btn small cream" data-a="delent">🗑 Remove</button>';
      box.innerHTML = html;
    }

    // ---------- client-side checks (the same rules as Levels.check on the server)
    var SOLID = {}; var MEATS = {}; var FLYERS = { fly: 1, gull: 1, wasp: 1, queen: 1 };  // same as Catalog.FLYERS
    function check(d) {
      CAT.tiles.forEach(function (t) { if (t.solid) SOLID[t.ch] = 1; });
      CAT.items.forEach(function (i) { if (i.cat === 'meat') MEATS[i.key] = 1; });
      var errors = [], warnings = [], ents = d.ents || [];
      var starts = ents.filter(function (e) { return e.t === 'start'; }), exits = ents.filter(function (e) { return e.t === 'exit'; });
      if (starts.length !== 1) errors.push('Place exactly one start (the bun).');
      if (exits.length !== 1) errors.push('Place exactly one exit steamer.');
      if (errors.length) return { errors: errors, warnings: warnings };
      function label(e) { return e.t === 'item' ? (ITEMS[e.k] || {}).name : e.t === 'npc' ? (e.name || 'Neighbour') : e.t === 'nest' ? e.k + ' nest' : e.t; }
      ents.forEach(function (e) { if (SOLID[d.tiles[e.y][e.x]] && !(e.t === 'pest' && FLYERS[e.k])) errors.push(label(e) + ' at ' + e.x + ',' + e.y + ' sits inside a solid tile.'); });
      var seen = {}, todo = [[starts[0].x, starts[0].y]]; seen[starts[0].x + ',' + starts[0].y] = 1;
      while (todo.length) {
        var c = todo.pop();
        [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (dd) {
          var nx = c[0] + dd[0], ny = c[1] + dd[1];
          if (nx < 0 || ny < 0 || nx >= d.w || ny >= d.h || seen[nx + ',' + ny]) return;
          var ch = d.tiles[ny][nx];
          if (!SOLID[ch] || ch === 'X') { seen[nx + ',' + ny] = 1; todo.push([nx, ny]); }
        });
      }
      ents.forEach(function (e) {
        if (e.t === 'pest' || seen[e.x + ',' + e.y]) return;
        (e.t === 'exit' || e.t === 'npc' || e.t === 'nest' ? errors : warnings).push(label(e) + ' at ' + e.x + ',' + e.y + " can't be reached from the start.");
      });
      var counts = {}; ents.forEach(function (e) { if (e.t === 'item') counts[e.k] = (counts[e.k] || 0) + 1; });
      var meat = 0; for (var k in counts) if (MEATS[k]) meat += counts[k];
      var g = d.goals || {};
      if ((g.meat || 0) > meat) errors.push('The meat goal is ' + g.meat + ' but the level only has ' + meat + ' meat.');
      var wants = {};
      ents.forEach(function (e) { if (e.t === 'npc') { if (!ITEMS[e.wants]) errors.push(label(e) + ' needs a wanted ingredient.'); else wants[e.wants] = (wants[e.wants] || 0) + Math.max(1, e.count || 1); } });
      for (var w in wants) if (wants[w] > (counts[w] || 0)) errors.push('Errands need ' + wants[w] + ' ' + ITEMS[w].name + ' but the level has ' + (counts[w] || 0) + '.');
      if (g.errands && !Object.keys(wants).length) warnings.push('The errands goal is on but there are no neighbours with errands.');
      if (g.nests && !ents.some(function (e) { return e.t === 'nest'; })) warnings.push('The nests goal is on but there are no nests.');
      if (!ents.some(function (e) { return e.t === 'item'; })) warnings.push('No ingredients to collect.');
      return { errors: errors, warnings: warnings, meat: meat, items: ents.filter(function (e) { return e.t === 'item'; }).length };
    }
    function drawChecks() {
      var box = root.querySelector('.a-msgs'); if (!box) return;
      var r = check(ed.data);
      box.innerHTML = (r.errors.map(function (m) { return '<div class="e">✖ ' + esc(m) + '</div>'; }).join('') + r.warnings.map(function (m) { return '<div class="w">⚠ ' + esc(m) + '</div>'; }).join('')) ||
        '<div class="ok">✔ Looks playable!' + (r.items != null ? ' ' + r.items + ' ingredients, ' + r.meat + ' meat.' : '') + '</div>';
      if (r.errors.length && ed.published) box.insertAdjacentHTML('beforeend', '<div class="w">Levels with errors are saved as drafts.</div>');
      var stEl = root.querySelector('.a-status');
      if (stEl) {
        var cnt = {}; ed.data.ents.forEach(function (e) { cnt[e.t] = (cnt[e.t] || 0) + 1; });
        stEl.innerHTML = '<span>' + ed.data.w + '×' + ed.data.h + '</span><span>🥩 ' + (r.meat || 0) + ' meat</span><span>🧺 ' + (cnt.item || 0) + ' ingredients</span><span>🤝 ' + (cnt.npc || 0) + ' neighbours</span><span>🐀 ' + (cnt.pest || 0) + ' pests</span><span>💥 ' + (cnt.nest || 0) + ' nests</span>' +
          '<span class="hov"></span><span style="margin-left:auto">' + (r.errors.length ? '<b style="color:#b8352a">' + r.errors.length + ' error(s)</b>' : '<b style="color:#457a35">Playable</b>') + '</span>';
      }
    }

    // ---------- editing
    function clampInt(v, a, b) { v = parseInt(v, 10); if (isNaN(v)) v = a; return Math.max(a, Math.min(b, v)); }
    function snapshot() { return JSON.stringify(ed.data); }
    function markDirty() { if (!ed.dirty) { ed.dirty = true; var dt = root.querySelector('.a-tools .dirty'); if (dt) dt.textContent = '● unsaved'; } }
    function change(fn, noSnap) {
      if (!noSnap) { ed.undo.push(snapshot()); if (ed.undo.length > 120) ed.undo.shift(); ed.redo = []; }
      fn(); markDirty(); render(); drawChecks();
      var bar = root.querySelector('.a-tools'); if (bar && !noSnap) drawTools(bar);
    }
    function undo() { if (!ed.undo.length) return; ed.redo.push(snapshot()); ed.data = JSON.parse(ed.undo.pop()); ed.sel = -1; afterHistory(); }
    function redo() { if (!ed.redo.length) return; ed.undo.push(snapshot()); ed.data = JSON.parse(ed.redo.pop()); ed.sel = -1; afterHistory(); }
    function afterHistory() { markDirty(); render(); drawChecks(); drawInspector(); drawTools(root.querySelector('.a-tools')); }
    function setTile(x, y, ch) { var r = ed.data.tiles[y]; if (r[x] === ch) return false; ed.data.tiles[y] = r.slice(0, x) + ch + r.slice(x + 1); return true; }
    function entAt(x, y) { for (var i = ed.data.ents.length - 1; i >= 0; i--) { var e = ed.data.ents[i]; if (e.x === x && e.y === y) return i; } return -1; }
    function placeEnt(x, y) {
      var b = ed.brush, ents = ed.data.ents, i = entAt(x, y);
      if (b.kind === 'start' || b.kind === 'exit') {
        for (var j = ents.length - 1; j >= 0; j--) if (ents[j].t === b.kind) ents.splice(j, 1);
        i = entAt(x, y); if (i >= 0) ents.splice(i, 1);
        ents.push({ t: b.kind, x: x, y: y }); return;
      }
      if (i >= 0) ents.splice(i, 1);
      var e = { t: b.kind, x: x, y: y };
      if (b.kind === 'item' || b.kind === 'pickup' || b.kind === 'pest') e.k = b.k;
      if (b.kind === 'nest') { e.k = b.k; e.r = 4; }
      if (b.kind === 'npc') {
        var any = CAT.items.filter(function (it) { return ed.data.ents.some(function (q) { return q.t === 'item' && q.k === it.key; }); })[0] || CAT.items[0];
        e = { t: 'npc', x: x, y: y, style: 'dumpling', name: 'Neighbour', wants: any.key, count: 1, gift: null, gift_count: 0, say: 'Could you bring me a ' + any.name.toLowerCase() + '?', thanks: 'Thank you!' };
      }
      ents.push(e);
      if (b.kind === 'npc') { ed.sel = ents.length - 1; ed.tool = 'select'; setTimeout(function () { drawInspector(); drawTools(root.querySelector('.a-tools')); BB.toast('Set up the neighbour\'s errand on the right →'); }, 0); }
    }
    function flood(x, y, ch) {
      var from = ed.data.tiles[y][x]; if (from === ch) return;
      var todo = [[x, y]], rows = ed.data.tiles.map(function (r) { return r.split(''); });
      while (todo.length) {
        var c = todo.pop(), cx = c[0], cy = c[1];
        if (cx < 0 || cy < 0 || cx >= ed.data.w || cy >= ed.data.h || rows[cy][cx] !== from) continue;
        rows[cy][cx] = ch; todo.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
      }
      ed.data.tiles = rows.map(function (r) { return r.join(''); });
    }
    function resizeTo(w, h) {
      var d = ed.data;
      d.tiles = Array.apply(null, Array(h)).map(function (_, y) { var r = d.tiles[y] || ''; r = r.slice(0, w); while (r.length < w) r += '.'; return r; });
      d.w = w; d.h = h;
      d.ents = d.ents.filter(function (e) { return e.x < w && e.y < h; });
    }

    // ---------- canvas
    var cv = null, ctx = null, drag = null, hover = null;
    function setupCanvas(c) {
      cv = c; ctx = c.getContext('2d');
      c.addEventListener('contextmenu', function (e) { e.preventDefault(); });
      c.addEventListener('mousedown', onDown);
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
      c.addEventListener('mouseleave', function () { hover = null; render(); });
      c.parentNode.addEventListener('wheel', function (e) {
        if (!e.ctrlKey && !e.metaKey) return;
        e.preventDefault(); ed.zoom = Math.max(12, Math.min(64, ed.zoom + (e.deltaY < 0 ? 4 : -4))); render();
      }, { passive: false });
    }
    function cellOf(e) {
      var r = cv.getBoundingClientRect(), z = ed.zoom;
      var x = Math.floor((e.clientX - r.left - 3) / z), y = Math.floor((e.clientY - r.top - 3) / z);
      return (x >= 0 && y >= 0 && x < ed.data.w && y < ed.data.h) ? { x: x, y: y } : null;
    }
    function onDown(e) {
      var c = cellOf(e); if (!c) return;
      e.preventDefault();
      var right = e.button === 2;
      if (right) { change(function () { var i = entAt(c.x, c.y); if (i >= 0) ed.data.ents.splice(i, 1); else setTile(c.x, c.y, '.'); if (ed.sel >= ed.data.ents.length) ed.sel = -1; }); drawInspector(); drag = { mode: 'erase2' }; return; }
      var tool = ed.tool, b = ed.brush;
      if (tool === 'select') {
        var i = entAt(c.x, c.y); ed.sel = i; drawInspector(); render();
        if (i >= 0) { ed.undo.push(snapshot()); ed.redo = []; drag = { mode: 'move', i: i }; }
        return;
      }
      if (tool === 'erase') { change(function () { var j = entAt(c.x, c.y); if (j >= 0) ed.data.ents.splice(j, 1); ed.sel = -1; }); drag = { mode: 'erase' }; drawInspector(); return; }
      if (b.kind === 'tile') {
        if (tool === 'fill') { change(function () { flood(c.x, c.y, b.ch); }); return; }
        if (tool === 'rect') { drag = { mode: 'rect', a: c, b: c }; render(); return; }
        change(function () { setTile(c.x, c.y, b.ch); }); drag = { mode: 'paint' }; return;
      }
      change(function () { placeEnt(c.x, c.y); }); drag = { mode: 'place', last: c };
    }
    function onMove(e) {
      if (!cv) return;
      var c = cellOf(e);
      var hv = root.querySelector('.a-status .hov');
      if (hv) hv.textContent = c ? 'x ' + c.x + ', y ' + c.y + ' · ' + ((CAT.tiles.filter(function (t) { return t.ch === ed.data.tiles[c.y][c.x]; })[0] || {}).name || '') : '';
      if (!drag) { if ((c && (!hover || c.x !== hover.x || c.y !== hover.y)) || (!c && hover)) { hover = c; render(); } return; }
      if (!c) return;
      hover = c;
      if (drag.mode === 'paint') { if (setTile(c.x, c.y, ed.brush.ch)) { render(); drawChecks(); } }
      else if (drag.mode === 'erase' || drag.mode === 'erase2') { var i = entAt(c.x, c.y); if (i >= 0) { ed.data.ents.splice(i, 1); render(); drawChecks(); } else if (drag.mode === 'erase2' && setTile(c.x, c.y, '.')) { render(); drawChecks(); } }
      else if (drag.mode === 'rect') { drag.b = c; render(); }
      else if (drag.mode === 'move') { var en = ed.data.ents[drag.i]; if (en && (en.x !== c.x || en.y !== c.y) && entAt(c.x, c.y) < 0) { en.x = c.x; en.y = c.y; markDirty(); render(); drawChecks(); drawInspector(); } }
      else if (drag.mode === 'place' && (ed.brush.kind === 'item' || ed.brush.kind === 'pickup') && (c.x !== drag.last.x || c.y !== drag.last.y)) { drag.last = c; if (entAt(c.x, c.y) < 0) { placeEnt(c.x, c.y); render(); drawChecks(); } }
    }
    function onUp() {
      if (!drag) return;
      if (drag.mode === 'rect') {
        var a = drag.a, b = drag.b;
        change(function () { for (var y = Math.min(a.y, b.y); y <= Math.max(a.y, b.y); y++) for (var x = Math.min(a.x, b.x); x <= Math.max(a.x, b.x); x++) setTile(x, y, ed.brush.ch); });
      }
      drag = null; drawTools(root.querySelector('.a-tools'));
    }
    document.addEventListener('keydown', function (e) {
      if (!ed || !cv || !document.body.contains(cv) || playGame) return;
      var tag = (document.activeElement && document.activeElement.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if ((e.ctrlKey || e.metaKey) && (e.key || '').toLowerCase() === 'z') { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
      if ((e.ctrlKey || e.metaKey) && (e.key || '').toLowerCase() === 'y') { e.preventDefault(); redo(); return; }
      if ((e.ctrlKey || e.metaKey) && (e.key || '').toLowerCase() === 's') { e.preventDefault(); save(); return; }
      var map = { b: 'paint', r: 'rect', f: 'fill', e: 'erase', v: 'select' };
      if (map[(e.key || '').toLowerCase()] && !e.ctrlKey && !e.metaKey) { ed.tool = map[(e.key || '').toLowerCase()]; drawTools(root.querySelector('.a-tools')); }
      if ((e.key === 'Delete' || e.key === 'Backspace') && ed.sel >= 0) { var en = ed.data.ents[ed.sel]; if (en && en.t !== 'start' && en.t !== 'exit') { change(function () { ed.data.ents.splice(ed.sel, 1); ed.sel = -1; }); drawInspector(); } }
    });
    function render() {
      if (!cv || !ed) return;
      var d = ed.data, z = ed.zoom, th = Art.theme((territoryOf(ed.territory) || {}).theme);
      var dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = Math.round(d.w * z * dpr); cv.height = Math.round(d.h * z * dpr);
      cv.style.width = d.w * z + 'px'; cv.style.height = d.h * z + 'px';
      var c = ctx; c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.fillStyle = th.bg; c.fillRect(0, 0, d.w * z, d.h * z);
      for (var y = 0; y < d.h; y++) for (var x = 0; x < d.w; x++) Art.drawTile(c, th, d.tiles, x, y, x * z, y * z, z + 0.5, 0.3);
      // nest radius
      d.ents.forEach(function (e) {
        if (e.t !== 'nest') return;
        c.save(); c.setLineDash([6, 5]); c.strokeStyle = 'rgba(140,60,190,.9)'; c.lineWidth = 2; c.fillStyle = 'rgba(120,40,160,.12)';
        c.beginPath(); c.arc((e.x + 0.5) * z, (e.y + 0.5) * z, (e.r || 4) * z, 0, Math.PI * 2); c.fill(); c.stroke(); c.restore();
      });
      if (ed.grid) {
        c.strokeStyle = 'rgba(0,0,0,.13)'; c.lineWidth = 1; c.beginPath();
        for (x = 1; x < d.w; x++) { c.moveTo(x * z + 0.5, 0); c.lineTo(x * z + 0.5, d.h * z); }
        for (y = 1; y < d.h; y++) { c.moveTo(0, y * z + 0.5); c.lineTo(d.w * z, y * z + 0.5); }
        c.stroke();
      }
      d.ents.slice().sort(function (a, b) { return a.y - b.y; }).forEach(function (e) { drawEntity(c, e, (e.x + 0.5) * z, (e.y + 0.5) * z, z, 0); });
      d.ents.forEach(function (e, i) {
        if (e.t === 'npc') { c.font = '700 ' + Math.max(9, z * 0.3) + 'px Fredoka, sans-serif'; c.textAlign = 'center'; c.lineWidth = 3; c.strokeStyle = '#3d2416'; c.fillStyle = '#fff'; var lb = (e.name || '') + ' → ' + ((ITEMS[e.wants] || {}).emoji || '?') + '×' + (e.count || 1); c.strokeText(lb, (e.x + 0.5) * z, e.y * z - 2); c.fillText(lb, (e.x + 0.5) * z, e.y * z - 2); }
        if (i === ed.sel) { c.strokeStyle = '#f4b63c'; c.lineWidth = 3; c.setLineDash([5, 3]); c.strokeRect(e.x * z + 1.5, e.y * z + 1.5, z - 3, z - 3); c.setLineDash([]); }
      });
      if (drag && drag.mode === 'rect') {
        var a = drag.a, b = drag.b;
        c.fillStyle = 'rgba(244,182,60,.35)'; c.strokeStyle = '#3d2416'; c.lineWidth = 2;
        var rx = Math.min(a.x, b.x) * z, ry = Math.min(a.y, b.y) * z, rw = (Math.abs(a.x - b.x) + 1) * z, rh = (Math.abs(a.y - b.y) + 1) * z;
        c.fillRect(rx, ry, rw, rh); c.strokeRect(rx, ry, rw, rh);
      } else if (hover) {
        c.strokeStyle = '#fff'; c.lineWidth = 2; c.strokeRect(hover.x * z + 1, hover.y * z + 1, z - 2, z - 2);
        c.strokeStyle = '#3d2416'; c.lineWidth = 1; c.strokeRect(hover.x * z + 3, hover.y * z + 3, z - 6, z - 6);
      }
    }

    // ---------- save / playtest
    function save() {
      if (!ed.territory) { BB.toast('Create a territory first.', 'err'); return; }
      var spec = { key: ed.key, territory: ed.territory, name: ed.name, published: ed.published, data: ed.data };
      call('save_level', [spec]).then(function (r) {
        if (!r || r.ok === false) { BB.toast(esc((r && r.error) || 'Could not save.'), 'err'); return; }
        setData(r);
        BB.toast(r.note ? '💾 ' + esc(r.note) : '💾 Saved' + (ed.published ? ' and published!' : ' as a draft.'), r.note ? 'err' : 'gold');
        reopen(r.saved);
      });
    }
    function playtest() {
      var th = territoryOf(ed.territory) || { theme: 'kitchen' };
      var chk = check(ed.data);
      if (chk.errors.length && chk.errors.some(function (m) { return /start|exit/.test(m); })) { BB.toast('Add a start and an exit first.', 'err'); return; }
      var wrap = document.createElement('div'); wrap.className = 'bb a-play';
      wrap.innerHTML = '<canvas></canvas><div class="hud"><span class="h"></span><span class="g"></span><span class="tm"></span><span class="sp"></span><button class="bb-btn small" data-a="restart">↻ Restart</button><button class="bb-btn small red" data-a="close">✕ Back to editor</button></div>';
      document.body.appendChild(wrap);
      var say = null;
      function startGame() {
        if (playGame) playGame.destroy();
        playGame = BB.Game(wrap.querySelector('canvas'), {
          level: ed.data, theme: th.theme, items: ITEMS, perks: [], hat: 'toque',
          onHud: function (h) {
            wrap.querySelector('.h').textContent = '♥'.repeat(Math.max(0, h.hearts)) + '♡'.repeat(Math.max(0, h.maxHearts - h.hearts));
            var g = h.goals;
            wrap.querySelector('.g').textContent = '🥩 ' + g.meat + '/' + g.meatGoal + ' · 🤝 ' + g.errandsDone + '/' + g.errandsTotal + ' · 💥 ' + (g.nestsTotal - g.nestsLeft) + '/' + g.nestsTotal + ' · 🧺 ' + h.found + '/' + h.totalItems + (g.ok ? ' · ♨️ open' : '');
            wrap.querySelector('.tm').textContent = '⏱ ' + BB.fmtTime(h.time) + ' / ' + BB.fmtTime(h.par);
          },
          onEvent: function (name, d) {
            if (name === 'toast') BB.toast(esc(d.text));
            else if (name === 'talk') { if (say) say.remove(); say = document.createElement('div'); say.className = 'say'; say.textContent = d.npc.name + ': ' + d.text; wrap.appendChild(say); }
            else if (name === 'win' || name === 'lose') {
              var r = d.result;
              var m = BB.modal('<div style="text-align:center"><h2>' + (name === 'win' ? 'Level complete!' : 'Squished!') + '</h2>' +
                (r ? '<p style="font-weight:700">⏱ ' + BB.fmtTime(r.time) + ' (par ' + BB.fmtTime(ed.data.par) + ') · 🧺 ' + d.found + '/' + d.totalItems + ' ingredients · 🐀 ' + r.pests + ' pests · 💔 ' + r.damage + ' hits</p>' : '<p>Lost all hearts.</p>') +
                '<div class="g-row" style="display:flex;gap:10px;justify-content:center"><button class="bb-btn red" data-a="again">↻ Again</button><button class="bb-btn cream" data-a="back">Back to editor</button></div></div>', { noClose: true });
              m.el.addEventListener('click', function (e) { var a = e.target.closest('[data-a]'); if (!a) return; m.close(); if (a.dataset.a === 'again') startGame(); else close(); });
            }
          }
        });
        playGame.start();
      }
      function close() { if (playGame) playGame.destroy(); playGame = null; wrap.remove(); }
      wrap.addEventListener('click', function (e) { var a = e.target.closest('[data-a]'); if (!a) return; if (a.dataset.a === 'close') close(); else startGame(); });
      startGame();
    }

    start();
    window.BB_ADMIN_DEBUG = { S: S, ed: function () { return ed; }, render: render, check: check };
    return {
      isDirty: function () { return !!(ed && ed.dirty); },
      dirtyName: function () { return ed ? ed.name : ''; },
      destroy: function () { alive = false; window.removeEventListener('beforeunload', onUnload); if (playGame) { playGame.destroy(); playGame = null; } root.innerHTML = ''; }
    };
  });
})();
