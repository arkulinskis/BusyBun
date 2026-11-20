"""The game rules, shared by the browser and the server (a client_code module the server imports too).

Progress is one dict per player. Every rule takes a progress dict and returns the changed dict plus a report, so the
same code scores a level in the browser (instant, works offline) and on the server (the record that syncs).

    new_progress() / normalize(p)        a fresh or cleaned progress dict
    status(p, jr)                        unlocked levels, cleared worlds, totals
    apply_finish / apply_cook / apply_buy_hat / apply_wear / apply_market / apply_daily
    dish_of(day, jr) / apply_dish        the Daily Dish: today's level and twist (same everywhere), a win on it
    diff(base, cur) / merge(p, delta)    offline sync: what changed since the last sync, added on top of the account

Journey `jr` = territories in order, each {"key", "name", "_postcard", "levels": [{"key", "name", "data"}]}.
Dates are datetime.date objects (day(text) makes one). No random module and no hashlib: the market and the daily
box come from a small seeded generator, so the browser and the server always get the same result.
"""
import datetime as dt

from . import Catalog as C

STAT_KEYS = ("meat", "pests", "nests", "crates", "errands", "flawless", "dailies", "runs", "bosses", "cooked", "coins_earned",
             "knobs", "bonuses", "dishes")
SYNC_KEEP = 40  # how many applied sync ids each account remembers (a retried sync is never added twice)
DISH_KEEP = 31  # how many Daily Dish days each account remembers (the week's stamps)


class GameError(Exception):
    pass


def day(text):
    """'2026-11-10' -> date (None if it isn't a date)."""
    try:
        s = str(text)[:10]
        return dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except Exception:
        return None


def _int(v, lo=0, hi=10 ** 7):
    try:
        v = int(v)
    except Exception:
        return lo
    return max(lo, min(hi, v))


