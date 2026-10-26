# Game — Server Module. Everything a player does: load the journey, finish levels, cook, shop, daily box.
#
# Progress is one Simple Object per player (users.progress). Guests keep the same object in their
# browser and send it with each call (the guest_* functions), so every rule lives here once:
# the _apply_* functions take a progress dict and return a new one.
import datetime as dt
import hashlib
import random
import re

import anvil.server
import anvil.tables as tables
import anvil.users
from anvil.tables import app_tables

from . import Catalog as C
from . import Levels as L

# Accounts with these emails become admins the first time they sign in (users.is_admin can also be ticked by hand).
ADMIN_EMAILS = {"arkulinskis@gmail.com"}

STAT_KEYS = ("meat", "pests", "nests", "crates", "errands", "flawless", "dailies", "runs", "bosses", "cooked", "coins_earned")


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

def ensure_seeded():
    if len(app_tables.territories.search()) == 0:
        seed_defaults()


def seed_defaults(only_missing=True):
    """Add the built-in territories and levels that aren't in the tables yet. Returns how many were added."""
    added = 0
    have_t = {r["key"]: r for r in app_tables.territories.search()}
    for i, t in enumerate(L.TERRITORIES):
        if t["key"] not in have_t:
            have_t[t["key"]] = app_tables.territories.add_row(
                key=t["key"], name=t["name"], emoji=t["emoji"], blurb=t["blurb"], theme=t["theme"], pest=t["pest"],
                postcard=t["postcard"], position=float(i), published=True)
            added += 1
    have_l = {r["key"] for r in app_tables.levels.search()}
    pos = {}
    for lv in L.LEVELS:
        pos[lv["territory"]] = pos.get(lv["territory"], -1) + 1
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
             "pest": t["pest"], "postcard": t["_postcard"] if t["key"] in pc else None,
             "levels": [{"key": l["key"], "name": l["name"], "data": l["data"]} for l in t["levels"]]}
            for t in jr]


# ---------------------------------------------------------------- progress

def new_progress():
    return {"v": 1, "coins": 0, "levels": {}, "pantry": {}, "seen": {}, "cooked": {}, "hats": ["none"], "hat": "none",
            "badges": {}, "stats": {k: 0 for k in STAT_KEYS}, "daily": {"last": None, "streak": 0},
            "postcards": [], "market": {"day": None, "bought": []}}


def _int(v, lo=0, hi=10 ** 7):
    try:
        v = int(v)
    except Exception:
        return lo
    return max(lo, min(hi, v))


def normalize(p):
    """A clean copy of a progress dict: known keys only, sane numbers (guests send theirs from the browser)."""
    base = new_progress()
    if not isinstance(p, dict):
        return base
    base["coins"] = _int(p.get("coins"), 0, 10 ** 6)
    for k, v in (p.get("pantry") or {}).items():
        if k in C.ITEMS and _int(v) > 0:
            base["pantry"][k] = _int(v, 0, 9999)
    for k, v in (p.get("seen") or {}).items():
        if k in C.ITEMS and _int(v) > 0:
            base["seen"][k] = _int(v, 0, 10 ** 6)
    for k, v in (p.get("cooked") or {}).items():
        if k in C.RECIPE_BY_KEY and _int(v) > 0:
            base["cooked"][k] = _int(v, 0, 10 ** 5)
    for k, v in (p.get("levels") or {}).items():
        if isinstance(v, dict) and isinstance(k, str) and len(k) < 80:
            st = v.get("stars") or []
            base["levels"][k] = {"stars": [bool(st[i]) if i < len(st) else False for i in range(3)],
                                 "best": float(v["best"]) if isinstance(v.get("best"), (int, float)) else None,
                                 "chop": bool(v.get("chop")), "clears": _int(v.get("clears"), 0, 10 ** 5)}
    hats = [h for h in (p.get("hats") or []) if h in C.HAT_BY_KEY]
    base["hats"] = ["none"] + [h for h in dict.fromkeys(hats) if h != "none"]
    base["hat"] = p.get("hat") if p.get("hat") in base["hats"] else "none"
    for k, v in (p.get("badges") or {}).items():
        if any(b["key"] == k for b in C.BADGES):
            base["badges"][k] = str(v)[:10]
    for k in STAT_KEYS:
        base["stats"][k] = _int((p.get("stats") or {}).get(k), 0, 10 ** 7)
    d = p.get("daily") or {}
    base["daily"] = {"last": str(d.get("last"))[:10] if d.get("last") else None, "streak": _int(d.get("streak"), 0, 10 ** 4)}
    base["postcards"] = [str(x)[:40] for x in dict.fromkeys(p.get("postcards") or [])][:50]
    m = p.get("market") or {}
    base["market"] = {"day": str(m.get("day"))[:10] if m.get("day") else None,
                      "bought": [str(x)[:30] for x in (m.get("bought") or [])][:20]}
    return base


