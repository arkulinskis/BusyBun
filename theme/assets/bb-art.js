/* Busy Bun — art. Everything is drawn with canvas paths (no image files), so the game, the level
   editor and the menus all share these functions. Sizes are in canvas pixels. */
(function () {
  'use strict';
  var BB = window.BB = window.BB || {};
  var Art = BB.Art = {};
  var TAU = Math.PI * 2;
  var INK = '#3d2416';
  var EMOJI_FONT = '"Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif';

  function hash(x, y) { var h = (x * 374761393 + y * 668265263) | 0; h = (h ^ (h >>> 13)) * 1274126177; return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }
  Art.hash = hash;
  function rr(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }
  Art.rr = rr;
  function circle(ctx, x, y, r, fill, stroke, lw) {
    ctx.beginPath(); ctx.arc(x, y, Math.max(0.1, r), 0, TAU);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1; ctx.stroke(); }
  }
  function ellipse(ctx, x, y, rx, ry, fill, stroke, lw, rot) {
    ctx.beginPath(); ctx.ellipse(x, y, Math.max(0.1, rx), Math.max(0.1, ry), rot || 0, 0, TAU);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1; ctx.stroke(); }
  }
  Art.circle = circle; Art.ellipse = ellipse;
  function shadow(ctx, x, y, rx, ry, a) { ellipse(ctx, x, y, rx, ry, 'rgba(30,15,10,' + (a == null ? 0.2 : a) + ')'); }
  Art.shadow = shadow;

  /* ================================================================ themes */
  Art.THEMES = {
    kitchen: { bg: '#4a2c1d', floorA: '#f6e4c4', floorB: '#eed6ad', floorStyle: 'checker', alt: '#d9574a', altB: '#f3c66b', altStyle: 'rug',
      wallTop: '#b07a52', wallFace: '#7d5236', wallLine: '#5a3823', ctrTop: '#f1e2c6', ctrFace: '#b8865a', ctrStyle: 'plates',
      decor: 'herb', water: '#6cc3e0', waterDeep: '#3d9cc0' },
    market: { bg: '#141020', floorA: '#4a4560', floorB: '#433e57', floorStyle: 'cobble', alt: '#9b2f3c', altB: '#e8b13b', altStyle: 'carpet',
      wallTop: '#3a2f4f', wallFace: '#251d35', wallLine: '#160f22', ctrTop: '#e9dcc4', ctrFace: '#8a3b2b', ctrStyle: 'awning',
      decor: 'lantern', water: '#3c6fa0', waterDeep: '#2a4f78', night: true },
    dimsum: { bg: '#3b1d14', floorA: '#e9c99a', floorB: '#ddb985', floorStyle: 'parquet', alt: '#b8322a', altB: '#e8b13b', altStyle: 'carpet',
      wallTop: '#3f9c86', wallFace: '#256b5a', wallLine: '#174a3e', ctrTop: '#f6efe2', ctrFace: '#a35a3a', ctrStyle: 'teacups',
      decor: 'steamers', water: '#6cc3e0', waterDeep: '#3d9cc0' },
    spice: { bg: '#4a1d10', floorA: '#e8b67f', floorB: '#e0a96e', floorStyle: 'stone', alt: '#7da04a', altB: '#d8402e', altStyle: 'field',
      wallTop: '#a8502d', wallFace: '#7a3519', wallLine: '#55220f', ctrTop: '#e6c79a', ctrFace: '#8a4a26', ctrStyle: 'spices',
      decor: 'chili', water: '#6cc3e0', waterDeep: '#3d9cc0' },
    harbour: { bg: '#1f4f6e', floorA: '#c39462', floorB: '#b78755', floorStyle: 'planks', alt: '#ecd9a6', altB: '#d9c48c', altStyle: 'sand',
      wallTop: '#8a98a3', wallFace: '#5d6b76', wallLine: '#414c55', ctrTop: '#a9805a', ctrFace: '#6f4f33', ctrStyle: 'nets',
      decor: 'barrel', water: '#3aa3cf', waterDeep: '#1f7aa8' },
    banquet: { bg: '#2a0a0e', floorA: '#8e2228', floorB: '#831f25', floorStyle: 'lacquer', alt: '#e0aa38', altB: '#b8322a', altStyle: 'gold',
      wallTop: '#4a1218', wallFace: '#2e0a0e', wallLine: '#1a0507', ctrTop: '#f4e3c0', ctrFace: '#c9962e', ctrStyle: 'feast',
      decor: 'vase', water: '#3aa3cf', waterDeep: '#1f7aa8' },
    // Worlds 7-16
    noodle: { bg: '#2b1a14', floorA: '#d9b48a', floorB: '#cfa77a', floorStyle: 'cobble', alt: '#c0392b', altB: '#f4b63c', altStyle: 'carpet',
      wallTop: '#7a4b32', wallFace: '#55311f', wallLine: '#3a1f12', ctrTop: '#f3e6cc', ctrFace: '#8c4a2a', ctrStyle: 'awning',
      decor: 'lantern', water: '#5aa9c9', waterDeep: '#357f9e' },
    bakery: { bg: '#5a3040', floorA: '#fbe7ec', floorB: '#f6d6de', floorStyle: 'checker', alt: '#f4a6b8', altB: '#fff2c4', altStyle: 'rug',
      wallTop: '#e2a6b4', wallFace: '#b86f84', wallLine: '#8a4a5c', ctrTop: '#fff6e8', ctrFace: '#d29a6a', ctrStyle: 'plates',
      decor: 'bread', water: '#7cc8e6', waterDeep: '#4ea3c6' },
    garden: { bg: '#1e3a1e', floorA: '#d8e8b0', floorB: '#cfe0a3', floorStyle: 'stone', alt: '#5e9c4a', altB: '#a6d36b', altStyle: 'field',
      wallTop: '#6b8f4a', wallFace: '#46663a', wallLine: '#2e4a26', ctrTop: '#efe6cf', ctrFace: '#7a5a3a', ctrStyle: 'teacups',
      decor: 'bush', water: '#6cc3e0', waterDeep: '#3d9cc0' },
    lake: { bg: '#10343a', floorA: '#c9a878', floorB: '#bd9b6b', floorStyle: 'planks', alt: '#7fc79a', altB: '#ffc1d6', altStyle: 'rug',
      wallTop: '#5f8f7a', wallFace: '#3d6b5a', wallLine: '#244a3d', ctrTop: '#e9dcc0', ctrFace: '#6f5a3a', ctrStyle: 'nets',
      decor: 'bush', water: '#4fb3a9', waterDeep: '#2a8a83' },
    terrace: { bg: '#3a3010', floorA: '#e9d79a', floorB: '#e0cc8a', floorStyle: 'stone', alt: '#9cc25a', altB: '#f2d46b', altStyle: 'field',
      wallTop: '#8a7a4a', wallFace: '#5f5230', wallLine: '#3e351c', ctrTop: '#efe2bf', ctrFace: '#8a6a3a', ctrStyle: 'spices',
      decor: 'bush', water: '#6cc3e0', waterDeep: '#3d9cc0' },
    cellar: { bg: '#120c0a', floorA: '#6a5a4c', floorB: '#615246', floorStyle: 'stone', alt: '#7a3b2b', altB: '#c9a46a', altStyle: 'carpet',
      wallTop: '#4a3a30', wallFace: '#2e231c', wallLine: '#1a120c', ctrTop: '#b8a07a', ctrFace: '#5a4230', ctrStyle: 'spices',
      decor: 'lantern', water: '#3c6fa0', waterDeep: '#2a4f78', night: true },
    orchard: { bg: '#3a2a08', floorA: '#f2e3b0', floorB: '#ead79b', floorStyle: 'stone', alt: '#8fc25a', altB: '#ff8f6b', altStyle: 'field',
      wallTop: '#a07a3a', wallFace: '#755425', wallLine: '#4d3615', ctrTop: '#f6e8c8', ctrFace: '#b8862e', ctrStyle: 'plates',
      decor: 'bush', water: '#6cc3e0', waterDeep: '#3d9cc0' },
    frost: { bg: '#0e2a40', floorA: '#e6f4fb', floorB: '#d6ecf7', floorStyle: 'ice', alt: '#a8d8f0', altB: '#ffffff', altStyle: 'rug',
      wallTop: '#9cc7de', wallFace: '#6a9cba', wallLine: '#466f8a', ctrTop: '#f4fbff', ctrFace: '#7ab0cc', ctrStyle: 'plates',
      decor: 'snowman', water: '#5fb6e0', waterDeep: '#2f86b8', slick: 'rgba(150,210,245,.7)' },
    festival: { bg: '#140a24', floorA: '#4a3a6a', floorB: '#433560', floorStyle: 'cobble', alt: '#b8322a', altB: '#f4b63c', altStyle: 'carpet',
      wallTop: '#3a2a5a', wallFace: '#241840', wallLine: '#150c28', ctrTop: '#f3e3c0', ctrFace: '#9b2f3c', ctrStyle: 'awning',
      decor: 'lantern', water: '#3c6fa0', waterDeep: '#2a4f78', night: true },
    dragon: { bg: '#1a0606', floorA: '#5a2420', floorB: '#521f1c', floorStyle: 'lacquer', alt: '#e0aa38', altB: '#8a1a14', altStyle: 'gold',
      wallTop: '#3a1210', wallFace: '#220806', wallLine: '#120302', ctrTop: '#e8c890', ctrFace: '#7a1a14', ctrStyle: 'feast',
      decor: 'vase', water: '#3aa3cf', waterDeep: '#1f7aa8' }
  };
  Art.theme = function (k) { return Art.THEMES[k] || Art.THEMES.kitchen; };
  var SOLID = { '#': 1, 'T': 1, 'P': 1, 'X': 1, '~': 1 };
  Art.SOLID = SOLID;

  function tileAt(tiles, x, y) { return (y < 0 || y >= tiles.length || x < 0 || x >= tiles[0].length) ? '#' : tiles[y][x]; }

  /* ---------------------------------------------------------------- floors */
  function drawFloor(ctx, th, tiles, tx, ty, x, y, s) {
    var h = hash(tx, ty);
    switch (th.floorStyle) {
      case 'checker':
        ctx.fillStyle = (tx + ty) % 2 ? th.floorA : th.floorB; ctx.fillRect(x, y, s, s);
        ctx.strokeStyle = 'rgba(120,80,40,.10)'; ctx.lineWidth = Math.max(1, s * 0.03); ctx.strokeRect(x + 0.5, y + 0.5, s - 1, s - 1);
        break;
      case 'cobble':
        ctx.fillStyle = th.floorA; ctx.fillRect(x, y, s, s);
        ctx.fillStyle = th.floorB;
        for (var i = 0; i < 4; i++) { var hx = hash(tx * 4 + i, ty), hy = hash(tx, ty * 4 + i); rr(ctx, x + (i % 2) * s / 2 + s * 0.04 + hx * s * 0.04, y + (i >> 1) * s / 2 + s * 0.04 + hy * s * 0.04, s * 0.42, s * 0.42, s * 0.1); ctx.fill(); }
        break;
      case 'parquet':
        ctx.fillStyle = th.floorA; ctx.fillRect(x, y, s, s);
        ctx.strokeStyle = 'rgba(110,60,20,.18)'; ctx.lineWidth = Math.max(1, s * 0.03);
        ctx.beginPath();
        if ((tx + ty) % 2) { for (var k = 1; k < 4; k++) { ctx.moveTo(x + k * s / 4, y); ctx.lineTo(x + k * s / 4, y + s); } }
        else { for (var k2 = 1; k2 < 4; k2++) { ctx.moveTo(x, y + k2 * s / 4); ctx.lineTo(x + s, y + k2 * s / 4); } }
        ctx.stroke(); ctx.strokeRect(x + 0.5, y + 0.5, s - 1, s - 1);
        break;
      case 'stone':
        ctx.fillStyle = h < 0.5 ? th.floorA : th.floorB; ctx.fillRect(x, y, s, s);
        ctx.strokeStyle = 'rgba(120,60,20,.16)'; ctx.lineWidth = Math.max(1, s * 0.035); ctx.strokeRect(x + 1, y + 1, s - 2, s - 2);
        if (h > 0.8) { ctx.beginPath(); ctx.moveTo(x + s * 0.2, y + s * 0.3); ctx.lineTo(x + s * 0.45, y + s * 0.5); ctx.lineTo(x + s * 0.4, y + s * 0.75); ctx.stroke(); }
        break;
      case 'planks':
        ctx.fillStyle = th.floorA; ctx.fillRect(x, y, s, s);
        ctx.fillStyle = th.floorB; ctx.fillRect(x, y + s / 2, s, s / 2);
        ctx.strokeStyle = 'rgba(70,40,20,.28)'; ctx.lineWidth = Math.max(1, s * 0.03);
        ctx.beginPath(); ctx.moveTo(x, y + 0.5); ctx.lineTo(x + s, y + 0.5); ctx.moveTo(x, y + s / 2); ctx.lineTo(x + s, y + s / 2);
        var off = ((tx * 7 + ty * 3) % 3) * s / 3; ctx.moveTo(x + off, y); ctx.lineTo(x + off, y + s / 2);
        var off2 = ((tx * 5 + ty * 11) % 3) * s / 3; ctx.moveTo(x + off2, y + s / 2); ctx.lineTo(x + off2, y + s); ctx.stroke();
        ctx.fillStyle = 'rgba(70,40,20,.35)'; circle(ctx, x + s * 0.12, y + s * 0.25, s * 0.03, ctx.fillStyle);
        break;
      case 'lacquer':
        ctx.fillStyle = (tx + ty) % 2 ? th.floorA : th.floorB; ctx.fillRect(x, y, s, s);
        ctx.strokeStyle = 'rgba(232,177,59,.28)'; ctx.lineWidth = Math.max(1, s * 0.03);
        ctx.beginPath(); ctx.moveTo(x + s / 2, y + s * 0.2); ctx.lineTo(x + s * 0.8, y + s / 2); ctx.lineTo(x + s / 2, y + s * 0.8); ctx.lineTo(x + s * 0.2, y + s / 2); ctx.closePath(); ctx.stroke();
        break;
      case 'ice':
        ctx.fillStyle = h < 0.5 ? th.floorA : th.floorB; ctx.fillRect(x, y, s, s);
        ctx.strokeStyle = 'rgba(120,170,200,.25)'; ctx.lineWidth = Math.max(1, s * 0.03); ctx.strokeRect(x + 0.5, y + 0.5, s - 1, s - 1);
        if (h > 0.55) { ctx.strokeStyle = 'rgba(255,255,255,.9)'; ctx.lineWidth = Math.max(1, s * 0.04); ctx.beginPath(); ctx.moveTo(x + s * 0.2, y + s * 0.55); ctx.lineTo(x + s * 0.45, y + s * 0.3); ctx.moveTo(x + s * 0.35, y + s * 0.7); ctx.lineTo(x + s * 0.55, y + s * 0.5); ctx.stroke(); }
        break;
      default:
        ctx.fillStyle = th.floorA; ctx.fillRect(x, y, s, s);
    }
  }

  function drawAlt(ctx, th, tiles, tx, ty, x, y, s) {
    var n = tileAt(tiles, tx, ty - 1) !== ',', so = tileAt(tiles, tx, ty + 1) !== ',', w = tileAt(tiles, tx - 1, ty) !== ',', e = tileAt(tiles, tx + 1, ty) !== ',';
    var b = s * 0.14;
    if (th.altStyle === 'field') {
      ctx.fillStyle = th.alt; ctx.fillRect(x, y, s, s);
      ctx.strokeStyle = 'rgba(40,80,20,.35)'; ctx.lineWidth = Math.max(1, s * 0.04);
      ctx.beginPath(); for (var i = 0; i < 3; i++) { ctx.moveTo(x, y + (i + 0.5) * s / 3); ctx.lineTo(x + s, y + (i + 0.5) * s / 3); } ctx.stroke();
      if (hash(tx, ty) > 0.55) { circle(ctx, x + s * 0.3, y + s * 0.2, s * 0.06, th.altB); circle(ctx, x + s * 0.7, y + s * 0.53, s * 0.06, th.altB); }
      return;
    }
    if (th.altStyle === 'sand') {
      ctx.fillStyle = th.alt; ctx.fillRect(x, y, s, s);
      ctx.fillStyle = th.altB;
      for (var j = 0; j < 5; j++) circle(ctx, x + hash(tx * 9 + j, ty) * s, y + hash(tx, ty * 9 + j) * s, s * 0.025, th.altB);
      return;
    }
    drawFloor(ctx, th, tiles, tx, ty, x, y, s);
    ctx.fillStyle = th.alt;
    ctx.fillRect(x + (w ? b * 0.5 : 0), y + (n ? b * 0.5 : 0), s - (w ? b * 0.5 : 0) - (e ? b * 0.5 : 0), s - (n ? b * 0.5 : 0) - (so ? b * 0.5 : 0));
    ctx.fillStyle = th.altB;
    if (n) ctx.fillRect(x + (w ? b * 0.5 : 0), y + b * 0.5, s - (w ? b * 0.5 : 0) - (e ? b * 0.5 : 0), b * 0.5);
    if (so) ctx.fillRect(x + (w ? b * 0.5 : 0), y + s - b, s - (w ? b * 0.5 : 0) - (e ? b * 0.5 : 0), b * 0.5);
    if (w) ctx.fillRect(x + b * 0.5, y + (n ? b * 0.5 : 0), b * 0.5, s - (n ? b * 0.5 : 0) - (so ? b * 0.5 : 0));
    if (e) ctx.fillRect(x + s - b, y + (n ? b * 0.5 : 0), b * 0.5, s - (n ? b * 0.5 : 0) - (so ? b * 0.5 : 0));
    if (th.altStyle === 'rug' && (tx + ty) % 2 === 0) { ctx.fillStyle = 'rgba(255,230,160,.35)'; circle(ctx, x + s / 2, y + s / 2, s * 0.09, ctx.fillStyle); }
    if (th.altStyle === 'gold') { ctx.strokeStyle = 'rgba(120,40,20,.25)'; ctx.lineWidth = Math.max(1, s * 0.03); ctx.beginPath(); ctx.arc(x + s / 2, y + s / 2, s * 0.22, 0, TAU); ctx.stroke(); }
  }

  /* ---------------------------------------------------------------- solid blocks */
  function drawWall(ctx, th, tiles, tx, ty, x, y, s) {
    var below = tileAt(tiles, tx, ty + 1) === '#';
    var face = below ? 0 : s * 0.32;
    ctx.fillStyle = th.wallTop; ctx.fillRect(x, y, s, s - face);
    if (face) {
      ctx.fillStyle = th.wallFace; ctx.fillRect(x, y + s - face, s, face);
      ctx.fillStyle = 'rgba(0,0,0,.18)'; ctx.fillRect(x, y + s - face, s, Math.max(1, s * 0.04));
    }
    ctx.strokeStyle = th.wallLine; ctx.lineWidth = Math.max(1, s * 0.04);
    ctx.beginPath();
    if (tileAt(tiles, tx, ty - 1) !== '#') { ctx.moveTo(x, y + 0.5); ctx.lineTo(x + s, y + 0.5); }
    if (tileAt(tiles, tx - 1, ty) !== '#') { ctx.moveTo(x + 0.5, y); ctx.lineTo(x + 0.5, y + s); }
    if (tileAt(tiles, tx + 1, ty) !== '#') { ctx.moveTo(x + s - 0.5, y); ctx.lineTo(x + s - 0.5, y + s); }
    ctx.stroke();
    // brick / panel texture on the top face
    ctx.strokeStyle = 'rgba(255,255,255,.08)'; ctx.lineWidth = Math.max(1, s * 0.025);
    ctx.beginPath(); ctx.moveTo(x, y + (s - face) / 2); ctx.lineTo(x + s, y + (s - face) / 2);
    var o = (ty % 2) ? s / 2 : 0; ctx.moveTo(x + o + s / 4, y); ctx.lineTo(x + o + s / 4, y + (s - face) / 2); ctx.stroke();
  }

  function drawCounter(ctx, th, tiles, tx, ty, x, y, s, time) {
    var below = tileAt(tiles, tx, ty + 1) === 'T';
    var face = below ? 0 : s * 0.3;
    ctx.fillStyle = th.ctrFace; ctx.fillRect(x, y + s - face - 1, s, face + 1);
    ctx.fillStyle = th.ctrTop; ctx.fillRect(x, y, s, s - face);
    ctx.strokeStyle = INK; ctx.lineWidth = Math.max(1, s * 0.05); ctx.globalAlpha = 0.5;
    ctx.beginPath();
    if (tileAt(tiles, tx, ty - 1) !== 'T') { ctx.moveTo(x, y + 1); ctx.lineTo(x + s, y + 1); }
    if (tileAt(tiles, tx - 1, ty) !== 'T') { ctx.moveTo(x + 1, y); ctx.lineTo(x + 1, y + s); }
    if (tileAt(tiles, tx + 1, ty) !== 'T') { ctx.moveTo(x + s - 1, y); ctx.lineTo(x + s - 1, y + s); }
    if (face) { ctx.moveTo(x, y + s - face); ctx.lineTo(x + s, y + s - face); }
    ctx.stroke(); ctx.globalAlpha = 1;
    var h = hash(tx, ty), cx = x + s / 2, cy = y + (s - face) / 2;
    if (th.ctrStyle === 'awning') {
      for (var i = 0; i < 4; i++) { ctx.fillStyle = i % 2 ? '#f6efe2' : '#c0392b'; ctx.fillRect(x + i * s / 4, y, s / 4, (s - face) * 0.55); }
    }
    if (h < 0.45) return;
    if (th.ctrStyle === 'plates' || th.ctrStyle === 'feast') {
      circle(ctx, cx, cy, s * 0.22, '#fff', 'rgba(0,0,0,.2)', 1); circle(ctx, cx, cy, s * 0.14, h > 0.75 ? '#e8b13b' : '#d9574a');
    } else if (th.ctrStyle === 'teacups') {
      circle(ctx, cx - s * 0.12, cy, s * 0.12, '#fff', '#2e9c8f', 2); circle(ctx, cx + s * 0.16, cy + s * 0.04, s * 0.1, '#fff', '#2e9c8f', 2);
    } else if (th.ctrStyle === 'spices') {
      var c = ['#d8402e', '#e8b13b', '#7a3519'];
      for (var j = 0; j < 3; j++) circle(ctx, x + s * (0.25 + j * 0.25), cy, s * 0.1, c[j], INK, 1);
    } else if (th.ctrStyle === 'nets') {
      ctx.strokeStyle = 'rgba(255,255,255,.45)'; ctx.lineWidth = 1; ctx.beginPath();
      for (var k = 0; k < 4; k++) { ctx.moveTo(x + k * s / 3, y); ctx.lineTo(x + k * s / 3 - s * 0.2, y + s - face); }
      ctx.stroke();
    } else if (th.ctrStyle === 'awning' && h > 0.7) {
      circle(ctx, cx, cy + s * 0.15, s * 0.1, '#f2d27a', INK, 1);
    }
  }

  function drawDecor(ctx, th, tiles, tx, ty, x, y, s, time) {
    var cx = x + s / 2, cy = y + s / 2, h = hash(tx, ty);
    shadow(ctx, cx, y + s * 0.85, s * 0.36, s * 0.12);
    switch (th.decor) {
      case 'lantern':
        ctx.fillStyle = '#2a2236'; ctx.fillRect(cx - s * 0.04, y + s * 0.15, s * 0.08, s * 0.72);
        ellipse(ctx, cx, y + s * 0.32, s * 0.26, s * 0.22, '#e0483a', INK, Math.max(1, s * 0.04));
        ctx.fillStyle = '#f4b63c'; ctx.fillRect(cx - s * 0.12, y + s * 0.1, s * 0.24, s * 0.05); ctx.fillRect(cx - s * 0.12, y + s * 0.52, s * 0.24, s * 0.05);
        ctx.strokeStyle = 'rgba(255,220,150,.6)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(cx, y + s * 0.12); ctx.lineTo(cx, y + s * 0.52); ctx.stroke();
        break;
      case 'steamers':
        for (var i = 0; i < 3; i++) {
          var yy = y + s * (0.68 - i * 0.2);
          ellipse(ctx, cx, yy, s * 0.36, s * 0.16, '#d9b26f', INK, Math.max(1, s * 0.035));
          ctx.fillStyle = '#c49a55'; ctx.fillRect(cx - s * 0.36, yy, s * 0.72, s * 0.08);
        }
        ellipse(ctx, cx, y + s * 0.26, s * 0.3, s * 0.12, '#e4c17f', INK, Math.max(1, s * 0.035));
        break;
      case 'chili':
        circle(ctx, cx, cy, s * 0.36, '#4d7f2f', INK, Math.max(1, s * 0.04));
        circle(ctx, cx - s * 0.1, cy - s * 0.1, s * 0.2, '#5e9c4a');
        for (var j = 0; j < 4; j++) { var a = j * 1.7 + h * 6; ellipse(ctx, cx + Math.cos(a) * s * 0.2, cy + Math.sin(a) * s * 0.18, s * 0.06, s * 0.11, '#d8402e', null, 0, a); }
        break;
      case 'barrel':
        ellipse(ctx, cx, cy + s * 0.05, s * 0.34, s * 0.38, '#9a6a3c', INK, Math.max(1, s * 0.04));
        ctx.strokeStyle = '#5d6b76'; ctx.lineWidth = Math.max(1, s * 0.06);
        ctx.beginPath(); ctx.moveTo(cx - s * 0.33, cy - s * 0.1); ctx.lineTo(cx + s * 0.33, cy - s * 0.1); ctx.moveTo(cx - s * 0.33, cy + s * 0.2); ctx.lineTo(cx + s * 0.33, cy + s * 0.2); ctx.stroke();
        ellipse(ctx, cx, cy - s * 0.3, s * 0.26, s * 0.09, '#b98a55', INK, 1);
        break;
      case 'vase':
        ctx.beginPath(); ctx.moveTo(cx - s * 0.12, y + s * 0.2); ctx.quadraticCurveTo(cx - s * 0.4, cy + s * 0.1, cx - s * 0.16, y + s * 0.85);
        ctx.lineTo(cx + s * 0.16, y + s * 0.85); ctx.quadraticCurveTo(cx + s * 0.4, cy + s * 0.1, cx + s * 0.12, y + s * 0.2); ctx.closePath();
        ctx.fillStyle = '#f4e3c0'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = Math.max(1, s * 0.04); ctx.stroke();
        ctx.strokeStyle = '#2e6fb0'; ctx.lineWidth = Math.max(1, s * 0.05); ctx.beginPath(); ctx.moveTo(cx - s * 0.22, cy + s * 0.05); ctx.lineTo(cx + s * 0.22, cy + s * 0.05); ctx.stroke();
        circle(ctx, cx - s * 0.1, y + s * 0.14, s * 0.08, '#e0483a'); circle(ctx, cx + s * 0.1, y + s * 0.12, s * 0.08, '#f4b63c'); circle(ctx, cx, y + s * 0.06, s * 0.07, '#ff8fb1');
        break;
      case 'bread': // a basket of buns and a baguette
        ellipse(ctx, cx, y + s * 0.66, s * 0.38, s * 0.2, '#b07a3c', INK, Math.max(1, s * 0.04));
        circle(ctx, cx - s * 0.15, y + s * 0.5, s * 0.16, '#e9b36a', INK, Math.max(1, s * 0.035));
        circle(ctx, cx + s * 0.15, y + s * 0.5, s * 0.16, '#f0c27c', INK, Math.max(1, s * 0.035));
        ellipse(ctx, cx, y + s * 0.3, s * 0.1, s * 0.3, '#d99a4e', INK, Math.max(1, s * 0.035), 0.5);
        break;
      case 'bush': // a round bush (tea bush, reeds, orchard tree) with a few fruit or buds
        circle(ctx, cx, cy, s * 0.38, '#4f8a3a', INK, Math.max(1, s * 0.04));
        circle(ctx, cx - s * 0.12, cy - s * 0.12, s * 0.2, '#62a34a');
        circle(ctx, cx + s * 0.13, cy - s * 0.05, s * 0.16, '#6fb556');
        for (var bj = 0; bj < 3; bj++) circle(ctx, cx + Math.cos(bj * 2.1 + h * 6) * s * 0.22, cy + Math.sin(bj * 2.1 + h * 6) * s * 0.18, s * 0.055, th.altB || '#ff8f6b', INK, 1);
        break;
      case 'snowman':
        circle(ctx, cx, y + s * 0.62, s * 0.26, '#ffffff', INK, Math.max(1, s * 0.04));
        circle(ctx, cx, y + s * 0.3, s * 0.18, '#ffffff', INK, Math.max(1, s * 0.04));
        circle(ctx, cx - s * 0.06, y + s * 0.27, s * 0.025, INK); circle(ctx, cx + s * 0.06, y + s * 0.27, s * 0.025, INK);
        ctx.beginPath(); ctx.moveTo(cx, y + s * 0.32); ctx.lineTo(cx + s * 0.14, y + s * 0.34); ctx.lineTo(cx, y + s * 0.36); ctx.fillStyle = '#f08a2a'; ctx.fill();
        ctx.fillStyle = '#d63031'; ctx.fillRect(cx - s * 0.16, y + s * 0.42, s * 0.32, s * 0.06);
        break;
      default: // herb pot
        ctx.beginPath(); ctx.moveTo(cx - s * 0.26, cy + s * 0.05); ctx.lineTo(cx + s * 0.26, cy + s * 0.05); ctx.lineTo(cx + s * 0.18, y + s * 0.85); ctx.lineTo(cx - s * 0.18, y + s * 0.85); ctx.closePath();
        ctx.fillStyle = '#c0643c'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = Math.max(1, s * 0.04); ctx.stroke();
        circle(ctx, cx - s * 0.13, cy - s * 0.08, s * 0.17, '#5e9c4a', INK, Math.max(1, s * 0.03));
        circle(ctx, cx + s * 0.13, cy - s * 0.1, s * 0.17, '#6aad55', INK, Math.max(1, s * 0.03));
        circle(ctx, cx, cy - s * 0.24, s * 0.17, '#78bb5f', INK, Math.max(1, s * 0.03));
    }
  }

  Art.drawCrate = function (ctx, x, y, s, crack) {
    var p = s * 0.06;
    shadow(ctx, x + s / 2, y + s * 0.9, s * 0.42, s * 0.1);
    rr(ctx, x + p, y + p, s - 2 * p, s - 2 * p, s * 0.08);
    ctx.fillStyle = '#c98f52'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = Math.max(1, s * 0.05); ctx.stroke();
    ctx.strokeStyle = '#8a5a2b'; ctx.lineWidth = Math.max(1, s * 0.07);
    ctx.beginPath(); ctx.moveTo(x + p * 2.2, y + p * 2.2); ctx.lineTo(x + s - p * 2.2, y + s - p * 2.2); ctx.moveTo(x + s - p * 2.2, y + p * 2.2); ctx.lineTo(x + p * 2.2, y + s - p * 2.2); ctx.stroke();
    ctx.strokeStyle = 'rgba(255,240,200,.35)'; ctx.lineWidth = Math.max(1, s * 0.03); ctx.strokeRect(x + p * 1.6, y + p * 1.6, s - p * 3.2, s - p * 3.2);
    if (crack) { ctx.strokeStyle = INK; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x + s * 0.3, y + s * 0.2); ctx.lineTo(x + s * 0.45, y + s * 0.45); ctx.lineTo(x + s * 0.35, y + s * 0.7); ctx.stroke(); }
  };

  /* ---------------------------------------------------------------- animated ground */
  Art.drawWater = function (ctx, th, tiles, tx, ty, x, y, s, t) {
    ctx.fillStyle = th.water; ctx.fillRect(x, y, s, s);
    ctx.fillStyle = th.waterDeep; ctx.globalAlpha = 0.35; ctx.fillRect(x, y + s * 0.5, s, s * 0.5); ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(255,255,255,.45)'; ctx.lineWidth = Math.max(1, s * 0.04);
    var ph = t * 2 + tx * 0.9 + ty * 0.6;
    ctx.beginPath();
    for (var i = 0; i < 2; i++) {
      var yy = y + s * (0.3 + i * 0.4) + Math.sin(ph + i) * s * 0.05, xx = x + s * (0.15 + 0.3 * ((tx + i) % 2));
      ctx.moveTo(xx, yy); ctx.quadraticCurveTo(xx + s * 0.12, yy - s * 0.08, xx + s * 0.24, yy);
    }
    ctx.stroke();
    if (tileAt(tiles, tx, ty - 1) !== '~' && tileAt(tiles, tx, ty - 1) !== 'H') { ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.fillRect(x, y, s, s * (0.08 + 0.03 * Math.sin(ph))); }
  };
  Art.drawStove = function (ctx, x, y, s, t, safe, off, warn) {
    rr(ctx, x + s * 0.04, y + s * 0.04, s * 0.92, s * 0.92, s * 0.12); ctx.fillStyle = '#3a3438'; ctx.fill();
    ctx.strokeStyle = INK; ctx.lineWidth = Math.max(1, s * 0.04); ctx.stroke();
    if (off && !(warn && Math.sin(t * 18) > 0)) {
      // Switched off: cold grey burners.
      ctx.strokeStyle = 'rgba(160,170,185,.55)'; ctx.lineWidth = Math.max(1.5, s * 0.06);
      ctx.beginPath(); ctx.arc(x + s / 2, y + s / 2, s * 0.3, 0, TAU); ctx.stroke();
      ctx.beginPath(); ctx.arc(x + s / 2, y + s / 2, s * 0.15, 0, TAU); ctx.stroke();
      return;
    }
    var g = 0.55 + 0.45 * Math.sin(t * 5 + x * 0.05);
    ctx.strokeStyle = safe ? 'rgba(120,180,255,.6)' : 'rgba(255,' + Math.round(90 + 60 * g) + ',40,' + (0.55 + 0.4 * g) + ')';
    ctx.lineWidth = Math.max(1.5, s * 0.07);
    ctx.beginPath(); ctx.arc(x + s / 2, y + s / 2, s * 0.3, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.arc(x + s / 2, y + s / 2, s * 0.15, 0, TAU); ctx.stroke();
    if (!safe) { ctx.fillStyle = 'rgba(255,120,40,' + (0.12 * g) + ')'; ctx.fillRect(x, y, s, s); }
  };
  Art.drawConveyor = function (ctx, x, y, s, dir, t) {
    ctx.fillStyle = '#5a5560'; ctx.fillRect(x, y, s, s);
    ctx.fillStyle = '#48434e'; if (dir === 'R' || dir === 'L') { ctx.fillRect(x, y, s, s * 0.12); ctx.fillRect(x, y + s * 0.88, s, s * 0.12); } else { ctx.fillRect(x, y, s * 0.12, s); ctx.fillRect(x + s * 0.88, y, s * 0.12, s); }
    ctx.save(); ctx.beginPath(); ctx.rect(x, y, s, s); ctx.clip();
    ctx.strokeStyle = '#f4b63c'; ctx.lineWidth = Math.max(1.5, s * 0.08); ctx.lineCap = 'round';
    var off = (t * 1.6 % 1) * s / 2;
    for (var i = -1; i < 3; i++) {
      var d = i * s / 2 + off;
      ctx.beginPath();
      if (dir === 'R') { ctx.moveTo(x + d - s * 0.1, y + s * 0.3); ctx.lineTo(x + d + s * 0.08, y + s / 2); ctx.lineTo(x + d - s * 0.1, y + s * 0.7); }
      if (dir === 'L') { ctx.moveTo(x + s - d + s * 0.1, y + s * 0.3); ctx.lineTo(x + s - d - s * 0.08, y + s / 2); ctx.lineTo(x + s - d + s * 0.1, y + s * 0.7); }
      if (dir === 'D') { ctx.moveTo(x + s * 0.3, y + d - s * 0.1); ctx.lineTo(x + s / 2, y + d + s * 0.08); ctx.lineTo(x + s * 0.7, y + d - s * 0.1); }
      if (dir === 'U') { ctx.moveTo(x + s * 0.3, y + s - d + s * 0.1); ctx.lineTo(x + s / 2, y + s - d - s * 0.08); ctx.lineTo(x + s * 0.7, y + s - d + s * 0.1); }
      ctx.stroke();
    }
    ctx.restore();
  };

  // A liquid that joins up with its neighbours: square edges toward the same liquid, round ones elsewhere.
  function puddle(ctx, tiles, tx, ty, x, y, s, ch, color) {
    var n = tileAt(tiles, tx, ty - 1) === ch, so = tileAt(tiles, tx, ty + 1) === ch, w = tileAt(tiles, tx - 1, ty) === ch, e = tileAt(tiles, tx + 1, ty) === ch;
    var m = s * 0.08, r = s * 0.38;
    var x0 = x + (w ? 0 : m), y0 = y + (n ? 0 : m), x1 = x + s - (e ? 0 : m), y1 = y + s - (so ? 0 : m);
    var rtl = (!n && !w) ? r : 0, rtr = (!n && !e) ? r : 0, rbr = (!so && !e) ? r : 0, rbl = (!so && !w) ? r : 0;
    ctx.beginPath();
    ctx.moveTo(x0 + rtl, y0); ctx.lineTo(x1 - rtr, y0); if (rtr) ctx.arcTo(x1, y0, x1, y0 + rtr, rtr);
    ctx.lineTo(x1, y1 - rbr); if (rbr) ctx.arcTo(x1, y1, x1 - rbr, y1, rbr);
    ctx.lineTo(x0 + rbl, y1); if (rbl) ctx.arcTo(x0, y1, x0, y1 - rbl, rbl);
    ctx.lineTo(x0, y0 + rtl); if (rtl) ctx.arcTo(x0, y0, x0 + rtl, y0, rtl);
    ctx.closePath(); ctx.fillStyle = color; ctx.fill();
  }

  /* Draw one tile. Animated tiles (water, stove, conveyor) are drawn by drawAnimated each frame;
     here they get a plain base so the cached static layer looks right. */
  Art.ANIMATED = { '~': 1, '^': 1, 'R': 1, 'L': 1, 'U': 1, 'D': 1 };
  Art.drawTile = function (ctx, th, tiles, tx, ty, x, y, s, t) {
    var ch = tiles[ty][tx];
    if (ch === '#') return drawWall(ctx, th, tiles, tx, ty, x, y, s);
    if (ch === ',') return drawAlt(ctx, th, tiles, tx, ty, x, y, s);
    if (ch === '~') return Art.drawWater(ctx, th, tiles, tx, ty, x, y, s, t || 0);
    drawFloor(ctx, th, tiles, tx, ty, x, y, s);
    if (ch === 'T') return drawCounter(ctx, th, tiles, tx, ty, x, y, s, t);
    if (ch === 'P') return drawDecor(ctx, th, tiles, tx, ty, x, y, s, t);
    if (ch === 'H') {
      ctx.fillStyle = th.water; ctx.fillRect(x, y, s, s);
      ctx.fillStyle = '#a8784a'; ctx.strokeStyle = '#5a3a20'; ctx.lineWidth = Math.max(1, s * 0.03);
      var vertical = (tileAt(tiles, tx, ty - 1) === 'H' || tileAt(tiles, tx, ty + 1) === 'H') && !(tileAt(tiles, tx - 1, ty) === 'H' || tileAt(tiles, tx + 1, ty) === 'H');
      for (var i = 0; i < 4; i++) {
        if (vertical) { ctx.fillRect(x + s * 0.08, y + i * s / 4 + 1, s * 0.84, s / 4 - 2); ctx.strokeRect(x + s * 0.08, y + i * s / 4 + 1, s * 0.84, s / 4 - 2); }
        else { ctx.fillRect(x + i * s / 4 + 1, y + s * 0.08, s / 4 - 2, s * 0.84); ctx.strokeRect(x + i * s / 4 + 1, y + s * 0.08, s / 4 - 2, s * 0.84); }
      }
      return;
    }
    if (ch === '^') return Art.drawStove(ctx, x, y, s, t || 0);
    if (ch === '=') {
      puddle(ctx, tiles, tx, ty, x, y, s, '=', th.slick || 'rgba(244,190,60,.6)');
      if (hash(tx, ty) > 0.4) { ctx.fillStyle = 'rgba(255,255,255,.6)'; ellipse(ctx, x + s * (0.25 + 0.4 * hash(ty, tx)), y + s * 0.4, s * 0.13, s * 0.05, ctx.fillStyle, null, 0, -0.4); }
      return;
    }
    if (ch === '%') {
      puddle(ctx, tiles, tx, ty, x, y, s, '%', 'rgba(110,50,20,.8)');
      var hb = hash(tx, ty);
      circle(ctx, x + s * (0.2 + 0.5 * hb), y + s * (0.3 + 0.3 * hash(ty, tx)), s * 0.07, 'rgba(165,85,45,.95)');
      if (hb > 0.5) circle(ctx, x + s * 0.7, y + s * 0.7, s * 0.045, 'rgba(165,85,45,.95)');
      return;
    }
    if (ch === 'R' || ch === 'L' || ch === 'U' || ch === 'D') return Art.drawConveyor(ctx, x, y, s, ch, t || 0);
    if (ch === 'X') return Art.drawCrate(ctx, x, y, s);
  };
  Art.drawAnimated = function (ctx, th, tiles, tx, ty, x, y, s, t, opts) {
    var ch = tiles[ty][tx];
    if (ch === '~') Art.drawWater(ctx, th, tiles, tx, ty, x, y, s, t);
    else if (ch === '^') Art.drawStove(ctx, x, y, s, t, opts && opts.fireproof, opts && opts.off, opts && opts.warn);
    else if (ch === 'R' || ch === 'L' || ch === 'U' || ch === 'D') Art.drawConveyor(ctx, x, y, s, ch, t);
  };

  /* ================================================================ the bun */
  Art.drawBun = function (ctx, x, y, r, o) {
    o = o || {};
    var t = o.t || 0, sx = o.sx || 1, sy = o.sy || 1;
    if (!o.noShadow) shadow(ctx, x, y + r * 0.82, r * 0.92 * sx, r * 0.28, 0.22);
    ctx.save();
    ctx.translate(x, y + r * 0.5);
    ctx.scale(sx, sy);
    ctx.translate(0, -r * 0.5);
    var w = r * 1.02, h = r * 0.95;
    // body
    ctx.beginPath();
    ctx.moveTo(-w, h * 0.5);
    ctx.bezierCurveTo(-w * 1.12, -h * 0.45, -w * 0.55, -h * 1.02, 0, -h * 1.0);
    ctx.bezierCurveTo(w * 0.55, -h * 1.02, w * 1.12, -h * 0.45, w, h * 0.5);
    ctx.quadraticCurveTo(0, h * 0.86, -w, h * 0.5);
    ctx.closePath();
    var g = ctx.createRadialGradient(-r * 0.35, -r * 0.45, r * 0.1, 0, 0, r * 1.25);
    g.addColorStop(0, '#ffffff'); g.addColorStop(0.55, o.tint || '#fbf1e1'); g.addColorStop(1, '#e9d0ab');
    ctx.fillStyle = g; ctx.fill();
    // filling showing through the dough
    if (o.fill > 0) {
      ctx.save(); ctx.clip();
      var f = Math.min(1, o.fill);
      var fg = ctx.createRadialGradient(0, r * 0.25, 0, 0, r * 0.25, r * (0.5 + 0.5 * f));
      fg.addColorStop(0, 'rgba(200,90,55,' + (0.32 * f) + ')'); fg.addColorStop(1, 'rgba(200,90,55,0)');
      ctx.fillStyle = fg; ctx.fillRect(-r * 1.2, -r, r * 2.4, r * 2);
      ctx.restore();
    }
    ctx.lineWidth = Math.max(1.5, r * 0.085); ctx.strokeStyle = INK; ctx.lineJoin = 'round'; ctx.stroke();
    // pleats on top
    ctx.strokeStyle = 'rgba(170,120,75,.75)'; ctx.lineWidth = Math.max(1, r * 0.055); ctx.lineCap = 'round';
    var top = -h * 0.93;
    for (var i = -2; i <= 2; i++) {
      ctx.beginPath(); ctx.moveTo(i * r * 0.05, top + r * 0.04);
      ctx.quadraticCurveTo(i * r * 0.2, top + r * 0.12, i * r * 0.3 + (i ? 0 : r * 0.04), top + r * (0.28 - Math.abs(i) * 0.04)); ctx.stroke();
    }
    circle(ctx, 0, top + r * 0.02, r * 0.07, '#f3e2c8', INK, Math.max(1, r * 0.04));
    // face
    var fx = (o.lookX || 0) * r * 0.16, fy = (o.lookY || 0) * r * 0.1 + r * 0.08;
    if (!o.back) {
      ellipse(ctx, fx - r * 0.56, fy + r * 0.22, r * 0.17, r * 0.1, 'rgba(255,130,140,.55)');
      ellipse(ctx, fx + r * 0.56, fy + r * 0.22, r * 0.17, r * 0.1, 'rgba(255,130,140,.55)');
      ctx.strokeStyle = INK; ctx.fillStyle = INK; ctx.lineWidth = Math.max(1.5, r * 0.08); ctx.lineCap = 'round';
      var face = o.face || 'happy';
      var blink = o.blink || (Math.sin(t * 1.3) > 0.985);
      [-1, 1].forEach(function (s) {
        var ex = fx + s * r * 0.32, ey = fy - r * 0.05;
        ctx.beginPath();
        if (face === 'ouch') { ctx.moveTo(ex - r * 0.1, ey - r * 0.1); ctx.lineTo(ex + r * 0.1, ey + r * 0.1); ctx.moveTo(ex + r * 0.1, ey - r * 0.1); ctx.lineTo(ex - r * 0.1, ey + r * 0.1); ctx.stroke(); }
        else if (face === 'dash') { ctx.moveTo(ex - s * r * 0.1, ey - r * 0.09); ctx.lineTo(ex + s * r * 0.06, ey); ctx.lineTo(ex - s * r * 0.1, ey + r * 0.09); ctx.stroke(); }
        else if (face === 'joy' || blink) { ctx.arc(ex, ey + r * 0.04, r * 0.09, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke(); }
        else { ellipse(ctx, ex, ey, r * 0.085, r * 0.12, INK); circle(ctx, ex + r * 0.03, ey - r * 0.045, r * 0.035, '#fff'); }
      });
      ctx.beginPath(); ctx.lineWidth = Math.max(1.2, r * 0.06);
      if (face === 'ouch') { ellipse(ctx, fx, fy + r * 0.24, r * 0.08, r * 0.06, INK); }
      else if (face === 'dash') { ctx.moveTo(fx - r * 0.1, fy + r * 0.22); ctx.lineTo(fx + r * 0.1, fy + r * 0.22); ctx.stroke(); }
      else if (face === 'joy') { ctx.beginPath(); ctx.arc(fx, fy + r * 0.16, r * 0.13, 0.1, Math.PI - 0.1); ctx.closePath(); ctx.fillStyle = '#b8352a'; ctx.fill(); ctx.stroke(); }
      else { ctx.moveTo(fx - r * 0.12, fy + r * 0.18); ctx.quadraticCurveTo(fx - r * 0.06, fy + r * 0.27, fx, fy + r * 0.19); ctx.quadraticCurveTo(fx + r * 0.06, fy + r * 0.27, fx + r * 0.12, fy + r * 0.18); ctx.stroke(); }
    }
    if (o.hat && o.hat !== 'none') Art.drawHat(ctx, o.hat, 0, top + r * 0.05, r, t, o.back);
    ctx.restore();
  };

  /* ---------------------------------------------------------------- hats (anchored at the top of the head) */
  Art.drawHat = function (ctx, hat, x, y, r, t, back) {
    var lw = Math.max(1.2, r * 0.07);
    ctx.save(); ctx.translate(x, y); ctx.lineWidth = lw; ctx.strokeStyle = INK; ctx.lineJoin = 'round';
    switch (hat) {
      case 'party':
        ctx.save(); ctx.rotate(0.18);
        ctx.beginPath(); ctx.moveTo(-r * 0.36, r * 0.12); ctx.lineTo(0, -r * 0.95); ctx.lineTo(r * 0.36, r * 0.12); ctx.closePath();
        ctx.fillStyle = '#ff7eb6'; ctx.fill();
        ctx.save(); ctx.clip(); ctx.fillStyle = '#7ec8ff';
        for (var i = 0; i < 4; i++) { ctx.beginPath(); ctx.moveTo(-r, -r * 0.1 - i * r * 0.28); ctx.lineTo(r, -r * 0.3 - i * r * 0.28); ctx.lineTo(r, -r * 0.18 - i * r * 0.28); ctx.lineTo(-r, r * 0.02 - i * r * 0.28); ctx.fill(); }
        ctx.restore();
        ctx.beginPath(); ctx.moveTo(-r * 0.36, r * 0.12); ctx.lineTo(0, -r * 0.95); ctx.lineTo(r * 0.36, r * 0.12); ctx.closePath(); ctx.stroke();
        circle(ctx, 0, -r * 0.98, r * 0.13, '#f4b63c', INK, lw * 0.8);
        ctx.restore();
        break;
      case 'toque':
        rr(ctx, -r * 0.42, -r * 0.2, r * 0.84, r * 0.3, r * 0.06); ctx.fillStyle = '#fff'; ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.arc(-r * 0.3, -r * 0.42, r * 0.28, Math.PI * 0.7, Math.PI * 1.75); ctx.arc(0, -r * 0.62, r * 0.32, Math.PI * 1.1, Math.PI * 1.9);
        ctx.arc(r * 0.3, -r * 0.42, r * 0.28, Math.PI * 1.25, Math.PI * 0.3); ctx.lineTo(r * 0.38, -r * 0.2); ctx.lineTo(-r * 0.38, -r * 0.2); ctx.closePath();
        ctx.fillStyle = '#fff'; ctx.fill(); ctx.stroke();
        ctx.strokeStyle = 'rgba(0,0,0,.15)'; ctx.beginPath(); ctx.moveTo(-r * 0.12, -r * 0.25); ctx.lineTo(-r * 0.15, -r * 0.55); ctx.moveTo(r * 0.12, -r * 0.25); ctx.lineTo(r * 0.15, -r * 0.55); ctx.stroke();
        break;
      case 'beanie':
        ctx.beginPath(); ctx.arc(0, r * 0.12, r * 0.62, Math.PI, 0); ctx.closePath(); ctx.fillStyle = '#e0483a'; ctx.fill(); ctx.stroke();
        rr(ctx, -r * 0.66, r * 0.02, r * 1.32, r * 0.22, r * 0.1); ctx.fillStyle = '#c0392b'; ctx.fill(); ctx.stroke();
        ctx.strokeStyle = 'rgba(0,0,0,.2)'; ctx.beginPath(); for (var b = -5; b <= 5; b++) { ctx.moveTo(b * r * 0.11, r * 0.05); ctx.lineTo(b * r * 0.11, r * 0.21); } ctx.stroke();
        circle(ctx, 0, -r * 0.52, r * 0.16, '#fff7ea', INK, lw * 0.8);
        break;
      case 'bamboo':
        ctx.beginPath(); ctx.moveTo(-r * 1.15, r * 0.12); ctx.lineTo(0, -r * 0.55); ctx.lineTo(r * 1.15, r * 0.12); ctx.quadraticCurveTo(0, r * 0.3, -r * 1.15, r * 0.12); ctx.closePath();
        ctx.fillStyle = '#e8c477'; ctx.fill(); ctx.stroke();
        ctx.strokeStyle = 'rgba(120,80,20,.45)'; ctx.lineWidth = lw * 0.6; ctx.beginPath();
        for (var k = -3; k <= 3; k++) { ctx.moveTo(0, -r * 0.5); ctx.lineTo(k * r * 0.34, r * 0.16); } ctx.stroke();
        break;
      case 'flowers':
        var cols = ['#ff7eb6', '#f4b63c', '#ffffff', '#7ec8ff', '#ff9f43'];
        ctx.strokeStyle = '#5e9c4a'; ctx.lineWidth = lw; ctx.beginPath(); ctx.ellipse(0, r * 0.05, r * 0.7, r * 0.2, 0, Math.PI, TAU); ctx.stroke();
        for (var f = 0; f < 5; f++) {
          var a = Math.PI + (f + 0.5) * Math.PI / 5, fx = Math.cos(a) * r * 0.7, fy = Math.sin(a) * r * 0.2 + r * 0.05;
          for (var pp = 0; pp < 5; pp++) circle(ctx, fx + Math.cos(pp * 1.257) * r * 0.1, fy + Math.sin(pp * 1.257) * r * 0.1, r * 0.08, cols[f]);
          circle(ctx, fx, fy, r * 0.06, '#f4b63c');
        }
        break;
      case 'bandana':
        ctx.beginPath(); ctx.moveTo(-r * 0.86, r * 0.3); ctx.quadraticCurveTo(-r * 0.8, -r * 0.45, 0, -r * 0.42); ctx.quadraticCurveTo(r * 0.8, -r * 0.45, r * 0.86, r * 0.3);
        ctx.quadraticCurveTo(0, r * 0.05, -r * 0.86, r * 0.3); ctx.closePath(); ctx.fillStyle = '#d63031'; ctx.fill(); ctx.stroke();
        [[-0.4, -0.1], [0.1, -0.22], [0.45, 0.02], [-0.1, 0.05]].forEach(function (d) { circle(ctx, d[0] * r, d[1] * r, r * 0.06, '#fff'); });
        ctx.beginPath(); ctx.moveTo(r * 0.82, r * 0.18); ctx.lineTo(r * 1.15, r * 0.05); ctx.lineTo(r * 1.08, r * 0.35); ctx.closePath(); ctx.fillStyle = '#d63031'; ctx.fill(); ctx.stroke();
        break;
      case 'headphones':
        ctx.beginPath(); ctx.arc(0, r * 0.55, r * 0.98, Math.PI * 1.08, Math.PI * 1.92); ctx.lineWidth = r * 0.16; ctx.strokeStyle = INK; ctx.stroke();
        ctx.lineWidth = r * 0.09; ctx.strokeStyle = '#3d8fd1'; ctx.stroke();
        ctx.lineWidth = lw;
        [-1, 1].forEach(function (s) { rr(ctx, s * r * 0.98 - r * 0.17, r * 0.35, r * 0.34, r * 0.46, r * 0.14); ctx.fillStyle = '#3d8fd1'; ctx.fill(); ctx.strokeStyle = INK; ctx.stroke(); });
        break;
      case 'wizard':
        ellipse(ctx, 0, r * 0.08, r * 0.95, r * 0.22, '#5b3f9c', INK, lw);
        ctx.beginPath(); ctx.moveTo(-r * 0.5, r * 0.05); ctx.quadraticCurveTo(-r * 0.1, -r * 0.6, r * 0.25, -r * 1.25); ctx.quadraticCurveTo(r * 0.2, -r * 0.5, r * 0.5, r * 0.05); ctx.closePath();
        ctx.fillStyle = '#6c4fb3'; ctx.fill(); ctx.stroke();
        ctx.fillStyle = '#f4b63c'; [[0.02, -0.35, 0.09], [0.2, -0.75, 0.06], [-0.2, -0.05, 0.06]].forEach(function (s2) { star(ctx, s2[0] * r, s2[1] * r, s2[2] * r * 1.4); });
        break;
      case 'crown':
        ctx.beginPath(); ctx.moveTo(-r * 0.55, r * 0.15); ctx.lineTo(-r * 0.62, -r * 0.45); ctx.lineTo(-r * 0.3, -r * 0.15); ctx.lineTo(0, -r * 0.6); ctx.lineTo(r * 0.3, -r * 0.15); ctx.lineTo(r * 0.62, -r * 0.45); ctx.lineTo(r * 0.55, r * 0.15); ctx.closePath();
        var cg = ctx.createLinearGradient(0, -r * 0.6, 0, r * 0.15); cg.addColorStop(0, '#ffe08a'); cg.addColorStop(1, '#d99417');
        ctx.fillStyle = cg; ctx.fill(); ctx.stroke();
        circle(ctx, 0, -r * 0.05, r * 0.09, '#e0483a', INK, lw * 0.6); circle(ctx, -r * 0.33, r * 0.0, r * 0.06, '#3d8fd1'); circle(ctx, r * 0.33, r * 0.0, r * 0.06, '#5e9c4a');
        [-0.62, 0, 0.62].forEach(function (px, i) { circle(ctx, px * r, (i === 1 ? -0.62 : -0.47) * r, r * 0.06, '#fff7ea', INK, lw * 0.5); });
        break;
    }
    ctx.restore();
  };
  function star(ctx, x, y, r) {
    ctx.beginPath();
    for (var i = 0; i < 10; i++) { var a = -Math.PI / 2 + i * Math.PI / 5, rad = i % 2 ? r * 0.45 : r; ctx.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad); }
    ctx.closePath(); ctx.fill();
  }
  Art.star = star;

  /* ================================================================ pests */
  Art.drawPest = function (ctx, kind, x, y, r, o) {
    o = o || {};
    var t = o.t || 0, ang = o.ang || 0, lw = Math.max(1, r * 0.1);
    var flyer = kind === 'fly' || kind === 'gull' || kind === 'wasp' || kind === 'queen';
    if (!flyer) shadow(ctx, x, y + r * 0.55, r * 0.8 * (1 - (o.z || 0) * 0.5), r * 0.25, 0.2);
    else shadow(ctx, x, y + r * 1.2, r * 0.55, r * 0.18, 0.15);
    ctx.save();
    ctx.translate(x, y - (flyer ? r * 0.4 : 0) - (o.z || 0) * r * 2);
    if (o.hidden) ctx.globalAlpha = 0.3 + 0.08 * Math.sin(t * 3);
    if (o.flash) ctx.globalAlpha = 0.5 + 0.5 * Math.sin(t * 40);
    ctx.rotate(ang);
    ctx.lineWidth = lw; ctx.strokeStyle = INK; ctx.lineCap = 'round';
    var step = Math.sin(t * 20) * 0.35;
    switch (kind) {
      case 'ant':
        ctx.strokeStyle = '#3b1610'; ctx.lineWidth = lw * 0.8;
        for (var i = -1; i <= 1; i++) {
          ctx.beginPath(); ctx.moveTo(i * r * 0.25, 0); ctx.lineTo(i * r * 0.3 + step * r * 0.3 * (i % 2 ? 1 : -1), -r * 0.6); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(i * r * 0.25, 0); ctx.lineTo(i * r * 0.3 - step * r * 0.3 * (i % 2 ? 1 : -1), r * 0.6); ctx.stroke();
        }
        ctx.lineWidth = lw;
        ellipse(ctx, -r * 0.55, 0, r * 0.38, r * 0.3, '#8a2e1c', INK, lw);
        circle(ctx, 0, 0, r * 0.22, '#8a2e1c', INK, lw);
        circle(ctx, r * 0.45, 0, r * 0.27, '#9b3a26', INK, lw);
        ctx.beginPath(); ctx.moveTo(r * 0.6, -r * 0.1); ctx.quadraticCurveTo(r * 0.9, -r * 0.35, r * 1.0, -r * 0.2); ctx.moveTo(r * 0.6, r * 0.1); ctx.quadraticCurveTo(r * 0.9, r * 0.35, r * 1.0, r * 0.2); ctx.stroke();
        circle(ctx, r * 0.55, -r * 0.1, r * 0.06, '#fff'); circle(ctx, r * 0.55, r * 0.1, r * 0.06, '#fff');
        break;
      case 'rat':
      case 'king':
        var big = kind === 'king';
        ctx.beginPath(); ctx.moveTo(-r * 0.8, 0); ctx.bezierCurveTo(-r * 1.3, Math.sin(t * 6) * r * 0.5, -r * 1.5, -Math.sin(t * 6) * r * 0.4, -r * 1.8, 0);
        ctx.strokeStyle = '#d98b94'; ctx.lineWidth = lw * 1.1; ctx.stroke();
        if (big) { ctx.beginPath(); ctx.moveTo(-r * 0.2, -r * 0.62); ctx.quadraticCurveTo(-r * 1.4, -r * 0.9 + step * r * 0.2, -r * 1.2, 0); ctx.quadraticCurveTo(-r * 1.4, r * 0.9 - step * r * 0.2, -r * 0.2, r * 0.62); ctx.closePath(); ctx.fillStyle = '#b8322a'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = lw; ctx.stroke(); }
        ctx.strokeStyle = INK; ctx.lineWidth = lw;
        ellipse(ctx, -r * 0.1, 0, r * 0.82, r * 0.6, big ? '#6f6a78' : '#8f8b99', INK, lw);
        ellipse(ctx, r * 0.55, 0, r * 0.45, r * 0.4, big ? '#7d7887' : '#9d99a6', INK, lw);
        circle(ctx, r * 0.4, -r * 0.42, r * 0.2, '#f2a8b4', INK, lw * 0.8); circle(ctx, r * 0.4, r * 0.42, r * 0.2, '#f2a8b4', INK, lw * 0.8);
        circle(ctx, r * 1.0, 0, r * 0.1, '#f28b9b');
        var angry = o.chasing || big;
        circle(ctx, r * 0.72, -r * 0.17, r * 0.08, angry ? '#ff3b30' : INK); circle(ctx, r * 0.72, r * 0.17, r * 0.08, angry ? '#ff3b30' : INK);
        ctx.strokeStyle = 'rgba(40,20,20,.6)'; ctx.lineWidth = lw * 0.5; ctx.beginPath();
        ctx.moveTo(r * 0.95, -r * 0.05); ctx.lineTo(r * 1.3, -r * 0.25); ctx.moveTo(r * 0.95, r * 0.05); ctx.lineTo(r * 1.3, r * 0.25); ctx.stroke();
        break;
      case 'fly':
        var flap = 0.6 + 0.4 * Math.abs(Math.sin(t * 50));
        ctx.fillStyle = 'rgba(220,240,255,.7)'; ctx.strokeStyle = 'rgba(40,40,60,.6)'; ctx.lineWidth = lw * 0.6;
        ctx.beginPath(); ctx.ellipse(-r * 0.15, -r * 0.55, r * 0.55 * flap, r * 0.3, -0.4, 0, TAU); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.ellipse(-r * 0.15, r * 0.55, r * 0.55 * flap, r * 0.3, 0.4, 0, TAU); ctx.fill(); ctx.stroke();
        ctx.strokeStyle = INK; ctx.lineWidth = lw;
        ellipse(ctx, -r * 0.1, 0, r * 0.55, r * 0.38, '#2d3a2e', INK, lw);
        ctx.fillStyle = 'rgba(120,200,120,.45)'; ellipse(ctx, -r * 0.2, -r * 0.1, r * 0.25, r * 0.12, ctx.fillStyle);
        circle(ctx, r * 0.42, -r * 0.2, r * 0.2, '#c0392b', INK, lw * 0.7); circle(ctx, r * 0.42, r * 0.2, r * 0.2, '#c0392b', INK, lw * 0.7);
        break;
      case 'roach':
        ctx.strokeStyle = '#3b1f10'; ctx.lineWidth = lw * 0.8;
        for (var j = -1; j <= 1; j++) {
          ctx.beginPath(); ctx.moveTo(j * r * 0.35, -r * 0.3); ctx.lineTo(j * r * 0.45 + step * r * 0.4 * (j % 2 ? 1 : -1), -r * 0.85); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(j * r * 0.35, r * 0.3); ctx.lineTo(j * r * 0.45 - step * r * 0.4 * (j % 2 ? 1 : -1), r * 0.85); ctx.stroke();
        }
        ctx.beginPath(); ctx.moveTo(r * 0.75, -r * 0.1); ctx.quadraticCurveTo(r * 1.3, -r * 0.5, r * 1.6, -r * 0.25 + step * r * 0.2);
        ctx.moveTo(r * 0.75, r * 0.1); ctx.quadraticCurveTo(r * 1.3, r * 0.5, r * 1.6, r * 0.25 - step * r * 0.2); ctx.stroke();
        ctx.strokeStyle = INK; ctx.lineWidth = lw;
        ellipse(ctx, 0, 0, r * 0.9, r * 0.55, '#7a4220', INK, lw);
        ellipse(ctx, r * 0.72, 0, r * 0.25, r * 0.3, '#5a2f16', INK, lw);
        ctx.strokeStyle = 'rgba(30,10,0,.5)'; ctx.beginPath(); ctx.moveTo(-r * 0.8, 0); ctx.lineTo(r * 0.5, 0); ctx.stroke();
        ctx.fillStyle = 'rgba(255,220,180,.35)'; ellipse(ctx, -r * 0.1, -r * 0.25, r * 0.45, r * 0.1, ctx.fillStyle);
        if (o.hp < o.maxHp) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(-r * 0.3, -r * 0.4); ctx.lineTo(-r * 0.1, -r * 0.1); ctx.lineTo(-r * 0.3, r * 0.2); ctx.stroke(); }
        break;
      case 'gull':
        var spread = o.swooping ? 1.25 : 0.7 + 0.3 * Math.sin(t * 8);
        ctx.fillStyle = '#c9d1d8'; ctx.strokeStyle = INK; ctx.lineWidth = lw;
        ctx.beginPath(); ctx.moveTo(r * 0.1, -r * 0.2); ctx.quadraticCurveTo(-r * 0.2, -r * 1.3 * spread, -r * 0.7, -r * 1.25 * spread); ctx.quadraticCurveTo(-r * 0.3, -r * 0.6, -r * 0.4, -r * 0.1); ctx.closePath(); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(r * 0.1, r * 0.2); ctx.quadraticCurveTo(-r * 0.2, r * 1.3 * spread, -r * 0.7, r * 1.25 * spread); ctx.quadraticCurveTo(-r * 0.3, r * 0.6, -r * 0.4, r * 0.1); ctx.closePath(); ctx.fill(); ctx.stroke();
        ctx.fillStyle = '#3d4a55'; ctx.beginPath(); ctx.moveTo(-r * 0.7, -r * 1.25 * spread); ctx.lineTo(-r * 0.5, -r * 0.9 * spread); ctx.lineTo(-r * 0.85, -r * 1.0 * spread); ctx.fill();
        ctx.beginPath(); ctx.moveTo(-r * 0.7, r * 1.25 * spread); ctx.lineTo(-r * 0.5, r * 0.9 * spread); ctx.lineTo(-r * 0.85, r * 1.0 * spread); ctx.fill();
        ellipse(ctx, 0, 0, r * 0.75, r * 0.38, '#ffffff', INK, lw);
        circle(ctx, r * 0.6, 0, r * 0.28, '#ffffff', INK, lw);
        ctx.beginPath(); ctx.moveTo(r * 0.82, -r * 0.08); ctx.lineTo(r * 1.2, 0); ctx.lineTo(r * 0.82, r * 0.08); ctx.closePath(); ctx.fillStyle = '#f4b63c'; ctx.fill(); ctx.stroke();
        circle(ctx, r * 0.68, -r * 0.12, r * 0.05, INK); circle(ctx, r * 0.68, r * 0.12, r * 0.05, INK);
        break;
      case 'snail':
        // a soft slug body with eye stalks, under a spiral shell
        ellipse(ctx, r * 0.15, 0, r * 1.0, r * 0.42, '#e8c59a', INK, lw);
        ctx.strokeStyle = INK; ctx.lineWidth = lw * 0.8; ctx.beginPath();
        ctx.moveTo(r * 0.95, -r * 0.15); ctx.lineTo(r * 1.35, -r * 0.4 + step * r * 0.1); ctx.moveTo(r * 0.95, r * 0.15); ctx.lineTo(r * 1.35, r * 0.4 - step * r * 0.1); ctx.stroke();
        circle(ctx, r * 1.38, -r * 0.42, r * 0.1, INK); circle(ctx, r * 1.38, r * 0.42, r * 0.1, INK);
        circle(ctx, -r * 0.2, 0, r * 0.62, '#d9893a', INK, lw);
        ctx.strokeStyle = '#8a4a1a'; ctx.lineWidth = lw * 0.9; ctx.beginPath();
        for (var sp = 0; sp < 22; sp++) { var sa = sp * 0.5, srad = r * 0.05 + sp * r * 0.024; ctx.lineTo(-r * 0.2 + Math.cos(sa) * srad, Math.sin(sa) * srad); }
        ctx.stroke();
        if (o.hp < o.maxHp) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(-r * 0.5, -r * 0.4); ctx.lineTo(-r * 0.3, -r * 0.1); ctx.stroke(); }
        break;
      case 'mould':
        // a wobbly green blob with fuzzy spots
        ctx.rotate(-ang);
        var wob = Math.sin(t * 7) * 0.12;
        ellipse(ctx, 0, r * 0.1, r * (1 + wob), r * (0.85 - wob), '#8fbf5a', INK, lw);
        circle(ctx, -r * 0.4, -r * 0.15, r * 0.16, '#b5d98a'); circle(ctx, r * 0.35, r * 0.3, r * 0.12, '#6f9e44'); circle(ctx, r * 0.45, -r * 0.3, r * 0.09, '#b5d98a');
        circle(ctx, -r * 0.22, r * 0.02, r * 0.14, '#fff', INK, lw * 0.6); circle(ctx, r * 0.18, r * 0.02, r * 0.14, '#fff', INK, lw * 0.6);
        circle(ctx, -r * 0.2, r * 0.05, r * 0.06, INK); circle(ctx, r * 0.2, r * 0.05, r * 0.06, INK);
        break;
      case 'frog':
        ctx.fillStyle = '#4f9a36';
        [[-1, -1], [-1, 1]].forEach(function (d) { ellipse(ctx, -r * 0.5, d[1] * r * 0.62, r * 0.42, r * 0.2, '#4f9a36', INK, lw * 0.8, d[1] * 0.4); });
        ellipse(ctx, 0, 0, r * 0.85, r * 0.7, '#6fbf4a', INK, lw);
        ellipse(ctx, -r * 0.1, 0, r * 0.45, r * 0.36, '#c9e8a0');
        circle(ctx, r * 0.5, -r * 0.42, r * 0.24, '#6fbf4a', INK, lw); circle(ctx, r * 0.5, r * 0.42, r * 0.24, '#6fbf4a', INK, lw);
        circle(ctx, r * 0.55, -r * 0.42, r * 0.11, INK); circle(ctx, r * 0.55, r * 0.42, r * 0.11, INK);
        ctx.strokeStyle = '#2f6a1e'; ctx.beginPath(); ctx.arc(r * 0.55, 0, r * 0.25, -0.9, 0.9); ctx.stroke();
        break;
      case 'weevil':
        ctx.strokeStyle = '#2a1a10'; ctx.lineWidth = lw * 0.8;
        for (var wj = -1; wj <= 1; wj++) {
          ctx.beginPath(); ctx.moveTo(wj * r * 0.3, -r * 0.3); ctx.lineTo(wj * r * 0.4 + step * r * 0.3 * (wj % 2 ? 1 : -1), -r * 0.8); ctx.stroke();
          ctx.beginPath(); ctx.moveTo(wj * r * 0.3, r * 0.3); ctx.lineTo(wj * r * 0.4 - step * r * 0.3 * (wj % 2 ? 1 : -1), r * 0.8); ctx.stroke();
        }
        ctx.strokeStyle = INK; ctx.lineWidth = lw;
        ellipse(ctx, -r * 0.1, 0, r * 0.8, r * 0.6, '#6b4a30', INK, lw);
        ctx.strokeStyle = 'rgba(20,10,0,.55)'; ctx.beginPath(); ctx.moveTo(-r * 0.85, 0); ctx.lineTo(r * 0.55, 0); ctx.stroke(); ctx.strokeStyle = INK;
        circle(ctx, r * 0.62, 0, r * 0.28, '#5a3a24', INK, lw);
        ctx.lineWidth = lw * 1.4; ctx.beginPath(); ctx.moveTo(r * 0.85, 0); ctx.lineTo(r * 1.35, 0); ctx.stroke(); ctx.lineWidth = lw;
        ctx.fillStyle = 'rgba(255,230,200,.35)'; ellipse(ctx, -r * 0.2, -r * 0.28, r * 0.4, r * 0.1, ctx.fillStyle);
        circle(ctx, r * 0.7, -r * 0.15, r * 0.06, o.chasing ? '#ff3b30' : '#fff'); circle(ctx, r * 0.7, r * 0.15, r * 0.06, o.chasing ? '#ff3b30' : '#fff');
        break;
      case 'spider':
        ctx.strokeStyle = '#1a1420'; ctx.lineWidth = lw * 0.9;
        for (var sj = 0; sj < 4; sj++) {
          var la = 0.5 + sj * 0.55, wig = Math.sin(t * 16 + sj) * 0.15;
          [-1, 1].forEach(function (sd) {
            ctx.beginPath(); ctx.moveTo(0, 0);
            ctx.quadraticCurveTo(Math.cos(la + wig) * r * 0.9, sd * Math.sin(la + wig) * r * 1.2, Math.cos(la + wig) * r * 1.3 - r * 0.2, sd * Math.sin(la + wig) * r * 1.5);
            ctx.stroke();
          });
        }
        ctx.strokeStyle = INK; ctx.lineWidth = lw;
        circle(ctx, -r * 0.3, 0, r * 0.62, '#3a3040', INK, lw);
        circle(ctx, r * 0.4, 0, r * 0.36, '#4a3e52', INK, lw);
        ctx.fillStyle = '#d63031'; ctx.beginPath(); ctx.moveTo(-r * 0.3, -r * 0.25); ctx.lineTo(-r * 0.15, 0); ctx.lineTo(-r * 0.3, r * 0.25); ctx.lineTo(-r * 0.45, 0); ctx.closePath(); ctx.fill();
        [[-0.1, 0.4], [0.1, 0.4], [-0.18, 0.55], [0.18, 0.55]].forEach(function (e) { circle(ctx, r * e[1] + r * 0.1, e[0] * r, r * 0.06, '#ff5a4a'); });
        break;
      case 'wasp':
      case 'queen':
        var wf = 0.6 + 0.4 * Math.abs(Math.sin(t * 45));
        ctx.fillStyle = 'rgba(230,245,255,.75)'; ctx.strokeStyle = 'rgba(40,40,60,.6)'; ctx.lineWidth = lw * 0.6;
        ctx.beginPath(); ctx.ellipse(-r * 0.05, -r * 0.6, r * 0.6 * wf, r * 0.28, -0.5, 0, TAU); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.ellipse(-r * 0.05, r * 0.6, r * 0.6 * wf, r * 0.28, 0.5, 0, TAU); ctx.fill(); ctx.stroke();
        ctx.strokeStyle = INK; ctx.lineWidth = lw;
        ctx.beginPath(); ctx.moveTo(-r * 1.0, 0); ctx.lineTo(-r * 1.3, 0); ctx.stroke();
        ellipse(ctx, -r * 0.4, 0, r * 0.6, r * 0.4, '#f4c430', INK, lw);
        ctx.save(); ctx.beginPath(); ctx.ellipse(-r * 0.4, 0, r * 0.6, r * 0.4, 0, 0, TAU); ctx.clip();
        ctx.fillStyle = '#2b1b10'; ctx.fillRect(-r * 0.6, -r, r * 0.16, r * 2); ctx.fillRect(-r * 0.25, -r, r * 0.16, r * 2); ctx.restore();
        ellipse(ctx, -r * 0.4, 0, r * 0.6, r * 0.4, null, INK, lw);
        circle(ctx, r * 0.28, 0, r * 0.22, '#3a2a14', INK, lw);
        circle(ctx, r * 0.6, 0, r * 0.25, '#f4c430', INK, lw);
        circle(ctx, r * 0.68, -r * 0.12, r * 0.07, o.chasing ? '#ff3b30' : INK); circle(ctx, r * 0.68, r * 0.12, r * 0.07, o.chasing ? '#ff3b30' : INK);
        break;
    }
    ctx.restore();
    if (o.dizzy) {
      for (var dz = 0; dz < 3; dz++) { var da = t * 4 + dz * 2.1; ctx.fillStyle = '#fff6c2'; star(ctx, x + Math.cos(da) * r * 0.8, y - r * 1.0 + Math.sin(da) * r * 0.25, r * 0.22); }
    }
    if (kind === 'king') Art.drawHat(ctx, 'crown', x + Math.cos(ang) * r * 0.5, y + Math.sin(ang) * r * 0.3 - r * 0.25, r * 0.75, t);
    if (kind === 'queen') Art.drawHat(ctx, 'crown', x + Math.cos(ang) * r * 0.55, y + Math.sin(ang) * r * 0.25 - r * 0.7, r * 0.6, t);
    if (o.maxHp > 1) {
      var bossBar = kind === 'king' || kind === 'queen';
      var py = y - r * (bossBar ? 1.55 : 1.25) - (kind === 'queen' ? r * 0.4 : 0), pr = bossBar ? r * 0.09 : r * 0.12, gap = bossBar ? r * 0.22 : r * 0.32;
      for (var hp = 0; hp < o.maxHp; hp++) circle(ctx, x - (o.maxHp - 1) * gap / 2 + hp * gap, py, pr, hp < o.hp ? '#e0483a' : 'rgba(0,0,0,.25)', INK, 1);
    }
    if (o.alert) {
      ctx.save(); ctx.font = '900 ' + Math.round(r * 1.2) + 'px Fredoka, sans-serif'; ctx.textAlign = 'center'; ctx.lineWidth = 4; ctx.strokeStyle = INK; ctx.fillStyle = '#f4b63c';
      ctx.strokeText('!', x, y - r * 1.4); ctx.fillText('!', x, y - r * 1.4); ctx.restore();
    }
  };

  /* ================================================================ nests, steamer, neighbours */
  Art.drawNest = function (ctx, x, y, r, o) {
    o = o || {};
    var t = o.t || 0, pulse = 1 + 0.05 * Math.sin(t * 4), dmg = o.maxHp ? 1 - o.hp / o.maxHp : 0;
    shadow(ctx, x, y + r * 0.55, r * 1.05, r * 0.3, 0.3);
    ctx.save(); ctx.translate(x, y); ctx.scale(pulse, 1 / pulse);
    if (o.flash) ctx.globalAlpha = 0.6;
    var lw = Math.max(1.5, r * 0.08);
    ctx.beginPath();
    for (var i = 0; i <= 14; i++) { var a = Math.PI + i / 14 * Math.PI, rad = r * (0.95 + 0.12 * Math.sin(i * 2.7)); ctx.lineTo(Math.cos(a) * rad, Math.sin(a) * rad * 0.85 + r * 0.25); }
    ctx.closePath();
    var g = ctx.createLinearGradient(0, -r, 0, r * 0.4); g.addColorStop(0, '#6b4a6e'); g.addColorStop(1, '#3a2340');
    ctx.fillStyle = g; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = lw; ctx.stroke();
    var crumbs = [[-0.5, -0.1, '#c9a46a'], [0.3, -0.45, '#8a5a2b'], [0.55, 0.05, '#e8d3a3'], [-0.15, -0.55, '#5e9c4a'], [0.05, -0.05, '#c0392b']];
    crumbs.forEach(function (c) { circle(ctx, c[0] * r, c[1] * r, r * 0.11, c[2], INK, 1); });
    ellipse(ctx, 0, r * 0.12, r * 0.38, r * 0.2, '#140a16', INK, lw * 0.7);
    var blink = Math.sin(t * 2.3 + x) > 0.92;
    if (!blink) { circle(ctx, -r * 0.12, r * 0.1, r * 0.06, '#ffde59'); circle(ctx, r * 0.12, r * 0.1, r * 0.06, '#ffde59'); }
    if (dmg > 0) {
      ctx.strokeStyle = '#ffe9c4'; ctx.lineWidth = 2; ctx.beginPath();
      ctx.moveTo(-r * 0.4, -r * 0.6); ctx.lineTo(-r * 0.2, -r * 0.3); ctx.lineTo(-r * 0.35, -r * 0.05);
      if (dmg > 0.5) { ctx.moveTo(r * 0.45, -r * 0.5); ctx.lineTo(r * 0.25, -r * 0.25); ctx.lineTo(r * 0.4, 0); }
      ctx.stroke();
    }
    ctx.restore();
    if (o.maxHp) for (var hp = 0; hp < o.maxHp; hp++) circle(ctx, x - (o.maxHp - 1) * r * 0.2 + hp * r * 0.4, y - r * 1.1, r * 0.13, hp < o.hp ? '#a35bd6' : 'rgba(0,0,0,.25)', INK, 1);
  };

  Art.drawGoo = function (ctx, x, y, s, t, a, tx, ty) {
    ctx.fillStyle = 'rgba(80,30,100,' + (0.3 * a) + ')'; ctx.fillRect(x, y, s, s);
    var h = hash(tx, ty);
    if (h > 0.45) {
      ctx.fillStyle = 'rgba(60,20,80,' + (0.45 * a) + ')';
      circle(ctx, x + s * (0.2 + 0.6 * h), y + s * (0.3 + 0.4 * hash(ty, tx)), s * (0.1 + 0.06 * Math.sin(t * 3 + h * 9)), ctx.fillStyle);
    }
    if (h > 0.85) { ctx.fillStyle = 'rgba(200,160,255,' + (0.4 * a) + ')'; circle(ctx, x + s * 0.5, y + s * (0.6 - ((t * 0.3 + h) % 1) * 0.5), s * 0.05, ctx.fillStyle); }
  };

  Art.drawSteamer = function (ctx, x, y, r, o) {
    o = o || {};
    var t = o.t || 0, lw = Math.max(1.5, r * 0.08);
    if (o.open) {
      var gl = ctx.createRadialGradient(x, y, r * 0.3, x, y, r * 2);
      gl.addColorStop(0, 'rgba(255,220,120,' + (0.45 + 0.15 * Math.sin(t * 4)) + ')'); gl.addColorStop(1, 'rgba(255,220,120,0)');
      ctx.fillStyle = gl; ctx.fillRect(x - r * 2, y - r * 2, r * 4, r * 4);
    }
    shadow(ctx, x, y + r * 0.7, r * 1.05, r * 0.3, 0.25);
    ctx.lineWidth = lw; ctx.strokeStyle = INK;
    // basket
    ctx.beginPath(); ctx.moveTo(-r + x, y - r * 0.1); ctx.lineTo(-r + x, y + r * 0.45); ctx.ellipse(x, y + r * 0.45, r, r * 0.32, 0, Math.PI, 0, true); ctx.lineTo(x + r, y - r * 0.1); ctx.closePath();
    ctx.fillStyle = '#d4a85e'; ctx.fill(); ctx.stroke();
    ctx.strokeStyle = 'rgba(110,70,20,.5)'; ctx.lineWidth = lw * 0.6; ctx.beginPath();
    for (var i = 1; i < 3; i++) { ctx.moveTo(x - r, y - r * 0.1 + i * r * 0.18); ctx.quadraticCurveTo(x, y + i * r * 0.18 + r * 0.22, x + r, y - r * 0.1 + i * r * 0.18); }
    ctx.stroke();
    ellipse(ctx, x, y - r * 0.1, r, r * 0.32, '#e6c27f', INK, lw);
    // lid
    var lift = o.open ? r * (0.5 + 0.08 * Math.sin(t * 6)) : 0, tilt = o.open ? -0.25 : 0;
    ctx.save(); ctx.translate(x + (o.open ? -r * 0.15 : 0), y - r * 0.15 - lift); ctx.rotate(tilt);
    ctx.beginPath(); ctx.ellipse(0, 0, r * 1.02, r * 0.34, 0, Math.PI, 0); ctx.quadraticCurveTo(0, -r * 0.95, -r * 1.02, 0); ctx.closePath();
    ctx.fillStyle = '#e8c27a'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = lw; ctx.stroke();
    ctx.strokeStyle = 'rgba(110,70,20,.45)'; ctx.lineWidth = lw * 0.6; ctx.beginPath();
    for (var k = -2; k <= 2; k++) { ctx.moveTo(k * r * 0.28, -r * 0.05); ctx.quadraticCurveTo(k * r * 0.12, -r * 0.4, 0, -r * 0.55); } ctx.stroke();
    circle(ctx, 0, -r * 0.55, r * 0.1, '#c49a55', INK, lw * 0.7);
    ctx.restore();
    if (o.open) {
      for (var p = 0; p < 3; p++) {
        var ph = (t * 0.6 + p / 3) % 1;
        circle(ctx, x + Math.sin(ph * 6 + p) * r * 0.4, y - r * 0.6 - ph * r * 1.6, r * (0.18 + ph * 0.25), 'rgba(255,255,255,' + (0.7 * (1 - ph)) + ')');
      }
    } else if (!o.noLock) {
      ctx.save(); ctx.translate(x, y + r * 0.2);
      rr(ctx, -r * 0.22, -r * 0.08, r * 0.44, r * 0.34, r * 0.06); ctx.fillStyle = '#f4b63c'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = lw * 0.7; ctx.stroke();
      ctx.beginPath(); ctx.arc(0, -r * 0.08, r * 0.13, Math.PI, 0); ctx.stroke();
      ctx.restore();
    }
  };

  Art.drawNPC = function (ctx, style, x, y, r, o) {
    o = o || {};
    var t = o.t || 0, lw = Math.max(1.5, r * 0.085), bob = Math.sin(t * 3 + x * 0.1) * r * 0.04;
    shadow(ctx, x, y + r * 0.8, r * 0.9, r * 0.26, 0.22);
    ctx.save(); ctx.translate(x, y + bob); ctx.lineWidth = lw; ctx.strokeStyle = INK; ctx.lineJoin = 'round';
    var face = function (fx, fy, s, glasses) {
      ellipse(ctx, fx - s * 0.5, fy + s * 0.2, s * 0.15, s * 0.09, 'rgba(255,130,140,.5)'); ellipse(ctx, fx + s * 0.5, fy + s * 0.2, s * 0.15, s * 0.09, 'rgba(255,130,140,.5)');
      if (o.happy) { ctx.lineWidth = lw * 0.9; ctx.beginPath(); ctx.arc(fx - s * 0.28, fy, s * 0.08, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke(); ctx.beginPath(); ctx.arc(fx + s * 0.28, fy, s * 0.08, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke(); }
      else { circle(ctx, fx - s * 0.28, fy - s * 0.02, s * 0.075, INK); circle(ctx, fx + s * 0.28, fy - s * 0.02, s * 0.075, INK); }
      if (glasses) { ctx.lineWidth = lw * 0.6; circle(ctx, fx - s * 0.28, fy - s * 0.02, s * 0.17, null, INK, lw * 0.6); circle(ctx, fx + s * 0.28, fy - s * 0.02, s * 0.17, null, INK, lw * 0.6); ctx.beginPath(); ctx.moveTo(fx - s * 0.11, fy - s * 0.02); ctx.lineTo(fx + s * 0.11, fy - s * 0.02); ctx.stroke(); }
      ctx.lineWidth = lw * 0.8; ctx.beginPath(); ctx.arc(fx, fy + s * 0.12, s * 0.1, 0.2, Math.PI - 0.2); ctx.stroke();
    };
    switch (style) {
      case 'grandma':
        circle(ctx, 0, -r * 0.95, r * 0.32, '#c9c3cf', INK, lw);
        ctx.beginPath(); ctx.moveTo(-r * 0.12, -r * 1.2); ctx.lineTo(r * 0.2, -r * 0.7); ctx.strokeStyle = '#b8322a'; ctx.lineWidth = lw; ctx.stroke(); ctx.strokeStyle = INK;
        Art.drawBun(ctx, 0, 0, r * 0.95, { noShadow: true, tint: '#f8eedc', face: o.happy ? 'joy' : 'happy', t: t });
        ctx.lineWidth = lw * 0.6; circle(ctx, -r * 0.3, r * 0.03, r * 0.17, null, INK, lw * 0.6); circle(ctx, r * 0.3, r * 0.03, r * 0.17, null, INK, lw * 0.6);
        ctx.beginPath(); ctx.ellipse(0, r * 0.62, r * 0.75, r * 0.2, 0, 0, Math.PI); ctx.fillStyle = '#b8322a'; ctx.fill();
        break;
      case 'dumpling':
        ctx.beginPath(); ctx.moveTo(-r * 1.05, r * 0.4); ctx.quadraticCurveTo(-r * 0.9, -r * 0.95, 0, -r * 0.95); ctx.quadraticCurveTo(r * 0.9, -r * 0.95, r * 1.05, r * 0.4); ctx.quadraticCurveTo(0, r * 0.75, -r * 1.05, r * 0.4); ctx.closePath();
        ctx.fillStyle = '#f7efe0'; ctx.fill(); ctx.stroke();
        ctx.beginPath(); for (var i = 0; i <= 8; i++) { var px = -r * 0.8 + i * r * 0.2; ctx.lineTo(px, -r * 0.82 + (i % 2) * r * 0.16 + Math.abs(i - 4) * r * 0.05); } ctx.strokeStyle = 'rgba(160,120,80,.8)'; ctx.stroke();
        face(0, r * 0.05, r);
        break;
      case 'tofu':
        rr(ctx, -r * 0.85, -r * 0.8, r * 1.7, r * 1.5, r * 0.3); ctx.fillStyle = '#fbf8ef'; ctx.fill(); ctx.stroke();
        ctx.fillStyle = 'rgba(0,0,0,.06)'; ctx.fillRect(-r * 0.85 + lw, r * 0.35, r * 1.7 - lw * 2, r * 0.3);
        face(0, -r * 0.02, r);
        ellipse(ctx, r * 0.55, -r * 0.7, r * 0.14, r * 0.2, '#5a2d14');
        break;
      case 'eggtart':
        ellipse(ctx, 0, 0, r * 1.0, r * 0.88, '#d9963f', INK, lw);
        ctx.strokeStyle = 'rgba(120,60,10,.45)'; ctx.beginPath(); for (var j = 0; j < 16; j++) { var a = j / 16 * TAU; ctx.moveTo(Math.cos(a) * r * 0.78, Math.sin(a) * r * 0.68); ctx.lineTo(Math.cos(a) * r * 0.98, Math.sin(a) * r * 0.86); } ctx.stroke(); ctx.strokeStyle = INK;
        ellipse(ctx, 0, 0, r * 0.74, r * 0.64, '#ffd34d', INK, lw * 0.8);
        ellipse(ctx, -r * 0.25, -r * 0.3, r * 0.2, r * 0.08, 'rgba(255,255,255,.6)');
        face(0, r * 0.02, r * 0.85);
        break;
      case 'mooncake':
        circle(ctx, 0, 0, r * 0.95, '#b06a2a', INK, lw);
        ctx.strokeStyle = 'rgba(70,30,5,.5)'; ctx.lineWidth = lw * 0.7; circle(ctx, 0, 0, r * 0.72, null, 'rgba(70,30,5,.5)', lw * 0.7);
        for (var k = 0; k < 8; k++) { var a2 = k / 8 * TAU; ctx.beginPath(); ctx.arc(Math.cos(a2) * r * 0.84, Math.sin(a2) * r * 0.84, r * 0.12, 0, TAU); ctx.stroke(); }
        ctx.strokeStyle = INK; face(0, 0, r * 0.85);
        break;
      case 'sesame':
        var sg = ctx.createRadialGradient(-r * 0.3, -r * 0.3, r * 0.1, 0, 0, r); sg.addColorStop(0, '#f2c46d'); sg.addColorStop(1, '#c98a2c');
        circle(ctx, 0, 0, r * 0.9, sg, INK, lw);
        for (var s = 0; s < 22; s++) { var aa = hash(s, 3) * TAU, d = Math.sqrt(hash(3, s)) * r * 0.82; if (Math.abs(Math.sin(aa) * d) < r * 0.45 && Math.cos(aa) * d > -r * 0.5 && Math.cos(aa) * d < r * 0.5 && Math.sin(aa) * d > -r * 0.2) continue; ellipse(ctx, Math.cos(aa) * d, Math.sin(aa) * d, r * 0.05, r * 0.025, '#fffaf0', null, 0, aa); }
        face(0, r * 0.05, r * 0.8);
        break;
      case 'fortune':
        ctx.beginPath(); ctx.moveTo(-r * 1.0, r * 0.2); ctx.quadraticCurveTo(-r * 0.9, -r * 0.95, 0, -r * 0.55); ctx.quadraticCurveTo(r * 0.9, -r * 0.95, r * 1.0, r * 0.2); ctx.quadraticCurveTo(r * 0.3, r * 0.8, 0, r * 0.25); ctx.quadraticCurveTo(-r * 0.3, r * 0.8, -r * 1.0, r * 0.2); ctx.closePath();
        ctx.fillStyle = '#f0c46a'; ctx.fill(); ctx.stroke();
        ctx.save(); ctx.rotate(-0.3); ctx.fillStyle = '#fff'; ctx.fillRect(r * 0.05, r * 0.25, r * 0.85, r * 0.2); ctx.strokeRect(r * 0.05, r * 0.25, r * 0.85, r * 0.2);
        ctx.fillStyle = '#e0483a'; ctx.fillRect(r * 0.2, r * 0.32, r * 0.5, r * 0.05); ctx.restore();
        face(0, -r * 0.2, r * 0.8);
        break;
    }
    ctx.restore();
  };

  /* ================================================================ items and pickups */
  var emojiCache = {};
  Art.emojiCanvas = function (emoji, size) {
    size = Math.max(8, Math.round(size));
    var key = emoji + '|' + size;
    if (emojiCache[key]) return emojiCache[key];
    var c = document.createElement('canvas'), pad = Math.ceil(size * 0.25);
    c.width = c.height = size + pad * 2;
    var x = c.getContext('2d');
    x.font = size + 'px ' + EMOJI_FONT; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillText(emoji, c.width / 2, c.height / 2 + size * 0.06);
    emojiCache[key] = c;
    return c;
  };
  Art.drawEmoji = function (ctx, emoji, x, y, size) {
    var c = Art.emojiCanvas(emoji, size);
    ctx.drawImage(c, x - c.width / 2, y - c.height / 2);
  };
  Art.RARITY_COLORS = { common: null, uncommon: '#3d8fd1', rare: '#9b59d0', legendary: '#f4b63c' };
  Art.drawItem = function (ctx, item, x, y, s, t, opts) {
    opts = opts || {};
    var bob = opts.still ? 0 : Math.sin(t * 3.5 + x * 0.07 + y * 0.03) * s * 0.07;
    shadow(ctx, x, y + s * 0.38, s * 0.28 * (1 - bob / s), s * 0.09, 0.18);
    var rc = item && (item.gold ? '#f4b63c' : Art.RARITY_COLORS[item.rarity]);
    if (rc) {
      var g = ctx.createRadialGradient(x, y + bob, s * 0.05, x, y + bob, s * 0.55);
      g.addColorStop(0, rc + 'aa'); g.addColorStop(1, rc + '00');
      ctx.fillStyle = g; ctx.fillRect(x - s * 0.6, y + bob - s * 0.6, s * 1.2, s * 1.2);
    }
    if (item && item.gold && !opts.still) {
      for (var i = 0; i < 3; i++) { var a = t * 2 + i * 2.1; ctx.fillStyle = '#fff6c2'; star(ctx, x + Math.cos(a) * s * 0.42, y + bob + Math.sin(a) * s * 0.3, s * 0.08); }
    }
    Art.drawEmoji(ctx, item ? item.emoji : '❔', x, y + bob, s * 0.62);
  };
  Art.drawCoin = function (ctx, x, y, r, t, still) {
    var sq = still ? 1 : Math.abs(Math.cos(t * 3 + x * 0.05));
    var bob = still ? 0 : Math.sin(t * 3.5 + x * 0.05) * r * 0.15;
    shadow(ctx, x, y + r * 1.0, r * 0.7, r * 0.22, 0.18);
    ctx.save(); ctx.translate(x, y + bob); ctx.scale(Math.max(0.12, sq), 1);
    circle(ctx, 0, 0, r, '#f4b63c', INK, Math.max(1, r * 0.14));
    circle(ctx, 0, 0, r * 0.72, null, '#d99417', Math.max(1, r * 0.1));
    ctx.fillStyle = INK; ctx.fillRect(-r * 0.2, -r * 0.2, r * 0.4, r * 0.4);
    ctx.fillStyle = 'rgba(255,255,255,.55)'; ctx.fillRect(-r * 0.55, -r * 0.55, r * 0.2, r * 0.2);
    ctx.restore();
  };
  Art.drawHeart = function (ctx, x, y, r, fill, stroke) {
    ctx.beginPath();
    ctx.moveTo(x, y + r * 0.85);
    ctx.bezierCurveTo(x - r * 1.3, y, x - r * 0.7, y - r * 0.95, x, y - r * 0.35);
    ctx.bezierCurveTo(x + r * 0.7, y - r * 0.95, x + r * 1.3, y, x, y + r * 0.85);
    ctx.closePath();
    ctx.fillStyle = fill || '#e0483a'; ctx.fill();
    ctx.strokeStyle = stroke || INK; ctx.lineWidth = Math.max(1, r * 0.16); ctx.stroke();
  };
  // Grandma's postcard: a little card with a stamp and handwriting (no hearts, so it isn't mistaken for health).
  Art.drawPostcard = function (ctx, x, y, w, rot) {
    var h = w * 0.68, lw = Math.max(1.2, w * 0.05);
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot || 0);
    rr(ctx, -w / 2, -h / 2, w, h, w * 0.06); ctx.fillStyle = '#fff7e2'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = lw; ctx.stroke();
    ctx.fillStyle = '#e0483a'; ctx.fillRect(w * 0.16, -h * 0.36, w * 0.24, h * 0.36);
    ctx.strokeStyle = '#fff7e2'; ctx.lineWidth = Math.max(1, w * 0.025); ctx.setLineDash([w * 0.03, w * 0.03]); ctx.strokeRect(w * 0.16, -h * 0.36, w * 0.24, h * 0.36); ctx.setLineDash([]);
    ctx.fillStyle = '#f4b63c'; circle(ctx, w * 0.28, -h * 0.18, w * 0.06, '#f4b63c');
    ctx.strokeStyle = '#3d8fd1'; ctx.lineWidth = Math.max(1, w * 0.035); ctx.lineCap = 'round'; ctx.beginPath();
    ctx.moveTo(-w * 0.38, -h * 0.18); ctx.lineTo(-w * 0.04, -h * 0.18);
    ctx.moveTo(-w * 0.38, 0); ctx.lineTo(-w * 0.1, 0);
    ctx.moveTo(-w * 0.38, h * 0.18); ctx.lineTo(w * 0.36, h * 0.18); ctx.stroke();
    ctx.restore();
  };
  Art.drawPickup = function (ctx, kind, x, y, s, t) {
    var bob = Math.sin(t * 3.5 + x * 0.07) * s * 0.07;
    if (kind === 'coin') return Art.drawCoin(ctx, x, y, s * 0.24, t);
    if (kind === 'knob' || kind === 'timer') return Art.drawKnob(ctx, x, y, s, t, { timer: kind === 'timer' });
    shadow(ctx, x, y + s * 0.38, s * 0.26, s * 0.08, 0.18);
    if (kind === 'heart') {
      // Health: a pulsing red heart with a white plus, so it reads as "heal" and not as a collectable.
      var pulse = 1 + 0.1 * Math.sin(t * 6 + x * 0.05);
      var hg = ctx.createRadialGradient(x, y + bob, s * 0.05, x, y + bob, s * 0.55);
      hg.addColorStop(0, 'rgba(255,90,90,.45)'); hg.addColorStop(1, 'rgba(255,90,90,0)');
      ctx.fillStyle = hg; ctx.fillRect(x - s * 0.6, y - s * 0.6 + bob, s * 1.2, s * 1.2);
      Art.drawHeart(ctx, x, y + bob, s * 0.3 * pulse);
      ctx.strokeStyle = '#fff'; ctx.lineWidth = Math.max(2, s * 0.07); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x - s * 0.1, y + bob); ctx.lineTo(x + s * 0.1, y + bob); ctx.moveTo(x, y + bob - s * 0.1); ctx.lineTo(x, y + bob + s * 0.1); ctx.stroke();
      return;
    }
    if (kind === 'chopsticks' || kind === 'postcard') {
      var g = ctx.createRadialGradient(x, y + bob, s * 0.05, x, y + bob, s * 0.6);
      g.addColorStop(0, kind === 'postcard' ? 'rgba(120,190,255,.6)' : 'rgba(255,215,90,.8)'); g.addColorStop(1, 'rgba(255,215,90,0)');
      ctx.fillStyle = g; ctx.fillRect(x - s * 0.6, y - s * 0.6 + bob, s * 1.2, s * 1.2);
      for (var i = 0; i < 2; i++) { var a = t * 2.5 + i * Math.PI; ctx.fillStyle = '#fffbe0'; star(ctx, x + Math.cos(a) * s * 0.4, y + bob + Math.sin(a) * s * 0.28, s * 0.08); }
    }
    if (kind === 'postcard') return Art.drawPostcard(ctx, x, y + bob, s * 0.62, Math.sin(t * 2 + x) * 0.12 - 0.1);
    var BONUS_GLOW = { magnet: '255,120,120', bubble: '140,210,255', bag: '255,210,80', anise: '255,214,80', clock: '190,170,255' };
    if (BONUS_GLOW[kind]) {
      // Bonuses: a glowing bubble that spins a little, so they read as "power-up".
      var pg = ctx.createRadialGradient(x, y + bob, s * 0.05, x, y + bob, s * 0.55);
      pg.addColorStop(0, 'rgba(' + BONUS_GLOW[kind] + ',.7)'); pg.addColorStop(1, 'rgba(' + BONUS_GLOW[kind] + ',0)');
      ctx.fillStyle = pg; ctx.fillRect(x - s * 0.6, y - s * 0.6 + bob, s * 1.2, s * 1.2);
      circle(ctx, x, y + bob, s * 0.33, 'rgba(255,255,255,.35)', 'rgba(255,255,255,.85)', Math.max(1.5, s * 0.04));
      ellipse(ctx, x - s * 0.12, y + bob - s * 0.15, s * 0.08, s * 0.04, 'rgba(255,255,255,.9)', null, 0, -0.6);
      if (kind === 'anise') for (var ai = 0; ai < 3; ai++) { var aa = t * 3 + ai * 2.1; ctx.fillStyle = '#fff6c2'; star(ctx, x + Math.cos(aa) * s * 0.42, y + bob + Math.sin(aa) * s * 0.32, s * 0.07); }
    }
    Art.drawEmoji(ctx, { tea: '🍵', chopsticks: '🥢', magnet: '🧲', bubble: '🛡️', bag: '💰', anise: '🌟', clock: '⏳' }[kind] || '✨', x, y + bob, s * (BONUS_GLOW[kind] ? 0.42 : 0.6));
  };
  // Oven knob / kitchen timer: a dial on a little stand. Red and glowing while the stoves are hot, blue once they're off.
  Art.drawKnob = function (ctx, x, y, s, t, o) {
    o = o || {};
    var lw = Math.max(1.2, s * 0.045), on = !o.off;
    shadow(ctx, x, y + s * 0.36, s * 0.3, s * 0.09, 0.22);
    if (on) {
      var g = ctx.createRadialGradient(x, y, s * 0.1, x, y, s * 0.6);
      g.addColorStop(0, 'rgba(255,140,60,' + (0.35 + 0.2 * Math.sin(t * 5)) + ')'); g.addColorStop(1, 'rgba(255,140,60,0)');
      ctx.fillStyle = g; ctx.fillRect(x - s * 0.6, y - s * 0.6, s * 1.2, s * 1.2);
    }
    rr(ctx, x - s * 0.3, y - s * 0.3, s * 0.6, s * 0.6, s * 0.12); ctx.fillStyle = '#e9e2d6'; ctx.fill(); ctx.strokeStyle = INK; ctx.lineWidth = lw; ctx.stroke();
    if (o.timer) {
      circle(ctx, x, y, s * 0.22, '#fff', INK, lw);
      if (o.off && o.frac > 0) { ctx.beginPath(); ctx.moveTo(x, y); ctx.arc(x, y, s * 0.2, -Math.PI / 2, -Math.PI / 2 + TAU * o.frac); ctx.closePath(); ctx.fillStyle = 'rgba(61,143,209,.6)'; ctx.fill(); }
      for (var i = 0; i < 12; i++) { var a = i / 12 * TAU; ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * s * 0.16, y + Math.sin(a) * s * 0.16); ctx.lineTo(x + Math.cos(a) * s * 0.2, y + Math.sin(a) * s * 0.2); ctx.lineWidth = 1; ctx.stroke(); }
      circle(ctx, x, y - s * 0.3, s * 0.06, on ? '#e0483a' : '#3d8fd1', INK, 1);
    } else {
      var ang = on ? -Math.PI / 2 + 0.9 : -Math.PI / 2 - 0.9;
      circle(ctx, x, y, s * 0.2, on ? '#e0483a' : '#3d8fd1', INK, lw);
      ctx.strokeStyle = '#fff'; ctx.lineWidth = Math.max(2, s * 0.06); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(ang) * s * 0.16, y + Math.sin(ang) * s * 0.16); ctx.stroke();
      ctx.font = '900 ' + Math.round(s * 0.13) + 'px Fredoka, sans-serif'; ctx.textAlign = 'center'; ctx.fillStyle = INK;
      ctx.fillText('OFF', x - s * 0.2, y - s * 0.21); ctx.fillText('ON', x + s * 0.2, y - s * 0.21);
    }
  };
  // Snail slime: a glossy trail that fades away.
  Art.drawSlime = function (ctx, x, y, s, a, tx, ty) {
    var h = hash(tx * 3, ty * 5);
    ctx.fillStyle = 'rgba(190,230,140,' + (0.45 * a) + ')';
    ellipse(ctx, x + s * (0.4 + 0.2 * h), y + s * 0.5, s * 0.42, s * 0.32, ctx.fillStyle);
    ctx.fillStyle = 'rgba(255,255,255,' + (0.5 * a) + ')';
    ellipse(ctx, x + s * (0.3 + 0.2 * h), y + s * 0.4, s * 0.1, s * 0.04, ctx.fillStyle, null, 0, -0.4);
  };

  /* ================================================================ small canvases for menus and the editor */
  Art.canvas = function (w, h) {
    var c = document.createElement('canvas'), dpr = Math.min(2, window.devicePixelRatio || 1);
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); c.style.width = w + 'px'; c.style.height = h + 'px';
    var ctx = c.getContext('2d'); ctx.scale(dpr, dpr);
    return { el: c, ctx: ctx };
  };
  Art.bunPortrait = function (size, hat, opts) {
    var c = Art.canvas(size, size);
    Art.drawBun(c.ctx, size / 2, size * 0.58, size * 0.3, Object.assign({ hat: hat, t: 0, face: 'happy' }, opts || {}));
    return c.el;
  };
  // The mascot as a PNG data URL (the same bun as the title screen), for CSS backgrounds.
  var mascotCache = {};
  Art.mascotURL = function (hat) {
    hat = hat || 'none';
    if (mascotCache[hat]) return mascotCache[hat];
    var c = document.createElement('canvas'); c.width = c.height = 240;
    Art.drawBun(c.getContext('2d'), 120, 150, 78, { noShadow: true, face: 'happy', hat: hat, t: 0 });
    try { mascotCache[hat] = c.toDataURL('image/png'); } catch (e) { mascotCache[hat] = ''; }
    return mascotCache[hat];
  };
  // Anvil's loading spinner and our own "one moment" overlays show the bouncing bun.
  // CSS for #loadingSpinner and .bb-hop is in native_libraries.html; it reads --bb-mascot.
  Art.installMascot = function () {
    var url = Art.mascotURL('none');
    if (url) document.documentElement.style.setProperty('--bb-mascot', 'url("' + url + '")');
  };
  Art.installMascot();

  // Renders a whole level to a small preview canvas (editor list + level cards).
  Art.levelThumb = function (data, theme, w) {
    var s = Math.max(2, Math.floor(w / data.w)), c = Art.canvas(data.w * s, data.h * s), th = Art.theme(theme);
    for (var y = 0; y < data.h; y++) for (var x = 0; x < data.w; x++) Art.drawTile(c.ctx, th, data.tiles, x, y, x * s, y * s, s, 0);
    (data.ents || []).forEach(function (e) {
      var col = { start: '#fff', exit: '#f4b63c', item: '#e0483a', pest: '#2b1b2e', nest: '#8e44ad', npc: '#3d8fd1', pickup: '#f4b63c' }[e.t];
      circle(c.ctx, e.x * s + s / 2, e.y * s + s / 2, Math.max(1.5, s * 0.38), col, INK, 1);
    });
    return c.el;
  };
})();
