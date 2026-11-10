# Game — Server Module. Everything a player does: load the journey, finish levels, cook, shop, daily box.
#
# Progress is one Simple Object per player (users.progress). The rules live in client_code/rules.py, shared with the
# browser: the game scores every action on the device (instant, works offline), keeps a copy per account in the
# browser's IndexedDB, and sync() adds what changed since the last sync on top of the account (additive merge).
# The older per-action callables and guest_* twins stay for pages still open from before.
import datetime as dt
import re

import anvil.server
import anvil.tables as tables
import anvil.users
from anvil.tables import app_tables

from . import Catalog as C
from . import Levels as L
from . import rules as R

# Accounts with these emails become admins the first time they sign in (users.is_admin can also be ticked by hand).
ADMIN_EMAILS = {"arkulinskis@gmail.com"}

STAT_KEYS = R.STAT_KEYS


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _iso(d):
    return d.isoformat() if d else None


def _client_today(today):
    """The player's local date, accepted only within a day of UTC (it drives the daily box and market)."""
    utc = _now().date()
    try:
        d = dt.date.fromisoformat(str(today)[:10])
        if abs((d - utc).days) <= 1:
            return d
    except Exception:
        pass
    return utc


# ---------------------------------------------------------------- seeding and the journey

_UPGRADED = [False]


def ensure_seeded():
    if len(app_tables.territories.search()) == 0:
        seed_defaults()
    if not _UPGRADED[0]:
        seed_new_territories()
        upgrade_builtins()
        _UPGRADED[0] = True


def seed_new_territories():
    """Add built-in territories that shipped after this app was first seeded (worlds 7-16), with their levels.
    Territories that already exist are left alone, so levels an admin deleted don't come back."""
    have = {r["key"] for r in app_tables.territories.search()}
    missing = [t["key"] for t in L.TERRITORIES if t["key"] not in have]
    if not missing:
        return 0
    return seed_defaults(territories=set(missing))


def upgrade_builtins():
    """Bring unedited built-in levels up to the latest shipped version. Returns how many changed."""
    shipped = {lv["key"]: lv for lv in L.LEVELS}
    n = 0
    for row in app_tables.levels.search(builtin=True):
        lv = shipped.get(row["key"])
        if lv and lv.get("v1") and row["data"] is not None and L.canon(row["data"]) == L.canon(lv["v1"]) and L.canon(lv["v1"]) != L.canon(lv["data"]):
            row["data"] = lv["data"]
            n += 1
    return n


def seed_defaults(only_missing=True, territories=None):
    """Add the built-in territories and levels that aren't in the tables yet (only those territories, if given).
    Returns how many were added."""
    added = 0
    have_t = {r["key"]: r for r in app_tables.territories.search()}
    for i, t in enumerate(L.TERRITORIES):
        if territories is not None and t["key"] not in territories:
            continue
        if t["key"] not in have_t:
            have_t[t["key"]] = app_tables.territories.add_row(
                key=t["key"], name=t["name"], emoji=t["emoji"], blurb=t["blurb"], theme=t["theme"], pest=t["pest"],
                postcard=t["postcard"], position=float(i), published=True)
            added += 1
    have_l = {r["key"] for r in app_tables.levels.search()}
    pos = {}
    for lv in L.LEVELS:
        pos[lv["territory"]] = pos.get(lv["territory"], -1) + 1
        if territories is not None and lv["territory"] not in territories:
            continue
        if lv["key"] not in have_l:
            app_tables.levels.add_row(key=lv["key"], territory=have_t[lv["territory"]], name=lv["name"],
                                      position=float(pos[lv["territory"]]), data=lv["data"], published=True,
                                      updated=_now(), builtin=True, clears=0)
            added += 1
    return added


