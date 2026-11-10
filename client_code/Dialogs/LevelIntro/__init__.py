from anvil import *
from anvil.js import window

from ._anvil_designer import LevelIntroTemplate
from ... import bun


def board_rows(b, guest):
    """Leaderboard lines for BoardRow: the top 5, you below them if you're further down, a note for guests."""
    if b and b.get("offline"):
        return [{"rank": None, "name": "📴 Offline: the leaderboard comes back when you're online."}]
    if not b or not b.get("top"):
        return [{"rank": None, "name": "No times yet. Be the first!"}]
    rows = [dict(r) for r in b["top"][:5]]
    you = b.get("you")
    if you and you.get("rank", 0) > 5:
        rows.append(dict(you, name=you["name"] + " (you)", you=True))
    if guest:
        rows.append({"rank": None, "name": "Create an account to get on the board."})
    return rows


class LevelIntro(LevelIntroTemplate):
    """A level's card on the map: where it is, a preview, goals, the ingredients in it (unknown ones as ???), par and
    best time, stars, hidden chopsticks/postcard, the top buns. Closes with "play"."""

    def __init__(self, key=None, **properties):
        super().__init__(**properties)
        t, l = bun.find_level(key)
        self.key, self._t, self._l = key, t, l
        dn, data = self.dom_nodes, l["data"]
        rec, info, seen = bun.level_rec(key), bun.level_info(data), bun.st["progress"]["seen"]
        dn["where"].textContent = "%s %s · %s" % (t["emoji"], t["name"], bun.level_label(t, l))
        dn["name"].textContent = l["name"]
        self.bonus.visible = info["bonus"]
        dn["intro"].textContent = data.get("intro") or ""
        dn["intro"].hidden = not data.get("intro")
        self.goals_panel.items = [{"e": e, "t": txt} for e, txt in bun.goals(data, info)]
        ks = sorted(info["items"].keys(), key=lambda k: bun.RARITY_ORDER.get(bun.item(k)["rarity"], 0))
        chips = []
        for k in ks:
            it, known = bun.item(k), seen.get(k)
            chips.append({"e": it["emoji"], "t": "%s ×%d" % (it["name"] if known else "???", info["items"][k]),
                          "kind": "g-chip" + ("" if known else " unknown"), "title": it["name"] if known else "Not discovered yet"})
        self.items_panel.items = chips
        facts = [{"t": "⏱ Par " + bun.fmt_time(data.get("par") or 60)}, {"t": "🏆 Best " + bun.fmt_time(rec.get("best"))},
                 {"t": bun.stars_text(rec["stars"]), "title": "%d of 3 stars" % bun.stars_of(key)}]
        if info["chop"]:
            facts.append({"e": "🥢", "t": "Found!" if rec.get("chop") else "Hidden here"})
        if info["post"]:
            facts.append({"e": "✉️", "t": "Postcard found" if t.get("postcard") else "A postcard is hidden here"})
        self.facts_panel.items = facts
        self.board_panel.items = [{"rank": None, "name": "Loading…"}]

    @handle("", "show")
    def form_show(self, **event_args):
        width = min(460, int(window.innerWidth) - 90)
        self.thumb.show(self._l["data"], self._t["theme"], max(160, width))
        b = bun.leaderboard(self.key)
        if b and b.get("total"):
            self.dom_nodes["board_title"].textContent = "Top buns · %d player%s" % (b["total"], "" if b["total"] == 1 else "s")
        self.board_panel.items = board_rows(b, bun.st["guest"])

    @handle("play_button", "click")
    def play_button_click(self, **event_args):
        self.raise_event("x-close-alert", value="play")

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
