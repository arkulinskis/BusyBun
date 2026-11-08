from anvil import *

from ._anvil_designer import PantryTemplate
from ... import bun, flows


class Pantry(PantryTemplate):
    """#pantry: every ingredient by category (unknown ones as ??? with a hint where to look), treasures, postcards."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        bun.music("menu")
        if bun.ensure():
            self.draw()

    def draw(self):
        st, dn = bun.st, self.dom_nodes
        p, s, cat = st["progress"], st["status"], st["catalog"]
        items = cat["items"]
        seen_n = len([i for i in items if p["seen"].get(i["key"])])
        pct = int(round(100.0 * seen_n / max(1, len(items))))
        dn["found"].textContent = "%d / %d discovered" % (seen_n, len(items))
        dn["found_fill"].style.width = "%d%%" % pct
        dn["found_bar"].setAttribute("aria-valuenow", str(pct))
        seen_new = bun.get("bb.seenNew", {}) or {}
        where = bun.where_found()
        self.sections_panel.items = [{"c": c, "items": [i for i in items if i["cat"] == c["key"]], "where": where,
                                      "seen_new": seen_new, "host": self} for c in cat["categories"]]
        hats = len([h for h in p["hats"] if h != "none"])
        dn["t_chop"].textContent = "%d / %d found" % (s["chopsticks"], s["chopsticks_max"])
        dn["t_recipes"].textContent = "%d / %d cooked" % (len(p["cooked"]), len(cat["recipes"]))
        dn["t_hats"].textContent = "%d / %d owned" % (hats, len(cat["hats"]) - 1)
        dn["t_terr"].textContent = "%d / %d liberated" % (len(s["cleared"]), len(st["journey"]))
        self.cards_panel.items = [{"t": t} for t in st["journey"]]

    def open_item(self, key):
        seen_new = bun.get("bb.seenNew", {}) or {}
        seen_new[key] = 1
        bun.put("bb.seenNew", seen_new)
        flows.item_info(key)