def journey(include_unpublished=False):
    """Territories in order, each with its levels in order (published only, unless asked)."""
    out = []
    levels = {}
    for lv in app_tables.levels.search():
        if lv["published"] or include_unpublished:
            if lv["territory"] is not None:
                levels.setdefault(lv["territory"]["key"], []).append(lv)
    for t in sorted(app_tables.territories.search(), key=lambda r: (r["position"] or 0, r["name"] or "")):
        if not (t["published"] or include_unpublished):
            continue
        rows = sorted(levels.get(t["key"], []), key=lambda r: (r["position"] or 0, r["name"] or ""))
        out.append({"key": t["key"], "name": t["name"], "emoji": t["emoji"] or "🏮", "blurb": t["blurb"] or "",
                    "theme": t["theme"] or "kitchen", "pest": t["pest"] or "ant", "published": bool(t["published"]),
                    "_postcard": t["postcard"] or "",
                    "levels": [{"key": r["key"], "name": r["name"], "data": r["data"], "published": bool(r["published"]),
                                "builtin": bool(r["builtin"]), "clears": r["clears"] or 0, "_row": r} for r in rows]})
    return out


def _public_journey(jr, progress):
    pc = set(progress.get("postcards") or [])
    return [{"key": t["key"], "name": t["name"], "emoji": t["emoji"], "blurb": t["blurb"], "theme": t["theme"],
             "pest": t["pest"], "postcard": t["_postcard"] if t["key"] in pc else None, "_postcard": t["_postcard"],
             "levels": [{"key": l["key"], "name": l["name"], "data": l["data"]} for l in t["levels"]]}
            for t in jr]


# ---------------------------------------------------------------- progress and the rules (client_code/rules.py)
# The rules are shared with the browser, which scores everything itself (instant, and it works offline) and syncs
# what changed through sync() below. These names stay here for Admin.py and the tests.

GameError = R.GameError
new_progress = R.new_progress
normalize = R.normalize
perks = R.perks
status = R.status
check_badges = R.check_badges
market_offers = R.market_offers
apply_finish = R.apply_finish
apply_cook = R.apply_cook
apply_buy_hat = R.apply_buy_hat
apply_wear = R.apply_wear
apply_market = R.apply_market
apply_daily = R.apply_daily
status_without = R.status_without
_int = R._int


def view(p, jr, today, me, full=True):
    """What the client needs. Actions send full=False: the journey and catalog don't change."""
    out = R.view(p, jr, today)
    out["me"] = me
    if full:
        out.update(journey=_public_journey(jr, p), catalog=C.public())
    return out


# ---------------------------------------------------------------- signed-in players

def _user():
    u = anvil.users.get_user()
    if u is None:
        raise anvil.server.PermissionDenied("Please sign in.")
    return u


def is_admin(u):
    if u is None:
        return False
    if u["is_admin"]:
        return True
    if (u["email"] or "").lower() in ADMIN_EMAILS:
        u["is_admin"] = True
        return True
    return False


def _me(u):
    return {"name": u["display_name"] or (u["email"] or "Bun").split("@")[0], "email": u["email"],
            "is_admin": is_admin(u), "guest": False}


def _load(u):
    return normalize(u["progress"]) if u["progress"] else new_progress()


def _ok(p, jr, today, me, report=None, full=True):
    out = view(p, jr, today, me, full)
    out["ok"] = True
    if report is not None:
        out["report"] = report
    return out


def _run(fn, *args):
    try:
        return fn(*args)
    except GameError as e:
        return {"ok": False, "error": str(e)}


def _level_row(level_key, jr):
    for t in jr:
        for l in t["levels"]:
            if l["key"] == level_key:
                return l
    raise GameError("That level doesn't exist any more.")


@anvil.server.callable
def get_state(today=None):
    ensure_seeded()
    u = _user()
    t = _client_today(today)
    jr = journey()
    p = _load(u)
    if u["progress"] is None:
        u["progress"] = p
    u["last_played"] = _now()
    if not u["display_name"]:
        u["display_name"] = (u["email"] or "Bun").split("@")[0][:24]
    return _ok(p, jr, t, _me(u))


def _user_action(today, fn):
    u = _user()
    t = _client_today(today)
    jr = journey()

    def go():
        p, report = fn(_load(u), jr, t)
        u["progress"] = p
        u["last_played"] = _now()
        return _ok(p, jr, t, _me(u), report, full=False)
    return _run(go)


@anvil.server.callable
def finish_level(level_key, result, today=None):
    u = _user()

    def fn(p, jr, t):
        lv = _level_row(level_key, jr)
        p, report = apply_finish(p, lv, jr, result, t)
        row = lv["_row"]
        row["clears"] = (row["clears"] or 0) + 1
        _save_score(u, row, report["time"], sum(1 for s in p["levels"][level_key]["stars"] if s))
        report["leaderboard"] = _board(row, u)
        return p, report
    return _user_action(today, fn)


