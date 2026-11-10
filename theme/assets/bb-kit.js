/* bb-kit.js: Busy Bun's small browser helpers (window.BB: store, esc, fmtTime, today, isTouch, toast, modal)
   and BB.Sound (synth sound effects + music moods, ArkMusic tracks when they load). Used by the engines
   (bb-art.js, bb-engine.js, bb-stage.js, bb-builder.js) and by Python through client_code/bun.py. */
(function () {
  'use strict';
  var BB = window.BB = window.BB || {};
  BB.components = BB.components || {};

  /* ---------- Python ⇄ JS bridge ----------
     Python mounts a component with window.BB.mount(name, rootNode, jsonString, emit).
     The component calls emit(event, payload) and gets a Promise of whatever Python returned
     (bb_ui sends it back as a JSON string; we parse it here). */
  BB.wrapEmit = function (emit) {
    return function (name, payload) {
      var r;
      try { r = emit ? emit(name, JSON.stringify(payload == null ? {} : payload)) : null; }
      catch (e) { console.error(e); return Promise.reject(e); }
      return Promise.resolve(r).then(function (v) {
        if (typeof v === 'string') { try { return JSON.parse(v); } catch (e) { return v; } }
        return v;
      });
    };
  };
  BB.define = function (name, mountFn) { BB.components[name] = mountFn; };
  BB.mount = function (name, root, json, emit) {
    var fn = BB.components[name];
    if (!fn) { console.error('BB component not loaded: ' + name); return null; }
    if (!root) { console.error('BB mount: no root node for ' + name); return null; }
    var data = typeof json === 'string' ? JSON.parse(json || '{}') : (json || {});
    return fn(root, data, BB.wrapEmit(emit));
  };

  /* ---------- small helpers ---------- */
  BB.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  BB.store = {
    get: function (k, dflt) { try { var v = localStorage.getItem(k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
    del: function (k) { try { localStorage.removeItem(k); } catch (e) {} }
  };
  BB.today = function () {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  };
  BB.fmtTime = function (s) {
    if (s == null) return '–';
    s = Math.max(0, s);
    var m = Math.floor(s / 60), r = s - m * 60;
    return (m ? m + ':' + (r < 10 ? '0' : '') + r.toFixed(1) : r.toFixed(1) + 's');
  };
  BB.isTouch = function () { return ('ontouchstart' in window) || navigator.maxTouchPoints > 0; };

  BB.toast = function (msg, kind) {
    var box = document.querySelector('.bb-toasts');
    if (!box) { box = document.createElement('div'); box.className = 'bb bb-toasts'; document.body.appendChild(box); }
    var t = document.createElement('div');
    t.className = 'bb-toast' + (kind === true || kind === 'err' ? ' err' : kind === 'gold' ? ' gold' : '');
    t.innerHTML = msg;
    box.appendChild(t);
    setTimeout(function () { t.style.transition = 'opacity .3s, transform .3s'; t.style.opacity = '0'; t.style.transform = 'translateY(-10px)'; }, 2600);
    setTimeout(function () { t.remove(); }, 3000);
  };

  // BB.modal(html, {onClose, cls}) → {el, close}. Clicking the backdrop or × closes it.
  BB.modal = function (html, opts) {
    opts = opts || {};
    var bg = document.createElement('div');
    bg.className = 'bb bb-modal-bg';
    bg.innerHTML = '<div class="bb-card bb-modal ' + (opts.cls || '') + '">' + (opts.noClose ? '' : '<button class="bb-x" aria-label="Close">✕</button>') + html + '</div>';
    document.body.appendChild(bg);
    var closed = false;
    function close() {
      if (closed) return; closed = true;
      bg.remove();
      document.removeEventListener('keydown', onKey);
      if (opts.onClose) opts.onClose();
    }
    function onKey(e) { if (e.key === 'Escape' && !opts.noClose) close(); }
    document.addEventListener('keydown', onKey);
    bg.addEventListener('click', function (e) {
      if ((e.target === bg && !opts.noClose) || (e.target.closest && e.target.closest('.bb-x'))) { BB.Sound.play('click'); close(); }
    });
    return { el: bg.querySelector('.bb-modal'), close: close };
  };

  /* ---------- Sound: everything is synthesized, no files ---------- */
  var Sound = BB.Sound = { ctx: null, master: null, sfxOn: BB.store.get('bb.sfx', true), musicOn: BB.store.get('bb.music', true) };
  Sound.init = function () {
    if (Sound.ctx) { if (Sound.ctx.state === 'suspended') Sound.ctx.resume(); return Sound.ctx; }
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    try {
      Sound.ctx = new AC();
      Sound.master = Sound.ctx.createGain(); Sound.master.gain.value = 0.5; Sound.master.connect(Sound.ctx.destination);
      Sound.musicGain = Sound.ctx.createGain(); Sound.musicGain.gain.value = 0.16; Sound.musicGain.connect(Sound.master);
    } catch (e) { Sound.ctx = null; }
    return Sound.ctx;
  };
  ['pointerdown', 'keydown', 'touchstart'].forEach(function (ev) {
    window.addEventListener(ev, function () { Sound.init(); if (Sound.wantMusic && Sound.musicOn) Sound.startMusic(Sound.wantMusic); }, { passive: true });
  });
  function tone(freq, start, dur, type, vol, slideTo, dest) {
    var c = Sound.ctx, o = c.createOscillator(), g = c.createGain();
    o.type = type || 'square';
    o.frequency.setValueAtTime(freq, start);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, start + dur);
    g.gain.setValueAtTime(0.0001, start);
    g.gain.exponentialRampToValueAtTime(vol || 0.2, start + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
    o.connect(g); g.connect(dest || Sound.master);
    o.start(start); o.stop(start + dur + 0.05);
  }
  function noise(start, dur, vol, filterFreq, type) {
    var c = Sound.ctx, n = Math.floor(c.sampleRate * dur), buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
    var src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    src.buffer = buf; f.type = type || 'lowpass'; f.frequency.value = filterFreq || 1200;
    g.gain.setValueAtTime(vol || 0.2, start); g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
    src.connect(f); f.connect(g); g.connect(Sound.master); src.start(start);
  }
  var SFX = {
    click: function (t) { tone(660, t, 0.06, 'triangle', 0.15); },
    pickup: function (t) { tone(660, t, 0.07, 'square', 0.09); tone(990, t + 0.06, 0.09, 'square', 0.09); },
    meat: function (t) { tone(520, t, 0.06, 'square', 0.1); tone(780, t + 0.05, 0.06, 'square', 0.1); tone(1040, t + 0.1, 0.1, 'triangle', 0.12); },
    coin: function (t) { tone(1320, t, 0.05, 'square', 0.07); tone(1760, t + 0.05, 0.12, 'square', 0.07); },
    dash: function (t) { noise(t, 0.22, 0.25, 2400, 'bandpass'); tone(300, t, 0.15, 'sine', 0.08, 700); },
    bonk: function (t) { tone(220, t, 0.12, 'square', 0.15, 90); noise(t, 0.08, 0.15, 900); },
    crate: function (t) { noise(t, 0.18, 0.3, 700); tone(140, t, 0.12, 'triangle', 0.15, 60); },
    hurt: function (t) { tone(400, t, 0.25, 'sawtooth', 0.12, 120); },
    nest: function (t) { noise(t, 0.35, 0.35, 500); tone(180, t, 0.3, 'square', 0.12, 50); },
    clear: function (t) { [523, 659, 784, 1047, 1319].forEach(function (f, i) { tone(f, t + i * 0.07, 0.18, 'triangle', 0.12); }); },
    errand: function (t) { [659, 784, 988].forEach(function (f, i) { tone(f, t + i * 0.08, 0.14, 'triangle', 0.14); }); },
    talk: function (t) { tone(500 + Math.random() * 200, t, 0.05, 'triangle', 0.06); },
    unlock: function (t) { tone(392, t, 0.1, 'square', 0.1); tone(523, t + 0.1, 0.1, 'square', 0.1); tone(784, t + 0.2, 0.25, 'triangle', 0.14); },
    win: function (t) { [523, 659, 784, 659, 784, 1047].forEach(function (f, i) { tone(f, t + i * 0.11, i === 5 ? 0.5 : 0.14, 'square', 0.1); }); },
    fail: function (t) { [392, 349, 311, 262].forEach(function (f, i) { tone(f, t + i * 0.16, 0.2, 'triangle', 0.14); }); },
    cook: function (t) { noise(t, 0.9, 0.12, 3000, 'highpass'); [523, 659, 784, 1047].forEach(function (f, i) { tone(f, t + 0.4 + i * 0.09, 0.2, 'triangle', 0.12); }); },
    star: function (t) { tone(1047, t, 0.09, 'square', 0.08); tone(1568, t + 0.08, 0.2, 'triangle', 0.1); },
    steam: function (t) { noise(t, 0.5, 0.15, 3500, 'highpass'); },
    boss: function (t) { tone(110, t, 0.5, 'sawtooth', 0.15, 55); noise(t, 0.4, 0.2, 400); },
    squawk: function (t) { tone(900, t, 0.12, 'sawtooth', 0.08, 500); tone(800, t + 0.12, 0.1, 'sawtooth', 0.07, 450); }
  };
  /* Haptics (phones that support vibration, i.e. Android): a short buzz on the moments that matter, never on the
     frequent ones (coins, pickups, footsteps). Its own switch in Settings (bb.haptics), independent of sound. */
  var HAPTIC = { bonk: 12, crate: 15, hurt: 40, nest: [20, 30, 40], boss: [60, 40, 60], errand: 15, unlock: [15, 40, 25],
    clear: [15, 40, 15], star: 10, cook: [10, 30, 10, 30, 20], win: [20, 60, 20, 60, 40], fail: 80 };
  BB.canVibrate = !!(navigator.vibrate);
  Sound.hapticsOn = BB.store.get('bb.haptics', true);
  Sound.setHaptics = function (on) { Sound.hapticsOn = !!on; BB.store.set('bb.haptics', Sound.hapticsOn); if (on) BB.haptic(20); };
  BB.haptic = function (pattern) {
    if (!Sound.hapticsOn || !BB.canVibrate || document.visibilityState === 'hidden') return;
    try { navigator.vibrate(pattern); } catch (e) {}
  };
  Sound.play = function (name) {
    if (HAPTIC[name]) BB.haptic(HAPTIC[name]);
    if (!Sound.sfxOn || !Sound.init() || !SFX[name]) return;
    try { SFX[name](Sound.ctx.currentTime + 0.005); } catch (e) {}
  };
  Sound.setSfx = function (on) { Sound.sfxOn = !!on; BB.store.set('bb.sfx', Sound.sfxOn); };
  Sound.setMusic = function (on) {
    Sound.musicOn = !!on; BB.store.set('bb.music', Sound.musicOn);
    if (on && Sound.wantMusic) Sound.startMusic(Sound.wantMusic); else Sound.stopMusic(true);
  };

  /* A tiny generative tune: pentatonic melody over a bass line, different per mood. */
  var MOODS = {
    menu: { bpm: 104, root: 60, scale: [0, 2, 4, 7, 9], wave: 'triangle', bass: [0, -5, -3, -7] },
    kitchen: { bpm: 112, root: 62, scale: [0, 2, 4, 7, 9], wave: 'triangle', bass: [0, -3, -5, -7] },
    market: { bpm: 96, root: 57, scale: [0, 3, 5, 7, 10], wave: 'square', bass: [0, -2, -4, -5] },
    dimsum: { bpm: 108, root: 64, scale: [0, 2, 4, 7, 9], wave: 'triangle', bass: [0, -5, -3, -8] },
    spice: { bpm: 122, root: 59, scale: [0, 1, 5, 7, 8], wave: 'square', bass: [0, -4, -2, -5] },
    harbour: { bpm: 92, root: 60, scale: [0, 2, 5, 7, 9], wave: 'sine', bass: [0, -5, -7, -3] },
    banquet: { bpm: 116, root: 55, scale: [0, 2, 4, 7, 9], wave: 'square', bass: [0, -3, -7, -5] },
    noodle: { bpm: 118, root: 60, scale: [0, 2, 5, 7, 9], wave: 'square', bass: [0, -5, -2, -7] },
    bakery: { bpm: 110, root: 65, scale: [0, 2, 4, 7, 9], wave: 'triangle', bass: [0, -4, -5, -7] },
    garden: { bpm: 88, root: 62, scale: [0, 2, 4, 7, 9], wave: 'sine', bass: [0, -5, -3, -7] },
    lake: { bpm: 84, root: 57, scale: [0, 2, 5, 7, 10], wave: 'sine', bass: [0, -7, -5, -3] },
    terrace: { bpm: 100, root: 59, scale: [0, 2, 4, 7, 9], wave: 'triangle', bass: [0, -3, -5, -2] },
    cellar: { bpm: 90, root: 52, scale: [0, 3, 5, 7, 10], wave: 'triangle', bass: [0, -2, -5, -4] },
    orchard: { bpm: 124, root: 64, scale: [0, 2, 4, 7, 9], wave: 'square', bass: [0, -5, -3, -8] },
    frost: { bpm: 96, root: 69, scale: [0, 2, 4, 7, 11], wave: 'sine', bass: [0, -5, -7, -4] },
    festival: { bpm: 126, root: 58, scale: [0, 2, 4, 7, 9], wave: 'square', bass: [0, -3, -5, -7] },
    dragon: { bpm: 132, root: 53, scale: [0, 1, 5, 7, 8], wave: 'sawtooth', bass: [0, -4, -2, -5] }
  };
  /* Real music: Audiio tracks streamed by ArkMusic (the ark-music block above). The synth tune is the fallback
     when the files can't load. Track list: APP_MAKER/media/manifest.json. */
  var TRACKS = {
    menu: ['dont-stress-out'], upbeat: ['dont-stress-out', 'my-love-for-you'], calm: ['bright-road', 'toulouse'],
    cellar: ['spiralis'], dragon: ['dark-terrain']
  };
  var MOOD_TRACKS = { menu: 'menu', garden: 'calm', lake: 'calm', harbour: 'calm', frost: 'calm', terrace: 'calm', cellar: 'cellar', dragon: 'dragon' };
  Sound.tracksFor = function (mood) { return TRACKS[MOOD_TRACKS[mood] || 'upbeat']; };
  Sound.useFiles = !!window.ArkMusic;
  if (window.ArkMusic) ArkMusic.onfail(function () {
    Sound.useFiles = false; Sound.music = null;
    if (Sound.wantMusic && Sound.musicOn) Sound.startMusic(Sound.wantMusic);
  });
  Sound.startMusic = function (mood) {
    Sound.wantMusic = mood;
    if (Sound.useFiles) {
      if (!Sound.musicOn) return;
      var list = Sound.tracksFor(mood);
      ArkMusic.play(list, { volume: 0.35, shuffle: list.length > 1 });
      Sound.music = { mood: mood, file: true };
      return;
    }
    if (!Sound.musicOn || !Sound.ctx || Sound.ctx.state !== 'running') return;
    if (Sound.music && Sound.music.mood === mood) return;
    Sound.stopMusic();
    var m = MOODS[mood] || MOODS.menu, beat = 60 / m.bpm / 2, next = Sound.ctx.currentTime + 0.1, step = 0, deg = 2;
    var timer = setInterval(function () {
      var c = Sound.ctx;
      if (!c) return;
      while (next < c.currentTime + 0.4) {
        var bar = Math.floor(step / 16) % 4;
        if (step % 4 === 0) tone(440 * Math.pow(2, (m.root - 24 + m.bass[bar] - 69) / 12), next, beat * 3.6, 'triangle', 0.22, null, Sound.musicGain);
        if (Math.random() < (step % 2 ? 0.45 : 0.8)) {
          deg = Math.max(0, Math.min(9, deg + [-2, -1, -1, 0, 1, 1, 2][Math.floor(Math.random() * 7)]));
          var semi = m.scale[deg % 5] + 12 * Math.floor(deg / 5);
          tone(440 * Math.pow(2, (m.root + semi - 69) / 12), next, beat * (Math.random() < 0.2 ? 1.8 : 0.9), m.wave, 0.09, null, Sound.musicGain);
        }
        if (step % 8 === 4) noise(next, 0.05, 0.05, 6000, 'highpass');
        next += beat; step++;
      }
    }, 120);
    Sound.music = { mood: mood, timer: timer };
  };
  Sound.stopMusic = function (forget) {
    if (Sound.music && Sound.music.file) { if (window.ArkMusic) ArkMusic.stop(); Sound.music = null; }
    if (Sound.music) { clearInterval(Sound.music.timer); Sound.music = null; }
    if (forget) Sound.wantMusic = Sound.wantMusic;
  };
})();
