from anvil import *

from ._anvil_designer import BadgesTemplate
from ... import bun


class Badges(BadgesTemplate):
    """#badges: every badge (earned with its date, or progress towards it) and the player's stats."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        bun.music("menu")
        if bun.ensure():
            p, cat = bun.st["progress"], bun.st["catalog"]
            self.dom_nodes["lead"].textContent = "%d of %d earned." % (len(p["badges"]), len(cat["badges"]))
            self.badges_panel.items = [{"b": b} for b in cat["badges"]]
            s = p["stats"]
            rows = [("🥩", "Meat collected", s.get("meat")), ("🧹", "Pests bonked", s.get("pests")),
                    ("💥", "Nests destroyed", s.get("nests")), ("📦", "Crates smashed", s.get("crates")),
                    ("🤝", "Errands", s.get("errands")), ("🏁", "Levels finished", s.get("runs")),
                    ("🍳", "Recipes cooked", s.get("cooked")), ("🪙", "Coins earned", s.get("coins_earned")),
                    ("👑", "Bosses beaten", s.get("bosses") or 0), ("🎛️", "Stoves switched off", s.get("knobs") or 0),
                    ("🌟", "Bonuses grabbed", s.get("bonuses") or 0)]
            self.stats_panel.items = [{"e": e, "t": "%s: %s" % (t, v or 0)} for e, t, v in rows]