@anvil.server.callable
def cook(recipe_key, today=None):
    return _user_action(today, lambda p, jr, t: apply_cook(p, recipe_key, jr, t))


@anvil.server.callable
def buy_hat(hat, today=None):
    return _user_action(today, lambda p, jr, t: apply_buy_hat(p, hat, jr, t))


@anvil.server.callable
def wear_hat(hat, today=None):
    return _user_action(today, lambda p, jr, t: apply_wear(p, hat))


@anvil.server.callable
def buy_market(offer_id, today=None):
    return _user_action(today, lambda p, jr, t: apply_market(p, offer_id, jr, t))


@anvil.server.callable
def claim_daily(today=None):
    return _user_action(today, lambda p, jr, t: apply_daily(p, jr, t))


@anvil.server.callable
def set_name(name, today=None):
    u = _user()
    name = re.sub(r"\s+", " ", str(name or "")).strip()[:24]
    if len(name) < 2:
        return {"ok": False, "error": "Pick a name with at least 2 letters."}
    u["display_name"] = name
    return get_state(today)


@anvil.server.callable
def import_guest(progress, today=None):
    """After sign-up: adopt the guest's browser progress if the account has none yet."""
    u = _user()
    mine = _load(u)
    g = normalize(progress)
    if not mine["levels"] and not mine["cooked"] and (g["levels"] or g["pantry"] or g["coins"]):
        jr = journey()
        known = {l["key"] for t in jr for l in t["levels"]}
        g["levels"] = {k: v for k, v in g["levels"].items() if k in known}
        u["progress"] = g
    return get_state(today)


@anvil.server.callable
def get_world(today=None):
    """The journey and catalog for anyone (signed in or not): the browser keeps a copy so the game plays offline."""
    ensure_seeded()
    t = _client_today(today)
    jr = journey()
    return {"ok": True, "journey": _public_journey(jr, new_progress()), "catalog": C.public(), "today": t.isoformat()}


@anvil.server.callable
def sync(delta, sync_id, finishes=None, today=None):
    """Add what this device changed since its last sync (rules.diff) on top of the account: offline play, play on
    another device in between, or a guest's progress the player chose to keep. Plays, coins, items and stats add up,
    stars/hats/badges combine, the best time wins (rules.merge). `finishes` = levels won since the last sync, for the
    leaderboards. A sync_id the account already applied is skipped, so a retry after a dropped connection is harmless."""
    u = _user()
    ensure_seeded()
    t = _client_today(today)
    jr = journey()
    p = _load(u)
    sid = str(sync_id or "")[:40]
    applied = False
    if sid and sid not in p["sync"]:
        rows = {lv["key"]: lv for tr in jr for lv in tr["levels"]}
        d = R.clean_delta(delta, set(rows))
        if not R.is_empty(d):
            p = R.merge(p, d)
            R.check_badges(p, jr, t)
            applied = True
        p["sync"] = (p["sync"] + [sid])[-R.SYNC_KEEP:]
        for f in (finishes if isinstance(finishes, list) else [])[:500]:
            lv = rows.get(f.get("level")) if isinstance(f, dict) else None
            if lv is None:
                continue
            try:
                tm = max(3.0, min(float(f.get("time")), 24 * 3600.0))
            except Exception:
                continue
            row = lv["_row"]
            row["clears"] = (row["clears"] or 0) + 1
            rec = p["levels"].get(lv["key"]) or {}
            _save_score(u, row, tm, sum(1 for x in rec.get("stars", []) if x))
        u["progress"] = p
        u["last_played"] = _now()
    return _ok(p, jr, t, _me(u), {"applied": applied}, full=False)


def _save_score(u, level_row, t, stars):
    row = app_tables.scores.get(user=u, level=level_row)
    if row is None:
        app_tables.scores.add_row(user=u, level=level_row, time=float(t), stars=float(stars), at=_now())
    else:
        if t < (row["time"] or 10 ** 9):
            row["time"] = float(t)
            row["at"] = _now()
        row["stars"] = float(max(stars, row["stars"] or 0))


