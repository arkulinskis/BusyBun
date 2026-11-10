"""Busy Bun's game state in the browser, offline play and sync, and small bridges to the JavaScript engines
(theme/assets: bb-kit.js = window.BB helpers + Sound, bb-art.js = drawing, bb-engine.js = the game, bb-stage.js,
bb-store.js = the saves on this device).

    bun.ensure()            open the game for whoever is here (signed out = the guest on this device)
    bun.act(name, *args)    a progress-changing action ("finish_level", "cook", "buy_hat", ...): scored right here by the
                            shared rules (rules.py), saved on the device, then synced when online
    bun.sync_now()          send what changed since the last sync (signed-in players); the server adds it on top
    bun.st                  {me, progress, status, journey, catalog, market, daily_ready, today, guest, online, ...}
    bun.sfx("coin")         a sound effect; bun.music("menu") the background music for a mood

Offline: every account that played on this device keeps its own save (IndexedDB "acct:<key>"): its progress, the copy
the server last confirmed (base), levels won since (for the leaderboards) and an unfinished sync. Back online,
rules.diff(base, progress) goes to the server's sync(), which adds it to the account (plays, coins and items add up).
"""
import json

import anvil.js
import anvil.server
from anvil import alert
from anvil.js import window

from . import rules as R
from . import state

GUEST_KEY = "bb.guest.v1"  # the old guest save (localStorage); moved into the device store on first load
RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "legendary": 3}
BOSS_NAMES = {"king": "the Rat King", "queen": "the Wasp Queen"}
PEST_EMOJI = {"ant": "🐜", "rat": "🐀", "fly": "🪰", "roach": "🪳", "gull": "🐦", "king": "👑", "snail": "🐌",
              "mould": "🦠", "frog": "🐸", "weevil": "🪲", "spider": "🕷️", "wasp": "🐝", "queen": "👑"}
DARK_THEMES = ("market", "banquet", "cellar", "festival", "dragon")
YT_VIDEO = "mFIuuENN_nI"  # the Busy Bun video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json)
GUEST_ME = {"name": "Guest Bun", "email": None, "is_admin": False, "guest": True}
RETRY_MS = 20000  # while offline, check for the server this often

st: dict = {"loaded": False, "guest": False, "me": None, "progress": None, "status": None, "journey": [],
            "catalog": None, "market": [], "daily_ready": False, "today": None, "world": None, "focus": None,
            "online": True, "acct": None, "base": None, "finishes": [], "sync_id": None, "sent": None, "sent_fin": [],
            "syncing": False, "world_loaded": False}
_ix: dict = {"items": {}, "recipes": {}, "hats": {}, "badges": {}, "levels": [], "where": None}
_hooks: dict = {"change": None, "timer": None}


# ---------------------------------------------------------------- browser storage (JSON, the old keys)
def get(key, default=None):
    try:
        raw = window.localStorage.getItem(key)
    except Exception:
        return default
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def put(key, value):
    try:
        window.localStorage.setItem(key, json.dumps(value))
    except Exception:
        pass


def drop(key):
    try:
        window.localStorage.removeItem(key)
    except Exception:
        pass


def today():
    return str(window.BB.today())


def js(value):
    """A Python dict/list as a plain JavaScript object (engines get real JS objects, not proxies)."""
    return window.JSON.parse(json.dumps(value))


def _copy(value):
    return json.loads(json.dumps(value))


# ---------------------------------------------------------------- the saves on this device (bb-store.js)
def _load(key):
    try:
        raw = window.BBStore.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        print("device store: could not read %s: %r" % (key, e))
        return None


def _keep(key, value):
    try:
        window.BBStore.set(key, json.dumps(value))
    except Exception as e:
        print("device store: could not save %s: %r" % (key, e))


def _acct_key(me):
    email = (me or {}).get("email")
    return "u:" + str(email).strip().lower() if email else "guest"


