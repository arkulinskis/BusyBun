from anvil import *

from ._anvil_designer import PantrySectionTemplate


class PantrySection(PantrySectionTemplate):
    """Pantry → one category (meat, greens, spices...) with its ingredient tiles."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c, dn = self.item["c"], self.dom_nodes
        dn["emo"].textContent = c["emoji"]
        dn["name"].textContent = c["name"]
        dn["blurb"].textContent = c.get("blurb") or ""
        self.grid.items = [{"i": i, "where": self.item["where"], "seen_new": self.item["seen_new"], "host": self.item["host"]}
                           for i in self.item["items"]]