def perks(p):
    return [r["perk"] for r in C.RECIPES if p["cooked"].get(r["key"])]


def status(p, jr):
    """What's unlocked and cleared, plus totals the screens show."""
    unlocked, cleared = [], []
    prev_clear = True
    for t in jr:
        keys = [l["key"] for l in t["levels"]]
        done = [k for k in keys if p["levels"].get(k, {}).get("stars", [False])[0]]
        if prev_clear:
            for i, k in enumerate(keys):
                if i == 0 or keys[i - 1] in done:
                    unlocked.append(k)
        t_clear = prev_clear and len(done) == len(keys)
        if t_clear and keys:
            cleared.append(t["key"])
        prev_clear = t_clear
    all_keys = [l["key"] for t in jr for l in t["levels"]]
    chop_max = sum(1 for t in jr for l in t["levels"] if L.totals(l["data"])["chopsticks"])
    return {
        "unlocked": unlocked, "cleared": cleared,
        "stars": sum(sum(1 for s in p["levels"].get(k, {}).get("stars", []) if s) for k in all_keys),
        "stars_max": 3 * len(all_keys),
        "chopsticks": sum(1 for k in all_keys if p["levels"].get(k, {}).get("chop")),
        "chopsticks_max": chop_max,
        "perks": perks(p),
        "postcards_max": sum(1 for t in jr if any(L.totals(l["data"])["postcard"] for l in t["levels"])),
    }


def check_badges(p, jr, today):
    st = status(p, jr)
    have = p["badges"]
    s = p["stats"]
    tests = {
        "first_bite": any(v["stars"][0] for v in p["levels"].values()),
        "speedy": sum(1 for v in p["levels"].values() if v["stars"][2]) >= 5,
        "collector": len(p["seen"]) >= 20,
        "legend_hunter": any(C.ITEMS[k]["rarity"] == "legendary" for k in p["seen"]),
        "chef": len(p["cooked"]) >= 1,
        "master_chef": len(p["cooked"]) >= len(C.RECIPES),
        "fashionista": len([h for h in p["hats"] if h != "none"]) >= 5,
        "golden_touch": st["chopsticks"] >= 10,
        "pen_pal": st["postcards_max"] > 0 and len([x for x in p["postcards"] if any(t["key"] == x for t in jr)]) >= st["postcards_max"],
        "liberator": bool(jr) and len(st["cleared"]) == len([t for t in jr if t["levels"]]),
        "star_chef": st["stars"] >= 45,
    }
    new = []
    for b in C.BADGES:
        if b["key"] in have:
            continue
        ok = tests.get(b["key"])
        if "stat" in b:
            ok = s.get(b["stat"], 0) >= b["at"]
        if ok:
            have[b["key"]] = today.isoformat()
            new.append(b["key"])
    return new


def market_offers(day):
    """Today's market stall: the same offers for everyone, changing every day."""
    rnd = random.Random(int(hashlib.sha256(("market:" + day.isoformat()).encode()).hexdigest()[:12], 16))
    pool = [k for k in C.ITEM_ORDER if C.ITEMS[k]["rarity"] != "legendary"]
    picks = []
    rares = [k for k in pool if C.ITEMS[k]["rarity"] == "rare"]
    picks.append(rnd.choice(rares))
    rest = [k for k in pool if k not in picks]
    rnd.shuffle(rest)
    picks += rest[:C.MARKET_SIZE - 1]
    qty = {"common": 3, "uncommon": 2, "rare": 1}
    out = []
    for k in picks:
        r = C.ITEMS[k]["rarity"]
        out.append({"id": "%s:%s" % (day.isoformat(), k), "item": k, "qty": qty[r],
                    "price": int(round(C.RARITY[r]["price"] * qty[r] * 0.75))})
    return out


def view(p, jr, today, me, full=True):
    """What the client needs. Actions send full=False: the journey and catalog don't change."""
    out = {"me": me, "progress": p, "status": status(p, jr), "market": market_offers(today),
           "daily_ready": p["daily"]["last"] != today.isoformat(), "today": today.isoformat()}
    if full:
        out.update(journey=_public_journey(jr, p), catalog=C.public())
    return out


# ---------------------------------------------------------------- the rules

class GameError(Exception):
    pass