def _save():
    """Write the open account's save (and who's playing) to the device."""
    if not st["acct"]:
        return
    _keep("acct:" + st["acct"], {"me": st["me"], "progress": st["progress"], "base": st["base"], "finishes": st["finishes"],
                                 "sync_id": st["sync_id"], "sent": st["sent"], "sent_fin": st["sent_fin"],
                                 "asked": st.get("asked") or {}})
    _keep("current", {"acct": st["acct"], "me": None if st["guest"] else st["me"]})


def cached_me():
    """Offline start: who played last on this device, in admin_whoami's shape (None = the guest)."""
    cur = _load("current") or {}
    me = cur.get("me")
    if not me or not me.get("email"):
        return None
    return {"signed_in": True, "email": me["email"], "name": me.get("name") or "Bun", "is_admin": bool(me.get("is_admin"))}


# ---------------------------------------------------------------- server and the network
def online():
    return bool(st["online"])


def pending():
    """Signed-in play not on the server yet."""
    if st["guest"] or not st["loaded"]:
        return False
    return bool(st["sync_id"] or st["finishes"] or not R.is_empty(R.diff(st["base"] or R.new_progress(), st["progress"])))


def listen(fn):
    """The hub's top bar redraws its online/sync pill through this."""
    _hooks["change"] = fn


def _changed():
    fn = _hooks["change"]
    if fn:
        try:
            fn()
        except Exception as e:
            print("top bar refresh failed: %r" % (e,))


def set_online(flag):
    flag = bool(flag)
    was = st["online"]
    st["online"] = flag
    if not flag and _hooks["timer"] is None:
        _hooks["timer"] = window.setInterval(_retry, RETRY_MS)
    if flag and _hooks["timer"] is not None:
        window.clearInterval(_hooks["timer"])
        _hooks["timer"] = None
    if was != flag:
        _changed()


def _offline_error(e):
    return type(e).__name__ in ("AppOfflineError", "TimeoutError")


def _try(fn, *args):
    """A quiet server call: (True, reply) or (False, None). Notices when the game goes offline or comes back.
    A session that expired while the game ran offline is replaced (a remembered sign-in comes back with it)."""
    for attempt in (1, 2):
        try:
            r = anvil.server.call_s(fn, *args)
        except Exception as e:
            if type(e).__name__ == "SessionExpiredError" and attempt == 1:
                try:
                    anvil.server.reset_session()
                    continue
                except Exception:
                    pass
            if _offline_error(e):
                set_online(False)
            else:
                print("server call %s failed: %r" % (fn, e))
            return False, None
        set_online(True)
        return True, r
    return False, None


def call(fn, *args):
    """anvil.server.call that turns failures into {"ok": False, "error": ...} like the old game did."""
    try:
        r = anvil.server.call(fn, *args)
        set_online(True)
        return r
    except Exception as e:
        kind = type(e).__name__
        if kind == "PermissionDenied":
            return {"ok": False, "error": str(e) or "You don't have access to that."}
        if kind == "SessionExpiredError":
            return {"ok": False, "error": "Your session expired. Reload the page and sign in again."}
        if _offline_error(e):
            set_online(False)
            return {"ok": False, "error": "You're offline. This needs the internet; your game itself keeps working."}
        print("server call %s failed: %r" % (fn, e))
        return {"ok": False, "error": "Something went wrong in the kitchen. Please try again."}


def _retry():
    """Offline: every RETRY_MS (and when the phone says the network is back) check for the server, then sync."""
    if st["syncing"]:
        return
    ok, who = _try("admin_whoami")
    if not ok:
        return
    who = who or {}
    me = who if who.get("signed_in") else None
    if _acct_key(me) != (st["acct"] or _acct_key(state.me())):
        # Signed out (or in as someone else) elsewhere while this device was offline: this save stays on the device
        # and syncs the next time that account signs in here.
        had = pending()
        state.set_me(me)
        st["loaded"] = False
        if had:
            toast("☁️ Sign in again to add the play saved on this device to your account.", "gold")
        try:
            from . import router
            router.show()
        except Exception as e:
            print("redraw after reconnect failed: %r" % (e,))
        return
    if st["loaded"] and not st["guest"]:
        had = pending()
        if sync_now() and had:
            toast("☁️ Back online: your offline play is added to your account.", "gold")
    _changed()


