# Admin — Server Module. The level builder's server side. Every callable checks the admin flag.
import datetime as dt
import re
import secrets

import anvil.server
import anvil.users
from anvil.tables import app_tables

from . import Catalog as C
from . import Game as G
from . import Levels as L


def _admin():
    u = anvil.users.get_user()
    if not G.is_admin(u):
        raise anvil.server.PermissionDenied("Admins only.")
    return u


@anvil.server.callable
def admin_whoami():
    u = anvil.users.get_user()
    if u is None:
        return {"signed_in": False}
    return {"signed_in": True, "email": u["email"], "name": u["display_name"] or (u["email"] or "").split("@")[0],
            "is_admin": G.is_admin(u)}


def _level_out(l):
    errors, warnings = L.check(l["data"])
    return {"key": l["key"], "name": l["name"], "data": l["data"], "published": l["published"], "builtin": l["builtin"],
            "clears": l["clears"], "errors": errors, "warnings": warnings}


@anvil.server.callable
def admin_state():
    _admin()
    G.ensure_seeded()
    jr = G.journey(include_unpublished=True)
    orphans = [l for l in app_tables.levels.search() if l["territory"] is None]
    users = list(app_tables.users.search())
    return {
        "ok": True,
        "territories": [{"key": t["key"], "name": t["name"], "emoji": t["emoji"], "blurb": t["blurb"], "theme": t["theme"],
                         "pest": t["pest"], "postcard": t["_postcard"], "published": t["published"],
                         "levels": [_level_out(l) for l in t["levels"]]} for t in jr],
        "orphans": [l["key"] for l in orphans],
        "catalog": C.public(),
        "stats": {"players": len(users), "clears": sum((l["clears"] or 0) for l in app_tables.levels.search()),
                  "levels": len(app_tables.levels.search()), "feedback_new": _feedback_counts()["new"]},
        "builtin_keys": [lv["key"] for lv in L.LEVELS],
    }


def _slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "level").lower()).strip("-")[:30] or "level"
    return "%s-%s" % (s, secrets.token_hex(2))


def clean_data(d):
    """Keep only what the game understands; reject anything that isn't a level."""
    if not isinstance(d, dict):
        raise ValueError("Level data must be an object.")
    w, h = int(d.get("w")), int(d.get("h"))
    tiles = [str(r)[:w].ljust(w, ".") for r in (d.get("tiles") or [])][:h]
    while len(tiles) < h:
        tiles.append("." * w)
    tiles = ["".join(ch if ch in C.TILE_CHARS else "." for ch in r) for r in tiles]
    ents = []
    for e in d.get("ents") or []:
        if not isinstance(e, dict) or e.get("t") not in ("start", "exit", "item", "pickup", "pest", "nest", "npc"):
            continue
        x, y = int(e.get("x", -1)), int(e.get("y", -1))
        if not (0 <= x < w and 0 <= y < h):
            continue
        out = {"t": e["t"], "x": x, "y": y}
        if e["t"] in ("item", "pickup", "pest", "nest"):
            out["k"] = str(e.get("k") or "")[:30]
        if e["t"] == "nest":
            out["r"] = max(1, min(12, int(e.get("r") or 4)))
        if e["t"] == "npc":
            out.update({"style": e.get("style") if e.get("style") in C.NPC_STYLE_KEYS else "dumpling",
                        "name": str(e.get("name") or "Neighbour")[:30], "wants": str(e.get("wants") or "")[:30],
                        "count": max(1, min(20, int(e.get("count") or 1))),
                        "gift": (str(e.get("gift"))[:30] if e.get("gift") in C.ITEMS else None),
                        "gift_count": max(0, min(20, int(e.get("gift_count") or 0))),
                        "say": str(e.get("say") or "")[:240], "thanks": str(e.get("thanks") or "")[:240]})
        ents.append(out)
    g = d.get("goals") or {}
    return {"w": w, "h": h, "tiles": tiles, "ents": ents,
            "goals": {"meat": max(0, min(200, int(g.get("meat") or 0))), "errands": bool(g.get("errands")),
                      "nests": bool(g.get("nests"))},
            "par": max(5, min(3600, int(d.get("par") or 60))), "intro": str(d.get("intro") or "")[:400]}


def _territory(key):
    t = app_tables.territories.get(key=key)
    if t is None:
        raise ValueError("Unknown territory.")
    return t


@anvil.server.callable
def save_level(spec):
    """Create or update a level. A level with errors is saved as a draft (unpublished)."""
    _admin()
    try:
        data = clean_data(spec.get("data"))
        terr = _territory(spec.get("territory"))
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    errors, warnings = L.check(data)
    publish = bool(spec.get("published")) and not errors
    name = (str(spec.get("name") or "").strip() or "Untitled level")[:40]
    row = app_tables.levels.get(key=spec["key"]) if spec.get("key") else None
    if row is None:
        siblings = [l for l in app_tables.levels.search() if l["territory"] == terr]
        row = app_tables.levels.add_row(key=_slug(name), territory=terr, name=name, data=data, published=publish,
                                        updated=G._now(), builtin=False, clears=0,
                                        position=float(max([l["position"] or 0 for l in siblings] + [-1]) + 1))
    else:
        if row["territory"] != terr:
            siblings = [l for l in app_tables.levels.search() if l["territory"] == terr]
            row["position"] = float(max([l["position"] or 0 for l in siblings] + [-1]) + 1)
        row.update(territory=terr, name=name, data=data, published=publish, updated=G._now())
    out = admin_state()
    out.update(saved=row["key"], errors=errors, warnings=warnings,
               note="Saved as a draft: fix the errors to publish it." if spec.get("published") and errors else None)
    return out


