from anvil import *

from ._anvil_designer import PantryItemTemplate
from ... import bun


class PantryItem(PantryItemTemplate):
    """Pantry → one ingredient: how many you have, its rarity; unknown ones are a shadow with a hint where to look."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, dn = self.item["i"], self.dom_nodes
        p = bun.st["progress"]
        known = bool(p["seen"].get(i["key"]))
        rar = bun.rarity(i["rarity"])
        dn["box"].className = "g-it r-%s%s" % (i["rarity"], "" if known else " unknown")
        dn["new_tag"].hidden = not (known and not self.item["seen_new"].get(i["key"]))
        dn["cnt"].hidden = not known
        dn["cnt"].textContent = "×%d" % (p["pantry"].get(i["key"]) or 0)
        dn["emo"].textContent = i["emoji"]
        dn["name"].textContent = i["name"] if known else "???"
        dn["rar"].textContent = rar["name"]
        dn["rar"].className = "g-rar rar-" + i["rarity"]
        where = self.item["where"].get(i["key"])
        dn["where"].hidden = known
        dn["where"].textContent = where[0] if where else ("A legend…" if i["rarity"] == "legendary" else "The market box")
        dn["box"].setAttribute("aria-label", (i["name"] if known else "Not discovered yet") + ", " + rar["name"])
        dn["box"].addEventListener("click", self._click)

    def _click(self, event):
        self.dom_nodes["new_tag"].hidden = True
        self.item["host"].open_item(self.item["i"]["key"])