def _on_net(is_online):
    if is_online:
        _retry()
    else:
        set_online(False)


try:
    window.BBStore.onNet = _on_net
except Exception:
    pass


# ---------------------------------------------------------------- the journey (every level) and the catalog
def _index():
    c = st["catalog"] or {}
    _ix["items"] = {i["key"]: i for i in c.get("items", [])}
    _ix["recipes"] = {r["key"]: r for r in c.get("recipes", [])}
    _ix["hats"] = {h["key"]: h for h in c.get("hats", [])}
    _ix["badges"] = {b["key"]: b for b in c.get("badges", [])}


def _set_world(journey, catalog):
    st["catalog"] = catalog
    _index()
    st["journey"] = journey
    _ix["levels"] = [(t, lv) for t in st["journey"] for lv in t["levels"]]
    _ix["where"] = None


def _load_world():
    """From the server when online (and kept on the device), otherwise the copy on the device."""
    if st["online"]:
        ok, r = _try("get_world", today())
        if ok and r and r.get("ok"):
            _set_world(r["journey"], r["catalog"])
            _keep("world", {"journey": r["journey"], "catalog": r["catalog"]})
            return True
    w = _load("world")
    if w and w.get("journey"):
        _set_world(w["journey"], w["catalog"])
        return True
    return False


def _view():
    """Everything the screens read, worked out here from the progress (no server needed)."""
    d = R.day(today()) or R.day("2026-01-01")
    v = R.view(st["progress"], st["journey"], d)
    for k in ("status", "market", "daily_ready", "today"):
        st[k] = v[k]
    found = set(st["progress"].get("postcards") or [])
    for t in st["journey"]:
        t["postcard"] = (t.get("_postcard") or t.get("postcard")) if t["key"] in found else None
    put("bb.lastHat", st["progress"].get("hat") or "none")


# ---------------------------------------------------------------- accounts on this device
def _open(acct, me):
    """Make `acct` the open save: its progress from the device (the old guest save moves in on first use)."""
    rec = _load("acct:" + acct) or {}
    st["acct"], st["guest"] = acct, acct == "guest"
    st["me"] = GUEST_ME if st["guest"] else (rec.get("me") or me or GUEST_ME)
    if me and not st["guest"]:
        st["me"] = dict(st["me"], name=me.get("name") or st["me"].get("name"), email=me.get("email"),
                        is_admin=bool(me.get("is_admin")), guest=False)
    prog = rec.get("progress")
    if prog is None and st["guest"]:
        prog = get(GUEST_KEY)
    st["progress"] = R.normalize(prog)
    st["base"] = rec.get("base")
    st["finishes"] = rec.get("finishes") or []
    st["sync_id"], st["sent"], st["sent_fin"] = rec.get("sync_id"), rec.get("sent"), rec.get("sent_fin") or []
    st["asked"] = rec.get("asked") or {}
    _view()
    _save()
    if st["guest"]:
        drop(GUEST_KEY)


def apply(r):
    """A reply from the server outside the sync (set_name): take the new name, keep this device's progress."""
    if r and r.get("me") and not st["guest"]:
        st["me"] = r["me"]
        _save()


def reset():
    """Forget the open save (after signing in or out); the next ensure() opens the right one."""
    st["loaded"] = False


def ensure(force=False):
    """Open the game for whoever is here now. False (with a toast) if it can't (offline before the first download)."""
    me = state.me()
    acct = _acct_key(me)
    if st["loaded"] and st["acct"] == acct and not force:
        return True
    if force or not st["world_loaded"]:
        if not _load_world():
            state.toast("Busy Bun needs the internet once to download its levels. Connect and try again.", "error")
            return False
        st["world_loaded"] = True
    _open(acct, me)
    st["loaded"] = True
    if not st["guest"] and st["online"]:
        sync_now()
    _changed()
    return True