def _unique(seq):
    out = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def _rng(seed_text):
    """A small seeded random generator (FNV-1a seed + mulberry32): the same numbers in Python and in the browser."""
    h = 2166136261
    for ch in seed_text:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    s = [h]

    def nxt():
        s[0] = (s[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = s[0]
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ ((t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    return nxt


# ---------------------------------------------------------------- levels

_TOTALS: dict = {}


def totals(data):
    """What a level holds: item counts, pickups, npcs, nests, crates, bosses (used to check results). Cached per data."""
    key = id(data)
    hit = _TOTALS.get(key)
    if hit is not None and hit[0] is data:
        return hit[1]
    out: dict = {"items": {}, "coins": 0, "chopsticks": 0, "postcard": 0, "npcs": 0, "nests": 0, "crates": 0, "kings": 0,
                 "bonuses": 0, "knobs": 0}
    for e in data.get("ents") or []:
        t = e.get("t")
        if t == "item":
            out["items"][e["k"]] = out["items"].get(e["k"], 0) + 1
        elif t == "pickup":
            k = e.get("k")
            if k == "coin":
                out["coins"] += 1
            elif k == "bag":
                out["coins"] += C.BAG_COINS
            elif k in ("chopsticks", "postcard"):
                out[k] += 1
            if k in C.BONUS_KEYS:
                out["bonuses"] += 1
            if k in C.KNOB_KEYS:
                out["knobs"] += 1
        elif t == "npc":
            out["npcs"] += 1
        elif t == "nest":
            out["nests"] += 1
        elif t == "pest" and e.get("k") in C.BOSSES:
            out["kings"] += 1  # "kings" = bosses (the Rat King, the Wasp Queen)
    out["crates"] = sum(r.count("X") for r in data.get("tiles") or [])
    if len(_TOTALS) > 2000:
        _TOTALS.clear()
    _TOTALS[key] = (data, out)
    return out


def level_of(level_key, jr):
    for t in jr:
        for lv in t["levels"]:
            if lv["key"] == level_key:
                return lv
    raise GameError("That level doesn't exist any more.")


# ---------------------------------------------------------------- progress

def new_progress():
    return {"v": 1, "coins": 0, "levels": {}, "pantry": {}, "seen": {}, "cooked": {}, "hats": ["none"], "hat": "none",
            "badges": {}, "stats": {k: 0 for k in STAT_KEYS}, "daily": {"last": None, "streak": 0},
            "postcards": [], "market": {"day": None, "bought": []}, "sync": [], "dish": {"days": [], "best": None}}


def normalize(p):
    """A clean copy of a progress dict: known keys only, sane numbers (browsers send theirs)."""
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
            best = v.get("best")
            base["levels"][k] = {"stars": [bool(st[i]) if i < len(st) else False for i in range(3)],
                                 "best": float(best) if isinstance(best, (int, float)) and not isinstance(best, bool) else None,
                                 "chop": bool(v.get("chop")), "clears": _int(v.get("clears"), 0, 10 ** 5)}
    hats = [h for h in (p.get("hats") or []) if h in C.HAT_BY_KEY]
    base["hats"] = ["none"] + [h for h in _unique(hats) if h != "none"]
    base["hat"] = p.get("hat") if p.get("hat") in base["hats"] else "none"
    for k, v in (p.get("badges") or {}).items():
        if k in C.BADGE_KEYS:
            base["badges"][k] = str(v)[:10]
    for k in STAT_KEYS:
        base["stats"][k] = _int((p.get("stats") or {}).get(k), 0, 10 ** 7)
    d = p.get("daily") or {}
    base["daily"] = {"last": str(d.get("last"))[:10] if d.get("last") else None, "streak": _int(d.get("streak"), 0, 10 ** 4)}
    base["postcards"] = [str(x)[:40] for x in _unique(p.get("postcards") or [])][:50]
    m = p.get("market") or {}
    base["market"] = {"day": str(m.get("day"))[:10] if m.get("day") else None,
                      "bought": [str(x)[:30] for x in (m.get("bought") or [])][:20]}
    base["sync"] = [str(x)[:40] for x in (p.get("sync") or []) if x][-SYNC_KEEP:]
    base["dish"] = _clean_dish(p.get("dish"))
    return base


def _clean_dish(d):
    """{"days": the days a Daily Dish was won (sorted, last 31), "best": {"day", "time", "hearts"} for the latest day}."""
    d = d if isinstance(d, dict) else {}
    days = sorted({str(x)[:10] for x in (d.get("days") or []) if day(x)})[-DISH_KEEP:]
    b = d.get("best")
    best = None
    if isinstance(b, dict) and day(b.get("day")):
        try:
            best = {"day": str(b["day"])[:10], "time": round(max(3.0, float(b.get("time"))), 2),
                    "hearts": _int(b.get("hearts"), 0, 9)}
        except Exception:
            best = None
    return {"days": days, "best": best}


def _better_best(a, b):
    """The Daily Dish best to keep: the later day, or the faster time on the same day."""
    if not a:
        return b
    if not b:
        return a
    if a["day"] != b["day"]:
        return a if a["day"] > b["day"] else b
    return a if a["time"] <= b["time"] else b


def perks(p):
    return [r["perk"] for r in C.RECIPES if p["cooked"].get(r["key"])]


def status(p, jr):
    """What's unlocked and cleared, plus totals the screens show."""
    unlocked, cleared = [], []
    prev_clear = True
    levels = p["levels"]
    for t in jr:
        keys = [lv["key"] for lv in t["levels"]]
        done = [k for k in keys if levels.get(k, {}).get("stars", [False])[0]]
        if prev_clear:
            for i, k in enumerate(keys):
                if i == 0 or keys[i - 1] in done:
                    unlocked.append(k)
        t_clear = prev_clear and len(done) == len(keys)
        if t_clear and keys:
            cleared.append(t["key"])
        prev_clear = t_clear
    all_keys = [lv["key"] for t in jr for lv in t["levels"]]
    chop_max = sum(1 for t in jr for lv in t["levels"] if totals(lv["data"])["chopsticks"])
    return {
        "unlocked": unlocked, "cleared": cleared,
        "stars": sum(sum(1 for s in levels.get(k, {}).get("stars", []) if s) for k in all_keys),
        "stars_max": 3 * len(all_keys),
        "chopsticks": sum(1 for k in all_keys if levels.get(k, {}).get("chop")),
        "clears": sum(1 for k in all_keys if levels.get(k, {}).get("stars", [False])[0]),
        "levels_max": len(all_keys),
        "chopsticks_max": chop_max,
        "perks": perks(p),
        "postcards_max": sum(1 for t in jr if any(totals(lv["data"])["postcard"] for lv in t["levels"])),
    }


def check_badges(p, jr, today):
    st = status(p, jr)
    have = p["badges"]
    s = p["stats"]
    tests = {
        "first_bite": any(v["stars"][0] for v in p["levels"].values()),
        "speedy": sum(1 for v in p["levels"].values() if v["stars"][2]) >= 5,
        "collector": len(p["seen"]) >= 20,
        "legend_hunter": any(C.ITEMS[k]["rarity"] == "legendary" for k in p["seen"] if k in C.ITEMS),
        "chef": len(p["cooked"]) >= 1,
        "master_chef": len(p["cooked"]) >= len(C.RECIPES),
        "fashionista": len([h for h in p["hats"] if h != "none"]) >= 5,
        "golden_touch": st["chopsticks"] >= 10,
        "pen_pal": st["postcards_max"] > 0 and len([x for x in p["postcards"] if any(t["key"] == x for t in jr)]) >= st["postcards_max"],
        "liberator": bool(jr) and len(st["cleared"]) == len([t for t in jr if t["levels"]]),
        "star_chef": st["stars"] >= 45,
        "traveller": st["clears"] >= 50,
        "century": st["clears"] >= 100,
        "constellation": st["stars"] >= 200,
        "chopstick_master": st["chopsticks"] >= 50,
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


def market_offers(today):
    """Today's market stall: the same offers for everyone, changing every day."""
    rnd = _rng("market:" + today.isoformat())
    pool = [k for k in C.ITEM_ORDER if C.ITEMS[k]["rarity"] != "legendary"]
    rares = [k for k in pool if C.ITEMS[k]["rarity"] == "rare"]
    picks = [rares[int(rnd() * len(rares))]]
    rest = [k for k in pool if k not in picks]
    for i in range(len(rest) - 1, 0, -1):  # Fisher-Yates
        j = int(rnd() * (i + 1))
        rest[i], rest[j] = rest[j], rest[i]
    picks += rest[:C.MARKET_SIZE - 1]
    qty = {"common": 3, "uncommon": 2, "rare": 1}
    out = []
    for k in picks:
        r = C.ITEMS[k]["rarity"]
        out.append({"id": "%s:%s" % (today.isoformat(), k), "item": k, "qty": qty[r],
                    "price": int(round(C.RARITY[r]["price"] * qty[r] * 0.75))})
    return out


def daily_items(today):
    """The daily box's ingredients: the same for everyone on a day (so a box opened offline syncs unchanged)."""
    rnd = _rng("daily:" + today.isoformat())
    keys = C.ITEM_ORDER
    weights = [C.RARITY[C.ITEMS[k]["rarity"]]["weight"] for k in keys]
    total = float(sum(weights))
    items: dict = {}
    for _n in range(C.DAILY["items"]):
        x, acc = rnd() * total, 0.0
        pick = keys[-1]
        for k, w in zip(keys, weights):
            acc += w
            if x < acc:
                pick = k
                break
        items[pick] = items.get(pick, 0) + 1
    return items


def view(p, jr, today):
    """What the screens need besides the journey and catalog."""
    return {"progress": p, "status": status(p, jr), "market": market_offers(today),
            "daily_ready": p["daily"]["last"] != today.isoformat(), "today": today.isoformat()}


# ---------------------------------------------------------------- the rules

def apply_finish(p, lv, jr, result, today):
    """Score a won level. `result` comes from the browser, so everything is capped by what the level holds."""
    key = lv["key"]
    if key not in status(p, jr)["unlocked"]:
        raise GameError("That level isn't unlocked yet.")
    data = lv["data"]
    tot = totals(data)
    result = result if isinstance(result, dict) else {}
    g = check_goals(lv, result)
    picked, npcs, errands, nests, kings, meat = g["picked"], g["npcs"], g["errands"], g["nests"], g["kings"], g["meat"]
    # Items: picked, minus what was handed over, plus thank-you gifts.
    bag = dict(picked)
    gifts: dict = {}
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
    rec: dict = p["levels"].get(key) or {"stars": [False, False, False], "best": None, "chop": False, "clears": 0}
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
    terr = None
    for tr in jr:
        if any(x["key"] == key for x in tr["levels"]):
            terr = tr
            break
    if result.get("postcard") and tot["postcard"] and terr and terr["key"] not in p["postcards"]:
        p["postcards"].append(terr["key"])
        postcard = {"territory": terr["key"], "name": terr["name"], "text": terr.get("_postcard") or ""}
    # Coins.
    pk = perks(p)
    pests = min(_int(result.get("pests")), 150)
    crates = min(_int(result.get("crates")), tot["crates"])
    parts = [("Coins picked up", min(_int(result.get("coins")), tot["coins"])),
             ("Pests bonked", pests * C.COINS["pest"] * (2 if "lucky" in pk else 1)),
             ("Crates smashed", crates * C.COINS["crate"]),
             ("Errands", len(errands) * C.COINS["errand"]),
             ("Nests destroyed", nests * C.COINS["nest"]),
             ("Bosses", kings * C.COINS["boss"]),
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
    s["knobs"] += min(_int(result.get("knobs")), 3 * tot["knobs"])
    s["bonuses"] += min(_int(result.get("bonuses")), tot["bonuses"])
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


def check_goals(lv, result):
    """What a reported win collected, capped by what the level holds; raises GameError when the goals aren't met."""
    data = lv["data"]
    tot = totals(data)
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
        raise GameError("The boss is still standing.")
    return {"picked": picked, "npcs": npcs, "errands": errands, "nests": nests, "kings": kings, "meat": meat}


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
    offer = None
    for o in market_offers(today):
        if o["id"] == offer_id:
            offer = o
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
    items = daily_items(today)
    new = [k for k in items if not p["seen"].get(k)]
    for k, n in items.items():
        p["pantry"][k] = p["pantry"].get(k, 0) + n
        p["seen"][k] = p["seen"].get(k, 0) + n
    p["stats"]["dailies"] += 1
    return p, {"coins": coins, "items": items, "streak": d["streak"], "new_items": new,
               "new_badges": check_badges(p, jr, today)}


# ---------------------------------------------------------------- the Daily Dish

def dish_no(today):
    """Today's Daily Dish number (#1 = Catalog.DISH_EPOCH)."""
    return (today - day(C.DISH_EPOCH)).days + 1


def dish_twist(today):
    """Today's twist: the same for everyone, gentler twists only early in the week."""
    rnd = _rng("dish-twist:" + today.isoformat())
    pool = [t for t in C.DISH_TWISTS if today.weekday() <= t["max_day"]]
    return pool[int(rnd() * len(pool))]


def dish_secret(today):
    """The day's secret ingredient for the first win (never a legendary one): (key, how many)."""
    rnd = _rng("dish-secret:" + today.isoformat())
    pool = [k for k in C.ITEM_ORDER if C.ITEMS[k]["rarity"] in ("uncommon", "rare")]
    k = pool[int(rnd() * len(pool))]
    return k, (1 if C.ITEMS[k]["rarity"] == "rare" else 2)


def dish_of(today, jr):
    """Today's Daily Dish for everyone: {no, day, level, territory, twist, secret, qty, tier}. The level comes from
    the part of the journey the weekday asks for (easy Monday, spicy Sunday), never a bonus round, no bosses Monday to
    Thursday. None when the journey has no levels."""
    wd = today.weekday()
    name, lo, hi = C.DISH_DAYS[wd]
    worlds = [t for t in jr if t["levels"]]
    nw = len(worlds)

    def pool_for(lo_f, hi_f, bosses):
        out = []
        for i, t in enumerate(worlds):
            if lo_f * nw <= i < max(hi_f * nw, lo_f * nw + 1):
                for lv in t["levels"]:
                    data = lv.get("data") or {}
                    if data.get("bonus"):
                        continue
                    if not bosses and totals(data)["kings"]:
                        continue
                    out.append((t, lv))
        return out
    pool = pool_for(lo, hi, wd >= 4) or pool_for(0.0, 1.0, True)
    if not pool:
        return None
    rnd = _rng("dish-level:" + today.isoformat())
    t, lv = pool[int(rnd() * len(pool))]
    secret, qty = dish_secret(today)
    return {"no": dish_no(today), "day": today.isoformat(), "level": lv["key"], "territory": t["key"],
            "twist": dish_twist(today), "secret": secret, "qty": qty, "tier": name, "weekday": wd}


def apply_dish(p, lv, jr, result, today):
    """A Daily Dish win. The first win of the day pays the coins and the secret ingredient; every win can improve the
    day's best time. Daily Dish wins never unlock levels or count as level clears."""
    dish = dish_of(today, jr)
    if not dish or dish["level"] != lv["key"]:
        raise GameError("Today's dish has changed. Open the Daily Dish again.")
    result = result if isinstance(result, dict) else {}
    check_goals(lv, result)
    t = round(max(3.0, min(float(result.get("time") or 0), 24 * 3600.0)), 2)
    hearts = _int(result.get("hearts"), 0, 9)
    iso = today.isoformat()
    d = p["dish"]
    first = iso not in d["days"]
    coins, gained, new_items = 0, {}, []
    if first:
        d["days"] = sorted(set(d["days"] + [iso]))[-DISH_KEEP:]
        coins = C.DISH["coins"]
        p["coins"] += coins
        k, n = dish["secret"], dish["qty"]
        gained = {k: n}
        if not p["seen"].get(k):
            new_items.append(k)
        p["pantry"][k] = p["pantry"].get(k, 0) + n
        p["seen"][k] = p["seen"].get(k, 0) + n
        p["stats"]["dishes"] += 1
        p["stats"]["coins_earned"] += coins
    old = d["best"] if d["best"] and d["best"]["day"] == iso else None
    new_best = old is None or t < old["time"]
    if new_best:
        d["best"] = {"day": iso, "time": t, "hearts": hearts}
    badges = check_badges(p, jr, today)
    return p, {"dish": dish["no"], "day": iso, "level": lv["key"], "time": t, "hearts": hearts, "first": first,
               "coins": coins, "gained": gained, "new_items": new_items, "new_best": new_best,
               "best": d["best"]["time"] if d["best"] else t, "new_badges": badges}


# ---------------------------------------------------------------- sync: additive merging

def diff(base, cur):
    """What changed from `base` (the last copy the server confirmed) to `cur` (this device's progress): counts as
    differences (coins and pantry can go down: spending and cooking), stars/hats/postcards/badges as what's new."""
    b, c = normalize(base), normalize(cur)
    d: dict = {"coins": c["coins"] - b["coins"], "pantry": {}, "seen": {}, "cooked": {}, "levels": {}, "stats": {},
               "hats": [h for h in c["hats"] if h not in b["hats"]],
               "hat": c["hat"] if c["hat"] != b["hat"] else None,
               "badges": {k: v for k, v in c["badges"].items() if k not in b["badges"]},
               "postcards": [x for x in c["postcards"] if x not in b["postcards"]],
               "daily": c["daily"] if c["daily"] != b["daily"] else None,
               "market": c["market"] if c["market"] != b["market"] else None,
               "dish": None}
    new_days = [x for x in c["dish"]["days"] if x not in b["dish"]["days"]]
    if new_days or c["dish"]["best"] != b["dish"]["best"]:
        d["dish"] = {"days": new_days, "best": c["dish"]["best"]}
    for f in ("pantry", "seen", "cooked"):
        for k in _unique(list(b[f].keys()) + list(c[f].keys())):
            n = c[f].get(k, 0) - b[f].get(k, 0)
            if n:
                d[f][k] = n
    for k in STAT_KEYS:
        n = c["stats"][k] - b["stats"][k]
        if n:
            d["stats"][k] = n
    for k, rec in c["levels"].items():
        old: dict = b["levels"].get(k) or {"stars": [False, False, False], "best": None, "chop": False, "clears": 0}
        ch = {"stars": [rec["stars"][i] and not old["stars"][i] for i in range(3)],
              "best": rec["best"] if rec["best"] is not None and (old["best"] is None or rec["best"] < old["best"]) else None,
              "chop": rec["chop"] and not old["chop"], "clears": max(0, rec["clears"] - old["clears"])}
        if any(ch["stars"]) or ch["best"] is not None or ch["chop"] or ch["clears"]:
            d["levels"][k] = ch
    return d


def is_empty(d):
    return not (d.get("coins") or d.get("pantry") or d.get("seen") or d.get("cooked") or d.get("levels") or d.get("stats")
                or d.get("hats") or d.get("hat") or d.get("badges") or d.get("postcards") or d.get("daily") or d.get("market")
                or d.get("dish"))


def clean_delta(d, known_levels=None):
    """A delta from a browser, made safe: known keys, whole numbers within limits, known levels only.
    known_levels may be a dict {level key: fastest plausible time}: a best time below it is dropped."""
    d = d if isinstance(d, dict) else {}
    out: dict = {"coins": _int(d.get("coins"), -10 ** 6, 10 ** 6), "pantry": {}, "seen": {}, "cooked": {}, "levels": {},
                 "stats": {}, "hats": [h for h in (d.get("hats") or []) if h in C.HAT_BY_KEY][:20],
                 "hat": d.get("hat") if d.get("hat") in C.HAT_BY_KEY else None,
                 "badges": {k: str(v)[:10] for k, v in (d.get("badges") or {}).items() if k in C.BADGE_KEYS},
                 "postcards": [str(x)[:40] for x in (d.get("postcards") or [])][:50],
                 "daily": None, "market": None, "dish": None}
    for f, ok in (("pantry", C.ITEMS), ("seen", C.ITEMS), ("cooked", C.RECIPE_BY_KEY)):
        for k, v in (d.get(f) or {}).items():
            if k in ok and _int(v, -10 ** 5, 10 ** 5):
                out[f][k] = _int(v, -10 ** 5, 10 ** 5)
    for k in STAT_KEYS:
        n = _int((d.get("stats") or {}).get(k), 0, 10 ** 6)
        if n:
            out["stats"][k] = n
    for k, v in (d.get("levels") or {}).items():
        if isinstance(v, dict) and isinstance(k, str) and (known_levels is None or k in known_levels):
            st = v.get("stars") or []
            best = v.get("best")
            floor = known_levels.get(k) or 3.0 if isinstance(known_levels, dict) else 3.0
            best = max(3.0, float(best)) if isinstance(best, (int, float)) and not isinstance(best, bool) else None
            out["levels"][k] = {"stars": [bool(st[i]) if i < len(st) else False for i in range(3)],
                                "best": best if best is not None and best >= floor else None,
                                "chop": bool(v.get("chop")), "clears": _int(v.get("clears"), 0, 10 ** 4)}
    dd = d.get("daily")
    if isinstance(dd, dict) and day(dd.get("last")):
        out["daily"] = {"last": str(dd["last"])[:10], "streak": _int(dd.get("streak"), 0, 10 ** 4)}
    m = d.get("market")
    if isinstance(m, dict) and day(m.get("day")):
        out["market"] = {"day": str(m["day"])[:10], "bought": [str(x)[:30] for x in (m.get("bought") or [])][:20]}
    if isinstance(d.get("dish"), dict):
        out["dish"] = _clean_dish(d["dish"])
    return out


def merge(p, d):
    """Add a delta on top of progress: plays, coins, items and stats add up; stars, chopsticks, hats, badges and
    postcards combine; the best time wins; the daily box and the market keep the later day."""
    p = normalize(p)
    p["coins"] = max(0, p["coins"] + _int(d.get("coins"), -10 ** 6, 10 ** 6))
    for f in ("pantry", "seen", "cooked"):
        for k, n in (d.get(f) or {}).items():
            v = p[f].get(k, 0) + _int(n, -10 ** 5, 10 ** 5)
            if v > 0:
                p[f][k] = v
            elif k in p[f]:
                del p[f][k]
    for k, n in (d.get("stats") or {}).items():
        if k in p["stats"]:
            p["stats"][k] += max(0, _int(n, 0, 10 ** 6))
    for k, ch in (d.get("levels") or {}).items():
        rec: dict = p["levels"].get(k) or {"stars": [False, False, False], "best": None, "chop": False, "clears": 0}
        st = ch.get("stars") or []
        rec["stars"] = [rec["stars"][i] or (bool(st[i]) if i < len(st) else False) for i in range(3)]
        b = ch.get("best")
        if isinstance(b, (int, float)) and (rec["best"] is None or b < rec["best"]):
            rec["best"] = round(float(b), 2)
        rec["chop"] = rec["chop"] or bool(ch.get("chop"))
        rec["clears"] = rec["clears"] + _int(ch.get("clears"), 0, 10 ** 4)
        p["levels"][k] = rec
    for h in d.get("hats") or []:
        if h in C.HAT_BY_KEY and h not in p["hats"]:
            p["hats"].append(h)
    if d.get("hat") in p["hats"]:
        p["hat"] = d["hat"]
    for k, v in (d.get("badges") or {}).items():
        if k not in p["badges"] or str(v) < p["badges"][k]:
            p["badges"][k] = str(v)[:10]
    for x in d.get("postcards") or []:
        if x not in p["postcards"]:
            p["postcards"].append(x)
    dd = d.get("daily")
    if dd and dd.get("last"):
        if not p["daily"]["last"] or dd["last"] > p["daily"]["last"]:
            p["daily"] = {"last": dd["last"], "streak": _int(dd.get("streak"), 0, 10 ** 4)}
        elif dd["last"] == p["daily"]["last"]:
            p["daily"]["streak"] = max(p["daily"]["streak"], _int(dd.get("streak"), 0, 10 ** 4))
    m = d.get("market")
    if m and m.get("day"):
        if not p["market"]["day"] or m["day"] > p["market"]["day"]:
            p["market"] = {"day": m["day"], "bought": list(m.get("bought") or [])[:20]}
        elif m["day"] == p["market"]["day"]:
            p["market"]["bought"] = _unique(p["market"]["bought"] + list(m.get("bought") or []))[:20]
    ds = d.get("dish")
    if isinstance(ds, dict):
        ds = _clean_dish(ds)
        p["dish"] = {"days": sorted(set(p["dish"]["days"] + ds["days"]))[-DISH_KEEP:],
                     "best": _better_best(p["dish"]["best"], ds["best"])}
    return p


def add_progress(p, other):
    """Everything in `other` (a guest's progress on this device) added on top of `p`."""
    return merge(p, diff(new_progress(), other))