def _board(level_row, u=None, n=10):
    rows = list(app_tables.scores.search(tables.order_by("time"), level=level_row))
    out = []
    you = None
    for i, r in enumerate(rows):
        usr = r["user"]
        name = (usr["display_name"] or "Bun") if usr is not None else "Bun"
        entry = {"rank": i + 1, "name": name, "time": r["time"], "stars": int(r["stars"] or 0), "you": usr == u}
        if i < n:
            out.append(entry)
        if usr == u:
            you = entry
    return {"top": out, "you": you, "total": len(rows)}


@anvil.server.callable
def leaderboard(level_key):
    row = app_tables.levels.get(key=level_key)
    if row is None:
        return {"top": [], "you": None, "total": 0}
    return _board(row, anvil.users.get_user())


# ---------------------------------------------------------------- guests (progress lives in the browser)

def _guest(progress, today, fn=None):
    ensure_seeded()
    t = _client_today(today)
    jr = journey()
    p = normalize(progress)
    me = {"name": "Guest Bun", "email": None, "is_admin": False, "guest": True}
    if fn is None:
        return _ok(p, jr, t, me)

    def go():
        p2, report = fn(p, jr, t)
        return _ok(p2, jr, t, me, report, full=False)
    return _run(go)


@anvil.server.callable
def guest_state(progress, today=None):
    return _guest(progress, today)


@anvil.server.callable
def guest_finish_level(progress, level_key, result, today=None):
    def fn(p, jr, t):
        lv = _level_row(level_key, jr)
        p, report = apply_finish(p, lv, jr, result, t)
        report["leaderboard"] = _board(lv["_row"], None)
        return p, report
    return _guest(progress, today, fn)


@anvil.server.callable
def guest_cook(progress, recipe_key, today=None):
    return _guest(progress, today, lambda p, jr, t: apply_cook(p, recipe_key, jr, t))


@anvil.server.callable
def guest_buy_hat(progress, hat, today=None):
    return _guest(progress, today, lambda p, jr, t: apply_buy_hat(p, hat, jr, t))


@anvil.server.callable
def guest_wear_hat(progress, hat, today=None):
    return _guest(progress, today, lambda p, jr, t: apply_wear(p, hat))


@anvil.server.callable
def guest_buy_market(progress, offer_id, today=None):
    return _guest(progress, today, lambda p, jr, t: apply_market(p, offer_id, jr, t))


@anvil.server.callable
def guest_claim_daily(progress, today=None):
    return _guest(progress, today, lambda p, jr, t: apply_daily(p, jr, t))


# ---------------------------------------------------------------- feedback and bug reports (anyone can send)

FEEDBACK_KINDS = {"bug": "Bug", "idea": "Idea", "level": "Level problem", "other": "Other"}
FEEDBACK_LIMIT = 8  # per browser session per hour


def _clean_context(ctx):
    out = {}
    if isinstance(ctx, dict):
        for k, v in list(ctx.items())[:25]:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[str(k)[:40]] = v
            elif v is not None:
                out[str(k)[:40]] = str(v)[:300]
    return out


@anvil.server.callable
def submit_feedback(kind, message, email=None, context=None):
    message = str(message or "").strip()
    if len(message) < 5:
        return {"ok": False, "error": "Please write a little more (at least 5 characters)."}
    now = _now()
    recent = [t for t in (anvil.server.session.get("feedback_times") or []) if (now - dt.datetime.fromisoformat(t)).total_seconds() < 3600]
    if len(recent) >= FEEDBACK_LIMIT:
        return {"ok": False, "error": "Thanks! You've sent a lot of messages this hour. Please try again a bit later."}
    getattr(anvil.server, "session")["feedback_times"] = recent + [now.isoformat()]
    u = anvil.users.get_user()
    email = re.sub(r"\s+", "", str(email or ""))[:120] or (u["email"] if u else None)
    app_tables.feedback.add_row(
        user=u, name=(u["display_name"] or u["email"]) if u else "Guest", email=email or None,
        kind=kind if kind in FEEDBACK_KINDS else "other", message=message[:4000],
        context=_clean_context(context), created=now, status="new")
    return {"ok": True}