def sync_now(quiet=True):
    """Signed in: send what changed since the last sync; the server adds it to the account and sends the account
    back. Play that happens during the call is kept and goes with the next sync. True when the device is up to date."""
    if st["guest"] or not st["loaded"] or st["syncing"] or not st["online"]:
        return False
    st["syncing"] = True
    _changed()
    try:
        for _round in range(3):
            base = st["base"] or R.new_progress()
            if not st["sync_id"]:
                sent = _copy(st["progress"])
                if R.is_empty(R.diff(base, sent)) and not st["finishes"] and st["base"] is not None:
                    ok, r = _try("get_state", today())  # nothing to send: just pick up play from other devices
                    if not ok or not r or not r.get("ok"):
                        return False
                    _adopt(r, sent)
                    return True
                st["sync_id"], st["sent"], st["sent_fin"], st["finishes"] = _new_id(), sent, st["finishes"], []
                _save()
            ok, r = _try("sync", R.diff(base, st["sent"]), st["sync_id"], st["sent_fin"], today())
            if not ok or not r or not r.get("ok"):
                return False
            _adopt(r, st["sent"])
            if not pending():
                return True
        return False
    finally:
        st["syncing"] = False
        _changed()


def _adopt(r, sent):
    """The account as the server has it, plus anything played on this device since `sent` was taken."""
    extra = R.diff(sent, st["progress"])
    st["base"] = R.normalize(r["progress"])
    st["progress"] = R.normalize(r["progress"]) if R.is_empty(extra) else R.merge(r["progress"], extra)
    if not R.is_empty(extra):
        R.check_badges(st["progress"], st["journey"], R.day(today()) or R.day("2026-01-01"))
    if r.get("me"):
        st["me"] = r["me"]
    st["sync_id"], st["sent"], st["sent_fin"] = None, None, []
    _view()
    _save()


def _new_id():
    try:
        return str(window.crypto.randomUUID())
    except Exception:
        return "%x-%x" % (int(window.Date.now()), int(window.Math.random() * 1e15))


def act(name, *args):
    """A progress-changing action, scored right here with the shared rules (works offline), saved on the device,
    then synced if online. Returns {"ok", "report", ...} like the server used to, or {"ok": False, "error"}."""
    if not ensure():
        return {"ok": False, "error": "The game isn't loaded."}
    d = R.day(today()) or R.day("2026-01-01")
    jr = st["journey"]
    p = R.normalize(st["progress"])
    try:
        if name == "finish_level":
            p, rep = R.apply_finish(p, R.level_of(args[0], jr), jr, args[1], d)
        elif name == "cook":
            p, rep = R.apply_cook(p, args[0], jr, d)
        elif name == "buy_hat":
            p, rep = R.apply_buy_hat(p, args[0], jr, d)
        elif name == "wear_hat":
            p, rep = R.apply_wear(p, args[0])
        elif name == "buy_market":
            p, rep = R.apply_market(p, args[0], jr, d)
        elif name == "claim_daily":
            p, rep = R.apply_daily(p, jr, d)
        else:
            raise R.GameError("Unknown action.")
    except R.GameError as e:
        state.toast(str(e) or "That didn't work.", "error")
        return {"ok": False, "error": str(e)}
    st["progress"] = p
    if name == "finish_level" and not st["guest"]:
        st["finishes"].append({"level": args[0], "time": rep["time"]})
    _view()
    _save()
    if not st["guest"] and st["online"] and name != "finish_level":
        window.setTimeout(_background_sync, 0)  # the results show at once; the sync follows
    _changed()
    return {"ok": True, "report": rep, "progress": st["progress"], "status": st["status"]}


def _background_sync():
    sync_now()


def leaderboard(level_key, after_win=False):
    """A level's leaderboard. After a win: sync first, so the new time is on it. Offline: a note instead."""
    if after_win and not st["guest"]:
        sync_now()
    if st["online"]:
        ok, b = _try("leaderboard", level_key)
        if ok and b is not None:
            return b
    return {"top": [], "you": None, "total": 0, "offline": True}


