/* Smoke test (tools/ui_test.py runs it at 1280 px and at 390 px): every page address opens without errors, is not
   empty and doesn't scroll sideways. Signed out (title, the five hub tabs as a guest, a level, the builder's sign-in
   card, the main dialogs), then as a new player (sign up through the dialog, every tab, a level's intro, settings),
   then as admin (ADMIN_EMAILS in Game.py: every builder tab). Python/JS errors are caught by ui_test.py from the
   browser log. Resolves to {ok, log}. */
(async function () {
  const log = [], bad = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 20000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const errs = [];
  window.addEventListener('error', (e) => errs.push(String(e.message || e)));
  const visible = (el) => !!el && el.getClientRects().length > 0;
  function type(input, value) {
    input.focus(); input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function button(re, root) { return $$((root || '') + ' button, ' + (root || '') + ' a').find((b) => re.test(b.textContent.trim()) && visible(b)); }
  const modal = () => $$('.modal, .anvil-modal').find((m) => visible(m) && m.innerText.trim().length > 5);
  function dbutton(re, sel) {  // a button inside the open dialog (optionally inside sel)
    const m = modal(); if (!m) return null;
    return Array.from(m.querySelectorAll((sel ? sel + ' ' : '') + 'button')).find((b) => re.test(b.textContent.trim()) && visible(b));
  }
  function check(name, expect) {
    const roots = $$('.bb').filter(visible);
    const text = roots.map((r) => r.innerText).join(' ').trim();
    const w = document.documentElement.scrollWidth, vw = screen.width <= 500 ? screen.width : window.innerWidth;
    const problems = [];
    if (text.length < 40) problems.push('empty page');
    if (expect && !new RegExp(expect.source, 'i').test(text)) problems.push('missing ' + expect);
    if (w > vw + 1) {
      const wide = $$('body *').filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 1; })
        .slice(0, 3).map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ').slice(0, 2).join('.'));
      problems.push('scrolls sideways (' + w + ' > ' + vw + ') ' + wide.join(' '));
    }
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push(name + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + name);
  }
  async function open(hash, expect) {
    if ((location.hash || '#') !== hash) window.UI_READY = false;
    location.hash = hash;
    await until(() => window.UI_READY && (location.hash || '#') === hash, hash, 40000);
    await sleep(800);
    check(hash, expect);
  }
  async function dialog(name, opener, expect, closeRe) {
    if (!opener) { bad.push('no opener for dialog ' + name); return; }
    opener.click();
    const dlg = await until(modal, 'dialog ' + name, 20000);
    await sleep(500);
    const problems = [];
    if (expect && !expect.test(dlg.innerText)) problems.push('missing ' + expect);
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push('dialog ' + name + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + 'dialog ' + name);
    const close = dbutton(closeRe || /^(✕|Got it!|Back to map)$/);
    if (close) close.click(); else document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27, bubbles: true }));
    await until(() => !modal(), 'dialog closed', 10000);
    await sleep(300);
  }
  async function hubTabs(tag) {
    await open('#journey', /The Journey/);
    await open('#pantry', /The Pantry/);
    await open('#kitchen', /Grandma's Kitchen/);
    await open('#shop', /Market stall/);
    await open('#badges', /Your stats/);
    await open('#journey', /The Journey/);
    await dialog('level intro (' + tag + ')', button(/▶ Play/, '.g-continue'), /Hop into the bamboo steamer/);
    await dialog('settings (' + tag + ')', $('.g-top .g-av'), /Settings/);
    await dialog('daily box (' + tag + ')', $('.g-top [aria-label="Daily market box"]'), /market box|Opened today/);
  }
  async function playLevel(key) {
    window.UI_READY = false;
    location.hash = '#play/' + key;
    const dlg = await until(() => { const m = modal(); return m && /Let's roll/.test(m.innerText) && m; }, 'the start card', 40000);
    await sleep(400);
    const go = dbutton(/Let's roll/);
    go.click();
    await until(() => !modal(), 'start card closed');
    await sleep(1500);
    const cv = $('.g-stage canvas.g-cv');
    const problems = [];
    if (!cv || !visible(cv)) problems.push('no game canvas');
    if (!$('.g-timer') || !/par/.test($('.g-timer').textContent)) problems.push('no heads-up display');
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push('#play/' + key + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + '#play/' + key + ' (running)');
    await dialog('pause', $('.g-hud [data-a="pause"]'), /Paused/, /Quit to map/);
    await until(() => location.hash === '#journey' && window.UI_READY, 'back on the map', 30000);
    await sleep(500);
    check('#journey (after quitting)', /The Journey/);
  }
  async function signUp(name, email, password) {
    await open('#', /Busy Bun/);
    button(/Sign in \/ Create account/).click();
    await until(modal, 'the sign-in dialog');
    await sleep(400);
    dbutton(/^Create an account$/).click();
    await sleep(400);
    const m = modal();
    const inputs = Array.from(m.querySelectorAll('input')).filter((i) => visible(i) && i.type !== 'checkbox');
    type(inputs[0], name); type(inputs[1], email); type(inputs[2], password);
    const tick = m.querySelector('input[type=checkbox]'); if (tick && !tick.checked) tick.click();
    dbutton(/^Create account$/).click();
    const end = Date.now() + 40000;
    while (Date.now() < end) {
      if (!modal() && location.hash === '#journey' && window.UI_READY) return true;
      const msg = m.querySelector('.anvil-role-bb-err');
      if (msg && visible(msg) && msg.textContent.trim()) { log.push('sign-up said: ' + msg.textContent.trim()); return false; }
      await sleep(250);
    }
    log.push('sign-up: still on ' + location.hash);
    return false;
  }
  async function signIn(email, password) {
    const m = modal();
    if (!m) { await open('#', /Busy Bun/); button(/Sign in \/ Create account/).click(); }
    const d = await until(modal, 'the sign-in dialog');
    await sleep(300);
    const back = dbutton(/^Sign in$/, '.g-auth-links');
    if (back) { back.click(); await sleep(300); }
    type(d.querySelector('input[type=email]'), email); type(d.querySelector('input[type=password]'), password);
    dbutton(/^Sign in$/, '.anvil-role-block').click();
    await until(() => !modal() && location.hash === '#journey' && window.UI_READY, 'signed in as ' + email, 40000);
  }
  async function signOut() {
    await open('#', /Busy Bun/);
    const b = button(/^Sign out$/);
    if (b) b.click();
    await until(() => button(/Sign in \/ Create account/) && window.UI_READY, 'signed out');
    await sleep(400);
  }
  try {
    // ---- signed out: the title, the guest's hub, a level, the builder's door
    await open('#', /Play now|Continue as guest/);
    await dialog('how to play', button(/^How to play$/), /Steam Dash/);
    await hubTabs('guest');
    await playLevel('kitchen-1');
    await open('#admin', /Admins only/);

    // ---- a new player
    const pw = 'Bb-' + Math.random().toString(36).slice(2) + '-Kq7';
    if (!(await signUp('Smoke Bun', 'smoke' + Date.now() + '@example.com', pw))) throw new Error('sign-up failed');
    check('#journey (signed up)', /The Journey/);
    await hubTabs('member');
    await open('#admin', /isn't an admin account/);
    await signOut();

    // ---- admin: sign up the first time, sign in after that
    const adminPw = 'Bb-smoke-adm-93Kx-7q';
    if (!(await signUp('Admin Bun', 'arkulinskis@gmail.com', adminPw))) await signIn('arkulinskis@gmail.com', adminPw);
    await open('#admin', /Level Builder/);
    await until(() => $('.a-tools') && $('.a-canvas canvas'), 'the level editor', 40000);
    check('#admin levels', /Playtest/);
    for (const [tab, re] of [['territories', /Restore missing built-ins/], ['players', /Last played/], ['feedback', /Feedback & bug reports/], ['levels', /Playtest/]]) {
      $('.a-top [data-tab="' + tab + '"]').click();
      await sleep(tab === 'levels' ? 2500 : 1800);
      await until(() => window.UI_READY, tab);
      check('#admin ' + tab, re);
    }
    await signOut();
    log.push(bad.length ? 'PROBLEMS: ' + bad.join(' | ') : 'PASSED');
    return { ok: !bad.length, log: log };
  } catch (e) {
    log.push(String(e && e.message || e));
    if (bad.length) log.push('PROBLEMS: ' + bad.join(' | '));
    return { ok: false, log: log };
  }
})();