def apply_finish(p, lv, jr, result, today):
    """Score a won level. `result` comes from the browser, so everything is capped by what the level holds."""
    key = lv["key"]
    if key not in status(p, jr)["unlocked"]:
        raise GameError("That level isn't unlocked yet.")
    data = lv["data"]
    tot = L.totals(data)
    goals = data.get("goals") or {}
    result = result if isinstance(result, dict) else {}
    picked = {}
    for k, v in (result.get("picked") or {}).items():
        if k in tot["items"]:
            n = min(_int(v), tot["items"][k])
            if n:
                picked[k] = n
    npcs = [e for e in data.get("ents") or [] if e.get("t") == "npc"]
    errands = sorted({_int(i, -1, 10 ** 4) for i in (result.get("errands") or [])} & set(range(len(npcs))))
    nests = min(_int(result.get("nests")), tot["nests"])
    kings = min(_int(result.get("kings")), tot["kings"])
    meat = sum(n for k, n in picked.items() if k in C.MEATS)
    # The win must meet the level's goals.
    if meat < (goals.get("meat") or 0):
        raise GameError("Not enough meat for this level.")
    if goals.get("errands") and len(errands) < len(npcs):
        raise GameError("Errands aren't finished.")
    if goals.get("nests") and nests < tot["nests"]:
        raise GameError("Nests are still standing.")
    if kings < tot["kings"]:
        raise GameError("The Rat King is still standing.")
    # Items: picked, minus what was handed over, plus thank-you gifts.
    bag = dict(picked)
    gifts = {}
    for i in errands:
        n = npcs[i]
        w, c = n.get("wants"), max(1, _int(n.get("count"), 1, 99))
        bag[w] = max(0, bag.get(w, 0) - c)
        g = n.get("gift")
        if g in C.ITEMS:
            gc = max(1, _int(n.get("gift_count"), 1, 20))
            gifts[g] = gifts.get(g, 0) + gc
            bag[g] = bag.get(g, 0) + gc
    gained = {k: v for k, v in bag.items() if v > 0}
    new_items = [k for k in gained if not p["seen"].get(k)]
    for k, v in gained.items():
        p["pantry"][k] = p["pantry"].get(k, 0) + v
        p["seen"][k] = p["seen"].get(k, 0) + v
    # Stars.
    t = float(result.get("time") or 0)
    t = max(3.0, min(t, 24 * 3600.0))
    all_items = all(picked.get(k, 0) >= n for k, n in tot["items"].items())
    stars = [True, all_items, t <= float(data.get("par") or 60)]
    rec = p["levels"].get(key) or {"stars": [False, False, False], "best": None, "chop": False, "clears": 0}
    first_clear = not rec["stars"][0]
    new_stars = [i for i in range(3) if stars[i] and not rec["stars"][i]]
    rec["stars"] = [rec["stars"][i] or stars[i] for i in range(3)]
    new_best = rec["best"] is None or t < rec["best"]
    rec["best"] = round(t, 2) if new_best else rec["best"]
    rec["clears"] = rec.get("clears", 0) + 1
    new_chop = bool(result.get("chopsticks")) and tot["chopsticks"] > 0 and not rec["chop"]
    rec["chop"] = rec["chop"] or (bool(result.get("chopsticks")) and tot["chopsticks"] > 0)
    p["levels"][key] = rec
    postcard = None
    terr = next((tr for tr in jr if any(l["key"] == key for l in tr["levels"])), None)
    if result.get("postcard") and tot["postcard"] and terr and terr["key"] not in p["postcards"]:
        p["postcards"].append(terr["key"])
        postcard = {"territory": terr["key"], "name": terr["name"], "text": terr["_postcard"]}
    # Coins.
    pk = perks(p)
    pests = min(_int(result.get("pests")), 150)
    crates = min(_int(result.get("crates")), tot["crates"])
    parts = [("Coins picked up", min(_int(result.get("coins")), tot["coins"])),
             ("Pests bonked", pests * C.COINS["pest"] * (2 if "lucky" in pk else 1)),
             ("Crates smashed", crates * C.COINS["crate"]),
             ("Errands", len(errands) * C.COINS["errand"]),
             ("Nests destroyed", nests * C.COINS["nest"]),
             ("Rat King", kings * C.COINS["boss"]),
             ("New stars", len(new_stars) * C.COINS["star"]),
             ("First clear", C.COINS["first_clear"] if first_clear else 0)]
    total = sum(v for _, v in parts)
    if "rich" in pk and total:
        parts.append(("Big Tipper +50%", total // 2))
        total += total // 2
    p["coins"] += total
    # Stats and badges.
    s = p["stats"]
    s["meat"] += meat
    s["pests"] += pests
    s["nests"] += nests
    s["crates"] += crates
    s["errands"] += len(errands)
    s["bosses"] += kings
    s["runs"] += 1
    s["coins_earned"] += total
    if _int(result.get("damage")) == 0:
        s["flawless"] += 1
    before = status(p, jr)
    badges = check_badges(p, jr, today)
    # What this win opened up.
    old_unlocked = set(status_without(p, key, jr)["unlocked"]) if first_clear else set(before["unlocked"])
    newly = [k for k in before["unlocked"] if k not in old_unlocked]
    liberated = terr["key"] if (first_clear and terr and terr["key"] in before["cleared"]) else None
    report = {"level": key, "time": round(t, 2), "stars": stars, "best": rec["best"], "new_best": new_best,
              "new_stars": new_stars, "first_clear": first_clear, "coins": total,
              "coin_parts": [[n, v] for n, v in parts if v], "gained": gained, "gifts": gifts, "new_items": new_items,
              "new_badges": badges, "unlocked": newly, "liberated": liberated, "postcard": postcard,
              "chopsticks": new_chop}
    return p, report


def status_without(p, key, jr):
    q = dict(p)
    q["levels"] = {k: v for k, v in p["levels"].items() if k != key}
    return status(q, jr)


def apply_cook(p, recipe_key, jr, today):
    r = C.RECIPE_BY_KEY.get(recipe_key)
    if not r:
        raise GameError("Unknown recipe.")
    for k, n in r["needs"].items():
        if p["pantry"].get(k, 0) < n:
            raise GameError("You need %d × %s." % (n, C.ITEMS[k]["name"]))
    for k, n in r["needs"].items():
        p["pantry"][k] -= n
        if p["pantry"][k] <= 0:
            del p["pantry"][k]
    first = not p["cooked"].get(recipe_key)
    p["cooked"][recipe_key] = p["cooked"].get(recipe_key, 0) + 1
    p["stats"]["cooked"] += 1
    coins = 0
    hat = None
    if first:
        if r.get("hat") and r["hat"] not in p["hats"]:
            p["hats"].append(r["hat"])
            hat = r["hat"]
    else:
        coins = C.RECIPE_SELL
        p["coins"] += coins
    badges = check_badges(p, jr, today)
    return p, {"recipe": recipe_key, "first": first, "perk": r["perk_name"] if first else None, "coins": coins,
               "hat": hat, "new_badges": badges}


def apply_buy_hat(p, hat, jr, today):
    h = C.HAT_BY_KEY.get(hat)
    if not h or h["price"] is None:
        raise GameError("That hat isn't for sale.")
    if hat in p["hats"]:
        raise GameError("You already own it.")
    if p["coins"] < h["price"]:
        raise GameError("Not enough coins.")
    p["coins"] -= h["price"]
    p["hats"].append(hat)
    p["hat"] = hat
    return p, {"hat": hat, "new_badges": check_badges(p, jr, today)}


def apply_wear(p, hat):
    if hat not in p["hats"]:
        raise GameError("You don't own that hat.")
    p["hat"] = hat
    return p, {"hat": hat}


def apply_market(p, offer_id, jr, today):
    offer = next((o for o in market_offers(today) if o["id"] == offer_id), None)
    if not offer:
        raise GameError("That offer has sold out. The market changes every day.")
    if p["market"]["day"] != today.isoformat():
        p["market"] = {"day": today.isoformat(), "bought": []}
    if offer_id in p["market"]["bought"]:
        raise GameError("You already bought that today.")
    if p["coins"] < offer["price"]:
        raise GameError("Not enough coins.")
    p["coins"] -= offer["price"]
    p["market"]["bought"].append(offer_id)
    k = offer["item"]
    new = not p["seen"].get(k)
    p["pantry"][k] = p["pantry"].get(k, 0) + offer["qty"]
    p["seen"][k] = p["seen"].get(k, 0) + offer["qty"]
    return p, {"item": k, "qty": offer["qty"], "new_items": [k] if new else [], "new_badges": check_badges(p, jr, today)}


def apply_daily(p, jr, today):
    d = p["daily"]
    if d["last"] == today.isoformat():
        raise GameError("You've already opened today's box. Come back tomorrow!")
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    d["streak"] = d["streak"] + 1 if d["last"] == yesterday else 1
    d["last"] = today.isoformat()
    coins = C.DAILY["coins"] + C.DAILY["streak_bonus"] * (min(d["streak"], C.DAILY["streak_cap"]) - 1)
    p["coins"] += coins
    keys = C.ITEM_ORDER
    weights = [C.RARITY[C.ITEMS[k]["rarity"]]["weight"] for k in keys]
    items = {}
    for k in random.choices(keys, weights=weights, k=C.DAILY["items"]):
        items[k] = items.get(k, 0) + 1
    new = [k for k in items if not p["seen"].get(k)]
    for k, n in items.items():
        p["pantry"][k] = p["pantry"].get(k, 0) + n
        p["seen"][k] = p["seen"].get(k, 0) + n
    p["stats"]["dailies"] += 1
    return p, {"coins": coins, "items": items, "streak": d["streak"], "new_items": new,
               "new_badges": check_badges(p, jr, today)}


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