def _has_progress(p):
    return bool(p and ((p.get("stats") or {}).get("runs") or p.get("coins") or p.get("cooked") or p.get("pantry")))


def after_sign_in(is_new=False):
    """Signed in: open the account's save on this device (anything played offline before is synced, adding up),
    then offer to add the guest's progress from this device to the account."""
    guest_rec = _load("acct:guest") or {}
    guest = R.normalize(guest_rec.get("progress") if guest_rec.get("progress") is not None else get(GUEST_KEY))
    st["loaded"] = False
    if not ensure():
        return False
    runs = guest["stats"]["runs"]
    asked = (guest_rec.get("asked") or {}).get(st["acct"])
    if _has_progress(guest) and asked != runs:
        levels = len([k for k, v in guest["levels"].items() if v["stars"][0]])
        text = ("You played %d level%s as a guest on this device (%d coins, %d ingredients). Add that progress to %s?\n\n"
                "It adds up: levels you also played on your account count as played twice."
                % (levels, "" if levels == 1 else "s", guest["coins"], sum(guest["pantry"].values()),
                   "your new account" if is_new else "your account"))
        yes = alert(text, title="Keep your guest progress?", buttons=[("Add it to my account", True), ("Not now", False)],
                    dismissible=False, role="app-dialog")
        if yes:
            st["progress"] = R.add_progress(st["progress"], guest)
            R.check_badges(st["progress"], st["journey"], R.day(today()) or R.day("2026-01-01"))
            _view()
            _save()
            _keep("acct:guest", {"me": None, "progress": R.new_progress(), "asked": {}})
            drop(GUEST_KEY)
            sync_now()
            toast("💾 Your guest progress is now part of your account!", "gold")
            return True
        guest_rec["asked"] = dict(guest_rec.get("asked") or {})
        guest_rec["asked"][st["acct"]] = runs
        guest_rec["progress"] = guest
        _keep("acct:guest", guest_rec)
    if is_new:
        toast("Welcome to Busy Bun, %s!" % ((st.get("me") or {}).get("name") or "bun"), "gold")
    return True


def before_sign_out():
    """Last sync before signing out; the save stays on this device either way."""
    if not st["guest"] and st["online"]:
        sync_now()


# ---------------------------------------------------------------- lookups
def item(k):
    return _ix["items"].get(k) or {"key": k, "emoji": "❔", "name": k, "rarity": "common", "cat": "pantry", "desc": ""}


def recipe(k):
    return _ix["recipes"].get(k)


def hat(k):
    return _ix["hats"].get(k) or {"key": k, "name": k}


def badge(k):
    return _ix["badges"].get(k)


def rarity(key):
    return ((st["catalog"] or {}).get("rarity") or {}).get(key) or {"name": key, "color": "#7a9a5b"}


def level_rec(key):
    return ((st["progress"] or {}).get("levels") or {}).get(key) or {"stars": [False, False, False], "best": None, "chop": False}


def stars_of(key):
    return len([s for s in level_rec(key)["stars"] if s])


def is_unlocked(key):
    return key in ((st["status"] or {}).get("unlocked") or [])


def all_levels():
    return _ix["levels"]


def find_level(key):
    """(territory, level) for a level key, or None."""
    for t, l in _ix["levels"]:
        if l["key"] == key:
            return t, l
    return None


def next_level():
    for t, l in _ix["levels"]:
        if is_unlocked(l["key"]) and not level_rec(l["key"])["stars"][0]:
            return l["key"]
    return None


def worlds():
    return [t for t in st["journey"] if t["levels"]]


def world_no(tkey):
    for i, t in enumerate(st["journey"]):
        if t["key"] == tkey:
            return i + 1
    return 0


def level_label(t, l):
    """'World 7 · Level 3': where a level sits, so nobody gets lost among 118 levels."""
    return "World %d · Level %d" % (world_no(t["key"]), t["levels"].index(l) + 1)


