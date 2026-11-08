from anvil import *

from ._anvil_designer import ChipTemplate


class Chip(ChipTemplate):
    """A little pill: {"e": emoji, "t": text, "kind": "g-chip" (default) / "g-need ok" ..., "new": bool, "title": tip}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, dn = self.item, self.dom_nodes
        dn["chip"].className = i.get("kind") or "g-chip"
        if i.get("title"):
            dn["chip"].title = i["title"]
        dn["new_tag"].hidden = not i.get("new")
        dn["emo"].textContent = i.get("e") or ""
        dn["emo"].hidden = not i.get("e")
        dn["txt"].textContent = i.get("t") or ""