@anvil.server.callable
def delete_level(key):
    _admin()
    row = app_tables.levels.get(key=key)
    if row is not None:
        for s in app_tables.scores.search(level=row):
            s.delete()
        row.delete()
    return admin_state()


@anvil.server.callable
def move_level(key, step):
    _admin()
    row = app_tables.levels.get(key=key)
    if row is None:
        return admin_state()
    sibs = sorted([l for l in app_tables.levels.search() if l["territory"] == row["territory"]],
                  key=lambda r: (r["position"] or 0, r["name"] or ""))
    i = sibs.index(row)
    j = max(0, min(len(sibs) - 1, i + (1 if step > 0 else -1)))
    sibs.insert(j, sibs.pop(i))
    for n, l in enumerate(sibs):
        l["position"] = float(n)
    return admin_state()


@anvil.server.callable
def save_territory(spec):
    _admin()
    name = (str(spec.get("name") or "").strip() or "New territory")[:40]
    fields = {"name": name, "emoji": (str(spec.get("emoji") or "🏮"))[:8], "blurb": str(spec.get("blurb") or "")[:200],
              "theme": spec.get("theme") if spec.get("theme") in C.THEME_KEYS else "kitchen",
              "pest": spec.get("pest") if spec.get("pest") in C.PEST_KEYS else "ant",
              "postcard": str(spec.get("postcard") or "")[:1200], "published": bool(spec.get("published", True))}
    row = app_tables.territories.get(key=spec["key"]) if spec.get("key") else None
    if row is None:
        pos = max([t["position"] or 0 for t in app_tables.territories.search()] + [-1]) + 1
        app_tables.territories.add_row(key=_slug(name), position=float(pos), **fields)
    else:
        row.update(**fields)
    return admin_state()


@anvil.server.callable
def move_territory(key, step):
    _admin()
    rows = sorted(app_tables.territories.search(), key=lambda r: (r["position"] or 0, r["name"] or ""))
    row = next((r for r in rows if r["key"] == key), None)
    if row is not None:
        i = rows.index(row)
        j = max(0, min(len(rows) - 1, i + (1 if step > 0 else -1)))
        rows.insert(j, rows.pop(i))
        for n, r in enumerate(rows):
            r["position"] = float(n)
    return admin_state()


@anvil.server.callable
def delete_territory(key):
    _admin()
    row = app_tables.territories.get(key=key)
    if row is not None:
        if any(l["territory"] == row for l in app_tables.levels.search()):
            out = admin_state()
            out.update(ok=False, error="Move or delete this territory's levels first.")
            return out
        row.delete()
    return admin_state()


@anvil.server.callable
def restore_level(key):
    """Put a built-in level back to how it shipped."""
    _admin()
    lv = next((x for x in L.LEVELS if x["key"] == key), None)
    row = app_tables.levels.get(key=key)
    if lv and row is not None:
        row.update(data=lv["data"], name=lv["name"], updated=G._now())
    return admin_state()


@anvil.server.callable
def restore_defaults():
    """Add back any built-in territories or levels that were deleted (edited ones are left alone)."""
    _admin()
    n = G.seed_defaults()
    out = admin_state()
    out["note"] = "Restored %d missing item(s)." % n if n else "Nothing was missing."
    return out


@anvil.server.callable
def list_players():
    _admin()
    jr = G.journey()
    out = []
    for u in app_tables.users.search():
        p = G.normalize(u["progress"]) if u["progress"] else G.new_progress()
        st = G.status(p, jr)
        out.append({"email": u["email"], "name": u["display_name"] or "", "is_admin": bool(u["is_admin"]),
                    "signed_up": G._iso(u["signed_up"]), "last_played": G._iso(u["last_played"]),
                    "stars": st["stars"], "coins": p["coins"], "cleared": len([v for v in p["levels"].values() if v["stars"][0]]),
                    "recipes": len(p["cooked"]), "found": len(p["seen"])})
    out.sort(key=lambda r: r["last_played"] or "", reverse=True)
    return {"ok": True, "players": out[:500]}


@anvil.server.callable
def set_admin(email, flag):
    me = _admin()
    u = app_tables.users.get(email=email)
    if u is None:
        return {"ok": False, "error": "No such player."}
    if u == me and not flag:
        return {"ok": False, "error": "You can't remove your own admin rights."}
    u["is_admin"] = bool(flag)
    return list_players()


# ---------------------------------------------------------------- feedback inbox

FEEDBACK_STATUSES = ("new", "read", "done")


def _feedback_counts():
    counts = {s: 0 for s in FEEDBACK_STATUSES}
    for r in app_tables.feedback.search():
        counts[r["status"] if r["status"] in counts else "new"] += 1
    return counts


@anvil.server.callable
def list_feedback(status=None):
    _admin()
    rows = sorted(app_tables.feedback.search(), key=lambda r: r["created"] or G._now(), reverse=True)
    items = []
    for r in rows:
        if status and (r["status"] or "new") != status:
            continue
        items.append({"id": r.get_id(), "kind": r["kind"] or "other", "kind_name": G.FEEDBACK_KINDS.get(r["kind"], "Other"),
                      "message": r["message"], "name": r["name"], "email": r["email"], "context": r["context"] or {},
                      "created": G._iso(r["created"]), "status": r["status"] or "new"})
    return {"ok": True, "items": items[:500], "counts": _feedback_counts()}


@anvil.server.callable
def set_feedback_status(row_id, status, filter_status=None):
    _admin()
    r = app_tables.feedback.get_by_id(row_id)
    if r is not None and status in FEEDBACK_STATUSES:
        r["status"] = status
    return list_feedback(filter_status)


@anvil.server.callable
def delete_feedback(row_id, filter_status=None):
    _admin()
    r = app_tables.feedback.get_by_id(row_id)
    if r is not None:
        r.delete()
    return list_feedback(filter_status)