def world_of_level(key):
    f = find_level(key) if key else None
    return f[0]["key"] if f else None


def territory(tkey):
    for t in st["journey"]:
        if t["key"] == tkey:
            return t
    return None


def level_info(data):
    items, npcs, bosses = {}, [], []
    out = {"nests": 0, "kings": 0, "chop": False, "post": False, "knob": None, "bonus": bool(data.get("bonus"))}
    for e in data.get("ents") or []:
        t, k = e.get("t"), e.get("k")
        if t == "item":
            items[k] = items.get(k, 0) + 1
        elif t == "npc":
            npcs.append(e)
        elif t == "nest":
            out["nests"] += 1
        elif t == "pest" and k in BOSS_NAMES:
            out["kings"] += 1
            if k not in bosses:
                bosses.append(k)
        elif t == "pickup" and k == "chopsticks":
            out["chop"] = True
        elif t == "pickup" and k == "postcard":
            out["post"] = True
        elif t == "pickup" and k in ("knob", "timer"):
            out["knob"] = k
    out.update(items=items, npcs=npcs, bosses=bosses)
    return out


def goals(data, info):
    """[(emoji, text)] for a level's intro card."""
    g, out = data.get("goals") or {}, []
    if g.get("meat"):
        out.append(("🥩", "Collect %d meat" % g["meat"]))
    if g.get("errands") and info["npcs"]:
        out.append(("🤝", "Help " + " & ".join(n.get("name") or "a neighbour" for n in info["npcs"])))
    if g.get("nests") and info["nests"]:
        out.append(("💥", "Destroy %d pest nest%s" % (info["nests"], "s" if info["nests"] > 1 else "")))
    if info["kings"]:
        out.append(("👑", "Defeat " + " and ".join(BOSS_NAMES[b] for b in info["bosses"])))
    if info["knob"]:
        out.append(("⏲️", "Tip: a kitchen timer turns the stoves off for 12 seconds") if info["knob"] == "timer"
                   else ("🎛️", "Tip: an oven knob turns every hot stove off"))
    out.append(("♨️", "Hop into the bamboo steamer"))
    return out


def where_found():
    """Where each ingredient can be found (territory names), for the pantry hints."""
    if _ix["where"] is None:
        w: dict = {}
        for t in st["journey"]:
            for l in t["levels"]:
                for e in (l.get("data") or {}).get("ents") or []:
                    k = e.get("k") if e.get("t") == "item" else (e.get("gift") if e.get("t") == "npc" else None)
                    if k:
                        names = w.setdefault(k, [])
                        if t["name"] not in names:
                            names.append(t["name"])
        _ix["where"] = w
    return _ix["where"]


def can_cook(r):
    pantry = (st["progress"] or {}).get("pantry") or {}
    return all(pantry.get(k, 0) >= n for k, n in r["needs"].items())


def can_cook_any():
    return any(can_cook(r) for r in (st["catalog"] or {}).get("recipes", []))


