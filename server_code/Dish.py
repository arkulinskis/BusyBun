# Dish — Server Module. The Daily Dish board: one level a day, the same for everyone (rules.dish_of), one best time per
# player per day in the table dish_runs. The win itself (coins, the secret ingredient, the week's stamps) is scored on
# the device by rules.apply_dish and reaches the account through Game.sync like every other action; this module only
# keeps the public board honest: signed-in players only, today's dish only, the goals met (rules.check_goals) and a
# time a bun could really manage with the twist's perks (Levels.min_time).
import re

import anvil.server
import anvil.tables as tables
import anvil.users
from anvil.tables import app_tables

from . import Game as G
from . import Levels as L
from . import rules as R

BOARD_SIZE = 10


def _today(day):
    """The player's local date, accepted only within a day of UTC (like the daily box)."""
    return G._client_today(day)


def _name(u):
    return re.sub(r"\s+", " ", str((u["display_name"] if u is not None else None) or "Bun")).strip()[:24] or "Bun"


@anvil.server.callable
def dish_submit(day, level_key, result):
    """Put a Daily Dish win on the day's board (the best time per player and day is kept). Returns the board."""
    u = anvil.users.get_user()
    if u is None:
        raise anvil.server.PermissionDenied("Please sign in to put your time on the board.")
    d = _today(day)
    if d.isoformat() != str(day or "")[:10]:
        return {"ok": False, "error": "That Daily Dish is over. Today's dish is waiting!"}
    G.ensure_seeded()
    jr = G.journey()
    dish = R.dish_of(d, jr)
    if not dish or dish["level"] != level_key:
        return {"ok": False, "error": "Today's dish changed. Reload the Daily Dish and try again."}
    lv = R.level_of(level_key, jr)
    result = result if isinstance(result, dict) else {}
    try:
        R.check_goals(lv, result)
        t = float(result.get("time"))
    except R.GameError as e:
        return {"ok": False, "error": str(e)}
    except Exception:
        return {"ok": False, "error": "That result doesn't look right."}
    if not (L.min_time(lv["data"], dish["twist"]["perks"]) <= t <= 24 * 3600.0):
        return {"ok": False, "error": "That time doesn't look possible, so it stays off the board."}
    twist = dish["twist"]
    max_hearts = twist["hearts"] or (3 + (1 if "hearty" in twist["perks"] else 0))
    hearts = max(1, min(max_hearts, R._int(result.get("hearts"), 1, 9)))
    row = app_tables.dish_runs.get(day=d.isoformat(), user=u)
    kept = False
    if row is None:
        app_tables.dish_runs.add_row(day=d.isoformat(), user=u, name=_name(u), time=round(t, 2), hearts=float(hearts),
                                     at=G._now())
    elif t < (row["time"] or 10 ** 9):
        row.update(time=round(t, 2), hearts=float(hearts), name=_name(u), at=G._now())
    else:
        row["name"] = _name(u)
        kept = True
    out = _board(d.isoformat(), u, t)
    out.update(ok=True, kept=kept)
    return out


@anvil.server.callable
def dish_board(day=None, time=None):
    """Today's Daily Dish board for anyone: the top 10, how many played, you (signed in), and where `time` would rank."""
    d = _today(day)
    try:
        t = float(time) if time is not None else None
    except Exception:
        t = None
    out = _board(d.isoformat(), anvil.users.get_user(), t)
    out["ok"] = True
    return out


def _board(iso, u=None, t=None):
    rows = list(app_tables.dish_runs.search(tables.order_by("time"), day=iso))
    top, you = [], None
    for i, r in enumerate(rows):
        mine = u is not None and r["user"] == u
        entry = {"rank": i + 1, "name": r["name"] or "Bun", "time": r["time"], "hearts": int(r["hearts"] or 0),
                 "you": mine}
        if i < BOARD_SIZE:
            top.append(entry)
        if mine:
            you = entry
    rank_if = None
    if t is not None:
        rank_if = 1 + sum(1 for r in rows if (r["time"] or 0) < t and not (u is not None and r["user"] == u))
    return {"day": iso, "top": top, "you": you, "total": len(rows), "rank_if": rank_if}
