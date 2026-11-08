from anvil import *

from ._anvil_designer import ItemInfoTemplate
from ... import bun


class ItemInfo(ItemInfoTemplate):
    """One ingredient from the pantry: what it is, how many you have, where it's found, which recipes use it."""

    def __init__(self, key=None, **properties):
        super().__init__(**properties)
        i, p, dn = bun.item(key), bun.st["progress"], self.dom_nodes
        known = bool(p["seen"].get(key))
        rar = bun.rarity(i["rarity"])
        dn["emo"].textContent = i["emoji"]
        if not known:
            dn["emo"].className = "g-bigemo bb-emoji unknown"
        dn["name"].textContent = i["name"] if known else "???"
        dn["rar"].textContent = rar["name"]
        dn["rar"].className = "g-rar rar-" + i["rarity"]
        dn["desc"].textContent = i.get("desc") or "" if known else "You haven't found this yet."
        self.facts_panel.items = [{"t": "In pantry: %s" % (p["pantry"].get(key) or 0)},
                                  {"t": "Found in total: %s" % p["seen"].get(key)}] if known else []
        where = bun.where_found().get(key) or []
        dn["where"].textContent = "Where: " + (", ".join(where) or (
            "Somewhere legendary…" if i["rarity"] == "legendary" else "The daily market box or the market stall"))
        uses = [r for r in bun.st["catalog"]["recipes"] if key in r["needs"]]
        dn["uses"].textContent = ("Used in: " + ", ".join(r["emoji"] + " " + r["name"] for r in uses)) if uses else ""
        dn["uses"].hidden = not uses

    def close_click(self, event):
        self.raise_event("x-close-alert", value=None)