def fmt_time(s):
    if s is None:
        return "–"
    s = max(0, float(s))
    m = int(s // 60)
    r = s - m * 60
    return ("%d:%s%.1f" % (m, "0" if r < 10 else "", r)) if m else ("%.1fs" % r)


def stars_text(stars, on="⭐", off="☆"):
    return "".join(on if s else off for s in stars)


# ---------------------------------------------------------------- sound, toasts, drawings
def sfx(name):
    try:
        window.BB.Sound.play(name)
    except Exception:
        pass


def music(mood="menu"):
    try:
        window.BB.Sound.startMusic(mood or "menu")
    except Exception:
        pass


def stop_music():
    try:
        window.BB.Sound.stopMusic()
    except Exception:
        pass


def sound_on():
    return bool(window.BB.Sound.sfxOn)


def music_on():
    return bool(window.BB.Sound.musicOn)


def can_vibrate():
    return bool(window.BB.canVibrate)


def haptics_on():
    return bool(window.BB.Sound.hapticsOn)


def set_haptics(on):
    window.BB.Sound.setHaptics(bool(on))


def dash_moved():
    """True when the player has dragged the phone Dash button somewhere (saved in this browser only)."""
    return bool(window.BB.dashMoved())


def reset_dash():
    window.BB.resetDash()


def install_offer():
    """How this browser can install the game: "prompt" (Chrome/Edge kept the install offer), "ios" (Safari on an
    iPhone/iPad: Share > Add to Home Screen), or "" (already installed, or no way to offer it)."""
    html = window.document.documentElement
    if html is not None and html.classList.contains("bb-app"):
        return ""
    if getattr(window, "bbInstall", None):
        return "prompt"
    ua = str(window.navigator.userAgent)
    ios = "iPhone" in ua or "iPad" in ua or ("Macintosh" in ua and int(window.navigator.maxTouchPoints or 0) > 1)
    return "ios" if ios else ""


def install():
    """Show the browser's install dialog (only when install_offer() is "prompt"). Returns True if they accepted."""
    ev = getattr(window, "bbInstall", None)
    if not ev:
        return False
    ev.prompt()
    choice = window.Promise.resolve(ev.userChoice)  # a promise returned by a call: Anvil waits for it
    window.bbInstall = None  # an offer can only be shown once
    return bool(choice) and choice.outcome == "accepted"


def set_sound(on):
    window.BB.Sound.setSfx(bool(on))


def set_music(on, mood="menu"):
    window.BB.Sound.setMusic(bool(on))
    if on:
        music(mood)


def toast(text, kind=None):
    """The game's little dough toast (top of the screen). kind: None, "gold" or "err"."""
    window.BB.toast(window.BB.esc(text), kind or False)


def portrait(size, hat_key=None, opts=None):
    """A canvas with the bun (wearing a hat)."""
    return window.BB.Art.bunPortrait(size, hat_key or "none", js(opts or {}))


def put_portrait(node, size, hat_key=None, opts=None):
    node.innerHTML = ""
    node.appendChild(portrait(size, hat_key, opts))


def feedback():
    state.feedback()


# ---------------------------------------------------------------- test hook (only with ?test=1 in the address)
def _test_act(name, args_json):
    r = act(name, *json.loads(args_json))
    return json.dumps({"ok": r.get("ok"), "error": r.get("error"), "clears": (st["status"] or {}).get("clears")})


def _test_state():
    p = st["progress"] or {}
    return json.dumps({"acct": st["acct"], "online": st["online"], "pending": pending(), "guest": st["guest"],
                       "clears": (st["status"] or {}).get("clears"), "runs": (p.get("stats") or {}).get("runs"),
                       "coins": p.get("coins"), "levels": {k: v.get("clears") for k, v in (p.get("levels") or {}).items()},
                       "order": [lv["key"] for _t, lv in _ix["levels"]], "base_runs": ((st["base"] or {}).get("stats") or {}).get("runs")})


def _test_win(key):
    """A perfect result for a level, built from its data (what a real playthrough reports)."""
    data = R.level_of(key, st["journey"])["data"]
    tot = R.totals(data)
    npcs = [e for e in data.get("ents") or [] if e.get("t") == "npc"]
    result = {"time": 10.0, "picked": dict(tot["items"]), "errands": list(range(len(npcs))), "nests": tot["nests"],
              "kings": tot["kings"], "coins": tot["coins"], "pests": 4, "crates": tot["crates"], "damage": 0,
              "chopsticks": tot["chopsticks"] > 0, "postcard": tot["postcard"] > 0, "knobs": tot["knobs"],
              "bonuses": tot["bonuses"]}
    return _test_act("finish_level", json.dumps([key, result]))


def _test_sync():
    return json.dumps({"synced": sync_now(), "pending": pending()})


try:
    if "test=1" in str(window.location.search):
        window.bbTest = {"act": _test_act, "win": _test_win, "state": _test_state, "sync": _test_sync, "ensure": lambda: ensure(),
                         "online": lambda flag: set_online(flag)}
except Exception:
    pass
