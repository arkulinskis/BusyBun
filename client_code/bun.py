"""Busy Bun's game state in the browser, the rules the screens need, and small bridges to the JavaScript engines
(theme/assets: bb-kit.js = window.BB helpers + Sound, bb-art.js = drawing, bb-engine.js = the game, bb-stage.js).

    bun.ensure()            load the player's journey once (signed out = guest: progress is kept in this browser)
    bun.act(name, *args)    a progress-changing action ("cook", "buy_hat", ...): the guest_ twin for guests
    bun.st                  {me, progress, status, journey, catalog, market, daily_ready, today, guest, world}
    bun.sfx("coin")         a sound effect; bun.music("menu") the background music for a mood
Every rule that changes progress lives on the server (Game.py); this module only reads and displays.
"""
import json

import anvil.js
import anvil.server
from anvil.js import window

from . import state

GUEST_KEY = "bb.guest.v1"  # same browser keys as the JavaScript version, so guest saves carry over
RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "legendary": 3}
BOSS_NAMES = {"king": "the Rat King", "queen": "the Wasp Queen"}
PEST_EMOJI = {"ant": "🐜", "rat": "🐀", "fly": "🪰", "roach": "🪳", "gull": "🐦", "king": "👑", "snail": "🐌",
              "mould": "🦠", "frog": "🐸", "weevil": "🪲", "spider": "🕷️", "wasp": "🐝", "queen": "👑"}
DARK_THEMES = ("market", "banquet", "cellar", "festival", "dragon")
YT_VIDEO = "mFIuuENN_nI"  # the Busy Bun video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json)

st: dict = {"loaded": False, "guest": False, "me": None, "progress": None, "status": None, "journey": [],
            "catalog": None, "market": [], "daily_ready": False, "today": None, "world": None, "focus": None}
_ix: dict = {"items": {}, "recipes": {}, "hats": {}, "badges": {}, "levels": [], "where": None}


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


# ---------------------------------------------------------------- server
def call(fn, *args):
    """anvil.server.call that turns failures into {"ok": False, "error": ...} like the old game did."""
    try:
        return anvil.server.call(fn, *args)
    except Exception as e:
        kind = type(e).__name__
        if kind == "PermissionDenied":
            return {"ok": False, "error": str(e) or "You don't have access to that."}
        if kind == "SessionExpiredError":
            return {"ok": False, "error": "Your session expired. Reload the page and sign in again."}
        if kind == "AppOfflineError":
            return {"ok": False, "error": "You seem to be offline. Check your connection and try again."}
        print("server call %s failed: %r" % (fn, e))
        return {"ok": False, "error": "Something went wrong in the kitchen. Please try again."}


def _index():
    c = st["catalog"] or {}
    _ix["items"] = {i["key"]: i for i in c.get("items", [])}
    _ix["recipes"] = {r["key"]: r for r in c.get("recipes", [])}
    _ix["hats"] = {h["key"]: h for h in c.get("hats", [])}
    _ix["badges"] = {b["key"]: b for b in c.get("badges", [])}


def apply(r):
    if not r:
        return
    if r.get("catalog"):
        st["catalog"] = r["catalog"]
        _index()
    if r.get("journey"):
        st["journey"] = r["journey"]
        _ix["levels"] = [(t, l) for t in st["journey"] for l in t["levels"]]
        _ix["where"] = None
    for k in ("me", "progress", "status", "market", "daily_ready", "today"):
        if k in r:
            st[k] = r[k]
    if st["guest"] and st["progress"] is not None:
        put(GUEST_KEY, st["progress"])
    rep = r.get("report") or {}
    pc = rep.get("postcard") if isinstance(rep, dict) else None
    if pc:
        for t in st["journey"]:
            if t["key"] == pc.get("territory"):
                t["postcard"] = pc.get("text")
    if st["progress"]:
        put("bb.lastHat", st["progress"].get("hat") or "none")


def reset():
    """Forget the loaded journey (after signing in or out)."""
    st["loaded"] = False


def ensure(force=False):
    """Load the journey for whoever is here now. False (with a toast) if it couldn't load."""
    guest = state.me() is None
    if st["loaded"] and st["guest"] == guest and not force:
        return True
    st["guest"] = guest
    r = call("guest_state", get(GUEST_KEY), today()) if guest else call("get_state", today())
    if r and r.get("ok"):
        apply(r)
        st["loaded"] = True
        return True
    state.toast((r or {}).get("error") or "Could not load your game.", "error")
    return False


def act(name, *args):
    """A progress-changing action on the server; for guests the guest_ twin with the browser's progress."""
    a = ([st["progress"]] if st["guest"] else []) + list(args) + [today()]
    r = call(("guest_" if st["guest"] else "") + name, *a)
    if r and r.get("ok"):
        apply(r)
    else:
        state.toast((r or {}).get("error") or "That didn't work.", "error")
    return r


def after_sign_in(is_new=False):
    """Signed in: adopt the guest's browser progress if the account has none, then load the account's journey."""
    guest = get(GUEST_KEY)
    had = bool(guest and (guest.get("levels") or {}))
    st["guest"] = False
    r = call("import_guest", guest, today()) if had else call("get_state", today())
    if not r or not r.get("ok"):
        state.toast((r or {}).get("error") or "Could not load your game.", "error")
        st["loaded"] = False
        return False
    apply(r)
    st["loaded"] = True
    if had and (r["progress"].get("levels") or {}):
        drop(GUEST_KEY)
        toast("💾 Your guest progress is now saved to your account!", "gold")
    elif is_new:
        toast("Welcome to Busy Bun, %s!" % ((r.get("me") or {}).get("name") or "bun"), "gold")
    return True


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
